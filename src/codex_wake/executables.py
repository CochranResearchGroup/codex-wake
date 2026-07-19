from __future__ import annotations

import os
import shutil
import stat
from pathlib import Path
from typing import Mapping

from .records import WakeError


_VERSIONED_LAYOUTS = (
    ("versions", "node"),
    ("node-versions",),
    ("installs", "nodejs"),
    ("installs", "node"),
    ("tools", "image", "node"),
    ("packages", "standalone", "releases"),
)
_STABLE_SWITCHPOINT_SEGMENTS = {"current", "default", "latest", "lts", "stable"}


def _absolute_spelling(raw: str) -> Path:
    expanded = Path(raw).expanduser()
    if not expanded.is_absolute():
        expanded = Path.cwd() / expanded
    return Path(os.path.abspath(expanded))


def _contains_sequence(parts: tuple[str, ...], sequence: tuple[str, ...]) -> int:
    width = len(sequence)
    for index in range(len(parts) - width):
        if parts[index : index + width] == sequence:
            return index + width
    return -1


def _is_version_managed_node_path(path: Path) -> bool:
    parts = path.parts
    if "fnm_multishells" in parts:
        return True
    for layout in _VERSIONED_LAYOUTS:
        version_index = _contains_sequence(parts, layout)
        if version_index >= 0 and version_index < len(parts):
            if parts[version_index].lower() not in _STABLE_SWITCHPOINT_SEGMENTS:
                return True
    return False


def _validate_executable(path: Path, *, label: str, reject_node_versioned: bool) -> Path:
    text = str(path)
    if reject_node_versioned and _is_version_managed_node_path(path):
        raise WakeError(
            f"{label} path is tied to a version-managed Node installation: {text}; "
            "provide a stable wrapper or symlink path instead"
        )
    try:
        mode = path.stat().st_mode
    except OSError as exc:
        raise WakeError(f"{label} executable does not exist: {text}") from exc
    if not stat.S_ISREG(mode):
        raise WakeError(f"{label} executable is not a regular file: {text}")
    if not os.access(path, os.X_OK):
        raise WakeError(f"{label} executable is not executable: {text}")
    return path


def resolve_stable_executable(
    raw: str | None,
    *,
    default_command: str,
    label: str,
    env: Mapping[str, str] | None = None,
    path: str | None = None,
    required: bool = True,
    reject_node_versioned: bool = False,
) -> str:
    """Resolve an executable without dereferencing its stable path spelling."""
    candidate = (raw or "").strip()
    source_env = env if env is not None else os.environ
    search_path = path if path is not None else source_env.get("PATH")
    if candidate and "/" in candidate:
        resolved = _absolute_spelling(candidate)
        try:
            return str(
                _validate_executable(
                    resolved,
                    label=label,
                    reject_node_versioned=reject_node_versioned,
                )
            )
        except WakeError:
            if required:
                raise
            return ""

    command = candidate or default_command
    rejected: WakeError | None = None
    for directory in (search_path or "").split(os.pathsep):
        if not directory:
            continue
        found = shutil.which(command, path=directory)
        if not found:
            continue
        resolved = _absolute_spelling(found)
        try:
            return str(
                _validate_executable(
                    resolved,
                    label=label,
                    reject_node_versioned=reject_node_versioned,
                )
            )
        except WakeError as exc:
            rejected = exc
    if required:
        if rejected is not None:
            raise rejected
        raise WakeError(f"{label} executable was not found on PATH: {command}")
    return ""
