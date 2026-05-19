from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from codex_wake.hook_config import check_hook_config, contains_hook_command, install_hook_config


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


if __name__ == "__main__":
    unittest.main()
