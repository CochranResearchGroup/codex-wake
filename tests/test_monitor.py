from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from codex_wake.monitor import (
    health_is_recent,
    monitor_health_path,
    monitor_readiness,
    parse_unit_exec_start_wake_root,
    write_monitor_health,
)
from codex_wake.service import build_service_config, render_unit


class FakeRunner:
    def __init__(self, active: str = "active", enabled: str = "enabled", environment: str = "") -> None:
        self.active = active
        self.enabled = enabled
        self.environment = environment

    def run(self, args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
        stdout = ""
        if "is-active" in args:
            stdout = f"{self.active}\n"
        elif "is-enabled" in args:
            stdout = f"{self.enabled}\n"
        elif "show-environment" in args:
            stdout = self.environment
        return subprocess.CompletedProcess(args=args, returncode=0, stdout=stdout, stderr="")


class MonitorTests(unittest.TestCase):
    def make_executable(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("#!/bin/sh\n", encoding="utf-8")
        path.chmod(0o755)
        return path

    def test_active_matching_repo_service_is_monitor_ready(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            repo = base / "repo"
            wake_root = repo / ".codex" / "wake"
            daemon = self.make_executable(base / "bin" / "codex-waked")
            config = build_service_config(
                repo_root=repo,
                wake_root=wake_root,
                daemon_path=str(daemon),
                unit_dir=base / "config" / "systemd" / "user",
                log_path=base / "state" / "wake.log",
            )
            config.unit_path.parent.mkdir(parents=True)
            config.unit_path.write_text(render_unit(config), encoding="utf-8")

            with patch.dict("os.environ", {"XDG_CONFIG_HOME": str(base / "config"), "PATH": str(daemon.parent)}, clear=True):
                readiness = monitor_readiness(
                    wake_root=wake_root,
                    repo_root=repo,
                    daemon_path=str(daemon),
                    runner=FakeRunner(active="active", enabled="enabled"),
                )

            self.assertTrue(readiness["monitor_ready"])
            self.assertEqual(readiness["monitor_source"], "repo_service")
            self.assertEqual(readiness["service"]["wake_root"], str(wake_root.resolve()))
            self.assertTrue(readiness["service"]["matches_wake_root"])

    def test_inactive_matching_service_is_not_monitor_ready_without_health(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            repo = base / "repo"
            wake_root = repo / ".codex" / "wake"
            daemon = self.make_executable(base / "bin" / "codex-waked")
            config = build_service_config(
                repo_root=repo,
                wake_root=wake_root,
                daemon_path=str(daemon),
                unit_dir=base / "config" / "systemd" / "user",
                log_path=base / "state" / "wake.log",
            )
            config.unit_path.parent.mkdir(parents=True)
            config.unit_path.write_text(render_unit(config), encoding="utf-8")

            with patch.dict("os.environ", {"XDG_CONFIG_HOME": str(base / "config"), "PATH": str(daemon.parent)}, clear=True):
                readiness = monitor_readiness(
                    wake_root=wake_root,
                    repo_root=repo,
                    daemon_path=str(daemon),
                    runner=FakeRunner(active="inactive", enabled="disabled"),
                )

            self.assertFalse(readiness["monitor_ready"])
            self.assertEqual(readiness["service"]["active"], "inactive")
            self.assertTrue(readiness["service"]["matches_wake_root"])

    def test_wrong_root_service_is_not_monitor_ready(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            repo = base / "repo"
            wake_root = repo / ".codex" / "wake"
            other_root = base / "other" / ".codex" / "wake"
            daemon = self.make_executable(base / "bin" / "codex-waked")
            config = build_service_config(
                repo_root=repo,
                wake_root=other_root,
                daemon_path=str(daemon),
                unit_dir=base / "config" / "systemd" / "user",
                log_path=base / "state" / "wake.log",
            )
            config.unit_path.parent.mkdir(parents=True)
            config.unit_path.write_text(render_unit(config), encoding="utf-8")

            with patch.dict("os.environ", {"XDG_CONFIG_HOME": str(base / "config"), "PATH": str(daemon.parent)}, clear=True):
                readiness = monitor_readiness(
                    wake_root=wake_root,
                    repo_root=repo,
                    daemon_path=str(daemon),
                    runner=FakeRunner(active="active", enabled="enabled"),
                )

            self.assertFalse(readiness["monitor_ready"])
            self.assertEqual(readiness["service"]["wake_root"], str(other_root.resolve()))
            self.assertFalse(readiness["service"]["matches_wake_root"])

    def test_missing_unit_reports_missing_service_wake_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            repo = base / "repo"
            wake_root = repo / ".codex" / "wake"
            daemon = self.make_executable(base / "bin" / "codex-waked")

            with patch.dict("os.environ", {"XDG_CONFIG_HOME": str(base / "config"), "PATH": str(daemon.parent)}, clear=True):
                readiness = monitor_readiness(
                    wake_root=wake_root,
                    repo_root=repo,
                    daemon_path=str(daemon),
                    runner=FakeRunner(active="active", enabled="enabled"),
                )

            self.assertFalse(readiness["monitor_ready"])
            self.assertEqual(readiness["service"]["wake_root"], "")
            self.assertFalse(readiness["service"]["matches_wake_root"])

    def test_service_environment_readiness_is_reported_without_manager_path_leak(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            repo = base / "repo"
            wake_root = repo / ".codex" / "wake"
            daemon = self.make_executable(base / "bin" / "codex-waked")
            codex = self.make_executable(base / "interactive" / "codex")

            with patch.dict(
                "os.environ",
                {"XDG_CONFIG_HOME": str(base / "config"), "PATH": str(codex.parent)},
                clear=True,
            ):
                readiness = monitor_readiness(
                    wake_root=wake_root,
                    repo_root=repo,
                    daemon_path=str(daemon),
                    runner=FakeRunner(active="inactive", enabled="disabled", environment=""),
                )

            app_server = readiness["transports"]["app_server"]
            self.assertFalse(app_server["codex_cmd_ready"])
            self.assertEqual(app_server["codex_cmd_source"], "interactive_path_only")
            self.assertEqual(app_server["user_manager_codex_cmd"], "")

    def test_recent_loop_health_can_prove_monitor_ready(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            wake_root = base / "repo" / ".codex" / "wake"
            state_dir = base / "state" / "monitors"
            write_monitor_health(
                wake_root=wake_root,
                source="supervisor",
                mode="loop",
                poll_result={"checked": 0},
                state_dir=state_dir,
                now=datetime(2026, 5, 25, 20, 39, 30, tzinfo=UTC),
            )

            readiness = monitor_readiness(
                wake_root=wake_root,
                repo_root=base / "repo",
                daemon_path=str(self.make_executable(base / "bin" / "codex-waked")),
                runner=FakeRunner(active="inactive", enabled="disabled"),
                state_dir=state_dir,
                now=datetime(2026, 5, 25, 20, 39, 34, tzinfo=UTC),
            )

            self.assertTrue(readiness["monitor_ready"])
            self.assertEqual(readiness["monitor_source"], "supervisor")
            self.assertTrue(readiness["health"]["recent"])
            self.assertTrue(readiness["health"]["persistent"])
            self.assertTrue(monitor_health_path(wake_root, state_dir).exists())

    def test_stale_once_health_is_not_ready(self) -> None:
        health = {"mode": "once", "checked_at": "2026-05-25T20:00:00Z"}
        self.assertFalse(health_is_recent(health, now=datetime(2026, 5, 25, 20, 3, tzinfo=UTC)))

    def test_parse_unit_exec_start_wake_root_handles_quoted_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            unit = Path(tmp) / "wake.service"
            unit.write_text('ExecStart="/bin/codex-waked" --wake-root "/tmp/with space/wake" --interval 1\n', encoding="utf-8")
            self.assertEqual(parse_unit_exec_start_wake_root(unit), str(Path("/tmp/with space/wake").resolve()))


if __name__ == "__main__":
    unittest.main()
