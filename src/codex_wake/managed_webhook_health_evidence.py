"""Durable, secret-free current-generation evidence for managed webhook health.

This store records only a successfully committed signed delivery and a completed
poll observation. It does not observe provider objects, listener readiness, or
dispatch, and its evidence is useful only while it remains exact and fresh for
one managed binding.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, replace
import fcntl
import json
import os
from pathlib import Path
import re
import stat
import tempfile
from typing import Iterator

from .managed_webhook_health import PollingFallbackHealth, ProviderDeliveryHealth
from .managed_webhooks import ManagedWebhookBinding


_FINGERPRINT = re.compile(r"[0-9a-f]{64}")
_LOCATOR = re.compile(r"[a-z][a-z0-9_-]{0,95}")
_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,95}")
_MAX_FILE_BYTES = 16_384
_MAX_AGE_SECONDS = 300


@dataclass(frozen=True, slots=True)
class ManagedWebhookHealthEvidence:
    """One owner-bound record, deliberately separate from health projection."""

    owner_id: str
    source_instance: str
    binding_generation: int
    secret_generation: int
    desired_fingerprint: str
    delivery_locator: str | None = None
    delivery_observed_at: int | None = None
    polling_observed_at: int | None = None

    def __post_init__(self) -> None:
        if (
            type(self.owner_id) is not str or _NAME.fullmatch(self.owner_id) is None
            or type(self.source_instance) is not str or _NAME.fullmatch(self.source_instance) is None
            or type(self.binding_generation) is not int or not 0 <= self.binding_generation < 2**63
            or type(self.secret_generation) is not int or not 1 <= self.secret_generation < 2**31
            or type(self.desired_fingerprint) is not str or _FINGERPRINT.fullmatch(self.desired_fingerprint) is None
            or (self.delivery_locator is None) != (self.delivery_observed_at is None)
            or self.delivery_locator is not None and _LOCATOR.fullmatch(self.delivery_locator) is None
            or self.delivery_observed_at is not None and not _valid_time(self.delivery_observed_at)
            or self.polling_observed_at is not None and not _valid_time(self.polling_observed_at)
        ):
            raise ValueError("managed webhook health evidence is invalid")

    @classmethod
    def for_binding(cls, binding: ManagedWebhookBinding) -> "ManagedWebhookHealthEvidence":
        _require_binding(binding)
        return cls(
            binding.owner_id, binding.source_instance, binding.generation,
            binding.secret_generation, binding.desired_fingerprint,
        )

    def matches(self, binding: ManagedWebhookBinding) -> bool:
        return type(binding) is ManagedWebhookBinding and (
            self.owner_id, self.source_instance, self.binding_generation,
            self.secret_generation, self.desired_fingerprint,
        ) == (
            binding.owner_id, binding.source_instance, binding.generation,
            binding.secret_generation, binding.desired_fingerprint,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": "managed_webhook_health_evidence", "version": 1,
            "owner_id": self.owner_id, "source_instance": self.source_instance,
            "binding_generation": self.binding_generation,
            "secret_generation": self.secret_generation,
            "desired_fingerprint": self.desired_fingerprint,
            "delivery_locator": self.delivery_locator,
            "delivery_observed_at": self.delivery_observed_at,
            "polling_observed_at": self.polling_observed_at,
        }

    @classmethod
    def from_dict(cls, value: object) -> "ManagedWebhookHealthEvidence":
        fields = {
            "kind", "version", "owner_id", "source_instance", "binding_generation",
            "secret_generation", "desired_fingerprint", "delivery_locator",
            "delivery_observed_at", "polling_observed_at",
        }
        if type(value) is not dict or set(value) != fields or value.get("kind") != "managed_webhook_health_evidence" or value.get("version") != 1:
            raise ValueError("managed webhook health evidence is invalid")
        try:
            return cls(
                value["owner_id"], value["source_instance"], value["binding_generation"],
                value["secret_generation"], value["desired_fingerprint"],
                value["delivery_locator"], value["delivery_observed_at"],
                value["polling_observed_at"],
            )
        except (TypeError, ValueError):
            raise ValueError("managed webhook health evidence is invalid") from None


class ManagedWebhookHealthEvidenceStore:
    """Single-writer owner record under one wake root with fail-closed reads."""

    def __init__(self, wake_root: Path):
        self.wake_root = Path(wake_root).resolve()
        self.path = self.wake_root / "managed-webhook" / "health-evidence.json"
        self.lock_path = self.wake_root / "managed-webhook" / "health-evidence.lock"

    def record_delivery(
        self, binding: ManagedWebhookBinding, *, generation: int, journal_locator: str,
        observed_at: int,
    ) -> ManagedWebhookHealthEvidence:
        _require_binding(binding)
        if generation != binding.secret_generation or type(journal_locator) is not str or _LOCATOR.fullmatch(journal_locator) is None or not _valid_time(observed_at):
            raise ValueError("managed webhook health evidence is invalid")
        with self._locked():
            current = self._load_unlocked()
            evidence = self._exact_or_new(current, binding)
            if evidence.delivery_locator is not None and evidence.delivery_locator != journal_locator:
                raise ValueError("managed webhook health evidence is ambiguous")
            if evidence.delivery_observed_at is not None and observed_at < evidence.delivery_observed_at:
                raise ValueError("managed webhook health evidence clock moved backwards")
            saved = replace(
                evidence, delivery_locator=journal_locator, delivery_observed_at=observed_at,
            )
            self._save_unlocked(saved)
            return saved

    def record_polling(
        self, binding: ManagedWebhookBinding, *, observed_at: int,
    ) -> ManagedWebhookHealthEvidence:
        _require_binding(binding)
        if not _valid_time(observed_at):
            raise ValueError("managed webhook health evidence is invalid")
        with self._locked():
            current = self._load_unlocked()
            evidence = self._exact_or_new(current, binding)
            if evidence.polling_observed_at is not None and observed_at < evidence.polling_observed_at:
                raise ValueError("managed webhook health evidence clock moved backwards")
            saved = replace(evidence, polling_observed_at=observed_at)
            self._save_unlocked(saved)
            return saved

    def project(
        self, binding: ManagedWebhookBinding, *, now: int,
    ) -> tuple[ProviderDeliveryHealth, PollingFallbackHealth]:
        _require_binding(binding)
        if not _valid_time(now):
            return ProviderDeliveryHealth.UNKNOWN, PollingFallbackHealth.UNKNOWN
        try:
            with self._locked():
                evidence = self._load_unlocked()
        except ValueError:
            return ProviderDeliveryHealth.UNKNOWN, PollingFallbackHealth.UNKNOWN
        if evidence is None:
            return ProviderDeliveryHealth.UNPROVEN, PollingFallbackHealth.UNOBSERVED
        if not evidence.matches(binding):
            return ProviderDeliveryHealth.UNKNOWN, PollingFallbackHealth.UNKNOWN
        delivery = (
            ProviderDeliveryHealth.OBSERVED
            if _fresh(evidence.delivery_observed_at, now)
            else ProviderDeliveryHealth.UNPROVEN
        )
        polling = (
            PollingFallbackHealth.READY
            if _fresh(evidence.polling_observed_at, now)
            else PollingFallbackHealth.DEGRADED
            if evidence.polling_observed_at is not None
            else PollingFallbackHealth.UNOBSERVED
        )
        return delivery, polling

    def _exact_or_new(
        self, current: ManagedWebhookHealthEvidence | None,
        binding: ManagedWebhookBinding,
    ) -> ManagedWebhookHealthEvidence:
        if current is None:
            return ManagedWebhookHealthEvidence.for_binding(binding)
        if not current.matches(binding):
            raise ValueError("managed webhook health evidence is ambiguous")
        return current

    @contextmanager
    def _locked(self) -> Iterator[None]:
        descriptor: int | None = None
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            parent_metadata = self.path.parent.lstat()
            if (
                self.path.parent.is_symlink()
                or not stat.S_ISDIR(parent_metadata.st_mode)
                or parent_metadata.st_uid != os.getuid()
            ):
                raise ValueError("managed webhook health evidence is invalid")
            os.chmod(self.path.parent, 0o700)
            descriptor = os.open(
                self.lock_path,
                os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0),
                0o600,
            )
            metadata = os.fstat(descriptor)
            if not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.getuid():
                raise ValueError("managed webhook health evidence is invalid")
            os.fchmod(descriptor, 0o600)
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            yield
        except ValueError:
            raise
        except OSError:
            raise ValueError("managed webhook health evidence is unavailable") from None
        finally:
            if descriptor is not None:
                try:
                    fcntl.flock(descriptor, fcntl.LOCK_UN)
                finally:
                    os.close(descriptor)

    def _load_unlocked(self) -> ManagedWebhookHealthEvidence | None:
        if self.path.is_symlink():
            raise ValueError("managed webhook health evidence is invalid")
        if not self.path.exists():
            return None
        try:
            if not self.path.is_file() or self.path.stat().st_size > _MAX_FILE_BYTES:
                raise ValueError
            return ManagedWebhookHealthEvidence.from_dict(json.loads(
                self.path.read_text(encoding="utf-8"), object_pairs_hook=_unique_object,
            ))
        except (OSError, TypeError, ValueError, json.JSONDecodeError):
            raise ValueError("managed webhook health evidence is invalid") from None

    def _save_unlocked(self, evidence: ManagedWebhookHealthEvidence) -> None:
        temporary: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                "w", encoding="utf-8", dir=self.path.parent,
                prefix=".health-evidence-", delete=False,
            ) as handle:
                temporary = Path(handle.name)
                os.chmod(temporary, 0o600)
                json.dump(evidence.to_dict(), handle, sort_keys=True, separators=(",", ":"))
                handle.write("\n")
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
            raise ValueError("managed webhook health evidence is unavailable") from None
        finally:
            if temporary is not None and temporary.exists():
                try:
                    temporary.unlink()
                except OSError:
                    pass


def _require_binding(binding: object) -> None:
    if type(binding) is not ManagedWebhookBinding:
        raise ValueError("managed webhook health evidence is invalid")


def _valid_time(value: object) -> bool:
    return type(value) is int and 0 <= value < 2**63


def _fresh(observed_at: int | None, now: int) -> bool:
    return observed_at is not None and observed_at <= now and now - observed_at <= _MAX_AGE_SECONDS


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result
