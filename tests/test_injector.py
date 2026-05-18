from __future__ import annotations

import json
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from codex_wake.injector import (
    PaneLock,
    canonical_prompt,
    dispatch_firing_record,
    lock_name_for_pane,
    unsafe_pane_reason,
)
from codex_wake.records import WakePath, build_record, write_record


class FakeTmuxRunner:
    def __init__(self, capture: str = "Codex ready") -> None:
        self.capture = capture
        self.pastes: list[tuple[str, str, str, str]] = []

    def capture_pane(self, socket: str, pane: str) -> str:
        return self.capture

    def paste_prompt(self, socket: str, pane: str, wake_id: str, prompt: str) -> None:
        self.pastes.append((socket, pane, wake_id, prompt))


class InjectorTests(unittest.TestCase):
    def make_firing_record(self, root: Path, cwd: Path, prompt: str = "full continuation prompt") -> WakePath:
        now = datetime(2026, 5, 18, 20, 30, tzinfo=UTC)
        record = build_record(
            predicate={"type": "not_before", "due_at": "2026-05-18T21:15:00Z"},
            prompt=prompt,
            cwd=cwd,
            target={"transport": "tmux", "tmux_socket": "/tmp/tmux/default", "pane": "%1"},
            now=now,
        )
        record["id"] = "wake_test"
        record["status"] = "firing"
        path = write_record(root, record)
        return WakePath(path=path, record=record)

    def test_canonical_prompt_uses_wake_id_only(self) -> None:
        self.assertEqual(canonical_prompt("wake_123"), "WAKE_TRIGGER_ID=wake_123\nResume the scheduled wake task.\n")

    def test_unsafe_pane_reason_rejects_shell_prompt_and_approval(self) -> None:
        self.assertEqual(unsafe_pane_reason("Approve command?"), "approval prompt visible")
        self.assertEqual(unsafe_pane_reason("user@host:~/repo$ "), "pane appears to be a shell prompt")
        self.assertIsNone(unsafe_pane_reason("Codex\nready for input"))

    def test_pane_lock_rejects_concurrent_lock(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with PaneLock(root, "/tmp/tmux/default", "%1"):
                with self.assertRaises(ValueError):
                    with PaneLock(root, "/tmp/tmux/default", "%1"):
                        pass
            self.assertFalse((root / "locks" / f"{lock_name_for_pane('/tmp/tmux/default', '%1')}.lock").exists())

    def test_dispatch_pastes_only_canonical_prompt_and_requeues_without_ack(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "wake"
            found = self.make_firing_record(root, Path(tmp), prompt="SECRET FULL PROMPT")
            runner = FakeTmuxRunner()

            result = dispatch_firing_record(
                root,
                found,
                runner=runner,
                now=datetime(2026, 5, 18, 21, 15, tzinfo=UTC),
                ack_timeout_override=0,
            )

            self.assertEqual(result.status, "requeued")
            self.assertEqual(len(runner.pastes), 1)
            self.assertEqual(runner.pastes[0][3], canonical_prompt("wake_test"))
            self.assertNotIn("SECRET FULL PROMPT", runner.pastes[0][3])
            pending = root / "pending" / "wake_test.json"
            self.assertTrue(pending.exists())
            data = json.loads(pending.read_text())
            self.assertEqual(data["attempts"], 1)
            self.assertEqual(data["events"][-2]["type"], "ack_timeout")
            self.assertEqual(data["events"][-1]["type"], "requeued")

    def test_dispatch_marks_submitted_when_ack_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "wake"
            found = self.make_firing_record(root, Path(tmp))
            ack_dir = root / "acks"
            ack_dir.mkdir(parents=True, exist_ok=True)
            (ack_dir / "wake_test.submitted").write_text("{}", encoding="utf-8")

            result = dispatch_firing_record(
                root,
                found,
                runner=FakeTmuxRunner(),
                now=datetime(2026, 5, 18, 21, 15, tzinfo=UTC),
                ack_timeout_override=0,
            )

            self.assertEqual(result.status, "submitted")
            self.assertTrue((root / "submitted" / "wake_test.json").exists())

    def test_unsafe_pane_requeues_and_does_not_paste(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "wake"
            found = self.make_firing_record(root, Path(tmp))
            runner = FakeTmuxRunner(capture="Approve command?")

            result = dispatch_firing_record(
                root,
                found,
                runner=runner,
                now=datetime(2026, 5, 18, 21, 15, tzinfo=UTC),
                ack_timeout_override=0,
            )

            self.assertEqual(result.status, "requeued")
            self.assertEqual(runner.pastes, [])
            data = json.loads((root / "pending" / "wake_test.json").read_text())
            self.assertEqual(data["attempts"], 1)
            self.assertEqual(data["events"][-2]["type"], "unsafe_pane")


if __name__ == "__main__":
    unittest.main()
