#!/usr/bin/env python3
"""Production-local effectors for the P53-C6 qualification contract.

This module owns only the isolated local wheel, no-dispatch anchor, loopback
listener, and user-service lifecycle. It contains no GitHub webhook transport,
pull-request merge, redelivery, route mutation, or dispatch path.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import socket
import sqlite3
import subprocess
import sys
import tarfile
import tempfile
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


_CONTRACT_PATH = Path(__file__).with_name("webhook_live_github_qualification.py")
_SPEC = importlib.util.spec_from_file_location("webhook_live_github_qualification", _CONTRACT_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError("P53-C6 qualification contract is unavailable")
contract = importlib.util.module_from_spec(_SPEC)
sys.modules.setdefault(_SPEC.name, contract)
_SPEC.loader.exec_module(contract)

MAX_COMMAND_SECONDS = 120
READY_SECONDS = 30
_CONSOLE_SCRIPTS = {
    "codex-wake": "codex_wake.cli:main",
    "codex-waked": "codex_wake.daemon:main",
    "codex-wake-hook": "codex_wake.hook:main",
    "codex-wake-github-webhook": "codex_wake.webhook_listener:main",
}


@dataclass(frozen=True)
class LocalContext:
    root: Path
    repo_root: Path
    wake_root: Path
    artifact_dir: Path
    wheel_dir: Path
    export_root: Path
    venv: Path
    cli: Path
    daemon: Path
    hook: Path
    listener: Path
    python: Path
    unit_dir: Path
    unit_path: Path
    log_path: Path


def context_for(root: Path, *, repo_root: Path | None = None,
                env: Mapping[str, str] | None = None) -> LocalContext:
    values = os.environ if env is None else env
    repository = (repo_root or Path(__file__).resolve().parents[1]).resolve()
    config_home = Path(values.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))).expanduser()
    if not config_home.is_absolute():
        raise RuntimeError("XDG_CONFIG_HOME must be absolute")
    unit_dir = (config_home / "systemd" / "user").resolve()
    venv = root / "venv"
    return LocalContext(
        root=root, repo_root=repository, wake_root=root / "wake",
        artifact_dir=root / "evidence", wheel_dir=root / "wheel",
        export_root=root / "export", venv=venv,
        cli=venv / "bin/codex-wake", daemon=venv / "bin/codex-waked",
        hook=venv / "bin/codex-wake-hook",
        listener=venv / "bin/codex-wake-github-webhook",
        python=venv / "bin/python", unit_dir=unit_dir,
        unit_path=unit_dir / contract.UNIT,
        log_path=root / "logs/webhook-listener.log",
    )


def _owner_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    os.chmod(path, 0o700)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ProductionLocalAdapter:
    """Bounded local implementation of ``RuntimeEffectors``.

    Command execution is an overridable method so tests can prove argv and
    ordering without touching a service, process, network, or repository.
    """

    def __init__(self, root: Path, *, repo_root: Path | None = None,
                 env: Mapping[str, str] | None = None):
        self.env = dict(os.environ if env is None else env)
        self.context = context_for(root, repo_root=repo_root, env=self.env)

    def _command(self, argv: list[str], *, name: str, timeout: int = MAX_COMMAND_SECONDS,
                 cwd: Path | None = None, allow: tuple[int, ...] = (0,),
                 binary: bool = False) -> subprocess.CompletedProcess:
        if not argv or timeout < 1 or timeout > MAX_COMMAND_SECONDS:
            raise RuntimeError("bounded local command is invalid")
        result = subprocess.run(
            argv, cwd=cwd, env=self.env, capture_output=True,
            text=not binary, check=False, timeout=timeout,
        )
        _owner_directory(self.context.artifact_dir)
        (self.context.artifact_dir / f"{name}.json").write_text(
            json.dumps({"argv": argv, "returncode": result.returncode}, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        if result.returncode not in allow:
            raise RuntimeError(f"{name} failed with exit code {result.returncode}")
        return result

    def _json(self, argv: list[str], *, name: str,
              allow: tuple[int, ...] = (0,)) -> dict[str, Any]:
        result = self._command(argv, name=name, allow=allow)
        try:
            value = json.loads(result.stdout)
        except (TypeError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"{name} did not emit JSON") from exc
        if type(value) is not dict:
            raise RuntimeError(f"{name} did not emit a JSON object")
        return value

    def _cli(self, *args: str) -> list[str]:
        return [str(self.context.cli), "--wake-root", str(self.context.wake_root), *args]

    def _source_args(self, enabled: bool) -> list[str]:
        return self._cli(
            "github-ci", "source", "configure", "--source", contract.SOURCE,
            "--repository", contract.REPOSITORY, "--repository-id", str(contract.REPOSITORY_ID),
            "--workflow-id", str(contract.WORKFLOW_ID), "--ref", contract.REF,
            "--conclusion", contract.CONCLUSION, "--credential-ref", contract.TOKEN_REF,
            "--enabled" if enabled else "--disabled",
        )

    def _failed_units(self, name: str) -> tuple[str, ...]:
        result = self._command(
            ["systemctl", "--user", "--failed", "--no-legend", "--plain"],
            name=name,
        )
        return tuple(sorted(line.split()[0] for line in result.stdout.splitlines() if line.split()))

    def canonical_candidate(self, _root: Path) -> Mapping[str, Any]:
        status = self._command(
            ["git", "-C", str(self.context.repo_root), "status", "--porcelain"],
            name="candidate-status",
        ).stdout.strip()
        commit = self._command(
            ["git", "-C", str(self.context.repo_root), "rev-parse", "HEAD"],
            name="candidate-head",
        ).stdout.strip()
        canonical = self._command(
            ["git", "-C", str(self.context.repo_root), "rev-parse", "refs/remotes/origin/main"],
            name="candidate-canonical",
        ).stdout.strip()
        if status or commit != canonical:
            raise RuntimeError("candidate is not clean exact origin/main")
        tree = self._command(
            ["git", "-C", str(self.context.repo_root), "rev-parse", f"{commit}^{{tree}}"],
            name="candidate-tree",
        ).stdout.strip()
        before = self._failed_units("failed-units-before")
        _owner_directory(self.context.artifact_dir)
        (self.context.artifact_dir / "failed-units-before-state.json").write_text(
            json.dumps(list(before), sort_keys=True) + "\n", encoding="utf-8",
        )
        return {"clean": True, "canonical_ref": "refs/remotes/origin/main",
                "commit": commit, "tree": tree}

    def _archive_binding(self, candidate: Mapping[str, Any]) -> dict[str, str]:
        commit = str(candidate.get("commit", ""))
        tree = str(candidate.get("tree", ""))
        ref = str(candidate.get("canonical_ref", ""))
        if ref != "refs/remotes/origin/main" or len(commit) != 40 or len(tree) != 40:
            raise RuntimeError("candidate archive binding is malformed")
        observed_ref = self._command(
            ["git", "-C", str(self.context.repo_root), "rev-parse", ref],
            name="archive-canonical-ref",
        ).stdout.strip()
        observed_commit = self._command(
            ["git", "-C", str(self.context.repo_root), "rev-parse", commit],
            name="archive-candidate-commit",
        ).stdout.strip()
        observed_tree = self._command(
            ["git", "-C", str(self.context.repo_root), "rev-parse", f"{commit}^{{tree}}"],
            name="archive-candidate-tree",
        ).stdout.strip()
        if (observed_ref, observed_commit, observed_tree) != (commit, commit, tree):
            raise RuntimeError("candidate archive is no longer bound to exact origin/main")
        return {"archive_ref": ref, "archive_commit": commit, "archive_tree": tree,
                "build_commit": commit}

    def _archive_candidate(self, binding: Mapping[str, str]) -> subprocess.CompletedProcess:
        return self._command(
            ["git", "-C", str(self.context.repo_root), "archive", "--format=tar", binding["archive_commit"]],
            name="candidate-archive", binary=True,
        )

    def build_wheel(self, _root: Path, candidate: Mapping[str, Any]) -> Mapping[str, Any]:
        binding = self._archive_binding(candidate)
        result = self._archive_candidate(binding)
        self.context.export_root.mkdir(mode=0o700)
        with tempfile.NamedTemporaryFile(dir=self.context.root, delete=False) as handle:
            handle.write(result.stdout)
            archive_path = Path(handle.name)
        try:
            with tarfile.open(archive_path) as archive:
                base = self.context.export_root.resolve()
                if any(not (self.context.export_root / member.name).resolve().is_relative_to(base)
                           for member in archive.getmembers()):
                    raise RuntimeError("candidate archive contains an unsafe path")
                archive.extractall(self.context.export_root, filter="data")
        finally:
            archive_path.unlink(missing_ok=True)
        uv = shutil.which("uv")
        if uv is None:
            raise RuntimeError("uv is required for the isolated wheel build")
        self.context.wheel_dir.mkdir(mode=0o700)
        build_env = dict(self.env)
        build_env.pop("PYTHONPATH", None)
        build_env.pop("PYTHONHOME", None)
        previous = self.env
        self.env = build_env
        try:
            self._command(
                [uv, "build", "--wheel", "--out-dir", str(self.context.wheel_dir)],
                name="build-wheel", cwd=self.context.export_root,
            )
        finally:
            self.env = previous
        wheels = tuple(self.context.wheel_dir.glob("codex_wake-*.whl"))
        if len(wheels) != 1:
            raise RuntimeError("candidate did not produce exactly one wheel")
        with zipfile.ZipFile(wheels[0]) as archive:
            if any("sitecustomize" in name or "webhook_live_github" in name
                   for name in archive.namelist()):
                raise RuntimeError("wheel contains qualification runner material")
        return {**binding, "wheel_path": str(wheels[0]), "wheel_sha256": _sha256(wheels[0])}

    def create_venv(self, _root: Path) -> Mapping[str, Any]:
        self._command([sys.executable, "-m", "venv", str(self.context.venv)], name="create-venv")
        return {"isolated": True}

    def install_wheel(self, _root: Path, wheel: Mapping[str, Any]) -> Mapping[str, Any]:
        path = Path(str(wheel.get("wheel_path", "")))
        if path.parent != self.context.wheel_dir or not path.is_file():
            raise RuntimeError("wheel path escaped the isolated build")
        install_env = dict(self.env)
        install_env.pop("PYTHONPATH", None)
        install_env.pop("PYTHONHOME", None)
        previous = self.env
        self.env = install_env
        try:
            self._command(
                [str(self.context.venv / "bin/pip"), "install", "--no-deps", "--force-reinstall", str(path)],
                name="install-wheel",
            )
            installed = self._json(
                [str(self.context.python), "-c", """
import importlib.metadata as metadata
import json
from pathlib import Path

distribution = metadata.distribution(\"codex-wake\")
entries = {
    entry.name: entry.value
    for entry in distribution.entry_points
    if entry.group == \"console_scripts\"
}
print(json.dumps({
    \"location\": str(Path(distribution.locate_file(\"\")).resolve()),
    \"console_scripts\": entries,
}, sort_keys=True))
"""],
                name="verify-wheel-install",
            )
        finally:
            self.env = previous
        location = Path(str(installed.get("location", "")))
        if not location.is_dir() or not location.is_relative_to(self.context.venv.resolve()):
            raise RuntimeError("installed distribution is outside the isolated virtual environment")
        if installed.get("console_scripts") != _CONSOLE_SCRIPTS:
            raise RuntimeError("installed distribution console scripts are incomplete")
        required = (self.context.cli, self.context.daemon, self.context.hook,
                    self.context.listener, self.context.python)
        if not all(item.is_file() for item in required):
            raise RuntimeError("installed qualification executables are incomplete")
        return {"global_install_mutations": 0,
                "installed_listener_sha256": _sha256(self.context.listener)}

    def configure_source(self, _root: Path, _environment: Mapping[str, Any]) -> Mapping[str, Any]:
        if self.context.unit_path.exists() or not self._port_free():
            raise RuntimeError("exact C6 service or port already exists")
        self._command(self._source_args(False), name="configure-source-disabled")
        return {"source": contract.SOURCE, "enabled": False}

    def _wait_monitor(self, process: subprocess.Popen) -> None:
        deadline = time.monotonic() + READY_SECONDS
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError("no-dispatch daemon exited before readiness")
            value = self._json(
                self._cli("monitor", "check", "--json"), name="daemon-readiness", allow=(0, 1),
            )
            if value.get("monitor_ready") is True and value.get("monitor_source") == "codex-waked":
                return
            time.sleep(0.2)
        raise RuntimeError("no-dispatch daemon did not become ready")

    def initialize_daemon(self, _root: Path, _environment: Mapping[str, Any]) -> Mapping[str, Any]:
        _owner_directory(self.context.artifact_dir)
        stdout = (self.context.artifact_dir / "daemon.stdout").open("w", encoding="utf-8")
        stderr = (self.context.artifact_dir / "daemon.stderr").open("w", encoding="utf-8")
        process = subprocess.Popen(
            [str(self.context.daemon), "--wake-root", str(self.context.wake_root),
             "--interval", "300", "--no-dispatch"],
            stdout=stdout, stderr=stderr, text=True, env=self.env, start_new_session=True,
        )
        try:
            self._wait_monitor(process)
            self._command(self._source_args(True), name="enable-source")
            armed = self._command(
                self._cli(
                    "github-ci", "completed", "--source", contract.SOURCE,
                    "--ref", contract.REF, "--conclusion", contract.CONCLUSION,
                    "--idempotency-key", contract.SOURCE, "--",
                    "P53-C6 live qualification; dispatch disabled",
                ),
                name="arm-live-qualification",
            )
            wake_id = armed.stdout.split(maxsplit=1)[0]
            if not wake_id.startswith("wake_"):
                raise RuntimeError("installed arm did not return a wake identity")
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
            stdout.close()
            stderr.close()
        database = self.context.wake_root / "signals" / "journal.sqlite3"
        with sqlite3.connect(f"file:{database}?mode=ro", uri=True) as connection:
            row = connection.execute(
                "SELECT source_anchor FROM arms WHERE wake_id = ?", (wake_id,),
            ).fetchone()
        if row is None or type(row[0]) is not str or not row[0]:
            raise RuntimeError("durable source anchor is unavailable")
        shown = self._json(
            self._cli("github-ci", "source", "show", contract.SOURCE, "--json"),
            name="enabled-source-readback",
        )
        if shown.get("enabled") is not True:
            raise RuntimeError("GitHub source did not remain enabled")
        return {"dispatch_enabled": False, "anchor": row[0],
                "source_enabled": True, "wake_id": wake_id}

    def configure_listener(self, _root: Path, _environment: Mapping[str, Any]) -> Mapping[str, Any]:
        self._command(
            self._cli(
                "github-webhook", "source", "configure", "--source", contract.SOURCE,
                "--bind-address", "127.0.0.1", "--port", "8820",
                "--secret-ref", contract.SECRET_REF, "--enabled",
            ), name="configure-listener",
        )
        return {"source": contract.SOURCE, "address": "127.0.0.1", "port": 8820}

    def _service_args(self, action: str) -> list[str]:
        values = self._cli(
            "github-webhook", "service", action, "--source", contract.SOURCE,
            "--unit-dir", str(self.context.unit_dir), "--log-path", str(self.context.log_path),
        )
        if action == "install":
            values.extend(("--executable-path", str(self.context.listener)))
        return values

    def install_service(self, _root: Path, _environment: Mapping[str, Any]) -> Mapping[str, Any]:
        self._command(self._service_args("install"), name="install-service")
        return {"unit": contract.UNIT}

    def readiness(self, _root: Path, _environment: Mapping[str, Any]) -> Mapping[str, Any]:
        deadline = time.monotonic() + READY_SECONDS
        while time.monotonic() < deadline:
            ready = self._json(
                self._cli("github-webhook", "readiness", "--source", contract.SOURCE, "--json"),
                name="listener-readiness", allow=(0, 1),
            )
            if ready.get("status") == "ready":
                break
            time.sleep(0.2)
        else:
            raise RuntimeError("installed listener did not become ready")
        active = self._command(
            ["systemctl", "--user", "is-active", contract.UNIT], name="listener-active",
        ).stdout.strip()
        enabled = self._command(
            ["systemctl", "--user", "is-enabled", contract.UNIT], name="listener-enabled",
        ).stdout.strip()
        pid_text = self._command(
            ["systemctl", "--user", "show", contract.UNIT, "--property=MainPID", "--value"],
            name="listener-pid",
        ).stdout.strip()
        if active != "active" or enabled != "enabled" or not pid_text.isdigit() or int(pid_text) <= 0:
            raise RuntimeError("installed listener service identity is invalid")
        if not self._pid_matches(int(pid_text)):
            raise RuntimeError("installed listener process identity is invalid")
        return {"ready": True, "source": contract.SOURCE, "dispatch_enabled": False,
                "pid": int(pid_text), "active": active, "enabled": enabled}

    def uninstall_service(self, _root: Path, _state: Mapping[str, Any]) -> Mapping[str, Any]:
        if self.context.unit_path.exists() or self.context.unit_path.is_symlink():
            self._command(self._service_args("uninstall"), name="uninstall-service")
        return {"unit": contract.UNIT, "uninstalled": True}

    def _pid_matches(self, pid: int) -> bool:
        try:
            args = tuple(item.decode("utf-8") for item in
                         (Path("/proc") / str(pid) / "cmdline").read_bytes().split(b"\0") if item)
        except (FileNotFoundError, OSError, UnicodeError):
            return False
        return (args and Path(args[0]).resolve() == self.context.python.resolve()
                and str(self.context.listener) in args
                and "--wake-root" in args and str(self.context.wake_root) in args
                and "--source" in args and contract.SOURCE in args)

    def _matching_processes(self) -> int:
        matches = 0
        for item in Path("/proc").iterdir():
            if item.name.isdigit() and self._pid_matches(int(item.name)):
                matches += 1
        return matches

    @staticmethod
    def _port_free() -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                probe.bind(("127.0.0.1", 8820))
            except OSError:
                return False
        return True

    def runtime_census(self, _root: Path, _state: Mapping[str, Any]) -> Mapping[str, Any]:
        active_result = self._command(
            ["systemctl", "--user", "is-active", contract.UNIT], name="cleanup-active",
            allow=(0, 3, 4),
        )
        active = active_result.stdout.strip()
        if (active_result.returncode, active) not in {(0, "active"), (3, "inactive"), (4, "inactive")}:
            raise RuntimeError("cleanup active-state systemctl query is invalid")
        enabled_result = self._command(
            ["systemctl", "--user", "is-enabled", contract.UNIT], name="cleanup-enabled",
            allow=(0, 1, 4),
        )
        enabled_raw = enabled_result.stdout.strip()
        if (enabled_result.returncode, enabled_raw) not in {
            (0, "enabled"), (1, "disabled"), (1, "not-found"), (4, "not-found"),
        }:
            raise RuntimeError("cleanup enabled-state systemctl query is invalid")
        pid_result = self._command(
            ["systemctl", "--user", "show", contract.UNIT, "--property=MainPID", "--value"],
            name="cleanup-pid",
        )
        pid_text = pid_result.stdout.strip()
        if (pid_result.returncode, pid_text) != (0, "0"):
            raise RuntimeError("cleanup PID systemctl query is invalid")
        failed_units = self._failed_units("cleanup-failed-units")
        return {"unit_absent": not self.context.unit_path.exists() and not self.context.unit_path.is_symlink(),
                "active": active,
                "enabled": "disabled" if enabled_raw in {"disabled", "not-found"} else enabled_raw,
                "pid": int(pid_text),
                "matching_processes": self._matching_processes(),
                "port_8820_released": self._port_free(),
                "unit_query": {"ok": True, "returncode": 0,
                               "observed_returncodes": {"active": active_result.returncode,
                                                        "enabled": enabled_result.returncode,
                                                        "pid": pid_result.returncode}},
                "failed_units_query": {"ok": True, "returncode": 0,
                                       "units": list(failed_units)}}

    def unrelated_state(self, _root: Path, _state: Mapping[str, Any]) -> Mapping[str, Any]:
        before_path = self.context.artifact_dir / "failed-units-before-state.json"
        if not before_path.is_file():
            raise RuntimeError("unrelated-state baseline is unavailable")
        before = tuple(json.loads(before_path.read_text(encoding="utf-8")))
        after = self._failed_units("failed-units-after")
        return {"failed_units_before": list(before), "failed_units_after": list(after),
                "failed_units_delta": sorted(set(before) ^ set(after))}

    def journal_snapshot(self, wake_id: str) -> dict[str, Any]:
        """Read the exact durable C6 journal without changing evaluation state."""
        if not wake_id.startswith("wake_"):
            raise RuntimeError("wake identity is invalid")
        database = self.context.wake_root / "signals" / "journal.sqlite3"
        with sqlite3.connect(f"file:{database}?mode=ro", uri=True) as connection:
            connection.row_factory = sqlite3.Row
            receipts = connection.execute(
                """
                SELECT receipt_id, occurrence_namespace, occurrence_value,
                       attributes_json, verification_state, verification_method
                FROM receipts
                WHERE source = 'github' AND source_instance = ?
                ORDER BY local_sequence
                """,
                (contract.SOURCE,),
            ).fetchall()
            arm = connection.execute(
                "SELECT registered_at, source_anchor FROM arms WHERE wake_id = ?",
                (wake_id,),
            ).fetchone()
            matches = connection.execute(
                "SELECT COUNT(*) FROM match_reservations WHERE wake_id = ?",
                (wake_id,),
            ).fetchone()[0]
            checkpoint = connection.execute(
                """
                SELECT checkpoint, checkpoint_order, observed_through
                FROM source_state WHERE source = 'github' AND source_instance = ?
                """,
                (contract.SOURCE,),
            ).fetchone()
        if arm is None or checkpoint is None:
            raise RuntimeError("durable C6 journal authority is incomplete")
        statuses = {
            name: int((self.context.wake_root / name / f"{wake_id}.json").is_file())
            for name in ("pending", "firing", "submitted", "failed")
        }
        return {
            "wake_id": wake_id, "registered_at": arm["registered_at"],
            "source_anchor": arm["source_anchor"], "receipt_count": len(receipts),
            "receipts": [
                {"receipt_id": row["receipt_id"],
                 "occurrence_namespace": row["occurrence_namespace"],
                 "occurrence_value": row["occurrence_value"],
                 "attributes": json.loads(row["attributes_json"]),
                 "verification_state": row["verification_state"],
                 "verification_method": row["verification_method"]}
                for row in receipts
            ],
            "match_count": int(matches), "statuses": statuses,
            "checkpoint": {"value": checkpoint["checkpoint"],
                           "order": checkpoint["checkpoint_order"],
                           "observed_through": checkpoint["observed_through"]},
        }

    def wait_for_webhook_commit(self, wake_id: str, *, timeout: int = 90) -> dict[str, Any]:
        if type(timeout) is not int or not 1 <= timeout <= 300:
            raise RuntimeError("webhook observation timeout is invalid")
        deadline = time.monotonic() + timeout
        last: dict[str, Any] | None = None
        while time.monotonic() < deadline:
            last = self.journal_snapshot(wake_id)
            if last["receipt_count"] == 1:
                return last
            if last["receipt_count"] > 1:
                raise RuntimeError("webhook committed more than one occurrence")
            time.sleep(0.5)
        raise RuntimeError("webhook occurrence did not commit within the bounded window")

    def poll_once_no_dispatch(self, wake_id: str) -> dict[str, Any]:
        before = self.journal_snapshot(wake_id)
        result = self._command(
            [str(self.context.daemon), "--wake-root", str(self.context.wake_root),
             "--once", "--no-dispatch"],
            name="poll-once-no-dispatch",
        )
        after = self.journal_snapshot(wake_id)
        return {"before": before, "after": after,
                "daemon_stdout_sha256": hashlib.sha256(result.stdout.encode()).hexdigest(),
                "dispatch_calls": 0}

    def effectors(self) -> contract.RuntimeEffectors:
        return contract.RuntimeEffectors(
            canonical_candidate=self.canonical_candidate, build_wheel=self.build_wheel,
            create_venv=self.create_venv, install_wheel=self.install_wheel,
            configure_source=self.configure_source, initialize_daemon=self.initialize_daemon,
            configure_listener=self.configure_listener, install_service=self.install_service,
            readiness=self.readiness, uninstall_service=self.uninstall_service,
            runtime_census=self.runtime_census, unrelated_state=self.unrelated_state,
        )


def production_effectors(root: Path, *, repo_root: Path | None = None,
                         env: Mapping[str, str] | None = None) -> tuple[ProductionLocalAdapter, contract.RuntimeEffectors]:
    adapter = ProductionLocalAdapter(root, repo_root=repo_root, env=env)
    return adapter, adapter.effectors()
