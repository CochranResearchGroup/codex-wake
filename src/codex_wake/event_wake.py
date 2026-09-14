from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from datetime import datetime
from typing import Callable, Iterable

from .signals import (
    ArmContext,
    Degraded,
    Invalid,
    RegisterResult,
    Registration,
    SignalSourceAdapter,
    WakeSignalModule,
    WakeId,
    WakeIntent,
)


class EventWake:
    def __init__(
        self,
        module: WakeSignalModule,
        *,
        adapters: Iterable[SignalSourceAdapter],
        clock: Callable[[], datetime],
        id_factory: Callable[[], str],
    ) -> None:
        self._module = module
        self._adapters = {(item.contract().source, item.contract().source_instance): item for item in adapters}
        self._clock = clock
        self._id_factory = id_factory

    def register(self, intent: WakeIntent, *, idempotency_key: str) -> RegisterResult:
        adapter = self._adapters.get((intent.when.source, intent.when.source_instance))
        if adapter is None:
            return Invalid(None, "INVALID_SIGNAL", ("signal specification is invalid",))
        now = self._clock()
        armed = self._module.arm(
            WakeId(self._id_factory()),
            intent.when,
            ArmContext(
                idempotency_key=idempotency_key,
                intent_fingerprint=_intent_fingerprint(intent),
                registered_at=now,
                expires_at=intent.expires_at,
                resume=intent.resume,
                adapter=adapter,
            ),
        )
        if isinstance(armed, (Degraded, Invalid)):
            return armed
        return Registration(
            wake_id=armed.wake_id,
            arm_id=armed.arm_id,
            contract_version=1,
            source=armed.spec.source,
            source_instance=armed.spec.source_instance,
            subject=armed.spec.subject,
            registered_at=armed.registered_at,
            recovery=armed.anchor.recovery,
        )


def _intent_fingerprint(intent: WakeIntent) -> str:
    payload = {
        "when": {
            "contract_version": intent.when.contract_version,
            "source": intent.when.source,
            "source_instance": intent.when.source_instance,
            "semantics": intent.when.semantics,
            "kind": intent.when.kind,
            "subject": intent.when.subject,
            "condition": intent.when.condition,
            "where": [asdict(item) for item in intent.when.where],
            "verification": intent.when.verification,
        },
        "resume": {
            "prompt": intent.resume.prompt,
            "cwd": str(intent.resume.cwd),
            "target": dict(intent.resume.target),
        },
        "expires_at": intent.expires_at.isoformat() if intent.expires_at else None,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=list).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
