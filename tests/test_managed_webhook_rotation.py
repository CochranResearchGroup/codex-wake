from __future__ import annotations

import json
import multiprocessing
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import codex_wake.managed_webhook_rotation as rotation
from codex_wake.managed_webhook_rotation import (
    ManagedWebhookRotationCoordinator,
    ManagedWebhookRotationStore,
    Observation,
    PendingEffect,
    RotationPhase,
    RotationRecord,
    RuntimeProof,
)


def record(root: Path, **changes: object) -> RotationRecord:
    values: dict[str, object] = {
        "owner_id": "wake-owner-1",
        "canonical_root": str(root.resolve()),
        "owner_uid": os.getuid(),
        "source_instance": "github-workflow",
        "service_id": "codex-wake-github-webhook-github-workflow.service",
        "binding_revision": 11,
        "previous_generation": 7,
        "target_generation": 8,
        "overlap_deadline": 200,
    }
    values.update(changes)
    return RotationRecord(**values)


def proof(**changes: object) -> RuntimeProof:
    values: dict[str, object] = {
        "process_id": 123,
        "process_started_at": 101,
        "authority_revision": 11,
        "loaded_generations": (7, 8),
        "evidence_locator": "runtime-42",
    }
    values.update(changes)
    return RuntimeProof(**values)


def competing_save(root: str, ready, release, results) -> None:
    store = ManagedWebhookRotationStore(Path(root))
    current = store.load("wake-owner-1")
    ready.put(True)
    release.wait(5)
    try:
        ManagedWebhookRotationCoordinator(store).intend_dual_restart(
            "wake-owner-1", expected_revision=current.revision, now=101,
        )
        results.put("saved")
    except ValueError as exc:
        results.put(str(exc))


class ManagedWebhookRotationStoreTests(unittest.TestCase):
    def test_deterministic_secret_free_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "wake"
            store = ManagedWebhookRotationStore(root)
            saved = store.save(record(root))
            self.assertEqual(store.load("wake-owner-1"), saved)
            rendered = store.path.read_text(encoding="utf-8")
            self.assertEqual(rendered, json.dumps(json.loads(rendered), sort_keys=True, separators=(",", ":")) + "\n")
            self.assertNotIn("secret", rendered.lower())
            self.assertNotIn("token", rendered.lower())
            self.assertNotIn("payload", rendered.lower())
            self.assertEqual(saved.summary()["target_generation"], 8)
            self.assertNotIn("runtime-42", json.dumps(saved.summary()))

    def test_rejects_duplicate_keys_foreign_root_symlink_and_uid(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "wake"
            store = ManagedWebhookRotationStore(root)
            store.save(record(root))
            store.path.write_text('{"schema_version":1,"schema_version":1,"records":[]}', encoding="utf-8")
            store.path.chmod(0o600)
            with self.assertRaisesRegex(ValueError, "store is invalid"):
                store.records()

            linked = ManagedWebhookRotationStore(Path(temporary) / "linked")
            linked.path.parent.mkdir(parents=True)
            target = Path(temporary) / "target"
            target.write_text("unchanged", encoding="utf-8")
            linked._lock_path.symlink_to(target)
            with self.assertRaisesRegex(ValueError, "store is unavailable"):
                linked.save(record(linked.wake_root))
            self.assertEqual(target.read_text(encoding="utf-8"), "unchanged")

            root_link = Path(temporary) / "root-link"
            root_link.symlink_to(root, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "root is invalid"):
                ManagedWebhookRotationStore(root_link)

            copied = ManagedWebhookRotationStore(Path(temporary) / "copied")
            copied.path.parent.mkdir(parents=True)
            copied.path.write_text(json.dumps({"schema_version": 1, "records": [record(root).to_dict()]}), encoding="utf-8")
            copied.path.chmod(0o600)
            with self.assertRaisesRegex(ValueError, "store is invalid"):
                copied.records()
            with patch.object(rotation.os, "getuid", return_value=os.getuid() + 1):
                with self.assertRaisesRegex(ValueError, "store is unavailable"):
                    store.records()

    def test_stale_revision_immutable_facts_and_cross_process_locking(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "wake"
            store = ManagedWebhookRotationStore(root)
            initial = store.save(record(root))
            with self.assertRaisesRegex(ValueError, "revision is stale"):
                store.save(initial, expected_revision=9)
            with self.assertRaisesRegex(ValueError, "ownership is immutable"):
                store.save(record(root, target_generation=9), expected_revision=initial.revision)

            context = multiprocessing.get_context("fork")
            ready, release, results = context.Queue(), context.Event(), context.Queue()
            processes = [context.Process(target=competing_save, args=(str(root), ready, release, results)) for _ in range(2)]
            for process in processes:
                process.start()
            self.assertTrue(ready.get(timeout=5))
            self.assertTrue(ready.get(timeout=5))
            release.set()
            outcomes = sorted(results.get(timeout=5) for _ in processes)
            for process in processes:
                process.join(timeout=5)
                self.assertEqual(process.exitcode, 0)
            self.assertEqual(outcomes, ["managed webhook rotation revision is stale", "saved"])


class ManagedWebhookRotationCoordinatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "wake"
        self.store = ManagedWebhookRotationStore(self.root)
        self.coordinator = ManagedWebhookRotationCoordinator(self.store)
        self.current = self.coordinator.begin(record(self.root), now=100)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def dual_ready(self) -> RotationRecord:
        self.current = self.coordinator.intend_dual_restart("wake-owner-1", expected_revision=self.current.revision, now=101)
        self.assertEqual((self.current.phase, self.current.pending_effect), (RotationPhase.PREPARED, PendingEffect.RESTART_DUAL))
        self.current = self.coordinator.observe_dual_restart("wake-owner-1", expected_revision=self.current.revision, proof=proof(), now=102)
        self.assertEqual(self.coordinator.admitted_generations("wake-owner-1", now=102), (7, 8))
        return self.current

    def provider_ready(self) -> RotationRecord:
        self.dual_ready()
        self.current = self.coordinator.intend_provider_update("wake-owner-1", expected_revision=self.current.revision, now=103)
        self.assertEqual((self.current.phase, self.current.pending_effect), (RotationPhase.PROVIDER_PENDING, PendingEffect.PROVIDER_UPDATE))
        self.current = self.coordinator.observe_provider_update("wake-owner-1", expected_revision=self.current.revision, observation=Observation.PROVED, now=104)
        return self.current

    def test_full_six_phase_intent_before_effect_and_idempotent_resume(self) -> None:
        self.provider_ready()
        self.current = self.coordinator.record_delivery("wake-owner-1", expected_revision=self.current.revision, generation=8, journal_locator="journal-42", now=105)
        self.assertEqual(self.current.phase, RotationPhase.AWAITING_DELIVERY)
        with self.assertRaisesRegex(ValueError, "runtime proof is required"):
            self.coordinator.intend_retirement("wake-owner-1", expected_revision=self.current.revision, now=106)
        self.current = self.coordinator.intend_target_restart(
            "wake-owner-1", expected_revision=self.current.revision, now=106,
        )
        self.current = self.coordinator.observe_target_restart(
            "wake-owner-1", expected_revision=self.current.revision,
            proof=proof(process_started_at=106, loaded_generations=(8,), evidence_locator="runtime-43"), now=107,
        )
        self.assertEqual(self.coordinator.admitted_generations("wake-owner-1", now=107), (8,))
        self.current = self.coordinator.intend_retirement("wake-owner-1", expected_revision=self.current.revision, now=108)
        self.assertEqual((self.current.phase, self.current.pending_effect), (RotationPhase.RETIRING, PendingEffect.RETIRE_PREVIOUS))
        completed = self.coordinator.observe_retirement("wake-owner-1", expected_revision=self.current.revision, observation=Observation.PROVED, now=109)
        self.assertEqual(completed.phase, RotationPhase.COMPLETE)
        self.assertEqual(completed.terminal_code, "RETIRED")
        self.assertEqual(self.coordinator.observe_retirement("wake-owner-1", expected_revision=completed.revision, observation=Observation.PROVED, now=109), completed)

    def test_crash_boundaries_do_not_repeat_or_skip_effects(self) -> None:
        pending = self.coordinator.intend_dual_restart("wake-owner-1", expected_revision=self.current.revision, now=101)
        resumed = ManagedWebhookRotationCoordinator(ManagedWebhookRotationStore(self.root)).load("wake-owner-1", now=101)
        self.assertEqual(resumed, pending)
        self.assertEqual(resumed.pending_effect, PendingEffect.RESTART_DUAL)
        self.assertEqual(
            self.coordinator.intend_dual_restart("wake-owner-1", expected_revision=resumed.revision, now=101),
            resumed,
        )

        self.current = self.coordinator.observe_dual_restart("wake-owner-1", expected_revision=resumed.revision, proof=proof(), now=102)
        self.current = self.coordinator.intend_provider_update("wake-owner-1", expected_revision=self.current.revision, now=103)
        uncertain = self.coordinator.observe_provider_update("wake-owner-1", expected_revision=self.current.revision, observation=Observation.UNKNOWN, now=104)
        self.assertEqual(uncertain.phase, RotationPhase.UNKNOWN)
        with self.assertRaisesRegex(ValueError, "not actionable"):
            self.coordinator.intend_provider_update("wake-owner-1", expected_revision=uncertain.revision, now=104)

    def test_bad_runtime_and_delivery_proofs_fail_closed(self) -> None:
        self.current = self.coordinator.intend_dual_restart("wake-owner-1", expected_revision=self.current.revision, now=101)
        unknown = self.coordinator.observe_dual_restart("wake-owner-1", expected_revision=self.current.revision, proof=proof(loaded_generations=(8,)), now=102)
        self.assertEqual((unknown.phase, unknown.terminal_code), (RotationPhase.UNKNOWN, "RUNTIME_PROOF_REJECTED"))

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "wake"
            coordinator = ManagedWebhookRotationCoordinator(ManagedWebhookRotationStore(root))
            current = coordinator.begin(record(root), now=100)
            current = coordinator.intend_dual_restart("wake-owner-1", expected_revision=current.revision, now=101)
            current = coordinator.observe_dual_restart("wake-owner-1", expected_revision=current.revision, proof=proof(), now=102)
            current = coordinator.intend_provider_update("wake-owner-1", expected_revision=current.revision, now=103)
            current = coordinator.observe_provider_update("wake-owner-1", expected_revision=current.revision, observation=Observation.PROVED, now=104)
            with self.assertRaisesRegex(ValueError, "delivery proof is invalid"):
                coordinator.record_delivery("wake-owner-1", expected_revision=current.revision, generation=7, journal_locator="journal-42", now=105)

    def test_expiry_admission_backward_clock_and_rollback(self) -> None:
        self.assertEqual(self.coordinator.admitted_generations("wake-owner-1", now=100), (7,))
        with self.assertRaisesRegex(ValueError, "clock moved backwards"):
            self.coordinator.load("wake-owner-1", now=99)
        self.assertEqual(self.coordinator.admitted_generations("wake-owner-1", now=201), ())
        expired = self.store.load("wake-owner-1")
        self.assertEqual(expired.phase, RotationPhase.EXPIRED)
        self.assertEqual(self.coordinator.admitted_generations("wake-owner-1", now=201), ())
        self.assertEqual(self.store.load("wake-owner-1").revision, expired.revision)
        with self.assertRaisesRegex(ValueError, "clock moved backwards"):
            self.coordinator.admitted_generations("wake-owner-1", now=200)
        rollback = self.coordinator.rollback("wake-owner-1", expected_revision=expired.revision, now=202)
        self.assertEqual(rollback.pending_effect, PendingEffect.ROLLBACK)
        rolled_back = self.coordinator.observe_rollback("wake-owner-1", expected_revision=rollback.revision, observation=Observation.PROVED, now=203)
        self.assertEqual(rolled_back.phase, RotationPhase.ROLLED_BACK)
        self.assertEqual(self.coordinator.admitted_generations("wake-owner-1", now=500), (7,))

    def test_terminal_admission_survives_old_overlap_deadline(self) -> None:
        self.provider_ready()
        self.current = self.coordinator.record_delivery("wake-owner-1", expected_revision=self.current.revision, generation=8, journal_locator="journal-42", now=105)
        self.current = self.coordinator.intend_target_restart("wake-owner-1", expected_revision=self.current.revision, now=106)
        self.current = self.coordinator.observe_target_restart("wake-owner-1", expected_revision=self.current.revision, proof=proof(process_started_at=106, loaded_generations=(8,), evidence_locator="runtime-43"), now=107)
        self.current = self.coordinator.intend_retirement("wake-owner-1", expected_revision=self.current.revision, now=108)
        complete = self.coordinator.observe_retirement("wake-owner-1", expected_revision=self.current.revision, observation=Observation.PROVED, now=109)
        self.assertEqual(self.coordinator.admitted_generations("wake-owner-1", now=500), (8,))
        self.assertEqual(self.store.load("wake-owner-1"), complete)

    def test_pending_rollback_fences_every_forward_operation(self) -> None:
        self.provider_ready()
        self.current = self.coordinator.record_delivery("wake-owner-1", expected_revision=self.current.revision, generation=8, journal_locator="journal-42", now=105)
        rollback = self.coordinator.rollback("wake-owner-1", expected_revision=self.current.revision, now=106)
        with self.assertRaisesRegex(ValueError, "rollback is pending"):
            self.coordinator.intend_target_restart("wake-owner-1", expected_revision=rollback.revision, now=106)
        with self.assertRaisesRegex(ValueError, "rollback is pending"):
            self.coordinator.record_target_runtime("wake-owner-1", expected_revision=rollback.revision, proof=proof(loaded_generations=(8,)), now=106)
        with self.assertRaisesRegex(ValueError, "rollback is pending"):
            self.coordinator.intend_retirement("wake-owner-1", expected_revision=rollback.revision, now=106)

    def test_rollback_uncertainty_is_durable_from_expired_origin(self) -> None:
        expired = self.coordinator.expire("wake-owner-1", expected_revision=self.current.revision, now=201)
        rollback = self.coordinator.rollback("wake-owner-1", expected_revision=expired.revision, now=202)
        unknown = self.coordinator.observe_rollback("wake-owner-1", expected_revision=rollback.revision, observation=Observation.UNKNOWN, now=203)
        self.assertEqual((unknown.phase, unknown.pending_effect, unknown.terminal_code), (RotationPhase.UNKNOWN, PendingEffect.NONE, "ROLLBACK_UNKNOWN"))
        self.assertEqual(self.store.load("wake-owner-1"), unknown)

    def test_store_cannot_bypass_intent_or_phase_specific_proof(self) -> None:
        with self.assertRaisesRegex(ValueError, "transition is invalid"):
            self.store.save(
                record(self.root, phase=RotationPhase.DUAL_READY, runtime_proof=proof(), effect_revision=1),
                expected_revision=self.current.revision,
            )
        with self.assertRaisesRegex(ValueError, "record is invalid"):
            RotationRecord.from_dict({
                **record(self.root).to_dict(), "phase": "PROVIDER_PENDING", "pending_effect": "NONE",
                "runtime_proof": proof().to_dict(), "effect_revision": 1,
            })

    def test_successor_retains_terminal_evidence_and_rejects_active_or_unknown(self) -> None:
        with self.assertRaisesRegex(ValueError, "terminal predecessor"):
            self.coordinator.begin_successor("wake-owner-1", expected_revision=self.current.revision, binding_revision=12, target_generation=9, overlap_deadline=300, now=101)
        self.provider_ready()
        self.current = self.coordinator.record_delivery("wake-owner-1", expected_revision=self.current.revision, generation=8, journal_locator="journal-42", now=105)
        self.current = self.coordinator.intend_target_restart("wake-owner-1", expected_revision=self.current.revision, now=106)
        self.current = self.coordinator.observe_target_restart("wake-owner-1", expected_revision=self.current.revision, proof=proof(process_started_at=106, loaded_generations=(8,), evidence_locator="runtime-43"), now=107)
        self.current = self.coordinator.intend_retirement("wake-owner-1", expected_revision=self.current.revision, now=108)
        complete = self.coordinator.observe_retirement("wake-owner-1", expected_revision=self.current.revision, observation=Observation.PROVED, now=109)
        successor = self.coordinator.begin_successor("wake-owner-1", expected_revision=complete.revision, binding_revision=12, target_generation=9, overlap_deadline=300, now=110)
        self.assertEqual((successor.phase, successor.previous_generation, successor.target_generation), (RotationPhase.PREPARED, 8, 9))
        self.assertEqual(successor.terminal_history[-1].phase, RotationPhase.COMPLETE)
        self.assertEqual(successor.terminal_history[-1].revision, complete.revision)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "wake"
            coordinator = ManagedWebhookRotationCoordinator(ManagedWebhookRotationStore(root))
            current = coordinator.begin(record(root), now=100)
            current = coordinator.intend_dual_restart("wake-owner-1", expected_revision=current.revision, now=101)
            unknown = coordinator.observe_dual_restart("wake-owner-1", expected_revision=current.revision, proof=proof(loaded_generations=(8,)), now=102)
            with self.assertRaisesRegex(ValueError, "terminal predecessor"):
                coordinator.begin_successor("wake-owner-1", expected_revision=unknown.revision, binding_revision=12, target_generation=9, overlap_deadline=300, now=103)

    def test_target_restart_requires_intent_and_provider_ambiguity_never_reopens_write(self) -> None:
        self.provider_ready()
        self.current = self.coordinator.record_delivery("wake-owner-1", expected_revision=self.current.revision, generation=8, journal_locator="journal-42", now=105)
        with self.assertRaisesRegex(ValueError, "target runtime is not awaited"):
            self.coordinator.observe_target_restart("wake-owner-1", expected_revision=self.current.revision, proof=proof(loaded_generations=(8,)), now=106)
        self.current = self.coordinator.intend_target_restart("wake-owner-1", expected_revision=self.current.revision, now=106)
        self.assertEqual(self.coordinator.intend_target_restart("wake-owner-1", expected_revision=self.current.revision, now=106), self.current)

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "wake"
            coordinator = ManagedWebhookRotationCoordinator(ManagedWebhookRotationStore(root))
            current = coordinator.begin(record(root), now=100)
            current = coordinator.intend_dual_restart("wake-owner-1", expected_revision=current.revision, now=101)
            current = coordinator.observe_dual_restart("wake-owner-1", expected_revision=current.revision, proof=proof(), now=102)
            pending = coordinator.intend_provider_update("wake-owner-1", expected_revision=current.revision, now=103)
            self.assertEqual(coordinator.intend_provider_update("wake-owner-1", expected_revision=pending.revision, now=103), pending)
            unknown = coordinator.observe_provider_update("wake-owner-1", expected_revision=pending.revision, observation=Observation.UNKNOWN, now=104)
            with self.assertRaisesRegex(ValueError, "not actionable"):
                coordinator.intend_provider_update("wake-owner-1", expected_revision=unknown.revision, now=104)

    def test_rollback_can_finish_from_a_pending_effect_without_replaying_it(self) -> None:
        pending = self.coordinator.intend_dual_restart("wake-owner-1", expected_revision=self.current.revision, now=101)
        rollback = self.coordinator.rollback("wake-owner-1", expected_revision=pending.revision, now=102)
        self.assertEqual((rollback.phase, rollback.pending_effect), (RotationPhase.PREPARED, PendingEffect.ROLLBACK))
        finished = self.coordinator.observe_rollback("wake-owner-1", expected_revision=rollback.revision, observation=Observation.PROVED, now=103)
        self.assertEqual(finished.phase, RotationPhase.ROLLED_BACK)

    def test_stale_revision_does_not_mutate_current_record(self) -> None:
        stale = self.current.revision
        self.current = self.coordinator.intend_dual_restart("wake-owner-1", expected_revision=stale, now=101)
        with self.assertRaisesRegex(ValueError, "revision is stale"):
            self.coordinator.observe_dual_restart("wake-owner-1", expected_revision=stale, proof=proof(), now=102)
        self.assertEqual(self.store.load("wake-owner-1"), self.current)


if __name__ == "__main__":
    unittest.main()
