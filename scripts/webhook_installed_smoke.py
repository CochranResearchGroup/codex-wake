#!/usr/bin/env python3
"""One explicitly armed, fail-closed installed webhook qualification packet.

The source-only runner refuses by default. ``--execute`` belongs only to the
separately authorized P53-C4 effect packet. It never contacts GitHub or starts
the wake dispatcher.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import secrets
import shutil
import socket
import stat
import subprocess
import sys
import tarfile
import tempfile
import time
import uuid
import zipfile
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from ipaddress import ip_address
from pathlib import Path
from typing import Any, Callable

SOURCE = "p53-c4-installed-canary"
HOST = "127.0.0.1"
PORT = 8820
UNIT = f"codex-wake-github-webhook-{SOURCE}.service"
REPOSITORY = "CochranResearchGroup/codex-wake"
MAX_COMMAND_SECONDS = 60
READY_SECONDS = 20


@dataclass(frozen=True)
class Fixture:
    secret: str
    body: bytes
    delivery_id: str
    restart_delivery_id: str
    workflow: dict[str, object]


@dataclass(frozen=True)
class ExecutionContext:
    root: Path
    artifact_dir: Path
    wake_root: Path
    manager_unit_dir: Path
    fixture_dir: Path
    installed_cli: Path
    installed_listener: Path
    installed_python: Path
    service_name: str = UNIT

    @property
    def unit_path(self) -> Path:
        return self.manager_unit_dir / self.service_name

    @property
    def bootstrap_path(self) -> Path:
        return self.fixture_dir / "webhook-fixture-bootstrap"

    @property
    def reader_bootstrap_path(self) -> Path:
        return self.fixture_dir / "managed-reader-bootstrap"

    @property
    def log_path(self) -> Path:
        return self.root / "logs" / "webhook-listener.log"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def owner_only_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    os.chmod(path, 0o700)


def create_execution_root(env: dict[str, str] | None = None) -> Path:
    """Create an owner-only root visible to a PrivateTmp systemd service."""
    source = os.environ if env is None else env
    configured_state_home = source.get("XDG_STATE_HOME")
    state_home = (
        Path(configured_state_home).expanduser()
        if configured_state_home
        else Path.home() / ".local" / "state"
    )
    if not state_home.is_absolute():
        raise ValueError("XDG_STATE_HOME must be absolute")
    qualification_dir = (state_home / "codex-wake" / "qualification").resolve()
    private_tmp_roots = (Path("/tmp").resolve(), Path("/var/tmp").resolve())
    if any(
        qualification_dir == temporary
        or qualification_dir.is_relative_to(temporary)
        for temporary in private_tmp_roots
    ):
        raise ValueError("execution state must not resolve under a temporary directory")
    owner_only_directory(qualification_dir)
    root = Path(tempfile.mkdtemp(prefix="p53-c4-", dir=qualification_dir))
    os.chmod(root, 0o700)
    return root


def isolated_build_env() -> dict[str, str]:
    """Preserve tool discovery while excluding caller import injection."""
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONHOME", None)
    return env


def run_command(
    argv: list[str], *, artifact_dir: Path, name: str,
    timeout: int = MAX_COMMAND_SECONDS, env: dict[str, str] | None = None,
    cwd: Path | None = None, allow_returncodes: tuple[int, ...] = (0,),
) -> subprocess.CompletedProcess[str]:
    """Run one bounded argv and retain only argv plus its return category."""
    if not argv or any(type(value) is not str or not value for value in argv):
        raise ValueError("command argv is invalid")
    if type(timeout) is not int or not 1 <= timeout <= MAX_COMMAND_SECONDS:
        raise ValueError("command timeout is outside the declared bound")
    result = subprocess.run(
        argv, text=True, capture_output=True, check=False, timeout=timeout,
        env=env, cwd=cwd,
    )
    owner_only_directory(artifact_dir)
    (artifact_dir / f"{name}.json").write_text(
        json.dumps({"argv": argv, "returncode": result.returncode}, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if result.returncode not in allow_returncodes:
        raise RuntimeError(f"{name} failed with exit code {result.returncode}")
    return result


def json_command(
    argv: list[str], *, context: ExecutionContext, name: str,
    env: dict[str, str] | None = None, allow_returncodes: tuple[int, ...] = (0,),
) -> dict[str, Any]:
    result = run_command(
        argv, artifact_dir=context.artifact_dir, name=name, env=env,
        allow_returncodes=allow_returncodes,
    )
    try:
        value = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{name} did not emit JSON") from exc
    if type(value) is not dict:
        raise RuntimeError(f"{name} did not emit a JSON object")
    return value


def sanitize_receipt(value: Any, *, secret_values: tuple[str, ...] = ()) -> Any:
    hidden = ("secret", "token", "payload", "environment", "body", "fixture")
    if isinstance(value, dict):
        return {
            str(key): (
                "[redacted]" if any(part in str(key).lower() for part in hidden)
                else sanitize_receipt(item, secret_values=secret_values)
            )
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [sanitize_receipt(item, secret_values=secret_values) for item in value]
    if isinstance(value, str):
        for secret_value in secret_values:
            if secret_value:
                value = value.replace(secret_value, "[redacted]")
    return value


def stage_receipt(
    receipt: dict[str, Any], *, destination: Path | None,
    secret_values: tuple[str, ...],
) -> None:
    if destination is None:
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".tmp")
    temporary.write_text(
        json.dumps(sanitize_receipt(receipt, secret_values=secret_values),
                   sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    os.chmod(temporary, 0o600)
    temporary.replace(destination)


def make_fixture() -> Fixture:
    """Freeze one authoritative attempt after registration for both paths."""
    proof = datetime.now(UTC).isoformat()
    secret = secrets.token_urlsafe(32)
    workflow: dict[str, object] = {
        "repository": REPOSITORY, "repository_id": 1, "workflow_id": 1,
        "run_id": 101, "run_attempt": 1, "ref": "refs/heads/main",
        "head_sha": "a" * 40, "status": "completed", "conclusion": "success",
        "terminal_proof_at": proof, "source_instance": SOURCE,
    }
    body = json.dumps({
        "action": "completed",
        "repository": {"id": 1, "full_name": REPOSITORY},
        "workflow_run": {
            "id": 101, "run_attempt": 1, "workflow_id": 1,
            "head_branch": "main", "head_sha": workflow["head_sha"],
            "status": "completed", "conclusion": "success", "updated_at": proof,
        },
    }, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return Fixture(secret, body, str(uuid.uuid4()), str(uuid.uuid4()), workflow)


def manager_unit_dir(environment: dict[str, str] | None = None) -> Path:
    source = environment if environment is not None else os.environ
    configured = source.get("XDG_CONFIG_HOME")
    base = Path(configured).expanduser() if configured else Path.home() / ".config"
    return (base / "systemd" / "user").resolve()


def manager_failed_units(artifact_dir: Path, *, name: str) -> tuple[str, ...]:
    result = run_command(
        ["systemctl", "--user", "--failed", "--no-legend", "--plain"],
        artifact_dir=artifact_dir, name=name,
    )
    return tuple(sorted(line.split()[0] for line in result.stdout.splitlines() if line.split()))


def manager_preflight(context: ExecutionContext) -> tuple[str, tuple[str, ...]]:
    result = run_command(
        ["systemctl", "--user", "is-system-running"],
        artifact_dir=context.artifact_dir, name="manager-state",
        allow_returncodes=(0, 1),
    )
    state = result.stdout.strip()
    if (state, result.returncode) not in {("running", 0), ("degraded", 1)}:
        raise RuntimeError("user systemd manager is unreachable")
    return state, manager_failed_units(context.artifact_dir, name="failed-units-before")


def port_is_free() -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        try:
            probe.bind((HOST, PORT))
        except OSError:
            return False
    return True


def _process_start_identity(path: Path) -> str:
    text = path.read_text(encoding="ascii")
    _, separator, remainder = text.rpartition(")")
    fields = remainder.split()
    if not separator or len(fields) < 20 or not fields[19].isdigit():
        raise RuntimeError("process start identity is invalid")
    return fields[19]


def matching_processes(
    context: ExecutionContext, *,
    tracked_identities: tuple[tuple[int, str], ...] = (),
    proc_root: Path = Path("/proc"),
) -> tuple[dict[str, str], ...]:
    """Find only this packet's exact bootstrap or already observed processes.

    A missing process during enumeration is a normal race. Any other census
    failure is unsafe because absence could not be proved.
    """
    tracked = {(int(pid), str(start)) for pid, start in tracked_identities}
    matches: list[dict[str, str]] = []
    try:
        entries = tuple(proc_root.iterdir())
    except OSError as exc:
        raise RuntimeError("listener process census is unavailable") from exc
    for entry in entries:
        if not entry.name.isdigit():
            continue
        pid = int(entry.name)
        try:
            arguments = tuple(
                value.decode("utf-8")
                for value in (entry / "cmdline").read_bytes().split(b"\0")
                if value
            )
            start = _process_start_identity(entry / "stat")
        except FileNotFoundError:
            continue
        except (OSError, UnicodeError, RuntimeError) as exc:
            raise RuntimeError("listener process census is incomplete") from exc
        exact = (
            len(arguments) >= 2
            and arguments[1] == str(context.bootstrap_path)
            and "--wake-root" in arguments
            and arguments.index("--wake-root") + 1 < len(arguments)
            and arguments[arguments.index("--wake-root") + 1] == str(context.wake_root)
            and "--source" in arguments
            and arguments.index("--source") + 1 < len(arguments)
            and arguments[arguments.index("--source") + 1] == SOURCE
        )
        reader_exact = (
            len(arguments) >= 2
            and arguments[0] == str(context.installed_python)
            and arguments[1] == str(context.reader_bootstrap_path)
            and "--wake-root" in arguments
            and arguments.index("--wake-root") + 1 < len(arguments)
            and arguments[arguments.index("--wake-root") + 1] == str(context.wake_root)
            and "--no-dispatch" in arguments
        )
        tracked_match = (pid, start) in tracked
        if exact or reader_exact or tracked_match:
            matches.append({
                "pid": str(pid),
                "process_start_ticks": start,
                "reason": (
                    "exact_bootstrap_argv" if exact
                    else "exact_reader_argv" if reader_exact
                    else "tracked_pid_start"
                ),
            })
    return tuple(sorted(matches, key=lambda item: int(item["pid"])))


def clean_candidate(root: Path, artifact_dir: Path) -> dict[str, str]:
    status = run_command(
        ["git", "-C", str(root), "status", "--porcelain"],
        artifact_dir=artifact_dir, name="candidate-status",
    )
    if status.stdout.strip():
        raise RuntimeError("candidate worktree is not clean")
    commit = run_command(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        artifact_dir=artifact_dir, name="candidate-commit",
    ).stdout.strip()
    tree = run_command(
        ["git", "-C", str(root), "rev-parse", "HEAD^{tree}"],
        artifact_dir=artifact_dir, name="candidate-tree",
    ).stdout.strip()
    if len(commit) != 40 or len(tree) != 40:
        raise RuntimeError("candidate Git identity is invalid")
    return {"commit": commit, "tree": tree}


def export_clean_tree(root: Path, destination: Path, artifact_dir: Path) -> None:
    result = subprocess.run(
        ["git", "-C", str(root), "archive", "--format=tar", "HEAD"],
        capture_output=True, check=False, timeout=MAX_COMMAND_SECONDS,
    )
    owner_only_directory(artifact_dir)
    (artifact_dir / "candidate-export.json").write_text(
        json.dumps({"argv": ["git", "archive", "HEAD"],
                    "returncode": result.returncode}) + "\n",
        encoding="utf-8",
    )
    if result.returncode != 0:
        raise RuntimeError("candidate export failed")
    destination.mkdir(parents=True, exist_ok=False)
    with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as handle:
        handle.write(result.stdout)
        archive_path = Path(handle.name)
    try:
        with tarfile.open(archive_path) as archive:
            base = destination.resolve()
            if any(not (destination / member.name).resolve().is_relative_to(base)
                   for member in archive.getmembers()):
                raise RuntimeError("candidate export contains an unsafe path")
            archive.extractall(destination, filter="data")
    finally:
        archive_path.unlink(missing_ok=True)


def build_wheel(export_root: Path, wheel_dir: Path, artifact_dir: Path) -> Path:
    uv = shutil.which("uv")
    if uv is None:
        raise RuntimeError("uv is required because python -m build is unavailable")
    wheel_dir.mkdir(parents=True, exist_ok=False)
    run_command(
        [uv, "build", "--wheel", "--out-dir", str(wheel_dir)],
        artifact_dir=artifact_dir, name="build-wheel", cwd=export_root,
        env=isolated_build_env(),
    )
    wheels = tuple(wheel_dir.glob("codex_wake-*.whl"))
    if len(wheels) != 1:
        raise RuntimeError("candidate export did not produce exactly one wheel")
    with zipfile.ZipFile(wheels[0]) as archive:
        names = archive.namelist()
    if any("sitecustomize" in name or "webhook_installed_smoke" in name for name in names):
        raise RuntimeError("wheel contains qualification fixture or runner material")
    return wheels[0]


def installed_provenance(context: ExecutionContext, env: dict[str, str]) -> dict[str, str]:
    code = (
        "import hashlib,importlib.metadata,json,pathlib,codex_wake,sys;"
        "p=pathlib.Path(codex_wake.__file__).resolve();"
        "print(json.dumps({'module':str(p),'module_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),"
        "'version':importlib.metadata.version('codex-wake'),'interpreter':str(pathlib.Path(sys.executable).resolve())}))"
    )
    result = run_command(
        [str(context.installed_python), "-I", "-c", code],
        artifact_dir=context.artifact_dir, name="installed-provenance", env=env,
    )
    try:
        value = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("installed provenance is invalid") from exc
    required = {"module", "module_sha256", "version", "interpreter"}
    if type(value) is not dict or set(value) != required:
        raise RuntimeError("installed provenance is incomplete")
    module = Path(str(value["module"]))
    if not module.is_relative_to(context.root / "venv"):
        raise RuntimeError("installed module escaped the isolated environment")
    return {key: str(item) for key, item in value.items()}


def write_fixture_bootstrap(
    context: ExecutionContext, fixture: Fixture, *,
    counter_path: Path | None = None,
) -> Path:
    """Create an explicit bootstrap that must succeed before the entrypoint."""
    owner_only_directory(context.fixture_dir)
    module_path = context.fixture_dir / "webhook_fixture_bootstrap.py"
    workflow_json = json.dumps(fixture.workflow, sort_keys=True)
    counter_expression = (
        f"Path({str(counter_path)!r})" if counter_path is not None else "None"
    )
    module_path.write_text(
        "import os\n"
        "import json\n"
        "from datetime import datetime\n"
        "from pathlib import Path\n"
        "_installed = False\n"
        f"_workflow = json.loads({workflow_json!r})\n"
        f"_tripwire = Path({str(context.fixture_dir / 'tripwire')!r})\n"
        f"_counter = {counter_expression}\n"
        "def _increment_counter(name):\n"
        "    if _counter is None: return\n"
        "    value = json.loads(_counter.read_text(encoding='utf-8'))\n"
        "    value[name] += 1\n"
        "    _counter.write_text(json.dumps(value, sort_keys=True) + '\\n', encoding='utf-8')\n"
        "    os.chmod(_counter, 0o600)\n"
        "def _count_fixture_read(): _increment_counter('authoritative_attempt_reads')\n"
        "def _blocked_production_provider_factory(*args, **kwargs):\n"
        "    _increment_counter('production_provider_factory_calls')\n"
        "    raise RuntimeError('production provider factory is forbidden in the provider-free fixture')\n"
        "def install():\n"
        "    global _installed\n"
        "    import codex_wake.webhook_listener as listener\n"
        "    from codex_wake.github_polling import WorkflowRun\n"
        "    original = listener.build_webhook_runtime\n"
        "    if not callable(original): raise RuntimeError('installed runtime seam is unavailable')\n"
        "    listener.GitHubRestClient = _blocked_production_provider_factory\n"
        "    class FixtureClient:\n"
        "        def __init__(self, deadline): self.deadline = deadline\n"
        "        def get_run_attempt(self, repository, run_id, run_attempt):\n"
        "            _count_fixture_read()\n"
        "            value = _workflow\n"
        "            if (repository, run_id, run_attempt) != (value['repository'], value['run_id'], value['run_attempt']): raise RuntimeError('unexpected provider identity')\n"
        "            return WorkflowRun(value['repository'], value['repository_id'], value['workflow_id'], value['run_id'], value['run_attempt'], value['ref'], value['head_sha'], value['status'], value['conclusion'], None, datetime.fromisoformat(value['terminal_proof_at']), 'github_attempt_started_or_job_completed_lower_bound')\n"
        "    def patched(**kwargs):\n"
        "        if 'attempt_client_factory' in kwargs: raise RuntimeError('provider seam already supplied')\n"
        "        return original(**kwargs, attempt_client_factory=FixtureClient)\n"
        "    listener.build_webhook_runtime = patched\n"
        "    _installed = True\n"
        "    _tripwire.write_text('ready', encoding='ascii')\n"
        "def assert_installed():\n"
        "    if not _installed or _tripwire.read_text(encoding='ascii') != 'ready': raise RuntimeError('fixture bootstrap did not install')\n",
        encoding="utf-8",
    )
    os.chmod(module_path, 0o600)
    context.bootstrap_path.write_text(
        f"#!{context.installed_python}\n"
        "import runpy, sys\n"
        "import webhook_fixture_bootstrap as fixture\n"
        "fixture.install()\n"
        "fixture.assert_installed()\n"
        f"sys.argv[0] = {str(context.installed_listener)!r}\n"
        f"runpy.run_path({str(context.installed_listener)!r}, run_name='__main__')\n",
        encoding="utf-8",
    )
    os.chmod(context.bootstrap_path, 0o700)
    return context.bootstrap_path


def installed_env(context: ExecutionContext) -> dict[str, str]:
    env = dict(os.environ)
    # Do not redirect XDG_CONFIG_HOME: all lifecycle commands must address the
    # same real user-manager namespace. Isolate application state separately.
    env["XDG_STATE_HOME"] = str(context.root / "state")
    env["PYTHONPATH"] = str(context.fixture_dir)
    return env


@contextmanager
def managed_reader(
    context: ExecutionContext, env: dict[str, str], *,
    checkpoint: Callable[[str, dict[str, Any]], None] = lambda _stage, _value: None,
    tracked_identities: list[tuple[int, str]] | None = None,
):
    """Hold one installed no-dispatch reader active only while arming."""
    owner_only_directory(context.artifact_dir)
    owner_only_directory(context.root / "state")
    bootstrap = write_managed_reader_bootstrap(context)
    stdout_path = context.artifact_dir / "managed-reader.stdout"
    stderr_path = context.artifact_dir / "managed-reader.stderr"
    argv = [
        str(context.installed_python), str(bootstrap),
        "--wake-root", str(context.wake_root),
        "--interval", "60", "--no-dispatch",
    ]
    with stdout_path.open("w", encoding="utf-8") as stdout, stderr_path.open(
        "w", encoding="utf-8",
    ) as stderr:
        process = subprocess.Popen(
            argv, text=True, stdout=stdout, stderr=stderr, env=env,
            start_new_session=True,
        )
        evidence: dict[str, Any] | None = None
        try:
            process_start = _process_start_identity(Path("/proc") / str(process.pid) / "stat")
            if tracked_identities is not None:
                tracked_identities.append((process.pid, process_start))
            deadline = time.monotonic() + READY_SECONDS
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise RuntimeError("installed managed reader exited before readiness")
                readiness = json_command(
                    [str(context.installed_cli), "--wake-root", str(context.wake_root),
                     "monitor", "check", "--json"],
                    context=context, name="managed-reader-readiness", env=env,
                    allow_returncodes=(0, 1),
                )
                health = readiness.get("health")
                if (
                    readiness.get("monitor_ready") is True
                    and readiness.get("monitor_source") == "codex-waked"
                    and type(health) is dict
                    and health.get("pid") == process.pid
                    and health.get("mode") == "loop"
                    and health.get("recent") is True
                    and health.get("persistent") is True
                ):
                    evidence = {
                        "pid": process.pid,
                        "process_start_ticks": process_start,
                        "mode": "loop",
                        "dispatch": "disabled",
                        "signal_sources": "blocked_by_explicit_bootstrap",
                        "poll_interval_seconds": 60,
                    }
                    checkpoint("managed_reader_ready", evidence)
                    break
                time.sleep(0.1)
            if evidence is None:
                raise RuntimeError("installed managed reader did not become ready")
            yield evidence
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
            if process.poll() is None:
                raise RuntimeError("installed managed reader did not stop")
            if evidence is not None:
                evidence["stopped"] = True
                checkpoint("managed_reader_stopped", evidence)


def write_managed_reader_bootstrap(context: ExecutionContext) -> Path:
    """Create a fail-closed installed daemon bootstrap with no source runners."""
    owner_only_directory(context.fixture_dir)
    context.reader_bootstrap_path.write_text(
        f"#!{context.installed_python}\n"
        "import sys\n"
        "from codex_wake import daemon\n"
        "def no_signal_sources(*args, **kwargs): return ()\n"
        "daemon.default_signal_runners = no_signal_sources\n"
        "raise SystemExit(daemon.main(sys.argv[1:]))\n",
        encoding="utf-8",
    )
    os.chmod(context.reader_bootstrap_path, 0o700)
    return context.reader_bootstrap_path


def fixture_preflight(context: ExecutionContext, env: dict[str, str]) -> None:
    code = "import webhook_fixture_bootstrap as f; f.install(); f.assert_installed()"
    run_command(
        [str(context.installed_python), "-c", code],
        artifact_dir=context.artifact_dir, name="fixture-preflight", env=env,
    )
    tripwire = context.fixture_dir / "tripwire"
    if not tripwire.is_file() or tripwire.read_text(encoding="ascii") != "ready":
        raise RuntimeError("fixture seam was not active in the installed interpreter")


def configure_and_arm(
    context: ExecutionContext, env: dict[str, str], *,
    checkpoint: Callable[[str, dict[str, Any]], None] = lambda _stage, _value: None,
    tracked_identities: list[tuple[int, str]] | None = None,
) -> tuple[str, dict[str, Any]]:
    common = [str(context.installed_cli), "--wake-root", str(context.wake_root)]
    source_configuration = [
        "github-ci", "source", "configure", "--source", SOURCE,
        "--repository", REPOSITORY, "--repository-id", "1",
        "--workflow-id", "1", "--ref", "refs/heads/main",
        "--conclusion", "success", "--credential-ref",
        "CODEX_WAKE_GITHUB_TOKEN",
    ]
    run_command(
        common + source_configuration + ["--disabled"],
        artifact_dir=context.artifact_dir, name="configure-source-disabled", env=env,
    )
    with managed_reader(
        context, env, checkpoint=checkpoint,
        tracked_identities=tracked_identities,
    ) as reader:
        run_command(
            common + source_configuration + ["--enabled"],
            artifact_dir=context.artifact_dir, name="enable-source", env=env,
        )
        armed = run_command(
            common + [
                "github-ci", "completed", "--source", SOURCE, "--ref",
                "refs/heads/main", "--conclusion", "success", "--idempotency-key",
                SOURCE, "--", "installed qualification; dispatch disabled",
            ],
            artifact_dir=context.artifact_dir, name="arm", env=env,
        )
        wake_id = armed.stdout.split(maxsplit=1)[0]
        if not wake_id.startswith("wake_"):
            raise RuntimeError("installed arm did not return a wake identity")
        checkpoint("armed", {"wake_id": wake_id, "configuration": "armed"})
    run_command(
        common + [
            "github-webhook", "source", "configure", "--source", SOURCE,
            "--bind-address", HOST, "--port", str(PORT), "--secret-ref",
            "CODEX_WAKE_WEBHOOK_SECRET", "--enabled",
        ],
        artifact_dir=context.artifact_dir, name="configure-webhook", env=env,
    )
    return wake_id, reader


def write_service_environment(context: ExecutionContext, fixture: Fixture) -> Path:
    path = context.wake_root / "github" / "webhook.env"
    owner_only_directory(path.parent)
    path.write_text(
        f"CODEX_WAKE_WEBHOOK_SECRET={fixture.secret}\n"
        "CODEX_WAKE_GITHUB_TOKEN=provider-disabled-by-explicit-bootstrap\n"
        f"PYTHONPATH={context.fixture_dir}\n",
        encoding="utf-8",
    )
    os.chmod(path, 0o600)
    return path


def service_command(
    context: ExecutionContext, action: str, *, env: dict[str, str], name: str,
    executable_path: Path | None = None,
    allow_returncodes: tuple[int, ...] = (0,),
) -> subprocess.CompletedProcess[str]:
    argv = [
        str(context.installed_cli), "--wake-root", str(context.wake_root),
        "github-webhook", "service", action, "--source", SOURCE,
        "--unit-dir", str(context.manager_unit_dir),
        "--log-path", str(context.log_path),
    ]
    if executable_path is not None:
        argv.extend(["--executable-path", str(executable_path)])
    return run_command(
        argv, artifact_dir=context.artifact_dir, name=name, env=env,
        allow_returncodes=allow_returncodes,
    )


def systemctl_value(context: ExecutionContext, property_name: str, *, name: str) -> str:
    return run_command(
        ["systemctl", "--user", "show", context.service_name,
         f"--property={property_name}", "--value"],
        artifact_dir=context.artifact_dir, name=name, allow_returncodes=(0, 1),
    ).stdout.strip()


def _decode_proc_address(value: str, *, ipv6: bool) -> str:
    packed = bytes.fromhex(value)
    if ipv6:
        packed = b"".join(
            packed[index:index + 4][::-1] for index in range(0, 16, 4)
        )
    else:
        packed = packed[::-1]
    return str(ip_address(packed))


def _socket_identity(pid: int, *, proc_root: Path = Path("/proc")) -> dict[str, str]:
    inodes: set[str] = set()
    for item in (proc_root / str(pid) / "fd").iterdir():
        try:
            target = os.readlink(item)
        except OSError:
            continue
        if target.startswith("socket:[") and target.endswith("]"):
            inodes.add(target[8:-1])
    listeners: list[dict[str, str]] = []
    for table, ipv6 in (("tcp", False), ("tcp6", True)):
        for line in (proc_root / "net" / table).read_text(encoding="utf-8").splitlines()[1:]:
            fields = line.split()
            if len(fields) < 10 or fields[3] != "0A" or fields[9] not in inodes:
                continue
            encoded_address, encoded_port = fields[1].split(":", 1)
            listeners.append({
                "address": _decode_proc_address(encoded_address, ipv6=ipv6),
                "port": str(int(encoded_port, 16)),
                "socket_inode": fields[9],
            })
    expected = [{"address": HOST, "port": str(PORT)}]
    actual = [
        {"address": item["address"], "port": item["port"]}
        for item in listeners
    ]
    if actual != expected:
        raise RuntimeError("service PID must own exactly the declared loopback listener")
    return listeners[0]


def service_identity(
    context: ExecutionContext, *, proc_root: Path = Path("/proc"),
) -> dict[str, Any]:
    values = {
        key: systemctl_value(context, prop, name=f"identity-{key}")
        for key, prop in (
            ("active", "ActiveState"), ("unit_state", "UnitFileState"),
            ("pid", "MainPID"), ("started", "ExecMainStartTimestampMonotonic"),
            ("exec_start", "ExecStart"), ("restarts", "NRestarts"),
        )
    }
    if (values["active"], values["unit_state"]) != ("active", "enabled"):
        raise RuntimeError("service is not active and enabled")
    if not values["pid"].isdigit() or int(values["pid"]) <= 0:
        raise RuntimeError("service MainPID is invalid")
    if values["restarts"] != "0":
        raise RuntimeError("service restarted automatically")
    pid = int(values["pid"])
    executable = (proc_root / str(pid) / "exe").resolve()
    if executable != context.installed_python.resolve():
        raise RuntimeError("service executable is outside the installed environment")
    arguments = tuple(
        value.decode("utf-8")
        for value in (proc_root / str(pid) / "cmdline").read_bytes().split(b"\0")
        if value
    )
    if not all(value in arguments for value in (
        str(context.bootstrap_path), "--wake-root", str(context.wake_root),
        "--source", SOURCE,
    )):
        raise RuntimeError("service command identity is invalid")
    process_start = _process_start_identity(proc_root / str(pid) / "stat")
    return {
        **values, "executable": str(executable), "process_start_ticks": process_start,
        "command": list(arguments), "socket": _socket_identity(pid, proc_root=proc_root),
    }


def assert_runtime_views(
    context: ExecutionContext, readiness: dict[str, Any], status: dict[str, Any],
    support: dict[str, Any],
) -> None:
    supported = support.get("webhook_listener")
    if (
        readiness.get("status") != "ready"
        or readiness.get("source_instance") != SOURCE
        or readiness.get("address") != HOST
        or readiness.get("port") != PORT
        or readiness.get("unit") != str(context.unit_path)
        or readiness.get("dispatch") != "not_included"
        or status.get("service") != UNIT
        or (status.get("active"), status.get("enabled")) != ("active", "enabled")
        or status.get("unit") != str(context.unit_path)
        or type(supported) is not dict
        or supported.get("status") != "ready"
        or supported.get("source_instance") != SOURCE
        or supported.get("unit") != str(context.unit_path)
    ):
        raise RuntimeError("installed readiness, status, and support disagree")


def wait_ready(
    context: ExecutionContext, env: dict[str, str], *,
    prior_identity: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    deadline = time.monotonic() + READY_SECONDS
    last_status: dict[str, Any] = {}
    while time.monotonic() < deadline:
        readiness = json_command(
            [str(context.installed_cli), "--wake-root", str(context.wake_root),
             "github-webhook", "readiness", "--source", SOURCE, "--json"],
            context=context, name="readiness", env=env, allow_returncodes=(0, 1),
        )
        last_status = json_command(
            [str(context.installed_cli), "--wake-root", str(context.wake_root),
             "github-webhook", "service", "status", "--source", SOURCE,
             "--unit-dir", str(context.manager_unit_dir), "--json"],
            context=context, name="service-status", env=env,
            allow_returncodes=(0, 1),
        )
        if last_status.get("active") == "failed":
            raise RuntimeError("installed service entered a terminal failure")
        restarts = systemctl_value(context, "NRestarts", name="readiness-restarts")
        if restarts not in {"", "0"}:
            raise RuntimeError("installed service restarted automatically")
        if readiness.get("status") == "ready":
            identity = service_identity(context)
            if prior_identity is not None and (
                identity["pid"] == prior_identity["pid"]
                or identity["process_start_ticks"] == prior_identity["process_start_ticks"]
            ):
                raise RuntimeError("manual restart did not create a new process identity")
            support = json_command(
                [str(context.installed_cli), "--wake-root", str(context.wake_root),
                 "github-webhook", "support", "--source", SOURCE, "--json"],
                context=context, name="support", env=env,
            )
            assert_runtime_views(context, readiness, last_status, support)
            return readiness, last_status, support, identity
        time.sleep(0.2)
    raise RuntimeError(
        f"installed service did not become ready: {last_status.get('active', 'unknown')}"
    )


def signed_loopback_delivery(fixture: Fixture, delivery_id: str) -> tuple[int, str]:
    signature = hmac.new(
        fixture.secret.encode("utf-8"), fixture.body, hashlib.sha256,
    ).hexdigest()
    request = (
        b"POST /github/webhook HTTP/1.1\r\nHost: 127.0.0.1\r\n"
        b"Content-Type: application/json\r\n"
        + f"Content-Length: {len(fixture.body)}\r\n".encode("ascii")
        + f"X-Hub-Signature-256: sha256={signature}\r\n".encode("ascii")
        + b"X-GitHub-Event: workflow_run\r\n"
        + f"X-GitHub-Delivery: {delivery_id}\r\n\r\n".encode("ascii")
        + fixture.body
    )
    with socket.create_connection((HOST, PORT), timeout=10) as connection:
        connection.sendall(request)
        response = bytearray()
        while chunk := connection.recv(4096):
            response.extend(chunk)
    head, content = bytes(response).split(b"\r\n\r\n", 1)
    return int(head.split(b" ", 2)[1]), str(json.loads(content)["code"])


def write_poll_fixture(context: ExecutionContext, fixture: Fixture, wake_id: str) -> Path:
    fixture_path = context.fixture_dir / "workflow.json"
    fixture_path.write_text(json.dumps(fixture.workflow, sort_keys=True), encoding="utf-8")
    os.chmod(fixture_path, 0o600)
    script = context.fixture_dir / "poll_fixture.py"
    script.write_text(
        "import json, sqlite3, sys\n"
        "from datetime import UTC, datetime\n"
        "from pathlib import Path\n"
        "from codex_wake.daemon import default_signal_runners, poll_once, poll_result_dict\n"
        "from codex_wake.github_polling import RunPage, WorkflowRun\n"
        "from codex_wake.signal_records import WakeRecordPublisher, current_reader_capability, signal_journal_path\n"
        "from codex_wake.signal_store import SQLiteSignalModule\n"
        "root, fixture_path, wake_id = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]\n"
        "data = json.loads(fixture_path.read_text(encoding='utf-8'))\n"
        "run = WorkflowRun(data['repository'], data['repository_id'], data['workflow_id'], data['run_id'], data['run_attempt'], data['ref'], data['head_sha'], data['status'], data['conclusion'], None, datetime.fromisoformat(data['terminal_proof_at']), 'github_attempt_started_or_job_completed_lower_bound')\n"
        "class Client:\n"
        "    def list_runs(self, query): return RunPage((run,), None, None, None)\n"
        "    def get_run_attempt(self, repository, run_id, run_attempt):\n"
        "        if (repository, run_id, run_attempt) != (run.repository, run.run_id, run.run_attempt): raise RuntimeError('unexpected identity')\n"
        "        return run\n"
        "def snapshot():\n"
        "    db = signal_journal_path(root)\n"
        "    with sqlite3.connect('file:' + str(db) + '?mode=ro', uri=True) as connection:\n"
        "        receipts = connection.execute(\"SELECT COUNT(*) FROM receipts WHERE source='github' AND source_instance=?\", (data['source_instance'],)).fetchone()[0]\n"
        "        matches = connection.execute('SELECT COUNT(*) FROM match_reservations WHERE wake_id=?', (wake_id,)).fetchone()[0]\n"
        "        arms = connection.execute('SELECT COUNT(*) FROM arms WHERE wake_id=?', (wake_id,)).fetchone()[0]\n"
        "    statuses = {name: int((root / name / (wake_id + '.json')).is_file()) for name in ('pending','firing','submitted','failed')}\n"
        "    return {'receipts': receipts, 'matches': matches, 'arms': arms, 'statuses': statuses}\n"
        "module = SQLiteSignalModule.open_existing(signal_journal_path(root), record_publisher=WakeRecordPublisher(root, current_reader_capability(root)))\n"
        "if module is None: raise RuntimeError('signal journal unavailable')\n"
        "before = snapshot()\n"
        "runners = default_signal_runners(root, module, github_client_factory=lambda source: Client())\n"
        "result = poll_result_dict(poll_once(root, now=datetime.now(UTC), dispatch=False, signal_runtime=module, signal_runners=runners))\n"
        "after = snapshot()\n"
        "print(json.dumps({'before': before, 'after': after, 'poll': result}, sort_keys=True))\n",
        encoding="utf-8",
    )
    os.chmod(script, 0o600)
    return script


def assert_poll_convergence(value: dict[str, Any]) -> None:
    before, after, poll = value.get("before"), value.get("after"), value.get("poll")
    if not all(type(item) is dict for item in (before, after, poll)):
        raise RuntimeError("polling convergence evidence is incomplete")
    sources = poll.get("signal_sources")
    expected_source = {
        "source": "github", "source_instance": SOURCE, "scope": "instance",
        "scanned": 1, "observed": 1, "degraded": 1,
        "code": "GITHUB_COVERAGE_UNPROVEN",
    }
    expected_before = {"pending": 1, "firing": 0, "submitted": 0, "failed": 0}
    expected_after = {"pending": 0, "firing": 1, "submitted": 0, "failed": 0}
    expected_poll = {
        "checked": 1, "fired": 1, "failed": 0, "pending": 0,
        "dispatched": 0, "submitted": 0, "requeued": 0,
    }
    if (
        type(sources) is not list or len(sources) != 1
        or any(sources[0].get(key) != expected for key, expected in expected_source.items())
        or (before.get("receipts"), after.get("receipts")) != (1, 1)
        or (before.get("arms"), after.get("arms")) != (1, 1)
        or (before.get("matches"), after.get("matches")) != (0, 1)
        or before.get("statuses") != expected_before
        or after.get("statuses") != expected_after
        or any(poll.get(key) != expected for key, expected in expected_poll.items())
    ):
        raise RuntimeError("polling convergence changed logical wake or dispatch state")


def provider_free_poll(
    context: ExecutionContext, env: dict[str, str], fixture: Fixture, wake_id: str,
) -> dict[str, Any]:
    script = write_poll_fixture(context, fixture, wake_id)
    result = run_command(
        [str(context.installed_python), str(script), str(context.wake_root),
         str(context.fixture_dir / "workflow.json"), wake_id],
        artifact_dir=context.artifact_dir, name="provider-free-poll", env=env,
    )
    try:
        value = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("provider-free poll evidence is invalid") from exc
    if type(value) is not dict:
        raise RuntimeError("provider-free poll evidence is incomplete")
    assert_poll_convergence(value)
    return value


def inactive_service_state(context: ExecutionContext) -> dict[str, str]:
    active = run_command(
        ["systemctl", "--user", "is-active", context.service_name],
        artifact_dir=context.artifact_dir, name="cleanup-active",
        allow_returncodes=(0, 1, 2, 3, 4),
    ).stdout.strip() or "unknown"
    observed_enabled = run_command(
        ["systemctl", "--user", "is-enabled", context.service_name],
        artifact_dir=context.artifact_dir, name="cleanup-enabled",
        allow_returncodes=(0, 1, 2, 3, 4),
    ).stdout.strip() or "unknown"
    pid = systemctl_value(context, "MainPID", name="cleanup-pid") or "0"
    enabled = "disabled" if observed_enabled in {"disabled", "not-found"} else observed_enabled
    return {
        "active": active, "enabled": enabled,
        "enabled_observed": observed_enabled, "pid": pid,
    }


def cleanup(
    context: ExecutionContext, *, env: dict[str, str], service_attempted: bool,
    failed_units_before: tuple[str, ...] | None,
    tracked_identities: tuple[tuple[int, str], ...] = (),
    preserve_root_on_safe: bool = False,
) -> dict[str, Any]:
    """Use product cleanup once; preserve the private root on uncertainty."""
    result: dict[str, Any] = {
        "service_attempted": service_attempted,
        "service_uninstall_attempted": False,
        "safe": False,
    }
    if not service_attempted:
        try:
            matches = matching_processes(
                context, tracked_identities=tracked_identities,
            )
        except RuntimeError as exc:
            result.update({
                "cleanup_error": type(exc).__name__,
                "recovery_root": str(context.root),
            })
            return result
        unit_absent = not context.unit_path.exists() and not context.unit_path.is_symlink()
        port_released = port_is_free()
        no_process = not matches
        safe = unit_absent and port_released and no_process
        result.update({
            "unit_absent": unit_absent, "port_released": port_released,
            "no_matching_process": no_process, "safe": safe,
        })
        if safe and not preserve_root_on_safe:
            shutil.rmtree(context.root)
            result["temporary_roots_removed"] = not context.root.exists()
        elif safe:
            os.chmod(context.root, stat.S_IRWXU)
            result.update({
                "temporary_roots_removed": False,
                "evidence_root_retained": True,
                "recovery_root": str(context.root),
            })
        else:
            result["recovery_root"] = str(context.root)
        return result

    result["service_uninstall_attempted"] = True
    try:
        command = service_command(
            context, "uninstall", env=env, name="cleanup-uninstall",
            allow_returncodes=(0, 1, 2),
        )
        state = inactive_service_state(context)
        failed_units_after = manager_failed_units(
            context.artifact_dir, name="failed-units-after",
        )
        unit_absent = not context.unit_path.exists() and not context.unit_path.is_symlink()
        matches = matching_processes(
            context, tracked_identities=tracked_identities,
        )
        no_process = not matches
        port_released = port_is_free()
        failed_unchanged = (
            failed_units_before is not None and failed_units_after == failed_units_before
        )
        safe = (
            command.returncode == 0 and unit_absent
            and state["active"] == "inactive" and state["enabled"] == "disabled"
            and state["pid"] == "0" and no_process and port_released
            and failed_unchanged
        )
        result.update({
            "uninstall_returncode": command.returncode, "state": state,
            "unit_absent": unit_absent, "no_matching_process": no_process,
            "port_released": port_released,
            "failed_units_before": list(failed_units_before or ()),
            "failed_units_after": list(failed_units_after),
            "failed_units_delta": sorted(
                set(failed_units_after) ^ set(failed_units_before or ())
            ),
            "failed_units_unchanged": failed_unchanged, "safe": safe,
        })
    except Exception as exc:
        safe = False
        result["cleanup_error"] = type(exc).__name__
    if safe and not preserve_root_on_safe:
        shutil.rmtree(context.root)
        result["temporary_roots_removed"] = not context.root.exists()
    elif safe:
        os.chmod(context.root, stat.S_IRWXU)
        result.update({
            "temporary_roots_removed": False,
            "evidence_root_retained": True,
            "recovery_root": str(context.root),
        })
    else:
        # Never unlink a unit or recursively remove evidence after a failed or
        # unproved product stop/uninstall.
        os.chmod(context.root, stat.S_IRWXU)
        result["recovery_root"] = str(context.root)
    return result


def execute(*, receipt_path: Path | None = None) -> int:
    root = create_execution_root()
    context = ExecutionContext(
        root=root, artifact_dir=root / "evidence", wake_root=root / "wake",
        manager_unit_dir=manager_unit_dir(), fixture_dir=root / "fixture",
        installed_cli=root / "venv/bin/codex-wake",
        installed_listener=root / "venv/bin/codex-wake-github-webhook",
        installed_python=root / "venv/bin/python",
    )
    if receipt_path is not None and receipt_path.resolve().is_relative_to(root.resolve()):
        raise ValueError("receipt path must be outside the disposable execution root")
    env = installed_env(context)
    fixture: Fixture | None = None
    service_attempted = False
    tracked_identities: list[tuple[int, str]] = []
    failed_units_before: tuple[str, ...] | None = None
    receipt: dict[str, Any] = {
        "source": SOURCE, "unit": UNIT,
        "manager_unit_dir": str(context.manager_unit_dir),
        "loopback": f"{HOST}:{PORT}", "overall": "failed",
        "dispatch": "absent", "provider_access": "absent",
    }
    stage_receipt(receipt, destination=receipt_path, secret_values=())
    try:
        manager_state, failed_units_before = manager_preflight(context)
        if context.unit_path.exists() or context.unit_path.is_symlink():
            raise RuntimeError("exact service unit already exists")
        if not port_is_free():
            raise RuntimeError("exact loopback port is occupied")
        if matching_processes(context):
            raise RuntimeError("matching listener process already exists")
        receipt.update({
            "manager_state": manager_state,
            "failed_units_before": list(failed_units_before), "preflight": "accepted",
        })
        stage_receipt(receipt, destination=receipt_path, secret_values=())

        receipt["setup_stage"] = "clean_candidate"
        stage_receipt(receipt, destination=receipt_path, secret_values=())
        provenance = clean_candidate(repo_root(), context.artifact_dir)
        export_root = root / "export"
        export_clean_tree(repo_root(), export_root, context.artifact_dir)
        receipt["setup_stage"] = "build_wheel"
        stage_receipt(receipt, destination=receipt_path, secret_values=())
        wheel = build_wheel(export_root, root / "wheel", context.artifact_dir)
        build_env = isolated_build_env()
        receipt["setup_stage"] = "install_wheel"
        stage_receipt(receipt, destination=receipt_path, secret_values=())
        run_command(
            [sys.executable, "-m", "venv", str(root / "venv")],
            artifact_dir=context.artifact_dir, name="create-venv", env=build_env,
        )
        run_command(
            [str(root / "venv/bin/pip"), "install", "--no-deps", str(wheel)],
            artifact_dir=context.artifact_dir, name="install-wheel", env=build_env,
        )
        if not all(path.is_file() for path in (
            context.installed_cli, context.installed_listener, context.installed_python,
        )):
            raise RuntimeError("installed executables are incomplete")
        receipt["setup_stage"] = "installed_provenance"
        stage_receipt(receipt, destination=receipt_path, secret_values=())
        provenance.update({
            "wheel_sha256": sha256(wheel),
            "installed_cli_sha256": sha256(context.installed_cli),
            "installed_listener_sha256": sha256(context.installed_listener),
            **installed_provenance(context, env),
        })
        receipt["provenance"] = provenance
        stage_receipt(receipt, destination=receipt_path, secret_values=())

        receipt["setup_stage"] = "configure_and_arm"
        stage_receipt(receipt, destination=receipt_path, secret_values=())

        def setup_checkpoint(stage: str, value: dict[str, Any]) -> None:
            receipt["setup_stage"] = stage
            if stage.startswith("managed_reader"):
                receipt["managed_reader"] = dict(value)
            else:
                receipt.update(value)
            stage_receipt(receipt, destination=receipt_path, secret_values=())

        wake_id, reader = configure_and_arm(
            context, env, checkpoint=setup_checkpoint,
            tracked_identities=tracked_identities,
        )
        fixture = make_fixture()
        write_fixture_bootstrap(context, fixture)
        fixture_preflight(context, env)
        write_service_environment(context, fixture)
        receipt.update({
            "wake_id": wake_id, "configuration": "armed",
            "managed_reader": reader, "setup_stage": "service_ready_to_attempt",
            "service_attempts": 0,
        })
        stage_receipt(
            receipt, destination=receipt_path, secret_values=(fixture.secret,),
        )

        receipt.update({
            "effect_stage": "service_install_start", "service_attempts": 1,
        })
        service_attempted = True
        stage_receipt(
            receipt, destination=receipt_path, secret_values=(fixture.secret,),
        )
        service_command(
            context, "install", env=env, name="install-start",
            executable_path=context.bootstrap_path,
        )
        receipt["effect_stage"] = "service_install_returned"
        stage_receipt(
            receipt, destination=receipt_path, secret_values=(fixture.secret,),
        )
        if not context.unit_path.is_file() or context.unit_path.is_symlink():
            raise RuntimeError("installed unit ownership is invalid")
        receipt["unit_sha256"] = sha256(context.unit_path)
        receipt["effect_stage"] = "service_readiness"
        stage_receipt(
            receipt, destination=receipt_path, secret_values=(fixture.secret,),
        )
        readiness, status, support, initial = wait_ready(context, env)
        tracked_identities.append((int(initial["pid"]), initial["process_start_ticks"]))
        receipt.update({
            "effect_stage": "service_ready",
            "configuration_identity": {
                "source": SOURCE, "wake_id": wake_id,
                "unit": str(context.unit_path), "log": str(context.log_path),
                "address": HOST, "port": PORT,
            },
            "readiness": readiness, "status": status, "support": support,
            "initial_service": initial, "deliveries": [],
        })
        stage_receipt(
            receipt, destination=receipt_path, secret_values=(fixture.secret,),
        )

        receipt["effect_stage"] = "first_delivery"
        stage_receipt(
            receipt, destination=receipt_path, secret_values=(fixture.secret,),
        )
        first = signed_loopback_delivery(fixture, fixture.delivery_id)
        receipt["deliveries"].append({"status": first[0], "code": first[1]})
        stage_receipt(
            receipt, destination=receipt_path, secret_values=(fixture.secret,),
        )
        if first != (200, "COMMITTED"):
            raise RuntimeError("first signed delivery did not commit")

        receipt["effect_stage"] = "delivery_replay"
        stage_receipt(
            receipt, destination=receipt_path, secret_values=(fixture.secret,),
        )
        same_delivery = signed_loopback_delivery(fixture, fixture.delivery_id)
        receipt["deliveries"].append({
            "status": same_delivery[0], "code": same_delivery[1],
        })
        stage_receipt(
            receipt, destination=receipt_path, secret_values=(fixture.secret,),
        )
        if same_delivery != (200, "DUPLICATE"):
            raise RuntimeError("same delivery replay was not duplicate")

        receipt["effect_stage"] = "manual_restart"
        stage_receipt(
            receipt, destination=receipt_path, secret_values=(fixture.secret,),
        )
        service_command(context, "stop", env=env, name="manual-stop")
        service_command(context, "start", env=env, name="manual-start")
        _, _, _, restarted = wait_ready(context, env, prior_identity=initial)
        tracked_identities.append((int(restarted["pid"]), restarted["process_start_ticks"]))
        receipt["restarted_service"] = restarted
        stage_receipt(
            receipt, destination=receipt_path, secret_values=(fixture.secret,),
        )

        receipt["effect_stage"] = "post_restart_delivery"
        stage_receipt(
            receipt, destination=receipt_path, secret_values=(fixture.secret,),
        )
        after_restart = signed_loopback_delivery(fixture, fixture.restart_delivery_id)
        receipt["deliveries"].append({
            "status": after_restart[0], "code": after_restart[1],
        })
        stage_receipt(
            receipt, destination=receipt_path, secret_values=(fixture.secret,),
        )
        if after_restart != (200, "DUPLICATE"):
            raise RuntimeError("post-restart occurrence replay was not duplicate")

        receipt["effect_stage"] = "provider_free_poll"
        stage_receipt(
            receipt, destination=receipt_path, secret_values=(fixture.secret,),
        )
        polling = provider_free_poll(context, env, fixture, wake_id)
        receipt.update({
            "effect_stage": "accepted", "polling": polling, "overall": "accepted",
        })
        stage_receipt(
            receipt, destination=receipt_path, secret_values=(fixture.secret,),
        )
    except Exception as exc:
        receipt["error"] = type(exc).__name__
    finally:
        secret_values = (fixture.secret,) if fixture is not None else ()
        receipt["cleanup"] = cleanup(
            context, env=env, service_attempted=service_attempted,
            failed_units_before=failed_units_before,
            tracked_identities=tuple(tracked_identities),
        )
        if receipt["overall"] != "accepted" or not receipt["cleanup"].get("safe"):
            receipt["overall"] = "failed"
        stage_receipt(
            receipt, destination=receipt_path, secret_values=secret_values,
        )
        print(json.dumps(
            sanitize_receipt(receipt, secret_values=secret_values), sort_keys=True,
        ))
    return 0 if receipt["overall"] == "accepted" else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args(argv)
    if not args.execute:
        print(
            "webhook installed smoke refuses by default; pass --execute only for the authorized one-shot packet",
            file=sys.stderr,
        )
        return 2
    return execute(receipt_path=args.receipt)


if __name__ == "__main__":
    raise SystemExit(main())
