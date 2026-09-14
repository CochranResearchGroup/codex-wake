from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from types import MappingProxyType
from typing import Any, Callable, Literal

from .process import boot_id_value, process_exists, process_identity
from .records import WakeError, parse_utc_timestamp
from .signals import (
    ArmContext,
    ArmedSignal,
    Eq,
    EvaluationLimits,
    InMemorySignalModule,
    Matched,
    NormalizedObservation,
    Resume,
    SignalRequest,
    SourceAnchor,
    SourceCommit,
    SourceContract,
    Verification,
    WakeId,
)


_SOURCE = "codex_wake.builtin"
_SOURCE_INSTANCE = "local-runtime-v1"
_OCCURRENCE_NAMESPACE = "predicate-state-v1"


@dataclass(frozen=True, slots=True)
class BuiltinPredicateResult:
    ready: bool
    message: str
    logical_identity: tuple[str, str, str, str]
    signal: SignalRequest


@dataclass(frozen=True, slots=True)
class _Sample:
    predicate_type: str
    subject: str
    ready: bool
    message: str
    occurrence_value: str
    condition: Literal["holds", "becomes"] = "holds"


class _StaticAdapter:
    def __init__(self, contract: SourceContract) -> None:
        self._contract = contract

    def contract(self) -> SourceContract:
        return self._contract

    def establish_anchor(self, spec: SignalRequest, now: datetime) -> SourceAnchor:
        return SourceAnchor(0, "builtin:v1", MappingProxyType({}), "state_recheck")


class BuiltinPredicateSignals:
    """Evaluate schema-v1 built-ins through the provider-neutral signal seam."""

    def __init__(
        self,
        *,
        process_exists_fn: Callable[[int], bool] | None = None,
        boot_id_fn: Callable[[], str | None] | None = None,
        process_identity_fn: Callable[[int], dict[str, Any] | None] | None = None,
    ) -> None:
        self._process_exists = process_exists_fn or process_exists
        self._boot_id = boot_id_fn or boot_id_value
        self._process_identity = process_identity_fn or process_identity

    def evaluate(self, record: dict, now: datetime) -> BuiltinPredicateResult:
        sample = self._sample(record, now)
        signal = SignalRequest(
            contract_version=1,
            source=_SOURCE,
            source_instance=_SOURCE_INSTANCE,
            semantics="state",
            kind=f"predicate.{sample.predicate_type}",
            subject=sample.subject,
            condition=sample.condition,
            where=(Eq("matched", True),),
            verification="required",
        )
        contract = SourceContract(
            source=_SOURCE,
            source_instance=_SOURCE_INSTANCE,
            kinds=frozenset({signal.kind}),
            subjects=frozenset({signal.subject}),
            allowed_attributes=MappingProxyType({"matched": bool}),
        )
        engine = InMemorySignalModule()
        wake_id = WakeId(str(record.get("id") or "wake_builtin_v1"))
        armed = engine.arm(
            wake_id,
            signal,
            ArmContext(
                idempotency_key=f"builtin:{wake_id}",
                intent_fingerprint=sample.subject,
                registered_at=now,
                expires_at=None,
                resume=Resume("", Path("."), MappingProxyType({})),
                adapter=_StaticAdapter(contract),
            ),
        )
        if not isinstance(armed, ArmedSignal):
            raise WakeError("built-in predicate could not be represented as a signal")
        identity = (
            _SOURCE,
            _SOURCE_INSTANCE,
            _OCCURRENCE_NAMESPACE,
            sample.occurrence_value,
        )
        if sample.ready:
            observation = NormalizedObservation(
                source=_SOURCE,
                source_instance=_SOURCE_INSTANCE,
                kind=signal.kind,
                subject=signal.subject,
                occurrence_namespace=_OCCURRENCE_NAMESPACE,
                occurrence_value=sample.occurrence_value,
                occurred_at=now,
                observed_at=now,
                attributes=MappingProxyType({"matched": True}),
                verification=Verification("verified", "builtin_state_recheck"),
            )
            ingested = engine.ingest(
                (observation,),
                SourceCommit(_SOURCE, _SOURCE_INSTANCE, sample.occurrence_value, 1, now),
            )
            if getattr(ingested, "outcome", None) != "ingested":
                raise WakeError("built-in predicate observation could not be ingested")
        outcome = engine.evaluate(wake_id, armed, now, EvaluationLimits(1))
        return BuiltinPredicateResult(
            isinstance(outcome, Matched),
            sample.message,
            identity,
            signal,
        )

    def _sample(self, record: dict, now: datetime) -> _Sample:
        predicate = record.get("predicate")
        if not isinstance(predicate, dict):
            raise WakeError("predicate must be an object")
        predicate_type = predicate.get("type")
        if predicate_type == "not_before":
            return self._sample_not_before(predicate, now)
        if predicate_type == "file_exists":
            return self._sample_file_exists(record, predicate)
        if predicate_type == "file_changed":
            return self._sample_file_changed(record, predicate)
        if predicate_type == "process_done":
            return self._sample_process_done(predicate)
        raise WakeError(f"unsupported predicate type: {predicate_type}")

    def _sample_not_before(self, predicate: dict, now: datetime) -> _Sample:
        due_at = predicate.get("due_at")
        if not isinstance(due_at, str) or not due_at:
            raise WakeError("not_before predicate requires due_at")
        ready = parse_utc_timestamp(due_at) <= now
        subject = _stable_digest({"type": "not_before", "due_at": due_at})
        return _Sample(
            "not_before",
            subject,
            ready,
            f"not_before due_at {due_at} matched",
            _stable_digest({"subject": subject, "ready": ready}),
        )

    def _sample_file_exists(self, record: dict, predicate: dict) -> _Sample:
        raw_path = predicate.get("path")
        if not isinstance(raw_path, str) or not raw_path:
            raise WakeError("file_exists predicate requires path")
        path = _resolve_record_path(record, raw_path, "file_exists")
        ready = path.exists()
        subject = _stable_digest({"type": "file_exists", "path": str(path)})
        return _Sample(
            "file_exists",
            subject,
            ready,
            f"file_exists path {path} matched",
            _stable_digest({"subject": subject, "ready": ready}),
        )

    def _sample_file_changed(self, record: dict, predicate: dict) -> _Sample:
        raw_path = predicate.get("path")
        if not isinstance(raw_path, str) or not raw_path:
            raise WakeError("file_changed predicate requires path")
        path = _resolve_record_path(record, raw_path, "file_changed")
        try:
            stat = path.stat()
        except FileNotFoundError:
            ready = False
            state: object = "missing"
            message = f"file_changed path {path} matched"
        else:
            registered_exists = bool(predicate.get("registered_exists"))
            registered_mtime_ns = predicate.get("registered_mtime_ns")
            registered_size = predicate.get("registered_size")
            state = {"mtime_ns": stat.st_mtime_ns, "size": stat.st_size}
            if not registered_exists:
                ready = True
                message = f"file_changed path {path} was created"
            else:
                if not isinstance(registered_mtime_ns, int) or not isinstance(registered_size, int):
                    raise WakeError("file_changed predicate requires registered_mtime_ns and registered_size")
                ready = stat.st_mtime_ns != registered_mtime_ns or stat.st_size != registered_size
                message = f"file_changed path {path} changed"
        subject = _stable_digest(
            {
                "type": "file_changed",
                "path": str(path),
                "registered_exists": bool(predicate.get("registered_exists")),
                "registered_mtime_ns": predicate.get("registered_mtime_ns"),
                "registered_size": predicate.get("registered_size"),
            }
        )
        return _Sample(
            "file_changed",
            subject,
            ready,
            message,
            _stable_digest({"subject": subject, "state": state}),
            "becomes",
        )

    def _sample_process_done(self, predicate: dict) -> _Sample:
        pid = predicate.get("pid")
        if not isinstance(pid, int) or pid <= 0:
            raise WakeError("process_done predicate requires positive integer pid")
        state: object
        if not self._process_exists(pid):
            ready = True
            state = "exited"
            message = f"process_done pid {pid} exited"
        else:
            registered_boot_id = predicate.get("registered_boot_id")
            if registered_boot_id is not None and not isinstance(registered_boot_id, str):
                raise WakeError("process_done registered_boot_id must be a string when present")
            if registered_boot_id:
                current_boot_id = self._boot_id()
                if current_boot_id and current_boot_id != registered_boot_id:
                    ready = True
                    state = {"boot_id": current_boot_id}
                    message = f"process_done pid {pid} was from previous boot"
                    return self._process_sample(predicate, pid, ready, state, message)
            registered_start_time_ticks = predicate.get("registered_start_time_ticks")
            if registered_start_time_ticks is None:
                ready = False
                state = "exists"
                message = f"process_done pid {pid} still exists"
            else:
                if not isinstance(registered_start_time_ticks, int):
                    raise WakeError("process_done registered_start_time_ticks must be an integer when present")
                current_identity = self._process_identity(pid)
                if current_identity is None:
                    ready = False
                    state = "identity_unavailable"
                    message = f"process_done pid {pid} still exists; process identity unavailable"
                elif current_identity.get("start_time_ticks") != registered_start_time_ticks:
                    ready = True
                    state = current_identity
                    message = f"process_done pid {pid} no longer matches registered process"
                else:
                    ready = False
                    state = current_identity
                    message = f"process_done pid {pid} still matches registered process"
        return self._process_sample(predicate, pid, ready, state, message)

    def _process_sample(
        self,
        predicate: dict,
        pid: int,
        ready: bool,
        state: object,
        message: str,
    ) -> _Sample:
        subject = _stable_digest(
            {
                "type": "process_done",
                "pid": pid,
                "registered_boot_id": predicate.get("registered_boot_id"),
                "registered_start_time_ticks": predicate.get("registered_start_time_ticks"),
            }
        )
        return _Sample(
            "process_done",
            subject,
            ready,
            message,
            _stable_digest({"subject": subject, "state": state}),
            "becomes",
        )


def _stable_digest(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _resolve_record_path(record: dict, raw_path: str, predicate_type: str) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path
    cwd = record.get("cwd")
    if not isinstance(cwd, str) or not cwd:
        raise WakeError(f"relative {predicate_type} predicate requires record cwd")
    return Path(cwd) / path
