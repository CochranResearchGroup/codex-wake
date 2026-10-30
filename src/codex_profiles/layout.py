from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import signal
import shutil
import socket
import time

from .config import Settings

DEFAULT_SHARED_DIRECTORIES = (
    "skills",
    "rules",
    "sessions",
    "cache/codex_apps_tools",
)


DEFAULT_PROFILE_DIRECTORIES = (
    "cache",
    "log",
    "memories",
)


@dataclass(slots=True)
class MigrationAction:
    kind: str
    source: Path | None
    destination: Path
    status: str
    detail: str


@dataclass(slots=True)
class ProjectionAction:
    kind: str
    source: Path | None
    destination: Path
    status: str
    detail: str


@dataclass(slots=True)
class ActiveProfileState:
    requested_profile: str
    active_profiles: tuple[str, ...]
    pid_file: Path


@dataclass(slots=True)
class ClosedSession:
    profile: str
    pid: int
    pid_file: Path
    status: str


def ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def ensure_symlink(target: Path, link_path: Path) -> None:
    if link_path.exists() or link_path.is_symlink():
        return
    link_path.parent.mkdir(parents=True, exist_ok=True)
    link_path.symlink_to(target)


def seed_shared_path(source_path: Path, shared_path: Path) -> None:
    if shared_path.exists() or shared_path.is_symlink() or not source_path.exists():
        return
    shared_path.parent.mkdir(parents=True, exist_ok=True)
    if source_path.is_dir():
        shared_path.symlink_to(source_path, target_is_directory=True)
    else:
        shared_path.symlink_to(source_path)


def copy_if_missing(source_path: Path, destination_path: Path) -> None:
    if destination_path.exists() or not source_path.exists():
        return
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    if source_path.is_dir():
        shutil.copytree(source_path, destination_path)
    else:
        destination_path.write_bytes(source_path.read_bytes())


def ensure_shared_directory(shared_path: Path) -> None:
    if shared_path.exists() or shared_path.is_symlink():
        return
    shared_path.mkdir(parents=True, exist_ok=True)


def merge_directory_contents(source_dir: Path, destination_dir: Path) -> None:
    destination_dir.mkdir(parents=True, exist_ok=True)
    for source_path in source_dir.rglob("*"):
        relative_path = source_path.relative_to(source_dir)
        destination_path = destination_dir / relative_path
        if source_path.is_dir():
            destination_path.mkdir(parents=True, exist_ok=True)
            continue
        if destination_path.exists():
            continue
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, destination_path)


def _same_file_contents(first: Path, second: Path) -> bool:
    try:
        return first.read_bytes() == second.read_bytes()
    except OSError:
        return False


def _backup_projection_conflict(settings: Settings, relative_path: str, conflict_path: Path) -> Path:
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    backup_path = settings.shared_root / ".projection-backups" / timestamp / relative_path
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(conflict_path), str(backup_path))
    return backup_path


def _replace_with_symlink(settings: Settings, target_path: Path, link_path: Path, relative_path: str) -> ProjectionAction:
    if link_path.is_symlink():
        if link_path.resolve(strict=False) == target_path.resolve(strict=False):
            return ProjectionAction("link", target_path, link_path, "skip", "projection already points at target")
        link_path.unlink()
    elif link_path.exists():
        if not target_path.exists() and not target_path.is_symlink():
            target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(link_path), str(target_path))
        elif link_path.is_dir() and target_path.is_dir():
            backup_path = _backup_projection_conflict(settings, relative_path, link_path)
            link_path.parent.mkdir(parents=True, exist_ok=True)
            link_path.symlink_to(target_path)
            return ProjectionAction("backup", link_path, backup_path, "applied", "backed up unmanaged projection directory")
        elif link_path.is_file() and target_path.is_file() and _same_file_contents(link_path, target_path):
            link_path.unlink()
        else:
            backup_path = _backup_projection_conflict(settings, relative_path, link_path)
            link_path.parent.mkdir(parents=True, exist_ok=True)
            link_path.symlink_to(target_path)
            return ProjectionAction("backup", link_path, backup_path, "applied", "backed up unmanaged projection conflict")

    link_path.parent.mkdir(parents=True, exist_ok=True)
    if not link_path.exists() and not link_path.is_symlink():
        link_path.symlink_to(target_path)
        return ProjectionAction("link", target_path, link_path, "applied", "project active profile path")
    return ProjectionAction("link", target_path, link_path, "skip", "projection path already exists")


def _copy_materialized_path(source_path: Path, destination_path: Path) -> None:
    if source_path.is_dir():
        shutil.copytree(source_path, destination_path, symlinks=False)
    elif source_path.exists():
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, destination_path)


def _materialize_source_backed_shared_links(settings: Settings) -> None:
    for relative_path in settings.shared_links:
        source_path = settings.source_root / relative_path
        shared_path = settings.shared_root / relative_path
        if not shared_path.is_symlink():
            continue
        if shared_path.resolve(strict=False) != source_path.resolve(strict=False):
            continue
        shared_path.unlink()
        if source_path.exists():
            shared_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source_path), str(shared_path))
        elif _is_default_shared_directory(relative_path):
            ensure_shared_directory(shared_path)


def _is_managed_projection(settings: Settings, link_path: Path) -> bool:
    if not link_path.is_symlink():
        return False
    try:
        return link_path.resolve(strict=False).is_relative_to(settings.state_root.resolve())
    except OSError:
        return False


def adopt_existing_path_as_symlink(shared_path: Path, link_path: Path) -> None:
    if link_path.is_symlink():
        return
    if not link_path.exists():
        ensure_symlink(shared_path, link_path)
        return

    if not shared_path.exists() and not shared_path.is_symlink():
        shared_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(link_path), str(shared_path))
        ensure_symlink(shared_path, link_path)
        return

    if link_path.is_dir():
        destination = shared_path.resolve(strict=False) if shared_path.is_symlink() else shared_path
        merge_directory_contents(link_path, destination)
        shutil.rmtree(link_path)
        ensure_symlink(shared_path, link_path)


def _shared_path_mode(relative_path: str) -> str:
    return "copy" if relative_path.startswith("state_5.sqlite") else "link"


def _is_default_shared_directory(relative_path: str) -> bool:
    return relative_path in DEFAULT_SHARED_DIRECTORIES


def plan_migration(settings: Settings) -> list[MigrationAction]:
    actions: list[MigrationAction] = []

    if settings.state_root == settings.source_root:
        actions.append(
            MigrationAction(
                kind="warning",
                source=settings.source_root,
                destination=settings.state_root,
                status="warning",
                detail="state_root and source_root are the same; migration will seed shared state from the live singleton root",
            )
        )

    actions.append(
        MigrationAction(
            kind="mkdir",
            source=None,
            destination=settings.shared_root,
            status="plan" if not settings.shared_root.exists() else "skip",
            detail="shared root",
        )
    )
    actions.append(
        MigrationAction(
            kind="mkdir",
            source=None,
            destination=settings.shared_root / "log",
            status="plan" if not (settings.shared_root / "log").exists() else "skip",
            detail="shared log directory",
        )
    )

    for relative_path in settings.shared_links:
        source_path = settings.source_root / relative_path
        destination = settings.shared_root / relative_path
        mode = _shared_path_mode(relative_path)
        if not source_path.exists():
            if _is_default_shared_directory(relative_path):
                actions.append(
                    MigrationAction(
                        kind="mkdir",
                        source=None,
                        destination=destination,
                        status="plan" if not destination.exists() else "skip",
                        detail="create shared directory",
                    )
                )
                continue
            actions.append(
                MigrationAction(
                    kind=mode,
                    source=source_path,
                    destination=destination,
                    status="skip",
                    detail="source path does not exist",
                )
            )
            continue
        if destination.exists() or destination.is_symlink():
            actions.append(
                MigrationAction(
                    kind=mode,
                    source=source_path,
                    destination=destination,
                    status="skip",
                    detail="destination already exists",
                )
            )
            continue
        actions.append(
            MigrationAction(
                kind=mode,
                source=source_path,
                destination=destination,
                status="plan",
                detail="copy sqlite index files" if mode == "copy" else "link shared path back to singleton source",
            )
        )

    history_path = settings.shared_root / "history.jsonl"
    if not history_path.exists():
        actions.append(
            MigrationAction(
                kind="touch",
                source=None,
                destination=history_path,
                status="plan",
                detail="create empty history log when not present in source or shared state",
            )
        )

    return actions


def ensure_layout(settings: Settings, profile_name: str) -> Path:
    shared_root = settings.shared_root
    account_root = settings.account_root(profile_name)

    ensure_directory(shared_root)
    ensure_directory(shared_root / "log")
    ensure_directory(account_root)
    for relative_path in DEFAULT_PROFILE_DIRECTORIES:
        ensure_directory(account_root / relative_path)

    for relative_path in settings.shared_links:
        if _shared_path_mode(relative_path) == "link":
            seed_shared_path(settings.source_root / relative_path, shared_root / relative_path)
        if _is_default_shared_directory(relative_path):
            ensure_shared_directory(shared_root / relative_path)

    history_path = shared_root / "history.jsonl"
    if not history_path.exists():
        history_path.touch()

    for relative_path in settings.shared_links:
        adopt_existing_path_as_symlink(shared_root / relative_path, account_root / relative_path)

    return account_root


def project_profile(settings: Settings, profile_name: str) -> list[ProjectionAction]:
    resolved_profile = settings.resolve_profile_name(profile_name)
    account_root = ensure_layout(settings, resolved_profile)
    _materialize_source_backed_shared_links(settings)
    actions: list[ProjectionAction] = []
    for relative_path in settings.projected_links:
        target_path = account_root / relative_path
        if relative_path in DEFAULT_PROFILE_DIRECTORIES:
            ensure_directory(target_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        link_path = settings.source_root / relative_path
        actions.append(_replace_with_symlink(settings, target_path, link_path, relative_path))
    return actions


def unproject_profile(settings: Settings) -> list[ProjectionAction]:
    actions: list[ProjectionAction] = []
    for relative_path in settings.projected_links:
        link_path = settings.source_root / relative_path
        if not link_path.is_symlink():
            actions.append(ProjectionAction("unproject", None, link_path, "skip", "projection path is not a symlink"))
            continue
        if not _is_managed_projection(settings, link_path):
            actions.append(ProjectionAction("unproject", link_path.resolve(strict=False), link_path, "skip", "symlink target is outside managed state root"))
            continue
        target_path = link_path.resolve(strict=False)
        link_path.unlink()
        if target_path.exists():
            _copy_materialized_path(target_path, link_path)
            actions.append(ProjectionAction("unproject", target_path, link_path, "applied", "materialized projected path for stock Codex"))
        else:
            actions.append(ProjectionAction("unproject", target_path, link_path, "applied", "removed dangling managed projection symlink"))
    return actions


def apply_migration(settings: Settings, actions: list[MigrationAction]) -> list[MigrationAction]:
    applied: list[MigrationAction] = []
    for action in actions:
        if action.status != "plan":
            applied.append(action)
            continue
        if action.kind == "mkdir":
            ensure_directory(action.destination)
            applied.append(MigrationAction(action.kind, action.source, action.destination, "applied", action.detail))
            continue
        if action.kind == "touch":
            action.destination.parent.mkdir(parents=True, exist_ok=True)
            action.destination.touch(exist_ok=True)
            applied.append(MigrationAction(action.kind, action.source, action.destination, "applied", action.detail))
            continue
        if action.kind == "copy":
            copy_if_missing(action.source, action.destination)
            applied.append(MigrationAction(action.kind, action.source, action.destination, "applied", action.detail))
            continue
        if action.kind == "link":
            seed_shared_path(action.source, action.destination)
            applied.append(MigrationAction(action.kind, action.source, action.destination, "applied", action.detail))
            continue
        applied.append(action)
    return applied


def profile_snapshot(settings: Settings, profile_name: str) -> dict[str, str]:
    resolved_profile = settings.resolve_profile_name(profile_name)
    account_root = settings.account_root(profile_name)
    shared_root = settings.shared_root
    return {
        "profile": resolved_profile,
        "account_root": str(account_root),
        "shared_root": str(shared_root),
        "exists": "yes" if account_root.exists() else "no",
        "codex_home": str(account_root),
        "lock_file": str(shared_root / ".codex-profiles-active.lock"),
        "active_root": str(shared_root / ".codex-profiles-active"),
    }


def validate_profile(settings: Settings, profile_name: str) -> list[str]:
    issues: list[str] = []
    account_root = settings.account_root(profile_name)
    if not account_root.exists():
        return [f"missing account root: {account_root}"]

    if not settings.shared_root.exists():
        issues.append(f"missing shared root: {settings.shared_root}")

    for relative_path in settings.shared_links:
        shared_path = settings.shared_root / relative_path
        link_path = account_root / relative_path
        if not shared_path.exists() and not shared_path.is_symlink():
            if relative_path.endswith((".sqlite-wal", ".sqlite-shm")):
                if link_path.is_symlink() and link_path.resolve(strict=False) != shared_path.resolve(strict=False):
                    issues.append(
                        f"wrong target: {link_path} -> {link_path.resolve(strict=False)} "
                        f"(expected {shared_path.resolve(strict=False)})"
                    )
                elif link_path.exists() and not link_path.is_symlink():
                    issues.append(f"expected transient sidecar symlink or absence: {link_path}")
                continue
            issues.append(f"missing shared path: {shared_path}")
            continue
        if not link_path.is_symlink():
            issues.append(f"missing symlink: {link_path}")
            continue
        resolved_target = link_path.resolve(strict=False)
        expected_target = shared_path.resolve(strict=False)
        if resolved_target != expected_target:
            issues.append(f"wrong target: {link_path} -> {resolved_target} (expected {expected_target})")

    return issues


class ProfileLock:
    def __init__(self, lock_path: Path, blocking: bool = True) -> None:
        self.lock_path = lock_path
        self.blocking = blocking
        self._file = None

    def __enter__(self) -> "ProfileLock":
        import fcntl

        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        self._file = self.lock_path.open("a+", encoding="utf-8")
        mode = fcntl.LOCK_EX
        if not self.blocking:
            mode |= fcntl.LOCK_NB
        fcntl.flock(self._file.fileno(), mode)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        import fcntl

        fcntl.flock(self._file.fileno(), fcntl.LOCK_UN)
        self._file.close()


class ActiveProfileGuard:
    def __init__(self, settings: Settings, profile_name: str, *, private_runtime: bool = False) -> None:
        self.settings = settings
        self.profile_name = profile_name
        self.lock = ProfileLock(settings.shared_root / ".codex-profiles-active.lock")
        self.active_root = settings.shared_root / ".codex-profiles-active"
        self.pid_file: Path | None = None
        self.private_runtime = private_runtime

    @staticmethod
    def _generation(pid: int) -> dict[str, str]:
        # A retained PID alone cannot identify a process after reuse or reboot.
        stat_text = Path(f"/proc/{pid}/stat").read_text()
        return {"start_ticks": stat_text.rsplit(")", 1)[1].split()[19],
                "boot_id": Path("/proc/sys/kernel/random/boot_id").read_text().strip()}

    def _private_home(self, profile_name: str) -> Path:
        if self.settings.selection_mode != "launcher":
            raise BlockingIOError("concurrent accounts require launcher mode, not legacy projection")
        if set(self.settings.shared_links) - {"config.toml", "skills", "rules"}:
            raise BlockingIOError("concurrent accounts cannot share mutable session or credential state")
        home = self.settings.account_root(profile_name).absolute()
        if not home.is_dir() or home != home.resolve() or home.stat().st_uid != os.getuid():
            raise BlockingIOError("private runtime requires an owned real tenant home")
        mutable = [home / name for name in ("auth.json", "sessions", "history.jsonl", "memories", "cache", "log")]
        mutable.extend(home.glob("*.sqlite*"))
        if any(path.is_symlink() for path in mutable):
            raise BlockingIOError("private runtime cannot use symlinked mutable tenant state")
        return home

    def _private_peers(self, profiles: tuple[str, ...]) -> bool:
        own_home = self._private_home(self.profile_name)
        for profile in profiles:
            home = self._private_home(profile)
            if profile != self.profile_name and home.samefile(own_home):
                return False
            names = {"auth.json", "sessions", "history.jsonl", "memories", "cache", "log"}
            names.update(path.name for path in own_home.glob("*.sqlite*"))
            names.update(path.name for path in home.glob("*.sqlite*"))
            for name in names:
                first, second = own_home / name, home / name
                if profile != self.profile_name and first.exists() and second.exists() and first.samefile(second):
                    raise BlockingIOError("concurrent account isolation found shared mutable state")
            for path in self._profile_pid_files(profile):
                try:
                    row = json.loads(path.read_text())
                    if (row.get("private_runtime") is not True or row.get("home") != str(home)
                            or row.get("generation") != self._generation(int(path.stem))):
                        return False
                except (OSError, ValueError, TypeError):
                    return False
        return True

    def _profile_dir(self, profile_name: str) -> Path:
        return self.active_root / profile_name

    def _pid_file(self, profile_name: str, pid: int | None = None) -> Path:
        effective_pid = os.getpid() if pid is None else pid
        return self._profile_dir(profile_name) / f"{effective_pid}.json"

    def _pid_alive(self, pid: int) -> bool:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        proc_stat = Path(f"/proc/{pid}/stat")
        if proc_stat.exists():
            try:
                stat_parts = proc_stat.read_text(encoding="utf-8").split()
            except OSError:
                return True
            if len(stat_parts) > 2 and stat_parts[2] == "Z":
                return False
        return True

    def _profile_pid_files(self, profile_name: str) -> list[Path]:
        profile_dir = self._profile_dir(profile_name)
        if not profile_dir.exists():
            return []
        return sorted(profile_dir.glob("*.json"))

    def _terminate_pid_group(self, pid: int, sig: signal.Signals) -> None:
        try:
            pgid = os.getpgid(pid)
        except ProcessLookupError:
            raise
        if pgid == os.getpgrp():
            os.kill(pid, sig)
            return
        try:
            os.killpg(pgid, sig)
        except ProcessLookupError:
            raise
        except PermissionError:
            os.kill(pid, sig)

    def _close_live_pid(self, profile_name: str, pid: int, pid_file: Path, timeout_seconds: float = 2.0, unlink_pid_file: bool = True) -> ClosedSession:
        if not self._pid_alive(pid):
            if unlink_pid_file:
                pid_file.unlink(missing_ok=True)
            return ClosedSession(profile=profile_name, pid=pid, pid_file=pid_file, status="removed-stale")

        try:
            self._terminate_pid_group(pid, signal.SIGTERM)
        except ProcessLookupError:
            if unlink_pid_file:
                pid_file.unlink(missing_ok=True)
            return ClosedSession(profile=profile_name, pid=pid, pid_file=pid_file, status="removed-stale")

        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            if not self._pid_alive(pid):
                if unlink_pid_file:
                    pid_file.unlink(missing_ok=True)
                return ClosedSession(profile=profile_name, pid=pid, pid_file=pid_file, status="terminated")
            time.sleep(0.05)

        try:
            self._terminate_pid_group(pid, signal.SIGKILL)
        except ProcessLookupError:
            if unlink_pid_file:
                pid_file.unlink(missing_ok=True)
            return ClosedSession(profile=profile_name, pid=pid, pid_file=pid_file, status="terminated")

        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            if not self._pid_alive(pid):
                if unlink_pid_file:
                    pid_file.unlink(missing_ok=True)
                return ClosedSession(profile=profile_name, pid=pid, pid_file=pid_file, status="killed")
            time.sleep(0.05)

        if unlink_pid_file:
            pid_file.unlink(missing_ok=True)
        return ClosedSession(profile=profile_name, pid=pid, pid_file=pid_file, status="cleared-after-kill-timeout")

    def _close_pid(self, profile_name: str, pid_file: Path, timeout_seconds: float = 2.0) -> ClosedSession:
        try:
            pid = int(pid_file.stem)
        except ValueError:
            pid_file.unlink(missing_ok=True)
            return ClosedSession(profile=profile_name, pid=-1, pid_file=pid_file, status="removed-invalid")

        return self._close_live_pid(profile_name, pid, pid_file, timeout_seconds=timeout_seconds)

    def _ancestor_pids(self) -> set[int]:
        ancestors = {os.getpid()}
        current = os.getpid()
        while True:
            stat_path = Path(f"/proc/{current}/stat")
            try:
                stat_parts = stat_path.read_text(encoding="utf-8").split()
            except OSError:
                return ancestors
            if len(stat_parts) < 4:
                return ancestors
            try:
                parent = int(stat_parts[3])
            except ValueError:
                return ancestors
            if parent <= 1 or parent in ancestors:
                return ancestors
            ancestors.add(parent)
            current = parent

    @staticmethod
    def _is_codex_cmdline(cmdline: list[str]) -> bool:
        if not cmdline:
            return False
        first_name = Path(cmdline[0]).name
        if first_name in {"codex", "codex-code-mode-host"}:
            return True
        for arg in cmdline[1:]:
            arg_name = Path(arg).name
            if arg_name != "codex":
                continue
            if "/@openai/codex" in arg or arg.endswith("/bin/codex"):
                return True
        return False

    def _read_cmdline(self, pid: int) -> list[str]:
        try:
            raw = Path(f"/proc/{pid}/cmdline").read_bytes()
        except OSError:
            return []
        return [part.decode("utf-8", errors="replace") for part in raw.split(b"\0") if part]

    def _stock_codex_group_leaders(self) -> list[int]:
        proc_root = Path("/proc")
        ancestor_pids = self._ancestor_pids()
        group_leaders: dict[int, int] = {}
        for path in proc_root.iterdir():
            if not path.name.isdigit():
                continue
            pid = int(path.name)
            if pid in ancestor_pids:
                continue
            cmdline = self._read_cmdline(pid)
            if not self._is_codex_cmdline(cmdline):
                continue
            try:
                pgid = os.getpgid(pid)
            except ProcessLookupError:
                continue
            if pgid in ancestor_pids:
                continue
            group_leaders.setdefault(pgid, pid)
        return sorted(group_leaders.values())

    def stock_codex_processes(self) -> tuple[int, ...]:
        return tuple(self._stock_codex_group_leaders())

    def codex_processes(self) -> tuple[int, ...]:
        processes: list[int] = []
        for path in Path("/proc").iterdir():
            if path.name.isdigit() and self._is_codex_cmdline(self._read_cmdline(int(path.name))):
                processes.append(int(path.name))
        return tuple(sorted(processes))

    def _cleanup_stale_entries(self) -> None:
        if not self.active_root.exists():
            return
        for profile_dir in list(self.active_root.iterdir()):
            if not profile_dir.is_dir():
                continue
            for pid_file in list(profile_dir.glob("*.json")):
                try:
                    pid = int(pid_file.stem)
                except ValueError:
                    pid_file.unlink(missing_ok=True)
                    continue
                if not self._pid_alive(pid):
                    pid_file.unlink(missing_ok=True)
            try:
                next(profile_dir.iterdir())
            except StopIteration:
                profile_dir.rmdir()

    def active_profiles(self) -> tuple[str, ...]:
        self.active_root.mkdir(parents=True, exist_ok=True)
        with self.lock:
            self._cleanup_stale_entries()
            return tuple(sorted(p.name for p in self.active_root.iterdir() if p.is_dir()))

    def close_profiles(self, profile_names: tuple[str, ...] | list[str]) -> list[ClosedSession]:
        requested = tuple(dict.fromkeys(profile_names))
        if not requested:
            return []
        self.active_root.mkdir(parents=True, exist_ok=True)
        closed: list[ClosedSession] = []
        with self.lock:
            self._cleanup_stale_entries()
            for profile_name in requested:
                for pid_file in self._profile_pid_files(profile_name):
                    closed.append(self._close_pid(profile_name, pid_file))
            self._cleanup_stale_entries()
        return closed

    def close_stock_codex_processes(self) -> list[ClosedSession]:
        closed: list[ClosedSession] = []
        synthetic_root = self.active_root / "stock-codex"
        for pid in self._stock_codex_group_leaders():
            synthetic_pid_file = synthetic_root / f"{pid}.json"
            closed.append(
                self._close_live_pid(
                    "stock-codex",
                    pid,
                    synthetic_pid_file,
                    unlink_pid_file=False,
                )
            )
        return closed

    def acquire(self) -> ActiveProfileState:
        self.active_root.mkdir(parents=True, exist_ok=True)
        with self.lock:
            self._cleanup_stale_entries()
            active_profiles = tuple(sorted(p.name for p in self.active_root.iterdir() if p.is_dir()))
            conflicting = tuple(profile for profile in active_profiles if profile != self.profile_name)
            if self.private_runtime:
                self._private_home(self.profile_name)
                if not self._private_peers(active_profiles):
                    raise BlockingIOError("legacy or unverified client prevents a private runtime launch")
            elif any(json.loads(path.read_text()).get("private_runtime") is True
                     for profile in active_profiles for path in self._profile_pid_files(profile)):
                raise BlockingIOError("legacy launch cannot share state with a private runtime")
            if conflicting and not self.private_runtime:
                raise BlockingIOError(
                    f"shared profile state is already in use by {', '.join(conflicting)}; "
                    "concurrent runs are only allowed within the same profile. "
                    f"To switch now, run 'codex-profiles use {self.settings.denormalize_profile_name(self.profile_name)} "
                    "--close-open-sessions'."
                )

            profile_dir = self._profile_dir(self.profile_name)
            profile_dir.mkdir(parents=True, exist_ok=True)
            self.pid_file = self._pid_file(self.profile_name)
            record = {"pid": os.getpid(), "profile": self.profile_name,
                      "hostname": socket.gethostname(), "private_runtime": self.private_runtime}
            if self.private_runtime:
                record.update(home=str(self._private_home(self.profile_name)), generation=self._generation(os.getpid()))
            self.pid_file.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
            return ActiveProfileState(
                requested_profile=self.profile_name,
                active_profiles=active_profiles,
                pid_file=self.pid_file,
            )

    def release(self) -> None:
        with self.lock:
            if self.pid_file is not None:
                self.pid_file.unlink(missing_ok=True)
                self.pid_file = None
            self._cleanup_stale_entries()

    def __enter__(self) -> ActiveProfileState:
        return self.acquire()

    def __exit__(self, exc_type, exc, tb) -> None:
        self.release()
