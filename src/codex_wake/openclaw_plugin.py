from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import tomllib
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any, Protocol

from .records import WakeError


DEFAULT_PLUGIN_ID = "codex-wake"
DEFAULT_PLUGIN_REPO_URL = "https://github.com/CochranResearchGroup/codex-wake.git"
PLUGIN_SUBDIR = Path("plugins") / "openclaw-codex-wake"
PROVENANCE_FILE = "codex-wake-plugin-source.json"


class CommandRunner(Protocol):
    def run(
        self,
        args: list[str],
        *,
        cwd: Path | None = None,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        ...


class SubprocessRunner:
    def run(
        self,
        args: list[str],
        *,
        cwd: Path | None = None,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(args, cwd=cwd, check=check, text=True, capture_output=True)


@dataclass(frozen=True)
class PluginSource:
    path: Path
    plugin_id: str
    plugin_version: str
    package_name: str
    package_version: str


@dataclass(frozen=True)
class PruneResult:
    config_path: str
    backup_path: str
    linked_source_dir: str
    removed_paths: list[str]
    changed: bool
    dry_run: bool


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise WakeError(f"missing required plugin file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise WakeError(f"invalid JSON in plugin file: {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise WakeError(f"plugin file must contain a JSON object: {path}")
    return payload


def validate_plugin_source_dir(path: Path) -> PluginSource:
    resolved = path.expanduser().resolve()
    manifest = _read_json(resolved / "openclaw.plugin.json")
    package = _read_json(resolved / "package.json")
    plugin_id = str(manifest.get("id") or "")
    package_name = str(package.get("name") or "")
    if plugin_id != DEFAULT_PLUGIN_ID:
        raise WakeError(f"unexpected OpenClaw plugin id {plugin_id!r}; expected {DEFAULT_PLUGIN_ID!r}")
    if not package_name:
        raise WakeError(f"plugin package.json missing name: {resolved / 'package.json'}")
    main = str(package.get("main") or "index.js")
    if not (resolved / main).exists():
        raise WakeError(f"plugin package main file is missing: {resolved / main}")
    return PluginSource(
        path=resolved,
        plugin_id=plugin_id,
        plugin_version=str(manifest.get("version") or ""),
        package_name=package_name,
        package_version=str(package.get("version") or ""),
    )


def package_version() -> str:
    pyproject = Path(__file__).resolve().parents[2] / "pyproject.toml"
    try:
        payload = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    except (FileNotFoundError, tomllib.TOMLDecodeError):
        payload = {}
    project = payload.get("project")
    if isinstance(project, dict) and isinstance(project.get("version"), str):
        return project["version"]
    try:
        return version("codex-wake")
    except PackageNotFoundError:
        return ""
    return ""


def default_plugin_ref() -> str:
    current = package_version()
    if not current:
        raise WakeError("cannot infer codex-wake version; pass --tag explicitly")
    return f"v{current}"


def user_data_dir(env: dict[str, str] | None = None) -> Path:
    source = env if env is not None else os.environ
    base = source.get("XDG_DATA_HOME")
    if base:
        return Path(base).expanduser() / "codex-wake"
    return Path.home() / ".local" / "share" / "codex-wake"


def default_materialize_root(env: dict[str, str] | None = None) -> Path:
    return user_data_dir(env) / "openclaw-plugins"


def safe_ref_slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-_.")
    return slug or "ref"


def repo_plugin_source_dir(repo_root: Path | None = None) -> Path:
    root = (repo_root or Path.cwd()).resolve()
    return root / PLUGIN_SUBDIR


def default_openclaw_config_path() -> Path:
    return Path.home() / ".openclaw" / "openclaw.json"


def _resolve_config_path(value: str, *, base: Path) -> Path:
    candidate = Path(value).expanduser()
    if not candidate.is_absolute():
        candidate = base / candidate
    return candidate.resolve()


def _same_path(left: str, right: Path, *, base: Path) -> bool:
    try:
        return _resolve_config_path(left, base=base) == right
    except OSError:
        return False


def _plugin_id_for_path(path: Path) -> str:
    try:
        payload = json.loads((path / "openclaw.plugin.json").read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return ""
    if not isinstance(payload, dict):
        return ""
    return str(payload.get("id") or "")


def prune_openclaw_linked_plugin_path(
    *,
    config_path: Path | None = None,
    linked_source_dir: Path | None = None,
    dry_run: bool = False,
    now: datetime | None = None,
) -> PruneResult:
    resolved_config = (config_path or default_openclaw_config_path()).expanduser().resolve()
    resolved_link = linked_source_dir.expanduser().resolve() if linked_source_dir else None
    try:
        raw = resolved_config.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise WakeError(f"OpenClaw config not found: {resolved_config}") from exc
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise WakeError(f"invalid OpenClaw config JSON: {resolved_config}: {exc}") from exc
    if not isinstance(payload, dict):
        raise WakeError(f"OpenClaw config must contain a JSON object: {resolved_config}")

    plugins = payload.get("plugins")
    load = plugins.get("load") if isinstance(plugins, dict) else None
    paths = load.get("paths") if isinstance(load, dict) else None
    if not isinstance(paths, list):
        return PruneResult(
            config_path=str(resolved_config),
            backup_path="",
            linked_source_dir=str(resolved_link) if resolved_link else "",
            removed_paths=[],
            changed=False,
            dry_run=dry_run,
        )

    kept: list[Any] = []
    removed: list[str] = []
    for item in paths:
        should_remove = False
        if isinstance(item, str) and resolved_link is not None:
            should_remove = _same_path(item, resolved_link, base=resolved_config.parent)
        elif isinstance(item, str):
            candidate = _resolve_config_path(item, base=resolved_config.parent)
            should_remove = _plugin_id_for_path(candidate) == DEFAULT_PLUGIN_ID
        if should_remove:
            removed.append(item)
        else:
            kept.append(item)

    if not removed:
        return PruneResult(
            config_path=str(resolved_config),
            backup_path="",
            linked_source_dir=str(resolved_link) if resolved_link else "",
            removed_paths=[],
            changed=False,
            dry_run=dry_run,
        )

    backup_path = ""
    if not dry_run:
        timestamp = (now or datetime.now(UTC)).replace(microsecond=0).strftime("%Y%m%dT%H%M%SZ")
        backup = resolved_config.with_name(f"{resolved_config.name}.codex-wake-backup-{timestamp}")
        backup.write_text(raw, encoding="utf-8")
        load["paths"] = kept
        tmp = resolved_config.with_name(f".{resolved_config.name}.codex-wake-tmp")
        tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        os.replace(tmp, resolved_config)
        backup_path = str(backup)

    return PruneResult(
        config_path=str(resolved_config),
        backup_path=backup_path,
        linked_source_dir=str(resolved_link) if resolved_link else "",
        removed_paths=removed,
        changed=True,
        dry_run=dry_run,
    )


def _run(
    runner: CommandRunner | None,
    args: list[str],
    *,
    cwd: Path | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    return (runner or SubprocessRunner()).run(args, cwd=cwd, check=check)


def _copy_plugin_tree(source: Path, destination: Path) -> None:
    if destination.exists():
        shutil.rmtree(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(
        source,
        destination,
        ignore=shutil.ignore_patterns("node_modules", ".git", "coverage", "*.tgz"),
    )


def materialize_plugin_from_git(
    *,
    repo_url: str = DEFAULT_PLUGIN_REPO_URL,
    ref: str | None = None,
    destination_root: Path | None = None,
    refresh: bool = False,
    runner: CommandRunner | None = None,
    now: datetime | None = None,
) -> PluginSource:
    resolved_ref = ref or default_plugin_ref()
    destination = (destination_root or default_materialize_root()).expanduser() / safe_ref_slug(resolved_ref)
    if destination.exists() and not refresh:
        return validate_plugin_source_dir(destination)
    with tempfile.TemporaryDirectory(prefix="codex-wake-openclaw-plugin-") as tmp:
        tmp_root = Path(tmp)
        repo_dir = tmp_root / "repo"
        _run(runner, ["git", "clone", "--depth", "1", "--branch", resolved_ref, repo_url, str(repo_dir)])
        source = repo_dir / PLUGIN_SUBDIR
        plugin = validate_plugin_source_dir(source)
        _copy_plugin_tree(plugin.path, destination)
        commit_result = _run(runner, ["git", "-C", str(repo_dir), "rev-parse", "HEAD"], check=False)
        commit = commit_result.stdout.strip() if commit_result.returncode == 0 else ""
    materialized = validate_plugin_source_dir(destination)
    provenance = {
        "schema_version": 1,
        "source": "git",
        "repo_url": repo_url,
        "ref": resolved_ref,
        "commit": commit,
        "plugin_subdir": str(PLUGIN_SUBDIR),
        "materialized_at": (now or datetime.now(UTC)).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    }
    (destination / PROVENANCE_FILE).write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return materialized


def resolve_openclaw_command(raw: str | None = None) -> str:
    if raw:
        return raw
    found = shutil.which("openclaw")
    if not found:
        raise WakeError("openclaw was not found on PATH; pass --openclaw-path")
    return found


def install_openclaw_plugin(
    *,
    source_dir: Path | None = None,
    repo_url: str = DEFAULT_PLUGIN_REPO_URL,
    ref: str | None = None,
    materialize_dir: Path | None = None,
    openclaw_path: str | None = None,
    force: bool = False,
    refresh: bool = False,
    dry_run: bool = False,
    prune_linked_path: bool = False,
    linked_source_dir: Path | None = None,
    openclaw_config: Path | None = None,
    runner: CommandRunner | None = None,
) -> dict[str, Any]:
    if source_dir:
        source = validate_plugin_source_dir(source_dir)
        source_kind = "local-path"
    else:
        source = materialize_plugin_from_git(
            repo_url=repo_url,
            ref=ref,
            destination_root=materialize_dir,
            refresh=refresh,
            runner=runner,
        )
        source_kind = "git-materialized"
    openclaw = resolve_openclaw_command(openclaw_path)
    command = [openclaw, "plugins", "install"]
    if force:
        command.append("--force")
    command.append(str(source.path))
    result: subprocess.CompletedProcess[str] | None = None
    prune_result: PruneResult | None = None
    registry_refresh: dict[str, Any] | None = None
    registry_command = [openclaw, "plugins", "registry", "--refresh"]
    if prune_linked_path:
        prune_result = prune_openclaw_linked_plugin_path(
            config_path=openclaw_config,
            linked_source_dir=linked_source_dir,
            dry_run=True,
        )
        if dry_run and prune_result.changed:
            registry_refresh = {
                "command": registry_command,
                "dry_run": True,
                "returncode": None,
                "stdout": "",
                "stderr": "",
            }
    if not dry_run:
        result = _run(runner, command)
        if prune_linked_path:
            prune_result = prune_openclaw_linked_plugin_path(
                config_path=openclaw_config,
                linked_source_dir=linked_source_dir,
                dry_run=False,
            )
            if prune_result.changed:
                refresh_result = _run(runner, registry_command)
                registry_refresh = {
                    "command": registry_command,
                    "dry_run": False,
                    "returncode": refresh_result.returncode,
                    "stdout": refresh_result.stdout,
                    "stderr": refresh_result.stderr,
                }
    return {
        "plugin_id": source.plugin_id,
        "plugin_version": source.plugin_version,
        "package_name": source.package_name,
        "package_version": source.package_version,
        "source_kind": source_kind,
        "source_path": str(source.path),
        "command": command,
        "dry_run": dry_run,
        "returncode": result.returncode if result else None,
        "stdout": result.stdout if result else "",
        "stderr": result.stderr if result else "",
        "prune_linked_path": asdict(prune_result) if prune_result else None,
        "registry_refresh": registry_refresh,
    }


def pack_openclaw_plugin(
    *,
    source_dir: Path | None = None,
    output_dir: Path,
    npm_path: str = "npm",
    runner: CommandRunner | None = None,
) -> dict[str, Any]:
    source = validate_plugin_source_dir(source_dir or repo_plugin_source_dir())
    resolved_output = output_dir.expanduser().resolve()
    resolved_output.mkdir(parents=True, exist_ok=True)
    result = _run(runner, [npm_path, "pack", str(source.path), "--pack-destination", str(resolved_output)])
    tarball_name = result.stdout.strip().splitlines()[-1] if result.stdout.strip() else ""
    tarball = resolved_output / tarball_name if tarball_name else None
    return {
        "plugin_id": source.plugin_id,
        "plugin_version": source.plugin_version,
        "package_name": source.package_name,
        "package_version": source.package_version,
        "source_path": str(source.path),
        "output_dir": str(resolved_output),
        "tarball": str(tarball) if tarball else "",
        "command": [npm_path, "pack", str(source.path), "--pack-destination", str(resolved_output)],
        "stdout": result.stdout,
        "stderr": result.stderr,
    }
