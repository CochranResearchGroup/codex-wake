"""Pure, secret-free managed-webhook health and future-cleanup records.

No provider, listener, service, process, or dispatch client is imported here.
Inputs are already-sanitized observations. An exact provider object is not a
delivery or secret proof, and C3-A never authorizes cleanup or dispatch.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import re


_FINGERPRINT = re.compile(r"[0-9a-f]{64}")
_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,95}")
_MAX_JSON_BYTES = 16_384
_MAX_HISTORY = 32
_MAX_GENERATION = 2**63


class ListenerHealth(str, Enum):
    UNOBSERVED = "UNOBSERVED"
    READY = "READY"
    DEGRADED = "DEGRADED"
    BLOCKED = "BLOCKED"
    DISABLED = "DISABLED"
    UNAVAILABLE = "UNAVAILABLE"
    UNKNOWN = "UNKNOWN"


class ProviderObjectHealth(str, Enum):
    """Sanitized C1 inventory classification, never delivery proof."""
    UNOBSERVED = "UNOBSERVED"
    EXACT = "EXACT"
    ABSENT = "ABSENT"
    DUPLICATE = "DUPLICATE"
    DRIFTED = "DRIFTED"
    COLLISION = "COLLISION"
    MISSING = "MISSING"
    DISABLED = "DISABLED"
    DELETED = "DELETED"
    BLOCKED = "BLOCKED"
    UNKNOWN = "UNKNOWN"


class ProviderDeliveryHealth(str, Enum):
    UNOBSERVED = "UNOBSERVED"
    UNPROVEN = "UNPROVEN"
    OBSERVED = "OBSERVED"
    BLOCKED = "BLOCKED"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"
    UNKNOWN = "UNKNOWN"


class PollingFallbackHealth(str, Enum):
    UNOBSERVED = "UNOBSERVED"
    READY = "READY"
    DEGRADED = "DEGRADED"
    BLOCKED = "BLOCKED"
    DISABLED = "DISABLED"
    UNAVAILABLE = "UNAVAILABLE"
    UNKNOWN = "UNKNOWN"


class DispatchHealth(str, Enum):
    NOT_INCLUDED = "NOT_INCLUDED"


class AggregateHealth(str, Enum):
    UNOBSERVED = "UNOBSERVED"
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    BLOCKED = "BLOCKED"
    UNKNOWN = "UNKNOWN"


class CleanupEligibility(str, Enum):
    NOT_AUTHORIZED = "NOT_AUTHORIZED"


class CleanupAction(str, Enum):
    DISABLE = "DISABLE"
    DELETE = "DELETE"


class CleanupTombstoneState(str, Enum):
    DISABLED_PROVEN = "DISABLED_PROVEN"
    DELETED_PROVEN = "DELETED_PROVEN"
    UNKNOWN = "UNKNOWN"


class CleanupHistoryPhase(str, Enum):
    INTENT_RECORDED = "INTENT_RECORDED"
    PLAN_PREPARED = "PLAN_PREPARED"
    TOMBSTONE_RETAINED = "TOMBSTONE_RETAINED"
    UNKNOWN = "UNKNOWN"


def project_health(*, generation: int, desired_fingerprint: str, local_listener: ListenerHealth,
                   provider_object: ProviderObjectHealth, provider_delivery: ProviderDeliveryHealth,
                   polling_fallback: PollingFallbackHealth) -> "ManagedWebhookHealth":
    """Project only supplied observations; this function has no external effect."""
    return ManagedWebhookHealth(
        generation, desired_fingerprint, local_listener, provider_object, provider_delivery, polling_fallback,
        DispatchHealth.NOT_INCLUDED, _aggregate(local_listener, provider_object, provider_delivery, polling_fallback),
        CleanupEligibility.NOT_AUTHORIZED,
    )


@dataclass(frozen=True, slots=True)
class ManagedWebhookHealth:
    generation: int
    desired_fingerprint: str
    local_listener: ListenerHealth
    provider_object: ProviderObjectHealth
    provider_delivery: ProviderDeliveryHealth
    polling_fallback: PollingFallbackHealth
    dispatch: DispatchHealth
    aggregate: AggregateHealth
    cleanup_eligibility: CleanupEligibility

    def __post_init__(self) -> None:
        if (
            not _valid_generation_fingerprint(self.generation, self.desired_fingerprint)
            or not isinstance(self.local_listener, ListenerHealth) or not isinstance(self.provider_object, ProviderObjectHealth)
            or not isinstance(self.provider_delivery, ProviderDeliveryHealth) or not isinstance(self.polling_fallback, PollingFallbackHealth)
            or self.dispatch is not DispatchHealth.NOT_INCLUDED
            or self.aggregate != _aggregate(self.local_listener, self.provider_object, self.provider_delivery, self.polling_fallback)
            or self.cleanup_eligibility is not CleanupEligibility.NOT_AUTHORIZED
        ):
            raise ValueError("managed webhook health data is invalid")

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": "managed_webhook_health", "version": 1, "generation": self.generation,
            "desired_fingerprint": self.desired_fingerprint, "local_listener": self.local_listener.value,
            "provider_object": self.provider_object.value, "provider_delivery": self.provider_delivery.value,
            "polling_fallback": self.polling_fallback.value, "dispatch": self.dispatch.value,
            "aggregate": self.aggregate.value, "cleanup_eligibility": self.cleanup_eligibility.value,
        }

    @classmethod
    def from_dict(cls, value: object) -> "ManagedWebhookHealth":
        fields = {"kind", "version", "generation", "desired_fingerprint", "local_listener", "provider_object", "provider_delivery", "polling_fallback", "dispatch", "aggregate", "cleanup_eligibility"}
        if type(value) is not dict or set(value) != fields or value.get("kind") != "managed_webhook_health" or value.get("version") != 1:
            raise ValueError("managed webhook health data is invalid")
        try:
            return cls(value["generation"], value["desired_fingerprint"], ListenerHealth(value["local_listener"]), ProviderObjectHealth(value["provider_object"]), ProviderDeliveryHealth(value["provider_delivery"]), PollingFallbackHealth(value["polling_fallback"]), DispatchHealth(value["dispatch"]), AggregateHealth(value["aggregate"]), CleanupEligibility(value["cleanup_eligibility"]))
        except (TypeError, ValueError):
            raise ValueError("managed webhook health data is invalid") from None


@dataclass(frozen=True, slots=True)
class CleanupIntent:
    """An exact future target, not an armed provider or service operation."""
    intent_id: str
    owner_id: str
    repository_id: int
    hook_id: int
    service_id: str
    generation: int
    desired_fingerprint: str
    action: CleanupAction

    def __post_init__(self) -> None:
        if (
            not _valid_cleanup_identity(self.owner_id, self.repository_id, self.hook_id, self.service_id, self.generation, self.desired_fingerprint)
            or not isinstance(self.action, CleanupAction)
            or self.intent_id != _intent_id(self.owner_id, self.repository_id, self.hook_id, self.service_id, self.generation, self.desired_fingerprint, self.action)
        ):
            raise ValueError("managed webhook health data is invalid")

    @classmethod
    def create(cls, *, owner_id: str, repository_id: int, hook_id: int, service_id: str,
               generation: int, desired_fingerprint: str, action: CleanupAction) -> "CleanupIntent":
        return cls(_intent_id(owner_id, repository_id, hook_id, service_id, generation, desired_fingerprint, action), owner_id, repository_id, hook_id, service_id, generation, desired_fingerprint, action)

    def to_dict(self) -> dict[str, object]:
        return {"kind": "cleanup_intent", "version": 1, **_identity_dict(self), "intent_id": self.intent_id, "action": self.action.value}

    @classmethod
    def from_dict(cls, value: object) -> "CleanupIntent":
        fields = _identity_fields() | {"kind", "version", "intent_id", "action"}
        if type(value) is not dict or set(value) != fields or value.get("kind") != "cleanup_intent" or value.get("version") != 1:
            raise ValueError("managed webhook health data is invalid")
        try:
            return cls(value["intent_id"], value["owner_id"], value["repository_id"], value["hook_id"], value["service_id"], value["generation"], value["desired_fingerprint"], CleanupAction(value["action"]))
        except (TypeError, ValueError):
            raise ValueError("managed webhook health data is invalid") from None


@dataclass(frozen=True, slots=True)
class CleanupPlan:
    intent: CleanupIntent
    inventory: ProviderObjectHealth
    eligibility: CleanupEligibility = CleanupEligibility.NOT_AUTHORIZED

    def __post_init__(self) -> None:
        if type(self.intent) is not CleanupIntent or not isinstance(self.inventory, ProviderObjectHealth) or self.eligibility is not CleanupEligibility.NOT_AUTHORIZED:
            raise ValueError("managed webhook health data is invalid")

    def to_dict(self) -> dict[str, object]:
        return {"kind": "cleanup_plan", "version": 1, "intent": self.intent.to_dict(), "inventory": self.inventory.value, "eligibility": self.eligibility.value}

    @classmethod
    def from_dict(cls, value: object) -> "CleanupPlan":
        fields = {"kind", "version", "intent", "inventory", "eligibility"}
        if type(value) is not dict or set(value) != fields or value.get("kind") != "cleanup_plan" or value.get("version") != 1:
            raise ValueError("managed webhook health data is invalid")
        try:
            return cls(CleanupIntent.from_dict(value["intent"]), ProviderObjectHealth(value["inventory"]), CleanupEligibility(value["eligibility"]))
        except (TypeError, ValueError):
            raise ValueError("managed webhook health data is invalid") from None


@dataclass(frozen=True, slots=True)
class CleanupTombstone:
    """Sanitized retained state; provider readback and service output stay outside."""
    intent_id: str
    owner_id: str
    repository_id: int
    hook_id: int
    service_id: str
    generation: int
    desired_fingerprint: str
    action: CleanupAction
    state: CleanupTombstoneState

    def __post_init__(self) -> None:
        if (
            not _valid_cleanup_identity(self.owner_id, self.repository_id, self.hook_id, self.service_id, self.generation, self.desired_fingerprint)
            or not isinstance(self.action, CleanupAction) or not isinstance(self.state, CleanupTombstoneState)
            or self.intent_id != _intent_id(self.owner_id, self.repository_id, self.hook_id, self.service_id, self.generation, self.desired_fingerprint, self.action)
        ):
            raise ValueError("managed webhook health data is invalid")

    @classmethod
    def from_intent(cls, intent: CleanupIntent, *, state: CleanupTombstoneState) -> "CleanupTombstone":
        return cls(intent.intent_id, intent.owner_id, intent.repository_id, intent.hook_id, intent.service_id, intent.generation, intent.desired_fingerprint, intent.action, state)

    def to_dict(self) -> dict[str, object]:
        return {"kind": "cleanup_tombstone", "version": 1, **_identity_dict(self), "intent_id": self.intent_id, "action": self.action.value, "state": self.state.value}

    @classmethod
    def from_dict(cls, value: object) -> "CleanupTombstone":
        fields = _identity_fields() | {"kind", "version", "intent_id", "action", "state"}
        if type(value) is not dict or set(value) != fields or value.get("kind") != "cleanup_tombstone" or value.get("version") != 1:
            raise ValueError("managed webhook health data is invalid")
        try:
            return cls(value["intent_id"], value["owner_id"], value["repository_id"], value["hook_id"], value["service_id"], value["generation"], value["desired_fingerprint"], CleanupAction(value["action"]), CleanupTombstoneState(value["state"]))
        except (TypeError, ValueError):
            raise ValueError("managed webhook health data is invalid") from None


@dataclass(frozen=True, slots=True)
class CleanupHistoryEvent:
    sequence: int
    intent_id: str
    owner_id: str
    repository_id: int
    hook_id: int
    service_id: str
    generation: int
    desired_fingerprint: str
    action: CleanupAction
    phase: CleanupHistoryPhase

    def __post_init__(self) -> None:
        if (
            type(self.sequence) is not int or not 0 <= self.sequence < _MAX_GENERATION
            or not _valid_cleanup_identity(self.owner_id, self.repository_id, self.hook_id, self.service_id, self.generation, self.desired_fingerprint)
            or not isinstance(self.action, CleanupAction) or not isinstance(self.phase, CleanupHistoryPhase)
            or self.intent_id != _intent_id(self.owner_id, self.repository_id, self.hook_id, self.service_id, self.generation, self.desired_fingerprint, self.action)
        ):
            raise ValueError("managed webhook health data is invalid")

    @classmethod
    def from_intent(cls, sequence: int, intent: CleanupIntent, phase: CleanupHistoryPhase) -> "CleanupHistoryEvent":
        return cls(sequence, intent.intent_id, intent.owner_id, intent.repository_id, intent.hook_id, intent.service_id, intent.generation, intent.desired_fingerprint, intent.action, phase)

    def to_dict(self) -> dict[str, object]:
        return {"sequence": self.sequence, **_identity_dict(self), "intent_id": self.intent_id, "action": self.action.value, "phase": self.phase.value}

    @classmethod
    def from_dict(cls, value: object) -> "CleanupHistoryEvent":
        fields = _identity_fields() | {"sequence", "intent_id", "action", "phase"}
        if type(value) is not dict or set(value) != fields:
            raise ValueError("managed webhook health data is invalid")
        try:
            return cls(value["sequence"], value["intent_id"], value["owner_id"], value["repository_id"], value["hook_id"], value["service_id"], value["generation"], value["desired_fingerprint"], CleanupAction(value["action"]), CleanupHistoryPhase(value["phase"]))
        except (TypeError, ValueError):
            raise ValueError("managed webhook health data is invalid") from None


@dataclass(frozen=True, slots=True)
class CleanupHistory:
    owner_id: str
    repository_id: int
    hook_id: int
    service_id: str
    generation: int
    desired_fingerprint: str
    entries: tuple[CleanupHistoryEvent, ...]

    def __post_init__(self) -> None:
        if (
            not _valid_cleanup_identity(self.owner_id, self.repository_id, self.hook_id, self.service_id, self.generation, self.desired_fingerprint)
            or type(self.entries) is not tuple or len(self.entries) > _MAX_HISTORY
            or any(type(item) is not CleanupHistoryEvent for item in self.entries)
            or any(not _same_identity(self, item) for item in self.entries)
            or tuple(item.sequence for item in self.entries) != tuple(sorted(item.sequence for item in self.entries))
            or len({item.sequence for item in self.entries}) != len(self.entries)
        ):
            raise ValueError("managed webhook health data is invalid")

    def to_dict(self) -> dict[str, object]:
        return {"kind": "cleanup_history", "version": 1, **_identity_dict(self), "entries": [item.to_dict() for item in self.entries]}

    @classmethod
    def from_dict(cls, value: object) -> "CleanupHistory":
        fields = _identity_fields() | {"kind", "version", "entries"}
        if type(value) is not dict or set(value) != fields or value.get("kind") != "cleanup_history" or value.get("version") != 1 or type(value.get("entries")) is not list:
            raise ValueError("managed webhook health data is invalid")
        try:
            return cls(value["owner_id"], value["repository_id"], value["hook_id"], value["service_id"], value["generation"], value["desired_fingerprint"], tuple(CleanupHistoryEvent.from_dict(item) for item in value["entries"]))
        except (TypeError, ValueError):
            raise ValueError("managed webhook health data is invalid") from None


class ManagedWebhookHealthCodec:
    """Bounded, deterministic and duplicate-key-rejecting codec for C3-A records."""
    @staticmethod
    def encode(value: ManagedWebhookHealth | CleanupIntent | CleanupPlan | CleanupTombstone | CleanupHistory) -> str:
        if type(value) not in {ManagedWebhookHealth, CleanupIntent, CleanupPlan, CleanupTombstone, CleanupHistory}:
            raise ValueError("managed webhook health data is invalid")
        rendered = json.dumps(value.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        if len(rendered.encode("utf-8")) > _MAX_JSON_BYTES:
            raise ValueError("managed webhook health data is invalid")
        return rendered

    @staticmethod
    def decode(rendered: object) -> ManagedWebhookHealth | CleanupIntent | CleanupPlan | CleanupTombstone | CleanupHistory:
        if type(rendered) is not str or len(rendered.encode("utf-8")) > _MAX_JSON_BYTES:
            raise ValueError("managed webhook health data is invalid")
        try:
            value = json.loads(rendered, object_pairs_hook=_unique_object, parse_constant=_invalid_constant)
        except (TypeError, ValueError, json.JSONDecodeError):
            raise ValueError("managed webhook health data is invalid") from None
        if type(value) is not dict or _contains_unsafe_data(value):
            raise ValueError("managed webhook health data is invalid")
        decoders = {"managed_webhook_health": ManagedWebhookHealth, "cleanup_intent": CleanupIntent, "cleanup_plan": CleanupPlan, "cleanup_tombstone": CleanupTombstone, "cleanup_history": CleanupHistory}
        decoder = decoders.get(value.get("kind"))
        if decoder is None:
            raise ValueError("managed webhook health data is invalid")
        return decoder.from_dict(value)

    @staticmethod
    def redact(_: object) -> str:
        return "REDACTED"


def _aggregate(local: ListenerHealth, obj: ProviderObjectHealth, delivery: ProviderDeliveryHealth, polling: PollingFallbackHealth) -> AggregateHealth:
    if local is ListenerHealth.UNOBSERVED and obj is ProviderObjectHealth.UNOBSERVED and delivery is ProviderDeliveryHealth.UNOBSERVED and polling is PollingFallbackHealth.UNOBSERVED:
        return AggregateHealth.UNOBSERVED
    if local is ListenerHealth.BLOCKED or obj is ProviderObjectHealth.BLOCKED or delivery is ProviderDeliveryHealth.BLOCKED or polling is PollingFallbackHealth.BLOCKED:
        return AggregateHealth.BLOCKED
    if local is ListenerHealth.UNKNOWN and obj is ProviderObjectHealth.UNKNOWN and delivery is ProviderDeliveryHealth.UNKNOWN and polling is PollingFallbackHealth.UNKNOWN:
        return AggregateHealth.UNKNOWN
    if local is ListenerHealth.READY and obj is ProviderObjectHealth.EXACT and delivery is ProviderDeliveryHealth.OBSERVED and polling is PollingFallbackHealth.READY:
        return AggregateHealth.HEALTHY
    return AggregateHealth.DEGRADED


def _valid_generation_fingerprint(generation: object, desired_fingerprint: object) -> bool:
    return type(generation) is int and 0 <= generation < _MAX_GENERATION and type(desired_fingerprint) is str and _FINGERPRINT.fullmatch(desired_fingerprint) is not None


def _valid_cleanup_identity(owner_id: object, repository_id: object, hook_id: object, service_id: object, generation: object, desired_fingerprint: object) -> bool:
    return type(owner_id) is str and _safe_identifier(owner_id) and type(repository_id) is int and 0 < repository_id < _MAX_GENERATION and type(hook_id) is int and 0 < hook_id < _MAX_GENERATION and type(service_id) is str and _safe_identifier(service_id) and _valid_generation_fingerprint(generation, desired_fingerprint)


def _identity_dict(value: CleanupIntent | CleanupTombstone | CleanupHistory | CleanupHistoryEvent) -> dict[str, object]:
    return {"owner_id": value.owner_id, "repository_id": value.repository_id, "hook_id": value.hook_id, "service_id": value.service_id, "generation": value.generation, "desired_fingerprint": value.desired_fingerprint}


def _identity_fields() -> set[str]:
    return {"owner_id", "repository_id", "hook_id", "service_id", "generation", "desired_fingerprint"}


def _intent_id(owner_id: str, repository_id: int, hook_id: int, service_id: str, generation: int, desired_fingerprint: str, action: CleanupAction) -> str:
    identity = {"owner_id": owner_id, "repository_id": repository_id, "hook_id": hook_id, "service_id": service_id, "generation": generation, "desired_fingerprint": desired_fingerprint, "action": action.value}
    return "cleanup_" + hashlib.sha256(json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("ascii")).hexdigest()


def _same_identity(history: CleanupHistory, event: CleanupHistoryEvent) -> bool:
    return _identity_dict(history) == _identity_dict(event)


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate JSON key")
        value[key] = item
    return value


def _invalid_constant(_: str) -> object:
    raise ValueError("invalid JSON constant")


def _contains_unsafe_data(value: object) -> bool:
    if type(value) is dict:
        return any(_unsafe_string(key) or _contains_unsafe_data(item) for key, item in value.items())
    if type(value) is list:
        return any(_contains_unsafe_data(item) for item in value)
    return type(value) is str and _unsafe_string(value)


def _unsafe_string(value: str) -> bool:
    lowered = value.lower()
    return "://" in value or value.startswith("/") or re.match(r"^[A-Za-z]:[\\\\/]", value) is not None or any(marker in lowered for marker in ("secret", "token", "payload", "response", "error", "reference", "_ref"))


def _safe_identifier(value: str) -> bool:
    return _NAME.fullmatch(value) is not None and not _unsafe_string(value)
