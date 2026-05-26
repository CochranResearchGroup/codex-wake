from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from codex_wake.monitor import write_monitor_health
from codex_wake.records import build_record, write_record
from codex_wake.supervisor import (
    build_supervisor_config,
    enroll_root,
    install_supervisor,
    iter_registry_entries,
    render_supervisor_unit,
    supervisor_poll_once,
    supervisor_status,
    uninstall_supervisor,
    unenroll_root,
)


class FakeRunner:
    def __init__(self, active: str = "active", enabled: str = "enabled") -> None:
        self.active = active
        self.enabled = enabled
        self.calls: list[list[str]] = []

    def run(self, args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
        self.calls.append(args)
        stdout = ""
        if "is-active" in args:
            stdout = f"{self.active}\n"
        if "is-enabled" in args:
            stdout = f"{self.enabled}\n"
        return subprocess.CompletedProcess(args=args, returncode=0, stdout=stdout, stderr="")


class SupervisorTests(unittest.TestCase):
    def make_executable(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("#!/bin/sh\n", encoding="utf-8")
        path.chmod(0o755)
        return path

    def test_enroll_and_unenroll_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            registry = base / "config" / "roots.d"
            wake_root = base / "repo" / ".codex" / "wake"
            path = enroll_root(wake_root=wake_root, repo_root=base / "repo", registry_dir=registry, root_id="repo-test")

            data = json.loads(path.read_text())
            self.assertEqual(data["root_id"], "repo-test")
            self.assertEqual(data["wake_root"], str(wake_root.resolve()))
            self.assertTrue(data["enabled"])
            self.assertEqual(len(iter_registry_entries(registry)), 1)

            removed = unenroll_root(root_id="repo-test", registry_dir=registry)
            self.assertEqual(removed, path)
            self.assertFalse(path.exists())

    def test_render_and_install_supervisor_unit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            codex_wake = self.make_executable(base / "bin" / "codex-wake")
            config = build_supervisor_config(
                codex_wake_path=str(codex_wake),
                unit_dir=base / "systemd",
                log_path=base / "state" / "supervisor.log",
                registry_dir=base / "config" / "roots.d",
                state_dir=base / "state" / "supervisor",
            )
            unit = render_supervisor_unit(config)

            self.assertIn("codex-wake-supervisor.service", config.name)
            self.assertIn("supervisor run --interval 1", unit)
            self.assertIn("--registry-dir", unit)
            self.assertIn("--state-dir", unit)

            runner = FakeRunner()
            install_supervisor(config, runner)
            self.assertTrue(config.unit_path.exists())
            self.assertEqual(
                runner.calls,
                [
                    ["systemctl", "--user", "daemon-reload"],
                    ["systemctl", "--user", "enable", "--now", config.name],
                    ["systemctl", "--user", "is-active", config.name],
                ],
            )
            uninstall_supervisor(config, runner)
            self.assertFalse(config.unit_path.exists())

    def test_supervisor_status_lists_registered_roots(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            codex_wake = self.make_executable(base / "bin" / "codex-wake")
            config = build_supervisor_config(
                codex_wake_path=str(codex_wake),
                unit_dir=base / "systemd",
                log_path=base / "state" / "supervisor.log",
                registry_dir=base / "config" / "roots.d",
                state_dir=base / "state" / "supervisor",
            )
            wake_root = base / "repo" / ".codex" / "wake"
            enroll_root(wake_root=wake_root, repo_root=base / "repo", registry_dir=config.registry_dir, root_id="repo-test")

            status = supervisor_status(config, FakeRunner(active="inactive", enabled="disabled"))

            self.assertEqual(status["service"]["active"], "inactive")
            self.assertEqual(status["root_count"], 1)
            self.assertEqual(status["roots"][0]["root_id"], "repo-test")
            self.assertEqual(status["roots"][0]["wake_root"], str(wake_root.resolve()))
            self.assertEqual(status["roots"][0]["health_status"], "missing")
            self.assertIn("supervisor run --once", status["roots"][0]["remediation"])

    def test_supervisor_status_marks_stale_health_with_remediation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            codex_wake = self.make_executable(base / "bin" / "codex-wake")
            config = build_supervisor_config(
                codex_wake_path=str(codex_wake),
                unit_dir=base / "systemd",
                log_path=base / "state" / "supervisor.log",
                registry_dir=base / "config" / "roots.d",
                state_dir=base / "state" / "supervisor",
            )
            wake_root = base / "repo" / ".codex" / "wake"
            enroll_root(wake_root=wake_root, repo_root=base / "repo", registry_dir=config.registry_dir, root_id="repo-test")
            write_monitor_health(
                wake_root=wake_root,
                repo_root=base / "repo",
                source="supervisor",
                mode="loop",
                state_dir=config.state_dir.parent / "monitors",
                now=datetime.now(UTC) - timedelta(hours=1),
            )

            status = supervisor_status(config, FakeRunner(active="active", enabled="enabled"))

            root_status = status["roots"][0]
            self.assertFalse(root_status["health_recent"])
            self.assertEqual(root_status["health_status"], "stale")
            self.assertIn("codex-wake-supervisor.service", root_status["remediation"])
            self.assertIn("supervisor unenroll --root-id repo-test", root_status["remediation"])

    def test_supervisor_run_once_polls_registered_roots_and_writes_health(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            codex_wake = self.make_executable(base / "bin" / "codex-wake")
            config = build_supervisor_config(
                codex_wake_path=str(codex_wake),
                unit_dir=base / "systemd",
                log_path=base / "state" / "supervisor.log",
                registry_dir=base / "config" / "roots.d",
                state_dir=base / "state" / "supervisor",
            )
            repo = base / "repo"
            wake_root = repo / ".codex" / "wake"
            enroll_root(wake_root=wake_root, repo_root=repo, registry_dir=config.registry_dir, root_id="repo-test")
            record = build_record(
                predicate={"type": "not_before", "due_at": "2026-05-25T20:39:34Z"},
                prompt="Resume",
                cwd=repo,
                target={"transport": "tmux", "tmux_socket": "/tmp/tmux/default", "pane": "%1"},
            )
            record["id"] = "wake_supervisor"
            write_record(wake_root, record)

            with patch("codex_wake.supervisor.poll_once") as poll_once:
                poll_once.return_value = type(
                    "Result",
                    (),
                    {
                        "checked": 1,
                        "fired": 1,
                        "failed": 0,
                        "pending": 0,
                        "dispatched": 0,
                        "submitted": 0,
                        "requeued": 0,
                    },
                )()
                results = supervisor_poll_once(config, mode="loop", dispatch=False)

            self.assertEqual(results[0]["root_id"], "repo-test")
            self.assertTrue(results[0]["ok"])
            self.assertTrue(results[0]["activity"])
            self.assertTrue((base / "state" / "monitors").exists())
            poll_once.assert_called_once()
            self.assertFalse(poll_once.call_args.kwargs["dispatch"])


if __name__ == "__main__":
    unittest.main()
