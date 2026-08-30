from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from codex_wake.app_server import APP_SERVER_CODEX_ENV
from codex_wake.records import WakeError
from codex_wake.service import (
    build_service_config,
    default_service_name,
    install_service,
    parse_unit_environment,
    read_log_tail,
    render_unit,
    service_app_server_readiness,
    service_status,
    slugify,
    stop_service,
    uninstall_service,
)


class FakeRunner:
    def __init__(self, active: str = "active", enabled: str = "enabled", environment: str = "") -> None:
        self.calls: list[list[str]] = []
        self.active = active
        self.enabled = enabled
        self.environment = environment

    def run(self, args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
        self.calls.append(args)
        stdout = ""
        if "is-active" in args:
            stdout = f"{self.active}\n"
        if "is-enabled" in args:
            stdout = f"{self.enabled}\n"
        if "show-environment" in args:
            stdout = self.environment
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
                daemon_path="/bin/sh",
                unit_dir=base / "systemd",
                log_path=base / "state" / "wake.log",
            )

            unit = render_unit(config)

            self.assertEqual(config.name, "wake-test.service")
            self.assertIn(f"WorkingDirectory={base / 'repo'}", unit)
            self.assertIn(f'ExecStart="/bin/sh" --wake-root "{base / "repo" / ".codex" / "wake"}" --interval 1', unit)
            self.assertIn(f"StandardOutput=append:{base / 'state' / 'wake.log'}", unit)
            self.assertNotIn(APP_SERVER_CODEX_ENV, unit)

    def test_render_unit_skips_start_when_repo_directory_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            repo = base / "repo with spaces"
            config = build_service_config(
                repo_root=repo,
                wake_root=repo / ".codex" / "wake",
                name="wake-test",
                daemon_path="/bin/sh",
                unit_dir=base / "systemd",
                log_path=base / "state" / "wake.log",
            )

            unit = render_unit(config)

            self.assertIn(f'ConditionPathIsDirectory="{repo.resolve()}"', unit)

    def test_render_unit_does_not_restart_after_working_directory_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            config = build_service_config(
                repo_root=base / "repo",
                wake_root=base / "repo" / ".codex" / "wake",
                name="wake-test",
                daemon_path="/bin/sh",
                unit_dir=base / "systemd",
                log_path=base / "state" / "wake.log",
            )

            unit = render_unit(config)

            self.assertIn("RestartPreventExitStatus=200", unit)

    def test_render_unit_can_persist_codex_path_for_app_server_dispatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            codex = base / "bin" / "codex"
            codex.parent.mkdir()
            codex.write_text("#!/bin/sh\n", encoding="utf-8")
            codex.chmod(0o755)
            config = build_service_config(
                repo_root=base / "repo",
                wake_root=base / "repo" / ".codex" / "wake",
                name="wake-test",
                daemon_path="/bin/sh",
                codex_path=str(codex),
                unit_dir=base / "systemd",
                log_path=base / "state" / "wake.log",
            )

            unit = render_unit(config)
            config.unit_path.parent.mkdir(parents=True)
            config.unit_path.write_text(unit, encoding="utf-8")

            self.assertIn(f'Environment="{APP_SERVER_CODEX_ENV}={codex.resolve()}"', unit)
            self.assertEqual(parse_unit_environment(config.unit_path)[APP_SERVER_CODEX_ENV], str(codex.resolve()))

    def test_render_unit_preserves_stable_codex_symlink_spelling(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            target = base / "packages" / "codex"
            target.parent.mkdir()
            target.write_text("#!/bin/sh\n", encoding="utf-8")
            target.chmod(0o755)
            stable = base / "bin" / "codex"
            stable.parent.mkdir()
            stable.symlink_to(target)

            config = build_service_config(
                repo_root=base / "repo",
                daemon_path="/bin/sh",
                codex_path=str(stable),
                unit_dir=base / "systemd",
                log_path=base / "state" / "wake.log",
            )

            self.assertEqual(config.codex_path, stable)
            self.assertIn(f'Environment="{APP_SERVER_CODEX_ENV}={stable}"', render_unit(config))

    def test_service_path_resolution_preserves_stable_codex_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            stable = Path(tmp) / "bin" / "codex"
            stable.parent.mkdir()
            stable.write_text("#!/bin/sh\n", encoding="utf-8")
            stable.chmod(0o755)

            with patch.dict("os.environ", {"PATH": str(stable.parent)}, clear=True):
                config = build_service_config(
                    daemon_path="/bin/sh",
                    resolve_default_codex=True,
                )

            self.assertEqual(config.codex_path, stable)

    def test_service_rejects_version_managed_codex_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            codex = Path(tmp) / ".nvm" / "versions" / "node" / "v24.1.0" / "bin" / "codex"
            codex.parent.mkdir(parents=True)
            codex.write_text("#!/bin/sh\n", encoding="utf-8")
            codex.chmod(0o755)

            with self.assertRaisesRegex(WakeError, "stable wrapper or symlink"):
                build_service_config(daemon_path="/bin/sh", codex_path=str(codex))

            with patch.dict("os.environ", {"PATH": str(codex.parent)}, clear=True):
                config = build_service_config(
                    daemon_path="/bin/sh",
                    resolve_default_codex=True,
                )
            self.assertIsNone(config.codex_path)

    def test_service_rejects_non_regular_daemon_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(WakeError, "not a regular file"):
                build_service_config(daemon_path=tmp)

    def test_lifecycle_config_does_not_require_launch_executables(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            config = build_service_config(
                daemon_path=str(base / "missing-codex-waked"),
                codex_path=str(base / "missing-codex"),
                unit_dir=base / "systemd",
                log_path=base / "state" / "wake.log",
                validate_executables=False,
            )

            self.assertIsNone(config.daemon_path)
            self.assertIsNone(config.codex_path)
            self.assertEqual(
                service_status(config, FakeRunner(active="inactive", enabled="disabled")),
                ("inactive", "disabled"),
            )
            runner = FakeRunner()
            stop_service(config, runner)
            uninstall_service(config, runner)
            self.assertIn(["systemctl", "--user", "disable", "--now", config.name], runner.calls)
            with self.assertRaisesRegex(WakeError, "resolved before rendering"):
                render_unit(config)

    def test_service_app_server_readiness_prefers_unit_environment(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            codex = base / "bin" / "codex"
            codex.parent.mkdir()
            codex.write_text("#!/bin/sh\n", encoding="utf-8")
            codex.chmod(0o755)
            config = build_service_config(
                repo_root=base / "repo",
                wake_root=base / "repo" / ".codex" / "wake",
                name="wake-test",
                daemon_path="/bin/sh",
                codex_path=str(codex),
                unit_dir=base / "systemd",
                log_path=base / "state" / "wake.log",
            )
            config.unit_path.parent.mkdir(parents=True)
            config.unit_path.write_text(render_unit(config), encoding="utf-8")

            readiness = service_app_server_readiness(config, FakeRunner())

            self.assertTrue(readiness.codex_cmd_ready)
            self.assertEqual(readiness.codex_cmd_source, "unit_environment")
            self.assertEqual(readiness.codex_cmd, str(codex.resolve()))

    def test_service_app_server_readiness_checks_user_manager_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            codex = base / "manager-bin" / "codex"
            codex.parent.mkdir()
            codex.write_text("#!/bin/sh\n", encoding="utf-8")
            codex.chmod(0o755)
            config = build_service_config(
                repo_root=base / "repo",
                wake_root=base / "repo" / ".codex" / "wake",
                name="wake-test",
                daemon_path="/bin/sh",
                unit_dir=base / "systemd",
                log_path=base / "state" / "wake.log",
            )

            readiness = service_app_server_readiness(config, FakeRunner(environment=f"PATH={codex.parent}\n"))

            self.assertTrue(readiness.codex_cmd_ready)
            self.assertEqual(readiness.codex_cmd_source, "user_manager_path")
            self.assertEqual(readiness.user_manager_codex_cmd, str(codex.resolve()))

    def test_service_app_server_readiness_does_not_use_interactive_path_for_manager(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            codex = base / "interactive-bin" / "codex"
            codex.parent.mkdir()
            codex.write_text("#!/bin/sh\n", encoding="utf-8")
            codex.chmod(0o755)
            config = build_service_config(
                repo_root=base / "repo",
                wake_root=base / "repo" / ".codex" / "wake",
                name="wake-test",
                daemon_path="/bin/sh",
                unit_dir=base / "systemd",
                log_path=base / "state" / "wake.log",
            )

            with patch.dict("os.environ", {"PATH": str(codex.parent)}, clear=True):
                readiness = service_app_server_readiness(config, FakeRunner(environment=""))

            self.assertFalse(readiness.codex_cmd_ready)
            self.assertEqual(readiness.codex_cmd_source, "interactive_path_only")
            self.assertEqual(readiness.user_manager_codex_cmd, "")
            self.assertEqual(readiness.interactive_codex_cmd, str(codex.resolve()))

    def test_install_and_uninstall_service_use_user_systemctl(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            config = build_service_config(
                repo_root=base / "repo",
                wake_root=base / "repo" / ".codex" / "wake",
                name="wake-test",
                daemon_path="/bin/sh",
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
                daemon_path="/bin/sh",
                unit_dir=base / "systemd",
                log_path=base / "state" / "wake.log",
            )
            config.log_path.parent.mkdir(parents=True)
            config.log_path.write_text("one\ntwo\nthree\n", encoding="utf-8")

            self.assertEqual(read_log_tail(config.log_path, 2), "two\nthree")
            self.assertEqual(service_status(config, FakeRunner(active="inactive", enabled="disabled")), ("inactive", "disabled"))


if __name__ == "__main__":
    unittest.main()
