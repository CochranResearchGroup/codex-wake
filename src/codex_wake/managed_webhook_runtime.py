"""Private process attestation for managed webhook secret generations.

The public rotation store retains only the sanitized ``RuntimeProof``.  This
module owns the private, owner-only evidence needed to bind that projection to
one Linux boot, PID, process start identity, service, source, root, binding
revision, and already-bound listener socket.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import stat
import tempfile

from .managed_webhook_rotation import PendingEffect, RotationPhase, RotationRecord, RuntimeProof
from .managed_webhooks import ManagedWebhookBinding
from .webhook_lifecycle import (
    WebhookListenerConfig, WebhookServiceConfig, linux_service_bind_probe, webhook_service_name,
)


_BOOT_ID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
_MAX_BYTES = 16_384


@dataclass(frozen=True, slots=True)
class RuntimeAttestation:
    canonical_root: str
    owner_uid: int
    owner_id: str
    source_instance: str
    service_id: str
    binding_revision: int
    loaded_generations: tuple[int, ...]
    process_id: int
    boot_id: str
    process_start_ticks: int

    def __post_init__(self) -> None:
        if (
            type(self.canonical_root) is not str or not self.canonical_root.startswith("/")
            or type(self.owner_uid) is not int or self.owner_uid < 0
            or type(self.owner_id) is not str or not self.owner_id
            or type(self.source_instance) is not str or not self.source_instance
            or type(self.service_id) is not str or not self.service_id
            or type(self.binding_revision) is not int or self.binding_revision < 0
            or type(self.loaded_generations) is not tuple or not self.loaded_generations
            or len(self.loaded_generations) > 2 or len(set(self.loaded_generations)) != len(self.loaded_generations)
            or not all(type(value) is int and 1 <= value < 2**31 for value in self.loaded_generations)
            or type(self.process_id) is not int or self.process_id <= 0
            or type(self.boot_id) is not str or _BOOT_ID.fullmatch(self.boot_id) is None
            or type(self.process_start_ticks) is not int or self.process_start_ticks < 0
        ):
            raise ValueError("managed webhook runtime attestation is invalid")

    def to_dict(self) -> dict[str, object]:
        return {
            "canonical_root": self.canonical_root,
            "owner_uid": self.owner_uid,
            "owner_id": self.owner_id,
            "source_instance": self.source_instance,
            "service_id": self.service_id,
            "binding_revision": self.binding_revision,
            "loaded_generations": list(self.loaded_generations),
            "process_id": self.process_id,
            "boot_id": self.boot_id,
            "process_start_ticks": self.process_start_ticks,
        }

    @classmethod
    def from_dict(cls, value: object) -> "RuntimeAttestation":
        fields = {
            "canonical_root", "owner_uid", "owner_id", "source_instance", "service_id",
            "binding_revision", "loaded_generations", "process_id", "boot_id", "process_start_ticks",
        }
        if type(value) is not dict or set(value) != fields or type(value["loaded_generations"]) is not list:
            raise ValueError("managed webhook runtime attestation is invalid")
        try:
            return cls(**{
                **{key: value[key] for key in fields - {"loaded_generations"}},
                "loaded_generations": tuple(value["loaded_generations"]),
            })
        except (TypeError, ValueError):
            raise ValueError("managed webhook runtime attestation is invalid") from None


def runtime_attestation_path(wake_root: Path, source_instance: str) -> Path:
    if not source_instance or "/" in source_instance or "\\" in source_instance or source_instance in {".", ".."}:
        raise ValueError("managed webhook runtime source is invalid")
    return Path(wake_root).resolve() / "github" / f"webhook-runtime-{source_instance}.json"


def write_runtime_attestation(
    *, wake_root: Path, listener: WebhookListenerConfig, binding: ManagedWebhookBinding,
    rotation: RotationRecord, process_id: int | None = None, proc_root: Path = Path("/proc"),
) -> RuntimeAttestation:
    """Persist private evidence after the caller has bound the listener socket."""
    root = Path(wake_root).resolve()
    generations = _listener_generations(listener)
    _validate_authority(root, listener, binding, rotation, generations)
    pid = os.getpid() if process_id is None else process_id
    attestation = RuntimeAttestation(
        canonical_root=str(root), owner_uid=os.getuid(), owner_id=rotation.owner_id,
        source_instance=listener.source_instance, service_id=rotation.service_id,
        binding_revision=rotation.binding_revision, loaded_generations=generations,
        process_id=pid, boot_id=_read_boot_id(proc_root),
        process_start_ticks=_read_process_start_ticks(proc_root, pid),
    )
    path = runtime_attestation_path(root, listener.source_instance)
    _atomic_write(path, {"schema_version": 1, "attestation": attestation.to_dict()})
    return attestation


def verify_runtime_attestation(
    *, config: WebhookServiceConfig, listener: WebhookListenerConfig,
    binding: ManagedWebhookBinding, rotation: RotationRecord, runner=None,
    proc_root: Path = Path("/proc"), bind_probe=None,
) -> RuntimeProof:
    """Verify live systemd, procfs, and socket ownership before projecting proof."""
    root = config.wake_root.resolve()
    generations = _listener_generations(listener)
    _validate_authority(root, listener, binding, rotation, generations)
    if config.name != rotation.service_id or config.source_instance != listener.source_instance:
        raise ValueError("managed webhook runtime service is invalid")
    attestation = _read_attestation(runtime_attestation_path(root, listener.source_instance))
    expected = {
        "canonical_root": str(root), "owner_uid": os.getuid(), "owner_id": rotation.owner_id,
        "source_instance": listener.source_instance, "service_id": rotation.service_id,
        "binding_revision": rotation.binding_revision, "loaded_generations": generations,
    }
    if any(getattr(attestation, key) != value for key, value in expected.items()):
        raise ValueError("managed webhook runtime attestation does not match authority")
    main_pid = _main_pid(config, runner)
    if main_pid != attestation.process_id:
        raise ValueError("managed webhook runtime process is unproven")
    if (
        _read_boot_id(proc_root) != attestation.boot_id
        or _read_process_start_ticks(proc_root, main_pid) != attestation.process_start_ticks
    ):
        raise ValueError("managed webhook runtime process is stale")
    probe = bind_probe or (lambda: linux_service_bind_probe(config, runner, proc_root=proc_root))
    if not probe():
        raise ValueError("managed webhook runtime bind ownership is unproven")
    ticks_per_second = os.sysconf("SC_CLK_TCK")
    if type(ticks_per_second) is not int or ticks_per_second <= 0:
        raise ValueError("managed webhook runtime clock is unavailable")
    started_at = _read_boot_time(proc_root) + attestation.process_start_ticks // ticks_per_second
    return RuntimeProof(
        process_id=main_pid, process_started_at=started_at,
        authority_revision=rotation.binding_revision, loaded_generations=generations,
        evidence_locator="runtime-attestation",
    )


def _listener_generations(listener: WebhookListenerConfig) -> tuple[int, ...]:
    if listener.previous_generation is not None:
        return (listener.previous_generation, listener.current_generation)
    return (listener.current_generation,)


def _validate_authority(
    root: Path, listener: WebhookListenerConfig, binding: ManagedWebhookBinding,
    rotation: RotationRecord, generations: tuple[int, ...],
) -> None:
    dual = (
        listener.current_generation == rotation.target_generation
        and listener.previous_generation == rotation.previous_generation
        and generations == (rotation.previous_generation, rotation.target_generation)
    )
    previous_only = (
        listener.current_generation == rotation.previous_generation
        and listener.previous_generation is None
        and generations == (rotation.previous_generation,)
    )
    target_only = (
        listener.current_generation == rotation.target_generation
        and listener.previous_generation is None
        and generations == (rotation.target_generation,)
    )
    shape_allowed = (
        previous_only and (
            rotation.phase is RotationPhase.PREPARED or rotation.phase is RotationPhase.ROLLED_BACK
            or rotation.pending_effect is PendingEffect.ROLLBACK
        )
        or dual and rotation.phase in {
            RotationPhase.PREPARED, RotationPhase.DUAL_READY,
            RotationPhase.PROVIDER_PENDING, RotationPhase.AWAITING_DELIVERY,
        } and rotation.pending_effect is not PendingEffect.RESTART_TARGET_ONLY
        or target_only and (
            rotation.phase in {RotationPhase.AWAITING_DELIVERY, RotationPhase.RETIRING, RotationPhase.COMPLETE}
            or rotation.pending_effect is PendingEffect.RESTART_TARGET_ONLY
        )
    )
    if (
        str(root) == "/" or root.is_symlink()
        or rotation.canonical_root != str(root) or binding.canonical_root != str(root)
        or rotation.owner_uid != os.getuid() or binding.owner_uid != os.getuid()
        or rotation.owner_id != binding.owner_id
        or rotation.source_instance != listener.source_instance
        or binding.source_instance != listener.source_instance
        or rotation.service_id != webhook_service_name(listener.source_instance)
        or binding.service_id != rotation.service_id
        or rotation.binding_revision != binding.generation
        or not shape_allowed
    ):
        raise ValueError("managed webhook runtime authority is invalid")


def _main_pid(config: WebhookServiceConfig, runner) -> int:
    try:
        from .service import systemctl
        value = systemctl(["show", config.name, "--property=MainPID", "--value"], runner, check=False).stdout.strip()
        if not value.isdigit() or int(value) <= 0:
            raise ValueError
        return int(value)
    except Exception:
        raise ValueError("managed webhook runtime process is unproven") from None


def _read_boot_id(proc_root: Path) -> str:
    try:
        value = (proc_root / "sys" / "kernel" / "random" / "boot_id").read_text(encoding="ascii").strip()
        if _BOOT_ID.fullmatch(value) is None:
            raise ValueError
        return value
    except (OSError, UnicodeError, ValueError):
        raise ValueError("managed webhook runtime boot identity is unavailable") from None


def _read_process_start_ticks(proc_root: Path, process_id: int) -> int:
    try:
        value = (proc_root / str(process_id) / "stat").read_text(encoding="ascii")
        tail = value[value.rindex(")") + 2:].split()
        start_ticks = int(tail[19])
        if start_ticks < 0:
            raise ValueError
        return start_ticks
    except (OSError, UnicodeError, ValueError, IndexError):
        raise ValueError("managed webhook runtime process identity is unavailable") from None


def _read_boot_time(proc_root: Path) -> int:
    try:
        matches = [line.split() for line in (proc_root / "stat").read_text(encoding="ascii").splitlines()
                   if line.startswith("btime ")]
        if len(matches) != 1 or len(matches[0]) != 2:
            raise ValueError
        value = int(matches[0][1])
        if value < 0:
            raise ValueError
        return value
    except (OSError, UnicodeError, ValueError):
        raise ValueError("managed webhook runtime clock is unavailable") from None


def _read_attestation(path: Path) -> RuntimeAttestation:
    try:
        metadata = path.lstat()
        if (
            not stat.S_ISREG(metadata.st_mode) or path.is_symlink() or metadata.st_uid != os.getuid()
            or stat.S_IMODE(metadata.st_mode) & 0o077 or metadata.st_size > _MAX_BYTES
        ):
            raise ValueError
        payload = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_object)
        if type(payload) is not dict or set(payload) != {"schema_version", "attestation"} or payload["schema_version"] != 1:
            raise ValueError
        return RuntimeAttestation.from_dict(payload["attestation"])
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError):
        raise ValueError("managed webhook runtime attestation is invalid") from None


def _atomic_write(path: Path, payload: dict[str, object]) -> None:
    temporary: Path | None = None
    try:
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        metadata = path.parent.lstat()
        if path.parent.is_symlink() or not stat.S_ISDIR(metadata.st_mode) or metadata.st_uid != os.getuid():
            raise ValueError
        os.chmod(path.parent, 0o700)
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, prefix=".runtime-", delete=False) as handle:
            temporary = Path(handle.name)
            os.chmod(temporary, 0o600)
            json.dump(payload, handle, sort_keys=True, separators=(",", ":"))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        os.chmod(path, 0o600)
    except OSError:
        raise ValueError("managed webhook runtime attestation is unavailable") from None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError
        result[key] = value
    return result
