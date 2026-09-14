from __future__ import annotations

import json
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from types import MappingProxyType

from codex_wake.daemon import poll_once
from codex_wake.event_wake import EventWake
from codex_wake.filesystem_signals import FilesystemSignalAdapter, FilesystemSignalRunner
from codex_wake.signal_records import ManagedReaderCapability, WakeRecordPublisher, signal_journal_path
from codex_wake.signal_store import SQLiteSignalModule
from codex_wake.signals import (
    Eq,
    EvaluationLimits,
    Invalid,
    Registration,
    Resume,
    SignalRequest,
    WakeIntent,
)


NOW = datetime(2026, 9, 14, 16, 0, tzinfo=UTC)


class FilesystemSignalAdapterTests(unittest.TestCase):
    def register(
        self,
        base: Path,
        wake_root: Path,
        adapter: FilesystemSignalAdapter,
        recipe: str,
        wake_id: str = "wake_filesystem",
    ):
        runtime = SQLiteSignalModule(
            signal_journal_path(wake_root),
            record_publisher=WakeRecordPublisher(
                wake_root,
                ManagedReaderCapability(wake_root, "reader", 1, frozenset({1, 2}), True),
            ),
        )
        registration = EventWake(
            runtime,
            adapters=(adapter,),
            clock=lambda: NOW,
            id_factory=lambda: wake_id,
        ).register(
            WakeIntent(
                adapter.request(recipe),
                Resume(
                    "continue",
                    base,
                    MappingProxyType(
                        {"transport": "tmux", "tmux_socket": "/tmp/tmux", "pane": "%1"}
                    ),
                ),
            ),
            idempotency_key=f"{recipe}-{wake_id}",
        )
        self.assertIsInstance(registration, Registration)
        armed = runtime.load_armed_signal(registration.wake_id)
        self.assertIsNotNone(armed)
        return runtime, armed

    def test_created_recipe_anchors_missing_file_without_reading_contents(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            adapter = FilesystemSignalAdapter(root, "out/result.txt")

            request = adapter.request("created")
            anchor = adapter.establish_anchor(request, NOW)

            self.assertEqual(request.source, "filesystem")
            self.assertEqual(request.kind, "file.created")
            self.assertEqual(request.condition, "becomes")
            self.assertEqual(request.subject, "path:out/result.txt")
            self.assertEqual(anchor.recovery, "state_recheck")
            self.assertEqual(
                dict(anchor.baseline),
                {
                    "exists": False,
                    "file_kind": "missing",
                    "fingerprint": anchor.baseline["fingerprint"],
                },
            )
            self.assertEqual(len(anchor.baseline["fingerprint"]), 64)

    def test_reconciliation_persists_coalesced_match_then_daemon_fires_without_dispatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            wake_root = base / "wake"
            watched = base / "out" / "result.txt"
            adapter = FilesystemSignalAdapter(base, "out/result.txt")
            runtime, armed = self.register(base, wake_root, adapter, "created")
            watched.parent.mkdir()
            watched.write_text("private-file-body", encoding="utf-8")
            runner = FilesystemSignalRunner((adapter,), armed_signals=(armed,))
            runner.notify(watched)
            runner.notify(watched)

            result = poll_once(
                wake_root,
                now=NOW,
                dispatch=False,
                signal_runtime=runtime,
                signal_runners=(runner,),
            )

            self.assertIsNotNone(runner.last_result)
            self.assertEqual(
                (runner.last_result.scanned, runner.last_result.observed, runner.last_result.degraded),
                (1, 1, 0),
            )
            self.assertEqual((result.fired, result.dispatched), (1, 0))
            firing = (wake_root / "firing" / "wake_filesystem.json").read_text(encoding="utf-8")
            self.assertNotIn("private-file-body", firing)
            record = json.loads(firing)
            evidence = record["trigger_match"]["attributes"]
            self.assertTrue(evidence["coalesced"])
            self.assertEqual(evidence["hint_count"], 2)
            self.assertEqual(evidence["observation_reason"], "notification")
            self.assertEqual(len(evidence["fingerprint"]), 64)

    def test_file_exists_holds_even_when_present_at_registration(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            watched = base / "ready.flag"
            watched.write_text("not retained", encoding="utf-8")
            adapter = FilesystemSignalAdapter(base, watched)
            runtime, armed = self.register(base, base / "wake", adapter, "exists")

            runner = FilesystemSignalRunner((adapter,), armed_signals=(armed,))
            result = runner.reconcile(runtime, NOW, EvaluationLimits(10))
            match = runtime.evaluate(armed.wake_id, armed, NOW, EvaluationLimits(10))

            self.assertEqual((result.scanned, result.observed, result.degraded), (1, 1, 0))
            self.assertEqual(match.outcome, "matched")
            self.assertTrue(match.receipt.attributes["exists"])

    def test_changed_ignores_registration_baseline_then_matches_rename_away(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            watched = base / "state.db"
            watched.write_text("baseline", encoding="utf-8")
            adapter = FilesystemSignalAdapter(base, watched)
            runtime, armed = self.register(base, base / "wake", adapter, "changed")
            runner = FilesystemSignalRunner((adapter,), armed_signals=(armed,))

            runner.reconcile(runtime, NOW, EvaluationLimits(10))
            initial = runtime.evaluate(armed.wake_id, armed, NOW, EvaluationLimits(10))
            watched.rename(base / "renamed.db")
            runner.reconcile(runtime, NOW, EvaluationLimits(10))
            renamed = runtime.evaluate(armed.wake_id, armed, NOW, EvaluationLimits(10))

            self.assertEqual(initial.outcome, "not_ready")
            self.assertEqual(renamed.outcome, "matched")
            self.assertFalse(renamed.receipt.attributes["exists"])
            self.assertEqual(renamed.receipt.attributes["file_kind"], "missing")

    def test_created_waits_for_delete_then_recreate_across_runner_restart(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            watched = base / "artifact.bin"
            watched.write_bytes(b"old")
            adapter = FilesystemSignalAdapter(base, watched)
            runtime, armed = self.register(base, base / "wake", adapter, "created")
            first = FilesystemSignalRunner((adapter,), armed_signals=(armed,))
            first.reconcile(runtime, NOW, EvaluationLimits(10))
            self.assertEqual(
                runtime.evaluate(armed.wake_id, armed, NOW, EvaluationLimits(10)).outcome,
                "not_ready",
            )
            watched.unlink()
            first.reconcile(runtime, NOW, EvaluationLimits(10))
            self.assertEqual(
                runtime.evaluate(armed.wake_id, armed, NOW, EvaluationLimits(10)).outcome,
                "not_ready",
            )
            watched.write_bytes(b"new")

            restarted = FilesystemSignalRunner(
                (adapter,), armed_signals=(armed,), initial_reason="startup"
            )
            restarted.reconcile(runtime, NOW, EvaluationLimits(10))
            matched = runtime.evaluate(armed.wake_id, armed, NOW, EvaluationLimits(10))

            self.assertEqual(matched.outcome, "matched")
            self.assertTrue(matched.receipt.attributes["coalesced"])
            self.assertEqual(matched.receipt.attributes["observation_reason"], "startup")

    def test_watcher_overflow_is_evidence_only_and_reconciliation_still_matches(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            watched = base / "log.txt"
            watched.write_text("one", encoding="utf-8")
            adapter = FilesystemSignalAdapter(base, watched)
            runtime, armed = self.register(base, base / "wake", adapter, "changed")
            watched.write_text("two", encoding="utf-8")
            runner = FilesystemSignalRunner((adapter,), armed_signals=(armed,))
            runner.watcher_overflow()

            report = runner.reconcile(runtime, NOW, EvaluationLimits(10))
            matched = runtime.evaluate(armed.wake_id, armed, NOW, EvaluationLimits(10))

            self.assertEqual(report.degraded, 0)
            self.assertEqual(matched.outcome, "matched")
            self.assertTrue(matched.receipt.attributes["coalesced"])
            self.assertEqual(matched.receipt.attributes["hint_count"], 0)
            self.assertEqual(matched.receipt.attributes["observation_reason"], "watcher_overflow")

    def test_reconciliation_degrades_if_path_is_redirected_outside_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as other:
            base = Path(tmp)
            adapter = FilesystemSignalAdapter(base, "nested/result.txt")
            runtime, armed = self.register(base, base / "wake", adapter, "created")
            (Path(other) / "result.txt").write_text("private", encoding="utf-8")
            (base / "nested").symlink_to(other, target_is_directory=True)

            report = FilesystemSignalRunner(
                (adapter,), armed_signals=(armed,)
            ).reconcile(runtime, NOW, EvaluationLimits(10))

            self.assertEqual((report.scanned, report.observed, report.degraded), (1, 0, 1))
            self.assertIsNone(runtime.source_checkpoint("filesystem", adapter.source_instance))

    def test_adapter_rejects_parent_escape_and_never_places_absolute_path_in_subject(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            with self.assertRaisesRegex(ValueError, "outside the configured root"):
                FilesystemSignalAdapter(base, "../secret.txt")
            nested = base / "folder" / "item.txt"
            adapter = FilesystemSignalAdapter(base, nested)
            self.assertEqual(adapter.subject, "path:folder/item.txt")
            self.assertNotIn(str(base), adapter.subject)

    def test_adapter_rejects_hostile_request_and_clause_subclasses(self) -> None:
        class SignalRequestSubclass(SignalRequest):
            pass

        class EqSubclass(Eq):
            def __eq__(self, other: object) -> bool:
                return True

        with tempfile.TemporaryDirectory() as tmp:
            adapter = FilesystemSignalAdapter(Path(tmp), "ready.flag")
            valid = adapter.request("created")
            request_subclass = SignalRequestSubclass(
                valid.contract_version,
                valid.source,
                valid.source_instance,
                valid.semantics,
                valid.kind,
                valid.subject,
                valid.condition,
                valid.where,
                valid.verification,
            )
            clause_subclass = SignalRequest(
                valid.contract_version,
                valid.source,
                valid.source_instance,
                valid.semantics,
                valid.kind,
                valid.subject,
                valid.condition,
                (EqSubclass("wrong", False),),
                valid.verification,
            )

            self.assertIsInstance(adapter.establish_anchor(request_subclass, NOW), Invalid)
            self.assertIsInstance(adapter.establish_anchor(clause_subclass, NOW), Invalid)

    def test_three_unchanged_reconciles_advance_checkpoint_without_receipts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            watched = base / "unchanged.txt"
            watched.write_text("same", encoding="utf-8")
            adapter = FilesystemSignalAdapter(base, watched)
            runtime, armed = self.register(base, base / "wake", adapter, "changed")
            runner = FilesystemSignalRunner((adapter,), armed_signals=(armed,))

            reports = [
                runner.reconcile(runtime, NOW, EvaluationLimits(10))
                for _ in range(3)
            ]
            outcome = runtime.evaluate(armed.wake_id, armed, NOW, EvaluationLimits(10))
            checkpoint = runtime.source_checkpoint("filesystem", adapter.source_instance)

            self.assertEqual([item.observed for item in reports], [0, 0, 0])
            self.assertEqual(outcome.outcome, "not_ready")
            self.assertEqual(outcome.scanned_through_sequence, 0)
            self.assertEqual(checkpoint.checkpoint_order, 3)

    def test_same_source_same_kind_arms_share_one_receipt_and_checkpoint(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            wake_root = base / "wake"
            adapter = FilesystemSignalAdapter(base, "shared.flag")
            runtime, first = self.register(
                base, wake_root, adapter, "created", "wake_first"
            )
            second_registration = EventWake(
                runtime,
                adapters=(adapter,),
                clock=lambda: NOW,
                id_factory=lambda: "wake_second",
            ).register(
                WakeIntent(
                    adapter.request("created"),
                    Resume(
                        "continue",
                        base,
                        MappingProxyType(
                            {"transport": "tmux", "tmux_socket": "/tmp/tmux", "pane": "%1"}
                        ),
                    ),
                ),
                idempotency_key="created-wake-second",
            )
            self.assertIsInstance(second_registration, Registration)
            second = runtime.load_armed_signal(second_registration.wake_id)
            (base / "shared.flag").write_text("ready", encoding="utf-8")

            report = FilesystemSignalRunner(
                (adapter,), armed_signals=(first, second)
            ).reconcile(runtime, NOW, EvaluationLimits(10))
            first_match = runtime.evaluate(first.wake_id, first, NOW, EvaluationLimits(10))
            second_match = runtime.evaluate(second.wake_id, second, NOW, EvaluationLimits(10))
            checkpoint = runtime.source_checkpoint("filesystem", adapter.source_instance)

            self.assertEqual((report.scanned, report.observed, report.degraded), (1, 1, 0))
            self.assertEqual(checkpoint.checkpoint_order, 1)
            self.assertEqual(first_match.outcome, "matched")
            self.assertEqual(second_match.outcome, "matched")
            self.assertEqual(
                first_match.receipt.receipt_id,
                second_match.receipt.receipt_id,
            )
            self.assertEqual(
                dict(first_match.receipt.attributes),
                dict(second_match.receipt.attributes),
            )

    def test_changed_transition_emits_once_then_quiesces(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            watched = base / "state.txt"
            watched.write_text("before", encoding="utf-8")
            adapter = FilesystemSignalAdapter(base, watched)
            runtime, armed = self.register(base, base / "wake", adapter, "changed")
            runner = FilesystemSignalRunner((adapter,), armed_signals=(armed,))

            before = runner.reconcile(runtime, NOW, EvaluationLimits(10))
            watched.write_text("after", encoding="utf-8")
            transition = runner.reconcile(runtime, NOW, EvaluationLimits(10))
            unchanged = runner.reconcile(runtime, NOW, EvaluationLimits(10))
            checkpoint = runtime.source_checkpoint("filesystem", adapter.source_instance)

            self.assertEqual(
                (before.observed, transition.observed, unchanged.observed),
                (0, 1, 0),
            )
            self.assertEqual(checkpoint.checkpoint_order, 3)
            matched = runtime.evaluate(armed.wake_id, armed, NOW, EvaluationLimits(10))
            self.assertEqual(matched.outcome, "matched")
            self.assertEqual(matched.receipt.local_sequence, 1)

    def test_distinct_kinds_share_one_source_commit_without_identity_collision(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            wake_root = base / "wake"
            adapter = FilesystemSignalAdapter(base, "shared.flag")
            runtime, created = self.register(
                base, wake_root, adapter, "created", "wake_created"
            )
            exists_registration = EventWake(
                runtime,
                adapters=(adapter,),
                clock=lambda: NOW,
                id_factory=lambda: "wake_exists",
            ).register(
                WakeIntent(
                    adapter.request("exists"),
                    Resume(
                        "continue",
                        base,
                        MappingProxyType(
                            {"transport": "tmux", "tmux_socket": "/tmp/tmux", "pane": "%1"}
                        ),
                    ),
                ),
                idempotency_key="exists-wake-exists",
            )
            self.assertIsInstance(exists_registration, Registration)
            exists = runtime.load_armed_signal(exists_registration.wake_id)
            (base / "shared.flag").touch()

            report = FilesystemSignalRunner(
                (adapter,), armed_signals=(created, exists)
            ).reconcile(runtime, NOW, EvaluationLimits(10))
            created_match = runtime.evaluate(
                created.wake_id, created, NOW, EvaluationLimits(10)
            )
            exists_match = runtime.evaluate(
                exists.wake_id, exists, NOW, EvaluationLimits(10)
            )

            self.assertEqual((report.scanned, report.observed), (1, 2))
            self.assertNotEqual(
                created_match.receipt.receipt_id,
                exists_match.receipt.receipt_id,
            )
            self.assertEqual(
                dict(created_match.receipt.attributes),
                dict(exists_match.receipt.attributes),
            )


if __name__ == "__main__":
    unittest.main()
