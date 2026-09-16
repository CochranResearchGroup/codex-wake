from __future__ import annotations

import importlib.util
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "webhook_installed_smoke.py"
SPEC = importlib.util.spec_from_file_location("webhook_installed_smoke", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
smoke = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = smoke
SPEC.loader.exec_module(smoke)


class InstalledWebhookSmokeTests(unittest.TestCase):
    def test_default_refuses_without_creating_or_running_anything(self) -> None:
        stderr = io.StringIO()
        with patch.object(smoke, "execute", side_effect=AssertionError("must not execute")):
            with redirect_stderr(stderr):
                result = smoke.main([])
        self.assertEqual(result, 2)
        self.assertIn("refuses", stderr.getvalue())
        self.assertIn("--execute", stderr.getvalue())

    def test_receipt_redacts_secret_values_payloads_and_environment_text(self) -> None:
        receipt = smoke.sanitize_receipt(
            {
                "token": "provider-token-value",
                "nested": {"webhook_secret": "webhook-secret-value"},
                "payload": '{"private": "body"}',
                "environment_file": "CODEX_WAKE_WEBHOOK_SECRET=webhook-secret-value",
                "safe": "COMMITTED",
            },
            secrets=("provider-token-value", "webhook-secret-value"),
        )
        rendered = json.dumps(receipt, sort_keys=True)
        self.assertNotIn("provider-token-value", rendered)
        self.assertNotIn("webhook-secret-value", rendered)
        self.assertNotIn('"private"', rendered)
        self.assertEqual(receipt["safe"], "COMMITTED")
        self.assertEqual(receipt["payload"], "[redacted]")
        self.assertEqual(receipt["environment_file"], "[redacted]")

    def test_command_runner_uses_exact_argv_and_declared_timeout_bound(self) -> None:
        calls = []

        def fake_run(argv, **kwargs):
            calls.append((argv, kwargs))
            return smoke.subprocess.CompletedProcess(argv, 0, "{}", "")

        with tempfile.TemporaryDirectory() as tmp, patch.object(smoke.subprocess, "run", side_effect=fake_run):
            artifacts = Path(tmp) / "artifacts"
            result = smoke.run_command(
                ["/isolated/bin/codex-wake", "--wake-root", "/isolated/root", "status", "--json"],
                artifact_dir=artifacts,
                name="status",
                timeout=30,
            )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(calls[0][0], ["/isolated/bin/codex-wake", "--wake-root", "/isolated/root", "status", "--json"])
        self.assertFalse(calls[0][1].get("shell", False))
        self.assertEqual(calls[0][1]["timeout"], 30)
        with self.assertRaisesRegex(ValueError, "timeout"):
            smoke.run_command(["/isolated/bin/codex-wake", "status"], artifact_dir=Path("/tmp"), name="too-long", timeout=61)

    def test_cleanup_uninstalls_before_removing_temporary_state_and_reports_all_checks(self) -> None:
        calls = []
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            unit = base / "unit.service"
            root = base / "wake"
            fixture = base / "sitecustomize.py"
            for path in (unit, fixture):
                path.write_text("fixture", encoding="utf-8")
            root.mkdir()
            context = smoke.ExecutionContext(
                root=base,
                artifact_dir=base / "artifacts",
                wake_root=root,
                unit_path=unit,
                fixture_dir=base,
                installed_cli=base / "bin" / "codex-wake",
                installed_listener=base / "bin" / "codex-wake-github-webhook",
                service_name="codex-wake-github-webhook-p53-c4-installed-canary.service",
            )
            context.installed_cli.parent.mkdir()
            context.installed_cli.write_text("fixture", encoding="utf-8")

            def fake_command(argv, **kwargs):
                calls.append(argv)
                return smoke.subprocess.CompletedProcess(argv, 0, "inactive\n", "")

            with patch.object(smoke, "run_command", side_effect=fake_command), patch.object(smoke, "port_is_free", return_value=True), patch.object(smoke, "matching_processes", return_value=()):
                receipt = smoke.cleanup(context)

            self.assertFalse(unit.exists())
            self.assertFalse(root.exists())
            self.assertFalse(fixture.exists())
            self.assertEqual(calls[0][-5:], ["github-webhook", "service", "uninstall", "--source", smoke.SOURCE])
            self.assertTrue(receipt["unit_absent"])
            self.assertTrue(receipt["port_released"])
            self.assertTrue(receipt["temporary_roots_removed"])

    def test_cleanup_preserves_preexisting_unit_when_no_service_attempt_started(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            unit = base / "foreign.service"
            unit.write_text("foreign", encoding="utf-8")
            context = smoke.ExecutionContext(
                root=base,
                artifact_dir=base / "artifacts",
                wake_root=base / "wake",
                unit_path=unit,
                fixture_dir=base / "fixture",
                installed_cli=base / "missing-cli",
                installed_listener=base / "missing-listener",
                service_name="foreign.service",
            )
            with patch.object(smoke, "port_is_free", return_value=True), patch.object(smoke, "matching_processes", return_value=()):
                receipt = smoke.cleanup(context, service_attempted=False)
            self.assertTrue(unit.exists())
            self.assertFalse(receipt["service_uninstall_attempted"])

    def test_sitecustomize_is_ephemeral_provider_seam_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = smoke.write_sitecustomize(Path(tmp))
            source = path.read_text(encoding="utf-8")
        self.assertIn("build_webhook_runtime", source)
        self.assertIn("attempt_client_factory", source)
        self.assertNotIn("endpoint", source.lower())
        self.assertNotIn("token", source.lower())


if __name__ == "__main__":
    unittest.main()
