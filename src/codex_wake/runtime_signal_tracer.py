"""Hermetic runtime-source tracer; never installed as a default source.

This fixture adapter proves the authorization and journal boundaries using an
injected bounded sample. Real adapters supply their own resource observation,
identity rules, and restart policy. All publication uses the existing journal.

Observers are trusted product code. The lifecycle timeout is wake expiration
and cancellation enforced by the durable module, not preemptive cancellation
of arbitrary Python callbacks. Real adapters must bound their backend calls.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType
from typing import Callable, Iterable

from .runtime_signals import RuntimeDiagnostic, RuntimeSourceDescriptor, RuntimeSourceRegistry
from .signals import (
    ArmedSignal, Degraded, Eq, EvaluationLimits, Ingested, Invalid,
    Matched, NormalizedObservation, SourceAnchor, SourceCommit, SourceContract,
    SourceInstanceReconcileResult, SourceReconcileResult, SignalRequest, Verification,
)


@dataclass(frozen=True, slots=True)
class TracerSample:
    state: str
    generation: int

    def valid(self) -> bool:
        return (type(self.state) is str and self.state in {"waiting", "ready"}
                and type(self.generation) is int and 0 <= self.generation <= 2**63 - 1)


class RuntimeSignalTracer:
    """One exact fake resource. Authorizers and observers are trusted code."""

    def __init__(self, descriptor: RuntimeSourceDescriptor, registry: RuntimeSourceRegistry,
                 observer: Callable[[], TracerSample]) -> None:
        if type(descriptor) is not RuntimeSourceDescriptor or descriptor.kind != "tracer.state":
            raise ValueError("tracer requires a tracer descriptor")
        self.descriptor = descriptor
        self.registry = registry
        self._observer = observer
        self.source_instance = "runtime-" + descriptor.fingerprint
        self.subject = "resource:" + descriptor.fingerprint
        self.diagnostic = RuntimeDiagnostic("RUNTIME_NOT_OBSERVED", descriptor.fingerprint, None)

    def _degraded(self, code: str) -> Degraded:
        self.diagnostic = RuntimeDiagnostic(code, self.descriptor.fingerprint, self.diagnostic.observed_at)
        return Degraded(None, code, None)

    def _authorized(self) -> bool:
        return self.registry.authorized(self.descriptor)

    def contract(self) -> SourceContract:
        return SourceContract("runtime", self.source_instance, frozenset({"tracer.state"}),
            frozenset({self.subject}), MappingProxyType({"state": str, "generation": int}),
            max_clauses=1, max_attribute_bytes=128, max_evidence_ref_bytes=96)

    def request(self) -> SignalRequest:
        return SignalRequest(1, "runtime", self.source_instance, "state", "tracer.state",
            self.subject, "becomes", (Eq("state", "ready"),), "required")

    def _valid_request(self, spec: SignalRequest) -> bool:
        return (type(spec) is SignalRequest and type(spec.contract_version) is int
                and type(spec.where) is tuple and len(spec.where) == 1
                and type(spec.where[0]) is Eq and spec == self.request())

    def _sample(self, now: datetime) -> TracerSample | Degraded:
        if not self._authorized():
            return self._degraded("RUNTIME_AUTHORIZATION_DENIED")
        try:
            sampled = self._observer()
        except Exception:
            return self._degraded("RUNTIME_OBSERVATION_UNAVAILABLE")
        if not self._authorized():
            return self._degraded("RUNTIME_AUTHORIZATION_DENIED")
        if type(sampled) is not TracerSample or not sampled.valid():
            return self._degraded("RUNTIME_OBSERVATION_UNAVAILABLE")
        self.diagnostic = RuntimeDiagnostic("RUNTIME_READY", self.descriptor.fingerprint, now)
        return sampled

    def establish_anchor(self, spec: SignalRequest, now: datetime):
        if not self._valid_request(spec) or now.tzinfo is None or now.utcoffset() is None:
            return Invalid(None, "RUNTIME_REQUEST_INVALID", ("runtime request is invalid",))
        sampled = self._sample(now)
        if isinstance(sampled, Degraded):
            return sampled
        if sampled.state == "ready":
            return self._degraded("RUNTIME_BASELINE_MATCHES")
        return SourceAnchor(0, "runtime:" + self.descriptor.fingerprint, MappingProxyType({
            "descriptor": json.dumps(self.descriptor.payload(), sort_keys=True, separators=(",", ":")),
            "state": sampled.state, "generation": sampled.generation}), "state_recheck")

    @classmethod
    def restore(cls, armed: ArmedSignal, registry: RuntimeSourceRegistry,
                observer: Callable[[], TracerSample]) -> RuntimeSignalTracer:
        try:
            raw = armed.anchor.baseline["descriptor"]
            if type(raw) is not str or len(raw.encode()) > 1024:
                raise ValueError
            descriptor = RuntimeSourceDescriptor.parse(json.loads(raw))
            tracer = cls(descriptor, registry, observer)
            if not tracer._valid_arm(armed):
                raise ValueError
            return tracer
        except (KeyError, TypeError, ValueError, AttributeError):
            raise ValueError("runtime anchor is invalid") from None

    def _valid_arm(self, armed: ArmedSignal) -> bool:
        try:
            baseline = armed.anchor.baseline
            return (type(armed) is ArmedSignal and self._valid_request(armed.spec)
                and armed.anchor.source_anchor == "runtime:" + self.descriptor.fingerprint
                and set(baseline) == {"descriptor", "state", "generation"}
                and type(baseline["descriptor"]) is str and len(baseline["descriptor"].encode()) <= 1024
                and RuntimeSourceDescriptor.parse(json.loads(baseline["descriptor"])) == self.descriptor
                and baseline["state"] == "waiting"
                and TracerSample(baseline["state"], baseline["generation"]).valid())
        except (AttributeError, KeyError, TypeError, ValueError):
            return False

    def runner(self, armed_signals: Iterable[ArmedSignal]) -> RuntimeTracerRunner:
        return RuntimeTracerRunner(self, armed_signals)

    def reconcile(self, module, armed_signals: tuple[ArmedSignal, ...], now: datetime,
                  limits: EvaluationLimits) -> SourceReconcileResult:
        def report(scanned=0, observed=0, degraded=0):
            return SourceReconcileResult("runtime", scanned, observed, degraded,
                (SourceInstanceReconcileResult("runtime", self.source_instance, scanned, observed, degraded),))
        if (now.tzinfo is None or now.utcoffset() is None or type(limits.max_candidates) is not int
                or limits.max_candidates <= 0 or len(armed_signals) > min(limits.max_candidates, 128)):
            self._degraded("RUNTIME_RESOURCE_LIMIT")
            return report(degraded=1)
        if not self._authorized():
            self._degraded("RUNTIME_AUTHORIZATION_DENIED")
            return report(degraded=1)
        active = []
        for supplied in armed_signals:
            if not self._valid_arm(supplied):
                self._degraded("RUNTIME_ANCHOR_INVALID")
                return report(degraded=1)
            # Durable state owns cancellation and expiration, never stale input.
            armed = module.load_armed_signal(supplied.wake_id)
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
        previous_sample = None
        if previous is not None:
            try:
                if type(previous.checkpoint) is not str or len(previous.checkpoint.encode()) > 256:
                    raise ValueError
                payload = json.loads(previous.checkpoint)
                if set(payload) != {"state", "generation", "fingerprint"} or payload["fingerprint"] != self.descriptor.fingerprint:
                    raise ValueError
                previous_sample = TracerSample(payload["state"], payload["generation"])
                if not previous_sample.valid():
                    raise ValueError
            except (KeyError, TypeError, ValueError):
                self._degraded("RUNTIME_CHECKPOINT_INVALID")
                return report(degraded=1)
        sampled = self._sample(now)
        if isinstance(sampled, Degraded):
            return report(scanned=1, degraded=1)
        baseline_generation = min(armed.anchor.baseline["generation"] for armed in active)
        floor = previous_sample.generation if previous_sample is not None else baseline_generation
        prior_state = previous_sample.state if previous_sample is not None else "waiting"
        if sampled.generation < floor or (sampled.generation == floor and sampled.state != prior_state):
            self._degraded("RUNTIME_OBSERVATION_AMBIGUOUS")
            return report(scanned=1, degraded=1)
        if previous_sample == sampled:
            return report(scanned=1)
        observations = ()
        if sampled.state == "ready" and sampled.generation > floor and (previous_sample is None or previous_sample.state != "ready"):
            observations = (NormalizedObservation("runtime", self.source_instance, "tracer.state", self.subject,
                "runtime-tracer-v1", f"{self.descriptor.fingerprint}:{sampled.generation}", now, now,
                MappingProxyType({"state": sampled.state, "generation": sampled.generation}),
                Verification("verified", "provider_free_state_recheck"), "runtime:" + self.descriptor.fingerprint),)
        if observations and (limits.max_attribute_bytes < 64 or limits.max_evidence_ref_bytes < 72):
            self._degraded("RUNTIME_RESOURCE_LIMIT")
            return report(scanned=1, degraded=1)
        if not self._authorized():
            self._degraded("RUNTIME_AUTHORIZATION_DENIED")
            return report(scanned=1, degraded=1)
        checkpoint = SourceCommit("runtime", self.source_instance,
            json.dumps({"state": sampled.state, "generation": sampled.generation,
                "fingerprint": self.descriptor.fingerprint}, sort_keys=True, separators=(",", ":")),
            previous.checkpoint_order + 1 if previous else 1, now)
        outcome = module.ingest(observations, checkpoint)
        if not isinstance(outcome, Ingested):
            self._degraded("RUNTIME_INGEST_UNAVAILABLE")
            return report(scanned=1, degraded=1)
        return report(scanned=1, observed=sum(not r.duplicate for r in outcome.receipts))

    def evaluate(self, module, armed: ArmedSignal, now: datetime, limits: EvaluationLimits):
        if not self._authorized():
            return self._degraded("RUNTIME_AUTHORIZATION_DENIED")
        if not self._valid_arm(armed):
            return Invalid(armed.wake_id, "RUNTIME_ANCHOR_INVALID", ("runtime anchor is invalid",))
        outcome = module.evaluate(armed.wake_id, armed, now, limits)
        if isinstance(outcome, Matched):
            if not self._authorized():
                return self._degraded("RUNTIME_AUTHORIZATION_DENIED")
            publication = module.reconcile_match_publication(armed.wake_id)
            if publication is not True:
                return self._degraded("RUNTIME_PUBLICATION_UNAVAILABLE")
        return outcome


class RuntimeTracerRunner:
    """Protocol-shaped runner for explicit fixture injection into the daemon."""

    def __init__(self, tracer: RuntimeSignalTracer, armed_signals: Iterable[ArmedSignal]):
        self.tracer = tracer
        # Stop consuming even an unbounded caller iterable at the fixed ceiling.
        from itertools import islice
        self.armed_signals = tuple(islice(armed_signals, 129))
        self.last_result: SourceReconcileResult | None = None

    def reconcile(self, module, now: datetime, limits: EvaluationLimits) -> SourceReconcileResult:
        self.last_result = self.tracer.reconcile(module, self.armed_signals, now, limits)
        return self.last_result
