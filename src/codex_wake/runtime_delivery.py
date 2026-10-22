"""Runtime delivery values; scheduling and durable attempts stay in the core.

Version 1 is an in-memory interface, not a new persisted wake-record schema.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Mapping, Protocol


CapabilityState = Literal["supported", "unsupported", "not_qualified", "unavailable"]


class RuntimeTargetError(ValueError):
    def __init__(self, state: str, reason: str):
        super().__init__(reason)
        self.state = state
        self.reason = reason


@dataclass(frozen=True)
class RuntimeRecipient:
    runtime: str
    session_id: str
    binding: Mapping[str, object] = field(repr=False)
    version: int = 1


@dataclass(frozen=True)
class RuntimeCapability:
    state: CapabilityState
    reason: str


@dataclass(frozen=True)
class RuntimeObservation:
    state: str
    reason: str
    capabilities: Mapping[str, RuntimeCapability]
    resumed: bool = False

    def summary(self, recipient: RuntimeRecipient) -> dict:
        # Do not expose opaque binding data, socket paths or credentials here.
        return dict(
            version=recipient.version, runtime=recipient.runtime,
            session_id=recipient.session_id, state=self.state, reason=self.reason,
            capabilities={name: dict(state=value.state, reason=value.reason)
                          for name, value in self.capabilities.items()},
        )


@dataclass(frozen=True)
class RuntimeSubmission:
    state: Literal["accepted", "uncertain", "not_sent"]
    receipt_id: str | None = None
    evidence_kind: str = "none"
    reason: str | None = None
    failure: dict | None = None
    exception_type: str | None = None


@dataclass(frozen=True)
class RuntimeReconciliation:
    evidence: dict | None = None
    reason: str | None = None


class RuntimeAdapter(Protocol):
    def resolve(self, target: Mapping[str, object]) -> RuntimeRecipient: ...
    def observe(self, recipient: RuntimeRecipient) -> RuntimeObservation: ...
    def submit(self, recipient: RuntimeRecipient, prompt: str) -> RuntimeSubmission: ...
    def reconcile(self, recipient: RuntimeRecipient, prompt: str) -> RuntimeReconciliation: ...
