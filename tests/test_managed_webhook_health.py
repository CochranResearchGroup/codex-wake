from __future__ import annotations

from dataclasses import FrozenInstanceError
import subprocess
import unittest
from unittest.mock import patch

from codex_wake.managed_webhook_health import (
    AggregateHealth, CleanupAction, CleanupEligibility, CleanupHistory, CleanupHistoryEvent,
    CleanupHistoryPhase, CleanupIntent, CleanupPlan, CleanupTombstone, CleanupTombstoneState,
    DispatchHealth, ListenerHealth, ManagedWebhookHealthCodec, PollingFallbackHealth,
    ProviderDeliveryHealth, ProviderObjectHealth, project_health,
)


FINGERPRINT = "a" * 64
OTHER_SAME_PREFIX_FINGERPRINT = "a" * 16 + "b" * 48
IDENTITY = {
    "owner_id": "wake-owner-1", "repository_id": 42, "hook_id": 44,
    "service_id": "codex-wake-webhook.service", "generation": 4,
    "desired_fingerprint": FINGERPRINT,
}


def health(**changes: object):
    values: dict[str, object] = {
        "generation": 4, "desired_fingerprint": FINGERPRINT,
        "local_listener": ListenerHealth.READY, "provider_object": ProviderObjectHealth.EXACT,
        "provider_delivery": ProviderDeliveryHealth.OBSERVED, "polling_fallback": PollingFallbackHealth.READY,
    }
    values.update(changes)
    return project_health(**values)


def intent(**changes: object) -> CleanupIntent:
    values: dict[str, object] = {**IDENTITY, "action": CleanupAction.DISABLE}
    values.update(changes)
    return CleanupIntent.create(**values)


class ManagedWebhookHealthProjectionTests(unittest.TestCase):
    def test_each_plane_is_distinct_and_c3_a_forces_dispatch_and_cleanup(self) -> None:
        projected = health()
        self.assertEqual(projected.aggregate, AggregateHealth.HEALTHY)
        self.assertEqual(projected.dispatch, DispatchHealth.NOT_INCLUDED)
        self.assertEqual(projected.cleanup_eligibility, CleanupEligibility.NOT_AUTHORIZED)

    def test_exact_provider_object_is_not_delivery_or_secret_proof(self) -> None:
        projected = health(provider_delivery=ProviderDeliveryHealth.UNPROVEN)
        self.assertEqual(projected.provider_object, ProviderObjectHealth.EXACT)
        self.assertEqual(projected.provider_delivery, ProviderDeliveryHealth.UNPROVEN)
        self.assertEqual(projected.aggregate, AggregateHealth.DEGRADED)
        self.assertNotIn("secret", ManagedWebhookHealthCodec.encode(projected).lower())

    def test_healthy_polling_leaves_webhook_trouble_degraded_and_polling_failure_visible(self) -> None:
        degraded = health(local_listener=ListenerHealth.DEGRADED, polling_fallback=PollingFallbackHealth.READY)
        failed_polling = health(polling_fallback=PollingFallbackHealth.UNAVAILABLE)
        self.assertEqual(degraded.aggregate, AggregateHealth.DEGRADED)
        self.assertEqual(failed_polling.polling_fallback, PollingFallbackHealth.UNAVAILABLE)
        self.assertEqual(failed_polling.aggregate, AggregateHealth.DEGRADED)

    def test_expanded_plane_vocabulary_projects_unobserved_and_blocked_without_effects(self) -> None:
        unobserved = health(
            local_listener=ListenerHealth.UNOBSERVED, provider_object=ProviderObjectHealth.UNOBSERVED,
            provider_delivery=ProviderDeliveryHealth.UNOBSERVED, polling_fallback=PollingFallbackHealth.UNOBSERVED,
        )
        blocked = health(local_listener=ListenerHealth.BLOCKED, polling_fallback=PollingFallbackHealth.DISABLED)
        self.assertEqual(unobserved.aggregate, AggregateHealth.UNOBSERVED)
        self.assertEqual(blocked.aggregate, AggregateHealth.BLOCKED)
        self.assertEqual(health(local_listener=ListenerHealth.DISABLED).aggregate, AggregateHealth.DEGRADED)
        self.assertEqual(health(polling_fallback=PollingFallbackHealth.DISABLED).aggregate, AggregateHealth.DEGRADED)
        self.assertEqual(health(provider_object=ProviderObjectHealth.DISABLED).aggregate, AggregateHealth.DEGRADED)
        self.assertEqual(health(provider_object=ProviderObjectHealth.DELETED).aggregate, AggregateHealth.DEGRADED)

    def test_c1_ambiguous_inventory_never_becomes_cleanup_eligible(self) -> None:
        for inventory in (ProviderObjectHealth.DUPLICATE, ProviderObjectHealth.COLLISION, ProviderObjectHealth.MISSING, ProviderObjectHealth.UNKNOWN):
            with self.subTest(inventory=inventory):
                self.assertEqual(health(provider_object=inventory).cleanup_eligibility, CleanupEligibility.NOT_AUTHORIZED)

    def test_projection_has_no_provider_service_or_external_effect(self) -> None:
        with patch.object(subprocess, "run", side_effect=AssertionError("external effect")):
            self.assertEqual(health().aggregate, AggregateHealth.HEALTHY)


class ManagedWebhookHealthCodecTests(unittest.TestCase):
    def test_codec_is_deterministic_round_trips_and_rejects_duplicate_or_raw_data(self) -> None:
        raw = ManagedWebhookHealthCodec.encode(health())
        self.assertEqual(ManagedWebhookHealthCodec.encode(health()), raw)
        self.assertEqual(ManagedWebhookHealthCodec.decode(raw), health())
        duplicate = raw.replace('"generation":4', '"generation":4,"generation":4', 1)
        for contaminated in (
            duplicate,
            raw[:-1] + ',"provider_response":{"token":"never-repeat"}}',
            raw.replace('"EXACT"', '"https://provider.invalid/hook"', 1),
            raw.replace('"EXACT"', '"C:\\\\portable-support-path"', 1),
        ):
            with self.subTest(contaminated=contaminated[:20]):
                with self.assertRaisesRegex(ValueError, "health data is invalid") as raised:
                    ManagedWebhookHealthCodec.decode(contaminated)
                self.assertNotIn("never-repeat", str(raised.exception))

    def test_redaction_never_returns_raw_value(self) -> None:
        self.assertEqual(ManagedWebhookHealthCodec.redact("token=never-repeat"), "REDACTED")


class CleanupModelTests(unittest.TestCase):
    def test_cleanup_records_bind_every_exact_identity_field_and_are_immutable(self) -> None:
        item = intent()
        plan = CleanupPlan(item, ProviderObjectHealth.EXACT)
        tombstone = CleanupTombstone.from_intent(item, state=CleanupTombstoneState.DISABLED_PROVEN)
        event = CleanupHistoryEvent.from_intent(1, item, CleanupHistoryPhase.INTENT_RECORDED)
        history = CleanupHistory(**IDENTITY, entries=(event,))
        self.assertEqual(plan.eligibility, CleanupEligibility.NOT_AUTHORIZED)
        for value in (item, plan, tombstone, history):
            self.assertEqual(ManagedWebhookHealthCodec.decode(ManagedWebhookHealthCodec.encode(value)), value)
        with self.assertRaises(FrozenInstanceError):
            item.hook_id = 45  # type: ignore[misc]

    def test_full_fingerprint_same_prefix_cannot_cross_bind_tombstone_or_history(self) -> None:
        first = intent()
        second = intent(desired_fingerprint=OTHER_SAME_PREFIX_FINGERPRINT)
        self.assertNotEqual(first.intent_id, second.intent_id)
        with self.assertRaisesRegex(ValueError, "health data is invalid"):
            CleanupTombstone(
                first.intent_id, **{**IDENTITY, "desired_fingerprint": OTHER_SAME_PREFIX_FINGERPRINT},
                action=CleanupAction.DISABLE, state=CleanupTombstoneState.DISABLED_PROVEN,
            )
        second_event = CleanupHistoryEvent.from_intent(1, second, CleanupHistoryPhase.INTENT_RECORDED)
        with self.assertRaisesRegex(ValueError, "health data is invalid"):
            CleanupHistory(**IDENTITY, entries=(second_event,))

    def test_each_exact_identity_component_changes_the_intent_identifier(self) -> None:
        first = intent()
        for changes in (
            {"owner_id": "other-owner"},
            {"repository_id": 43},
            {"hook_id": 45},
            {"service_id": "other-webhook.service"},
            {"generation": 5},
        ):
            with self.subTest(changes=changes):
                self.assertNotEqual(first.intent_id, intent(**changes).intent_id)

    def test_free_form_public_identifiers_reject_all_unsafe_markers_before_encoding(self) -> None:
        for field, value in (
            ("owner_id", "token-owner"),
            ("owner_id", "reference-owner"),
            ("owner_id", "payload-owner"),
            ("owner_id", "response-owner"),
            ("owner_id", "error-owner"),
            ("service_id", "secret-service"),
            ("service_id", "token-service"),
            ("service_id", "reference-service"),
            ("service_id", "payload-service"),
            ("service_id", "response-service"),
            ("service_id", "error-service"),
            ("service_id", "/portable-support-path"),
        ):
            with self.subTest(field=field, value=value):
                with self.assertRaisesRegex(ValueError, "health data is invalid") as raised:
                    intent(**{field: value})
                self.assertNotIn(value, str(raised.exception))

    def test_cleanup_models_reject_cross_identity_and_unbounded_history(self) -> None:
        item = intent()
        event = CleanupHistoryEvent.from_intent(1, item, CleanupHistoryPhase.PLAN_PREPARED)
        with self.assertRaisesRegex(ValueError, "health data is invalid"):
            CleanupHistory(**{**IDENTITY, "service_id": "other.service"}, entries=(event,))
        with self.assertRaisesRegex(ValueError, "health data is invalid"):
            CleanupHistory(**IDENTITY, entries=tuple(event for _ in range(33)))

    def test_cleanup_plan_remains_ineligible_for_all_c1_nonexact_states(self) -> None:
        item = intent()
        for inventory in (ProviderObjectHealth.DUPLICATE, ProviderObjectHealth.COLLISION, ProviderObjectHealth.MISSING, ProviderObjectHealth.UNKNOWN):
            with self.subTest(inventory=inventory):
                self.assertEqual(CleanupPlan(item, inventory).eligibility, CleanupEligibility.NOT_AUTHORIZED)


if __name__ == "__main__":
    unittest.main()
