from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from dataclasses import replace
from io import StringIO
from pathlib import Path

from codex_wake.webhook_lifecycle import (
    WebhookListenerConfig, WebhookListenerStore, WebhookServiceConfig,
    install_webhook_service, render_webhook_unit, stop_webhook_service,
    disable_webhook_listener, linux_service_bind_probe, uninstall_webhook_service,
    webhook_http_config_kwargs, webhook_readiness, webhook_service_status, webhook_support,
)
from codex_wake.webhook_listener import run_listener
from codex_wake.cli import main as cli_main


class WebhookListenerConfigTests(unittest.TestCase):
    def test_owner_store_persists_bounded_configuration_and_only_opaque_refs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "wake"
            config = WebhookListenerConfig(
                source_instance="github-webhook",
                address="127.0.0.1",
                port=8820,
                secret_ref="CODEX_WAKE_WEBHOOK_SECRET",
                previous_secret_ref="CODEX_WAKE_WEBHOOK_SECRET_PREVIOUS",
                enabled=True,
            )

            store = WebhookListenerStore(root)
            store.configure(config)

            self.assertEqual(WebhookListenerStore(root).select("github-webhook"), config)
            payload = json.loads(store.path.read_text(encoding="utf-8"))
            rendered = json.dumps(payload)
            self.assertNotIn("fixture-secret", rendered)
            self.assertIn("CODEX_WAKE_WEBHOOK_SECRET", rendered)
            self.assertEqual(payload["schema_version"], 1)
            self.assertFalse(payload["listeners"][0]["allow_non_loopback"])
            self.assertEqual(payload["listeners"][0]["max_connections"], 8)
            self.assertEqual(payload["listeners"][0]["max_body_bytes"], 262_144)

    def test_only_enabled_toggle_may_reuse_a_listener_instance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = WebhookListenerStore(Path(tmp) / "wake")
            config = WebhookListenerConfig("github-webhook", secret_ref="CODEX_WAKE_WEBHOOK_SECRET")
            store.configure(config)
            original = store.path.read_bytes()
            store.configure(config)
            self.assertEqual(store.path.read_bytes(), original)
            store.configure(replace(config, enabled=True))
            with self.assertRaisesRegex(ValueError, "new source_instance"):
                store.configure(replace(config, port=9444))

    def test_rejects_public_wildcard_and_secret_values(self) -> None:
        for values in (
            {"address": "0.0.0.0"},
            {"address": "localhost"},
            {"secret_ref": "fixture-secret"},
            {"secret_ref": "CODEX_WAKE_WEBHOOK_SECRET", "previous_secret_ref": "CODEX_WAKE_WEBHOOK_SECRET"},
        ):
            with self.subTest(values=values), self.assertRaisesRegex(ValueError, "configuration is invalid"):
                WebhookListenerConfig("github-webhook", **values)

    def test_non_loopback_requires_persisted_named_opt_in(self) -> None:
        with self.assertRaisesRegex(ValueError, "configuration is invalid"):
            WebhookListenerConfig("github-webhook", address="192.0.2.10", secret_ref="CODEX_WAKE_WEBHOOK_SECRET")
        configured = WebhookListenerConfig(
            "github-webhook", address="192.0.2.10", allow_non_loopback=True,
            secret_ref="CODEX_WAKE_WEBHOOK_SECRET",
        )
        self.assertTrue(configured.allow_non_loopback)
        self.assertEqual(webhook_http_config_kwargs(configured)["max_workers"], 1)
        self.assertNotIn("queue", webhook_http_config_kwargs(configured))
        with self.assertRaisesRegex(ValueError, "configuration is invalid"):
            WebhookListenerConfig("github-webhook", address="0.0.0.0", allow_non_loopback=True, secret_ref="CODEX_WAKE_WEBHOOK_SECRET")

    def test_executable_uses_injected_blocking_runtime_without_disclosing_secret(self) -> None:
        class Runtime:
            def __init__(self) -> None:
                self.served = False
                self.timeout = None
                self.resolve_secret = None
            def serve(self) -> None:
                self.served = True
                assert self.resolve_secret is not None
                self.resolved = self.resolve_secret("CODEX_WAKE_WEBHOOK_SECRET")
            def shutdown(self) -> None:
                self.timeout = True
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "wake"
            WebhookListenerStore(root).configure(WebhookListenerConfig(
                "github-webhook", secret_ref="CODEX_WAKE_WEBHOOK_SECRET", enabled=True,
            ))
            runtime = Runtime()
            received = []
            result = run_listener(
                wake_root=root, source_instance="github-webhook",
                runtime_factory=lambda config, resolve_secret: received.append((config, resolve_secret)) or setattr(runtime, "resolve_secret", resolve_secret) or runtime,
                env={"CODEX_WAKE_WEBHOOK_SECRET": "fixture-secret"},
            )
            self.assertEqual(result, 0)
            self.assertTrue(runtime.served)
            self.assertTrue(runtime.timeout)
            self.assertEqual(runtime.resolved, b"fixture-secret")
            self.assertNotIn("fixture-secret", json.dumps(WebhookListenerStore(root).listeners(), default=str))

    def test_rendered_unit_and_support_omit_secret_references(self) -> None:
        config = WebhookServiceConfig(
            name="codex-wake-github-webhook-github-webhook.service",
            wake_root=Path("/tmp/wake"), source_instance="github-webhook",
            executable_path=Path("/usr/local/bin/codex-wake-github-webhook"),
            unit_path=Path("/tmp/unit"), log_path=Path("/tmp/log"),
        )
        rendered = render_webhook_unit(config)
        self.assertIn("TimeoutStopSec=15", rendered)
        self.assertNotIn("ProtectHome", rendered)
        self.assertNotIn("SECRET", rendered)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "wake"
            WebhookListenerStore(root).configure(WebhookListenerConfig(
                "github-webhook", secret_ref="CODEX_WAKE_WEBHOOK_SECRET", enabled=True,
            ))
            support = webhook_support(wake_root=root, source_instance="github-webhook")
            self.assertNotIn("CODEX_WAKE_WEBHOOK_SECRET", json.dumps(support))
            self.assertEqual(support["webhook_listener"]["provider_delivery"], "unproven")

    def test_user_service_lifecycle_and_foreign_unit_fail_closed(self) -> None:
        class Runner:
            def __init__(self) -> None:
                self.calls = []
            def run(self, args, *, check=True):
                self.calls.append((args, check))
                output = "active\n" if "is-active" in args else "enabled\n" if "is-enabled" in args else ""
                return subprocess.CompletedProcess(args, 0, output, "")
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            config = WebhookServiceConfig(
                "codex-wake-github-webhook-github-webhook.service", base / "wake", "github-webhook",
                base / "bin" / "codex-wake-github-webhook", base / "unit" / "listener.service", base / "log",
            )
            runner = Runner()
            install_webhook_service(config, runner)
            self.assertIn("Restart=on-failure", config.unit_path.read_text())
            self.assertEqual(webhook_service_status(config, runner), ("active", "enabled"))
            stop_webhook_service(config, runner)
            uninstall_webhook_service(config, runner)
            self.assertFalse(config.unit_path.exists())
            config.unit_path.parent.mkdir(exist_ok=True)
            config.unit_path.write_text("foreign", encoding="utf-8")
            config.unit_path.chmod(0o600)
            with self.assertRaisesRegex(Exception, "ownership is invalid"):
                install_webhook_service(config, runner, start=False)

    def test_disable_stops_active_owner_before_persisting(self) -> None:
        class Runner:
            def __init__(self) -> None:
                self.active = True
            def run(self, args, *, check=True):
                if "disable" in args:
                    self.active = False
                output = "active\n" if "is-active" in args and self.active else "inactive\n" if "is-active" in args else "disabled\n"
                return subprocess.CompletedProcess(args, 0, output, "")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "wake"
            store = WebhookListenerStore(root)
            enabled = WebhookListenerConfig("github-webhook", secret_ref="CODEX_WAKE_WEBHOOK_SECRET", enabled=True)
            store.configure(enabled)
            disabled = disable_webhook_listener(store, replace(enabled, enabled=False), Runner())
            self.assertFalse(disabled.enabled)
            self.assertFalse(store.select("github-webhook").enabled)

    def test_install_rejects_disabled_source_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            config = WebhookServiceConfig("listener.service", base / "wake", "github-webhook", base / "bin", base / "unit", base / "log", source_enabled=False)
            with self.assertRaisesRegex(Exception, "requires an enabled source"):
                install_webhook_service(config, start=False)

    def test_linux_probe_requires_main_pid_socket_inode_and_exact_bind(self) -> None:
        class Runner:
            def run(self, args, *, check=True):
                return subprocess.CompletedProcess(args, 0, "42\n", "")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "wake"
            WebhookListenerStore(root).configure(WebhookListenerConfig("github-webhook", secret_ref="CODEX_WAKE_WEBHOOK_SECRET", enabled=True))
            proc = Path(tmp) / "proc"
            fd = proc / "42" / "fd"
            fd.mkdir(parents=True)
            (fd / "3").symlink_to("socket:[12345]")
            (proc / "net").mkdir()
            (proc / "net" / "tcp").write_text("sl local rem st tx rx tr tm retr uid timeout inode\n0: 0100007F:2274 00000000:0000 0A 00:0 0 0 0 0 12345\n")
            config = WebhookServiceConfig("listener.service", root, "github-webhook", None, Path(tmp) / "unit", Path(tmp) / "log")
            self.assertTrue(linux_service_bind_probe(config, Runner(), proc_root=proc))

    def test_readiness_requires_runtime_bind_and_safe_journal_proofs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "wake"
            store = WebhookListenerStore(root)
            store.configure(WebhookListenerConfig("github-webhook", secret_ref="CODEX_WAKE_WEBHOOK_SECRET", enabled=True))
            blocked = webhook_readiness(
                wake_root=root, source_instance="github-webhook", runtime_available=True,
                bind_probe=lambda address, port: False, journal_probe=lambda path: True,
            )
            self.assertEqual(blocked["status"], "blocked")
            self.assertEqual(blocked["bind_ownership"], "unproven")
            blocked_journal = webhook_readiness(
                wake_root=root, source_instance="github-webhook", runtime_available=True,
                bind_probe=lambda address, port: True, journal_probe=lambda path: False,
            )
            self.assertEqual(blocked_journal["status"], "blocked")
            self.assertEqual(blocked_journal["journal_access"], "unsafe")

    def test_cli_configure_and_show_are_nonsecret_json_surfaces(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "wake"
            self.assertEqual(cli_main([
                "--wake-root", str(root), "github-webhook", "source", "configure",
                "--source", "github-webhook", "--secret-ref", "CODEX_WAKE_WEBHOOK_SECRET", "--enabled",
            ]), 0)
            self.assertEqual(cli_main([
                "--wake-root", str(root), "github-webhook", "source", "show", "github-webhook", "--json",
            ]), 0)
            self.assertEqual(WebhookListenerStore(root).select("github-webhook").address, "127.0.0.1")
            self.assertEqual(WebhookListenerStore(root).select("github-webhook").port, 8820)
            self.assertEqual(cli_main([
                "--wake-root", str(root), "github-webhook", "source", "configure",
                "--source", "public-webhook", "--bind-address", "192.0.2.10",
                "--secret-ref", "CODEX_WAKE_WEBHOOK_SECRET", "--enabled",
            ]), 2)
            self.assertEqual(cli_main([
                "--wake-root", str(root), "github-webhook", "source", "configure",
                "--source", "public-webhook", "--bind-address", "192.0.2.10", "--allow-non-loopback",
                "--secret-ref", "CODEX_WAKE_WEBHOOK_SECRET", "--enabled",
            ]), 0)

    def test_secret_canary_is_absent_from_cli_unit_status_and_support(self) -> None:
        canary = "super-secret-canary-value"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "wake"
            output = StringIO()
            with redirect_stdout(output):
                self.assertEqual(cli_main([
                    "--wake-root", str(root), "github-webhook", "source", "configure",
                    "--source", "github-webhook", "--secret-ref", "CODEX_WAKE_WEBHOOK_SECRET", "--enabled",
                ]), 0)
                self.assertEqual(cli_main([
                    "--wake-root", str(root), "github-webhook", "source", "show", "github-webhook", "--json",
                ]), 0)
            stored = WebhookListenerStore(root).select("github-webhook")
            unit = render_webhook_unit(WebhookServiceConfig(
                "codex-wake-github-webhook-github-webhook.service", root, "github-webhook",
                Path("/usr/bin/codex-wake-github-webhook"), Path(tmp) / "unit", Path(tmp) / "log",
            ))
            readiness = webhook_readiness(
                wake_root=root, source_instance="github-webhook", runtime_available=True,
                bind_probe=lambda address, port: False, journal_probe=lambda path: False,
            )
            support = webhook_support(
                wake_root=root, source_instance="github-webhook", runtime_available=True,
                bind_probe=lambda address, port: False, journal_probe=lambda path: False,
            )
            self.assertNotIn(canary, output.getvalue())
            self.assertNotIn(canary, unit)
            self.assertNotIn(canary, json.dumps(readiness))
            self.assertNotIn(canary, json.dumps(support))
            self.assertNotIn(canary, WebhookListenerStore(root).path.read_text())
            self.assertNotIn(canary, stored.secret_ref)


if __name__ == "__main__":
    unittest.main()
