"""Restart-correct, read-only process-termination signal adapter.

The observer is deliberately injected.  Product integration may implement its
fixed-field ``/proc`` read behind that boundary, while tests never inspect or
mutate a live process.  This adapter neither discovers processes nor retains
command lines, environments, exit codes, or an asserted exit timestamp.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime
from itertools import islice
from types import MappingProxyType
from typing import Callable, Iterable, Literal

from .runtime_signals import RuntimeDiagnostic, RuntimeSourceDescriptor, RuntimeSourceRegistry
from .signals import (
    ArmedSignal,
    Degraded,
    Eq,
    EvaluationLimits,
    Ingested,
    Invalid,
    Matched,
    NormalizedObservation,
    SourceAnchor,
    SourceCommit,
    SourceContract,
    SourceInstanceReconcileResult,
    SourceReconcileResult,
    SignalRequest,
    Verification,
)


_DISAPPEARANCE_CLASSIFICATION = "exact_identity_absent_after_alive_baseline"


@dataclass(frozen=True, slots=True)
class ProcessExitSample:
    """Sanitized result of one bounded exact-identity observation.

    ``disappeared`` is accepted only when a trusted fixed-field observer has
    positively classified the absence against the persisted alive baseline.
    It retains only the current boot identifier because the process directory
    no longer exists; a changed boot is therefore never classified as an exit.
    """

    state: Literal["alive", "zombie", "disappeared"]
    boot_id: str | None
    pid: int | None
    start_time_ticks: int | None
    owner_uid: int | None
    disappearance: str | None = None

    @classmethod
    def alive(cls, *, boot_id: str, pid: int, start_time_ticks: int, owner_uid: int) -> ProcessExitSample:
        return cls("alive", boot_id, pid, start_time_ticks, owner_uid)

    @classmethod
    def zombie(cls, *, boot_id: str, pid: int, start_time_ticks: int, owner_uid: int) -> ProcessExitSample:
        return cls("zombie", boot_id, pid, start_time_ticks, owner_uid)

    @classmethod
    def disappeared(cls, *, boot_id: str) -> ProcessExitSample:
        return cls("disappeared", boot_id, None, None, None, _DISAPPEARANCE_CLASSIFICATION)

    def valid(self) -> bool:
        if self.state in {"alive", "zombie"}:
            return (
                self.disappearance is None
                and type(self.boot_id) is str
                and type(self.pid) is int
                and self.pid >= 1
                and type(self.start_time_ticks) is int
                and self.start_time_ticks >= 1
                and type(self.owner_uid) is int
                and self.owner_uid >= 0
            )
        return (
            self.state == "disappeared"
            and type(self.boot_id) is str
            and self.pid is None
            and self.start_time_ticks is None
            and self.owner_uid is None
            and self.disappearance == _DISAPPEARANCE_CLASSIFICATION
        )

    def identity(self) -> dict[str, str | int] | None:
        if self.state == "disappeared":
            return None
        return {
            "boot_id": self.boot_id,
            "pid": self.pid,
            "start_time_ticks": self.start_time_ticks,
            "owner_uid": self.owner_uid,
        }


class ProcessExitAdapter:
    """One descriptor-bound same-effective-UID process exit source."""

    def __init__(
        self,
        descriptor: RuntimeSourceDescriptor,
        registry: RuntimeSourceRegistry,
        observer: Callable[[], ProcessExitSample],
        effective_uid: Callable[[], int] = os.geteuid,
    ) -> None:
        if type(descriptor) is not RuntimeSourceDescriptor or descriptor.kind != "process.exit":
            raise ValueError("process exit adapter requires a process descriptor")
        if not callable(observer) or not callable(effective_uid):
            raise ValueError("process exit adapter observer is invalid")
        self.descriptor = descriptor
        self.registry = registry
        self._observer = observer
        self._effective_uid = effective_uid
        self.source_instance = "runtime-" + descriptor.fingerprint
        self.subject = "process:" + descriptor.fingerprint
        self.diagnostic = RuntimeDiagnostic("RUNTIME_NOT_OBSERVED", descriptor.fingerprint, None)

    def _degraded(self, code: str) -> Degraded:
        self.diagnostic = RuntimeDiagnostic(code, self.descriptor.fingerprint, self.diagnostic.observed_at)
        return Degraded(None, code, None)

    def _authorized(self) -> bool:
        try:
            effective_uid = self._effective_uid()
            return (
                type(effective_uid) is int
                and effective_uid == self.descriptor.resource["owner_uid"]
                and self.registry.authorized(self.descriptor)
            )
        except Exception:
            return False

    def contract(self) -> SourceContract:
        return SourceContract(
            "runtime",
            self.source_instance,
            frozenset({"process.exit"}),
            frozenset({self.subject}),
            MappingProxyType({"state": str}),
            max_clauses=1,
            max_attribute_bytes=64,
            max_evidence_ref_bytes=96,
        )

    def request(self) -> SignalRequest:
        return SignalRequest(
            1,
            "runtime",
            self.source_instance,
            "occurrence",
            "process.exit",
            self.subject,
            "occurs",
            (Eq("state", "terminated"),),
            "required",
        )

    def _valid_request(self, spec: SignalRequest) -> bool:
        return (
            type(spec) is SignalRequest
            and type(spec.contract_version) is int
            and type(spec.where) is tuple
            and len(spec.where) == 1
            and type(spec.where[0]) is Eq
            and spec == self.request()
        )

    def _sample(self, now: datetime) -> ProcessExitSample | Degraded:
        if not self._authorized():
            return self._degraded("RUNTIME_AUTHORIZATION_DENIED")
        try:
            sample = self._observer()
        except Exception:
            return self._degraded("RUNTIME_OBSERVATION_UNAVAILABLE")
        if not self._authorized():
            return self._degraded("RUNTIME_AUTHORIZATION_DENIED")
        if type(sample) is not ProcessExitSample or not sample.valid():
            return self._degraded("RUNTIME_OBSERVATION_UNAVAILABLE")
        self.diagnostic = RuntimeDiagnostic("RUNTIME_READY", self.descriptor.fingerprint, now)
        return sample

    def _exact_identity(self, sample: ProcessExitSample) -> bool:
        return sample.identity() == dict(self.descriptor.resource)

    def establish_anchor(self, spec: SignalRequest, now: datetime) -> SourceAnchor | Degraded | Invalid:
        if not self._valid_request(spec) or now.tzinfo is None or now.utcoffset() is None:
            return Invalid(None, "RUNTIME_REQUEST_INVALID", ("process request is invalid",))
        sample = self._sample(now)
        if isinstance(sample, Degraded):
            return sample
        if sample.state == "disappeared" or not self._exact_identity(sample):
            return self._degraded("RUNTIME_OBSERVATION_AMBIGUOUS")
        if sample.state == "zombie":
            return self._degraded("RUNTIME_BASELINE_MATCHES")
        return SourceAnchor(
            0,
            "process-exit:" + self.descriptor.fingerprint,
            MappingProxyType({
                "descriptor": json.dumps(self.descriptor.payload(), sort_keys=True, separators=(",", ":")),
                "state": "alive",
            }),
            "state_recheck",
        )

    @classmethod
    def restore(
        cls,
        armed: ArmedSignal,
        registry: RuntimeSourceRegistry,
        observer: Callable[[], ProcessExitSample],
        effective_uid: Callable[[], int] = os.geteuid,
    ) -> ProcessExitAdapter:
        try:
            raw = armed.anchor.baseline["descriptor"]
            if type(raw) is not str or len(raw.encode()) > 1024:
                raise ValueError
            adapter = cls(RuntimeSourceDescriptor.parse(json.loads(raw)), registry, observer, effective_uid)
            if not adapter._valid_arm(armed):
                raise ValueError
            return adapter
        except (AttributeError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            raise ValueError("process exit anchor is invalid") from None

    def _valid_arm(self, armed: ArmedSignal) -> bool:
        try:
            baseline = armed.anchor.baseline
            return (
                type(armed) is ArmedSignal
                and self._valid_request(armed.spec)
                and armed.anchor.source_anchor == "process-exit:" + self.descriptor.fingerprint
                and armed.anchor.recovery == "state_recheck"
                and set(baseline) == {"descriptor", "state"}
                and baseline["state"] == "alive"
                and type(baseline["descriptor"]) is str
                and len(baseline["descriptor"].encode()) <= 1024
                and RuntimeSourceDescriptor.parse(json.loads(baseline["descriptor"])) == self.descriptor
            )
        except (AttributeError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            return False

    def runner(self, armed_signals: Iterable[ArmedSignal]) -> ProcessExitRunner:
        return ProcessExitRunner(self, armed_signals)

    def _checkpoint(self, state: str, previous: SourceCommit | None, now: datetime) -> SourceCommit:
        return SourceCommit(
            "runtime",
            self.source_instance,
            json.dumps(
                {"fingerprint": self.descriptor.fingerprint, "state": state},
                sort_keys=True,
                separators=(",", ":"),
            ),
            previous.checkpoint_order + 1 if previous is not None else 1,
            now,
        )

    def _previous_state(self, previous: SourceCommit | None) -> str | Degraded | None:
        if previous is None:
            return None
        try:
            if type(previous.checkpoint) is not str or len(previous.checkpoint.encode()) > 256:
                raise ValueError
            payload = json.loads(previous.checkpoint)
            if set(payload) != {"fingerprint", "state"} or payload["fingerprint"] != self.descriptor.fingerprint:
                raise ValueError
            if payload["state"] not in {"alive", "zombie", "disappeared"}:
                raise ValueError
            return payload["state"]
        except (TypeError, ValueError, json.JSONDecodeError):
            return self._degraded("RUNTIME_CHECKPOINT_INVALID")

    def reconcile(
        self,
        module,
        armed_signals: tuple[ArmedSignal, ...],
        now: datetime,
        limits: EvaluationLimits,
    ) -> SourceReconcileResult:
        def report(scanned: int = 0, observed: int = 0, degraded: int = 0) -> SourceReconcileResult:
            return SourceReconcileResult(
                "runtime", scanned, observed, degraded,
                (SourceInstanceReconcileResult("runtime", self.source_instance, scanned, observed, degraded),),
            )

        if (
            now.tzinfo is None
            or now.utcoffset() is None
            or type(limits.max_candidates) is not int
            or limits.max_candidates <= 0
            or len(armed_signals) > min(limits.max_candidates, 128)
        ):
            self._degraded("RUNTIME_RESOURCE_LIMIT")
            return report(degraded=1)
        if not self._authorized():
            self._degraded("RUNTIME_AUTHORIZATION_DENIED")
            return report(degraded=1)
        active: list[ArmedSignal] = []
        for supplied in armed_signals:
            if not self._valid_arm(supplied):
                self._degraded("RUNTIME_ANCHOR_INVALID")
                return report(degraded=1)
            try:
                armed = module.load_armed_signal(supplied.wake_id)
            except Exception:
                self._degraded("RUNTIME_CHECKPOINT_UNAVAILABLE")
                return report(degraded=1)
            if armed is None:
                continue
            if not self._valid_arm(armed) or armed.arm_id != supplied.arm_id:
                self._degraded("RUNTIME_ANCHOR_INVALID")
                return report(degraded=1)
            if armed.expires_at is None or now < armed.expires_at:
                active.append(armed)
        if not active:
            return report()
        previous = module.source_checkpoint("runtime", self.source_instance)
        if isinstance(previous, Degraded):
            self._degraded("RUNTIME_CHECKPOINT_UNAVAILABLE")
            return report(degraded=1)
        previous_state = self._previous_state(previous)
        if isinstance(previous_state, Degraded):
            return report(degraded=1)
        sample = self._sample(now)
        if isinstance(sample, Degraded):
            return report(scanned=1, degraded=1)
        if sample.state == "disappeared" and sample.boot_id != self.descriptor.resource["boot_id"]:
            self._degraded("RUNTIME_OBSERVATION_AMBIGUOUS")
            return report(scanned=1, degraded=1)
        if sample.state != "disappeared" and not self._exact_identity(sample):
            self._degraded("RUNTIME_OBSERVATION_AMBIGUOUS")
            return report(scanned=1, degraded=1)
        if previous_state in {"zombie", "disappeared"} and sample.state == "alive":
            self._degraded("RUNTIME_OBSERVATION_AMBIGUOUS")
            return report(scanned=1, degraded=1)
        terminated = sample.state in {"zombie", "disappeared"}
        was_terminated = previous_state in {"zombie", "disappeared"}
        if sample.state == previous_state:
            return report(scanned=1)
        observations = ()
        if terminated and not was_terminated:
            observations = (
                NormalizedObservation(
                    "runtime",
                    self.source_instance,
                    "process.exit",
                    self.subject,
                    "process-exit-v1",
                    self.descriptor.fingerprint + ":terminated",
                    now,
                    now,
                    MappingProxyType({"state": "terminated"}),
                    Verification("verified", "exact_identity_state_recheck"),
                    "process:" + self.descriptor.fingerprint,
                ),
            )
        if observations and (limits.max_attribute_bytes < 24 or limits.max_evidence_ref_bytes < 72):
            self._degraded("RUNTIME_RESOURCE_LIMIT")
            return report(scanned=1, degraded=1)
        if not self._authorized():
            self._degraded("RUNTIME_AUTHORIZATION_DENIED")
            return report(scanned=1, degraded=1)
        outcome = module.ingest(observations, self._checkpoint(sample.state, previous, now))
        if not isinstance(outcome, Ingested):
            self._degraded("RUNTIME_INGEST_UNAVAILABLE")
            return report(scanned=1, degraded=1)
        return report(scanned=1, observed=sum(not receipt.duplicate for receipt in outcome.receipts))

    def evaluate(self, module, armed: ArmedSignal, now: datetime, limits: EvaluationLimits):
        if not self._authorized():
            return self._degraded("RUNTIME_AUTHORIZATION_DENIED")
        if not self._valid_arm(armed):
            return Invalid(armed.wake_id, "RUNTIME_ANCHOR_INVALID", ("process exit anchor is invalid",))
        outcome = module.evaluate(armed.wake_id, armed, now, limits)
        if isinstance(outcome, Matched):
            if not self._authorized():
                return self._degraded("RUNTIME_AUTHORIZATION_DENIED")
            publication = module.reconcile_match_publication(armed.wake_id)
            if publication is not True:
                return self._degraded("RUNTIME_PUBLICATION_UNAVAILABLE")
        return outcome


class ProcessExitRunner:
    """Protocol-shaped bounded runner for explicit daemon injection."""

    def __init__(self, adapter: ProcessExitAdapter, armed_signals: Iterable[ArmedSignal]) -> None:
        self.adapter = adapter
        self.armed_signals = tuple(islice(armed_signals, 129))
        self.last_result: SourceReconcileResult | None = None

    def reconcile(self, module, now: datetime, limits: EvaluationLimits) -> SourceReconcileResult:
        self.last_result = self.adapter.reconcile(module, self.armed_signals, now, limits)
        return self.last_result
