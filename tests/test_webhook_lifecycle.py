from __future__ import annotations

import json
import hashlib
import socket
import sqlite3
import threading
import subprocess
import tempfile
import unittest
from datetime import timedelta
from contextlib import redirect_stdout
from dataclasses import replace
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from codex_wake.webhook_lifecycle import (
    WebhookListenerConfig, WebhookListenerStore, WebhookServiceConfig,
    build_webhook_service_config, install_webhook_service, render_webhook_unit, stop_webhook_service,
    disable_webhook_listener, linux_service_bind_probe, uninstall_webhook_service,
    _journal_is_safe, secret_environment_has_references, webhook_http_config_kwargs, webhook_readiness, webhook_service_status, webhook_support,
)
from codex_wake.webhook_listener import run_listener
from codex_wake.webhook_listener import build_webhook_runtime
from codex_wake.cli import main as cli_main
from codex_wake.github_polling import GitHubPollingAdapter
from codex_wake.github_source_config import GitHubSourceStore
from codex_wake.signal_records import signal_journal_path
from codex_wake.signals import ArmContext, WakeId
from tests.test_github_polling import NOW, FixtureClient, config as github_config, run
from tests.test_github_webhook_runtime import SECRET, exchange, signed_body
from tests.test_signal_store import make_module
from tests.test_signals import make_intent


class WebhookListenerConfigTests(unittest.TestCase):
    def test_product_builder_joins_configured_source_to_existing_journal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "wake"
            source = github_config(evidence_mode="positive_only")
            GitHubSourceStore(root).configure(source)
            module = make_module(signal_journal_path(root))
            adapter = GitHubPollingAdapter(source, FixtureClient([]))
            spec = adapter.request(ref="refs/heads/main", conclusions=("success",))
            module.arm(
                WakeId("product-builder"),
                spec,
                ArmContext(
                    "product-builder",
                    "product-builder",
                    NOW,
                    None,
                    make_intent().resume,
                    adapter,
                ),
            )
            with socket.socket() as reservation:
                reservation.bind(("127.0.0.1", 0))
                port = reservation.getsockname()[1]
            listener = WebhookListenerConfig(
                source.source_instance,
                port=port,
                secret_ref="CODEX_WAKE_WEBHOOK_SECRET",
                enabled=True,
            )
            WebhookListenerStore(root).configure(listener)
            runtime = build_webhook_runtime(
                wake_root=root,
                listener=listener,
                environment={
                    "CODEX_WAKE_WEBHOOK_SECRET": SECRET.decode(),
                    source.credential_ref: "fixture-provider-token",
                },
                attempt_client_factory=lambda deadline: FixtureClient([
                    replace(
                        run(),
                        completed_at=None,
                        terminal_proof_at=run().completed_at,
                        time_provenance="github_attempt_started_or_job_completed_lower_bound",
                    )
                ]),
                now=lambda: NOW + timedelta(seconds=2),
            )
            body, signature = signed_body()
            result = []

            def deliver() -> None:
                result.append(exchange(runtime.address, body, signature))
                runtime.shutdown()

            client = threading.Thread(target=deliver)
            client.start()
            runtime.serve()
            client.join(2)
            self.assertFalse(client.is_alive())
            self.assertEqual(result, [(200, "COMMITTED")])
            self.assertIsNotNone(module.source_checkpoint("github", source.source_instance))

    def test_real_socket_revokes_listener_and_github_source_before_ingest(self) -> None:
        for revoke in ("listener", "source"):
            with self.subTest(revoke=revoke), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp) / "wake"
                source = github_config(evidence_mode="positive_only")
                GitHubSourceStore(root).configure(source)
                make_module(signal_journal_path(root))
                with socket.socket() as reservation:
                    reservation.bind(("127.0.0.1", 0))
                    port = reservation.getsockname()[1]
                listener = WebhookListenerConfig(source.source_instance, port=port, secret_ref="CODEX_WAKE_WEBHOOK_SECRET", enabled=True)
                WebhookListenerStore(root).configure(listener)
                runtime = build_webhook_runtime(
                    wake_root=root, listener=listener,
                    environment={"CODEX_WAKE_WEBHOOK_SECRET": SECRET.decode(), source.credential_ref: "fixture-provider-token"},
                )
                if revoke == "listener":
                    WebhookListenerStore(root).configure(replace(listener, enabled=False))
                else:
                    GitHubSourceStore(root).configure(replace(source, enabled=False))
                body, signature = signed_body()
                result = []
                client = threading.Thread(target=lambda: (result.append(exchange(runtime.address, body, signature)), runtime.shutdown()))
                client.start()
                runtime.serve()
                client.join(2)
                self.assertEqual(result, [(503, "SECRET_UNAVAILABLE")])

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

    def test_provider_store_operation_budget_is_explicit_and_nested(self) -> None:
        with self.assertRaisesRegex(ValueError, "configuration is invalid"):
            WebhookListenerConfig(
                "github-webhook",
                secret_ref="CODEX_WAKE_WEBHOOK_SECRET",
                operation_timeout_seconds=11,
                shutdown_timeout_seconds=10,
            )
        with self.assertRaisesRegex(ValueError, "configuration is invalid"):
            WebhookListenerConfig(
                "github-webhook",
                secret_ref="CODEX_WAKE_WEBHOOK_SECRET",
                max_body_bytes=1023,
            )
        configured = WebhookListenerConfig(
            "github-webhook",
            secret_ref="CODEX_WAKE_WEBHOOK_SECRET",
            operation_timeout_seconds=3,
        )
        self.assertEqual(configured.operation_timeout_seconds, 3)

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
        self.assertIn("EnvironmentFile=/tmp/wake/github/webhook.env", rendered)
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
                self.active = "active"
                self.enabled = "enabled"
            def run(self, args, *, check=True):
                self.calls.append((args, check))
                if "disable" in args:
                    self.active, self.enabled = "inactive", "disabled"
                output = self.active + "\n" if "is-active" in args else self.enabled + "\n" if "is-enabled" in args else ""
                return subprocess.CompletedProcess(args, 0, output, "")
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            config = WebhookServiceConfig(
                "codex-wake-github-webhook-github-webhook.service", base / "wake", "github-webhook",
                base / "bin" / "codex-wake-github-webhook", base / "unit" / "listener.service", base / "log",
            )
            environment_file = config.wake_root / "github" / "webhook.env"
            environment_file.parent.mkdir(parents=True)
            environment_file.write_text("CODEX_WAKE_WEBHOOK_SECRET=fixture-only\n", encoding="utf-8")
            environment_file.chmod(0o600)
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

    def test_install_requires_owner_only_secret_environment_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            config = WebhookServiceConfig(
                "listener.service",
                base / "wake",
                "github-webhook",
                base / "bin" / "codex-wake-github-webhook",
                base / "listener.service",
                base / "listener.log",
            )
            with self.assertRaisesRegex(Exception, "secret environment file"):
                install_webhook_service(config, start=False)
            environment_file = config.wake_root / "github" / "webhook.env"
            environment_file.parent.mkdir(parents=True)
            environment_file.write_text("CODEX_WAKE_WEBHOOK_SECRET=fixture-only\n", encoding="utf-8")
            environment_file.chmod(0o644)
            with self.assertRaisesRegex(Exception, "secret environment file"):
                install_webhook_service(config, start=False)

    def test_disable_stops_active_owner_before_persisting(self) -> None:
        class Runner:
            def __init__(self) -> None:
                self.active = "activating"
                self.enabled = "enabled"
                self.calls = []
            def run(self, args, *, check=True):
                self.calls.append(args)
                if "disable" in args:
                    self.active = "inactive"
                    self.enabled = "disabled"
                output = self.active + "\n" if "is-active" in args else self.enabled + "\n"
                return subprocess.CompletedProcess(args, 0, output, "")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "wake"
            unit_dir = Path(tmp) / "units"
            store = WebhookListenerStore(root)
            enabled = WebhookListenerConfig("github-webhook", secret_ref="CODEX_WAKE_WEBHOOK_SECRET", enabled=True)
            store.configure(enabled)
            config = build_webhook_service_config(
                wake_root=root,
                source_instance=enabled.source_instance,
                unit_dir=unit_dir,
                validate_executable=False,
            )
            config.unit_path.parent.mkdir()
            config.unit_path.write_text(
                f"EnvironmentFile={root / 'github' / 'webhook.env'}\n"
                f'ExecStart="/usr/bin/codex-wake-github-webhook" --wake-root "{root}" --source {enabled.source_instance}\n'
                "Restart=on-failure\nTimeoutStopSec=15\n",
                encoding="utf-8",
            )
            config.unit_path.chmod(0o600)
            environment_file = root / "github" / "webhook.env"
            environment_file.write_text("CODEX_WAKE_WEBHOOK_SECRET=fixture-only\n", encoding="utf-8")
            environment_file.chmod(0o600)
            runner = Runner()
            disabled = disable_webhook_listener(
                store,
                replace(enabled, enabled=False),
                runner,
                unit_dir=unit_dir,
            )
            self.assertFalse(disabled.enabled)
            self.assertFalse(store.select("github-webhook").enabled)
            self.assertTrue(any("disable" in call for call in runner.calls))

    def test_uninstall_refuses_to_delete_a_foreign_unit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            config = WebhookServiceConfig(
                "listener.service",
                base / "wake",
                "github-webhook",
                None,
                base / "listener.service",
                base / "listener.log",
            )
            config.unit_path.write_text("foreign\n", encoding="utf-8")
            config.unit_path.chmod(0o600)
            with self.assertRaisesRegex(Exception, "ownership is invalid"):
                uninstall_webhook_service(config, runner=lambda *args, **kwargs: None)
            self.assertTrue(config.unit_path.exists())

    def test_stop_and_uninstall_preserve_unit_when_readback_is_not_inactive_disabled(self) -> None:
        class Runner:
            def run(self, args, *, check=True):
                return subprocess.CompletedProcess(args, 0, "active\n" if "is-active" in args else "enabled\n", "")
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            config = WebhookServiceConfig("listener.service", base / "wake", "github-webhook", None, base / "listener.service", base / "log")
            config.unit_path.write_text('EnvironmentFile=' + str(base / 'wake/github/webhook.env') + '\nExecStart="x" --wake-root "' + str(base / 'wake') + '" --source github-webhook\nRestart=on-failure\nTimeoutStopSec=15\n')
            config.unit_path.chmod(0o600)
            with self.assertRaisesRegex(Exception, "did not stop and disable"):
                uninstall_webhook_service(config, Runner())
            self.assertTrue(config.unit_path.exists())

    def test_custom_webhook_service_name_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "wake"
            WebhookListenerStore(root).configure(WebhookListenerConfig("github-webhook", secret_ref="CODEX_WAKE_WEBHOOK_SECRET", enabled=True))
            with self.assertRaisesRegex(Exception, "name is fixed"):
                build_webhook_service_config(wake_root=root, source_instance="github-webhook", name="other.service", validate_executable=False)

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
            GitHubSourceStore(root).configure(github_config(source_instance="github-webhook", evidence_mode="positive_only"))
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

    def test_readiness_fails_closed_for_missing_source_empty_environment_and_invalid_journal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "wake"
            listener = WebhookListenerConfig("github-webhook", secret_ref="CODEX_WAKE_WEBHOOK_SECRET", enabled=True)
            WebhookListenerStore(root).configure(listener)
            missing = webhook_readiness(wake_root=root, source_instance=listener.source_instance, runtime_available=True)
            self.assertEqual(missing["status"], "blocked")
            source = replace(github_config(source_instance="github-webhook", evidence_mode="positive_only"), credential_ref="CODEX_WAKE_GITHUB_TOKEN")
            GitHubSourceStore(root).configure(source)
            journal = signal_journal_path(root)
            journal.parent.mkdir(exist_ok=True)
            journal.write_text("not sqlite", encoding="utf-8")
            journal.chmod(0o600)
            self.assertFalse(_journal_is_safe(journal))

    def test_readonly_journal_validation_never_initializes_or_changes_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "wake"
            journal = signal_journal_path(root)
            make_module(journal)
            writer = sqlite3.connect(journal)
            writer.execute("PRAGMA journal_mode=WAL")
            writer.execute("UPDATE journal_meta SET migrated_at = migrated_at WHERE singleton = 1")
            writer.commit()
            before = {
                item.name: hashlib.sha256(item.read_bytes()).hexdigest()
                for item in journal.parent.glob("journal.sqlite3*")
            }
            self.assertTrue(_journal_is_safe(journal))
            after = {
                item.name: hashlib.sha256(item.read_bytes()).hexdigest()
                for item in journal.parent.glob("journal.sqlite3*")
            }
            self.assertEqual(after, before)
            writer.close()
            journal.write_bytes(b"")
            self.assertFalse(_journal_is_safe(journal))

    def test_secret_environment_rejects_quoted_empty_and_unsupported_syntax(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "wake"
            listener = WebhookListenerConfig("github-webhook", secret_ref="CODEX_WAKE_WEBHOOK_SECRET", enabled=True)
            source = github_config(source_instance="github-webhook", evidence_mode="positive_only")
            config = WebhookServiceConfig("listener.service", root, listener.source_instance, None, Path(tmp) / "unit", Path(tmp) / "log")
            env_path = root / "github" / "webhook.env"
            env_path.parent.mkdir(parents=True)
            for empty in ('""', "''"):
                env_path.write_text(f"CODEX_WAKE_WEBHOOK_SECRET={empty}\n{source.credential_ref}=token\n", encoding="utf-8")
                env_path.chmod(0o600)
                self.assertFalse(secret_environment_has_references(config, listener, source))
            env_path.write_text(f"CODEX_WAKE_WEBHOOK_SECRET=token\n{source.credential_ref}=token\nUNSUPPORTED LINE\n", encoding="utf-8")
            self.assertFalse(secret_environment_has_references(config, listener, source))

    def test_readiness_requires_restart_safe_secret_environment(self) -> None:
        class Runner:
            def run(self, args, *, check=True):
                output = "active\n" if "is-active" in args else "enabled\n"
                return subprocess.CompletedProcess(args, 0, output, "")

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = base / "wake"
            store = WebhookListenerStore(root)
            listener = WebhookListenerConfig(
                "github-webhook",
                secret_ref="CODEX_WAKE_WEBHOOK_SECRET",
                enabled=True,
            )
            store.configure(listener)
            source = replace(github_config(source_instance="github-webhook", evidence_mode="positive_only"), credential_ref="CODEX_WAKE_GITHUB_TOKEN")
            GitHubSourceStore(root).configure(source)
            environment_file = root / "github" / "webhook.env"
            environment_file.write_text(
                f"CODEX_WAKE_WEBHOOK_SECRET=fixture-only\n{source.credential_ref}=fixture-provider-token\n",
                encoding="utf-8",
            )
            environment_file.chmod(0o600)
            with patch.dict("os.environ", {"XDG_CONFIG_HOME": str(base / "config")}, clear=False):
                config = build_webhook_service_config(
                    wake_root=root,
                    source_instance=listener.source_instance,
                    validate_executable=False,
                )
                configured = replace(
                    config,
                    executable_path=Path("/usr/bin/codex-wake-github-webhook"),
                )
                config.unit_path.parent.mkdir(parents=True)
                config.unit_path.write_text(render_webhook_unit(configured), encoding="utf-8")
                config.unit_path.chmod(0o600)
                ready = webhook_readiness(
                    wake_root=root,
                    source_instance=listener.source_instance,
                    runner=Runner(),
                    runtime_available=True,
                    bind_probe=lambda address, port: True,
                    journal_probe=lambda path: True,
                )
                self.assertEqual(ready["status"], "ready")
                self.assertEqual(ready["secret_environment_access"], "safe")
                environment_file.chmod(0o644)
                blocked = webhook_readiness(
                    wake_root=root,
                    source_instance=listener.source_instance,
                    runner=Runner(),
                    runtime_available=True,
                    bind_probe=lambda address, port: True,
                    journal_probe=lambda path: True,
                )
                self.assertEqual(blocked["status"], "blocked")
                self.assertEqual(blocked["secret_environment_access"], "unsafe")

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
