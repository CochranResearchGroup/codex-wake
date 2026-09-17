"""Secret-free, owner-scoped webhook binding reconciliation.

This module is deliberately below the provider adapter and above neither
ingress nor dispatch.  It records only opaque references and compact outcome
codes; credentials, secret material, provider responses, and webhook payloads
never enter its data model or JSON store.
"""
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, replace
from enum import Enum
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import tempfile
import threading
from typing import Protocol
from urllib.parse import urlsplit


_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,95}")
_REPOSITORY = re.compile(r"[A-Za-z0-9_.-]{1,80}/[A-Za-z0-9_.-]{1,80}")
_ENV_REF = re.compile(r"[A-Z][A-Z0-9_]{0,95}")
_FINGERPRINT = re.compile(r"[0-9a-f]{64}")
_CODE = re.compile(r"[A-Z][A-Z0-9_]{0,63}")
_MAX_BINDINGS = 32
_MAX_RECEIPTS = 32
_MAX_FILE_BYTES = 262_144


class LifecycleState(str, Enum):
    UNMANAGED = "UNMANAGED"
    CREATING = "CREATING"
    ACTIVE = "ACTIVE"
    UPDATING = "UPDATING"
    UNKNOWN = "UNKNOWN"
    DISABLED = "DISABLED"
    DELETED = "DELETED"


class OperationKind(str, Enum):
    OBSERVE = "OBSERVE"
    CREATE = "CREATE"
    UPDATE = "UPDATE"


class OperationState(str, Enum):
    INTENDED = "INTENDED"
    SUCCEEDED = "SUCCEEDED"
    UNKNOWN = "UNKNOWN"


class InventoryClass(str, Enum):
    ABSENT = "ABSENT"
    EXACT = "EXACT"
    DUPLICATE = "DUPLICATE"
    DRIFTED = "DRIFTED"
    COLLISION = "COLLISION"
    MISSING = "MISSING"


class PlanAction(str, Enum):
    NOOP = "NOOP"
    WRITE = "WRITE"
    READ_ONLY = "READ_ONLY"


@dataclass(frozen=True, slots=True)
class OperationReceipt:
    """A bounded, sanitized reconciliation receipt (not a provider response)."""

    operation_id: str
    operation: OperationKind
    state: OperationState
    generation: int
    inventory: InventoryClass
    hook_id: int | None
    code: str

    def __post_init__(self) -> None:
        if (
            type(self.operation_id) is not str or _NAME.fullmatch(self.operation_id) is None
            or not isinstance(self.operation, OperationKind)
            or not isinstance(self.state, OperationState)
            or type(self.generation) is not int or not 0 <= self.generation < 2**63
            or not isinstance(self.inventory, InventoryClass)
            or self.hook_id is not None and (type(self.hook_id) is not int or not 0 < self.hook_id < 2**63)
            or type(self.code) is not str or _CODE.fullmatch(self.code) is None
        ):
            raise ValueError("managed webhook receipt is invalid")

    def to_dict(self) -> dict[str, object]:
        return {
            "operation_id": self.operation_id,
            "operation": self.operation.value,
            "state": self.state.value,
            "generation": self.generation,
            "inventory": self.inventory.value,
            "hook_id": self.hook_id,
            "code": self.code,
        }

    @classmethod
    def from_dict(cls, value: object) -> "OperationReceipt":
        if type(value) is not dict or set(value) != {
            "operation_id", "operation", "state", "generation", "inventory", "hook_id", "code"
        }:
            raise ValueError("managed webhook receipt is invalid")
        try:
            return cls(
                operation_id=value["operation_id"], operation=OperationKind(value["operation"]),
                state=OperationState(value["state"]), generation=value["generation"],
                inventory=InventoryClass(value["inventory"]), hook_id=value["hook_id"], code=value["code"],
            )
        except (TypeError, ValueError):
            raise ValueError("managed webhook receipt is invalid") from None


@dataclass(frozen=True, slots=True)
class ManagedWebhookBinding:
    """The complete nonsecret ownership and desired-state identity for one hook."""

    owner_id: str
    installation_id: str
    canonical_root: str
    owner_uid: int
    provider_host: str
    source_instance: str
    repository: str
    repository_id: int
    callback_url: str
    events: tuple[str, ...]
    service_id: str
    executable_id: str
    provider_credential_ref: str
    secret_generation: int
    provider_hook_id: int | None = None
    desired_fingerprint: str = ""
    lifecycle: LifecycleState = LifecycleState.UNMANAGED
    generation: int = 0
    receipts: tuple[OperationReceipt, ...] = ()

    def __post_init__(self) -> None:
        if not _valid_binding_values(self):
            raise ValueError("managed webhook binding is invalid")
        fingerprint = _fingerprint(self)
        if self.desired_fingerprint and self.desired_fingerprint != fingerprint:
            raise ValueError("managed webhook binding is invalid")
        object.__setattr__(self, "desired_fingerprint", fingerprint)

    def to_dict(self) -> dict[str, object]:
        return {
            "owner_id": self.owner_id,
            "installation_id": self.installation_id,
            "canonical_root": self.canonical_root,
            "owner_uid": self.owner_uid,
            "provider_host": self.provider_host,
            "source_instance": self.source_instance,
            "repository": self.repository,
            "repository_id": self.repository_id,
            "callback_url": self.callback_url,
            "events": list(self.events),
            "service_id": self.service_id,
            "executable_id": self.executable_id,
            "provider_credential_ref": self.provider_credential_ref,
            "secret_generation": self.secret_generation,
            "provider_hook_id": self.provider_hook_id,
            "desired_fingerprint": self.desired_fingerprint,
            "lifecycle": self.lifecycle.value,
            "generation": self.generation,
            "receipts": [receipt.to_dict() for receipt in self.receipts],
        }

    @classmethod
    def from_dict(cls, value: object) -> "ManagedWebhookBinding":
        fields = {
            "owner_id", "installation_id", "canonical_root", "owner_uid", "provider_host", "source_instance",
            "repository", "repository_id", "callback_url", "events", "service_id", "executable_id",
            "provider_credential_ref", "secret_generation",
            "provider_hook_id", "desired_fingerprint", "lifecycle", "generation", "receipts",
        }
        if type(value) is not dict or set(value) != fields or type(value["events"]) is not list or type(value["receipts"]) is not list:
            raise ValueError("managed webhook binding is invalid")
        try:
            return cls(
                **{key: value[key] for key in fields - {"events", "receipts", "lifecycle"}},
                events=tuple(value["events"]), receipts=tuple(OperationReceipt.from_dict(item) for item in value["receipts"]),
                lifecycle=LifecycleState(value["lifecycle"]),
            )
        except (TypeError, ValueError):
            raise ValueError("managed webhook binding is invalid") from None


@dataclass(frozen=True, slots=True)
class ProviderHook:
    """The bounded, secret-free part of a provider hook inventory item."""

    hook_id: int
    callback_url: str
    events: tuple[str, ...]
    active: bool
    content_type: str
    insecure_ssl: bool

    def __post_init__(self) -> None:
        if (
            type(self.hook_id) is not int or not 0 < self.hook_id < 2**63
            or not _valid_provider_callback(self.callback_url)
            or not _valid_provider_events(self.events)
            or type(self.active) is not bool or self.content_type not in {"json", "form"}
            or type(self.insecure_ssl) is not bool
        ):
            raise ValueError("provider hook is invalid")

    def matches(self, binding: ManagedWebhookBinding) -> bool:
        return (
            self.callback_url == binding.callback_url and self.events == binding.events and self.active
            and self.content_type == "json" and not self.insecure_ssl
        )

    def targets(self, binding: ManagedWebhookBinding) -> bool:
        return self.callback_url == binding.callback_url


class WebhookProviderManager(Protocol):
    """Provider adapter contract; implementations must never return raw responses."""

    def list_hooks(self, *, repository_id: int) -> tuple[ProviderHook, ...]: ...

    def create_hook(self, binding: ManagedWebhookBinding) -> ProviderHook: ...

    def update_hook(self, *, hook_id: int, binding: ManagedWebhookBinding) -> ProviderHook: ...

    def get_hook(self, *, repository_id: int, hook_id: int) -> ProviderHook | None: ...


@dataclass(frozen=True, slots=True)
class ReconciliationPlan:
    owner_id: str
    generation: int
    desired_fingerprint: str
    inventory: InventoryClass
    action: PlanAction
    operation: OperationKind
    hook_id: int | None

    def __post_init__(self) -> None:
        if (
            type(self.owner_id) is not str or _NAME.fullmatch(self.owner_id) is None
            or type(self.generation) is not int or not 0 <= self.generation < 2**63
            or type(self.desired_fingerprint) is not str or _FINGERPRINT.fullmatch(self.desired_fingerprint) is None
            or not isinstance(self.inventory, InventoryClass) or not isinstance(self.action, PlanAction)
            or not isinstance(self.operation, OperationKind)
            or self.hook_id is not None and (type(self.hook_id) is not int or not 0 < self.hook_id < 2**63)
        ):
            raise ValueError("managed webhook reconciliation plan is invalid")

    def to_dict(self) -> dict[str, object]:
        return {
            "owner_id": self.owner_id, "generation": self.generation,
            "desired_fingerprint": self.desired_fingerprint, "inventory": self.inventory.value,
            "action": self.action.value, "operation": self.operation.value, "hook_id": self.hook_id,
        }


class ManagedWebhookStore:
    """An owner-only, bounded JSON authority set with atomic replacement."""

    _thread_locks: dict[str, threading.RLock] = {}
    _thread_locks_guard = threading.Lock()

    def __init__(self, wake_root: Path):
        self.wake_root = Path(wake_root).resolve()
        self.path = self.wake_root / "github" / "managed-webhooks.json"
        self._lock_path = self.wake_root / "github" / ".managed-webhooks.lock"

    @contextmanager
    def locked(self) -> Iterator[None]:
        key = str(self._lock_path)
        with self._thread_locks_guard:
            lock = self._thread_locks.setdefault(key, threading.RLock())
        with lock:
            handle = None
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                if self.path.parent.is_symlink():
                    raise ValueError("managed webhook store is unavailable")
                os.chmod(self.path.parent, 0o700)
                descriptor = os.open(
                    self._lock_path,
                    os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0),
                    0o600,
                )
                metadata = os.fstat(descriptor)
                if not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.getuid():
                    os.close(descriptor)
                    raise ValueError("managed webhook store is unavailable")
                os.fchmod(descriptor, 0o600)
                handle = os.fdopen(descriptor, "a+", encoding="utf-8")
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
                yield
            except OSError:
                raise ValueError("managed webhook store is unavailable") from None
            finally:
                if handle is not None:
                    try:
                        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
                    finally:
                        handle.close()

    def bindings(self) -> tuple[ManagedWebhookBinding, ...]:
        with self.locked():
            return self._bindings_unlocked()

    def load(self, owner_id: str) -> ManagedWebhookBinding:
        if type(owner_id) is not str or _NAME.fullmatch(owner_id) is None:
            raise ValueError("managed webhook owner is invalid")
        with self.locked():
            return self._load_unlocked(owner_id)

    def save(self, binding: ManagedWebhookBinding, *, expected_generation: int | None = None) -> ManagedWebhookBinding:
        with self.locked():
            return self._save_unlocked(binding, expected_generation=expected_generation)

    def _load_unlocked(self, owner_id: str) -> ManagedWebhookBinding:
        for binding in self._bindings_unlocked():
            if binding.owner_id == owner_id:
                return binding
        raise ValueError("managed webhook binding is not configured for owner")

    def _save_unlocked(self, binding: ManagedWebhookBinding, *, expected_generation: int | None = None) -> ManagedWebhookBinding:
        if type(binding) is not ManagedWebhookBinding:
            raise ValueError("managed webhook binding is invalid")
        if binding.canonical_root != str(self.wake_root) or binding.owner_uid != os.getuid():
            raise ValueError("managed webhook binding ownership is invalid")
        selected = {item.owner_id: item for item in self._bindings_unlocked()}
        prior = selected.get(binding.owner_id)
        if prior is None:
            if expected_generation is not None or binding.generation != 0:
                raise ValueError("managed webhook generation is stale")
            saved = binding
        else:
            if type(expected_generation) is not int or expected_generation != prior.generation:
                raise ValueError("managed webhook generation is stale")
            if (
                binding.owner_id != prior.owner_id or binding.installation_id != prior.installation_id
                or binding.canonical_root != prior.canonical_root or binding.owner_uid != prior.owner_uid
                or binding.provider_host != prior.provider_host or binding.source_instance != prior.source_instance
                or binding.repository != prior.repository or binding.repository_id != prior.repository_id
                or binding.service_id != prior.service_id or binding.executable_id != prior.executable_id
            ):
                raise ValueError("managed webhook ownership is immutable")
            if not _transition_allowed(prior.lifecycle, binding.lifecycle):
                raise ValueError("managed webhook lifecycle transition is invalid")
            saved = replace(binding, generation=prior.generation + 1)
        for other in selected.values():
            if other.owner_id == saved.owner_id:
                continue
            if _bindings_conflict(other, saved):
                raise ValueError("managed webhook binding conflicts with existing ownership")
        selected[saved.owner_id] = saved
        if len(selected) > _MAX_BINDINGS:
            raise ValueError("managed webhook store is full")
        self._write_unlocked(tuple(sorted(selected.values(), key=lambda item: item.owner_id)))
        return saved

    def _bindings_unlocked(self) -> tuple[ManagedWebhookBinding, ...]:
        if self.path.is_symlink():
            raise ValueError("managed webhook store is invalid")
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
            if type(payload) is not dict or set(payload) != {"schema_version", "bindings"}:
                raise ValueError
            rows = payload["bindings"]
            if payload["schema_version"] != 1 or type(rows) is not list or len(rows) > _MAX_BINDINGS:
                raise ValueError
            bindings = tuple(ManagedWebhookBinding.from_dict(row) for row in rows)
            if tuple(item.owner_id for item in bindings) != tuple(sorted(item.owner_id for item in bindings)):
                raise ValueError
            if len({item.owner_id for item in bindings}) != len(bindings):
                raise ValueError
            if any(
                item.canonical_root != str(self.wake_root) or item.owner_uid != os.getuid()
                for item in bindings
            ):
                raise ValueError
            if any(
                _bindings_conflict(left, right)
                for index, left in enumerate(bindings)
                for right in bindings[index + 1:]
            ):
                raise ValueError
            return bindings
        except (OSError, TypeError, ValueError, json.JSONDecodeError):
            raise ValueError("managed webhook store is invalid") from None

    def _write_unlocked(self, bindings: tuple[ManagedWebhookBinding, ...]) -> None:
        temporary: Path | None = None
        try:
            rendered = json.dumps(
                {"schema_version": 1, "bindings": [item.to_dict() for item in bindings]},
                sort_keys=True,
                separators=(",", ":"),
            ) + "\n"
            if len(rendered.encode("utf-8")) > _MAX_FILE_BYTES:
                raise ValueError("managed webhook store is full")
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=self.path.parent, prefix=".managed-webhooks-", delete=False) as handle:
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
            raise ValueError("managed webhook store is unavailable") from None
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)


class ManagedWebhookReconciler:
    """Bounded observe/calculate/intent/write/readback controller.

    A pending or unknown write is never retried here.  Later calls may only
    observe inventory until exact ownership can be proven again.
    """

    def __init__(self, store: ManagedWebhookStore, provider: WebhookProviderManager):
        if type(store) is not ManagedWebhookStore:
            raise ValueError("managed webhook store is invalid")
        self.store = store
        self.provider = provider

    def classify(self, binding: ManagedWebhookBinding, hooks: tuple[ProviderHook, ...]) -> InventoryClass:
        if (
            type(binding) is not ManagedWebhookBinding or type(hooks) is not tuple or len(hooks) > 128
            or any(type(item) is not ProviderHook for item in hooks)
        ):
            raise ValueError("provider hook inventory is invalid")
        if len({item.hook_id for item in hooks}) != len(hooks):
            raise ValueError("provider hook inventory is invalid")
        target_matches = tuple(item for item in hooks if item.targets(binding))
        if binding.provider_hook_id is None:
            return InventoryClass.COLLISION if target_matches else InventoryClass.ABSENT
        bound = next((item for item in hooks if item.hook_id == binding.provider_hook_id), None)
        if bound is None:
            return InventoryClass.MISSING
        if any(item.hook_id != bound.hook_id for item in target_matches):
            return InventoryClass.DUPLICATE
        return InventoryClass.EXACT if bound.matches(binding) else InventoryClass.DRIFTED

    def preview(self, owner_id: str) -> ReconciliationPlan:
        binding = self.store.load(owner_id)
        try:
            hooks = self.provider.list_hooks(repository_id=binding.repository_id)
        except Exception:
            raise ValueError("provider hook inventory is unavailable") from None
        inventory = self.classify(binding, hooks)
        bound = next((item for item in hooks if item.hook_id == binding.provider_hook_id), None)
        if binding.lifecycle in {
            LifecycleState.CREATING, LifecycleState.UPDATING, LifecycleState.UNKNOWN,
            LifecycleState.DISABLED, LifecycleState.DELETED,
        }:
            action, operation = PlanAction.READ_ONLY, OperationKind.OBSERVE
        elif inventory is InventoryClass.ABSENT and binding.provider_hook_id is None:
            action, operation = PlanAction.WRITE, OperationKind.CREATE
        elif inventory is InventoryClass.DRIFTED:
            action, operation = PlanAction.WRITE, OperationKind.UPDATE
        elif inventory is InventoryClass.EXACT:
            action, operation = PlanAction.NOOP, OperationKind.OBSERVE
        else:
            action, operation = PlanAction.READ_ONLY, OperationKind.OBSERVE
        return ReconciliationPlan(
            owner_id=binding.owner_id, generation=binding.generation,
            desired_fingerprint=binding.desired_fingerprint, inventory=inventory,
            action=action, operation=operation, hook_id=bound.hook_id if bound else None,
        )

    def execute(self, plan: ReconciliationPlan) -> OperationReceipt:
        if type(plan) is not ReconciliationPlan:
            raise ValueError("managed webhook reconciliation plan is invalid")
        with self.store.locked():
            from .managed_webhook_cleanup import ManagedWebhookCleanupStore
            cleanup_store = ManagedWebhookCleanupStore(self.store.wake_root)
            with cleanup_store.locked():
                if any(
                    item.intent.owner_id == plan.owner_id
                    for item in cleanup_store._records_unlocked()
                ):
                    raise ValueError("generic webhook reconciliation is blocked while cleanup authority exists")
                binding = self.store._load_unlocked(plan.owner_id)
                if binding.generation != plan.generation or binding.desired_fingerprint != plan.desired_fingerprint:
                    raise ValueError("managed webhook reconciliation plan is stale")
                if plan.action is not PlanAction.WRITE:
                    return self._complete_read_only(binding, plan)
                try:
                    current_hooks = self.provider.list_hooks(repository_id=binding.repository_id)
                except Exception:
                    raise ValueError("provider hook inventory is unavailable") from None
                current_inventory = self.classify(binding, current_hooks)
                current_hook = next(
                    (item for item in current_hooks if item.hook_id == binding.provider_hook_id),
                    None,
                )
                if (
                    current_inventory is not plan.inventory
                    or plan.operation is OperationKind.CREATE and current_inventory is not InventoryClass.ABSENT
                    or plan.operation is OperationKind.UPDATE and current_inventory is not InventoryClass.DRIFTED
                    or plan.hook_id != (current_hook.hook_id if current_hook else None)
                ):
                    raise ValueError("managed webhook reconciliation plan is stale")
                return self._write_once(binding, plan)

    def _complete_read_only(self, binding: ManagedWebhookBinding, plan: ReconciliationPlan) -> OperationReceipt:
        if plan.inventory is InventoryClass.EXACT and plan.hook_id is not None:
            next_state, hook_id, code = LifecycleState.ACTIVE, plan.hook_id, "OBSERVED_EXACT"
        elif plan.inventory in {InventoryClass.DUPLICATE, InventoryClass.COLLISION, InventoryClass.MISSING}:
            next_state, hook_id, code = LifecycleState.UNKNOWN, binding.provider_hook_id, "OWNERSHIP_UNRESOLVED"
        elif binding.lifecycle in {LifecycleState.CREATING, LifecycleState.UPDATING}:
            next_state, hook_id, code = LifecycleState.UNKNOWN, binding.provider_hook_id, "PENDING_WRITE_UNRESOLVED"
        else:
            next_state, hook_id, code = binding.lifecycle, binding.provider_hook_id, "OBSERVED_NO_WRITE"
        receipt = OperationReceipt(
            operation_id=_operation_id(binding, OperationKind.OBSERVE), operation=OperationKind.OBSERVE,
            state=OperationState.SUCCEEDED if next_state is not LifecycleState.UNKNOWN else OperationState.UNKNOWN,
            generation=binding.generation + 1, inventory=plan.inventory, hook_id=hook_id, code=code,
        )
        saved = self.store._save_unlocked(_with_receipt(replace(binding, lifecycle=next_state, provider_hook_id=hook_id), receipt), expected_generation=binding.generation)
        return replace(receipt, generation=saved.generation)

    def _write_once(self, binding: ManagedWebhookBinding, plan: ReconciliationPlan) -> OperationReceipt:
        if plan.operation is OperationKind.CREATE:
            pending = LifecycleState.CREATING
        elif plan.operation is OperationKind.UPDATE and plan.hook_id is not None:
            pending = LifecycleState.UPDATING
        else:
            raise ValueError("managed webhook reconciliation plan is invalid")
        intent = OperationReceipt(
            operation_id=_operation_id(binding, plan.operation), operation=plan.operation, state=OperationState.INTENDED,
            generation=binding.generation + 1, inventory=plan.inventory, hook_id=plan.hook_id, code="INTENT_RECORDED",
        )
        pending_binding = self.store._save_unlocked(_with_receipt(replace(binding, lifecycle=pending), intent), expected_generation=binding.generation)
        returned_hook_id: int | None = None
        try:
            if plan.operation is OperationKind.CREATE:
                result = self.provider.create_hook(pending_binding)
            else:
                result = self.provider.update_hook(hook_id=plan.hook_id, binding=pending_binding)
            if type(result) is not ProviderHook:
                raise RuntimeError("invalid provider write result")
            returned_hook_id = result.hook_id
            if plan.operation is OperationKind.UPDATE and returned_hook_id != plan.hook_id:
                raise RuntimeError("provider update returned another hook")
            observed = self.provider.get_hook(repository_id=pending_binding.repository_id, hook_id=result.hook_id)
            if (
                type(observed) is not ProviderHook
                or observed.hook_id != returned_hook_id
                or not observed.matches(pending_binding)
            ):
                raise RuntimeError("provider readback did not prove desired hook")
        except Exception:
            ambiguous_hook_id = (
                returned_hook_id if plan.operation is OperationKind.CREATE else plan.hook_id
            )
            receipt = OperationReceipt(
                operation_id=intent.operation_id, operation=plan.operation, state=OperationState.UNKNOWN,
                generation=pending_binding.generation + 1, inventory=plan.inventory,
                hook_id=ambiguous_hook_id,
                code="WRITE_OR_READBACK_UNRESOLVED",
            )
            saved = self.store._save_unlocked(
                replace(
                    pending_binding, lifecycle=LifecycleState.UNKNOWN, provider_hook_id=receipt.hook_id,
                    receipts=(pending_binding.receipts + (receipt,))[-_MAX_RECEIPTS:],
                ),
                expected_generation=pending_binding.generation,
            )
            return replace(receipt, generation=saved.generation)
        receipt = OperationReceipt(
            operation_id=intent.operation_id, operation=plan.operation, state=OperationState.SUCCEEDED,
            generation=pending_binding.generation + 1, inventory=InventoryClass.EXACT, hook_id=observed.hook_id,
            code="READBACK_EXACT",
        )
        saved = self.store._save_unlocked(
            replace(
                pending_binding, lifecycle=LifecycleState.ACTIVE, provider_hook_id=observed.hook_id,
                receipts=(pending_binding.receipts + (receipt,))[-_MAX_RECEIPTS:],
            ),
            expected_generation=pending_binding.generation,
        )
        return replace(receipt, generation=saved.generation)


def _valid_binding_values(binding: ManagedWebhookBinding) -> bool:
    return (
        all(type(value) is str and _NAME.fullmatch(value) is not None for value in (
            binding.owner_id, binding.installation_id, binding.source_instance, binding.service_id, binding.executable_id
        ))
        and _valid_canonical_root(binding.canonical_root)
        and type(binding.owner_uid) is int and 0 <= binding.owner_uid < 2**31
        and _valid_provider_host(binding.provider_host)
        and type(binding.repository) is str and _REPOSITORY.fullmatch(binding.repository) is not None
        and type(binding.repository_id) is int and 0 < binding.repository_id < 2**63
        and _valid_callback(binding.callback_url) and _valid_events(binding.events)
        and type(binding.provider_credential_ref) is str and _ENV_REF.fullmatch(binding.provider_credential_ref) is not None
        and type(binding.secret_generation) is int and 1 <= binding.secret_generation < 2**31
        and (
            binding.provider_hook_id is None
            or (type(binding.provider_hook_id) is int and 0 < binding.provider_hook_id < 2**63)
        )
        and isinstance(binding.lifecycle, LifecycleState) and type(binding.generation) is int and 0 <= binding.generation < 2**63
        and (binding.lifecycle is not LifecycleState.ACTIVE or binding.provider_hook_id is not None)
        and type(binding.receipts) is tuple and len(binding.receipts) <= _MAX_RECEIPTS and all(type(item) is OperationReceipt for item in binding.receipts)
        and _has_attributable_receipt(binding)
    )


def _valid_callback(value: object) -> bool:
    if type(value) is not str or not 12 <= len(value) <= 512 or not value.startswith("https://"):
        return False
    if any(character in value for character in ("?", "#", "@", "\n", "\r", " ")):
        return False
    try:
        parsed = urlsplit(value)
        return parsed.scheme == "https" and bool(parsed.netloc) and bool(parsed.hostname) and bool(parsed.path)
    except ValueError:
        return False


def _valid_provider_callback(value: object) -> bool:
    if type(value) is not str or not 11 <= len(value) <= 2_048:
        return False
    if any(character in value for character in ("#", "@", "\n", "\r", " ")):
        return False
    try:
        parsed = urlsplit(value)
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc) and bool(parsed.hostname) and bool(parsed.path)
    except ValueError:
        return False


def _valid_canonical_root(value: object) -> bool:
    if type(value) is not str or not 1 < len(value) <= 512 or "\x00" in value:
        return False
    try:
        path = Path(value)
        return path.is_absolute() and str(path.resolve()) == value and value != "/"
    except (OSError, ValueError):
        return False


def _valid_provider_host(value: object) -> bool:
    if type(value) is not str or not 1 <= len(value) <= 253 or value.lower() != value:
        return False
    return re.fullmatch(r"[a-z0-9](?:[a-z0-9.-]{0,251}[a-z0-9])?", value) is not None and ".." not in value


def _valid_events(events: object) -> bool:
    return type(events) is tuple and 1 <= len(events) <= 8 and tuple(sorted(events)) == events and len(set(events)) == len(events) and all(type(item) is str and _NAME.fullmatch(item) is not None for item in events)


def _valid_provider_events(events: object) -> bool:
    return (
        type(events) is tuple and 1 <= len(events) <= 128
        and tuple(sorted(events)) == events and len(set(events)) == len(events)
        and all(type(item) is str and (item == "*" or _NAME.fullmatch(item) is not None) for item in events)
    )


def _has_attributable_receipt(binding: ManagedWebhookBinding) -> bool:
    if binding.provider_hook_id is None:
        return True
    return any(
        receipt.hook_id == binding.provider_hook_id
        and receipt.operation in {OperationKind.CREATE, OperationKind.UPDATE}
        and receipt.state in {OperationState.SUCCEEDED, OperationState.UNKNOWN}
        for receipt in binding.receipts
    )


def _bindings_conflict(left: ManagedWebhookBinding, right: ManagedWebhookBinding) -> bool:
    return (
        left.installation_id == right.installation_id
        or left.source_instance == right.source_instance
        or (
            left.provider_host == right.provider_host
            and left.repository_id == right.repository_id
            and left.callback_url == right.callback_url
        )
        or (
            left.provider_hook_id is not None
            and right.provider_hook_id is not None
            and left.provider_host == right.provider_host
            and left.repository_id == right.repository_id
            and left.provider_hook_id == right.provider_hook_id
        )
    )


def _fingerprint(binding: ManagedWebhookBinding) -> str:
    desired = {
        "owner_id": binding.owner_id, "installation_id": binding.installation_id,
        "canonical_root": binding.canonical_root, "owner_uid": binding.owner_uid,
        "provider_host": binding.provider_host, "source_instance": binding.source_instance,
        "repository": binding.repository, "repository_id": binding.repository_id, "callback_url": binding.callback_url,
        "events": binding.events, "service_id": binding.service_id, "executable_id": binding.executable_id,
        "provider_credential_ref": binding.provider_credential_ref, "secret_generation": binding.secret_generation,
        "content_type": "json", "insecure_ssl": False, "active": True,
    }
    return hashlib.sha256(json.dumps(desired, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _operation_id(binding: ManagedWebhookBinding, operation: OperationKind) -> str:
    return f"op_{binding.generation + 1}_{operation.value.lower()}"


def _with_receipt(binding: ManagedWebhookBinding, receipt: OperationReceipt) -> ManagedWebhookBinding:
    receipts = binding.receipts + (receipt,)
    if len(receipts) > _MAX_RECEIPTS:
        bounded = receipts[-_MAX_RECEIPTS:]
        anchor = next(
            (
                item for item in reversed(receipts)
                if binding.provider_hook_id is not None
                and item.hook_id == binding.provider_hook_id
                and item.operation in {OperationKind.CREATE, OperationKind.UPDATE}
                and item.state in {OperationState.SUCCEEDED, OperationState.UNKNOWN}
            ),
            None,
        )
        if anchor is not None and anchor not in bounded:
            bounded = (anchor,) + bounded[-(_MAX_RECEIPTS - 1):]
        receipts = bounded
    return replace(binding, receipts=receipts)


def _transition_allowed(before: LifecycleState, after: LifecycleState) -> bool:
    return after in {
        LifecycleState.UNMANAGED: {
            LifecycleState.UNMANAGED, LifecycleState.CREATING, LifecycleState.UPDATING,
            LifecycleState.ACTIVE, LifecycleState.DISABLED, LifecycleState.UNKNOWN,
        },
        LifecycleState.CREATING: {LifecycleState.CREATING, LifecycleState.ACTIVE, LifecycleState.UNKNOWN},
        LifecycleState.ACTIVE: {LifecycleState.ACTIVE, LifecycleState.UPDATING, LifecycleState.DISABLED, LifecycleState.UNKNOWN},
        LifecycleState.UPDATING: {LifecycleState.UPDATING, LifecycleState.ACTIVE, LifecycleState.UNKNOWN},
        LifecycleState.UNKNOWN: {LifecycleState.UNKNOWN, LifecycleState.ACTIVE, LifecycleState.DISABLED},
        LifecycleState.DISABLED: {
            LifecycleState.DISABLED, LifecycleState.CREATING,
            LifecycleState.DELETED, LifecycleState.UNKNOWN,
        },
        LifecycleState.DELETED: {LifecycleState.DELETED},
    }[before]


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError
        result[key] = value
    return result
