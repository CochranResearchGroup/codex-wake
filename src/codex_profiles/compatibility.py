from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile

from .config import DEFAULT_SHARED_LINKS, Settings


RECEIPT_SCHEMA_VERSION = 1


@dataclass(frozen=True, slots=True)
class CompatibilityReceipt:
    schema_version: int
    codex_version: str
    tool_version: str
    policy_fingerprint: str
    accepted_at: str


@dataclass(frozen=True, slots=True)
class CompatibilityStatus:
    compatible: bool
    issues: tuple[str, ...]
    current: CompatibilityReceipt
    accepted: CompatibilityReceipt | None


def receipt_path(settings: Settings) -> Path:
    return settings.shared_root / ".compatibility.json"


def requires_compatibility_gate(settings: Settings) -> bool:
    return settings.selection_mode == "projection" or any(
        path not in DEFAULT_SHARED_LINKS for path in settings.shared_links
    )


def policy_fingerprint(settings: Settings) -> str:
    policy = {
        "selection_mode": settings.selection_mode,
        "state_root": str(settings.state_root.resolve(strict=False)),
        "source_root": str(settings.source_root.resolve(strict=False)),
        "shared_dir_name": settings.shared_dir_name,
        "account_prefix": settings.account_prefix,
        "shared_links": list(settings.shared_links),
        "projected_links": list(settings.projected_links),
    }
    encoded = json.dumps(policy, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _current_receipt(settings: Settings, codex_version: str, tool_version: str) -> CompatibilityReceipt:
    return CompatibilityReceipt(
        schema_version=RECEIPT_SCHEMA_VERSION,
        codex_version=codex_version,
        tool_version=tool_version,
        policy_fingerprint=policy_fingerprint(settings),
        accepted_at=datetime.now(timezone.utc).isoformat(),
    )


def read_compatibility_receipt(settings: Settings) -> CompatibilityReceipt | None:
    path = receipt_path(settings)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return CompatibilityReceipt(**payload)
    except (FileNotFoundError, OSError, json.JSONDecodeError, TypeError, KeyError):
        return None


def write_compatibility_receipt(settings: Settings, *, codex_version: str, tool_version: str) -> CompatibilityReceipt:
    receipt = _current_receipt(settings, codex_version, tool_version)
    path = receipt_path(settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(asdict(receipt), handle, indent=2, sort_keys=True)
        handle.write("\n")
        temporary_path = Path(handle.name)
    os.replace(temporary_path, path)
    return receipt


def compatibility_status(settings: Settings, *, codex_version: str, tool_version: str) -> CompatibilityStatus:
    current = _current_receipt(settings, codex_version, tool_version)
    accepted = read_compatibility_receipt(settings)
    issues: list[str] = []
    if accepted is None:
        issues.append("No compatibility receipt has been accepted")
    else:
        if accepted.schema_version != current.schema_version:
            issues.append("Compatibility receipt schema changed")
        if accepted.codex_version != current.codex_version:
            issues.append("Codex version changed")
        if accepted.tool_version != current.tool_version:
            issues.append("codex-profiles version changed")
        if accepted.policy_fingerprint != current.policy_fingerprint:
            issues.append("Profile policy changed")
    return CompatibilityStatus(not issues, tuple(issues), current, accepted)


def _path_policy_issues(settings: Settings) -> list[str]:
    issues: list[str] = []
    for field_name, paths in (("shared_links", settings.shared_links), ("projected_links", settings.projected_links)):
        for value in paths:
            path = Path(value)
            if path.is_absolute() or not value or ".." in path.parts or path == Path("."):
                issues.append(f"unsafe {field_name} path: {value!r}")
    return issues


def _sqlite_integrity_issues(settings: Settings) -> list[str]:
    candidates: set[Path] = set()
    roots = [settings.shared_root, settings.source_root]
    if settings.state_root.exists():
        roots.extend(
            path
            for path in settings.state_root.glob(f"{settings.account_prefix}*")
            if path.is_dir()
        )
    for root in roots:
        if root.exists():
            candidates.update(root.glob("*.sqlite"))

    issues: list[str] = []
    for database in sorted(candidates):
        try:
            connection = sqlite3.connect(f"{database.resolve(strict=False).as_uri()}?mode=ro", uri=True)
            try:
                result = connection.execute("PRAGMA quick_check").fetchone()
            finally:
                connection.close()
            if not result or result[0] != "ok":
                detail = result[0] if result else "no result"
                issues.append(f"SQLite integrity check failed for {database}: {detail}")
        except sqlite3.Error as exc:
            issues.append(f"SQLite integrity check failed for {database}: {exc}")
    return issues


def _legacy_shared_symlink_issues(settings: Settings) -> list[str]:
    if not settings.state_root.exists():
        return []
    shared_root = settings.shared_root.resolve(strict=False)
    allowed = set(settings.shared_links)
    issues: list[str] = []
    profile_roots = {
        path
        for path in settings.state_root.glob(f"{settings.account_prefix}*")
        if path.is_dir()
    }
    profile_roots.update(settings.account_root(name) for name in settings.known_profiles)
    for profile_root in sorted(profile_roots):
        if not profile_root.exists():
            continue
        candidates = list(profile_root.iterdir())
        candidates.append(profile_root / "cache" / "codex_apps_tools")
        for path in candidates:
            if not path.is_symlink():
                continue
            try:
                target = path.resolve(strict=False)
                relative = str(path.relative_to(profile_root))
                targets_shared = target.is_relative_to(shared_root)
            except (OSError, ValueError):
                continue
            if targets_shared and relative not in allowed:
                issues.append(f"stale shared runtime symlink in launcher mode: {path} -> {target}")
    return issues


def preflight_issues(settings: Settings) -> tuple[str, ...]:
    issues = [*launcher_safety_issues(settings), *_sqlite_integrity_issues(settings)]
    return tuple(issues)


def launcher_safety_issues(settings: Settings) -> tuple[str, ...]:
    issues = [*_path_policy_issues(settings), *_legacy_shared_symlink_issues(settings)]
    for alias, target in settings.aliases.items():
        alias_root = settings.state_root / settings.normalize_profile_name(alias)
        target_root = settings.state_root / settings.normalize_profile_name(target)
        if alias_root != target_root and alias_root.exists():
            issues.append(f"literal alias home exists and can split profile state: {alias_root}")
    return tuple(issues)
