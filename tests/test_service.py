from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from codex_wake.service import (
    build_service_config,
    default_service_name,
    install_service,
    read_log_tail,
    render_unit,
    service_status,
    slugify,
    uninstall_service,
)


class FakeRunner:
    def __init__(self, active: str = "active", enabled: str = "enabled") -> None:
        self.calls: list[list[str]] = []
        self.active = active
        self.enabled = enabled

    def run(self, args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
        self.calls.append(args)
        stdout = ""
        if "is-active" in args:
            stdout = f"{self.active}\n"
        if "is-enabled" in args:
            stdout = f"{self.enabled}\n"
        return subprocess.CompletedProcess(args=args, returncode=0, stdout=stdout, stderr="")


class ServiceTests(unittest.TestCase):
    def test_slug_and_default_service_name(self) -> None:
        self.assertEqual(slugify("Codex Wake!"), "codex-wake")
        self.assertEqual(default_service_name(Path("/tmp/Codex Wake!")), "codex-wake-codex-wake.service")

    def test_render_unit_uses_repo_wake_root_daemon_and_log(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            config = build_service_config(
                repo_root=base / "repo",
                wake_root=base / "repo" / ".codex" / "wake",
                name="wake-test",
                daemon_path="/usr/local/bin/codex-waked",
                unit_dir=base / "systemd",
                log_path=base / "state" / "wake.log",
            )

            unit = render_unit(config)

            self.assertEqual(config.name, "wake-test.service")
            self.assertIn(f"WorkingDirectory={base / 'repo'}", unit)
            self.assertIn(f'ExecStart="/usr/local/bin/codex-waked" --wake-root "{base / "repo" / ".codex" / "wake"}" --interval 1', unit)
            self.assertIn(f"StandardOutput=append:{base / 'state' / 'wake.log'}", unit)

    def test_install_and_uninstall_service_use_user_systemctl(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            config = build_service_config(
                repo_root=base / "repo",
                wake_root=base / "repo" / ".codex" / "wake",
                name="wake-test",
                daemon_path="/usr/local/bin/codex-waked",
                unit_dir=base / "systemd",
                log_path=base / "state" / "wake.log",
            )
            runner = FakeRunner()

            install_service(config, runner)

            self.assertTrue(config.unit_path.exists())
            self.assertTrue(config.log_path.parent.exists())
            self.assertEqual(
                runner.calls,
                [
                    ["systemctl", "--user", "daemon-reload"],
                    ["systemctl", "--user", "enable", "--now", "wake-test.service"],
                    ["systemctl", "--user", "is-active", "wake-test.service"],
                ],
            )

            uninstall_service(config, runner)

            self.assertFalse(config.unit_path.exists())
            self.assertEqual(runner.calls[-2:], [["systemctl", "--user", "disable", "--now", "wake-test.service"], ["systemctl", "--user", "daemon-reload"]])

    def test_service_status_and_log_tail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            config = build_service_config(
                repo_root=base / "repo",
                wake_root=base / "repo" / ".codex" / "wake",
                name="wake-test",
                daemon_path="/usr/local/bin/codex-waked",
                unit_dir=base / "systemd",
                log_path=base / "state" / "wake.log",
            )
            config.log_path.parent.mkdir(parents=True)
            config.log_path.write_text("one\ntwo\nthree\n", encoding="utf-8")

            self.assertEqual(read_log_tail(config.log_path, 2), "two\nthree")
            self.assertEqual(service_status(config, FakeRunner(active="inactive", enabled="disabled")), ("inactive", "disabled"))


if __name__ == "__main__":
    unittest.main()
