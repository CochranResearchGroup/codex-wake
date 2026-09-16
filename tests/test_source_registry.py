from __future__ import annotations

import json
import unittest
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
from unittest.mock import Mock

from codex_wake.records import WakePath
from codex_wake.signal_records import build_signal_record
from codex_wake.signals import ArmId, ArmedSignal, SourceAnchor, WakeId
from codex_wake.source_registry import (
    BuiltinSourceRegistration,
    BuiltinSourceRegistry,
    ReconstructionCandidate,
    ReconstructionContext,
)
from tests.test_signals import NOW, make_intent


def candidate(wake_id: str, *, source: str = "memory", kind: str = "job.completed",
              source_instance: str = "fixture") -> ReconstructionCandidate:
    intent = make_intent()
    armed = ArmedSignal(
        WakeId(wake_id), ArmId(f"arm_{wake_id}"),
        replace(intent.when, source=source, kind=kind, source_instance=source_instance),
        SourceAnchor(0, "fixture:0", {}, "local_journal"), NOW, None,
    )
    payload, _ = build_signal_record(armed, intent.resume, journal_uuid="fixture", revision=1)
    return ReconstructionCandidate(
        WakePath(Path("/unused/pending") / f"{wake_id}.json", json.loads(payload)), armed,
    )


class SourceRegistryTests(unittest.TestCase):
    def test_catalogue_is_immutable_and_introspection_never_constructs(self) -> None:
        factory = Mock(return_value=())
        ownership = {("memory", "job.completed")}
        registration = BuiltinSourceRegistration("memory", ownership, factory)
        registrations = [registration]
        registry = BuiltinSourceRegistry(registrations)
        ownership.clear()
        registrations.clear()

        self.assertEqual(registry.registrations, (registration,))
        self.assertEqual(registration.ownership, frozenset({("memory", "job.completed")}))
        for obj, field, value in (
            (registration, "registration_id", "other"),
            (registration, "ownership", frozenset()),
            (registry, "registrations", ()),
        ):
            with self.assertRaises(FrozenInstanceError):
                setattr(obj, field, value)
        factory.assert_not_called()

    def test_duplicate_ids_and_overlapping_ownership_fail_before_factories(self) -> None:
        factory = Mock(return_value=())
        first = BuiltinSourceRegistration("family", {("memory", "job.completed")}, factory)
        for second, message in (
            (BuiltinSourceRegistration("family", {("other", "done")}, factory),
             "duplicate registration id: family"),
            (BuiltinSourceRegistration("other", {("memory", "job.completed")}, factory),
             "overlapping source ownership: memory/job.completed"),
        ):
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                BuiltinSourceRegistry((first, second))
        factory.assert_not_called()

    def test_ownership_requires_nonempty_closed_source_kind_pairs(self) -> None:
        factory = Mock(return_value=())
        for identity, ownership in (
            ("", {("memory", "done")}), ("family", set()),
            ("family", {("memory", "")}), ("family", {("", "done")}),
            ("family", {"memory"}), ("family", {("memory", "done", "extra")}),
        ):
            with self.subTest(identity=identity, ownership=ownership), self.assertRaises(ValueError):
                BuiltinSourceRegistration(identity, ownership, factory)
        with self.assertRaises(TypeError):
            BuiltinSourceRegistration("family", {("memory", "done")}, None)
        factory.assert_not_called()

    def test_overlap_diagnostic_uses_stable_source_kind_order(self) -> None:
        factory = Mock(return_value=())
        ownership = {("z", "done"), ("a", "done")}
        for pairs in (ownership, tuple(reversed(sorted(ownership)))):
            with self.assertRaisesRegex(ValueError, "overlapping source ownership: a/done"):
                BuiltinSourceRegistry((
                    BuiltinSourceRegistration("first", pairs, factory),
                    BuiltinSourceRegistration("second", pairs, factory),
                ))
        factory.assert_not_called()

    def test_durable_identity_selects_one_complete_ordered_batch_per_family(self) -> None:
        items = (
            candidate("z", source_instance="z"),
            candidate("other", source="other"),
            candidate("a", kind="job.failed", source_instance="a"),
            candidate("unowned", kind="unknown"),
            candidate("unknown", source="unknown"),
        )
        # A projected predicate cannot grant another family ownership.
        items[0].pending.record["predicate"]["source"] = "other"
        items[0].pending.record["predicate"]["kind"] = "misleading"
        loader = Mock(side_effect={item.armed.wake_id: item.armed for item in items}.get)
        context = ReconstructionContext(Path("/unused"), loader, initial_reason="periodic")
        calls = []
        first_runner, second_runner, third_runner = Mock(), Mock(), Mock()

        def factory(name, runners):
            def construct(received_context, candidates):
                self.assertIs(received_context, context)
                self.assertIsInstance(candidates, tuple)
                calls.append((name, candidates))
                return runners
            return construct

        registry = BuiltinSourceRegistry((
            BuiltinSourceRegistration("other", {("other", "job.completed")},
                                      factory("other", (first_runner,))),
            BuiltinSourceRegistration("memory", {("memory", "job.completed"), ("memory", "job.failed")},
                                      factory("memory", (second_runner, third_runner))),
            BuiltinSourceRegistration("unused", {("unused", "done")}, Mock()),
        ))

        runners = registry.reconstruct(context, tuple(item.pending for item in items))

        self.assertEqual(runners, (first_runner, second_runner, third_runner))
        self.assertEqual(calls, [("other", (items[1],)), ("memory", (items[0], items[2]))])
        self.assertEqual(loader.call_count, len(items))
        registry.registrations[2].factory.assert_not_called()
        with self.assertRaises(FrozenInstanceError):
            context.initial_reason = "startup"
        with self.assertRaises(FrozenInstanceError):
            items[0].armed = items[1].armed

    def test_malformed_nonpending_missing_and_mismatched_arms_are_skipped(self) -> None:
        good = candidate("good")
        malformed = candidate("malformed")
        malformed.pending.record["cwd"] = None
        terminal = candidate("terminal")
        terminal.pending.record["status"] = "cancelled"
        missing = candidate("missing")
        broken = candidate("broken")
        wrong_wake = candidate("wrong_wake")
        wrong_arm = candidate("wrong_arm")
        prepared = candidate("prepared")
        arms = {
            "good": good.armed,
            "wrong_wake": good.armed,
            "wrong_arm": replace(wrong_arm.armed, arm_id=ArmId("different")),
            "prepared": replace(prepared.armed, publication="prepared"),
        }

        def load(wake_id):
            if wake_id == "broken":
                raise ValueError("malformed journal arm")
            return arms.get(wake_id)

        loader = Mock(side_effect=load)
        factory = Mock(return_value=())
        registry = BuiltinSourceRegistry((
            BuiltinSourceRegistration("memory", {("memory", "job.completed")}, factory),
        ))
        context = ReconstructionContext(Path("/unused"), loader)
        registry.reconstruct(context, tuple(item.pending for item in (
            malformed, terminal, missing, broken, wrong_wake, wrong_arm, prepared, good,
        )))

        factory.assert_called_once_with(context, (good,))
        self.assertEqual([call.args[0] for call in loader.call_args_list],
                         ["missing", "broken", "wrong_wake", "wrong_arm", "prepared", "good"])

    def test_factory_failure_is_isolated_without_retry_or_partial_runners(self) -> None:
        first, second = candidate("first"), candidate("second", source="other")
        loader = Mock(side_effect={"first": first.armed, "second": second.armed}.get)
        good_runner = Mock()

        def partial_failure(_context, _candidates):
            yield Mock()
            raise RuntimeError("construction failed")

        for failure in (RuntimeError("construction failed"), partial_failure):
            with self.subTest(failure=failure):
                broken = Mock(side_effect=failure)
                working = Mock(return_value=(good_runner,))
                registry = BuiltinSourceRegistry((
                    BuiltinSourceRegistration("broken", {("memory", "job.completed")}, broken),
                    BuiltinSourceRegistration("working", {("other", "job.completed")}, working),
                ))

                self.assertEqual(registry.reconstruct(
                    ReconstructionContext(Path("/unused"), loader), (first.pending, second.pending),
                ), (good_runner,))
                broken.assert_called_once()
                working.assert_called_once()
                good_runner.reconcile.assert_not_called()

    def test_process_interruptions_are_not_swallowed(self) -> None:
        item = candidate("interrupt")
        factory = Mock(side_effect=KeyboardInterrupt)
        registry = BuiltinSourceRegistry((
            BuiltinSourceRegistration("memory", {("memory", "job.completed")}, factory),
        ))
        with self.assertRaises(KeyboardInterrupt):
            registry.reconstruct(
                ReconstructionContext(Path("/unused"), lambda _wake_id: item.armed), (item.pending,),
            )
        factory.assert_called_once()

    def test_empty_catalogue_does_not_even_load_arms(self) -> None:
        loader = Mock()
        self.assertEqual(BuiltinSourceRegistry(()).reconstruct(
            ReconstructionContext(Path("/unused"), loader), (candidate("unused").pending,),
        ), ())
        loader.assert_not_called()
