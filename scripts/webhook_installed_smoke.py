#!/usr/bin/env python3
"""One-shot, explicitly armed installed webhook loopback qualification.

This runner is intentionally source-only and refuses by default.  ``--execute``
is for the separately authorized P53-C4 effect packet; unit tests exercise its
pre-effect safety mechanics without building a wheel or touching systemd.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SOURCE = "p53-c4-installed-canary"
HOST = "127.0.0.1"
PORT = 8820
UNIT = f"codex-wake-github-webhook-{SOURCE}.service"
MAX_COMMAND_SECONDS = 60


@dataclass(frozen=True)
class ExecutionContext:
    root: Path
    artifact_dir: Path
    wake_root: Path
    unit_path: Path
    fixture_dir: Path
    installed_cli: Path
    installed_listener: Path
    service_name: str


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def port_is_free() -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            probe.bind((HOST, PORT))
        except OSError:
            return False
    return True


def matching_processes() -> tuple[str, ...]:
    """Return only command-line identities, never process environments."""
    result = subprocess.run(
        ["ps", "-eo", "pid=,args="], text=True, capture_output=True,
        timeout=10, check=False,
    )
    return tuple(
        line.strip() for line in result.stdout.splitlines()
        if "codex-wake-github-webhook" in line or UNIT in line
    )


def run_command(
    argv: list[str], *, artifact_dir: Path, name: str, timeout: int = 60,
    env: dict[str, str] | None = None, allow_returncodes: tuple[int, ...] = (0,),
) -> subprocess.CompletedProcess[str]:
    """Run a bounded argv only; command output is deliberately not retained."""
    if not argv or any(not isinstance(item, str) or not item for item in argv):
        raise ValueError("command argv is invalid")
    if not isinstance(timeout, int) or not 1 <= timeout <= MAX_COMMAND_SECONDS:
        raise ValueError("command timeout is outside the declared bound")
    result = subprocess.run(argv, text=True, capture_output=True, timeout=timeout,
                            env=env, check=False)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    # Preserve only the non-sensitive command identity and result category.
    (artifact_dir / f"{name}.json").write_text(json.dumps({
        "argv": argv, "returncode": result.returncode,
    }, sort_keys=True) + "\n", encoding="utf-8")
    if result.returncode not in allow_returncodes:
        raise RuntimeError(f"{name} failed with exit code {result.returncode}")
    return result


def json_command(argv: list[str], *, context: ExecutionContext, name: str,
                 env: dict[str, str] | None = None,
                 allow_returncodes: tuple[int, ...] = (0,)) -> dict[str, Any]:
    result = run_command(argv, artifact_dir=context.artifact_dir, name=name, env=env,
                         allow_returncodes=allow_returncodes)
    try:
        value = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{name} did not emit JSON") from exc
    if not isinstance(value, dict):
        raise RuntimeError(f"{name} did not emit a JSON object")
    return value


def sanitize_receipt(value: Any, *, secrets: tuple[str, ...] = ()) -> Any:
    """Never publish payload bodies, env text, credential values, or secret-like keys."""
    if isinstance(value, dict):
        return {
            str(key): "[redacted]" if any(fragment in str(key).lower() for fragment in
                                           ("secret", "token", "payload", "environment", "body"))
            else sanitize_receipt(item, secrets=secrets)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [sanitize_receipt(item, secrets=secrets) for item in value]
    if isinstance(value, str):
        result = value
        for secret in secrets:
            if secret:
                result = result.replace(secret, "[redacted]")
        return result
    return value


def write_sitecustomize(directory: Path) -> Path:
    """Write the untracked provider fixture seam used only by the fresh venv."""
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "sitecustomize.py"
    path.write_text(
        "from datetime import UTC, datetime\n"
        "from codex_wake.github_polling import WorkflowRun\n"
        "import codex_wake.webhook_listener as listener\n"
        "class _FixtureClient:\n"
        "    def __init__(self, deadline): self.deadline = deadline\n"
        "    def get_run_attempt(self, repository, run_id, run_attempt):\n"
        "        return WorkflowRun(repository, 1, 1, run_id, run_attempt, 'refs/heads/main', 'a'*40, 'completed', 'success', None, datetime.now(UTC), 'github_attempt_started_or_job_completed_lower_bound')\n"
        "_original = listener.build_webhook_runtime\n"
        "def _fixture_runtime(**kwargs):\n"
        "    return _original(**kwargs, attempt_client_factory=_FixtureClient)\n"
        "listener.build_webhook_runtime = _fixture_runtime\n",
        encoding="utf-8",
    )
    os.chmod(path, 0o600)
    return path


def preflight(context: ExecutionContext) -> None:
    if context.unit_path.exists() or context.unit_path.is_symlink():
        raise RuntimeError(f"exact unit already exists: {context.unit_path}")
    if not port_is_free():
        raise RuntimeError(f"{HOST}:{PORT} is occupied")
    status = run_command(["systemctl", "--user", "is-system-running"],
                         artifact_dir=context.artifact_dir, name="user-manager",
                         allow_returncodes=(0, 1, 2, 3))
    if status.returncode == 1:
        raise RuntimeError("user systemd manager is unavailable")
    if matching_processes():
        raise RuntimeError("matching webhook process exists before install")


def installed_env(context: ExecutionContext) -> dict[str, str]:
    env = dict(os.environ)
    env["XDG_CONFIG_HOME"] = str(context.root / "xdg-config")
    env["XDG_STATE_HOME"] = str(context.root / "xdg-state")
    return env


def configure_and_arm(context: ExecutionContext, env: dict[str, str]) -> None:
    cli = str(context.installed_cli)
    common = [cli, "--wake-root", str(context.wake_root)]
    run_command(common + ["github-ci", "source", "configure", "--source", SOURCE,
                           "--repository", "CochranResearchGroup/codex-wake", "--repository-id", "1",
                           "--workflow-id", "1", "--ref", "refs/heads/main", "--conclusion", "success",
                           "--credential-ref", "CODEX_WAKE_GITHUB_TOKEN", "--enabled"],
                artifact_dir=context.artifact_dir, name="configure-source", env=env)
    run_command(common + ["github-ci", "completed", "--source", SOURCE, "--ref", "refs/heads/main",
                           "--conclusion", "success", "--idempotency-key", SOURCE, "--",
                           "installed webhook qualification; dispatch remains absent"],
                artifact_dir=context.artifact_dir, name="arm", env=env)
    run_command(common + ["github-webhook", "source", "configure", "--source", SOURCE,
                           "--bind-address", HOST, "--port", str(PORT),
                           "--secret-ref", "CODEX_WAKE_WEBHOOK_SECRET", "--enabled"],
                artifact_dir=context.artifact_dir, name="configure-webhook", env=env)
    environment_file = context.wake_root / "github" / "webhook.env"
    environment_file.parent.mkdir(parents=True, exist_ok=True)
    # This is the only fixture injection path.  The service inherits this
    # owner-only file through its rendered EnvironmentFile; the runner itself
    # never imports or installs the fixture.
    environment_file.write_text(
        "CODEX_WAKE_WEBHOOK_SECRET=fixture-only\n"
        "CODEX_WAKE_GITHUB_TOKEN=fixture-only\n"
        f"PYTHONPATH={context.fixture_dir}\n",
        encoding="utf-8",
    )
    os.chmod(environment_file, 0o600)


def signed_loopback_delivery(*, delivery: str) -> tuple[int, str]:
    """Send one bounded real HTTP request without retaining its raw body."""
    from datetime import UTC, datetime

    now = datetime.now(UTC).isoformat()
    body = json.dumps({
        "action": "completed",
        "repository": {"id": 1, "full_name": "CochranResearchGroup/codex-wake"},
        "workflow_run": {
            "id": 101, "run_attempt": 1, "workflow_id": 1, "head_branch": "main",
            "head_sha": "a" * 40, "status": "completed", "conclusion": "success",
            "updated_at": now,
        },
    }, separators=(",", ":")).encode("utf-8")
    signature = hmac.new(b"fixture-only", body, hashlib.sha256).hexdigest()
    request = (
        b"POST /github/webhook HTTP/1.1\r\nHost: 127.0.0.1\r\n"
        b"Content-Type: application/json\r\n"
        + f"Content-Length: {len(body)}\r\n".encode()
        + f"X-Hub-Signature-256: sha256={signature}\r\n".encode()
        + b"X-GitHub-Event: workflow_run\r\n"
        + f"X-GitHub-Delivery: {delivery}\r\n\r\n".encode()
        + body
    )
    with socket.create_connection((HOST, PORT), timeout=10) as connection:
        connection.sendall(request)
        response = bytearray()
        while True:
            chunk = connection.recv(4096)
            if not chunk:
                break
            response.extend(chunk)
    head, content = bytes(response).split(b"\r\n\r\n", 1)
    return int(head.split(b" ", 2)[1]), str(json.loads(content)["code"])


def provider_free_poll(context: ExecutionContext, env: dict[str, str]) -> dict[str, Any]:
    """Reconcile the armed source through a local fake, never the REST client."""
    code = """
import json
from datetime import UTC, datetime
from pathlib import Path
from codex_wake.daemon import default_signal_runners, poll_once, poll_result_dict
from codex_wake.github_polling import RunPage, WorkflowRun
from codex_wake.signal_records import signal_journal_path
from codex_wake.signal_store import SQLiteSignalModule
class Client:
    def list_runs(self, query):
        now = datetime.now(UTC)
        return RunPage((WorkflowRun('CochranResearchGroup/codex-wake', 1, 1, 101, 1, 'refs/heads/main', 'a'*40, 'completed', 'success', None, now, 'github_attempt_started_or_job_completed_lower_bound'),), None, None, None)
    def get_run_attempt(self, repository, run_id, run_attempt):
        now = datetime.now(UTC)
        return WorkflowRun(repository, 1, 1, run_id, run_attempt, 'refs/heads/main', 'a'*40, 'completed', 'success', None, now, 'github_attempt_started_or_job_completed_lower_bound')
root = Path(__import__('sys').argv[1])
module = SQLiteSignalModule.open_existing(signal_journal_path(root))
assert module is not None
runners = default_signal_runners(root, module, github_client_factory=lambda source: Client())
result = poll_once(root, dispatch=False, signal_runtime=module, signal_runners=runners)
print(json.dumps(poll_result_dict(result), sort_keys=True))
"""
    result = run_command([str(context.installed_cli.parent / "python"), "-c", code, str(context.wake_root)],
                         artifact_dir=context.artifact_dir, name="provider-free-poll", env=env)
    value = json.loads(result.stdout)
    if not isinstance(value, dict) or value.get("dispatched") != 0:
        raise RuntimeError("provider-free polling did not preserve dispatch absence")
    return value


def cleanup(context: ExecutionContext, *, service_attempted: bool = True) -> dict[str, bool]:
    """Cleanup is unconditional and retains no command output or secret material."""
    uninstall_attempted = service_attempted and context.installed_cli.is_file()
    uninstall_ok = False
    try:
        if uninstall_attempted:
            result = run_command([str(context.installed_cli), "--wake-root", str(context.wake_root),
                                  "github-webhook", "service", "uninstall", "--source", SOURCE],
                                 artifact_dir=context.artifact_dir, name="cleanup-uninstall",
                                 allow_returncodes=(0, 1, 2))
            uninstall_ok = result.returncode == 0
    except (OSError, RuntimeError, subprocess.SubprocessError):
        # Cleanup evidence remains useful even if an installed command becomes
        # unavailable after a failed setup; never retry the service attempt.
        uninstall_ok = False
    finally:
        if service_attempted:
            context.unit_path.unlink(missing_ok=True)
        (context.fixture_dir / "sitecustomize.py").unlink(missing_ok=True)
        shutil.rmtree(context.wake_root, ignore_errors=True)
    return {
        "service_uninstall_attempted": uninstall_attempted,
        "service_uninstall_ok": uninstall_ok,
        "unit_absent": not context.unit_path.exists(),
        "port_released": port_is_free(),
        "no_matching_process": not matching_processes(),
        "temporary_roots_removed": not context.wake_root.exists() and not (context.fixture_dir / "sitecustomize.py").exists(),
    }


def execute(*, receipt_path: Path | None = None) -> int:
    """Perform exactly one effect packet; every failure exits through cleanup."""
    with tempfile.TemporaryDirectory(prefix="codex-wake-p53-c4-") as temporary:
        root = Path(temporary)
        artifact_dir = root / "receipt"
        wheel_dir = root / "wheel"
        venv = root / "venv"
        fixture_dir = root / "fixture"
        wake_root = root / "wake"
        unit_path = Path.home() / ".config" / "systemd" / "user" / UNIT
        context = ExecutionContext(root, artifact_dir, wake_root, unit_path, fixture_dir,
                                   venv / "bin" / "codex-wake",
                                   venv / "bin" / "codex-wake-github-webhook", UNIT)
        receipt: dict[str, Any] = {"source": SOURCE, "loopback": f"{HOST}:{PORT}", "service": UNIT}
        service_attempted = False
        try:
            preflight(context)
            commit = run_command(["git", "-C", str(repo_root()), "rev-parse", "HEAD"],
                                 artifact_dir=artifact_dir, name="candidate-commit").stdout.strip()
            run_command([sys.executable, "-m", "build", "--wheel", "--outdir", str(wheel_dir)],
                        artifact_dir=artifact_dir, name="build-wheel", timeout=MAX_COMMAND_SECONDS,
                        env=dict(os.environ, PYTHONPATH=""))
            wheels = tuple(wheel_dir.glob("codex_wake-*.whl"))
            if len(wheels) != 1:
                raise RuntimeError("build did not produce exactly one wheel")
            run_command([sys.executable, "-m", "venv", str(venv)], artifact_dir=artifact_dir, name="create-venv")
            run_command([str(venv / "bin" / "pip"), "install", "--no-deps", str(wheels[0])],
                        artifact_dir=artifact_dir, name="install-wheel")
            if not context.installed_cli.is_file() or not context.installed_listener.is_file():
                raise RuntimeError("exact installed executables are missing")
            receipt.update({"candidate_commit": commit, "wheel_sha256": sha256(wheels[0]),
                            "installed_cli_sha256": sha256(context.installed_cli),
                            "installed_listener_sha256": sha256(context.installed_listener),
                            "interpreter": str(venv / "bin" / "python")})
            write_sitecustomize(fixture_dir)
            env = installed_env(context)
            configure_and_arm(context, env)
            # The one service attempt begins only after all build/configuration evidence above.
            service_attempted = True
            run_command([str(context.installed_cli), "--wake-root", str(wake_root), "github-webhook", "service", "install",
                         "--source", SOURCE, "--executable-path", str(context.installed_listener), "--unit-dir", str(unit_path.parent)],
                        artifact_dir=artifact_dir, name="install-and-start", env=env)
            readiness = json_command([str(context.installed_cli), "--wake-root", str(wake_root), "github-webhook", "readiness", "--source", SOURCE, "--json"], context=context, name="readiness", env=env)
            status = json_command([str(context.installed_cli), "--wake-root", str(wake_root), "github-webhook", "service", "status", "--source", SOURCE, "--unit-dir", str(unit_path.parent), "--json"], context=context, name="status", env=env)
            support = json_command([str(context.installed_cli), "--wake-root", str(wake_root), "github-webhook", "support", "--source", SOURCE, "--json"], context=context, name="support", env=env)
            if readiness.get("status") != "ready" or status.get("active") != "active":
                raise RuntimeError("installed service readiness/status is not ready")
            first = signed_loopback_delivery(delivery="p53-c4-first")
            duplicate = signed_loopback_delivery(delivery="p53-c4-first")
            run_command([str(context.installed_cli), "--wake-root", str(wake_root), "github-webhook", "service", "stop",
                         "--source", SOURCE, "--unit-dir", str(unit_path.parent)],
                        artifact_dir=artifact_dir, name="stop", env=env)
            run_command([str(context.installed_cli), "--wake-root", str(wake_root), "github-webhook", "service", "start",
                         "--source", SOURCE, "--unit-dir", str(unit_path.parent)],
                        artifact_dir=artifact_dir, name="restart", env=env)
            main_pid = run_command(["systemctl", "--user", "show", UNIT, "--property=MainPID", "--value"],
                                   artifact_dir=artifact_dir, name="post-restart-pid").stdout.strip()
            after_restart = signed_loopback_delivery(delivery="p53-c4-after-restart")
            poll = provider_free_poll(context, env)
            if (first, duplicate, after_restart) != ((200, "COMMITTED"), (200, "DUPLICATE"), (200, "DUPLICATE")):
                raise RuntimeError("signed loopback delivery did not preserve durable duplicate semantics")
            receipt.update({"readiness": readiness, "status": status, "support": support,
                            "first_delivery": first[1], "same_delivery": duplicate[1],
                            "post_restart_delivery": after_restart[1], "post_restart_main_pid": main_pid,
                            "polling": poll, "dispatch": "absent"})
        finally:
            receipt["cleanup"] = cleanup(context, service_attempted=service_attempted)
            sanitized = sanitize_receipt(receipt, secrets=("fixture-only",))
            if receipt_path is not None:
                receipt_path.parent.mkdir(parents=True, exist_ok=True)
                receipt_path.write_text(json.dumps(sanitized, sort_keys=True, indent=2) + "\n", encoding="utf-8")
            print(json.dumps(sanitized, sort_keys=True))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="perform the one separately authorized installed-service attempt")
    parser.add_argument("--receipt", type=Path, help="optional sanitized receipt output outside the temporary root")
    args = parser.parse_args(argv)
    if not args.execute:
        print("webhook installed smoke refuses by default; pass --execute only for the authorized one-shot effect packet", file=sys.stderr)
        return 2
    try:
        return execute(receipt_path=args.receipt)
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f"webhook installed smoke failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
