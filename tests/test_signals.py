from __future__ import annotations

import unittest
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

from codex_wake.event_wake import EventWake
from codex_wake.signals import (
    ArmContext,
    ArmedSignal,
    Degraded,
    Eq,
    EvaluationLimits,
    Expired,
    In,
    InMemorySignalModule,
    Ingested,
    Invalid,
    Matched,
    NotReady,
    NormalizedObservation,
    Registration,
    Resume,
    ScriptedSourceAdapter,
    SignalRequest,
    SourceAnchor,
    SourceCommit,
    SourceContract,
    Verification,
    WakeId,
    WakeIntent,
)


NOW = datetime(2026, 9, 14, 14, 0, tzinfo=UTC)


def make_adapter() -> ScriptedSourceAdapter:
    return ScriptedSourceAdapter(
        SourceContract(
            source="memory",
            source_instance="contract-test",
            kinds=frozenset({"job.completed"}),
            subjects=frozenset({"job:42"}),
            allowed_attributes={"result": str, "attempt": int},
            max_clauses=2,
            max_in_values=3,
        ),
        anchor=SourceAnchor(
            local_after_sequence=0,
            source_anchor="memory:0",
            baseline={},
            recovery="local_journal",
        ),
    )


def make_intent(*, result: str = "ready", max_attempts: int = 3) -> WakeIntent:
    return WakeIntent(
        when=SignalRequest(
            contract_version=1,
            source="memory",
            source_instance="contract-test",
            semantics="occurrence",
            kind="job.completed",
            subject="job:42",
            condition="occurs",
            where=(Eq("result", result),),
        ),
        resume=Resume(
            prompt="Inspect the completed job.",
            cwd=Path("/tmp/repo"),
            target={"transport": "tmux", "tmux_socket": "/tmp/tmux/default", "pane": "%1"},
        ),
        max_attempts=max_attempts,
    )


def arm_signal(
    module: InMemorySignalModule,
    adapter: ScriptedSourceAdapter,
    *,
    wake_id: str = "wake_1",
    idempotency_key: str = "job-42",
    intent: WakeIntent | None = None,
) -> ArmedSignal:
    selected = intent or make_intent()
    result = module.arm(
        WakeId(wake_id),
        selected.when,
        ArmContext(
            idempotency_key=idempotency_key,
            intent_fingerprint=f"fingerprint:{idempotency_key}",
            registered_at=NOW,
            expires_at=selected.expires_at,
            resume=selected.resume,
            adapter=adapter,
        ),
    )
    if not isinstance(result, ArmedSignal):
        raise AssertionError(f"expected armed signal, got {result!r}")
    return result


class SignalContractTests(unittest.TestCase):
    def test_registration_is_idempotent_and_rejects_conflicting_intent(self) -> None:
        adapter = make_adapter()
        module = InMemorySignalModule()
        event_wake = EventWake(module, adapters=[adapter], clock=lambda: NOW, id_factory=lambda: "wake_1")

        first = event_wake.register(make_intent(), idempotency_key="job-42")
        replay = event_wake.register(make_intent(), idempotency_key="job-42")
        conflict = event_wake.register(make_intent(result="failed"), idempotency_key="job-42")
        delivery_conflict = event_wake.register(make_intent(max_attempts=1), idempotency_key="job-42")

        self.assertIsInstance(first, Registration)
        self.assertEqual(replay, first)
        self.assertIsInstance(conflict, Invalid)
        self.assertEqual(conflict.code, "IDEMPOTENCY_CONFLICT")
        self.assertIsInstance(delivery_conflict, Invalid)
        self.assertEqual(delivery_conflict.code, "IDEMPOTENCY_CONFLICT")
        self.assertEqual(adapter.anchor_calls, 1)

    def test_registration_rejects_out_of_range_attempt_bounds_before_arming(self) -> None:
        adapter = make_adapter()
        module = InMemorySignalModule()
        event_wake = EventWake(module, adapters=[adapter], clock=lambda: NOW, id_factory=lambda: "wake_1")

        for max_attempts in (0, 101):
            result = event_wake.register(
                make_intent(max_attempts=max_attempts),
                idempotency_key=f"attempts-{max_attempts}",
            )
            self.assertIsInstance(result, Invalid)
            self.assertEqual(result.code, "INVALID_SIGNAL")
        self.assertEqual(adapter.anchor_calls, 0)

    def test_registration_publishes_only_after_anchor_and_retries_reserved_identity(self) -> None:
        degraded = Degraded(None, "SOURCE_UNAVAILABLE", None)
        adapter = ScriptedSourceAdapter(
            make_adapter().contract(),
            anchors=[degraded, make_adapter().establish_anchor(make_intent().when, NOW)],
        )
        ids = iter(("wake_1", "wake_2"))
        event_wake = EventWake(InMemorySignalModule(), adapters=[adapter], clock=lambda: NOW, id_factory=lambda: next(ids))

        first = event_wake.register(make_intent(), idempotency_key="job-42")
        retry = event_wake.register(make_intent(), idempotency_key="job-42")

        self.assertIsInstance(first, Degraded)
        self.assertEqual(first.wake_id, "wake_1")
        self.assertIsInstance(retry, Registration)
        self.assertEqual(retry.wake_id, "wake_1")
        self.assertEqual(adapter.anchor_calls, 2)

    def test_ingest_deduplicates_one_logical_occurrence(self) -> None:
        module = InMemorySignalModule()
        event_wake = EventWake(module, adapters=[make_adapter()], clock=lambda: NOW, id_factory=lambda: "wake_1")
        self.assertIsInstance(event_wake.register(make_intent(), idempotency_key="job-42"), Registration)
        observation = NormalizedObservation(
            source="memory",
            source_instance="contract-test",
            kind="job.completed",
            subject="job:42",
            occurrence_namespace="job-run",
            occurrence_value="delivery-1",
            occurred_at=NOW,
            observed_at=NOW,
            attributes={"result": "ready", "attempt": 1},
            verification=Verification("verified", "scripted"),
            evidence_ref="memory:evidence:delivery-1",
        )

        first = module.ingest(
            [observation],
            SourceCommit("memory", "contract-test", "checkpoint-1", checkpoint_order=1, observed_through=NOW),
        )
        replay = module.ingest(
            [observation],
            SourceCommit("memory", "contract-test", "checkpoint-1", checkpoint_order=1, observed_through=NOW),
        )

        self.assertIsInstance(first, Ingested)
        self.assertFalse(first.receipts[0].duplicate)
        self.assertIsInstance(replay, Ingested)
        self.assertTrue(replay.receipts[0].duplicate)
        self.assertEqual(replay.receipts[0].receipt_id, first.receipts[0].receipt_id)
        self.assertEqual(replay.receipts[0].local_sequence, first.receipts[0].local_sequence)

    def test_conflicting_occurrence_rejects_the_whole_batch(self) -> None:
        module = InMemorySignalModule()
        event_wake = EventWake(module, adapters=[make_adapter()], clock=lambda: NOW, id_factory=lambda: "wake_1")
        self.assertIsInstance(event_wake.register(make_intent(), idempotency_key="job-42"), Registration)
        original = NormalizedObservation(
            source="memory",
            source_instance="contract-test",
            kind="job.completed",
            subject="job:42",
            occurrence_namespace="job-run",
            occurrence_value="delivery-1",
            occurred_at=NOW,
            observed_at=NOW,
            attributes={"result": "ready", "attempt": 1},
            verification=Verification("verified", "scripted"),
        )
        first = module.ingest([original], SourceCommit("memory", "contract-test", "c1", 1, NOW))
        self.assertIsInstance(first, Ingested)
        new_occurrence = replace(original, occurrence_value="delivery-2")
        conflicting = replace(original, attributes={"result": "failed", "attempt": 1})

        rejected = module.ingest(
            [new_occurrence, conflicting],
            SourceCommit("memory", "contract-test", "c2", 2, NOW),
        )
        after_rejection = module.ingest(
            [new_occurrence],
            SourceCommit("memory", "contract-test", "c2", 2, NOW),
        )

        self.assertIsInstance(rejected, Invalid)
        self.assertEqual(rejected.code, "OCCURRENCE_IDENTITY_CONFLICT")
        self.assertIsInstance(after_rejection, Ingested)
        self.assertFalse(after_rejection.receipts[0].duplicate)
        self.assertEqual(after_rejection.receipts[0].local_sequence, 2)

    def test_ingest_rejects_credential_shaped_attributes_without_echoing_values(self) -> None:
        module = InMemorySignalModule()
        event_wake = EventWake(module, adapters=[make_adapter()], clock=lambda: NOW, id_factory=lambda: "wake_1")
        self.assertIsInstance(event_wake.register(make_intent(), idempotency_key="job-42"), Registration)
        secret = "ghp_should_never_appear"
        unsafe = NormalizedObservation(
            source="memory",
            source_instance="contract-test",
            kind="job.completed",
            subject="job:42",
            occurrence_namespace="job-run",
            occurrence_value="delivery-1",
            occurred_at=NOW,
            observed_at=NOW,
            attributes={"result": "ready", "token": secret},
            verification=Verification("verified", "scripted"),
        )

        rejected = module.ingest([unsafe], SourceCommit("memory", "contract-test", "c1", 1, NOW))

        self.assertIsInstance(rejected, Invalid)
        self.assertEqual(rejected.code, "ATTRIBUTE_NOT_ALLOWED")
        self.assertNotIn(secret, repr(rejected))

    def test_ingest_copies_bounded_attributes_before_storing_evidence(self) -> None:
        module = InMemorySignalModule()
        adapter = make_adapter()
        armed = arm_signal(module, adapter)
        attributes = {"result": "ready", "attempt": 1}
        observation = NormalizedObservation(
            "memory",
            "contract-test",
            "job.completed",
            "job:42",
            "job-run",
            "delivery-immutable",
            NOW,
            NOW,
            attributes,
            Verification("verified", "scripted"),
        )

        ingested = module.ingest(
            [observation], SourceCommit("memory", "contract-test", "c1", 1, NOW)
        )
        attributes["result"] = "failed"
        matched = module.evaluate(WakeId("wake_1"), armed, NOW, EvaluationLimits(10))

        self.assertIsInstance(ingested, Ingested)
        self.assertIsInstance(matched, Matched)
        self.assertEqual(matched.receipt.attributes["result"], "ready")

    def test_ingest_rejects_oversized_attributes_before_commit(self) -> None:
        contract = replace(make_adapter().contract(), max_attribute_bytes=16)
        adapter = ScriptedSourceAdapter(
            contract,
            anchor=SourceAnchor(0, "memory:0", {}, "local_journal"),
        )
        module = InMemorySignalModule()
        arm_signal(module, adapter)
        oversized = NormalizedObservation(
            "memory",
            "contract-test",
            "job.completed",
            "job:42",
            "job-run",
            "oversized",
            NOW,
            NOW,
            {"result": "ready", "attempt": 123456789},
            Verification("verified", "scripted"),
        )

        rejected = module.ingest(
            [oversized], SourceCommit("memory", "contract-test", "c1", 1, NOW)
        )

        self.assertIsInstance(rejected, Invalid)
        self.assertEqual(rejected.code, "ATTRIBUTE_LIMIT_EXCEEDED")

    def test_ingest_rejects_observations_outside_the_source_contract(self) -> None:
        module = InMemorySignalModule()
        arm_signal(module, make_adapter())
        unsupported = NormalizedObservation(
            "memory",
            "contract-test",
            "job.unknown",
            "job:42",
            "job-run",
            "unsupported",
            NOW,
            NOW,
            {"result": "ready", "attempt": 1},
            Verification("verified", "scripted"),
        )

        rejected = module.ingest(
            [unsupported], SourceCommit("memory", "contract-test", "c1", 1, NOW)
        )

        self.assertIsInstance(rejected, Invalid)
        self.assertEqual(rejected.code, "OBSERVATION_OUTSIDE_CONTRACT")

    def test_occurrence_namespace_is_part_of_logical_identity(self) -> None:
        module = InMemorySignalModule()
        event_wake = EventWake(module, adapters=[make_adapter()], clock=lambda: NOW, id_factory=lambda: "wake_1")
        self.assertIsInstance(event_wake.register(make_intent(), idempotency_key="job-42"), Registration)
        base = NormalizedObservation(
            source="memory",
            source_instance="contract-test",
            kind="job.completed",
            subject="job:42",
            occurrence_namespace="poll",
            occurrence_value="run-7",
            occurred_at=NOW,
            observed_at=NOW,
            attributes={"result": "ready", "attempt": 1},
            verification=Verification("verified", "scripted"),
        )

        result = module.ingest(
            [base, replace(base, occurrence_namespace="webhook")],
            SourceCommit("memory", "contract-test", "c1", 1, NOW),
        )

        self.assertIsInstance(result, Ingested)
        self.assertNotEqual(result.receipts[0].receipt_id, result.receipts[1].receipt_id)

    def test_registration_rejects_invalid_contracts_before_anchor_effects(self) -> None:
        base = make_intent().when
        invalid_specs = (
            replace(base, contract_version=2),
            replace(base, source="other"),
            replace(base, source_instance="other"),
            replace(base, kind="job.unknown"),
            replace(base, subject="job:other"),
            replace(base, condition="holds"),
            replace(base, semantics="state", condition="occurs"),
            replace(base, where=(Eq("unknown", "ready"),)),
            replace(base, where=(Eq("attempt", "one"),)),
            replace(base, where=(In("result", ()),)),
            replace(base, where=(In("result", ("a", "b", "c", "d")),)),
            replace(base, where=(Eq("result", "ready"), Eq("attempt", 1), Eq("result", "ready"))),
        )

        for index, spec in enumerate(invalid_specs):
            with self.subTest(index=index):
                adapter = make_adapter()
                event_wake = EventWake(
                    InMemorySignalModule(),
                    adapters=[adapter],
                    clock=lambda: NOW,
                    id_factory=lambda: "wake_1",
                )
                result = event_wake.register(replace(make_intent(), when=spec), idempotency_key="job-42")
                self.assertIsInstance(result, Invalid)
                self.assertEqual(result.code, "INVALID_SIGNAL")
                self.assertEqual(adapter.anchor_calls, 0)

    def test_ingest_requires_matching_source_commit_and_nonregressing_checkpoint(self) -> None:
        module = InMemorySignalModule()
        event_wake = EventWake(module, adapters=[make_adapter()], clock=lambda: NOW, id_factory=lambda: "wake_1")
        self.assertIsInstance(event_wake.register(make_intent(), idempotency_key="job-42"), Registration)
        observation = NormalizedObservation(
            source="memory",
            source_instance="contract-test",
            kind="job.completed",
            subject="job:42",
            occurrence_namespace="job-run",
            occurrence_value="delivery-1",
            occurred_at=NOW,
            observed_at=NOW,
            attributes={"result": "ready", "attempt": 1},
            verification=Verification("verified", "scripted"),
        )

        mismatch = module.ingest([observation], SourceCommit("other", "contract-test", "bad", 1, NOW))
        accepted = module.ingest([observation], SourceCommit("memory", "contract-test", "c2", 2, NOW))
        regression = module.ingest([observation], SourceCommit("memory", "contract-test", "c1", 1, NOW))

        self.assertIsInstance(mismatch, Invalid)
        self.assertEqual(mismatch.code, "SOURCE_COMMIT_MISMATCH")
        self.assertIsInstance(accepted, Ingested)
        self.assertIsInstance(regression, Invalid)
        self.assertEqual(regression.code, "CHECKPOINT_REGRESSION")

    def test_evaluate_reserves_lowest_matching_receipt_and_replays_stably(self) -> None:
        module = InMemorySignalModule()
        armed = arm_signal(module, make_adapter())
        first_observation = NormalizedObservation(
            "memory",
            "contract-test",
            "job.completed",
            "job:42",
            "job-run",
            "delivery-1",
            NOW,
            NOW,
            {"result": "ready", "attempt": 1},
            Verification("verified", "scripted"),
            "memory:evidence:1",
        )
        second_observation = replace(first_observation, occurrence_value="delivery-2", evidence_ref="memory:evidence:2")
        ingested = module.ingest(
            [first_observation, second_observation],
            SourceCommit("memory", "contract-test", "c2", 2, NOW),
        )
        self.assertIsInstance(ingested, Ingested)

        first = module.evaluate(WakeId("wake_1"), armed, NOW, EvaluationLimits(max_candidates=10))
        replay = module.evaluate(WakeId("wake_1"), armed, NOW, EvaluationLimits(max_candidates=10))

        self.assertIsInstance(first, Matched)
        self.assertEqual(first.receipt.receipt_id, ingested.receipts[0].receipt_id)
        self.assertEqual(first, replay)
        with self.assertRaises(TypeError):
            first.receipt.attributes["result"] = "changed"  # type: ignore[index]

    def test_evaluate_returns_closed_outcomes_for_nonmatching_states(self) -> None:
        empty_module = InMemorySignalModule()
        empty_arm = arm_signal(empty_module, make_adapter())
        not_ready = empty_module.evaluate(WakeId("wake_1"), empty_arm, NOW, EvaluationLimits(10))
        invalid = empty_module.evaluate(WakeId("other"), empty_arm, NOW, EvaluationLimits(10))
        unpublished = empty_module.evaluate(
            WakeId("wake_1"), replace(empty_arm, publication="prepared"), NOW, EvaluationLimits(10)
        )

        expired_module = InMemorySignalModule()
        expired_intent = replace(make_intent(), expires_at=NOW)
        expired_arm = arm_signal(expired_module, make_adapter(), intent=expired_intent)
        expired = expired_module.evaluate(WakeId("wake_1"), expired_arm, NOW, EvaluationLimits(10))

        pending_module = InMemorySignalModule()
        pending_arm = arm_signal(pending_module, make_adapter())
        pending_observation = NormalizedObservation(
            "memory",
            "contract-test",
            "job.completed",
            "job:42",
            "job-run",
            "delivery-pending",
            NOW,
            NOW,
            {"result": "ready", "attempt": 1},
            Verification("pending", "scripted"),
        )
        pending_module.ingest(
            [pending_observation], SourceCommit("memory", "contract-test", "pending", 1, NOW)
        )
        pending = pending_module.evaluate(WakeId("wake_1"), pending_arm, NOW, EvaluationLimits(10))

        anchored_module = InMemorySignalModule()
        anchored_adapter = ScriptedSourceAdapter(
            make_adapter().contract(),
            anchor=SourceAnchor(1, "memory:1", {}, "local_journal"),
        )
        anchored = arm_signal(anchored_module, anchored_adapter)
        anchored_module.ingest(
            [replace(pending_observation, occurrence_value="at-anchor", verification=Verification("verified", "scripted"))],
            SourceCommit("memory", "contract-test", "anchor", 1, NOW),
        )
        at_anchor = anchored_module.evaluate(WakeId("wake_1"), anchored, NOW + timedelta(seconds=1), EvaluationLimits(10))

        self.assertIsInstance(not_ready, NotReady)
        self.assertIsInstance(invalid, Invalid)
        self.assertIsInstance(unpublished, Degraded)
        self.assertEqual(unpublished.code, "ARM_NOT_PUBLISHED")
        self.assertIsInstance(expired, Expired)
        self.assertIsInstance(pending, Degraded)
        self.assertEqual(pending.code, "VERIFICATION_PENDING")
        self.assertIsInstance(at_anchor, NotReady)

    def test_evaluate_enforces_evidence_projection_limits(self) -> None:
        module = InMemorySignalModule()
        armed = arm_signal(module, make_adapter())
        observation = NormalizedObservation(
            "memory",
            "contract-test",
            "job.completed",
            "job:42",
            "job-run",
            "bounded",
            NOW,
            NOW,
            {"result": "ready", "attempt": 1},
            Verification("verified", "scripted"),
            "memory:evidence:bounded",
        )
        module.ingest(
            [observation], SourceCommit("memory", "contract-test", "c1", 1, NOW)
        )

        result = module.evaluate(
            WakeId("wake_1"),
            armed,
            NOW,
            EvaluationLimits(
                max_candidates=10,
                max_attribute_bytes=8,
                max_evidence_ref_bytes=8,
            ),
        )

        self.assertIsInstance(result, Degraded)
        self.assertEqual(result.code, "EVALUATION_BUDGET_EXHAUSTED")

    def test_one_receipt_matches_two_wakes_with_bounded_in_filter(self) -> None:
        module = InMemorySignalModule()
        adapter = make_adapter()
        intent = replace(
            make_intent(),
            when=replace(make_intent().when, where=(In("result", ("ready", "done")),)),
        )
        first_arm = arm_signal(
            module,
            adapter,
            wake_id="wake_1",
            idempotency_key="first",
            intent=intent,
        )
        second_arm = arm_signal(
            module,
            adapter,
            wake_id="wake_2",
            idempotency_key="second",
            intent=intent,
        )
        observation = NormalizedObservation(
            "memory",
            "contract-test",
            "job.completed",
            "job:42",
            "job-run",
            "fan-out",
            NOW,
            NOW,
            {"result": "ready", "attempt": 1},
            Verification("verified", "scripted"),
        )
        ingested = module.ingest(
            [observation], SourceCommit("memory", "contract-test", "c1", 1, NOW)
        )

        first = module.evaluate(WakeId("wake_1"), first_arm, NOW, EvaluationLimits(10))
        second = module.evaluate(WakeId("wake_2"), second_arm, NOW, EvaluationLimits(10))

        self.assertIsInstance(ingested, Ingested)
        self.assertIsInstance(first, Matched)
        self.assertIsInstance(second, Matched)
        self.assertEqual(first.receipt.receipt_id, second.receipt.receipt_id)
        self.assertNotEqual(first.match_token, second.match_token)

    def test_evaluation_isolates_source_instances(self) -> None:
        module = InMemorySignalModule()
        target_arm = arm_signal(module, make_adapter())
        other_contract = replace(make_adapter().contract(), source_instance="other")
        other_adapter = ScriptedSourceAdapter(
            other_contract,
            anchor=SourceAnchor(0, "other:0", {}, "local_journal"),
        )
        other_intent = replace(
            make_intent(),
            when=replace(make_intent().when, source_instance="other"),
        )
        arm_signal(
            module,
            other_adapter,
            wake_id="wake_other",
            idempotency_key="other",
            intent=other_intent,
        )
        other_observation = NormalizedObservation(
            "memory",
            "other",
            "job.completed",
            "job:42",
            "job-run",
            "same-logical-id",
            NOW,
            NOW,
            {"result": "ready", "attempt": 1},
            Verification("verified", "scripted"),
        )
        target_observation = replace(other_observation, source_instance="contract-test")
        other_ingest = module.ingest(
            [other_observation], SourceCommit("memory", "other", "other:1", 1, NOW)
        )
        target_ingest = module.ingest(
            [target_observation],
            SourceCommit("memory", "contract-test", "target:1", 1, NOW),
        )

        matched = module.evaluate(
            WakeId("wake_1"), target_arm, NOW, EvaluationLimits(10)
        )

        self.assertIsInstance(other_ingest, Ingested)
        self.assertIsInstance(target_ingest, Ingested)
        self.assertIsInstance(matched, Matched)
        self.assertEqual(matched.receipt.receipt_id, target_ingest.receipts[0].receipt_id)


if __name__ == "__main__":
    unittest.main()
