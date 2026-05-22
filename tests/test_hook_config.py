from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from codex_wake.hook_config import (
    check_hook_config,
    check_hook_sources,
    check_user_hook_config,
    contains_hook_command,
    hook_entry,
    hook_review_note,
    hook_runtime_evidence,
    install_hook_config,
    install_user_hook_config,
)


class HookConfigTests(unittest.TestCase):
    def test_install_hook_config_creates_expected_user_prompt_submit_hook(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)

            path = install_hook_config(repo)

            self.assertEqual(path, repo / ".codex" / "hooks.json")
            data = json.loads(path.read_text())
            self.assertTrue(contains_hook_command(data, "codex-wake-hook"))
            check = check_hook_config(repo)
            self.assertTrue(check.exists)
            self.assertTrue(check.valid_json)
            self.assertTrue(check.installed)

    def test_install_hook_config_preserves_existing_hooks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            path = repo / ".codex" / "hooks.json"
            path.parent.mkdir()
            path.write_text(
                json.dumps({"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "echo stop"}]}]}}),
                encoding="utf-8",
            )

            install_hook_config(repo)

            data = json.loads(path.read_text())
            self.assertIn("Stop", data["hooks"])
            self.assertTrue(contains_hook_command(data, "codex-wake-hook"))

    def test_check_hook_config_reports_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            check = check_hook_config(Path(tmp))

            self.assertFalse(check.exists)
            self.assertFalse(check.valid_json)
            self.assertFalse(check.installed)
            self.assertEqual(check.message, "missing")

    def test_hook_review_note_names_missing_hooks_list_case(self) -> None:
        note = hook_review_note()

        self.assertIn("/hooks", note)
        self.assertIn("does not list", note)
        self.assertIn("restart or resume", note)

    def test_check_hook_sources_detects_project_user_overlap(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            repo = base / "repo"
            codex_home = base / "codex-home"
            repo.mkdir()
            install_hook_config(repo)
            user_hook = codex_home / "hooks.json"
            user_hook.parent.mkdir()
            user_hook.write_text(
                json.dumps({"hooks": {"UserPromptSubmit": [{"hooks": [hook_entry("codex-wake-hook")]}]}}),
                encoding="utf-8",
            )

            sources = check_hook_sources(repo, codex_home=codex_home)

            self.assertTrue(sources.project.installed)
            self.assertTrue(sources.user.installed)
            self.assertEqual(sources.installed_scopes, ("project", "user"))
            self.assertTrue(sources.duplicate_installed)
            self.assertIn("duplicate wake context", sources.overlap_warning)

    def test_check_hook_sources_reports_user_only_install(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            repo = base / "repo"
            codex_home = base / "codex-home"
            repo.mkdir()
            user_hook = codex_home / "hooks.json"
            user_hook.parent.mkdir()
            user_hook.write_text(
                json.dumps({"hooks": {"UserPromptSubmit": [{"hooks": [hook_entry("codex-wake-hook")]}]}}),
                encoding="utf-8",
            )

            sources = check_hook_sources(repo, codex_home=codex_home)

            self.assertFalse(sources.project.installed)
            self.assertTrue(sources.user.installed)
            self.assertEqual(sources.installed_scopes, ("user",))
            self.assertFalse(sources.duplicate_installed)
            self.assertEqual(sources.overlap_warning, "")

    def test_install_user_hook_config_uses_codex_home(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            codex_home = Path(tmp) / "codex-home"

            path = install_user_hook_config(codex_home)
            check = check_user_hook_config(codex_home)

            self.assertEqual(path, codex_home / "hooks.json")
            self.assertTrue(path.exists())
            self.assertEqual(check.scope, "user")
            self.assertTrue(check.installed)
            self.assertEqual(check.path, path)

    def test_hook_runtime_evidence_reports_unknown_without_ack(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            evidence = hook_runtime_evidence(Path(tmp) / ".codex" / "wake")

            self.assertEqual(evidence.ack_count, 0)
            self.assertEqual(evidence.active_session_loaded, "unknown_without_ack")
            self.assertIsNone(evidence.latest_ack_path)

    def test_hook_runtime_evidence_reports_latest_ack(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            wake_root = Path(tmp) / ".codex" / "wake"
            ack_dir = wake_root / "acks"
            ack_dir.mkdir(parents=True)
            (ack_dir / "wake_old.submitted").write_text(
                json.dumps(
                    {
                        "wake_id": "wake_old",
                        "submitted_at": "2026-05-18T20:30:00Z",
                        "session_id": "session_old",
                    }
                ),
                encoding="utf-8",
            )
            latest = ack_dir / "wake_new.submitted"
            latest.write_text(
                json.dumps(
                    {
                        "wake_id": "wake_new",
                        "submitted_at": "2026-05-18T21:30:00Z",
                        "session_id": "session_new",
                    }
                ),
                encoding="utf-8",
            )

            evidence = hook_runtime_evidence(wake_root)

            self.assertEqual(evidence.ack_count, 2)
            self.assertEqual(evidence.active_session_loaded, "observed_ack")
            self.assertEqual(evidence.latest_ack_path, latest)
            self.assertEqual(evidence.latest_ack_wake_id, "wake_new")
            self.assertEqual(evidence.latest_ack_session_id, "session_new")


if __name__ == "__main__":
    unittest.main()
