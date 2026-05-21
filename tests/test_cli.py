from __future__ import annotations

import contextlib
import io
import json
import os
import tempfile
import unittest
from datetime import UTC, datetime
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

    def test_schema_command_reports_version_and_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            code, out, err = self.run_cli(["schema"], root)
            self.assertEqual(code, 0, err)
            self.assertIn("schema_version=1", out)
            self.assertIn("compatibility=additive_optional_fields", out)
            self.assertIn("schema_doc=docs/dev/wake-record-schema.md", out)

            code, json_out, err = self.run_cli(["schema", "--json"], root)
            self.assertEqual(code, 0, err)
            data = json.loads(json_out)
            self.assertEqual(data["schema_version"], 1)
            self.assertIn("file_changed", data["predicate_types"])

    def test_app_status_reports_thread_status_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch(
                "codex_wake.cli.read_app_server_thread_status",
                return_value={
                    "thread_id": "thread_abc",
                    "status": {"type": "active", "activeFlags": ["waitingOnApproval"]},
                    "status_type": "active",
                    "active_flags": ["waitingOnApproval"],
                    "cwd": "/tmp/repo",
                    "sessionId": "session_123",
                },
            ):
                code, out, err = self.run_cli(["app", "status", "--json", "thread_abc"], root)

            self.assertEqual(code, 0, err)
            data = json.loads(out)
            self.assertEqual(data["thread_id"], "thread_abc")
            self.assertEqual(data["status_type"], "active")
            self.assertEqual(data["active_flags"], ["waitingOnApproval"])

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

    def test_status_command_reports_counts_and_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            code, out, err = self.run_cli(["after", "45m", "--", "Continue later"], root)
            self.assertEqual(code, 0, err)
            wake_id = out.split()[0]
            code, _, err = self.run_cli(["cancel", wake_id], root)
            self.assertEqual(code, 0, err)
            code, _, err = self.run_cli(["archive", wake_id], root)
            self.assertEqual(code, 0, err)
            code, _, err = self.run_cli(["file", ".codex/events/done", "--", "Check event"], root)
            self.assertEqual(code, 0, err)

            code, text_out, err = self.run_cli(["status"], root)
            self.assertEqual(code, 0, err)
            self.assertIn("total=2", text_out)
            self.assertIn("active_total=1", text_out)
            self.assertIn("archived_total=1", text_out)
            self.assertIn("counts_by_status=", text_out)

            code, json_out, err = self.run_cli(["status", "--json"], root)
            self.assertEqual(code, 0, err)
            data = json.loads(json_out)
            self.assertEqual(data["total"], 2)
            self.assertEqual(data["active_total"], 1)
            self.assertEqual(data["archived_total"], 1)
            self.assertEqual(data["counts_by_status"]["pending"], 1)
            self.assertEqual(data["counts_by_status"]["archived"], 1)
            self.assertEqual(data["counts_by_predicate"]["file_exists"], 1)
            self.assertEqual(data["counts_by_target_transport"]["tmux"], 2)
            self.assertTrue(data["earliest_next_attempt_at"])

    def test_cleanup_dry_run_and_delete_archived_records(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            code, out, err = self.run_cli(["after", "1m", "--", "Cleanup later"], root)
            self.assertEqual(code, 0, err)
            wake_id = out.split()[0]
            code, _, err = self.run_cli(["cancel", wake_id], root)
            self.assertEqual(code, 0, err)
            code, _, err = self.run_cli(["archive", wake_id], root)
            self.assertEqual(code, 0, err)
            archived_path = root / "archive" / f"{wake_id}.json"
            data = json.loads(archived_path.read_text())
            data["archived_at"] = "2026-05-01T00:00:00Z"
            data["updated_at"] = "2026-05-01T00:00:00Z"
            archived_path.write_text(json.dumps(data), encoding="utf-8")

            with patch("codex_wake.records.utc_now", return_value=datetime(2026, 5, 19, tzinfo=UTC)):
                code, dry_run, err = self.run_cli(["cleanup", "--older-than", "7d"], root)
            self.assertEqual(code, 0, err)
            self.assertIn("would-delete", dry_run)
            self.assertTrue(archived_path.exists())

            with patch("codex_wake.records.utc_now", return_value=datetime(2026, 5, 19, tzinfo=UTC)):
                code, deleted, err = self.run_cli(["cleanup", "--older-than", "7d", "--delete"], root)
            self.assertEqual(code, 0, err)
            self.assertIn("deleted", deleted)
            self.assertFalse(archived_path.exists())

    def test_cleanup_json_reports_archive_and_delete_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            code, out, err = self.run_cli(["after", "1m", "--", "Cleanup json"], root)
            self.assertEqual(code, 0, err)
            wake_id = out.split()[0]
            code, _, err = self.run_cli(["cancel", wake_id], root)
            self.assertEqual(code, 0, err)

            code, archive_json, err = self.run_cli(["cleanup", "--archive-terminal", "--older-than", "30d", "--json"], root)
            self.assertEqual(code, 0, err)
            archive_data = json.loads(archive_json)
            self.assertEqual(archive_data["mode"], "dry-run")
            self.assertTrue(archive_data["archive_terminal"])
            self.assertEqual(archive_data["archived_terminal_count"], 1)
            self.assertEqual(archive_data["archived_terminal"][0]["wake_id"], wake_id)
            archived_path = root / "archive" / f"{wake_id}.json"
            record = json.loads(archived_path.read_text())
            record["archived_at"] = "2026-05-01T00:00:00Z"
            record["updated_at"] = "2026-05-01T00:00:00Z"
            archived_path.write_text(json.dumps(record), encoding="utf-8")

            with patch("codex_wake.records.utc_now", return_value=datetime(2026, 5, 19, tzinfo=UTC)):
                code, delete_json, err = self.run_cli(["cleanup", "--older-than", "7d", "--delete", "--json"], root)
            self.assertEqual(code, 0, err)
            delete_data = json.loads(delete_json)
            self.assertEqual(delete_data["mode"], "delete")
            self.assertEqual(delete_data["matched_count"], 1)
            self.assertEqual(delete_data["matched"][0]["wake_id"], wake_id)
            self.assertTrue(delete_data["matched"][0]["deleted"])
            self.assertFalse(archived_path.exists())

    def test_cleanup_can_archive_terminal_records_first(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            code, out, err = self.run_cli(["after", "1m", "--", "Cleanup later"], root)
            self.assertEqual(code, 0, err)
            wake_id = out.split()[0]
            code, _, err = self.run_cli(["cancel", wake_id], root)
            self.assertEqual(code, 0, err)

            code, cleanup_out, err = self.run_cli(["cleanup", "--archive-terminal", "--older-than", "1d"], root)

            self.assertEqual(code, 0, err)
            self.assertIn(f"archived {wake_id}", cleanup_out)
            self.assertTrue((root / "archive" / f"{wake_id}.json").exists())
            self.assertFalse((root / "cancelled" / f"{wake_id}.json").exists())

    def test_changed_creates_file_changed_predicate_with_baseline(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            watched = repo / "watched.log"
            watched.write_text("before", encoding="utf-8")
            root = repo / ".codex" / "wake"
            cwd = Path.cwd()
            try:
                os.chdir(repo)
                code, out, err = self.run_cli(["changed", "watched.log", "--", "Read changed log"], root)
            finally:
                os.chdir(cwd)

            self.assertEqual(code, 0, err)
            wake_id = out.split()[0]
            data = json.loads((root / "pending" / f"{wake_id}.json").read_text())
            self.assertEqual(data["predicate"]["type"], "file_changed")
            self.assertEqual(data["predicate"]["path"], "watched.log")
            self.assertTrue(data["predicate"]["registered_exists"])
            self.assertIsInstance(data["predicate"]["registered_mtime_ns"], int)
            self.assertEqual(data["predicate"]["registered_size"], len("before"))

    def test_changed_allows_missing_file_creation_watch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            root = repo / ".codex" / "wake"
            cwd = Path.cwd()
            try:
                os.chdir(repo)
                code, out, err = self.run_cli(["changed", "missing.log", "--", "Read created log"], root)
            finally:
                os.chdir(cwd)

            self.assertEqual(code, 0, err)
            wake_id = out.split()[0]
            data = json.loads((root / "pending" / f"{wake_id}.json").read_text())
            self.assertEqual(data["predicate"]["type"], "file_changed")
            self.assertFalse(data["predicate"]["registered_exists"])
            self.assertIsNone(data["predicate"]["registered_mtime_ns"])
            self.assertIsNone(data["predicate"]["registered_size"])

    def test_pid_creates_process_done_predicate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch("codex_wake.cli.process_identity", return_value={"start_time_ticks": 12345, "boot_id": "boot-abc"}):
                code, out, err = self.run_cli(["pid", str(os.getpid()), "--", "Process done"], root)

            self.assertEqual(code, 0, err)
            wake_id = out.split()[0]
            data = json.loads((root / "pending" / f"{wake_id}.json").read_text())
            self.assertEqual(
                data["predicate"],
                {
                    "type": "process_done",
                    "pid": os.getpid(),
                    "registered_start_time_ticks": 12345,
                    "registered_boot_id": "boot-abc",
                },
            )

    def test_pid_keeps_liveness_fallback_when_identity_unavailable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch("codex_wake.cli.process_identity", return_value=None):
                code, out, err = self.run_cli(["pid", str(os.getpid()), "--", "Process done"], root)

            self.assertEqual(code, 0, err)
            wake_id = out.split()[0]
            data = json.loads((root / "pending" / f"{wake_id}.json").read_text())
            self.assertEqual(data["predicate"], {"type": "process_done", "pid": os.getpid()})

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

    def test_app_after_creates_app_server_target_without_tmux(self) -> None:
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
                            "app",
                            "after",
                            "thread_abc",
                            "1m",
                            "--",
                            "Wake app server",
                        ]
                    )

            self.assertEqual(code, 0, stderr.getvalue())
            wake_id = stdout.getvalue().split()[0]
            data = json.loads((root / "pending" / f"{wake_id}.json").read_text())
            self.assertEqual(data["predicate"]["type"], "not_before")
            self.assertEqual(data["target"], {"transport": "app-server", "endpoint": "stdio://", "thread_id": "thread_abc"})

    def test_app_rejects_non_stdio_endpoint(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                code = cli.main(
                    [
                        "--wake-root",
                            str(root),
                            "app",
                            "after",
                            "--endpoint",
                            "ws://127.0.0.1:4500",
                            "thread_abc",
                            "1m",
                            "--",
                            "Wake app server",
                    ]
                )

            self.assertEqual(code, 2)
            self.assertIn("only app-server endpoint stdio://", stderr.getvalue())

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
            self.assertIn("hook_ack_count=0", stdout.getvalue())
            self.assertIn("hook_active_session_loaded=unknown_without_ack", stdout.getvalue())

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
            self.assertIn("hook_active_session_loaded=unknown_without_ack", output)
            self.assertIn("service_active=inactive", output)
            self.assertIn("restart or resume", output)

    def test_doctor_json_reports_readiness_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            root = repo / ".codex" / "wake"
            ack_dir = root / "acks"
            ack_dir.mkdir(parents=True)
            (ack_dir / "wake_seen.submitted").write_text(
                json.dumps(
                    {
                        "wake_id": "wake_seen",
                        "submitted_at": "2026-05-20T03:30:00Z",
                        "session_id": "session_seen",
                    }
                ),
                encoding="utf-8",
            )
            stdout = io.StringIO()
            stderr = io.StringIO()
            with patch("codex_wake.cli.service_status", return_value=("active", "enabled")):
                with patch("codex_wake.cli.shutil.which", side_effect=lambda name: f"/usr/bin/{name}"):
                    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                        code = cli.main(["--wake-root", str(root), "doctor", "--repo-root", str(repo), "--json"])

            self.assertEqual(code, 0, stderr.getvalue())
            data = json.loads(stdout.getvalue())
            self.assertEqual(data["repo_root"], str(repo))
            self.assertEqual(data["wake_root"], str(root))
            self.assertEqual(data["commands"]["codex_waked"], "/usr/bin/codex-waked")
            self.assertEqual(data["commands"]["tmux"], "/usr/bin/tmux")
            self.assertFalse(data["hook_config"]["installed"])
            self.assertEqual(data["hook_runtime"]["ack_count"], 1)
            self.assertEqual(data["hook_runtime"]["active_session_loaded"], "observed_ack")
            self.assertEqual(data["hook_runtime"]["latest_ack_wake_id"], "wake_seen")
            self.assertEqual(data["service"]["active"], "active")
            self.assertIn("restart or resume", data["trust"])

    def test_hook_check_reports_latest_ack_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            root = repo / ".codex" / "wake"
            ack_dir = root / "acks"
            ack_dir.mkdir(parents=True)
            (ack_dir / "wake_seen.submitted").write_text(
                json.dumps(
                    {
                        "wake_id": "wake_seen",
                        "submitted_at": "2026-05-18T21:30:00Z",
                        "session_id": "session_seen",
                    }
                ),
                encoding="utf-8",
            )
            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                code = cli.main(["--wake-root", str(root), "hook", "install", "--repo-root", str(repo)])
            self.assertEqual(code, 0, stderr.getvalue())

            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                code = cli.main(["--wake-root", str(root), "hook", "check", "--repo-root", str(repo)])

            self.assertEqual(code, 0, stderr.getvalue())
            output = stdout.getvalue()
            self.assertIn("hook_ack_count=1", output)
            self.assertIn("hook_active_session_loaded=observed_ack", output)
            self.assertIn("hook_latest_ack_wake_id=wake_seen", output)
            self.assertIn("hook_latest_ack_session_id=session_seen", output)


if __name__ == "__main__":
    unittest.main()
