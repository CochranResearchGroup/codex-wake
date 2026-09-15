"""A fixed, injected read boundary for current-user systemd state signals.

There is intentionally no D-Bus implementation here.  A host integration may
provide the two-method ``SystemdUserManager`` protocol, but it cannot choose a
manager, method, path, property, or command through this product surface.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType
from typing import Iterable, Literal, Mapping, Protocol

from .runtime_signals import RuntimeSourceRegistry
from .signals import (
    ArmedSignal,
    Degraded,
    Eq,
    EvaluationLimits,
    Ingested,
    Invalid,
    NormalizedObservation,
    SignalEngine,
    SignalRequest,
    SourceAnchor,
    SourceCommit,
    SourceContract,
    SourceInstanceReconcileResult,
    SourceReconcileResult,
    Verification,
)
from .systemd_source_config import SystemdSourceConfig


_SOURCE = "systemd"
_KIND = "unit.active_state"
_STATES = frozenset({"active", "inactive", "failed"})
_GENERATION = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}")


@dataclass(frozen=True, slots=True)
class SystemdUnitState:
    """Sanitized read result; it deliberately excludes unit properties/payloads."""

    unit: str
    active_state: str
    generation: str


class SystemdReadError(Exception):
    """A sanitized category for timeout/unavailable read failures."""

    def __init__(self, kind: str = "unavailable") -> None:
        super().__init__("systemd user-manager read failed")
        self.kind = kind if kind in {"timeout", "unavailable"} else "unavailable"


@dataclass(frozen=True, slots=True)
class SystemdReadCapability:
    """Closed token for the only two user-manager read operations.

    It deliberately carries neither a manager connection nor caller-selected
    operation names.  The adapter accepts it only for the configured owner and
    an injected effective UID, so tests can prove foreign-UID denial without a
    host lookup.
    """

    manager: str
    owner_uid: int

    def __post_init__(self) -> None:
        if (self.manager != "user" or type(self.owner_uid) is not int
                or isinstance(self.owner_uid, bool) or not 0 <= self.owner_uid <= 2**32 - 1):
            raise ValueError("systemd read capability is invalid")

    @property
    def operations(self) -> frozenset[str]:
        return frozenset({"resolve_unit", "read_unit"})


class SystemdUserManager(Protocol):
    """The complete production backend authority: resolve and read only."""

    def resolve_unit(self, unit: str, *, timeout_seconds: int) -> str: ...

    def read_unit(self, unit: str, *, timeout_seconds: int) -> SystemdUnitState | None: ...


class SystemdSignalAdapter:
    """One exact canonical unit behind an injected current-user read backend."""

    def __init__(
        self,
        config: SystemdSourceConfig,
        backend: SystemdUserManager,
        authorization: RuntimeSourceRegistry,
        capability: SystemdReadCapability,
    ) -> None:
        if type(config) is not SystemdSourceConfig or not config.enabled:
            raise ValueError("systemd signal configuration is invalid")
        if not isinstance(authorization, RuntimeSourceRegistry):
            raise ValueError("systemd signal authorization is invalid")
        if type(capability) is not SystemdReadCapability:
            raise ValueError("systemd signal capability is invalid")
        self.config = config
        self._backend = backend
        self._authorization = authorization
        self._capability = capability
        self.source_instance = config.source_instance
        self.subject = f"unit:{config.unit}"

    def contract(self) -> SourceContract:
        return SourceContract(
            _SOURCE,
            self.source_instance,
            frozenset({_KIND}),
            frozenset({self.subject}),
            MappingProxyType({
                "active_state": str,
                "previous_active_state": str,
                "generation": str,
                "transition": bool,
                "observation_reason": str,
            }),
            max_clauses=2,
            max_attribute_bytes=512,
            max_evidence_ref_bytes=128,
        )

    def request(self, target_state: str) -> SignalRequest:
        descriptor = self.config.descriptor(target_state)
        return SignalRequest(
            1, _SOURCE, self.source_instance, "state", _KIND, self.subject,
            "becomes", (Eq("active_state", descriptor.target_state), Eq("transition", True)),
            "required",
        )

    def establish_anchor(self, spec: SignalRequest, now: datetime) -> SourceAnchor | Degraded | Invalid:
        if not self._valid_request(spec) or not _aware(now):
            return Invalid(None, "SYSTEMD_SIGNAL_NOT_ALLOWED", ("systemd signal is outside the configured unit",))
        if not self._capability_allows_read():
            return Degraded(None, "SYSTEMD_CAPABILITY_DENIED", None)
        sampled = self.sample(spec, now)
        if isinstance(sampled, (Degraded, Invalid)):
            return sampled
        if sampled.active_state == spec.where[0].value:
            return Degraded(None, "SYSTEMD_BASELINE_MATCHES", None)
        return SourceAnchor(
            0,
            _anchor_value(self._descriptor(spec), sampled),
            MappingProxyType({"active_state": sampled.active_state, "generation": sampled.generation}),
            "state_recheck",
        )

    def sample(self, spec: SignalRequest, now: datetime) -> SystemdUnitState | Degraded | Invalid:
        """Resolve aliases before authorizing the exact canonical descriptor.

        A configured name that resolves elsewhere is rejected rather than
        treating an alias as a new authority.  A missing unit is unavailable,
        never synthesized as ``inactive``.
        """
        if not self._valid_request(spec) or not _aware(now):
            return Invalid(None, "SYSTEMD_SIGNAL_NOT_ALLOWED", ("systemd signal is outside the configured unit",))
        if not self._capability_allows_read():
            return Degraded(None, "SYSTEMD_CAPABILITY_DENIED", None)
        try:
            canonical = self._backend.resolve_unit(self.config.unit, timeout_seconds=self.config.poll_timeout_seconds)
        except SystemdReadError as error:
            return Degraded(None, _error_code(error), None)
        except Exception:
            return Degraded(None, "SYSTEMD_OBSERVATION_UNAVAILABLE", None)
        if type(canonical) is not str or canonical != self.config.unit:
            return Invalid(None, "SYSTEMD_SIGNAL_NOT_ALLOWED", ("resolved unit is not the configured canonical unit",))
        descriptor = self._descriptor(spec)
        if descriptor is None or not self._authorization.authorized(descriptor):
            return Degraded(None, "SYSTEMD_AUTHORIZATION_DENIED", None)
        try:
            state = self._backend.read_unit(canonical, timeout_seconds=self.config.poll_timeout_seconds)
        except SystemdReadError as error:
            return Degraded(None, _error_code(error), None)
        except Exception:
            return Degraded(None, "SYSTEMD_OBSERVATION_UNAVAILABLE", None)
        if state is None:
            return Degraded(None, "SYSTEMD_UNIT_UNAVAILABLE", None)
        if not _valid_state(state, canonical):
            return Degraded(None, "SYSTEMD_OBSERVATION_UNAVAILABLE", None)
        if not self._authorization.authorized(descriptor):
            return Degraded(None, "SYSTEMD_AUTHORIZATION_DENIED", None)
        return state

    def _descriptor(self, spec: SignalRequest):
        if not self._valid_request(spec):
            return None
        return self.config.descriptor(spec.where[0].value)

    def _authorized_target(self, target_state: str) -> bool:
        try:
            return self._authorization.authorized(self.config.descriptor(target_state))
        except (TypeError, ValueError):
            return False

    def _capability_allows_read(self) -> bool:
        try:
            effective_uid = os.geteuid()
            return bool(
                type(effective_uid) is int and not isinstance(effective_uid, bool)
                and self._capability.manager == "user"
                and self._capability.owner_uid == self.config.owner_uid == effective_uid
                and self._capability.operations == frozenset({"resolve_unit", "read_unit"})
            )
        except OSError:
            return False

    def _valid_request(self, spec: object) -> bool:
        try:
            if type(spec) is not SignalRequest or type(spec.where) is not tuple or len(spec.where) != 2:
                return False
            state, transition = spec.where
            return bool(
                type(spec.contract_version) is int and spec.contract_version == 1
                and type(spec.source) is str and spec.source == _SOURCE
                and type(spec.source_instance) is str and spec.source_instance == self.source_instance
                and type(spec.semantics) is str and spec.semantics == "state"
                and type(spec.kind) is str and spec.kind == _KIND
                and type(spec.subject) is str and spec.subject == self.subject
                and type(spec.condition) is str and spec.condition == "becomes"
                and type(spec.verification) is str and spec.verification == "required"
                and type(state) is Eq and type(transition) is Eq
                and state.field == "active_state" and type(state.value) is str
                and state.value in self.config.target_states
                and transition.field == "transition" and transition.value is True
            )
        except (AttributeError, TypeError, ValueError):
            return False


class SystemdSignalRunner:
    """State recheck runner; uncertain gaps and boot changes are rebaselined."""

    def __init__(
        self,
        adapters: Iterable[SystemdSignalAdapter],
        *,
        armed_signals: Iterable[ArmedSignal] = (),
        initial_reason: Literal["periodic", "startup", "reconnect", "observation_gap"] = "periodic",
    ) -> None:
        configured = tuple(adapters)
        if any(type(adapter) is not SystemdSignalAdapter for adapter in configured):
            raise ValueError("systemd adapters are invalid")
        self._adapters = {adapter.source_instance: adapter for adapter in configured}
        if len(self._adapters) != len(configured) or initial_reason not in {"periodic", "startup", "reconnect", "observation_gap"}:
            raise ValueError("systemd adapters are invalid")
        self._armed_signals = tuple(armed_signals)
        self._reason = initial_reason
        self.last_result: SourceReconcileResult | None = None

    def reconnect(self) -> None:
        self._reason = "reconnect"

    def observation_gap(self) -> None:
        self._reason = "observation_gap"

    def reconcile(self, module: SignalEngine, now: datetime, limits: EvaluationLimits) -> SourceReconcileResult:
        if not _aware(now) or limits.max_candidates <= 0:
            self.last_result = SourceReconcileResult(_SOURCE, 0, 0, 1)
            return self.last_result
        groups: dict[str, list[ArmedSignal]] = {}
        degraded = observed = scanned = 0
        rows: list[SourceInstanceReconcileResult] = []
        for armed in self._armed_signals[:limits.max_candidates]:
            if type(armed) is not ArmedSignal or armed.spec.source != _SOURCE:
                continue
            try:
                persisted = module.load_armed_signal(armed.wake_id)  # type: ignore[attr-defined]
            except Exception:
                degraded += 1
                rows.append(SourceInstanceReconcileResult(_SOURCE, armed.spec.source_instance, 0, 0, 1))
                continue
            if persisted is None:
                continue
            if not _valid_persisted_arm(armed, persisted):
                degraded += 1
                rows.append(SourceInstanceReconcileResult(_SOURCE, armed.spec.source_instance, 0, 0, 1))
                continue
            if persisted.expires_at is not None and now >= persisted.expires_at:
                continue
            adapter = self._adapters.get(persisted.spec.source_instance)
            if adapter is None or not adapter._valid_request(persisted.spec):
                degraded += 1
                rows.append(SourceInstanceReconcileResult(_SOURCE, persisted.spec.source_instance, 0, 0, 1))
                continue
            groups.setdefault(adapter.source_instance, []).append(persisted)
        for name, arms in groups.items():
            adapter = self._adapters[name]
            scanned += 1
            sample = adapter.sample(arms[0].spec, now)
            if isinstance(sample, (Degraded, Invalid)):
                degraded += 1
                rows.append(SourceInstanceReconcileResult(_SOURCE, name, 1, 0, 1))
                continue
            prior = module.source_checkpoint(_SOURCE, name)
            previous = _checkpoint_state(prior, adapter)
            if isinstance(prior, Degraded) or (prior is not None and previous is None):
                degraded += 1
                rows.append(SourceInstanceReconcileResult(_SOURCE, name, 1, 0, 1))
                continue
            if previous is None:
                earliest = min(arms, key=lambda item: item.registered_at)
                baseline = earliest.anchor.baseline
                previous = _baseline_state(baseline)
                if previous is None:
                    degraded += 1
                    rows.append(SourceInstanceReconcileResult(_SOURCE, name, 1, 0, 1))
                    continue
            order = prior.checkpoint_order + 1 if isinstance(prior, SourceCommit) else 1
            uncertain = self._reason in {"reconnect", "observation_gap"} or previous.generation != sample.generation
            observations = () if uncertain else _observations(adapter, arms, previous, sample, now, order, self._reason)
            commit = SourceCommit(_SOURCE, name, _checkpoint(adapter, sample), order, now)
            outcome = module.ingest(observations, commit)
            if isinstance(outcome, Ingested):
                fresh = sum(not receipt.duplicate for receipt in outcome.receipts)
                observed += fresh
                rows.append(SourceInstanceReconcileResult(_SOURCE, name, 1, fresh, 0))
            else:
                degraded += 1
                rows.append(SourceInstanceReconcileResult(_SOURCE, name, 1, 0, 1))
        self._reason = "periodic"
        self.last_result = SourceReconcileResult(_SOURCE, scanned, observed, degraded, tuple(rows))
        return self.last_result


def _observations(adapter: SystemdSignalAdapter, arms: list[ArmedSignal], previous: SystemdUnitState, current: SystemdUnitState, now: datetime, order: int, reason: str) -> tuple[NormalizedObservation, ...]:
    rows: list[NormalizedObservation] = []
    if previous.active_state == current.active_state:
        return ()
    for target in sorted({arm.spec.where[0].value for arm in arms}):
        if current.active_state != target or not adapter._authorized_target(target):
            continue
        attributes = MappingProxyType({
            "active_state": current.active_state,
            "previous_active_state": previous.active_state,
            "generation": current.generation,
            "transition": True,
            "observation_reason": "reconciled" if reason in {"startup", "reconnect"} else "periodic",
        })
        rows.append(NormalizedObservation(
            _SOURCE, adapter.source_instance, _KIND, adapter.subject,
            "systemd-unit-state-v1", _digest({"descriptor": adapter.config.descriptor(target).fingerprint, "generation": current.generation, "from": previous.active_state, "to": current.active_state, "order": order}),
            now, now, attributes, Verification("verified", "user-manager-state-recheck"),
            f"systemd:user:{adapter.config.unit}:{current.generation}",
        ))
    return tuple(rows)


def _valid_persisted_arm(supplied: ArmedSignal, persisted: object) -> bool:
    """Only a matching durable published arm may authorize reconciliation."""
    try:
        return bool(
            type(persisted) is ArmedSignal
            and persisted.wake_id == supplied.wake_id
            and persisted.arm_id == supplied.arm_id
            and persisted.spec.source == supplied.spec.source
            and persisted.spec.source_instance == supplied.spec.source_instance
            and persisted.spec.kind == supplied.spec.kind
            and persisted.spec.subject == supplied.spec.subject
            and persisted.publication == "published"
        )
    except (AttributeError, TypeError, ValueError):
        return False


def _checkpoint(adapter: SystemdSignalAdapter, state: SystemdUnitState) -> str:
    return json.dumps({"version": 1, "fingerprint": _config_fingerprint(adapter), "active_state": state.active_state, "generation": state.generation}, sort_keys=True, separators=(",", ":"))


def _checkpoint_state(commit: SourceCommit | None, adapter: SystemdSignalAdapter) -> SystemdUnitState | None:
    if commit is None:
        return None
    try:
        if (commit.source != _SOURCE or commit.source_instance != adapter.source_instance
                or type(commit.checkpoint_order) is not int or commit.checkpoint_order < 1):
            return None
        value = json.loads(commit.checkpoint)
        if type(value) is not dict or set(value) != {"version", "fingerprint", "active_state", "generation"}:
            return None
        if value["version"] != 1 or value["fingerprint"] != _config_fingerprint(adapter):
            return None
        state = SystemdUnitState(adapter.config.unit, value["active_state"], value["generation"])
        return state if _valid_state(state, adapter.config.unit) else None
    except (TypeError, ValueError, json.JSONDecodeError):
        return None


def _baseline_state(value: Mapping[str, object]) -> SystemdUnitState | None:
    try:
        state = SystemdUnitState("", value["active_state"], value["generation"])
        return state if state.active_state in _STATES and type(state.generation) is str and _GENERATION.fullmatch(state.generation) else None
    except (KeyError, TypeError):
        return None


def _valid_state(state: object, unit: str) -> bool:
    return bool(type(state) is SystemdUnitState and state.unit == unit and state.active_state in _STATES and type(state.generation) is str and _GENERATION.fullmatch(state.generation))


def _anchor_value(descriptor, state: SystemdUnitState) -> str:
    return f"systemd:{descriptor.fingerprint}:{state.generation}"


def _config_fingerprint(adapter: SystemdSignalAdapter) -> str:
    payload = {"source_instance": adapter.config.source_instance, "unit": adapter.config.unit, "owner_uid": adapter.config.owner_uid, "target_states": sorted(adapter.config.target_states)}
    return _digest(payload)


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _aware(value: object) -> bool:
    return type(value) is datetime and value.tzinfo is not None and value.utcoffset() is not None


def _error_code(error: SystemdReadError) -> str:
    return "SYSTEMD_OBSERVATION_TIMEOUT" if error.kind == "timeout" else "SYSTEMD_OBSERVATION_UNAVAILABLE"
