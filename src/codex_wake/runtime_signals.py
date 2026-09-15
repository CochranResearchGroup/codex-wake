"""Closed runtime-source identities and operator-owned authorization hooks.

The registry describes capabilities; it neither loads plugins nor inspects a
resource. Callers must authorize before observation, ingestion, and evaluation.
Each successful guard is the authorization linearization point for its next
operation. Revocation takes effect at the next guarded boundary; it never
retracts an in-flight operation or an occurrence reserved by the durable journal.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from types import MappingProxyType
from typing import Callable, Mapping


class RuntimeHealthState(StrEnum):
    UNOBSERVED = "unobserved"
    READY = "ready"
    UNAVAILABLE = "unavailable"
    INVALIDATED = "invalidated"
    UNSUPPORTED = "unsupported"


class RuntimeRecoveryMode(StrEnum):
    STATE_RECHECK = "state_recheck"
    LOCAL_JOURNAL = "local_journal"
    SOURCE_REPLAY = "source_replay"


class RuntimeDiagnosticCode(StrEnum):
    NOT_OBSERVED = "RUNTIME_NOT_OBSERVED"
    READY = "RUNTIME_READY"
    SOURCE_UNSUPPORTED = "RUNTIME_SOURCE_UNSUPPORTED"
    AUTHORIZATION_DENIED = "RUNTIME_AUTHORIZATION_DENIED"
    OBSERVATION_UNAVAILABLE = "RUNTIME_OBSERVATION_UNAVAILABLE"
    OBSERVATION_AMBIGUOUS = "RUNTIME_OBSERVATION_AMBIGUOUS"
    BASELINE_MATCHES = "RUNTIME_BASELINE_MATCHES"
    RESOURCE_LIMIT = "RUNTIME_RESOURCE_LIMIT"
    ANCHOR_INVALID = "RUNTIME_ANCHOR_INVALID"
    REQUEST_INVALID = "RUNTIME_REQUEST_INVALID"
    CHECKPOINT_UNAVAILABLE = "RUNTIME_CHECKPOINT_UNAVAILABLE"
    CHECKPOINT_INVALID = "RUNTIME_CHECKPOINT_INVALID"
    INGEST_UNAVAILABLE = "RUNTIME_INGEST_UNAVAILABLE"
    PUBLICATION_UNAVAILABLE = "RUNTIME_PUBLICATION_UNAVAILABLE"


RUNTIME_DEGRADATION_CODES = frozenset(RuntimeDiagnosticCode) - {
    RuntimeDiagnosticCode.NOT_OBSERVED, RuntimeDiagnosticCode.READY,
}
_HEALTH_BY_CODE = MappingProxyType({
    RuntimeDiagnosticCode.NOT_OBSERVED: RuntimeHealthState.UNOBSERVED,
    RuntimeDiagnosticCode.READY: RuntimeHealthState.READY,
    RuntimeDiagnosticCode.SOURCE_UNSUPPORTED: RuntimeHealthState.UNSUPPORTED,
    RuntimeDiagnosticCode.AUTHORIZATION_DENIED: RuntimeHealthState.INVALIDATED,
    RuntimeDiagnosticCode.OBSERVATION_UNAVAILABLE: RuntimeHealthState.UNAVAILABLE,
    RuntimeDiagnosticCode.OBSERVATION_AMBIGUOUS: RuntimeHealthState.INVALIDATED,
    RuntimeDiagnosticCode.BASELINE_MATCHES: RuntimeHealthState.INVALIDATED,
    RuntimeDiagnosticCode.RESOURCE_LIMIT: RuntimeHealthState.UNAVAILABLE,
    RuntimeDiagnosticCode.ANCHOR_INVALID: RuntimeHealthState.INVALIDATED,
    RuntimeDiagnosticCode.REQUEST_INVALID: RuntimeHealthState.INVALIDATED,
    RuntimeDiagnosticCode.CHECKPOINT_UNAVAILABLE: RuntimeHealthState.UNAVAILABLE,
    RuntimeDiagnosticCode.CHECKPOINT_INVALID: RuntimeHealthState.INVALIDATED,
    RuntimeDiagnosticCode.INGEST_UNAVAILABLE: RuntimeHealthState.UNAVAILABLE,
    RuntimeDiagnosticCode.PUBLICATION_UNAVAILABLE: RuntimeHealthState.UNAVAILABLE,
})
_TARGET_STATES = frozenset({"terminated", "active", "inactive", "failed", "ready"})


@dataclass(frozen=True, slots=True)
class RuntimeDiagnostic:
    code: RuntimeDiagnosticCode
    source_fingerprint: str
    observed_at: datetime | None
    recovery: RuntimeRecoveryMode = RuntimeRecoveryMode.STATE_RECHECK

    def __post_init__(self) -> None:
        try:
            code = RuntimeDiagnosticCode(self.code)
            recovery = RuntimeRecoveryMode(self.recovery)
            valid = (type(self.source_fingerprint) is str
                and re.fullmatch(r"[0-9a-f]{64}", self.source_fingerprint) is not None
                and (self.observed_at is None or (type(self.observed_at) is datetime
                    and self.observed_at.tzinfo is not None and self.observed_at.utcoffset() is not None)))
            if not valid:
                raise ValueError
        except (TypeError, ValueError):
            raise ValueError("runtime diagnostic is invalid") from None
        object.__setattr__(self, "code", code)
        object.__setattr__(self, "recovery", recovery)

    @property
    def health(self) -> RuntimeHealthState:
        return _HEALTH_BY_CODE[self.code]

    def payload(self) -> dict[str, object]:
        return {"version": 1, "code": self.code.value, "health": self.health.value,
            "source_fingerprint": self.source_fingerprint,
            "observed_at": self.observed_at.isoformat() if self.observed_at is not None else None,
            "recovery": self.recovery.value}

    @classmethod
    def parse(cls, payload: object) -> RuntimeDiagnostic:
        try:
            if (type(payload) is not dict or set(payload) != {
                    "version", "code", "health", "source_fingerprint", "observed_at", "recovery"}
                    or type(payload["version"]) is not int or payload["version"] != 1):
                raise ValueError
            raw_time = payload["observed_at"]
            if raw_time is not None and (type(raw_time) is not str or len(raw_time) > 64):
                raise ValueError
            observed_at = datetime.fromisoformat(raw_time) if raw_time is not None else None
            result = cls(payload["code"], payload["source_fingerprint"], observed_at, payload["recovery"])
            if type(payload["health"]) is not str or payload["health"] != result.health.value:
                raise ValueError
            return result
        except (KeyError, TypeError, ValueError):
            raise ValueError("runtime diagnostic is invalid") from None


@dataclass(frozen=True, slots=True)
class RuntimeCapability:
    target_states: frozenset[str]
    recovery: RuntimeRecoveryMode = RuntimeRecoveryMode.STATE_RECHECK
    production: bool = True

    def __post_init__(self) -> None:
        try:
            recovery = RuntimeRecoveryMode(self.recovery)
            if (type(self.target_states) is not frozenset or not self.target_states
                    or any(type(state) is not str for state in self.target_states)
                    or not self.target_states <= _TARGET_STATES or type(self.production) is not bool):
                raise ValueError
        except (TypeError, ValueError):
            raise ValueError("runtime capability is invalid") from None
        object.__setattr__(self, "recovery", recovery)

    def payload(self) -> dict[str, object]:
        return {"version": 1, "target_states": sorted(self.target_states),
            "recovery": self.recovery.value, "production": self.production,
            "health_states": sorted(state.value for state in RuntimeHealthState),
            "diagnostic_codes": sorted(code.value for code in RuntimeDiagnosticCode)}


_CAPABILITIES = MappingProxyType({
    "process.exit": RuntimeCapability(frozenset({"terminated"})),
    "systemd.unit": RuntimeCapability(frozenset({"active", "inactive", "failed"})),
    "tracer.state": RuntimeCapability(frozenset({"ready"}), production=False),
})


def _canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True, slots=True)
class RuntimeSourceDescriptor:
    version: int
    kind: str
    resource: Mapping[str, str | int]
    target_state: str

    def __post_init__(self) -> None:
        invalid = ValueError("runtime source descriptor is invalid")
        if type(self.version) is not int or self.version != 1 or type(self.kind) is not str:
            raise invalid
        capability = _CAPABILITIES.get(self.kind)
        if capability is None or type(self.target_state) is not str or self.target_state not in capability.target_states:
            raise invalid
        if not isinstance(self.resource, Mapping):
            raise invalid
        resource = dict(self.resource)
        if self.kind == "process.exit":
            if set(resource) != {"boot_id", "pid", "start_time_ticks", "owner_uid"}:
                raise invalid
            boot = resource["boot_id"]
            if type(boot) is not str or re.fullmatch(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", boot) is None:
                raise invalid
            if not all(type(resource[k]) is int and resource[k] >= minimum for k, minimum in (("pid", 1), ("start_time_ticks", 1), ("owner_uid", 0))):
                raise invalid
            if any(resource[k] > 2**63 - 1 for k in ("pid", "start_time_ticks", "owner_uid")):
                raise invalid
        elif self.kind == "systemd.unit":
            if set(resource) != {"manager", "owner_uid", "unit"} or resource["manager"] != "user":
                raise invalid
            if type(resource["owner_uid"]) is not int or not 0 <= resource["owner_uid"] <= 2**32 - 1:
                raise invalid
            unit = resource["unit"]
            if type(unit) is not str or len(unit) > 255 or re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.:@-]*\.(?:service|scope|target|timer|socket|path)", unit) is None:
                raise invalid
        else:
            if set(resource) != {"identity"}:
                raise invalid
            identity = resource["identity"]
            if type(identity) is not str or re.fullmatch(r"[A-Za-z0-9_-]{1,96}", identity) is None:
                raise invalid
        object.__setattr__(self, "resource", MappingProxyType(resource))

    @classmethod
    def parse(cls, payload: object) -> RuntimeSourceDescriptor:
        if type(payload) is not dict or set(payload) != {"version", "kind", "resource", "target_state"}:
            raise ValueError("runtime source descriptor is invalid")
        return cls(**payload)

    def payload(self) -> dict[str, object]:
        return {"version": self.version, "kind": self.kind, "resource": dict(self.resource), "target_state": self.target_state}

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(_canonical(self.payload()).encode()).hexdigest()


class RuntimeSourceRegistry:
    """Callbacks belong to trusted configuration, never to a request payload.

    Each hook must compare exact resources and check source-specific authority
    (including same-user ownership and canonical unit resolution). Hooks are
    called afresh at every boundary; missing hooks and errors deny access.
    A successful guard authorizes the immediately following operation. A later
    revocation is observed at the next guard, without retracting in-flight or
    reserved durable work; callers must preserve those journal facts.
    """

    capabilities = _CAPABILITIES

    def __init__(self, authorizers: Mapping[str, Callable[[RuntimeSourceDescriptor], bool]]) -> None:
        hooks = dict(authorizers)
        if not set(hooks) <= set(_CAPABILITIES) or any(not callable(hook) for hook in hooks.values()):
            raise ValueError("runtime source authorizers are invalid")
        self._authorizers = MappingProxyType(hooks)

    def authorized(self, descriptor: RuntimeSourceDescriptor) -> bool:
        if type(descriptor) is not RuntimeSourceDescriptor:
            return False
        hook = self._authorizers.get(descriptor.kind)
        if hook is None:
            return False
        try:
            return hook(descriptor) is True
        except Exception:
            return False
