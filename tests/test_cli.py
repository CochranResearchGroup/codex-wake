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

            code, archive_out, err = self.run_cli(["archive", wake_id], root)
            self.assertEqual(code, 0, err)
            self.assertIn("archived", archive_out)
            self.assertTrue((root / "archive" / f"{wake_id}.json").exists())

            code, archived_list, err = self.run_cli(["list", "--archived"], root)
            self.assertEqual(code, 0, err)
            self.assertIn(wake_id, archived_list)

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

    def test_app_server_thread_target_does_not_require_tmux(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stdout = io.StringIO()
            stderr = io.StringIO()
            with patch.dict(os.environ, {"TMUX_PANE": "", "TMUX": ""}, clear=False):
                with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                    code = cli.main(
                        [
                            "--wake-root",
                            str(root),
                            "after",
                            "--app-server-thread-id",
                            "thread_abc",
                            "1m",
                            "--",
                            "Wake app server",
                        ]
                    )
            self.assertEqual(code, 0, stderr.getvalue())
            wake_id = stdout.getvalue().split()[0]
            data = json.loads((root / "pending" / f"{wake_id}.json").read_text())
            self.assertEqual(data["target"], {"transport": "app-server", "endpoint": "stdio://", "thread_id": "thread_abc"})

    def test_app_server_rejects_non_stdio_endpoint(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                code = cli.main(
                    [
                        "--wake-root",
                        str(root),
                        "after",
                        "--app-server-thread-id",
                        "thread_abc",
                        "--app-server-endpoint",
                        "ws://127.0.0.1:4500",
                        "1m",
                        "--",
                        "Wake app server",
                    ]
                )
            self.assertEqual(code, 2)
            self.assertIn("only app-server endpoint stdio://", stderr.getvalue())

    def test_service_status_command_prints_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "wake"
            unit_path = Path(tmp) / "unit.service"
            log_path = Path(tmp) / "service.log"
            stdout = io.StringIO()
            stderr = io.StringIO()
            with patch("codex_wake.cli.service_status", return_value=("inactive", "disabled")):
                with patch("codex_wake.cli.build_service_config") as build_config:
                    build_config.return_value = type(
                        "Config",
                        (),
                        {
                            "name": "wake-test.service",
                            "unit_path": unit_path,
                            "log_path": log_path,
                        },
                    )()
                    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                        code = cli.main(["--wake-root", str(root), "service", "status"])

            self.assertEqual(code, 0, stderr.getvalue())
            self.assertIn("name=wake-test.service", stdout.getvalue())
            self.assertIn(f"unit={unit_path}", stdout.getvalue())

    def test_hook_install_and_check_commands(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            root = repo / ".codex" / "wake"
            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                code = cli.main(["--wake-root", str(root), "hook", "install", "--repo-root", str(repo)])
            self.assertEqual(code, 0, stderr.getvalue())
            self.assertIn("installed hook config", stdout.getvalue())

            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                code = cli.main(["--wake-root", str(root), "hook", "check", "--repo-root", str(repo)])
            self.assertEqual(code, 0, stderr.getvalue())
            self.assertIn("installed=true", stdout.getvalue())
            self.assertIn("/hooks review", stdout.getvalue())
            self.assertIn("does not list", stdout.getvalue())

    def test_doctor_reports_readiness_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            root = repo / ".codex" / "wake"
            stdout = io.StringIO()
            stderr = io.StringIO()
            with patch("codex_wake.cli.service_status", return_value=("inactive", "disabled")):
                with patch("codex_wake.cli.shutil.which", side_effect=lambda name: f"/usr/bin/{name}"):
                    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                        code = cli.main(["--wake-root", str(root), "doctor", "--repo-root", str(repo)])
            self.assertEqual(code, 0, stderr.getvalue())
            output = stdout.getvalue()
            self.assertIn(f"repo_root={repo}", output)
            self.assertIn(f"wake_root={root}", output)
            self.assertIn("codex_waked=/usr/bin/codex-waked", output)
            self.assertIn("hook_config_installed=false", output)
            self.assertIn("service_active=inactive", output)
            self.assertIn("restart or resume", output)


if __name__ == "__main__":
    unittest.main()
