"""Durable, secret-free state for managed webhook key rotation.

This module deliberately has no provider, service, secret, ingress, or
dispatch implementation.  It is a small authority boundary for the code that
will be injected by later lifecycle work: callers persist intent before an
external effect and report only compact, non-secret observations afterwards.
"""
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, replace
from enum import Enum
import fcntl
import json
import os
from pathlib import Path
import re
import stat
import tempfile
import threading


_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,95}")
# Journal receipt IDs use the canonical ``event_000...`` form.  Locators are
# still bounded opaque identifiers; admitting underscores keeps the rotation
# contract aligned with the durable signal store without exposing paths.
_LOCATOR = re.compile(r"[a-z][a-z0-9_-]{0,95}")
_CODE = re.compile(r"[A-Z][A-Z0-9_]{0,63}")
_MAX_RECORDS = 32
_MAX_FILE_BYTES = 262_144
_MAX_LOCATORS = 8
_MAX_GENERATION = 2**31 - 1


class RotationPhase(str, Enum):
    """Six forward phases plus durable failure and terminal outcomes."""

    PREPARED = "PREPARED"
    DUAL_READY = "DUAL_READY"
    PROVIDER_PENDING = "PROVIDER_PENDING"
    AWAITING_DELIVERY = "AWAITING_DELIVERY"
    RETIRING = "RETIRING"
    COMPLETE = "COMPLETE"
    UNKNOWN = "UNKNOWN"
    EXPIRED = "EXPIRED"
    ROLLED_BACK = "ROLLED_BACK"


class PendingEffect(str, Enum):
    NONE = "NONE"
    RESTART_DUAL = "RESTART_DUAL"
    RESTART_TARGET_ONLY = "RESTART_TARGET_ONLY"
    PROVIDER_UPDATE = "PROVIDER_UPDATE"
    RETIRE_PREVIOUS = "RETIRE_PREVIOUS"
    ROLLBACK = "ROLLBACK"


class Observation(str, Enum):
    PROVED = "PROVED"
    REJECTED = "REJECTED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class RuntimeProof:
    """A process-bound, non-secret readiness observation.

    ``loaded_generations`` is numeric by design.  Generation values are the
    only key identity this package admits; references and key material never
    enter the record. ``process_started_at`` is a Unix-epoch second derived
    from the attested Linux boot time plus the process start ticks. Rotation
    intent clocks use the same Unix-epoch-second domain; the private
    attestation retains the exact boot identity and tick value needed to
    reject PID reuse before this sanitized projection is persisted.
    """

    process_id: int
    process_started_at: int
    authority_revision: int
    loaded_generations: tuple[int, ...]
    evidence_locator: str

    def __post_init__(self) -> None:
        if (
            type(self.process_id) is not int or not 1 <= self.process_id < 2**63
            or type(self.process_started_at) is not int or self.process_started_at < 0
            or type(self.authority_revision) is not int or self.authority_revision < 0
            or not _valid_generations(self.loaded_generations)
            or type(self.evidence_locator) is not str or _LOCATOR.fullmatch(self.evidence_locator) is None
        ):
            raise ValueError("rotation runtime proof is invalid")

    def to_dict(self) -> dict[str, object]:
        return {
            "process_id": self.process_id,
            "process_started_at": self.process_started_at,
            "authority_revision": self.authority_revision,
            "loaded_generations": list(self.loaded_generations),
            "evidence_locator": self.evidence_locator,
        }

    @classmethod
    def from_dict(cls, value: object) -> "RuntimeProof":
        if type(value) is not dict or set(value) != {
            "process_id", "process_started_at", "authority_revision", "loaded_generations", "evidence_locator"
        } or type(value["loaded_generations"]) is not list:
            raise ValueError("rotation runtime proof is invalid")
        try:
            return cls(
                process_id=value["process_id"], process_started_at=value["process_started_at"],
                authority_revision=value["authority_revision"],
                loaded_generations=tuple(value["loaded_generations"]), evidence_locator=value["evidence_locator"],
            )
        except (TypeError, ValueError):
            raise ValueError("rotation runtime proof is invalid") from None


@dataclass(frozen=True, slots=True)
class TerminalEvidence:
    """Attributable, non-secret evidence retained across successor rotations."""

    phase: RotationPhase
    revision: int
    code: str
    previous_generation: int
    target_generation: int
    binding_revision: int

    def __post_init__(self) -> None:
        if (
            self.phase not in {RotationPhase.COMPLETE, RotationPhase.ROLLED_BACK}
            or type(self.revision) is not int or self.revision < 1
            or type(self.code) is not str or _CODE.fullmatch(self.code) is None
            or type(self.previous_generation) is not int or not 1 <= self.previous_generation <= _MAX_GENERATION
            or type(self.target_generation) is not int or not 1 <= self.target_generation <= _MAX_GENERATION
            or type(self.binding_revision) is not int or self.binding_revision < 0
        ):
            raise ValueError("rotation terminal evidence is invalid")

    def to_dict(self) -> dict[str, object]:
        return {
            "phase": self.phase.value, "revision": self.revision, "code": self.code,
            "previous_generation": self.previous_generation, "target_generation": self.target_generation,
            "binding_revision": self.binding_revision,
        }

    @classmethod
    def from_dict(cls, value: object) -> "TerminalEvidence":
        if type(value) is not dict or set(value) != {
            "phase", "revision", "code", "previous_generation", "target_generation", "binding_revision"
        }:
            raise ValueError("rotation terminal evidence is invalid")
        try:
            return cls(
                phase=RotationPhase(value["phase"]), revision=value["revision"], code=value["code"],
                previous_generation=value["previous_generation"], target_generation=value["target_generation"],
                binding_revision=value["binding_revision"],
            )
        except (TypeError, ValueError):
            raise ValueError("rotation terminal evidence is invalid") from None


@dataclass(frozen=True, slots=True)
class RotationRecord:
    """One owner-scoped rotation transaction; it contains no secret values."""

    owner_id: str
    canonical_root: str
    owner_uid: int
    source_instance: str
    service_id: str
    binding_revision: int
    previous_generation: int
    target_generation: int
    overlap_deadline: int
    phase: RotationPhase = RotationPhase.PREPARED
    revision: int = 0
    pending_effect: PendingEffect = PendingEffect.NONE
    effect_revision: int | None = None
    runtime_proof: RuntimeProof | None = None
    delivery_locator: str | None = None
    terminal_code: str | None = None
    last_observed_at: int = 0
    restart_intended_at: int | None = None
    terminal_history: tuple[TerminalEvidence, ...] = ()

    def __post_init__(self) -> None:
        if not _valid_record(self):
            raise ValueError("managed webhook rotation record is invalid")

    def to_dict(self) -> dict[str, object]:
        return {
            "owner_id": self.owner_id,
            "canonical_root": self.canonical_root,
            "owner_uid": self.owner_uid,
            "source_instance": self.source_instance,
            "service_id": self.service_id,
            "binding_revision": self.binding_revision,
            "previous_generation": self.previous_generation,
            "target_generation": self.target_generation,
            "overlap_deadline": self.overlap_deadline,
            "phase": self.phase.value,
            "revision": self.revision,
            "pending_effect": self.pending_effect.value,
            "effect_revision": self.effect_revision,
            "runtime_proof": None if self.runtime_proof is None else self.runtime_proof.to_dict(),
            "delivery_locator": self.delivery_locator,
            "terminal_code": self.terminal_code,
            "last_observed_at": self.last_observed_at,
            "restart_intended_at": self.restart_intended_at,
            "terminal_history": [item.to_dict() for item in self.terminal_history],
        }

    def summary(self) -> dict[str, object]:
        """Return a safe support projection, intentionally omitting locators."""
        return {
            "phase": self.phase.value,
            "revision": self.revision,
            "previous_generation": self.previous_generation,
            "target_generation": self.target_generation,
            "overlap_deadline": self.overlap_deadline,
            "pending_effect": self.pending_effect.value,
            "terminal_code": self.terminal_code,
        }

    @classmethod
    def from_dict(cls, value: object) -> "RotationRecord":
        fields = {
            "owner_id", "canonical_root", "owner_uid", "source_instance", "service_id", "binding_revision",
            "previous_generation", "target_generation", "overlap_deadline", "phase", "revision", "pending_effect",
            "effect_revision", "runtime_proof", "delivery_locator", "terminal_code", "last_observed_at",
            "restart_intended_at", "terminal_history",
        }
        if type(value) is not dict or set(value) != fields:
            raise ValueError("managed webhook rotation record is invalid")
        try:
            proof_value = value["runtime_proof"]
            decoded = cls(
                owner_id=value["owner_id"], canonical_root=value["canonical_root"], owner_uid=value["owner_uid"],
                source_instance=value["source_instance"], service_id=value["service_id"],
                binding_revision=value["binding_revision"], previous_generation=value["previous_generation"],
                target_generation=value["target_generation"], overlap_deadline=value["overlap_deadline"],
                phase=RotationPhase(value["phase"]), revision=value["revision"],
                pending_effect=PendingEffect(value["pending_effect"]), effect_revision=value["effect_revision"],
                runtime_proof=None if proof_value is None else RuntimeProof.from_dict(proof_value),
                delivery_locator=value["delivery_locator"], terminal_code=value["terminal_code"],
                last_observed_at=value["last_observed_at"], restart_intended_at=value["restart_intended_at"], terminal_history=tuple(
                    TerminalEvidence.from_dict(item) for item in value["terminal_history"]
                ),
            )
            if not _stored_consistent(decoded):
                raise ValueError
            return decoded
        except (TypeError, ValueError):
            raise ValueError("managed webhook rotation record is invalid") from None


class ManagedWebhookRotationStore:
    """Strict owner-only JSON persistence with process and thread locking."""

    _thread_locks: dict[str, threading.RLock] = {}
    _thread_locks_guard = threading.Lock()

    def __init__(self, wake_root: Path):
        root = Path(wake_root)
        if not root.is_absolute() or root.is_symlink() or str(root.resolve()) == "/":
            raise ValueError("rotation store root is invalid")
        self.wake_root = root.resolve()
        self.path = self.wake_root / "github" / "managed-webhook-rotations.json"
        self._lock_path = self.wake_root / "github" / ".managed-webhook-rotations.lock"

    @contextmanager
    def locked(self) -> Iterator[None]:
        key = str(self._lock_path)
        with self._thread_locks_guard:
            lock = self._thread_locks.setdefault(key, threading.RLock())
        with lock:
            handle = None
            try:
                self._prepare_directory()
                descriptor = os.open(self._lock_path, os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600)
                metadata = os.fstat(descriptor)
                if not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.getuid():
                    os.close(descriptor)
                    raise ValueError("rotation store is unavailable")
                os.fchmod(descriptor, 0o600)
                handle = os.fdopen(descriptor, "a+", encoding="utf-8")
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
                yield
            except OSError:
                raise ValueError("rotation store is unavailable") from None
            finally:
                if handle is not None:
                    try:
                        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
                    finally:
                        handle.close()

    def records(self) -> tuple[RotationRecord, ...]:
        with self.locked():
            return self._records_unlocked()

    def load(self, owner_id: str) -> RotationRecord:
        _require_name(owner_id, "rotation owner")
        with self.locked():
            return self._load_unlocked(owner_id)

    def save(self, record: RotationRecord, *, expected_revision: int | None = None) -> RotationRecord:
        with self.locked():
            return self._save_unlocked(record, expected_revision=expected_revision)

    def observe_admission(self, owner_id: str, *, now: int) -> RotationRecord:
        """Durably advance the admission clock under the same owner lock."""
        _require_name(owner_id, "rotation owner")
        _require_time(now)
        with self.locked():
            record = self._load_unlocked(owner_id)
            if now < record.last_observed_at:
                raise ValueError("managed webhook rotation clock moved backwards")
            if now == record.last_observed_at:
                return record
            return self._save_unlocked(
                replace(record, last_observed_at=now), expected_revision=record.revision,
            )

    def _prepare_directory(self) -> None:
        self.wake_root.mkdir(mode=0o700, parents=True, exist_ok=True)
        root_meta = self.wake_root.lstat()
        if self.wake_root.is_symlink() or not stat.S_ISDIR(root_meta.st_mode) or root_meta.st_uid != os.getuid():
            raise ValueError("rotation store is unavailable")
        parent = self.path.parent
        parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        meta = parent.lstat()
        if parent.is_symlink() or not stat.S_ISDIR(meta.st_mode) or meta.st_uid != os.getuid():
            raise ValueError("rotation store is unavailable")
        os.chmod(parent, 0o700)

    def _load_unlocked(self, owner_id: str) -> RotationRecord:
        for record in self._records_unlocked():
            if record.owner_id == owner_id:
                return record
        raise ValueError("managed webhook rotation is not configured for owner")

    def _save_unlocked(self, record: RotationRecord, *, expected_revision: int | None = None) -> RotationRecord:
        if type(record) is not RotationRecord:
            raise ValueError("managed webhook rotation record is invalid")
        if record.canonical_root != str(self.wake_root) or record.owner_uid != os.getuid():
            raise ValueError("managed webhook rotation ownership is invalid")
        selected = {item.owner_id: item for item in self._records_unlocked()}
        prior = selected.get(record.owner_id)
        if prior is None:
            if expected_revision is not None or record.revision != 0:
                raise ValueError("managed webhook rotation revision is stale")
            saved = record
        else:
            if type(expected_revision) is not int or expected_revision != prior.revision:
                raise ValueError("managed webhook rotation revision is stale")
            successor = _is_successor(prior, record)
            if _immutable_facts(prior) != _immutable_facts(record) and not successor:
                raise ValueError("managed webhook rotation ownership is immutable")
            if not successor and not _phase_allowed(prior.phase, record.phase):
                raise ValueError("managed webhook rotation phase is invalid")
            saved = replace(record, revision=prior.revision + 1)
            if not successor and not _stored_transition_allowed(prior, saved):
                raise ValueError("managed webhook rotation transition is invalid")
        if not _stored_consistent(saved):
            raise ValueError("managed webhook rotation record is invalid")
        if any(item.owner_id != saved.owner_id and _conflicts(item, saved) for item in selected.values()):
            raise ValueError("managed webhook rotation conflicts with existing ownership")
        selected[saved.owner_id] = saved
        if len(selected) > _MAX_RECORDS:
            raise ValueError("rotation store is full")
        self._write_unlocked(tuple(sorted(selected.values(), key=lambda item: item.owner_id)))
        return saved

    def _records_unlocked(self) -> tuple[RotationRecord, ...]:
        if self.path.is_symlink():
            raise ValueError("rotation store is invalid")
        if not self.path.exists():
            return ()
        try:
            metadata = self.path.stat()
            if (
                self.path.is_symlink() or not self.path.is_file() or metadata.st_size > _MAX_FILE_BYTES
                or metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) & 0o077
            ):
                raise ValueError
            payload = json.loads(self.path.read_text(encoding="utf-8"), object_pairs_hook=_unique_object)
            if type(payload) is not dict or set(payload) != {"schema_version", "records"}:
                raise ValueError
            rows = payload["records"]
            if payload["schema_version"] != 1 or type(rows) is not list or len(rows) > _MAX_RECORDS:
                raise ValueError
            records = tuple(RotationRecord.from_dict(item) for item in rows)
            if tuple(item.owner_id for item in records) != tuple(sorted(item.owner_id for item in records)):
                raise ValueError
            if len({item.owner_id for item in records}) != len(records):
                raise ValueError
            if any(item.canonical_root != str(self.wake_root) or item.owner_uid != os.getuid() for item in records):
                raise ValueError
            if any(not _stored_consistent(item) for item in records):
                raise ValueError
            if any(_conflicts(left, right) for index, left in enumerate(records) for right in records[index + 1:]):
                raise ValueError
            return records
        except (OSError, TypeError, ValueError, json.JSONDecodeError):
            raise ValueError("rotation store is invalid") from None

    def _write_unlocked(self, records: tuple[RotationRecord, ...]) -> None:
        temporary: Path | None = None
        try:
            rendered = json.dumps({"schema_version": 1, "records": [item.to_dict() for item in records]}, sort_keys=True, separators=(",", ":")) + "\n"
            if len(rendered.encode("utf-8")) > _MAX_FILE_BYTES:
                raise ValueError("rotation store is full")
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=self.path.parent, prefix=".managed-webhook-rotations-", delete=False) as handle:
                temporary = Path(handle.name)
                os.chmod(temporary, 0o600)
                handle.write(rendered)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.path)
            os.chmod(self.path, 0o600)
            directory = os.open(self.path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        except OSError:
            raise ValueError("rotation store is unavailable") from None
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)


class ManagedWebhookRotationCoordinator:
    """Pure transition coordinator; all effects are caller-injected seams."""

    def __init__(self, store: ManagedWebhookRotationStore):
        if type(store) is not ManagedWebhookRotationStore:
            raise ValueError("rotation store is invalid")
        self.store = store

    def begin(self, record: RotationRecord, *, now: int) -> RotationRecord:
        _require_time(now)
        if record.phase is not RotationPhase.PREPARED or record.pending_effect is not PendingEffect.NONE:
            raise ValueError("managed webhook rotation must begin prepared")
        if now > record.overlap_deadline:
            raise ValueError("managed webhook rotation overlap is expired")
        return self.store.save(replace(record, last_observed_at=now))

    def load(self, owner_id: str, *, now: int) -> RotationRecord:
        _require_time(now)
        record = self.store.load(owner_id)
        self._assert_clock(record, now)
        return record

    def admitted_generations(self, owner_id: str, *, now: int) -> tuple[int, ...]:
        """Return the fail-closed admission set without requiring a controller write.

        The listener-side integration calls this on every admission decision.
        Consequently an elapsed immutable deadline stops previous-generation
        acceptance even if the rotation coordinator process is absent.
        """
        # This CAS heartbeat is deliberate: every advancing admission decision
        # establishes the durable high-water clock even before expiry.
        record = self.store.observe_admission(owner_id, now=now)
        if record.phase is RotationPhase.COMPLETE:
            return (record.target_generation,)
        if record.phase is RotationPhase.ROLLED_BACK:
            return (record.previous_generation,)
        if record.pending_effect is PendingEffect.ROLLBACK:
            return ()
        if record.phase in {RotationPhase.UNKNOWN, RotationPhase.EXPIRED}:
            return ()
        if now > record.overlap_deadline:
            # This is the one durable admission-side mutation.  Once observed,
            # expiry becomes a clock fence, so a later backwards clock cannot
            # revive either old or dual-key admission.
            record = self._expire_record(record, now)
            return ()
        if record.phase is RotationPhase.PREPARED:
            return (record.previous_generation,)
        if record.phase in {RotationPhase.DUAL_READY, RotationPhase.PROVIDER_PENDING}:
            return (record.previous_generation, record.target_generation)
        if record.phase is RotationPhase.AWAITING_DELIVERY:
            if record.runtime_proof is not None and record.runtime_proof.loaded_generations == (record.target_generation,):
                return (record.target_generation,)
            return (record.previous_generation, record.target_generation)
        if record.phase is RotationPhase.RETIRING:
            return (record.target_generation,)
        return (record.previous_generation, record.target_generation)

    def intend_dual_restart(self, owner_id: str, *, expected_revision: int, now: int) -> RotationRecord:
        return self._intend(owner_id, expected_revision, now, RotationPhase.PREPARED, PendingEffect.RESTART_DUAL)

    def observe_dual_restart(self, owner_id: str, *, expected_revision: int, proof: RuntimeProof, now: int) -> RotationRecord:
        record = self._current(owner_id, expected_revision, now)
        if record.phase is RotationPhase.DUAL_READY and record.pending_effect is PendingEffect.NONE:
            return record
        if record.phase is not RotationPhase.PREPARED or record.pending_effect is not PendingEffect.RESTART_DUAL:
            raise ValueError("managed webhook rotation restart is not pending")
        if not self._is_dual_proof(record, proof):
            return self._unknown(record, now, "RUNTIME_PROOF_REJECTED")
        return self.store.save(replace(record, phase=RotationPhase.DUAL_READY, pending_effect=PendingEffect.NONE, runtime_proof=proof, last_observed_at=now), expected_revision=record.revision)

    def intend_provider_update(self, owner_id: str, *, expected_revision: int, now: int) -> RotationRecord:
        return self._intend(owner_id, expected_revision, now, RotationPhase.DUAL_READY, PendingEffect.PROVIDER_UPDATE)

    def observe_provider_update(self, owner_id: str, *, expected_revision: int, observation: Observation, now: int) -> RotationRecord:
        record = self._current(owner_id, expected_revision, now)
        if record.phase is RotationPhase.AWAITING_DELIVERY and record.pending_effect is PendingEffect.NONE and observation is Observation.PROVED:
            return record
        if record.phase is not RotationPhase.PROVIDER_PENDING or record.pending_effect is not PendingEffect.PROVIDER_UPDATE:
            raise ValueError("managed webhook rotation provider update is not pending")
        if observation is Observation.PROVED:
            return self.store.save(replace(record, phase=RotationPhase.AWAITING_DELIVERY, pending_effect=PendingEffect.NONE, last_observed_at=now), expected_revision=record.revision)
        return self._unknown(record, now, "PROVIDER_UPDATE_REJECTED" if observation is Observation.REJECTED else "PROVIDER_UPDATE_UNKNOWN")

    def record_delivery(self, owner_id: str, *, expected_revision: int, generation: int, journal_locator: str, now: int) -> RotationRecord:
        record = self._current(owner_id, expected_revision, now)
        if record.phase is RotationPhase.RETIRING and record.delivery_locator == journal_locator:
            return record
        if record.phase is not RotationPhase.AWAITING_DELIVERY or record.pending_effect is not PendingEffect.NONE:
            raise ValueError("managed webhook rotation delivery is not awaited")
        if type(generation) is not int or generation != record.target_generation or _LOCATOR.fullmatch(journal_locator) is None:
            raise ValueError("managed webhook rotation delivery proof is invalid")
        return self.store.save(replace(record, delivery_locator=journal_locator, last_observed_at=now), expected_revision=record.revision)

    def intend_target_restart(self, owner_id: str, *, expected_revision: int, now: int) -> RotationRecord:
        record = self._current(owner_id, expected_revision, now)
        if record.pending_effect is PendingEffect.RESTART_TARGET_ONLY:
            return record
        if record.phase is not RotationPhase.AWAITING_DELIVERY or record.delivery_locator is None:
            raise ValueError("managed webhook rotation target restart is not available")
        if record.runtime_proof is None or record.runtime_proof.loaded_generations != (record.previous_generation, record.target_generation):
            raise ValueError("managed webhook rotation dual runtime proof is required")
        return self._save_intent(record, RotationPhase.AWAITING_DELIVERY, PendingEffect.RESTART_TARGET_ONLY, now)

    def observe_target_restart(self, owner_id: str, *, expected_revision: int, proof: RuntimeProof, now: int) -> RotationRecord:
        """Observe the target-only restart after its durable intent boundary."""
        record = self._current(owner_id, expected_revision, now)
        if record.phase is not RotationPhase.AWAITING_DELIVERY or record.pending_effect is not PendingEffect.RESTART_TARGET_ONLY:
            raise ValueError("managed webhook rotation target runtime is not awaited")
        if not self._is_target_proof(record, proof):
            return self._unknown(record, now, "TARGET_RUNTIME_PROOF_REJECTED")
        return self.store.save(replace(record, pending_effect=PendingEffect.NONE, runtime_proof=proof, last_observed_at=now), expected_revision=record.revision)

    def record_target_runtime(self, owner_id: str, *, expected_revision: int, proof: RuntimeProof, now: int) -> RotationRecord:
        """Compatibility observation name; it still requires target-restart intent."""
        return self.observe_target_restart(owner_id, expected_revision=expected_revision, proof=proof, now=now)

    def intend_retirement(self, owner_id: str, *, expected_revision: int, now: int) -> RotationRecord:
        record = self._current(owner_id, expected_revision, now)
        if record.phase is RotationPhase.RETIRING and record.pending_effect is PendingEffect.RETIRE_PREVIOUS:
            return record
        if record.phase is not RotationPhase.AWAITING_DELIVERY or record.delivery_locator is None:
            raise ValueError("managed webhook rotation delivery proof is required")
        if record.runtime_proof is None or record.runtime_proof.loaded_generations != (record.target_generation,):
            raise ValueError("managed webhook rotation runtime proof is required")
        return self._save_intent(record, RotationPhase.RETIRING, PendingEffect.RETIRE_PREVIOUS, now)

    def observe_retirement(self, owner_id: str, *, expected_revision: int, observation: Observation, now: int) -> RotationRecord:
        record = self._current(owner_id, expected_revision, now)
        if record.phase is RotationPhase.COMPLETE and observation is Observation.PROVED:
            return record
        if record.phase is not RotationPhase.RETIRING or record.pending_effect is not PendingEffect.RETIRE_PREVIOUS:
            raise ValueError("managed webhook rotation retirement is not pending")
        if observation is Observation.PROVED:
            return self._terminal(record, RotationPhase.COMPLETE, "RETIRED", now)
        return self._unknown(record, now, "RETIREMENT_REJECTED" if observation is Observation.REJECTED else "RETIREMENT_UNKNOWN")

    def rollback(self, owner_id: str, *, expected_revision: int, now: int) -> RotationRecord:
        record = self._current(owner_id, expected_revision, now, allow_expired=True, allow_rollback=True)
        if record.phase is RotationPhase.ROLLED_BACK:
            return record
        if record.phase is RotationPhase.COMPLETE:
            raise ValueError("completed managed webhook rotation requires a new transaction")
        if record.pending_effect is PendingEffect.ROLLBACK:
            return record
        return self._save_intent(record, record.phase, PendingEffect.ROLLBACK, now)

    def observe_rollback(self, owner_id: str, *, expected_revision: int, observation: Observation, now: int) -> RotationRecord:
        record = self._current(owner_id, expected_revision, now, allow_expired=True, allow_rollback=True)
        if record.phase is RotationPhase.ROLLED_BACK and observation is Observation.PROVED:
            return record
        if record.pending_effect is not PendingEffect.ROLLBACK:
            raise ValueError("managed webhook rotation rollback is not pending")
        if observation is Observation.PROVED:
            return self._terminal(record, RotationPhase.ROLLED_BACK, "ROLLED_BACK", now)
        return self._unknown(record, now, "ROLLBACK_REJECTED" if observation is Observation.REJECTED else "ROLLBACK_UNKNOWN")

    def expire(self, owner_id: str, *, expected_revision: int, now: int) -> RotationRecord:
        record = self._current(owner_id, expected_revision, now, allow_expired=True)
        if record.phase in {RotationPhase.COMPLETE, RotationPhase.ROLLED_BACK, RotationPhase.EXPIRED}:
            return record
        if now <= record.overlap_deadline:
            raise ValueError("managed webhook rotation overlap is not expired")
        return self._expire_record(record, now)

    def begin_successor(
        self, owner_id: str, *, expected_revision: int, binding_revision: int,
        target_generation: int, overlap_deadline: int, now: int,
    ) -> RotationRecord:
        """Start a new transaction only after a retained terminal predecessor."""
        prior = self._current(owner_id, expected_revision, now, allow_expired=True, allow_rollback=True)
        if prior.phase not in {RotationPhase.COMPLETE, RotationPhase.ROLLED_BACK}:
            raise ValueError("managed webhook rotation successor requires a terminal predecessor")
        _require_time(overlap_deadline)
        if overlap_deadline < now or type(binding_revision) is not int or binding_revision < 0:
            raise ValueError("managed webhook rotation successor is invalid")
        previous = prior.target_generation if prior.phase is RotationPhase.COMPLETE else prior.previous_generation
        if type(target_generation) is not int or not 1 <= target_generation <= _MAX_GENERATION or target_generation == previous:
            raise ValueError("managed webhook rotation successor is invalid")
        successor = RotationRecord(
            owner_id=prior.owner_id, canonical_root=prior.canonical_root, owner_uid=prior.owner_uid,
            source_instance=prior.source_instance, service_id=prior.service_id, binding_revision=binding_revision,
            previous_generation=previous, target_generation=target_generation, overlap_deadline=overlap_deadline,
            revision=prior.revision, last_observed_at=now, terminal_history=prior.terminal_history,
        )
        return self.store.save(successor, expected_revision=prior.revision)

    def _intend(self, owner_id: str, expected_revision: int, now: int, phase: RotationPhase, effect: PendingEffect) -> RotationRecord:
        record = self._current(owner_id, expected_revision, now)
        # Retrying a caller after it crashed *after* durable intent is a read of
        # the same intent, never permission to emit a second external effect.
        if record.pending_effect is effect:
            return record
        if record.phase is not phase or record.pending_effect is not PendingEffect.NONE:
            raise ValueError("managed webhook rotation effect is not available")
        target_phase = RotationPhase.PROVIDER_PENDING if effect is PendingEffect.PROVIDER_UPDATE else phase
        return self._save_intent(record, target_phase, effect, now)

    def _save_intent(self, record: RotationRecord, phase: RotationPhase, effect: PendingEffect, now: int) -> RotationRecord:
        restart_intended_at = now if effect in {PendingEffect.RESTART_DUAL, PendingEffect.RESTART_TARGET_ONLY} else record.restart_intended_at
        return self.store.save(replace(record, phase=phase, pending_effect=effect, effect_revision=record.revision + 1, last_observed_at=now, restart_intended_at=restart_intended_at), expected_revision=record.revision)

    def _current(self, owner_id: str, expected_revision: int, now: int, *, allow_expired: bool = False, allow_rollback: bool = False) -> RotationRecord:
        record = self.load(owner_id, now=now)
        if type(expected_revision) is not int or expected_revision != record.revision:
            raise ValueError("managed webhook rotation revision is stale")
        if not allow_expired and now > record.overlap_deadline and record.phase not in {RotationPhase.COMPLETE, RotationPhase.ROLLED_BACK}:
            raise ValueError("managed webhook rotation overlap is expired")
        if record.phase in {RotationPhase.UNKNOWN, RotationPhase.EXPIRED, RotationPhase.ROLLED_BACK} and not allow_expired:
            raise ValueError("managed webhook rotation is not actionable")
        if record.pending_effect is PendingEffect.ROLLBACK and not allow_rollback:
            raise ValueError("managed webhook rotation rollback is pending")
        return record

    @staticmethod
    def _is_dual_proof(record: RotationRecord, proof: RuntimeProof) -> bool:
        return (
            proof.authority_revision == record.binding_revision
            and proof.loaded_generations == (record.previous_generation, record.target_generation)
            and record.restart_intended_at is not None and proof.process_started_at >= record.restart_intended_at
        )

    @staticmethod
    def _is_target_proof(record: RotationRecord, proof: RuntimeProof) -> bool:
        return (
            proof.authority_revision == record.binding_revision
            and proof.loaded_generations == (record.target_generation,)
            and record.restart_intended_at is not None and proof.process_started_at >= record.restart_intended_at
        )

    @staticmethod
    def _assert_clock(record: RotationRecord, now: int) -> None:
        if now < record.last_observed_at:
            raise ValueError("managed webhook rotation clock moved backwards")

    def _unknown(self, record: RotationRecord, now: int, code: str) -> RotationRecord:
        return self.store.save(replace(record, phase=RotationPhase.UNKNOWN, pending_effect=PendingEffect.NONE, terminal_code=code, last_observed_at=now), expected_revision=record.revision)

    def _expire_record(self, record: RotationRecord, now: int) -> RotationRecord:
        if record.phase is RotationPhase.EXPIRED:
            return record
        return self.store.save(replace(record, phase=RotationPhase.EXPIRED, pending_effect=PendingEffect.NONE, terminal_code="OVERLAP_EXPIRED", last_observed_at=now), expected_revision=record.revision)

    def _terminal(self, record: RotationRecord, phase: RotationPhase, code: str, now: int) -> RotationRecord:
        evidence = TerminalEvidence(
            phase=phase, revision=record.revision + 1, code=code,
            previous_generation=record.previous_generation, target_generation=record.target_generation,
            binding_revision=record.binding_revision,
        )
        return self.store.save(
            replace(record, phase=phase, pending_effect=PendingEffect.NONE, terminal_code=code,
                    last_observed_at=now, terminal_history=(record.terminal_history + (evidence,))[-_MAX_LOCATORS:]),
            expected_revision=record.revision,
        )


def _valid_record(record: RotationRecord) -> bool:
    return (
        all(type(value) is str and _NAME.fullmatch(value) is not None for value in (record.owner_id, record.source_instance, record.service_id))
        and _valid_root(record.canonical_root) and type(record.owner_uid) is int and 0 <= record.owner_uid < 2**31
        and type(record.binding_revision) is int and 0 <= record.binding_revision < 2**63
        and type(record.previous_generation) is int and 1 <= record.previous_generation <= _MAX_GENERATION
        and type(record.target_generation) is int and 1 <= record.target_generation <= _MAX_GENERATION
        and record.previous_generation < record.target_generation and type(record.overlap_deadline) is int and record.overlap_deadline >= 0
        and isinstance(record.phase, RotationPhase) and type(record.revision) is int and 0 <= record.revision < 2**63
        and isinstance(record.pending_effect, PendingEffect)
        and (record.effect_revision is None or type(record.effect_revision) is int and 1 <= record.effect_revision < 2**63)
        and (record.runtime_proof is None or type(record.runtime_proof) is RuntimeProof)
        and (record.delivery_locator is None or type(record.delivery_locator) is str and _LOCATOR.fullmatch(record.delivery_locator) is not None)
        and (record.terminal_code is None or type(record.terminal_code) is str and _CODE.fullmatch(record.terminal_code) is not None)
        and type(record.last_observed_at) is int and record.last_observed_at >= 0
        and (record.restart_intended_at is None or type(record.restart_intended_at) is int and 0 <= record.restart_intended_at <= record.last_observed_at)
        and type(record.terminal_history) is tuple and len(record.terminal_history) <= _MAX_LOCATORS
        and all(type(item) is TerminalEvidence for item in record.terminal_history)
        and _consistent(record)
    )


def _consistent(record: RotationRecord) -> bool:
    if tuple(item.revision for item in record.terminal_history) != tuple(sorted(item.revision for item in record.terminal_history)):
        return False
    if len({item.revision for item in record.terminal_history}) != len(record.terminal_history):
        return False
    if record.phase in {RotationPhase.COMPLETE, RotationPhase.ROLLED_BACK}:
        if record.pending_effect is not PendingEffect.NONE or not record.terminal_history:
            return False
        last = record.terminal_history[-1]
        if (last.phase, last.code, last.previous_generation, last.target_generation, last.binding_revision) != (
            record.phase, record.terminal_code, record.previous_generation, record.target_generation, record.binding_revision
        ):
            return False
    if record.phase is RotationPhase.COMPLETE and (record.terminal_code != "RETIRED" or record.delivery_locator is None):
        return False
    if record.phase is RotationPhase.EXPIRED and record.terminal_code != "OVERLAP_EXPIRED":
        return False
    if record.phase is RotationPhase.ROLLED_BACK and record.terminal_code != "ROLLED_BACK":
        return False
    return True


def _stored_consistent(record: RotationRecord) -> bool:
    """Validate the post-CAS form, where revision/effect facts are durable."""
    if not _valid_record(record):
        return False
    if record.pending_effect is not PendingEffect.NONE:
        if (
            record.effect_revision is None or record.effect_revision > record.revision
            or record.phase in {RotationPhase.COMPLETE, RotationPhase.ROLLED_BACK}
        ):
            return False
        if record.pending_effect is PendingEffect.ROLLBACK:
            return True
    elif record.effect_revision is not None and record.effect_revision >= record.revision:
        return False
    phase = record.phase
    proof = record.runtime_proof
    dual = proof is not None and proof.authority_revision == record.binding_revision and proof.loaded_generations == (record.previous_generation, record.target_generation)
    target = proof is not None and proof.authority_revision == record.binding_revision and proof.loaded_generations == (record.target_generation,)
    fresh_runtime = proof is not None and record.restart_intended_at is not None and proof.process_started_at >= record.restart_intended_at
    if phase is RotationPhase.PREPARED:
        return (
            proof is None and record.delivery_locator is None and record.terminal_code is None
            and ((record.pending_effect is PendingEffect.NONE and record.restart_intended_at is None)
                 or (record.pending_effect is PendingEffect.RESTART_DUAL and record.restart_intended_at is not None))
        )
    if phase is RotationPhase.DUAL_READY:
        return dual and fresh_runtime and record.delivery_locator is None and record.terminal_code is None and record.pending_effect is PendingEffect.NONE
    if phase is RotationPhase.PROVIDER_PENDING:
        return dual and fresh_runtime and record.delivery_locator is None and record.terminal_code is None and record.pending_effect is PendingEffect.PROVIDER_UPDATE
    if phase is RotationPhase.AWAITING_DELIVERY:
        return (
            record.terminal_code is None
            and ((record.pending_effect is PendingEffect.NONE and fresh_runtime and (dual or target))
                 or (record.pending_effect is PendingEffect.RESTART_TARGET_ONLY and dual and record.delivery_locator is not None))
        )
    if phase is RotationPhase.RETIRING:
        return target and fresh_runtime and record.delivery_locator is not None and record.terminal_code is None and record.pending_effect is PendingEffect.RETIRE_PREVIOUS
    if phase is RotationPhase.COMPLETE:
        return target and fresh_runtime and record.delivery_locator is not None and record.pending_effect is PendingEffect.NONE and record.terminal_history[-1].revision <= record.revision
    if phase is RotationPhase.ROLLED_BACK:
        return record.pending_effect is PendingEffect.NONE and record.terminal_history[-1].revision <= record.revision
    if phase is RotationPhase.EXPIRED:
        return record.pending_effect in {PendingEffect.NONE, PendingEffect.ROLLBACK}
    return phase is RotationPhase.UNKNOWN and record.pending_effect in {PendingEffect.NONE, PendingEffect.ROLLBACK}


def _stored_transition_allowed(prior: RotationRecord, saved: RotationRecord) -> bool:
    # Admission heartbeats may advance only time/revision.  They deliberately
    # cannot be used to attach proof, delivery, or an effect intent.
    if (
        saved.phase is prior.phase and saved.pending_effect is prior.pending_effect
        and saved.effect_revision == prior.effect_revision and saved.runtime_proof == prior.runtime_proof
        and saved.delivery_locator == prior.delivery_locator and saved.terminal_code == prior.terminal_code
        and saved.restart_intended_at == prior.restart_intended_at and saved.terminal_history == prior.terminal_history
        and saved.last_observed_at > prior.last_observed_at
    ):
        return True
    if saved.pending_effect is PendingEffect.ROLLBACK:
        return (
            prior.pending_effect is not PendingEffect.ROLLBACK and saved.phase is prior.phase
            and saved.runtime_proof == prior.runtime_proof and saved.delivery_locator == prior.delivery_locator
            and saved.terminal_code == prior.terminal_code and saved.restart_intended_at == prior.restart_intended_at
            and saved.terminal_history == prior.terminal_history
            and saved.effect_revision == saved.revision
        )
    if prior.pending_effect is PendingEffect.ROLLBACK:
        if saved.pending_effect is not PendingEffect.NONE or saved.phase not in {RotationPhase.ROLLED_BACK, RotationPhase.UNKNOWN}:
            return False
        return saved.phase is RotationPhase.UNKNOWN or saved.terminal_history[-1].revision == saved.revision
    if saved.phase is RotationPhase.EXPIRED:
        return saved.pending_effect is PendingEffect.NONE and prior.phase not in {RotationPhase.COMPLETE, RotationPhase.ROLLED_BACK} and _preserves_evidence(prior, saved, preserve_outcome=False)
    if saved.phase is RotationPhase.UNKNOWN:
        return saved.pending_effect is PendingEffect.NONE and prior.pending_effect is not PendingEffect.NONE and _preserves_evidence(prior, saved, preserve_outcome=False)
    if prior.phase is RotationPhase.PREPARED:
        return (
            saved.phase is RotationPhase.PREPARED and prior.pending_effect is PendingEffect.NONE
            and saved.pending_effect is PendingEffect.RESTART_DUAL and saved.effect_revision == saved.revision
            and _preserves_evidence(prior, saved, preserve_restart=False)
            and saved.restart_intended_at == saved.last_observed_at
        ) or (
            saved.phase is RotationPhase.DUAL_READY and prior.pending_effect is PendingEffect.RESTART_DUAL
            and saved.pending_effect is PendingEffect.NONE and saved.delivery_locator is None
            and saved.effect_revision == prior.effect_revision and _preserves_evidence(prior, saved, preserve_runtime=False)
        )
    if prior.phase is RotationPhase.DUAL_READY:
        return (
            saved.phase is RotationPhase.PROVIDER_PENDING and prior.pending_effect is PendingEffect.NONE
            and saved.pending_effect is PendingEffect.PROVIDER_UPDATE and saved.effect_revision == saved.revision
            and _preserves_evidence(prior, saved)
        )
    if prior.phase is RotationPhase.PROVIDER_PENDING:
        return (
            saved.phase is RotationPhase.AWAITING_DELIVERY and prior.pending_effect is PendingEffect.PROVIDER_UPDATE
            and saved.pending_effect is PendingEffect.NONE and _preserves_evidence(prior, saved)
        )
    if prior.phase is RotationPhase.AWAITING_DELIVERY:
        if saved.phase is RotationPhase.RETIRING:
            return (
                prior.pending_effect is PendingEffect.NONE and saved.pending_effect is PendingEffect.RETIRE_PREVIOUS
                and prior.delivery_locator is not None and prior.runtime_proof is not None
                and prior.runtime_proof.loaded_generations == (prior.target_generation,)
                and saved.effect_revision == saved.revision and _preserves_evidence(prior, saved)
            )
        if saved.phase is not RotationPhase.AWAITING_DELIVERY:
            return False
        return (
            prior.pending_effect is PendingEffect.NONE and saved.pending_effect is PendingEffect.NONE
            and prior.delivery_locator is None and saved.delivery_locator is not None
            and saved.runtime_proof == prior.runtime_proof and saved.effect_revision == prior.effect_revision
            and saved.restart_intended_at == prior.restart_intended_at and saved.terminal_history == prior.terminal_history
        ) or (
            prior.pending_effect is PendingEffect.NONE and saved.pending_effect is PendingEffect.RESTART_TARGET_ONLY
            and prior.delivery_locator is not None and saved.effect_revision == saved.revision
            and _preserves_evidence(prior, saved, preserve_restart=False)
            and saved.restart_intended_at == saved.last_observed_at
        ) or (
            prior.pending_effect is PendingEffect.RESTART_TARGET_ONLY and saved.pending_effect is PendingEffect.NONE
            and saved.runtime_proof is not None and saved.runtime_proof.loaded_generations == (saved.target_generation,)
            and saved.delivery_locator == prior.delivery_locator and saved.effect_revision == prior.effect_revision
            and saved.restart_intended_at == prior.restart_intended_at and saved.terminal_history == prior.terminal_history
        )
    if prior.phase is RotationPhase.RETIRING:
        return (
            saved.phase is RotationPhase.COMPLETE and prior.pending_effect is PendingEffect.RETIRE_PREVIOUS
            and saved.pending_effect is PendingEffect.NONE and saved.runtime_proof == prior.runtime_proof
            and saved.delivery_locator == prior.delivery_locator and saved.effect_revision == prior.effect_revision
            and saved.restart_intended_at == prior.restart_intended_at and saved.terminal_history[-1].revision == saved.revision
        )
    return False


def _preserves_evidence(
    prior: RotationRecord, saved: RotationRecord, *, preserve_restart: bool = True,
    preserve_runtime: bool = True, preserve_outcome: bool = True,
) -> bool:
    return (
        (not preserve_runtime or saved.runtime_proof == prior.runtime_proof)
        and saved.delivery_locator == prior.delivery_locator
        and (not preserve_outcome or saved.terminal_code == prior.terminal_code)
        and saved.terminal_history == prior.terminal_history
        and (not preserve_restart or saved.restart_intended_at == prior.restart_intended_at)
    )


def _is_successor(prior: RotationRecord, record: RotationRecord) -> bool:
    return (
        prior.phase in {RotationPhase.COMPLETE, RotationPhase.ROLLED_BACK}
        and record.phase is RotationPhase.PREPARED and record.pending_effect is PendingEffect.NONE
        and record.runtime_proof is None and record.delivery_locator is None and record.terminal_code is None
        and record.terminal_history == prior.terminal_history
        and (record.owner_id, record.canonical_root, record.owner_uid, record.source_instance, record.service_id)
        == (prior.owner_id, prior.canonical_root, prior.owner_uid, prior.source_instance, prior.service_id)
        and record.previous_generation == (prior.target_generation if prior.phase is RotationPhase.COMPLETE else prior.previous_generation)
        and record.target_generation != record.previous_generation
    )


def _valid_generations(value: object) -> bool:
    return type(value) is tuple and 1 <= len(value) <= 2 and tuple(sorted(value)) == value and len(set(value)) == len(value) and all(type(item) is int and 1 <= item <= _MAX_GENERATION for item in value)


def _valid_root(value: object) -> bool:
    if type(value) is not str or not 1 < len(value) <= 512 or "\x00" in value:
        return False
    try:
        path = Path(value)
        return path.is_absolute() and str(path.resolve()) == value and value != "/"
    except (OSError, ValueError):
        return False


def _immutable_facts(record: RotationRecord) -> tuple[object, ...]:
    return (
        record.owner_id, record.canonical_root, record.owner_uid, record.source_instance, record.service_id,
        record.binding_revision, record.previous_generation, record.target_generation, record.overlap_deadline,
    )


def _conflicts(left: RotationRecord, right: RotationRecord) -> bool:
    return left.source_instance == right.source_instance or left.service_id == right.service_id


def _phase_allowed(before: RotationPhase, after: RotationPhase) -> bool:
    return after in {
        RotationPhase.PREPARED: {RotationPhase.PREPARED, RotationPhase.DUAL_READY, RotationPhase.UNKNOWN, RotationPhase.EXPIRED, RotationPhase.ROLLED_BACK},
        RotationPhase.DUAL_READY: {RotationPhase.DUAL_READY, RotationPhase.PROVIDER_PENDING, RotationPhase.UNKNOWN, RotationPhase.EXPIRED, RotationPhase.ROLLED_BACK},
        RotationPhase.PROVIDER_PENDING: {RotationPhase.PROVIDER_PENDING, RotationPhase.AWAITING_DELIVERY, RotationPhase.UNKNOWN, RotationPhase.EXPIRED, RotationPhase.ROLLED_BACK},
        RotationPhase.AWAITING_DELIVERY: {RotationPhase.AWAITING_DELIVERY, RotationPhase.RETIRING, RotationPhase.UNKNOWN, RotationPhase.EXPIRED, RotationPhase.ROLLED_BACK},
        RotationPhase.RETIRING: {RotationPhase.RETIRING, RotationPhase.COMPLETE, RotationPhase.UNKNOWN, RotationPhase.EXPIRED, RotationPhase.ROLLED_BACK},
        RotationPhase.UNKNOWN: {RotationPhase.UNKNOWN, RotationPhase.ROLLED_BACK},
        RotationPhase.EXPIRED: {RotationPhase.EXPIRED, RotationPhase.UNKNOWN, RotationPhase.ROLLED_BACK},
        RotationPhase.COMPLETE: {RotationPhase.COMPLETE},
        RotationPhase.ROLLED_BACK: {RotationPhase.ROLLED_BACK},
    }[before]


def _require_name(value: object, label: str) -> None:
    if type(value) is not str or _NAME.fullmatch(value) is None:
        raise ValueError(f"{label} is invalid")


def _require_time(value: object) -> None:
    if type(value) is not int or value < 0:
        raise ValueError("rotation time is invalid")


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result
