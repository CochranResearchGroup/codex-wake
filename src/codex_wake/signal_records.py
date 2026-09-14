from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable, Literal

from .signals import ArmedSignal, Eq, Resume


SIGNAL_RECORD_SCHEMA_VERSION = 2


@dataclass(frozen=True, slots=True)
class ManagedReaderCapability:
    wake_root: Path
    reader_id: str
    generation: int
    schema_versions: frozenset[int]
    active: bool


@dataclass(frozen=True, slots=True)
class PublicationResult:
    outcome: Literal["applied", "missing", "conflict", "unavailable"]
    path: Path | None = None


class WakeRecordPublisher:
    """Durably projects exact signal-record bytes into one managed wake root."""

    def __init__(
        self,
        wake_root: Path,
        capability: ManagedReaderCapability,
        *,
        checkpoint: Callable[[str], None] | None = None,
    ) -> None:
        self.wake_root = Path(wake_root).resolve()
        self.capability = capability
        self._checkpoint = checkpoint or (lambda _name: None)

    def capability_code(self) -> str | None:
        capability = self.capability
        try:
            capability_root = Path(capability.wake_root).resolve()
        except OSError:
            return "READER_CAPABILITY_UNAVAILABLE"
        if (
            capability_root != self.wake_root
            or not capability.active
            or not capability.reader_id
            or capability.generation < 1
            or SIGNAL_RECORD_SCHEMA_VERSION not in capability.schema_versions
        ):
            return "READER_CAPABILITY_UNAVAILABLE"
        return None

    def apply(self, payload_json: str, payload_sha256: str) -> PublicationResult:
        if self.capability_code() is not None:
            return PublicationResult("unavailable")
        try:
            payload = json.loads(payload_json)
            wake_id = payload["id"]
            status = payload["status"]
            if (
                not isinstance(wake_id, str)
                or not wake_id
                or status != "pending"
                or payload.get("schema_version") != SIGNAL_RECORD_SCHEMA_VERSION
            ):
                return PublicationResult("conflict")
            expected = (payload_json + "\n").encode("utf-8")
            if hashlib.sha256(expected).hexdigest() != payload_sha256:
                return PublicationResult("conflict")
            final_path = self.wake_root / status / f"{wake_id}.json"
            if final_path.exists():
                return PublicationResult(
                    "applied" if final_path.read_bytes() == expected else "conflict",
                    final_path,
                )
            final_path.parent.mkdir(parents=True, exist_ok=True)
            temp_path: Path | None = None
            try:
                with tempfile.NamedTemporaryFile(
                    mode="wb",
                    dir=final_path.parent,
                    prefix=f".{wake_id}.",
                    suffix=".json.tmp",
                    delete=False,
                ) as handle:
                    temp_path = Path(handle.name)
                    handle.write(expected)
                    handle.flush()
                    self._checkpoint("after_temp_write")
                    os.fsync(handle.fileno())
                    self._checkpoint("after_file_fsync")
                os.replace(temp_path, final_path)
                temp_path = None
                self._checkpoint("after_replace")
                directory_fd = os.open(
                    final_path.parent,
                    os.O_RDONLY | getattr(os, "O_DIRECTORY", 0),
                )
                try:
                    os.fsync(directory_fd)
                finally:
                    os.close(directory_fd)
                self._checkpoint("after_directory_fsync")
                return PublicationResult("applied", final_path)
            finally:
                if temp_path is not None:
                    temp_path.unlink(missing_ok=True)
        except (OSError, TypeError, ValueError, KeyError):
            return PublicationResult("unavailable")

    def inspect(self, payload_json: str, payload_sha256: str) -> PublicationResult:
        if self.capability_code() is not None:
            return PublicationResult("unavailable")
        try:
            payload = json.loads(payload_json)
            wake_id = payload["id"]
            status = payload["status"]
            final_path = self.wake_root / status / f"{wake_id}.json"
            if not final_path.exists():
                return PublicationResult("missing", final_path)
            expected = (payload_json + "\n").encode("utf-8")
            if hashlib.sha256(expected).hexdigest() != payload_sha256:
                return PublicationResult("conflict", final_path)
            return PublicationResult(
                "applied" if final_path.read_bytes() == expected else "conflict",
                final_path,
            )
        except (OSError, TypeError, ValueError, KeyError):
            return PublicationResult("conflict")


def build_signal_record(
    armed: ArmedSignal,
    resume: Resume,
    *,
    journal_uuid: str,
    revision: int,
) -> tuple[str, str]:
    timestamp = _format_time(armed.registered_at)
    predicate = {
        "type": "signal",
        "contract_version": armed.spec.contract_version,
        "arm_id": str(armed.arm_id),
        "source": armed.spec.source,
        "source_instance": armed.spec.source_instance,
        "semantics": armed.spec.semantics,
        "kind": armed.spec.kind,
        "subject": armed.spec.subject,
        "condition": armed.spec.condition,
        "where": [
            {"op": "eq", **asdict(clause)}
            if isinstance(clause, Eq)
            else {"op": "in", **asdict(clause)}
            for clause in armed.spec.where
        ],
        "verification": armed.spec.verification,
        "anchor": {
            "local_after_sequence": armed.anchor.local_after_sequence,
            "source_anchor": armed.anchor.source_anchor,
            "baseline": dict(armed.anchor.baseline),
            "recovery": armed.anchor.recovery,
        },
    }
    payload = {
        "schema_version": SIGNAL_RECORD_SCHEMA_VERSION,
        "id": str(armed.wake_id),
        "arm_id": str(armed.arm_id),
        "journal_uuid": journal_uuid,
        "record_revision": revision,
        "created_at": timestamp,
        "updated_at": timestamp,
        "cwd": str(resume.cwd.resolve()),
        "target": dict(resume.target),
        "predicate": predicate,
        "prompt": resume.prompt,
        "status": "pending",
        "attempts": 0,
        "max_attempts": 3,
        "ack_timeout_seconds": 30,
        "next_attempt_at": timestamp,
        "events": [
            {
                "at": timestamp,
                "type": "created",
                "message": "Signal wake record created",
            }
        ],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    digest = hashlib.sha256((encoded + "\n").encode("utf-8")).hexdigest()
    return encoded, digest


def _format_time(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
