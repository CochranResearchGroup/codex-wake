from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from codex_wake.openclaw_gateway import (
    OpenClawGatewayDispatchResult,
    build_openclaw_gateway_target,
    dispatch_openclaw_gateway_record,
    openclaw_gateway_agent_params,
    openclaw_wake_prompt,
)
from codex_wake.records import WakePath, build_record, write_record


class FakeOpenClawRunner:
    def __init__(self, responses: list[subprocess.CompletedProcess[str] | BaseException]) -> None:
        self.responses = list(responses)
        self.commands: list[list[str]] = []
        self.timeouts: list[float] = []

    def run(self, command: list[str], *, timeout: float) -> subprocess.CompletedProcess[str]:
        self.commands.append(command)
        self.timeouts.append(timeout)
        response = self.responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        return response


def completed(command: list[str] | None = None, *, returncode: int = 0, stdout: dict | str = "", stderr: str = "") -> subprocess.CompletedProcess[str]:
    text = json.dumps(stdout) if isinstance(stdout, dict) else stdout
    return subprocess.CompletedProcess(command or ["openclaw"], returncode=returncode, stdout=text, stderr=stderr)


class OpenClawGatewayTests(unittest.TestCase):
    def make_target(self) -> dict:
        return build_openclaw_gateway_target(
            agent_id="main",
            session_key="agent:main:slack:channel:c0ahqqcg7j4",
            workspace="default",
            channel_id="C0AHQQCG7J4",
            thread_ts="1779729958.218239",
            timeout_seconds=120,
            gateway_timeout_ms=10_000,
        )

    def make_firing_record(self, root: Path, cwd: Path, *, target: dict | None = None) -> WakePath:
        record = build_record(
            predicate={"type": "not_before", "due_at": "2026-05-25T21:15:00Z"},
            prompt="SECRET ORIGINAL PROMPT",
            cwd=cwd,
            target=target or self.make_target(),
            now=datetime(2026, 5, 25, 20, 30, tzinfo=UTC),
        )
        record["id"] = "wake_openclaw"
        record["status"] = "firing"
        path = write_record(root, record)
        return WakePath(path=path, record=record)

    def preflight_ok(self) -> subprocess.CompletedProcess[str]:
        return completed(
            stdout={
                "version": "2026.5.22",
                "url": "ws://127.0.0.1:18789",
                "rpc": {"ok": True, "capability": "admin_capable"},
            }
        )

    def dispatch_ok(self) -> subprocess.CompletedProcess[str]:
        return completed(
            stdout={
                "runId": "codex-wake:wake_openclaw",
                "status": "ok",
                "summary": "completed",
                "result": {
                    "payloads": [{"text": "P40_OPENCLAW_OK"}],
                    "finalAssistantVisibleText": "P40_OPENCLAW_OK",
                    "meta": {
                        "agentMeta": {
                            "sessionId": "session_123",
                            "provider": "openai-codex",
                            "model": "gpt-5.5",
                        },
                    },
                },
            }
        )

    def test_openclaw_wake_prompt_points_to_record_without_original_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "wake"
            found = self.make_firing_record(root, Path(tmp))

            prompt = openclaw_wake_prompt(root, found.record)

            self.assertIn("WAKE_TRIGGER_ID=wake_openclaw", prompt)
            self.assertIn(f"Wake root: {root.resolve()}", prompt)
            self.assertIn(f"Record cwd: {Path(tmp)}", prompt)
            self.assertNotIn("SECRET ORIGINAL PROMPT", prompt)

    def test_build_target_rejects_placeholder_session_key(self) -> None:
        with self.assertRaises(ValueError):
            build_openclaw_gateway_target(
                agent_id="main",
                session_key="agent:main:noop-smoke-test",
            )

    def test_build_target_rejects_mismatched_agent_id(self) -> None:
        with self.assertRaises(ValueError):
            build_openclaw_gateway_target(
                agent_id="ops",
                session_key="agent:main:slack:channel:c0ahqqcg7j4",
            )

    def test_agent_params_are_gateway_ready_and_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "wake"
            found = self.make_firing_record(root, Path(tmp))

            params = openclaw_gateway_agent_params(root, found.record, found.record["target"])

            self.assertEqual(params["agentId"], "main")
            self.assertEqual(params["sessionKey"], "agent:main:slack:channel:c0ahqqcg7j4")
            self.assertEqual(params["idempotencyKey"], "codex-wake:wake_openclaw")
            self.assertFalse(params["deliver"])
            self.assertEqual(params["timeout"], 120)
            self.assertIn("WAKE_TRIGGER_ID=wake_openclaw", params["message"])
            self.assertNotIn("SECRET ORIGINAL PROMPT", params["message"])
            self.assertNotIn("expectFinal", params)

    def test_dispatch_success_records_sanitized_gateway_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "wake"
            found = self.make_firing_record(root, Path(tmp))
            found.record["last_error"] = "previous transient failure"
            write_record(root, found.record)
            runner = FakeOpenClawRunner([self.preflight_ok(), self.dispatch_ok()])

            result = dispatch_openclaw_gateway_record(
                root,
                found,
                runner=runner,
                now=datetime(2026, 5, 25, 21, 15, tzinfo=UTC),
            )

            self.assertIsInstance(result, OpenClawGatewayDispatchResult)
            self.assertEqual(result.status, "submitted")
            self.assertEqual(runner.commands[0][1:3], ["gateway", "status"])
            self.assertEqual(runner.commands[1][1:3], ["gateway", "call"])
            params = json.loads(runner.commands[1][runner.commands[1].index("--params") + 1])
            self.assertEqual(params["agentId"], "main")
            self.assertEqual(params["sessionKey"], "agent:main:slack:channel:c0ahqqcg7j4")
            submitted = json.loads((root / "submitted" / "wake_openclaw.json").read_text())
            self.assertEqual(submitted["status"], "submitted")
            self.assertNotIn("last_error", submitted)
            self.assertEqual(submitted["openclaw_gateway_preflight"]["rpc_ok"], True)
            dispatch_result = submitted["dispatch_result"]
            self.assertEqual(dispatch_result["transport"], "openclaw_gateway")
            self.assertEqual(dispatch_result["run_id"], "codex-wake:wake_openclaw")
            self.assertEqual(dispatch_result["session_id"], "session_123")
            self.assertEqual(dispatch_result["provider"], "openai-codex")
            self.assertEqual(dispatch_result["model"], "gpt-5.5")
            self.assertEqual(dispatch_result["final_text_summary"], {"present": True, "length": 15, "wake_marker_present": False})
            self.assertNotIn("P40_OPENCLAW_OK", json.dumps(dispatch_result))
            self.assertEqual(submitted["events"][-1]["type"], "openclaw_gateway_dispatch_result")

    def test_dispatch_failure_requeues_with_gateway_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "wake"
            found = self.make_firing_record(root, Path(tmp))
            runner = FakeOpenClawRunner(
                [
                    self.preflight_ok(),
                    completed(returncode=1, stderr="gateway rejected request"),
                ]
            )

            result = dispatch_openclaw_gateway_record(
                root,
                found,
                runner=runner,
                now=datetime(2026, 5, 25, 21, 15, tzinfo=UTC),
            )

            self.assertEqual(result.status, "requeued")
            data = json.loads((root / "pending" / "wake_openclaw.json").read_text())
            self.assertEqual(data["attempts"], 1)
            self.assertEqual(data["next_attempt_at"], "2026-05-25T21:16:00Z")
            self.assertIn("gateway rejected request", data["last_error"])
            self.assertEqual(data["events"][-2]["type"], "openclaw_gateway_dispatch_failed")
            self.assertEqual(data["events"][-1]["type"], "requeued")

    def test_timeout_requeues_and_timeout_is_auditable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "wake"
            found = self.make_firing_record(root, Path(tmp))
            runner = FakeOpenClawRunner(
                [
                    subprocess.TimeoutExpired(["openclaw", "gateway", "status"], 15.0),
                ]
            )

            result = dispatch_openclaw_gateway_record(
                root,
                found,
                runner=runner,
                now=datetime(2026, 5, 25, 21, 15, tzinfo=UTC),
            )

            self.assertEqual(result.status, "requeued")
            data = json.loads((root / "pending" / "wake_openclaw.json").read_text())
            self.assertEqual(data["events"][-2]["type"], "openclaw_gateway_timeout")
            self.assertIn("timed out", data["last_error"])

    def test_max_attempts_marks_gateway_failure_terminal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "wake"
            found = self.make_firing_record(root, Path(tmp))
            found.record["max_attempts"] = 1
            write_record(root, found.record)
            runner = FakeOpenClawRunner([completed(returncode=1, stderr="gateway unavailable")])

            result = dispatch_openclaw_gateway_record(
                root,
                WakePath(path=found.path, record=found.record),
                runner=runner,
                now=datetime(2026, 5, 25, 21, 15, tzinfo=UTC),
            )

            self.assertEqual(result.status, "failed")
            data = json.loads((root / "failed" / "wake_openclaw.json").read_text())
            self.assertIn("gateway unavailable", data["last_error"])
            self.assertEqual(data["events"][-2]["type"], "openclaw_gateway_dispatch_failed")
            self.assertEqual(data["events"][-1]["type"], "failed")


if __name__ == "__main__":
    unittest.main()
