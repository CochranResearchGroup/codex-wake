"""Durable, explicitly armed cleanup for one managed GitHub webhook."""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, replace
from enum import Enum
import fcntl
import json
import os
from pathlib import Path
import stat
import tempfile
import threading
from typing import Iterator, Protocol

from .github_source_config import GitHubSourceStore
from .managed_webhook_health import (
    CleanupAction, CleanupEligibility, CleanupHistory, CleanupHistoryEvent,
    CleanupHistoryPhase, CleanupIntent, CleanupPlan, CleanupTombstone,
    CleanupTombstoneState, ProviderObjectHealth,
)
from .managed_webhook_rotation import ManagedWebhookRotationStore, RotationPhase
from .managed_webhooks import (
    LifecycleState, ManagedWebhookBinding, ManagedWebhookStore, ProviderHook,
)
from .webhook_lifecycle import (
    WebhookListenerConfig, WebhookListenerStore, WebhookServiceConfig,
    webhook_service_name,
)


class LocalCleanupState(str, Enum):
    OWNED_ACTIVE = "OWNED_ACTIVE"
    PROVEN_ABSENT = "PROVEN_ABSENT"
    UNKNOWN = "UNKNOWN"


class CleanupPhase(str, Enum):
    PREPARED = "PREPARED"
    PROVIDER_PENDING = "PROVIDER_PENDING"
    PROVIDER_DISABLED = "PROVIDER_DISABLED"
    LOCAL_PENDING = "LOCAL_PENDING"
    DISABLED_PROVEN = "DISABLED_PROVEN"
    DELETE_PENDING = "DELETE_PENDING"
    DELETED_PROVEN = "DELETED_PROVEN"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class CleanupRecord:
    canonical_root: str
    owner_uid: int
    source_instance: str
    revision: int
    phase: CleanupPhase
    intent: CleanupIntent
    history: CleanupHistory
    resulting_binding_generation: int | None = None
    disabled_tombstone: CleanupTombstone | None = None
    tombstone: CleanupTombstone | None = None

    def __post_init__(self) -> None:
        if (
            type(self.canonical_root) is not str or not self.canonical_root.startswith("/")
            or type(self.owner_uid) is not int or self.owner_uid < 0
            or type(self.source_instance) is not str or not self.source_instance
            or type(self.revision) is not int or self.revision < 0
            or not isinstance(self.phase, CleanupPhase)
            or type(self.intent) is not CleanupIntent
            or type(self.history) is not CleanupHistory
            or self.history.owner_id != self.intent.owner_id
            or self.history.repository_id != self.intent.repository_id
            or self.history.hook_id != self.intent.hook_id
            or self.history.service_id != self.intent.service_id
            or self.history.generation != self.intent.generation
            or self.history.desired_fingerprint != self.intent.desired_fingerprint
            or self.resulting_binding_generation is not None
            and (type(self.resulting_binding_generation) is not int or self.resulting_binding_generation < 0)
            or self.tombstone is not None and self.tombstone.intent_id != self.intent.intent_id
            or self.disabled_tombstone is not None
            and (
                self.disabled_tombstone.action is not CleanupAction.DISABLE
                or self.disabled_tombstone.state is not CleanupTombstoneState.DISABLED_PROVEN
            )
            or self.phase in {
                CleanupPhase.PREPARED, CleanupPhase.PROVIDER_PENDING,
                CleanupPhase.PROVIDER_DISABLED, CleanupPhase.LOCAL_PENDING,
            }
            and (
                self.intent.action is not CleanupAction.DISABLE
                or self.resulting_binding_generation is not None
                or self.disabled_tombstone is not None
                or self.tombstone is not None
            )
            or self.phase is CleanupPhase.DISABLED_PROVEN
            and (
                self.intent.action is not CleanupAction.DISABLE
                or self.tombstone is None
                or self.tombstone.state is not CleanupTombstoneState.DISABLED_PROVEN
                or self.disabled_tombstone != self.tombstone
                or self.resulting_binding_generation is None
            )
            or self.phase is CleanupPhase.DELETE_PENDING
            and (
                self.intent.action is not CleanupAction.DELETE
                or self.resulting_binding_generation is None
                or self.disabled_tombstone is None
                or self.tombstone is not None
            )
            or self.phase is CleanupPhase.DELETED_PROVEN
            and (
                self.intent.action is not CleanupAction.DELETE
                or self.tombstone is None
                or self.tombstone.state is not CleanupTombstoneState.DELETED_PROVEN
                or self.disabled_tombstone is None
                or self.resulting_binding_generation is None
            )
            or self.phase is CleanupPhase.UNKNOWN
            and (
                self.tombstone is None
                or self.tombstone.state is not CleanupTombstoneState.UNKNOWN
            )
        ):
            raise ValueError("managed webhook cleanup record is invalid")

    def to_dict(self) -> dict[str, object]:
        return {
            "canonical_root": self.canonical_root,
            "owner_uid": self.owner_uid,
            "source_instance": self.source_instance,
            "revision": self.revision,
            "phase": self.phase.value,
            "intent": self.intent.to_dict(),
            "history": self.history.to_dict(),
            "resulting_binding_generation": self.resulting_binding_generation,
            "disabled_tombstone": (
                self.disabled_tombstone.to_dict() if self.disabled_tombstone else None
            ),
            "tombstone": self.tombstone.to_dict() if self.tombstone else None,
        }

    @classmethod
    def from_dict(cls, value: object) -> "CleanupRecord":
        fields = {
            "canonical_root", "owner_uid", "source_instance", "revision", "phase",
            "intent", "history", "resulting_binding_generation",
            "disabled_tombstone", "tombstone",
        }
        if type(value) is not dict or set(value) != fields:
            raise ValueError("managed webhook cleanup record is invalid")
        try:
            return cls(
                canonical_root=value["canonical_root"], owner_uid=value["owner_uid"],
                source_instance=value["source_instance"], revision=value["revision"],
                phase=CleanupPhase(value["phase"]),
                intent=CleanupIntent.from_dict(value["intent"]),
                history=CleanupHistory.from_dict(value["history"]),
                resulting_binding_generation=value["resulting_binding_generation"],
                disabled_tombstone=(
                    None if value["disabled_tombstone"] is None
                    else CleanupTombstone.from_dict(value["disabled_tombstone"])
                ),
                tombstone=(
                    None if value["tombstone"] is None
                    else CleanupTombstone.from_dict(value["tombstone"])
                ),
            )
        except (TypeError, ValueError):
            raise ValueError("managed webhook cleanup record is invalid") from None


class ManagedWebhookCleanupStore:
    """Owner-only durable cleanup authority and tombstone store."""

    _thread_locks: dict[str, threading.RLock] = {}
    _thread_locks_guard = threading.Lock()

    def __init__(self, wake_root: Path):
        supplied = Path(wake_root)
        if not supplied.is_absolute() or supplied.is_symlink() or str(supplied.resolve()) == "/":
            raise ValueError("managed webhook cleanup root is invalid")
        self.wake_root = supplied.resolve()
        self.path = self.wake_root / "github" / "managed-webhook-cleanups.json"
        self._lock_path = self.wake_root / "github" / ".managed-webhook-cleanups.lock"

    @contextmanager
    def locked(self) -> Iterator[None]:
        key = str(self._lock_path)
        with self._thread_locks_guard:
            lock = self._thread_locks.setdefault(key, threading.RLock())
        with lock:
            handle = None
            try:
                self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                metadata = self.path.parent.lstat()
                if (
                    self.path.parent.is_symlink() or not stat.S_ISDIR(metadata.st_mode)
                    or metadata.st_uid != os.getuid()
                ):
                    raise ValueError("managed webhook cleanup store is unavailable")
                os.chmod(self.path.parent, 0o700)
                descriptor = os.open(
                    self._lock_path,
                    os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600,
                )
                lock_metadata = os.fstat(descriptor)
                if not stat.S_ISREG(lock_metadata.st_mode) or lock_metadata.st_uid != os.getuid():
                    os.close(descriptor)
                    raise ValueError("managed webhook cleanup store is unavailable")
                os.fchmod(descriptor, 0o600)
                handle = os.fdopen(descriptor, "a+", encoding="utf-8")
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
                yield
            except OSError:
                raise ValueError("managed webhook cleanup store is unavailable") from None
            finally:
                if handle is not None:
                    try:
                        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
                    finally:
                        handle.close()

    def records(self) -> tuple[CleanupRecord, ...]:
        with self.locked():
            return self._records_unlocked()

    def load(self, owner_id: str) -> CleanupRecord:
        with self.locked():
            return self._load_unlocked(owner_id)

    def _load_unlocked(self, owner_id: str) -> CleanupRecord:
        selected = [item for item in self._records_unlocked() if item.intent.owner_id == owner_id]
        if len(selected) != 1:
            raise ValueError("managed webhook cleanup is not configured for owner")
        return selected[0]

    def _save_unlocked(
        self, record: CleanupRecord, *, expected_revision: int | None,
    ) -> CleanupRecord:
        if type(record) is not CleanupRecord:
            raise ValueError("managed webhook cleanup record is invalid")
        if record.canonical_root != str(self.wake_root) or record.owner_uid != os.getuid():
            raise ValueError("managed webhook cleanup ownership is invalid")
        selected = {item.intent.owner_id: item for item in self._records_unlocked()}
        prior = selected.get(record.intent.owner_id)
        if prior is None:
            if (
                expected_revision is not None or record.revision != 0
                or record.phase is not CleanupPhase.PREPARED
            ):
                raise ValueError("managed webhook cleanup revision is stale")
            saved = record
        else:
            if expected_revision != prior.revision:
                raise ValueError("managed webhook cleanup revision is stale")
            successor = _delete_successor(prior, record)
            if (
                record.canonical_root != prior.canonical_root
                or record.owner_uid != prior.owner_uid
                or record.source_instance != prior.source_instance
                or record.intent != prior.intent and not successor
            ):
                raise ValueError("managed webhook cleanup ownership is immutable")
            if not successor and record.phase not in _PHASE_SUCCESSORS[prior.phase]:
                raise ValueError("managed webhook cleanup transition is invalid")
            saved = replace(record, revision=prior.revision + 1)
        selected[saved.intent.owner_id] = saved
        if len(selected) > 32:
            raise ValueError("managed webhook cleanup store is full")
        self._write_unlocked(tuple(sorted(selected.values(), key=lambda item: item.intent.owner_id)))
        return saved

    def _records_unlocked(self) -> tuple[CleanupRecord, ...]:
        if self.path.is_symlink():
            raise ValueError("managed webhook cleanup store is invalid")
        if not self.path.exists():
            return ()
        try:
            metadata = self.path.stat()
            if (
                not self.path.is_file() or self.path.is_symlink() or metadata.st_uid != os.getuid()
                or stat.S_IMODE(metadata.st_mode) & 0o077 or metadata.st_size > 262_144
            ):
                raise ValueError
            payload = json.loads(self.path.read_text(encoding="utf-8"), object_pairs_hook=_unique_object)
            if type(payload) is not dict or set(payload) != {"schema_version", "records"}:
                raise ValueError
            rows = payload["records"]
            if payload["schema_version"] != 1 or type(rows) is not list or len(rows) > 32:
                raise ValueError
            records = tuple(CleanupRecord.from_dict(item) for item in rows)
            if tuple(item.intent.owner_id for item in records) != tuple(sorted(item.intent.owner_id for item in records)):
                raise ValueError
            if len({item.intent.owner_id for item in records}) != len(records):
                raise ValueError
            if any(item.canonical_root != str(self.wake_root) or item.owner_uid != os.getuid() for item in records):
                raise ValueError
            return records
        except (OSError, TypeError, ValueError, json.JSONDecodeError):
            raise ValueError("managed webhook cleanup store is invalid") from None

    def _write_unlocked(self, records: tuple[CleanupRecord, ...]) -> None:
        temporary: Path | None = None
        try:
            rendered = json.dumps(
                {"schema_version": 1, "records": [item.to_dict() for item in records]},
                sort_keys=True, separators=(",", ":"),
            ) + "\n"
            if len(rendered.encode("utf-8")) > 262_144:
                raise ValueError("managed webhook cleanup store is full")
            with tempfile.NamedTemporaryFile(
                "w", encoding="utf-8", dir=self.path.parent,
                prefix=".managed-webhook-cleanups-", delete=False,
            ) as handle:
                temporary = Path(handle.name)
                os.chmod(temporary, 0o600)
                handle.write(rendered)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.path)
            os.chmod(self.path, 0o600)
        except OSError:
            raise ValueError("managed webhook cleanup store is unavailable") from None
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)


class CleanupProvider(Protocol):
    def list_hooks(self, *, repository_id: int) -> tuple[ProviderHook, ...]: ...

    def disable_hook(self, *, repository_id: int, hook_id: int) -> ProviderHook: ...

    def get_hook(self, *, repository_id: int, hook_id: int) -> ProviderHook | None: ...

    def delete_hook(self, *, repository_id: int, hook_id: int) -> None: ...


class LocalCleanupAdapter(Protocol):
    def observe(
        self, *, listener: WebhookListenerConfig, service_id: str,
    ) -> LocalCleanupState: ...

    def disable_and_prove_absent(
        self, *, listener: WebhookListenerConfig, service_id: str,
    ) -> LocalCleanupState: ...

    def delete_and_prove_absent(
        self, *, listener: WebhookListenerConfig, service_id: str,
    ) -> LocalCleanupState: ...


class SystemdCleanupAdapter:
    """Exact user-unit and Linux process/socket cleanup adapter."""

    def __init__(
        self, wake_root: Path, *, runner=None, proc_root: Path = Path("/proc"),
        cgroup_root: Path = Path("/sys/fs/cgroup"), unit_dir: Path | None = None,
    ) -> None:
        self.wake_root = Path(wake_root).resolve()
        self.runner = runner
        self.proc_root = Path(proc_root)
        self.cgroup_root = Path(cgroup_root)
        self.unit_dir = unit_dir

    def _config(
        self, listener: WebhookListenerConfig, service_id: str,
    ) -> WebhookServiceConfig | None:
        from .webhook_lifecycle import user_state_dir, user_systemd_dir
        if webhook_service_name(listener.source_instance) != service_id:
            return None
        unit_base = (self.unit_dir or user_systemd_dir()).expanduser()
        state_base = user_state_dir()
        return WebhookServiceConfig(
            name=service_id, wake_root=self.wake_root,
            source_instance=listener.source_instance, executable_path=None,
            unit_path=unit_base / service_id,
            log_path=state_base / f"{service_id.removesuffix('.service')}.log",
            source_enabled=listener.enabled,
        )

    def observe(
        self, *, listener: WebhookListenerConfig, service_id: str,
    ) -> LocalCleanupState:
        from .service import systemctl
        from .webhook_lifecycle import (
            _unit_is_safe, linux_service_bind_probe, webhook_service_status,
        )
        try:
            config = self._config(listener, service_id)
            if config is None:
                return LocalCleanupState.UNKNOWN
            active, enabled = webhook_service_status(config, self.runner)
            if (
                active == "active" and enabled == "enabled"
                and _unit_is_safe(config)
                and linux_service_bind_probe(
                    config, self.runner, proc_root=self.proc_root,
                    listener=listener,
                )
            ):
                return LocalCleanupState.OWNED_ACTIVE
            if active != "inactive" or enabled not in {"disabled", "not-found"}:
                return LocalCleanupState.UNKNOWN
            main_pid = systemctl(
                ["show", config.name, "--property=MainPID", "--value"],
                self.runner, check=False,
            ).stdout.strip()
            control_pid = systemctl(
                ["show", config.name, "--property=ControlPID", "--value"],
                self.runner, check=False,
            ).stdout.strip()
            if main_pid not in {"", "0"} or control_pid not in {"", "0"}:
                return LocalCleanupState.UNKNOWN
            control_group = systemctl(
                ["show", config.name, "--property=ControlGroup", "--value"],
                self.runner, check=False,
            ).stdout.strip()
            if control_group:
                relative = control_group.removeprefix("/")
                procs = self.cgroup_root / relative / "cgroup.procs"
                if not procs.is_file() or procs.read_text(encoding="ascii").strip():
                    return LocalCleanupState.UNKNOWN
            elif not _managed_process_is_proven_absent(
                self.proc_root, self.wake_root, listener.source_instance,
            ):
                return LocalCleanupState.UNKNOWN
            if not _socket_is_proven_absent(self.proc_root, listener.port):
                return LocalCleanupState.UNKNOWN
            return LocalCleanupState.PROVEN_ABSENT
        except Exception:
            return LocalCleanupState.UNKNOWN

    def disable_and_prove_absent(
        self, *, listener: WebhookListenerConfig, service_id: str,
    ) -> LocalCleanupState:
        from .webhook_lifecycle import stop_webhook_service
        config = self._config(listener, service_id)
        if config is None:
            return LocalCleanupState.UNKNOWN
        stop_webhook_service(config, self.runner)
        return self.observe(listener=listener, service_id=service_id)

    def delete_and_prove_absent(
        self, *, listener: WebhookListenerConfig, service_id: str,
    ) -> LocalCleanupState:
        from .webhook_lifecycle import uninstall_webhook_service
        config = self._config(listener, service_id)
        if config is None:
            return LocalCleanupState.UNKNOWN
        uninstall_webhook_service(config, self.runner)
        return self.observe(listener=listener, service_id=service_id)


class ManagedWebhookCleanupController:
    """Join durable ownership and observations behind one small interface."""

    def __init__(
        self, wake_root: Path, *, provider: CleanupProvider,
        local: LocalCleanupAdapter,
    ) -> None:
        supplied = Path(wake_root)
        if not supplied.is_absolute() or supplied.is_symlink() or str(supplied.resolve()) == "/":
            raise ValueError("managed webhook cleanup root is invalid")
        self.wake_root = supplied.resolve()
        self.provider = provider
        self.local = local

    def preview(self, owner_id: str, action: CleanupAction) -> CleanupPlan:
        if not isinstance(action, CleanupAction):
            raise ValueError("managed webhook cleanup action is invalid")
        binding = ManagedWebhookStore(self.wake_root).load(owner_id)
        listener = WebhookListenerStore(self.wake_root).select(binding.source_instance)
        source = GitHubSourceStore(self.wake_root).registry().select(binding.source_instance)
        if (
            binding.canonical_root != str(self.wake_root)
            or binding.owner_uid != os.getuid()
            or binding.provider_host != "api.github.com"
            or binding.repository != source.repository
            or binding.repository_id != source.repository_id
            or binding.service_id != webhook_service_name(binding.source_instance)
            or binding.provider_hook_id is None
            or listener.source_instance != binding.source_instance
        ):
            raise ValueError("managed webhook cleanup authority is invalid")
        rotations = tuple(
            item for item in ManagedWebhookRotationStore(self.wake_root).records()
            if item.owner_id == binding.owner_id
        )
        if len(rotations) > 1 or rotations and rotations[0].phase not in {
            RotationPhase.COMPLETE, RotationPhase.ROLLED_BACK,
        }:
            raise ValueError("managed webhook cleanup is blocked by rotation authority")
        try:
            hooks = self.provider.list_hooks(repository_id=binding.repository_id)
        except Exception:
            raise ValueError("managed webhook cleanup provider inventory is unavailable") from None
        inventory, selected = classify_provider_object(binding, hooks)
        local_state = self.local.observe(
            listener=listener, service_id=binding.service_id,
        )
        cleanup_records = tuple(
            item for item in ManagedWebhookCleanupStore(self.wake_root).records()
            if item.intent.owner_id == binding.owner_id
        )
        disable_eligible = (
            action is CleanupAction.DISABLE
            and not cleanup_records
            and binding.lifecycle is LifecycleState.ACTIVE
            and listener.enabled
            and inventory is ProviderObjectHealth.EXACT
            and selected is not None and selected.active
            and local_state is LocalCleanupState.OWNED_ACTIVE
        )
        prior = cleanup_records[0] if len(cleanup_records) == 1 else None
        delete_eligible = (
            action is CleanupAction.DELETE
            and prior is not None
            and prior.phase is CleanupPhase.DISABLED_PROVEN
            and prior.disabled_tombstone is not None
            and prior.resulting_binding_generation == binding.generation
            and binding.lifecycle is LifecycleState.DISABLED
            and not listener.enabled
            and inventory is ProviderObjectHealth.EXACT
            and selected is not None and not selected.active
            and local_state is LocalCleanupState.PROVEN_ABSENT
        )
        intent = CleanupIntent.create(
            owner_id=binding.owner_id, repository_id=binding.repository_id,
            hook_id=binding.provider_hook_id, service_id=binding.service_id,
            generation=binding.generation,
            desired_fingerprint=binding.desired_fingerprint, action=action,
        )
        return CleanupPlan(
            intent, inventory,
            CleanupEligibility.ELIGIBLE_FOR_EXPLICIT_PLAN
            if disable_eligible or delete_eligible else CleanupEligibility.NOT_AUTHORIZED,
        )

    def execute(self, plan: CleanupPlan) -> CleanupTombstone:
        if (
            type(plan) is not CleanupPlan
            or plan.eligibility is not CleanupEligibility.ELIGIBLE_FOR_EXPLICIT_PLAN
        ):
            raise ValueError("managed webhook cleanup plan is not executable")
        if plan.intent.action is CleanupAction.DELETE:
            return self._execute_delete(plan)
        if plan.intent.action is not CleanupAction.DISABLE:
            raise ValueError("managed webhook cleanup plan is not executable")
        rotation_store = ManagedWebhookRotationStore(self.wake_root)
        binding_store = ManagedWebhookStore(self.wake_root)
        listener_store = WebhookListenerStore(self.wake_root)
        cleanup_store = ManagedWebhookCleanupStore(self.wake_root)
        with rotation_store.locked():
            with binding_store.locked():
                with listener_store.locked():
                    with cleanup_store.locked():
                        if any(
                            item.intent.owner_id == plan.intent.owner_id
                            for item in cleanup_store._records_unlocked()
                        ):
                            raise ValueError("managed webhook cleanup authority already exists")
                        binding = binding_store._load_unlocked(plan.intent.owner_id)
                        listener = next(
                            (item for item in listener_store._listeners_unlocked()
                             if item.source_instance == binding.source_instance),
                            None,
                        )
                        rotations = tuple(
                            item for item in rotation_store._records_unlocked()
                            if item.owner_id == binding.owner_id
                        )
                        if (
                            binding.generation != plan.intent.generation
                            or binding.desired_fingerprint != plan.intent.desired_fingerprint
                            or binding.provider_hook_id != plan.intent.hook_id
                            or binding.lifecycle is not LifecycleState.ACTIVE
                            or listener is None or not listener.enabled
                            or len(rotations) > 1
                            or rotations and rotations[0].phase not in {
                                RotationPhase.COMPLETE, RotationPhase.ROLLED_BACK,
                            }
                        ):
                            raise ValueError("managed webhook cleanup plan is stale")
                        try:
                            hooks = self.provider.list_hooks(repository_id=binding.repository_id)
                        except Exception:
                            raise ValueError("managed webhook cleanup provider inventory is unavailable") from None
                        inventory, selected = classify_provider_object(binding, hooks)
                        if (
                            inventory is not ProviderObjectHealth.EXACT
                            or selected is None or not selected.active
                            or self.local.observe(
                                listener=listener,
                                service_id=binding.service_id,
                            ) is not LocalCleanupState.OWNED_ACTIVE
                        ):
                            raise ValueError("managed webhook cleanup plan is stale")
                        intent = plan.intent
                        history = CleanupHistory(
                            owner_id=intent.owner_id, repository_id=intent.repository_id,
                            hook_id=intent.hook_id, service_id=intent.service_id,
                            generation=intent.generation,
                            desired_fingerprint=intent.desired_fingerprint,
                            entries=(CleanupHistoryEvent.from_intent(
                                0, intent, CleanupHistoryPhase.INTENT_RECORDED,
                            ),),
                        )
                        record = cleanup_store._save_unlocked(CleanupRecord(
                            canonical_root=str(self.wake_root), owner_uid=os.getuid(),
                            source_instance=binding.source_instance, revision=0,
                            phase=CleanupPhase.PREPARED, intent=intent, history=history,
                        ), expected_revision=None)
                        record = cleanup_store._save_unlocked(replace(
                            record, phase=CleanupPhase.PROVIDER_PENDING,
                            history=_append_history(record, CleanupHistoryPhase.PLAN_PREPARED),
                        ), expected_revision=record.revision)
                        try:
                            disabled = self.provider.disable_hook(
                                repository_id=binding.repository_id,
                                hook_id=intent.hook_id,
                            )
                            observed = self.provider.get_hook(
                                repository_id=binding.repository_id,
                                hook_id=intent.hook_id,
                            )
                            if not _disabled_exact(binding, disabled) or not _disabled_exact(binding, observed):
                                raise RuntimeError
                            record = cleanup_store._save_unlocked(replace(
                                record, phase=CleanupPhase.PROVIDER_DISABLED,
                            ), expected_revision=record.revision)
                            record = cleanup_store._save_unlocked(replace(
                                record, phase=CleanupPhase.LOCAL_PENDING,
                            ), expected_revision=record.revision)
                            if self.local.disable_and_prove_absent(
                                listener=listener,
                                service_id=binding.service_id,
                            ) is not LocalCleanupState.PROVEN_ABSENT:
                                raise RuntimeError
                            selected_listeners = {
                                item.source_instance: item
                                for item in listener_store._listeners_unlocked()
                            }
                            if selected_listeners.get(listener.source_instance) != listener:
                                raise RuntimeError
                            selected_listeners[listener.source_instance] = replace(listener, enabled=False)
                            listener_store._write_unlocked(selected_listeners)
                            saved_binding = binding_store._save_unlocked(
                                replace(binding, lifecycle=LifecycleState.DISABLED),
                                expected_generation=binding.generation,
                            )
                            tombstone = CleanupTombstone.from_intent(
                                intent, state=CleanupTombstoneState.DISABLED_PROVEN,
                            )
                            record = cleanup_store._save_unlocked(replace(
                            record, phase=CleanupPhase.DISABLED_PROVEN,
                                resulting_binding_generation=saved_binding.generation,
                                disabled_tombstone=tombstone,
                                tombstone=tombstone,
                                history=_append_history(record, CleanupHistoryPhase.TOMBSTONE_RETAINED),
                            ), expected_revision=record.revision)
                            return record.tombstone  # type: ignore[return-value]
                        except Exception:
                            cleanup_store._save_unlocked(replace(
                                record, phase=CleanupPhase.UNKNOWN,
                                tombstone=CleanupTombstone.from_intent(
                                    intent, state=CleanupTombstoneState.UNKNOWN,
                                ),
                                history=_append_history(record, CleanupHistoryPhase.UNKNOWN),
                            ), expected_revision=record.revision)
                            try:
                                current = binding_store._load_unlocked(binding.owner_id)
                                if current.generation == binding.generation:
                                    binding_store._save_unlocked(
                                        replace(current, lifecycle=LifecycleState.UNKNOWN),
                                        expected_generation=current.generation,
                                    )
                            except ValueError:
                                pass
                            raise ValueError("managed webhook cleanup outcome is unknown") from None

    def _execute_delete(self, plan: CleanupPlan) -> CleanupTombstone:
        rotation_store = ManagedWebhookRotationStore(self.wake_root)
        binding_store = ManagedWebhookStore(self.wake_root)
        listener_store = WebhookListenerStore(self.wake_root)
        cleanup_store = ManagedWebhookCleanupStore(self.wake_root)
        with rotation_store.locked():
            with binding_store.locked():
                with listener_store.locked():
                    with cleanup_store.locked():
                        prior = cleanup_store._load_unlocked(plan.intent.owner_id)
                        binding = binding_store._load_unlocked(plan.intent.owner_id)
                        listener = next(
                            (item for item in listener_store._listeners_unlocked()
                             if item.source_instance == binding.source_instance),
                            None,
                        )
                        rotations = tuple(
                            item for item in rotation_store._records_unlocked()
                            if item.owner_id == binding.owner_id
                        )
                        if (
                            prior.phase is not CleanupPhase.DISABLED_PROVEN
                            or prior.disabled_tombstone is None
                            or prior.resulting_binding_generation != binding.generation
                            or binding.generation != plan.intent.generation
                            or binding.desired_fingerprint != plan.intent.desired_fingerprint
                            or binding.provider_hook_id != plan.intent.hook_id
                            or binding.lifecycle is not LifecycleState.DISABLED
                            or listener is None or listener.enabled
                            or len(rotations) > 1
                            or rotations and rotations[0].phase not in {
                                RotationPhase.COMPLETE, RotationPhase.ROLLED_BACK,
                            }
                        ):
                            raise ValueError("managed webhook cleanup plan is stale")
                        try:
                            hooks = self.provider.list_hooks(repository_id=binding.repository_id)
                        except Exception:
                            raise ValueError("managed webhook cleanup provider inventory is unavailable") from None
                        inventory, selected = classify_provider_object(binding, hooks)
                        if (
                            inventory is not ProviderObjectHealth.EXACT
                            or selected is None or selected.active
                            or self.local.observe(
                                listener=listener,
                                service_id=binding.service_id,
                            ) is not LocalCleanupState.PROVEN_ABSENT
                        ):
                            raise ValueError("managed webhook cleanup plan is stale")
                        intent = plan.intent
                        history = CleanupHistory(
                            owner_id=intent.owner_id, repository_id=intent.repository_id,
                            hook_id=intent.hook_id, service_id=intent.service_id,
                            generation=intent.generation,
                            desired_fingerprint=intent.desired_fingerprint,
                            entries=(CleanupHistoryEvent.from_intent(
                                0, intent, CleanupHistoryPhase.INTENT_RECORDED,
                            ),),
                        )
                        record = cleanup_store._save_unlocked(CleanupRecord(
                            canonical_root=prior.canonical_root, owner_uid=prior.owner_uid,
                            source_instance=prior.source_instance, revision=prior.revision,
                            phase=CleanupPhase.DELETE_PENDING, intent=intent,
                            history=history,
                            resulting_binding_generation=prior.resulting_binding_generation,
                            disabled_tombstone=prior.disabled_tombstone,
                        ), expected_revision=prior.revision)
                        try:
                            self.provider.delete_hook(
                                repository_id=binding.repository_id,
                                hook_id=intent.hook_id,
                            )
                            if self.provider.get_hook(
                                repository_id=binding.repository_id,
                                hook_id=intent.hook_id,
                            ) is not None:
                                raise RuntimeError
                            if self.local.delete_and_prove_absent(
                                listener=listener,
                                service_id=binding.service_id,
                            ) is not LocalCleanupState.PROVEN_ABSENT:
                                raise RuntimeError
                            saved_binding = binding_store._save_unlocked(
                                replace(binding, lifecycle=LifecycleState.DELETED),
                                expected_generation=binding.generation,
                            )
                            tombstone = CleanupTombstone.from_intent(
                                intent, state=CleanupTombstoneState.DELETED_PROVEN,
                            )
                            record = cleanup_store._save_unlocked(replace(
                                record, phase=CleanupPhase.DELETED_PROVEN,
                                resulting_binding_generation=saved_binding.generation,
                                tombstone=tombstone,
                                history=_append_history(record, CleanupHistoryPhase.TOMBSTONE_RETAINED),
                            ), expected_revision=record.revision)
                            return record.tombstone  # type: ignore[return-value]
                        except Exception:
                            cleanup_store._save_unlocked(replace(
                                record, phase=CleanupPhase.UNKNOWN,
                                tombstone=CleanupTombstone.from_intent(
                                    intent, state=CleanupTombstoneState.UNKNOWN,
                                ),
                                history=_append_history(record, CleanupHistoryPhase.UNKNOWN),
                            ), expected_revision=record.revision)
                            try:
                                current = binding_store._load_unlocked(binding.owner_id)
                                if current.generation == binding.generation:
                                    binding_store._save_unlocked(
                                        replace(current, lifecycle=LifecycleState.UNKNOWN),
                                        expected_generation=current.generation,
                                    )
                            except ValueError:
                                pass
                            raise ValueError("managed webhook cleanup outcome is unknown") from None


def classify_provider_object(
    binding: ManagedWebhookBinding, hooks: tuple[ProviderHook, ...],
) -> tuple[ProviderObjectHealth, ProviderHook | None]:
    if (
        type(hooks) is not tuple or len(hooks) > 128
        or any(type(item) is not ProviderHook for item in hooks)
        or len({item.hook_id for item in hooks}) != len(hooks)
    ):
        raise ValueError("managed webhook cleanup provider inventory is invalid")
    target_matches = tuple(item for item in hooks if item.targets(binding))
    selected = next((item for item in hooks if item.hook_id == binding.provider_hook_id), None)
    if selected is None:
        return ProviderObjectHealth.MISSING, None
    if any(item.hook_id != selected.hook_id for item in target_matches):
        return ProviderObjectHealth.DUPLICATE, selected
    exact_shape = (
        selected.callback_url == binding.callback_url
        and selected.events == binding.events
        and selected.content_type == "json"
        and not selected.insecure_ssl
    )
    return (
        ProviderObjectHealth.EXACT if exact_shape else ProviderObjectHealth.DRIFTED,
        selected,
    )


def _disabled_exact(binding: ManagedWebhookBinding, hook: object) -> bool:
    return (
        type(hook) is ProviderHook
        and hook.hook_id == binding.provider_hook_id
        and hook.callback_url == binding.callback_url
        and hook.events == binding.events
        and not hook.active
        and hook.content_type == "json"
        and not hook.insecure_ssl
    )


def _delete_successor(prior: CleanupRecord, record: CleanupRecord) -> bool:
    return (
        prior.phase is CleanupPhase.DISABLED_PROVEN
        and prior.disabled_tombstone is not None
        and prior.resulting_binding_generation == record.intent.generation
        and record.phase is CleanupPhase.DELETE_PENDING
        and record.intent.action is CleanupAction.DELETE
        and record.disabled_tombstone == prior.disabled_tombstone
        and record.intent.owner_id == prior.intent.owner_id
        and record.intent.repository_id == prior.intent.repository_id
        and record.intent.hook_id == prior.intent.hook_id
        and record.intent.service_id == prior.intent.service_id
        and record.intent.desired_fingerprint == prior.intent.desired_fingerprint
    )


_PHASE_SUCCESSORS: dict[CleanupPhase, frozenset[CleanupPhase]] = {
    CleanupPhase.PREPARED: frozenset({CleanupPhase.PROVIDER_PENDING}),
    CleanupPhase.PROVIDER_PENDING: frozenset({
        CleanupPhase.PROVIDER_DISABLED, CleanupPhase.UNKNOWN,
    }),
    CleanupPhase.PROVIDER_DISABLED: frozenset({CleanupPhase.LOCAL_PENDING}),
    CleanupPhase.LOCAL_PENDING: frozenset({
        CleanupPhase.DISABLED_PROVEN, CleanupPhase.UNKNOWN,
    }),
    CleanupPhase.DISABLED_PROVEN: frozenset(),
    CleanupPhase.DELETE_PENDING: frozenset({
        CleanupPhase.DELETED_PROVEN, CleanupPhase.UNKNOWN,
    }),
    CleanupPhase.DELETED_PROVEN: frozenset(),
    CleanupPhase.UNKNOWN: frozenset(),
}


def _append_history(record: CleanupRecord, phase: CleanupHistoryPhase) -> CleanupHistory:
    sequence = (
        record.history.entries[-1].sequence + 1
        if record.history.entries else 0
    )
    entries = record.history.entries + (
        CleanupHistoryEvent.from_intent(sequence, record.intent, phase),
    )
    return replace(record.history, entries=entries[-32:])


def _managed_process_is_proven_absent(
    proc_root: Path, wake_root: Path, source_instance: str,
) -> bool:
    """Prove no process command line identifies the exact managed listener."""
    try:
        for process in proc_root.iterdir():
            if not process.name.isdigit():
                continue
            cmdline = process / "cmdline"
            try:
                raw = cmdline.read_bytes()
            except (FileNotFoundError, ProcessLookupError):
                continue
            except OSError:
                return False
            arguments = tuple(
                item.decode("utf-8") for item in raw.split(b"\0") if item
            )
            if not arguments:
                continue
            process_root = _option_value(arguments, "--wake-root")
            process_source = _option_value(arguments, "--source")
            is_listener = any(
                Path(argument).name == "codex-wake-github-webhook"
                or argument in {
                    "codex_wake.webhook_listener",
                    "codex_wake.webhook_listener:main",
                }
                for argument in arguments
            )
            if process_root is None or process_source is None or not is_listener:
                continue
            if (
                Path(process_root).resolve() == wake_root
                and process_source == source_instance
            ):
                return False
        return True
    except (OSError, UnicodeError, ValueError):
        return False


def _option_value(arguments: tuple[str, ...], option: str) -> str | None:
    for index, argument in enumerate(arguments):
        if argument == option:
            return arguments[index + 1] if index + 1 < len(arguments) else None
        prefix = option + "="
        if argument.startswith(prefix):
            return argument[len(prefix):] or None
    return None


def _socket_is_proven_absent(proc_root: Path, port: int) -> bool:
    """Conservatively reject any IPv4/IPv6 listener using the managed port."""
    try:
        for table in (proc_root / "net" / "tcp", proc_root / "net" / "tcp6"):
            if not table.is_file():
                return False
            for line in table.read_text(encoding="ascii").splitlines()[1:]:
                fields = line.split()
                if len(fields) < 4 or fields[3] != "0A":
                    continue
                local = fields[1].rsplit(":", 1)
                if len(local) != 2:
                    return False
                if int(local[1], 16) == port:
                    return False
        return True
    except (OSError, UnicodeError, ValueError):
        return False


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError
        value[key] = item
    return value
