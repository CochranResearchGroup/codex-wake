from __future__ import annotations

import os
from pathlib import Path
from typing import Any


_HOST_BOOT_ID: str | None = None


def process_exists(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def process_identity(pid: int, proc_root: Path = Path("/proc")) -> dict[str, Any] | None:
    start_time_ticks = process_start_time_ticks(pid, proc_root=proc_root)
    if start_time_ticks is None:
        return None
    identity: dict[str, Any] = {"start_time_ticks": start_time_ticks}
    boot_id = boot_id_value(proc_root=proc_root)
    if boot_id:
        identity["boot_id"] = boot_id
    return identity


def process_start_time_ticks(pid: int, proc_root: Path = Path("/proc")) -> int | None:
    stat_path = proc_root / str(pid) / "stat"
    try:
        text = stat_path.read_text(encoding="utf-8")
    except (FileNotFoundError, NotADirectoryError, PermissionError, OSError):
        return None
    marker = ") "
    marker_index = text.rfind(marker)
    if marker_index < 0:
        return None
    fields_from_state = text[marker_index + len(marker) :].split()
    start_time_index = 22 - 3
    try:
        return int(fields_from_state[start_time_index])
    except (IndexError, ValueError):
        return None


def boot_id_value(proc_root: Path = Path("/proc")) -> str | None:
    global _HOST_BOOT_ID
    # A Linux process cannot survive a host reboot. Only the real host boot ID
    # is immutable for this process lifetime; alternate proc roots remain live.
    host = proc_root == Path("/proc")
    if host and _HOST_BOOT_ID is not None:
        return _HOST_BOOT_ID
    boot_id_path = proc_root / "sys" / "kernel" / "random" / "boot_id"
    try:
        value = boot_id_path.read_text(encoding="utf-8").strip()
    except (FileNotFoundError, PermissionError, OSError):
        return None
    if host and value:
        _HOST_BOOT_ID = value
    return value or None
