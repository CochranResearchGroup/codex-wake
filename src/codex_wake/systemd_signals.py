"""A fixed read boundary for current-user systemd state signals.

The production backend uses a closed low-level D-Bus call plan.  Tests may
inject the two-method ``SystemdUserManager`` protocol, but no product surface
can choose a manager, method, path, property, or command.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType
from typing import Awaitable, Callable, Iterable, Literal, Mapping, Protocol

from .runtime_signals import RuntimeSourceRegistry
from .signals import (
    ArmedSignal,
    Degraded,
    Eq,
    EvaluationLimits,
    Ingested,
    Invalid,
    Matched,
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
_SYSTEMD_DESTINATION = "org.freedesktop.systemd1"
_SYSTEMD_MANAGER_PATH = "/org/freedesktop/systemd1"
_SYSTEMD_MANAGER_INTERFACE = "org.freedesktop.systemd1.Manager"
_SYSTEMD_UNIT_INTERFACE = "org.freedesktop.systemd1.Unit"
_PROPERTIES_INTERFACE = "org.freedesktop.DBus.Properties"
_DBUS_DESTINATION = "org.freedesktop.DBus"
_DBUS_PATH = "/org/freedesktop/DBus"
_DBUS_INTERFACE = "org.freedesktop.DBus"


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
class SystemdBusCall:
    """One member of the fixed systemd observation call plan."""

    destination: str
    path: str
    interface: str
    member: str
    signature: str
    body: tuple[str, ...]


SystemdBusQuery = Callable[[SystemdBusCall], Awaitable[tuple[object, ...]]]


class DbusNextUserManager:
    """Fixed current-session-bus systemd reader with no dynamic bus surface.

    The optional query is a narrow test seam.  Its input is always created by
    this class from the fixed call plan below; callers cannot select an object
    path, destination, interface, member, or property.
    """

    def __init__(self, query: SystemdBusQuery | None = None) -> None:
        if query is not None and not callable(query):
            raise ValueError("systemd bus query is invalid")
        self._query = query or _dbus_next_query
        self._cached: tuple[str, SystemdUnitState] | None = None

    def resolve_unit(self, unit: str, *, timeout_seconds: int) -> str:
        sample = self._transaction(unit, timeout_seconds)
        self._cached = (unit, sample)
        return sample.unit

    def read_unit(self, unit: str, *, timeout_seconds: int) -> SystemdUnitState | None:
        cached = self._cached
        self._cached = None
        if cached is not None and cached[0] == unit:
            return cached[1]
        return self._transaction(unit, timeout_seconds)

    def _transaction(self, unit: str, timeout_seconds: int) -> SystemdUnitState:
        if not _valid_unit_name(unit) or type(timeout_seconds) is not int or isinstance(timeout_seconds, bool) or not 1 <= timeout_seconds <= 60:
            raise SystemdReadError("unavailable")
        try:
            try:
                asyncio.get_running_loop()
            except RuntimeError:
                pass
            else:
                raise SystemdReadError("unavailable")
            return asyncio.run(self._bounded_observe(unit, timeout_seconds))
        except TimeoutError:
            raise SystemdReadError("timeout") from None
        except SystemdReadError:
            raise
        except Exception:
            raise SystemdReadError("unavailable") from None

    async def _bounded_observe(self, unit: str, timeout_seconds: int) -> SystemdUnitState:
        return await asyncio.wait_for(self._observe(unit), timeout=timeout_seconds)

    async def _observe(self, unit: str) -> SystemdUnitState:
        owner_before = _unique_owner(await self._query(_owner_call()))
        object_path = _unit_path(await self._query(_get_unit_call(unit)))
        canonical = _unit_id(await self._query(_property_call(object_path, "Id")))
        active_state = _active_state(await self._query(_property_call(object_path, "ActiveState")))
        owner_after = _unique_owner(await self._query(_owner_call()))
        if owner_before != owner_after:
            raise SystemdReadError("unavailable")
        return SystemdUnitState(canonical, active_state, _owner_generation(owner_before))


# Product integration uses this explicit name; the implementation remains the
# fixed dbus-next reader above and exposes no additional transport surface.
SystemdUserBusBackend = DbusNextUserManager


def _owner_call() -> SystemdBusCall:
    return SystemdBusCall(_DBUS_DESTINATION, _DBUS_PATH, _DBUS_INTERFACE, "GetNameOwner", "s", (_SYSTEMD_DESTINATION,))


def _get_unit_call(unit: str) -> SystemdBusCall:
    return SystemdBusCall(_SYSTEMD_DESTINATION, _SYSTEMD_MANAGER_PATH, _SYSTEMD_MANAGER_INTERFACE, "GetUnit", "s", (unit,))


def _property_call(path: str, property_name: Literal["Id", "ActiveState"]) -> SystemdBusCall:
    return SystemdBusCall(_SYSTEMD_DESTINATION, path, _PROPERTIES_INTERFACE, "Get", "ss", (_SYSTEMD_UNIT_INTERFACE, property_name))


async def _dbus_next_query(call: SystemdBusCall) -> tuple[object, ...]:
    """Lazy dbus-next 0.2.x bridge for the fixed low-level call plan only."""
    try:
        from dbus_next import BusType, Message, MessageType  # type: ignore[import-not-found]
        from dbus_next.aio import MessageBus  # type: ignore[import-not-found]
    except Exception:
        raise SystemdReadError("unavailable") from None
    bus = None
    try:
        bus = MessageBus(bus_type=BusType.SESSION)
        await bus.connect()
        reply = await bus.call(Message(
            destination=call.destination, path=call.path, interface=call.interface,
            member=call.member, signature=call.signature, body=list(call.body),
        ))
        if (
            reply.message_type != MessageType.METHOD_RETURN
            or type(reply.body) is not list
            or len(reply.body) != 1
        ):
            raise SystemdReadError("unavailable")
        if call.interface == _PROPERTIES_INTERFACE:
            if type(getattr(reply.body[0], "value", None)) is not str:
                raise SystemdReadError("unavailable")
            return (reply.body[0].value,)
        return (reply.body[0],)
    except SystemdReadError:
        raise
    except Exception:
        raise SystemdReadError("unavailable") from None
    finally:
        if bus is not None:
            try:
                bus.disconnect()
            except Exception:
                pass


def _one_string(reply: object, *, maximum: int) -> str:
    if type(reply) is not tuple or len(reply) != 1 or type(reply[0]) is not str:
        raise SystemdReadError("unavailable")
    value = reply[0]
    if not value or len(value.encode("utf-8")) > maximum or "\x00" in value:
        raise SystemdReadError("unavailable")
    return value


def _unique_owner(reply: object) -> str:
    value = _one_string(reply, maximum=128)
    if re.fullmatch(r":[A-Za-z0-9_.-]{1,120}", value) is None:
        raise SystemdReadError("unavailable")
    return value


def _unit_path(reply: object) -> str:
    value = _one_string(reply, maximum=512)
    if re.fullmatch(r"/org/freedesktop/systemd1/unit/[A-Za-z0-9_]+", value) is None:
        raise SystemdReadError("unavailable")
    return value


def _unit_id(reply: object) -> str:
    value = _one_string(reply, maximum=255)
    if not _valid_unit_name(value):
        raise SystemdReadError("unavailable")
    return value


def _active_state(reply: object) -> str:
    value = _one_string(reply, maximum=16)
    if value not in _STATES:
        raise SystemdReadError("unavailable")
    return value


def _owner_generation(owner: str) -> str:
    return hashlib.sha256(owner.encode("utf-8")).hexdigest()


def _valid_unit_name(value: object) -> bool:
    return bool(type(value) is str and len(value) <= 255 and re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.:@-]*\.(?:service|scope|target|timer|socket|path)", value))


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

    def _authorized(self, spec: SignalRequest) -> bool:
        descriptor = self._descriptor(spec)
        return bool(
            self._capability_allows_read()
            and descriptor is not None
            and self._authorization.authorized(descriptor)
        )

    def _valid_arm(self, armed: object) -> bool:
        try:
            baseline = armed.anchor.baseline
            descriptor = self._descriptor(armed.spec)
            baseline_state = SystemdUnitState(
                self.config.unit, baseline["active_state"], baseline["generation"]
            )
            return bool(
                type(armed) is ArmedSignal
                and self._valid_request(armed.spec)
                and descriptor is not None
                and armed.anchor.recovery == "state_recheck"
                and set(baseline) == {"active_state", "generation"}
                and type(baseline["active_state"]) is str
                and baseline["active_state"] in _STATES
                and baseline["active_state"] != armed.spec.where[0].value
                and type(baseline["generation"]) is str
                and _GENERATION.fullmatch(baseline["generation"]) is not None
                and armed.anchor.source_anchor == _anchor_value(descriptor, baseline_state)
            )
        except (AttributeError, KeyError, TypeError, ValueError):
            return False

    def evaluate(self, module, armed: ArmedSignal, now: datetime, limits: EvaluationLimits):
        """Guard generic evaluation and publication against fresh revocation."""
        if not self._valid_arm(armed):
            wake_id = armed.wake_id if type(armed) is ArmedSignal else None
            return Invalid(wake_id, "SYSTEMD_ANCHOR_INVALID", ("systemd arm is invalid",))
        if not self._authorized(armed.spec):
            return Degraded(armed.wake_id, "SYSTEMD_AUTHORIZATION_DENIED", None)
        outcome = module.evaluate(armed.wake_id, armed, now, limits)
        if isinstance(outcome, Matched):
            if not self._authorized(armed.spec):
                return Degraded(armed.wake_id, "SYSTEMD_AUTHORIZATION_DENIED", None)
            try:
                published = module.reconcile_match_publication(armed.wake_id)
            except Exception:
                published = False
            if published is not True:
                return Degraded(armed.wake_id, "SYSTEMD_PUBLICATION_UNAVAILABLE", None)
        return outcome


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

    def handles(self, armed: ArmedSignal) -> bool:
        return bool(
            type(armed) is ArmedSignal
            and armed.spec.source == _SOURCE
            and armed.spec.source_instance in self._adapters
        )

    def evaluate(self, module, armed: ArmedSignal, now: datetime, limits: EvaluationLimits):
        if not self.handles(armed):
            wake_id = armed.wake_id if type(armed) is ArmedSignal else None
            return Invalid(wake_id, "SYSTEMD_SOURCE_UNSUPPORTED", ("systemd source is not owned by this runner",))
        return self._adapters[armed.spec.source_instance].evaluate(module, armed, now, limits)

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
            if adapter is None or not adapter._valid_arm(persisted):
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
