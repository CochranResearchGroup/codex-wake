from __future__ import annotations

import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/webhook_live_github_qualification.py"
SPEC = importlib.util.spec_from_file_location("webhook_live_github_qualification", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
runner = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = runner
SPEC.loader.exec_module(runner)


def private_root(base: Path) -> Path:
    root = base / "p53-c6-live-github-test"
    root.mkdir(mode=0o700)
    os.chmod(root, 0o700)
    return root


def hook_response(hook_id: int = 456) -> dict:
    return {
        "id": hook_id, "active": True, "events": ["workflow_run"],
        "config": {"url": runner.CALLBACK_URL, "content_type": "json", "insecure_ssl": "0"},
    }


class LiveGitHubQualificationTests(unittest.TestCase):
    def test_frozen_identity_and_create_request_are_exact(self) -> None:
        identity = runner.frozen_identity()
        self.assertEqual(identity.github_host, "github.com")
        self.assertEqual(identity.actor, "ecochran76")
        self.assertEqual(identity.repository, "CochranResearchGroup/codex-wake")
        self.assertEqual(identity.repository_id, 1242753508)
        self.assertEqual(identity.workflow_id, 279450573)
        self.assertEqual(identity.callback_url, "https://codex-wake.ecochran.dyndns.org/github/webhook")
        self.assertEqual(identity.source_instance, "p53-c6-live-github")
        self.assertEqual(identity.listener, "127.0.0.1:8820")
        request = runner.build_provider_request("create", secret="very-private")
        self.assertEqual(request.method, "POST")
        self.assertEqual(request.path, "/repos/CochranResearchGroup/codex-wake/hooks")
        self.assertEqual(request.body["events"], ["workflow_run"])
        self.assertEqual(request.body["config"]["url"], identity.callback_url)
        self.assertEqual(request.body["config"]["content_type"], "json")
        self.assertEqual(request.body["config"]["insecure_ssl"], "0")
        self.assertTrue(request.body["active"])

    def test_provider_request_and_receipts_redact_secret_bytes(self) -> None:
        request = runner.build_provider_request("create", secret="very-private")
        sanitized = runner.sanitize_for_receipt({"request": request.body, "token": "very-private"}, secrets=("very-private",))
        rendered = json.dumps(sanitized, sort_keys=True)
        self.assertNotIn("very-private", rendered)
        self.assertEqual(sanitized["token"], "[redacted]")
        self.assertEqual(sanitized["request"]["config"]["secret"], "[redacted]")
        self.assertIn("request_sha256", runner.sanitized_request_summary(request, secrets=("very-private",)))

    def test_exact_hook_response_validation_is_pure_and_fail_closed(self) -> None:
        response = hook_response(987)
        observed = runner.validate_hook_response(response)
        self.assertEqual(observed["hook_id"], 987)
        response["config"]["url"] = "https://wrong.invalid/github/webhook"
        with self.assertRaisesRegex(RuntimeError, "hook response mismatch"):
            runner.validate_hook_response(response)

    def test_counters_are_separate_and_redelivery_dispatch_are_zero_only(self) -> None:
        state = runner.new_state(Path("/private/p53-c6-live-github-test"), Path("/receipt.json"))
        state = runner.record_attempt(state, "create")
        state = runner.record_provider_result(state, "create", response=hook_response())
        state = runner.record_attempt(state, "trigger")
        state = runner.record_attempt(state, "delete")
        self.assertEqual(state["counters"], {
            "create": 1, "trigger": 1, "delete": 1, "redelivery": 0, "dispatch": 0,
        })
        for forbidden in ("redelivery", "dispatch"):
            with self.subTest(action=forbidden):
                with self.assertRaisesRegex(RuntimeError, "forbidden"):
                    runner.record_attempt(state, forbidden)

    def test_ambiguous_write_fails_closed_without_retry(self) -> None:
        state = runner.new_state(Path("/private/p53-c6-live-github-test"), Path("/receipt.json"))
        state = runner.record_attempt(state, "create")
        uncertain = runner.record_provider_result(state, "create", response=None, ambiguous=True)
        self.assertEqual(uncertain["phase"], "provider_write_ambiguous")
        self.assertTrue(uncertain["requires_exact_readback"])
        with self.assertRaisesRegex(RuntimeError, "ambiguous"):
            runner.record_attempt(uncertain, "create")

    def test_receipt_is_staged_redacted_and_local_prepare_requires_exact_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = private_root(base)
            receipt = base / "receipt.json"
            result = runner.prepare_local(root, receipt)
            self.assertEqual(result["phase"], "prepared")
            rendered = receipt.read_text(encoding="utf-8")
            self.assertIn("p53-c6-live-github", rendered)
            self.assertIn(runner.SECRET_REF, rendered)
            self.assertNotIn('"secret":', rendered)
            self.assertEqual((root / runner.STATE_FILE).stat().st_mode & 0o777, 0o600)
            with self.assertRaisesRegex(RuntimeError, "exact private root"):
                runner.prepare_local(base / "wrong-root", receipt)

    def test_cleanup_interlock_preserves_root_until_exact_delete_readback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = private_root(base)
            receipt = base / "receipt.json"
            runner.prepare_local(root, receipt)
            state = runner.load_private_state(root)
            state = runner.record_attempt(state, "create")
            state = runner.record_provider_result(state, "create", response=hook_response())
            state = runner.record_attempt(state, "delete")
            runner.write_private_state(root, state)
            unsafe = runner.cleanup_local(root)
            self.assertFalse(unsafe["safe"])
            self.assertTrue(root.exists())
            state = runner.record_provider_result(
                state, "delete", response={"hook_id": 456, "absent": True},
            )
            runner.write_private_state(root, state)
            safe = runner.cleanup_local(root)
            self.assertTrue(safe["safe"])
            self.assertFalse(root.exists())

    def test_cli_defaults_to_read_only_preflight_and_effects_require_arm_and_root(self) -> None:
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            self.assertEqual(runner.main([]), 0)
            self.assertEqual(runner.main(["prepare"]), 2)
        self.assertIn("--execute", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
