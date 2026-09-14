from __future__ import annotations

import json
from dataclasses import dataclass, field, replace
from datetime import datetime
from pathlib import Path
from types import MappingProxyType
from typing import Literal, Mapping, NewType, Protocol, Sequence, TypeAlias


WakeId = NewType("WakeId", str)
ArmId = NewType("ArmId", str)
ReceiptId = NewType("ReceiptId", str)
MatchToken = NewType("MatchToken", str)
JsonScalar: TypeAlias = str | int | bool


@dataclass(frozen=True, slots=True)
class Eq:
    field: str
    value: JsonScalar


@dataclass(frozen=True, slots=True)
class In:
    field: str
    values: tuple[JsonScalar, ...]


WhereClause: TypeAlias = Eq | In


@dataclass(frozen=True, slots=True)
class SignalRequest:
    contract_version: Literal[1]
    source: str
    source_instance: str
    semantics: Literal["occurrence", "state"]
    kind: str
    subject: str
    condition: Literal["occurs", "holds", "becomes"]
    where: tuple[WhereClause, ...] = ()
    verification: Literal["required", "not_required"] = "required"


@dataclass(frozen=True, slots=True)
class Resume:
    prompt: str
    cwd: Path
    target: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class WakeIntent:
    when: SignalRequest
    resume: Resume
    expires_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class SourceAnchor:
    local_after_sequence: int
    source_anchor: str
    baseline: Mapping[str, JsonScalar]
    recovery: Literal["local_journal", "source_replay", "state_recheck"]


@dataclass(frozen=True, slots=True)
class SourceContract:
    source: str
    source_instance: str
    kinds: frozenset[str]
    subjects: frozenset[str]
    allowed_attributes: Mapping[str, type]
    max_clauses: int = 16
    max_in_values: int = 32
    max_attribute_bytes: int = 4096
    max_evidence_ref_bytes: int = 1024


@dataclass(frozen=True, slots=True)
class Verification:
    state: Literal["verified", "pending", "rejected"]
    method: str


@dataclass(frozen=True, slots=True)
class NormalizedObservation:
    source: str
    source_instance: str
    kind: str
    subject: str
    occurrence_namespace: str
    occurrence_value: str
    occurred_at: datetime
    observed_at: datetime
    attributes: Mapping[str, JsonScalar]
    verification: Verification
    evidence_ref: str | None = None


@dataclass(frozen=True, slots=True)
class SourceCommit:
    source: str
    source_instance: str
    checkpoint: str
    checkpoint_order: int
    observed_through: datetime


@dataclass(frozen=True, slots=True)
class ReceiptRef:
    receipt_id: ReceiptId
    local_sequence: int
    duplicate: bool


@dataclass(frozen=True, slots=True)
class Ingested:
    receipts: tuple[ReceiptRef, ...]
    checkpoint: str
    outcome: Literal["ingested"] = field(default="ingested", init=False)


@dataclass(frozen=True, slots=True)
class EvaluationLimits:
    max_candidates: int
    max_attribute_bytes: int = 4096
    max_evidence_ref_bytes: int = 1024


@dataclass(frozen=True, slots=True)
class EvidenceSummary:
    receipt_id: ReceiptId
    local_sequence: int
    evidence_ref: str | None
    attributes: Mapping[str, JsonScalar]
    verification_state: Literal["verified", "pending", "rejected"] = "verified"
    verification_method: str = ""


@dataclass(frozen=True, slots=True)
class Matched:
    wake_id: WakeId
    match_token: MatchToken
    receipt: EvidenceSummary
    matched_at: datetime
    outcome: Literal["matched"] = field(default="matched", init=False)


@dataclass(frozen=True, slots=True)
class NotReady:
    wake_id: WakeId
    scanned_through_sequence: int
    outcome: Literal["not_ready"] = field(default="not_ready", init=False)


@dataclass(frozen=True, slots=True)
class Expired:
    wake_id: WakeId
    expired_at: datetime
    outcome: Literal["expired"] = field(default="expired", init=False)


@dataclass(frozen=True, slots=True)
class Registration:
    wake_id: WakeId
    arm_id: ArmId
    contract_version: Literal[1]
    source: str
    source_instance: str
    subject: str
    registered_at: datetime
    recovery: Literal["local_journal", "source_replay", "state_recheck"]
    outcome: Literal["registered"] = field(default="registered", init=False)


@dataclass(frozen=True, slots=True)
class Invalid:
    wake_id: WakeId | None
    code: str
    issues: tuple[str, ...]
    outcome: Literal["invalid"] = field(default="invalid", init=False)


@dataclass(frozen=True, slots=True)
class Degraded:
    wake_id: WakeId | None
    code: str
    retry_at: datetime | None
    evidence_ref: str | None = None
    outcome: Literal["degraded"] = field(default="degraded", init=False)


@dataclass(frozen=True, slots=True)
class ArmContext:
    idempotency_key: str
    intent_fingerprint: str
    registered_at: datetime
    expires_at: datetime | None
    resume: Resume
    adapter: SignalSourceAdapter


@dataclass(frozen=True, slots=True)
class ArmedSignal:
    wake_id: WakeId
    arm_id: ArmId
    spec: SignalRequest
    anchor: SourceAnchor
    registered_at: datetime
    expires_at: datetime | None
    publication: Literal["prepared", "published"] = "published"


class SignalSourceAdapter(Protocol):
    def contract(self) -> SourceContract: ...

    def establish_anchor(self, spec: SignalRequest, now: datetime) -> SourceAnchor | Degraded | Invalid: ...


class SignalEngine(Protocol):
    def arm(self, wake_id: WakeId, spec: SignalRequest, context: ArmContext) -> ArmedSignal | Degraded | Invalid: ...

    def ingest(
        self,
        observations: Sequence[NormalizedObservation],
        source_commit: SourceCommit,
    ) -> Ingested | Degraded | Invalid: ...

    def evaluate(
        self,
        wake_id: WakeId,
        armed_signal: ArmedSignal,
        now: datetime,
        limits: EvaluationLimits,
    ) -> Matched | NotReady | Degraded | Invalid | Expired: ...


WakeSignalModule = SignalEngine


class ScriptedSourceAdapter:
    def __init__(
        self,
        contract: SourceContract,
        *,
        anchor: SourceAnchor | None = None,
        anchors: Sequence[SourceAnchor | Degraded | Invalid] | None = None,
    ) -> None:
        self._contract = contract
        configured = tuple(anchors or (() if anchor is None else (anchor,)))
        if not configured:
            raise ValueError("at least one anchor result is required")
        self._anchors = configured
        self.anchor_calls = 0

    def contract(self) -> SourceContract:
        return self._contract

    def establish_anchor(self, spec: SignalRequest, now: datetime) -> SourceAnchor | Degraded | Invalid:
        index = min(self.anchor_calls, len(self._anchors) - 1)
        self.anchor_calls += 1
        return self._anchors[index]


class InMemorySignalModule:
    def __init__(self) -> None:
        self._registrations: dict[str, tuple[str, ArmedSignal]] = {}
        self._preparations: dict[str, tuple[str, WakeId]] = {}
        self._contracts: dict[tuple[str, str], SourceContract] = {}
        self._receipts: dict[tuple[str, str, str, str], tuple[NormalizedObservation, ReceiptRef]] = {}
        self._checkpoints: dict[tuple[str, str], tuple[int, str]] = {}
        self._reservations: dict[WakeId, Matched] = {}
        self._next_sequence = 1

    def arm(self, wake_id: WakeId, spec: SignalRequest, context: ArmContext) -> ArmedSignal | Degraded | Invalid:
        contract = context.adapter.contract()
        invalid = _validate_signal(spec, contract)
        if invalid is not None:
            return invalid
        existing = self._registrations.get(context.idempotency_key)
        if existing is not None:
            fingerprint, armed = existing
            if fingerprint == context.intent_fingerprint:
                return armed
            return Invalid(armed.wake_id, "IDEMPOTENCY_CONFLICT", ("idempotency key already used",))
        prepared = self._preparations.get(context.idempotency_key)
        if prepared is not None:
            fingerprint, reserved_wake_id = prepared
            if fingerprint != context.intent_fingerprint:
                return Invalid(reserved_wake_id, "IDEMPOTENCY_CONFLICT", ("idempotency key already used",))
            wake_id = reserved_wake_id
        else:
            self._preparations[context.idempotency_key] = (context.intent_fingerprint, wake_id)
        anchor = context.adapter.establish_anchor(spec, context.registered_at)
        if isinstance(anchor, Degraded):
            return Degraded(wake_id, anchor.code, anchor.retry_at, anchor.evidence_ref)
        if isinstance(anchor, Invalid):
            return anchor
        armed = ArmedSignal(
            wake_id=wake_id,
            arm_id=ArmId(f"arm_{wake_id}"),
            spec=spec,
            anchor=anchor,
            registered_at=context.registered_at,
            expires_at=context.expires_at,
        )
        self._contracts[(contract.source, contract.source_instance)] = contract
        self._registrations[context.idempotency_key] = (context.intent_fingerprint, armed)
        return armed

    def ingest(
        self,
        observations: Sequence[NormalizedObservation],
        source_commit: SourceCommit,
    ) -> Ingested | Degraded | Invalid:
        source_key = (source_commit.source, source_commit.source_instance)
        if any((item.source, item.source_instance) != source_key for item in observations):
            return Invalid(None, "SOURCE_COMMIT_MISMATCH", ("source commit does not match observation batch",))
        previous_checkpoint = self._checkpoints.get(source_key)
        if previous_checkpoint is not None:
            previous_order, previous_value = previous_checkpoint
            if source_commit.checkpoint_order < previous_order:
                return Invalid(None, "CHECKPOINT_REGRESSION", ("source checkpoint order regressed",))
            if source_commit.checkpoint_order == previous_order and source_commit.checkpoint != previous_value:
                return Invalid(None, "CHECKPOINT_CONFLICT", ("source checkpoint content conflicts at the same order",))
        preexisting = set(self._receipts)
        staged: dict[tuple[str, str, str, str], NormalizedObservation] = {}
        for observation in observations:
            contract = self._contracts.get((observation.source, observation.source_instance))
            if contract is None:
                return Invalid(None, "SOURCE_NOT_CONFIGURED", ("source instance is not configured",))
            if (
                observation.kind not in contract.kinds
                or observation.subject not in contract.subjects
                or not observation.occurrence_namespace
                or not observation.occurrence_value
                or observation.verification.state not in {"verified", "pending", "rejected"}
                or not observation.verification.method
            ):
                return Invalid(
                    None,
                    "OBSERVATION_OUTSIDE_CONTRACT",
                    ("observation is outside the configured source contract",),
                )
            if (
                observation.evidence_ref is not None
                and len(observation.evidence_ref.encode("utf-8")) > contract.max_evidence_ref_bytes
            ):
                return Invalid(None, "EVIDENCE_LIMIT_EXCEEDED", ("observation evidence reference exceeds the source limit",))
            for name, value in observation.attributes.items():
                normalized_name = name.casefold()
                if any(part in normalized_name for part in ("authorization", "cookie", "password", "secret", "signature", "token")):
                    return Invalid(None, "ATTRIBUTE_NOT_ALLOWED", ("observation contains a forbidden attribute",))
                expected_type = contract.allowed_attributes.get(name)
                if expected_type is None or type(value) is not expected_type:
                    return Invalid(None, "ATTRIBUTE_NOT_ALLOWED", ("observation contains an unsupported attribute",))
            attribute_bytes = len(
                json.dumps(
                    dict(observation.attributes),
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            )
            if attribute_bytes > contract.max_attribute_bytes:
                return Invalid(None, "ATTRIBUTE_LIMIT_EXCEEDED", ("observation attributes exceed the source limit",))
            identity = (
                observation.source,
                observation.source_instance,
                observation.occurrence_namespace,
                observation.occurrence_value,
            )
            existing = self._receipts.get(identity)
            if existing is not None and existing[0] != observation:
                return Invalid(None, "OCCURRENCE_IDENTITY_CONFLICT", ("occurrence identity has different content",))
            earlier = staged.get(identity)
            if earlier is not None and earlier != observation:
                return Invalid(None, "OCCURRENCE_IDENTITY_CONFLICT", ("occurrence identity has different content",))
            staged[identity] = replace(
                observation,
                attributes=MappingProxyType(dict(observation.attributes)),
            )

        for identity, observation in staged.items():
            if identity in self._receipts:
                continue
            receipt = ReceiptRef(
                ReceiptId(f"event_{self._next_sequence:012d}"),
                self._next_sequence,
                False,
            )
            self._next_sequence += 1
            self._receipts[identity] = (observation, receipt)

        results: list[ReceiptRef] = []
        returned: set[tuple[str, str, str, str]] = set()
        for observation in observations:
            identity = (
                observation.source,
                observation.source_instance,
                observation.occurrence_namespace,
                observation.occurrence_value,
            )
            _stored, receipt = self._receipts[identity]
            was_duplicate = identity in preexisting or identity in returned
            results.append(ReceiptRef(receipt.receipt_id, receipt.local_sequence, was_duplicate))
            returned.add(identity)
        self._checkpoints[source_key] = (source_commit.checkpoint_order, source_commit.checkpoint)
        return Ingested(tuple(results), source_commit.checkpoint)

    def evaluate(
        self,
        wake_id: WakeId,
        armed_signal: ArmedSignal,
        now: datetime,
        limits: EvaluationLimits,
    ) -> Matched | NotReady | Degraded | Invalid | Expired:
        if wake_id != armed_signal.wake_id:
            return Invalid(wake_id, "INVALID_ARM", ("armed signal identity does not match",))
        existing = self._reservations.get(wake_id)
        if existing is not None:
            return existing
        if armed_signal.publication != "published":
            return Degraded(wake_id, "ARM_NOT_PUBLISHED", None)
        if armed_signal.expires_at is not None and now >= armed_signal.expires_at:
            return Expired(wake_id, armed_signal.expires_at)
        candidates: list[tuple[NormalizedObservation, ReceiptRef]] = []
        verification_pending = False
        for observation, receipt in self._receipts.values():
            if receipt.local_sequence <= armed_signal.anchor.local_after_sequence:
                continue
            if (
                observation.source,
                observation.source_instance,
                observation.kind,
                observation.subject,
            ) != (
                armed_signal.spec.source,
                armed_signal.spec.source_instance,
                armed_signal.spec.kind,
                armed_signal.spec.subject,
            ):
                continue
            if not _matches(observation, armed_signal.spec.where):
                continue
            if armed_signal.spec.verification == "required" and observation.verification.state != "verified":
                if observation.verification.state == "pending":
                    verification_pending = True
                continue
            candidates.append((observation, receipt))
        candidates.sort(key=lambda item: item[1].local_sequence)
        if len(candidates) > limits.max_candidates:
            return Degraded(wake_id, "EVALUATION_BUDGET_EXHAUSTED", None)
        if not candidates:
            if verification_pending:
                return Degraded(wake_id, "VERIFICATION_PENDING", None)
            return NotReady(wake_id, self._next_sequence - 1)
        observation, receipt = candidates[0]
        attribute_bytes = len(
            json.dumps(
                dict(observation.attributes),
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        )
        evidence_ref_bytes = len((observation.evidence_ref or "").encode("utf-8"))
        if (
            attribute_bytes > limits.max_attribute_bytes
            or evidence_ref_bytes > limits.max_evidence_ref_bytes
        ):
            return Degraded(wake_id, "EVALUATION_BUDGET_EXHAUSTED", None)
        matched = Matched(
            wake_id,
            MatchToken(f"match:{wake_id}:{receipt.receipt_id}"),
            EvidenceSummary(
                receipt.receipt_id,
                receipt.local_sequence,
                observation.evidence_ref,
                MappingProxyType(dict(observation.attributes)),
                observation.verification.state,
                observation.verification.method,
            ),
            now,
        )
        self._reservations[wake_id] = matched
        return matched


RegisterResult: TypeAlias = Registration | Degraded | Invalid
IngestResult: TypeAlias = Ingested | Degraded | Invalid
Evaluation: TypeAlias = Matched | NotReady | Degraded | Invalid | Expired


def _validate_signal(spec: SignalRequest, contract: SourceContract) -> Invalid | None:
    if type(spec.contract_version) is not int or spec.contract_version != 1:
        return _invalid_signal()
    if spec.source != contract.source or spec.source_instance != contract.source_instance:
        return _invalid_signal()
    if spec.kind not in contract.kinds or spec.subject not in contract.subjects:
        return _invalid_signal()
    if (spec.semantics, spec.condition) not in {
        ("occurrence", "occurs"),
        ("state", "holds"),
        ("state", "becomes"),
    }:
        return _invalid_signal()
    if len(spec.where) > contract.max_clauses:
        return _invalid_signal()
    for clause in spec.where:
        expected_type = contract.allowed_attributes.get(clause.field)
        if expected_type is None:
            return _invalid_signal()
        if isinstance(clause, Eq):
            if type(clause.value) is not expected_type:
                return _invalid_signal()
        elif isinstance(clause, In):
            if not clause.values or len(clause.values) > contract.max_in_values:
                return _invalid_signal()
            if any(type(value) is not expected_type for value in clause.values):
                return _invalid_signal()
        else:
            return _invalid_signal()
    return None


def _invalid_signal() -> Invalid:
    return Invalid(None, "INVALID_SIGNAL", ("signal specification is invalid",))


def _matches(observation: NormalizedObservation, clauses: Sequence[WhereClause]) -> bool:
    for clause in clauses:
        value = observation.attributes.get(clause.field)
        if isinstance(clause, Eq) and value != clause.value:
            return False
        if isinstance(clause, In) and value not in clause.values:
            return False
    return True
