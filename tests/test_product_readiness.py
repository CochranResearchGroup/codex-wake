from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from codex_wake.monitor import write_monitor_health
from codex_wake.product_readiness import (
    STATUS_BLOCKED,
    STATUS_READY,
    app_server_readiness_from_service,
    monitor_product_readiness,
    openclaw_auth_readiness,
    openclaw_gateway_readiness,
    openclaw_plugin_readiness,
    product_readiness_summary,
    supervisor_product_readiness,
)
from codex_wake.service import ServiceAppServerReadiness
from codex_wake.supervisor import build_supervisor_config, enroll_root


class FakeRunner:
    def __init__(self, *, active: str = "inactive", enabled: str = "disabled", environment: str = "") -> None:
        self.active = active
        self.enabled = enabled
        self.environment = environment
        self.calls: list[list[str]] = []

    def run(
        self,
        args: list[str],
        *,
        check: bool = True,
        timeout: float | None = None,
    ) -> subprocess.CompletedProcess[str]:
        self.calls.append(args)
        stdout = ""
        if "is-active" in args:
            stdout = f"{self.active}\n"
        elif "is-enabled" in args:
            stdout = f"{self.enabled}\n"
        elif "show-environment" in args:
            stdout = self.environment
        return subprocess.CompletedProcess(args, 0, stdout=stdout, stderr="")


class OpenClawRunner:
    def __init__(self, responses: dict[tuple[str, ...], subprocess.CompletedProcess[str]]) -> None:
        self.responses = responses
        self.calls: list[list[str]] = []

    def run(
        self,
        args: list[str],
        *,
        check: bool = True,
        timeout: float | None = None,
    ) -> subprocess.CompletedProcess[str]:
        self.calls.append(args)
        key = tuple(args[1:])
        if key not in self.responses:
            return subprocess.CompletedProcess(args, 1, stdout="", stderr="unexpected command")
        result = self.responses[key]
        return subprocess.CompletedProcess(args, result.returncode, stdout=result.stdout, stderr=result.stderr)


def make_executable(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/bin/sh\n", encoding="utf-8")
    path.chmod(0o755)
    return path


class ProductReadinessTests(unittest.TestCase):
    def test_openclaw_auth_reports_missing_token_env_without_secret_value(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "openclaw.json"
            config.write_text(
                json.dumps({"gateway": {"auth": {"mode": "token", "token": "${OPENCLAW_GATEWAY_TOKEN}"}}}),
                encoding="utf-8",
            )

            result = openclaw_auth_readiness(config_path=config, env={})

            self.assertEqual(result["status"], STATUS_BLOCKED)
            self.assertEqual(result["missing_env"], ["OPENCLAW_GATEWAY_TOKEN"])
            self.assertEqual(result["token_source"], "env_ref")
            self.assertFalse(result["token_env_present"])
            self.assertNotIn("secret", json.dumps(result).lower())

    def test_gateway_readiness_skips_rpc_when_gateway_auth_env_missing(self) -> None:
        auth = {"status": STATUS_BLOCKED, "missing_env": ["OPENCLAW_GATEWAY_TOKEN"]}
        runner = OpenClawRunner({})

        result = openclaw_gateway_readiness(openclaw_cmd="/usr/bin/openclaw", auth=auth, runner=runner)

        self.assertEqual(result["status"], STATUS_BLOCKED)
        self.assertFalse(result["rpc_ok"])
        self.assertEqual(runner.calls, [])

    def test_openclaw_plugin_readiness_reports_missing_plugin(self) -> None:
        runner = OpenClawRunner(
            {
                ("plugins", "inspect", "codex-wake", "--runtime", "--json"): subprocess.CompletedProcess(
                    ["openclaw"], 1, stdout="", stderr="plugin not found"
                )
            }
        )

        result = openclaw_plugin_readiness(openclaw_cmd="/usr/bin/openclaw", runner=runner)

        self.assertEqual(result["status"], STATUS_BLOCKED)
        self.assertIn("plugin not found", result["message"])

    def test_openclaw_plugin_readiness_reports_active_tool(self) -> None:
        payload = {
            "plugin": {
                "id": "codex-wake",
                "version": "0.1.1",
                "source": "/home/user/.openclaw/extensions/codex-wake/index.js",
                "origin": "global",
                "activated": True,
                "status": "loaded",
                "toolNames": ["codex_wake_schedule"],
                "configSchema": True,
            },
            "diagnostics": [],
            "install": {"source": "path", "installPath": "/home/user/.openclaw/extensions/codex-wake"},
        }
        runner = OpenClawRunner(
            {
                ("plugins", "inspect", "codex-wake", "--runtime", "--json"): subprocess.CompletedProcess(
                    ["openclaw"], 0, stdout=json.dumps(payload), stderr=""
                )
            }
        )

        result = openclaw_plugin_readiness(openclaw_cmd="/usr/bin/openclaw", runner=runner)

        self.assertEqual(result["status"], STATUS_READY)
        self.assertEqual(result["tool_names"], ["codex_wake_schedule"])
        self.assertEqual(result["diagnostic_count"], 0)

    def test_stale_monitor_health_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            daemon = make_executable(base / "bin" / "codex-waked")
            repo = base / "repo"
            wake_root = repo / ".codex" / "wake"
            monitor_dir = base / "state" / "monitors"
            write_monitor_health(
                wake_root=wake_root,
                repo_root=repo,
                source="supervisor",
                mode="loop",
                state_dir=monitor_dir,
                now=datetime.now(UTC) - timedelta(hours=1),
            )

            result = monitor_product_readiness(
                wake_root=wake_root,
                repo_root=repo,
                daemon_path=str(daemon),
                runner=FakeRunner(active="inactive", enabled="disabled"),
                state_dir=monitor_dir,
                stale_after_seconds=120,
            )

            self.assertEqual(result["status"], STATUS_BLOCKED)
            self.assertIn("stale", result["message"])

    def test_missing_supervisor_is_blocked_even_with_registry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            codex_wake = make_executable(base / "bin" / "codex-wake")
            config = build_supervisor_config(
                codex_wake_path=str(codex_wake),
                unit_dir=base / "systemd",
                registry_dir=base / "config" / "roots.d",
                state_dir=base / "state" / "supervisor",
                log_path=base / "state" / "supervisor.log",
            )
            wake_root = base / "repo" / ".codex" / "wake"
            enroll_root(wake_root=wake_root, repo_root=base / "repo", registry_dir=config.registry_dir)

            result = supervisor_product_readiness(
                wake_root=wake_root,
                codex_wake_path=str(codex_wake),
                registry_dir=config.registry_dir,
                state_dir=config.state_dir,
                log_path=config.log_path,
                runner=FakeRunner(active="inactive", enabled="disabled"),
            )

            self.assertEqual(result["status"], STATUS_BLOCKED)
            self.assertEqual(result["root_count"], 1)
            self.assertTrue(result["current_root_enrolled"])

    def test_app_server_command_drift_is_blocked(self) -> None:
        readiness = ServiceAppServerReadiness(
            codex_cmd_ready=False,
            codex_cmd_source="interactive_path_only",
            codex_cmd="",
            unit_codex_cmd="",
            user_manager_codex_cmd="",
            interactive_codex_cmd="/usr/bin/codex",
            message="interactive shell can resolve codex, but user-systemd cannot",
        )

        with unittest.mock.patch("codex_wake.product_readiness.service_app_server_readiness", return_value=readiness):
            result = app_server_readiness_from_service(object())

        self.assertEqual(result["status"], STATUS_BLOCKED)
        self.assertEqual(result["codex_cmd_source"], "interactive_path_only")

    def test_product_readiness_summary_omits_gateway_secret_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            daemon = make_executable(base / "bin" / "codex-waked")
            codex_wake = make_executable(base / "bin" / "codex-wake")
            codex = make_executable(base / "bin" / "codex")
            repo = base / "repo"
            wake_root = repo / ".codex" / "wake"
            openclaw_config = base / "openclaw.json"
            openclaw_config.write_text(
                json.dumps({"gateway": {"auth": {"mode": "token", "token": "${OPENCLAW_GATEWAY_TOKEN}"}}}),
                encoding="utf-8",
            )
            env = {"OPENCLAW_GATEWAY_TOKEN": "super-secret-token", "TMUX": "/tmp/tmux,1,0", "TMUX_PANE": "%1"}
            gateway_payload = {"rpc": {"ok": True, "url": "ws://127.0.0.1:18789", "server": {"version": "test"}}}
            plugin_payload = {
                "plugin": {
                    "id": "codex-wake",
                    "activated": True,
                    "status": "loaded",
                    "toolNames": ["codex_wake_schedule"],
                    "configSchema": True,
                },
                "diagnostics": [],
            }
            runner = OpenClawRunner(
                {
                    ("gateway", "status", "--require-rpc", "--json", "--timeout", "30000"): subprocess.CompletedProcess(
                        ["openclaw"], 0, stdout=json.dumps(gateway_payload), stderr=""
                    ),
                    ("plugins", "inspect", "codex-wake", "--runtime", "--json"): subprocess.CompletedProcess(
                        ["openclaw"], 0, stdout=json.dumps(plugin_payload), stderr=""
                    ),
                }
            )

            with unittest.mock.patch(
                "codex_wake.product_readiness.command_paths",
                return_value={
                    "codex_wake": str(codex_wake),
                    "codex_waked": str(daemon),
                    "codex_wake_hook": str(base / "bin" / "codex-wake-hook"),
                    "codex": str(codex),
                    "tmux": "/usr/bin/tmux",
                    "openclaw": "/usr/bin/openclaw",
                },
            ):
                summary = product_readiness_summary(
                    wake_root=wake_root,
                    repo_root=repo,
                    daemon_path=str(daemon),
                    codex_path=str(codex),
                    codex_wake_path=str(codex_wake),
                    openclaw_config=openclaw_config,
                    runner=FakeRunner(active="inactive", enabled="disabled"),
                    openclaw_runner=runner,
                    env=env,
                )

            rendered = json.dumps(summary)
            self.assertNotIn("super-secret-token", rendered)
            self.assertEqual(summary["checks"]["openclaw_gateway"]["status"], STATUS_READY)
            self.assertEqual(summary["checks"]["openclaw_plugin"]["status"], STATUS_READY)


if __name__ == "__main__":
    unittest.main()
