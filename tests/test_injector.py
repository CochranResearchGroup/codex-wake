from __future__ import annotations

import json
import os
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

from codex_wake.injector import (
    PaneLock,
    canonical_prompt,
    dispatch_firing_record,
    lock_name_for_pane,
    unsafe_pane_reason,
)
from codex_wake.daemon import poll_once
from codex_wake.event_wake import EventWake
from codex_wake.records import WakePath, build_record, cancel_record, find_record, write_record
from codex_wake.signal_records import ManagedReaderCapability, WakeRecordPublisher, signal_journal_path
from codex_wake.signal_store import SQLiteSignalModule
from codex_wake.signals import SourceCommit
from tests.test_signal_store import make_observation
from tests.test_signals import make_adapter, make_intent


class FakeTmuxRunner:
    def __init__(self, capture: str = "Codex ready", captures: list[str | BaseException] | None = None) -> None:
        self.captures: list[str | BaseException] = list(captures) if captures is not None else [capture]
        self.capture_calls = 0
        self.pastes: list[tuple[str, str, str, str]] = []

    def capture_pane(self, socket: str, pane: str) -> str:
        self.capture_calls += 1
        if len(self.captures) > 1:
            value = self.captures.pop(0)
        else:
            value = self.captures[0]
        if isinstance(value, BaseException):
            raise value
        return value

    def paste_prompt(self, socket: str, pane: str, wake_id: str, prompt: str) -> None:
        self.pastes.append((socket, pane, wake_id, prompt))


class InjectorTests(unittest.TestCase):
    def test_signal_cancellation_holds_lifecycle_lock_until_dispatch_reloads_authority(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "wake"
            runtime = SQLiteSignalModule(
                signal_journal_path(root),
                record_publisher=WakeRecordPublisher(
                    root,
                    ManagedReaderCapability(root, "reader", 1, frozenset({1, 2}), True),
                ),
            )
            EventWake(
                runtime,
                adapters=[make_adapter()],
                clock=lambda: datetime(2026, 9, 14, 14, 0, tzinfo=UTC),
                id_factory=lambda: "wake_signal",
            ).register(make_intent(), idempotency_key="job-42")
            runtime.ingest(
                [make_observation()],
                SourceCommit(
                    "memory", "contract-test", "checkpoint-1", 1,
                    datetime(2026, 9, 14, 14, 1, tzinfo=UTC),
                ),
            )
            poll_once(
                root,
                now=datetime(2026, 9, 14, 14, 2, tzinfo=UTC),
                dispatch=False,
                signal_runtime=runtime,
            )
            firing = find_record(root, "wake_signal")
            lock_held = threading.Event()
            release = threading.Event()

            def cancellation_checkpoint(name: str) -> None:
                if name == "after_cancel_lock":
                    lock_held.set()
                    self.assertTrue(release.wait(timeout=5))

            runner = FakeTmuxRunner()
            with ThreadPoolExecutor(max_workers=2) as pool:
                cancellation = pool.submit(
                    cancel_record,
                    root,
                    "wake_signal",
                    datetime(2026, 9, 14, 14, 3, tzinfo=UTC),
                    checkpoint=cancellation_checkpoint,
                )
                self.assertTrue(lock_held.wait(timeout=5))
                dispatch = pool.submit(
                    dispatch_firing_record,
                    root,
                    firing,
                    runner=runner,
                    signal_authorizer=runtime.authorize_firing_record,
                )
                release.set()
                cancellation.result(timeout=5)
                result = dispatch.result(timeout=5)

            self.assertEqual(result.status, "skipped")
            self.assertEqual(runner.capture_calls, 0)
            self.assertEqual(runner.pastes, [])
            cancelled = json.loads((root / "cancelled" / "wake_signal.json").read_text())
            self.assertEqual(cancelled["attempts"], 0)

    def test_signal_firing_without_live_authority_makes_no_transport_attempt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "wake"
            found = self.make_firing_record(root, Path(tmp))
            found.record["schema_version"] = 2
            found.record["record_revision"] = 2
            runner = FakeTmuxRunner()

            result = dispatch_firing_record(
                root,
                found,
                runner=runner,
                signal_authorizer=lambda _record: False,
            )

            self.assertEqual(result.status, "skipped")
            self.assertEqual(found.record["attempts"], 0)
            self.assertEqual(runner.capture_calls, 0)
            self.assertEqual(runner.pastes, [])

    def test_signal_firing_with_tampered_payload_makes_no_transport_attempt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "wake"
            runtime = SQLiteSignalModule(
                signal_journal_path(root),
                record_publisher=WakeRecordPublisher(
                    root,
                    ManagedReaderCapability(root, "reader", 1, frozenset({1, 2}), True),
                ),
            )
            EventWake(
                runtime,
                adapters=[make_adapter()],
                clock=lambda: datetime(2026, 9, 14, 14, 0, tzinfo=UTC),
                id_factory=lambda: "wake_signal",
            ).register(make_intent(), idempotency_key="job-42")
            runtime.ingest(
                [make_observation()],
                SourceCommit(
                    "memory", "contract-test", "checkpoint-1", 1,
                    datetime(2026, 9, 14, 14, 1, tzinfo=UTC),
                ),
            )
            poll_once(
                root,
                now=datetime(2026, 9, 14, 14, 2, tzinfo=UTC),
                dispatch=False,
                signal_runtime=runtime,
            )
            found = find_record(root, "wake_signal")
            tampered = dict(found.record)
            tampered["prompt"] = "tampered prompt"
            found.path.write_text(json.dumps(tampered), encoding="utf-8")
            runner = FakeTmuxRunner()

            result = dispatch_firing_record(
                root,
                WakePath(found.path, tampered),
                runner=runner,
                signal_authorizer=runtime.authorize_firing_record,
            )

            self.assertEqual(result.status, "skipped")
            self.assertEqual(runner.capture_calls, 0)
            self.assertEqual(runner.pastes, [])

    def make_firing_record(
        self,
        root: Path,
        cwd: Path,
        prompt: str = "full continuation prompt",
        *,
        max_attempts: int = 3,
    ) -> WakePath:
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
        record["max_attempts"] = max_attempts
        path = write_record(root, record)
        return WakePath(path=path, record=record)

    def test_canonical_prompt_routes_to_owning_wake_root(self) -> None:
        root = Path("/tmp/a wake root")
        self.assertEqual(
            canonical_prompt("wake_123", root),
            "WAKE_TRIGGER_ID=wake_123\n"
            "WAKE_TRIGGER_ROOT=/tmp/a wake root\n"
            "Resume the scheduled wake task.\n",
        )

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

    def test_pane_lock_removes_stale_dead_pid_lock(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            lock_path = root / "locks" / f"{lock_name_for_pane('/tmp/tmux/default', '%1')}.lock"
            lock_path.parent.mkdir(parents=True, exist_ok=True)
            lock_path.write_text("999999999", encoding="ascii")

            with PaneLock(root, "/tmp/tmux/default", "%1"):
                self.assertEqual(lock_path.read_text(encoding="ascii"), str(os.getpid()))

            self.assertFalse(lock_path.exists())

    def test_pane_lock_removes_malformed_lock(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            lock_path = root / "locks" / f"{lock_name_for_pane('/tmp/tmux/default', '%1')}.lock"
            lock_path.parent.mkdir(parents=True, exist_ok=True)
            lock_path.write_text("not-a-pid", encoding="ascii")

            with PaneLock(root, "/tmp/tmux/default", "%1"):
                self.assertEqual(lock_path.read_text(encoding="ascii"), str(os.getpid()))

            self.assertFalse(lock_path.exists())

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
            self.assertEqual(runner.pastes[0][3], canonical_prompt("wake_test", root))
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
            submitted_path = root / "submitted" / "wake_test.json"
            self.assertTrue(submitted_path.exists())
            data = json.loads(submitted_path.read_text())
            self.assertEqual(data["visibility_result"]["classification"], "ack_observed_visibility_unproven")
            self.assertEqual(data["events"][-2]["type"], "ack_observed")
            self.assertEqual(data["events"][-1]["type"], "tmux_visibility_checked")

    def test_dispatch_records_visible_prompt_when_marker_appears_after_ack(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "wake"
            found = self.make_firing_record(root, Path(tmp))
            ack_dir = root / "acks"
            ack_dir.mkdir(parents=True, exist_ok=True)
            (ack_dir / "wake_test.submitted").write_text("{}", encoding="utf-8")
            runner = FakeTmuxRunner(
                captures=[
                    "Codex ready",
                    "Codex\n> WAKE_TRIGGER_ID=wake_test\n  Resume the scheduled wake task.",
                ]
            )

            result = dispatch_firing_record(
                root,
                found,
                runner=runner,
                now=datetime(2026, 5, 18, 21, 15, tzinfo=UTC),
                ack_timeout_override=0,
            )

            self.assertEqual(result.status, "submitted")
            data = json.loads((root / "submitted" / "wake_test.json").read_text())
            visibility = data["visibility_result"]
            self.assertEqual(visibility["classification"], "visible_prompt_observed")
            self.assertFalse(visibility["pre_capture"]["wake_marker_present"])
            self.assertTrue(visibility["post_capture"]["wake_marker_present"])
            self.assertTrue(visibility["post_marker_new"])
            self.assertEqual(visibility["privacy"], "raw_pane_text_not_stored")
            self.assertEqual(data["events"][-1]["visibility_result"]["classification"], "visible_prompt_observed")
            self.assertNotIn("WAKE_TRIGGER_ID", json.dumps(visibility))

    def test_dispatch_records_visibility_check_failure_without_failing_ack(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "wake"
            found = self.make_firing_record(root, Path(tmp))
            ack_dir = root / "acks"
            ack_dir.mkdir(parents=True, exist_ok=True)
            (ack_dir / "wake_test.submitted").write_text("{}", encoding="utf-8")
            runner = FakeTmuxRunner(captures=["Codex ready", OSError("capture failed")])

            result = dispatch_firing_record(
                root,
                found,
                runner=runner,
                now=datetime(2026, 5, 18, 21, 15, tzinfo=UTC),
                ack_timeout_override=0,
            )

            self.assertEqual(result.status, "submitted")
            data = json.loads((root / "submitted" / "wake_test.json").read_text())
            visibility = data["visibility_result"]
            self.assertEqual(visibility["classification"], "visibility_check_failed")
            self.assertIn("post-ack tmux capture failed", visibility["error"])
            self.assertEqual(data["events"][-2]["type"], "ack_observed")
            self.assertEqual(data["events"][-1]["type"], "tmux_visibility_checked")
            self.assertEqual(data["status"], "submitted")

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

    def test_one_attempt_bound_fails_terminally_without_requeue(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "wake"
            found = self.make_firing_record(root, Path(tmp), max_attempts=1)
            runner = FakeTmuxRunner(capture="Approve command?")

            result = dispatch_firing_record(
                root,
                found,
                runner=runner,
                now=datetime(2026, 5, 18, 21, 15, tzinfo=UTC),
                ack_timeout_override=0,
            )

            self.assertEqual(result.status, "failed")
            self.assertEqual(runner.pastes, [])
            data = json.loads((root / "failed" / "wake_test.json").read_text())
            self.assertEqual(data["attempts"], 1)
            self.assertEqual(data["max_attempts"], 1)
            self.assertNotIn("requeued", [event["type"] for event in data["events"]])


if __name__ == "__main__":
    unittest.main()
