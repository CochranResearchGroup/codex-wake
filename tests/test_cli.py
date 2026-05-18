from __future__ import annotations

import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from codex_wake import cli


class CliTests(unittest.TestCase):
    def run_cli(self, argv: list[str], root: Path) -> tuple[int, str, str]:
        env = {
            **os.environ,
            "TMUX_PANE": "%11",
            "TMUX": "/tmp/tmux-1000/default,123,0",
        }
        stdout = io.StringIO()
        stderr = io.StringIO()
        with patch.dict(os.environ, env, clear=False):
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                code = cli.main(["--wake-root", str(root), *argv])
        return code, stdout.getvalue(), stderr.getvalue()

    def test_after_creates_pending_wake(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            code, out, err = self.run_cli(["after", "45m", "--", "Continue later"], root)
            self.assertEqual(code, 0, err)
            wake_id = out.split()[0]
            record_path = root / "pending" / f"{wake_id}.json"
            data = json.loads(record_path.read_text())
            self.assertEqual(data["predicate"]["type"], "not_before")
            self.assertEqual(data["target"]["pane"], "%11")
            self.assertEqual(data["prompt"], "Continue later")
            self.assertEqual(data["status"], "pending")

    def test_file_show_list_and_cancel(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            code, out, err = self.run_cli(["file", ".codex/events/pytest.done", "--", "Read log"], root)
            self.assertEqual(code, 0, err)
            wake_id = out.split()[0]

            code, show_out, err = self.run_cli(["show", wake_id], root)
            self.assertEqual(code, 0, err)
            shown = json.loads(show_out)
            self.assertEqual(shown["predicate"], {"type": "file_exists", "path": ".codex/events/pytest.done"})

            code, list_out, err = self.run_cli(["list"], root)
            self.assertEqual(code, 0, err)
            self.assertIn(wake_id, list_out)
            self.assertIn("file_exists", list_out)

            code, cancel_out, err = self.run_cli(["cancel", wake_id], root)
            self.assertEqual(code, 0, err)
            self.assertIn("cancelled", cancel_out)
            self.assertTrue((root / "cancelled" / f"{wake_id}.json").exists())
            self.assertFalse((root / "pending" / f"{wake_id}.json").exists())

    def test_create_requires_tmux_environment(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stdout = io.StringIO()
            stderr = io.StringIO()
            with patch.dict(os.environ, {"TMUX_PANE": "", "TMUX": ""}, clear=False):
                with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                    code = cli.main(["--wake-root", str(root), "after", "1m", "--", "Wake"])
            self.assertEqual(code, 2)
            self.assertIn("TMUX_PANE is required", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
