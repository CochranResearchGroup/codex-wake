"""Portable filesystem state signals backed by structural reconciliation.

Filesystem notifications are deliberately absent from the correctness seam.
Callers may submit hints to :class:`FilesystemSignalRunner`, but every run
samples the allowlisted path and derives authority from that sample.
"""
from __future__ import annotations

import hashlib
import json
import os
import stat as stat_module
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from types import MappingProxyType
from typing import Iterable, Literal, Mapping

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
    SourceReconcileResult,
    Verification,
)


FilesystemRecipe = Literal["created", "exists", "changed"]
_SOURCE = "filesystem"
_KINDS = frozenset({"file.created", "file.exists", "file.changed"})


@dataclass(frozen=True, slots=True)
class FileFingerprint:
    exists: bool
    file_kind: str
    digest: str

    def baseline(self) -> Mapping[str, str | bool]:
        return MappingProxyType(
            {
                "exists": self.exists,
                "file_kind": self.file_kind,
                "fingerprint": self.digest,
            }
        )


class FilesystemSignalRunner:
    """Reconcile filesystem state; notification state affects evidence only."""

    def __init__(
        self,
        adapters: Iterable[FilesystemSignalAdapter],
        *,
        armed_signals: Iterable[ArmedSignal] = (),
        initial_reason: Literal[
            "periodic", "startup", "watcher_recovery", "watcher_overflow"
        ] = "periodic",
    ) -> None:
        configured = tuple(adapters)
        self._adapters = {item.source_instance: item for item in configured}
        if len(self._adapters) != len(configured):
            raise ValueError("filesystem source instances must be unique")
        self._hint_counts: dict[str, int] = {}
        self._watcher_uncertain = False
        self._armed_signals = tuple(armed_signals)
        self._reason = initial_reason
        self.last_result: SourceReconcileResult | None = None

    def notify(self, path: str | Path) -> bool:
        for adapter in self._adapters.values():
            try:
                _resolved, relative = _normalize_path(adapter.root, path)
            except ValueError:
                continue
            if relative == adapter.relative_path:
                self._hint_counts[adapter.source_instance] = min(
                    self._hint_counts.get(adapter.source_instance, 0) + 1,
                    1_000_000,
                )
                return True
        return False

    def watcher_lost(self) -> None:
        self._watcher_uncertain = True
        self._reason = "watcher_recovery"

    def watcher_overflow(self) -> None:
        self._watcher_uncertain = True
        self._reason = "watcher_overflow"

    def reconcile(
        self,
        module: SignalEngine,
        now: datetime,
        limits: EvaluationLimits,
    ) -> SourceReconcileResult:
        if now.tzinfo is None or now.utcoffset() is None:
            self.last_result = SourceReconcileResult(_SOURCE, 0, 0, 1)
            return self.last_result
        scanned = observed = degraded = 0
        if limits.max_candidates <= 0:
            self.last_result = SourceReconcileResult(_SOURCE, 0, 0, 1)
            return self.last_result
        groups: dict[str, list[ArmedSignal]] = {}
        for armed in self._armed_signals[: limits.max_candidates]:
            if not isinstance(armed, ArmedSignal) or armed.spec.source != _SOURCE:
                continue
            adapter = self._adapters.get(armed.spec.source_instance)
            if adapter is None or not adapter._valid_request(armed.spec):
                degraded += 1
                continue
            groups.setdefault(armed.spec.source_instance, []).append(armed)
        for source_instance, source_arms in groups.items():
            adapter = self._adapters[source_instance]
            scanned += 1
            sampled = _fingerprint(adapter.root, adapter.relative_path)
            if isinstance(sampled, Degraded):
                degraded += 1
                continue
            previous = module.source_checkpoint(_SOURCE, adapter.source_instance)
            if isinstance(previous, Degraded):
                degraded += 1
                continue
            order = (
                previous.checkpoint_order + 1
                if isinstance(previous, SourceCommit)
                else 1
            )
            previous_state = _checkpoint_fingerprint(previous)
            if isinstance(previous, SourceCommit) and previous_state is None:
                degraded += 1
                continue
            if previous_state is None:
                earliest = min(source_arms, key=lambda item: item.registered_at)
                previous_state = FileFingerprint(
                    bool(earliest.anchor.baseline.get("exists")),
                    str(earliest.anchor.baseline.get("file_kind", "unknown")),
                    str(earliest.anchor.baseline.get("fingerprint", "")),
                )
            hint_count = self._hint_counts.get(adapter.source_instance, 0)
            uncertain = self._watcher_uncertain or self._reason != "periodic"
            coalesced = uncertain or hint_count > 1
            observation_reason = (
                self._reason if uncertain else "notification" if hint_count else "periodic"
            )
            observations: list[NormalizedObservation] = []
            kinds = {armed.spec.kind for armed in source_arms}
            for kind in sorted(kinds):
                recipe = kind.removeprefix("file.")
                if recipe == "exists":
                    matched = sampled.exists and (
                        previous is None or not previous_state.exists
                    )
                elif recipe == "created":
                    matched = sampled.exists and not previous_state.exists
                else:
                    matched = sampled.digest != previous_state.digest
                if not matched:
                    continue
                attributes = MappingProxyType(
                    {
                        "matched": True,
                        "exists": sampled.exists,
                        "file_kind": sampled.file_kind,
                        "fingerprint": sampled.digest,
                        "baseline_fingerprint": previous_state.digest,
                        "coalesced": coalesced,
                        "observation_reason": observation_reason,
                        "hint_count": hint_count,
                    }
                )
                observations.append(
                    NormalizedObservation(
                        _SOURCE,
                        adapter.source_instance,
                        kind,
                        adapter.subject,
                        "filesystem-reconciliation-v1",
                        _digest(
                            {
                                "source_instance": adapter.source_instance,
                                "kind": kind,
                                "order": order,
                                "fingerprint": sampled.digest,
                            }
                        ),
                        now,
                        now,
                        attributes,
                        Verification("verified", "filesystem_state_recheck"),
                        f"filesystem:{sampled.digest[:24]}",
                    )
                )
            checkpoint = SourceCommit(
                _SOURCE,
                adapter.source_instance,
                _checkpoint_payload(
                    sampled,
                    matched=bool(observations),
                    coalesced=coalesced,
                    observation_reason=observation_reason,
                    hint_count=hint_count,
                ),
                order,
                now,
            )
            outcome = module.ingest(tuple(observations), checkpoint)
            if isinstance(outcome, Ingested):
                observed += len(observations)
                self._hint_counts.pop(adapter.source_instance, None)
            else:
                degraded += 1
        if degraded == 0:
            self._watcher_uncertain = False
            self._reason = "periodic"
        self.last_result = SourceReconcileResult(_SOURCE, scanned, observed, degraded)
        return self.last_result


class FilesystemSignalAdapter:
    """One allowlisted path exposed through the provider-neutral signal seam."""

    def __init__(
        self,
        root: Path,
        path: str | Path,
        *,
        source_instance: str | None = None,
    ) -> None:
        self.root = Path(root).resolve()
        self.path, self.relative_path = _normalize_path(self.root, path)
        identity = _digest({"root": str(self.root), "path": self.relative_path})[:24]
        self.source_instance = source_instance or f"local-{identity}"
        if not _safe_instance(self.source_instance):
            raise ValueError("filesystem source instance is invalid")
        self.subject = f"path:{self.relative_path}"

    def contract(self) -> SourceContract:
        return SourceContract(
            _SOURCE,
            self.source_instance,
            _KINDS,
            frozenset({self.subject}),
            MappingProxyType(
                {
                    "matched": bool,
                    "exists": bool,
                    "file_kind": str,
                    "fingerprint": str,
                    "baseline_fingerprint": str,
                    "coalesced": bool,
                    "observation_reason": str,
                    "hint_count": int,
                }
            ),
            max_clauses=1,
            max_attribute_bytes=1024,
            max_evidence_ref_bytes=128,
        )

    def request(self, recipe: FilesystemRecipe) -> SignalRequest:
        if recipe not in {"created", "exists", "changed"}:
            raise ValueError("filesystem recipe is invalid")
        condition = "holds" if recipe == "exists" else "becomes"
        return SignalRequest(
            1,
            _SOURCE,
            self.source_instance,
            "state",
            f"file.{recipe}",
            self.subject,
            condition,
            (Eq("matched", True),),
            "required",
        )

    def establish_anchor(
        self,
        spec: SignalRequest,
        now: datetime,
    ) -> SourceAnchor | Invalid | Degraded:
        if not self._valid_request(spec) or now.tzinfo is None or now.utcoffset() is None:
            return Invalid(
                None,
                "FILESYSTEM_SIGNAL_NOT_ALLOWED",
                ("filesystem signal is outside the configured path",),
            )
        sampled = _fingerprint(self.root, self.relative_path)
        if isinstance(sampled, Degraded):
            return sampled
        return SourceAnchor(
            0,
            f"filesystem:{sampled.digest}",
            sampled.baseline(),
            "state_recheck",
        )

    def _valid_request(self, spec: SignalRequest) -> bool:
        return bool(
            type(spec) is SignalRequest
            and spec.source == _SOURCE
            and spec.source_instance == self.source_instance
            and spec.kind in _KINDS
            and spec.subject == self.subject
            and spec.semantics == "state"
            and spec.condition == ("holds" if spec.kind == "file.exists" else "becomes")
            and type(spec.where) is tuple
            and len(spec.where) == 1
            and type(spec.where[0]) is Eq
            and spec.where[0].field == "matched"
            and spec.where[0].value is True
            and spec.verification == "required"
        )


def _safe_instance(value: object) -> bool:
    return isinstance(value, str) and 0 < len(value) <= 96 and all(
        character.isalnum() or character in "_-" for character in value
    )


def _normalize_path(root: Path, path: str | Path) -> tuple[Path, str]:
    raw = os.fspath(path)
    if not isinstance(raw, str) or not raw or "\x00" in raw:
        raise ValueError("filesystem path is invalid")
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = root / candidate
    resolved = candidate.resolve(strict=False)
    try:
        relative = resolved.relative_to(root)
    except ValueError:
        raise ValueError("filesystem path is outside the configured root") from None
    normalized = relative.as_posix()
    if not normalized or normalized == "." or len(normalized.encode("utf-8")) > 512:
        raise ValueError("filesystem path is invalid")
    return resolved, normalized


def _fingerprint(root: Path, relative_path: str) -> FileFingerprint | Degraded:
    try:
        path, _normalized = _normalize_path(root, relative_path)
        sampled = path.stat()
    except FileNotFoundError:
        payload = {"exists": False, "kind": "missing"}
        return FileFingerprint(False, "missing", _digest(payload))
    except (OSError, ValueError):
        return Degraded(None, "FILESYSTEM_SAMPLE_UNAVAILABLE", None)
    mode = sampled.st_mode
    if stat_module.S_ISREG(mode):
        kind = "file"
    elif stat_module.S_ISDIR(mode):
        kind = "directory"
    elif stat_module.S_ISLNK(mode):
        kind = "symlink"
    else:
        kind = "other"
    payload = {
        "exists": True,
        "kind": kind,
        "size": int(sampled.st_size),
        "mtime_ns": int(sampled.st_mtime_ns),
        "ctime_ns": int(sampled.st_ctime_ns),
        "device": int(sampled.st_dev),
        "inode": int(sampled.st_ino),
    }
    return FileFingerprint(True, kind, _digest(payload))


def _digest(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _checkpoint_payload(
    fingerprint: FileFingerprint,
    *,
    matched: bool,
    coalesced: bool,
    observation_reason: str,
    hint_count: int,
) -> str:
    return json.dumps(
        {
            "exists": fingerprint.exists,
            "file_kind": fingerprint.file_kind,
            "fingerprint": fingerprint.digest,
            "matched": matched,
            "coalesced": coalesced,
            "observation_reason": observation_reason,
            "hint_count": hint_count,
        },
        sort_keys=True,
        separators=(",", ":"),
    )


def _checkpoint_fingerprint(commit: SourceCommit | None) -> FileFingerprint | None:
    if commit is None:
        return None
    try:
        payload = json.loads(commit.checkpoint)
        exists = payload["exists"]
        file_kind = payload["file_kind"]
        digest = payload["fingerprint"]
        if (
            type(exists) is not bool
            or not isinstance(file_kind, str)
            or not isinstance(digest, str)
            or len(digest) != 64
        ):
            return None
        return FileFingerprint(exists, file_kind, digest)
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None
