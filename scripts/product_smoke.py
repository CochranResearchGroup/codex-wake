#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


TERMINAL_STATUSES = {"submitted", "failed", "expired", "cancelled"}


def utc_stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def resolve_command(raw: str) -> Path:
    if "/" in raw:
        path = Path(raw).expanduser()
        if not path.exists():
            raise SystemExit(f"command does not exist: {raw}")
        return path.resolve()
    found = shutil.which(raw)
    if not found:
        raise SystemExit(f"command was not found on PATH: {raw}")
    return Path(found).resolve()


def reject_source_tree_binary(path: Path, root: Path, *, allow_source: bool) -> None:
    if allow_source:
        return
    try:
        path.relative_to(root)
    except ValueError:
        return
    raise SystemExit(
        f"{path} is inside the source checkout; use an installed codex-wake binary "
        "or pass --allow-source for a source-tree smoke"
    )


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def command_text(args: list[str]) -> str:
    return " ".join(shlex.quote(item) for item in args)


def run_command(
    args: list[str],
    *,
    artifact_dir: Path,
    name: str,
    env: dict[str, str] | None = None,
    timeout: float = 60.0,
    allow_returncodes: tuple[int, ...] = (0,),
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        args, text=True, capture_output=True, env=env, cwd=cwd,
        timeout=timeout, check=False,
    )
    command_dir = artifact_dir / "commands"
    write_text(command_dir / f"{name}.cmd", command_text(args) + "\n")
    write_text(command_dir / f"{name}.stdout", result.stdout)
    write_text(command_dir / f"{name}.stderr", result.stderr)
    write_text(command_dir / f"{name}.returncode", f"{result.returncode}\n")
    if result.returncode not in allow_returncodes:
        raise SystemExit(
            f"{name} failed with exit code {result.returncode}; "
            f"see {command_dir / f'{name}.stderr'}"
        )
    return result


def run_json(
    args: list[str],
    *,
    artifact_dir: Path,
    name: str,
    env: dict[str, str] | None = None,
    timeout: float = 60.0,
    allow_returncodes: tuple[int, ...] = (0,),
    expect_object: bool = True,
    cwd: Path | None = None,
) -> Any:
    result = run_command(
        args,
        artifact_dir=artifact_dir,
        name=name,
        env=env,
        timeout=timeout,
        allow_returncodes=allow_returncodes,
        cwd=cwd,
    )
    try:
        payload = json.loads(result.stdout or "{}")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{name} did not emit valid JSON: {exc}") from exc
    if expect_object and not isinstance(payload, dict):
        raise SystemExit(f"{name} JSON output was not an object")
    write_json(artifact_dir / f"{name}.json", payload)
    return payload


def make_isolated_env(base: dict[str, str], artifact_dir: Path) -> dict[str, str]:
    env = dict(base)
    env["XDG_CONFIG_HOME"] = str(artifact_dir / "xdg-config")
    env["XDG_STATE_HOME"] = str(artifact_dir / "xdg-state")
    return env


def install_public_tag(tag: str, artifact_dir: Path) -> tuple[Path, Path, Path]:
    work = Path(tempfile.mkdtemp(prefix="codex-wake-public-tag-"))
    venv = work / "venv"
    install_log = artifact_dir / "public-tag-install.log"
    subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True)
    pip = venv / "bin" / "pip"
    package = f"git+https://github.com/CochranResearchGroup/codex-wake.git@{tag}"
    result = subprocess.run(
        [str(pip), "install", package],
        text=True,
        capture_output=True,
        check=False,
        timeout=240,
    )
    write_text(install_log, result.stdout + result.stderr)
    if result.returncode != 0:
        raise SystemExit(f"public tag install failed for {tag}; see {install_log}")
    return venv / "bin" / "codex-wake", venv / "bin" / "codex-waked", work


def parse_wake_id(output: str) -> str:
    first = output.strip().split()
    if not first:
        raise SystemExit("wake creation command did not print a wake id")
    return first[0]


def wait_for_wake(
    *,
    codex_wake: Path,
    wake_root: Path,
    wake_id: str,
    artifact_dir: Path,
    name: str,
    timeout_seconds: float,
    env: dict[str, str],
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    last: dict[str, Any] = {}
    while time.monotonic() < deadline:
        payload = run_json(
            [str(codex_wake), "--wake-root", str(wake_root), "show", wake_id],
            artifact_dir=artifact_dir,
            name=f"{name}-show",
            env=env,
            timeout=30,
        )
        last = payload
        status = str(payload.get("status") or "")
        if status in TERMINAL_STATUSES:
            write_json(artifact_dir / f"{name}-final.json", payload)
            return payload
        time.sleep(2)
    write_json(artifact_dir / f"{name}-timeout-last.json", last)
    raise SystemExit(f"{name} wake {wake_id} did not reach a terminal status within {timeout_seconds:g}s")


def run_surface_smoke(
    *,
    codex_wake: Path,
    codex_waked: Path,
    artifact_dir: Path,
    root: Path,
    source_env: dict[str, str],
    use_user_state: bool,
    upgrade_wheel: Path | None = None,
) -> dict[str, Any]:
    env = dict(source_env) if use_user_state else make_isolated_env(source_env, artifact_dir)
    surface_root = artifact_dir / "surface-wake"
    surface_registry = artifact_dir / "roots.d"
    surface_state = artifact_dir / "supervisor-state"
    surface_log = artifact_dir / "supervisor.log"
    summary: dict[str, Any] = {
        "surface_wake_root": str(surface_root),
        "isolated_state": not use_user_state,
    }

    run_command([str(codex_wake), "--version"], artifact_dir=artifact_dir, name="cli-version", env=env)
    schema = run_json(
        [str(codex_wake), "--wake-root", str(surface_root), "schema", "--json"],
        artifact_dir=artifact_dir,
        name="schema",
        env=env,
    )
    if not schema.get("schema_version"):
        raise SystemExit("schema smoke did not report a schema_version")
    summary["schema_version"] = schema.get("schema_version")

    readiness = run_json(
        [
            str(codex_wake),
            "--wake-root",
            str(surface_root),
            "product-readiness",
            "--json",
            "--repo-root",
            str(root),
            "--registry-dir",
            str(surface_registry),
            "--state-dir",
            str(surface_state),
            "--supervisor-log-path",
            str(surface_log),
            "--openclaw-timeout",
            "5",
        ],
        artifact_dir=artifact_dir,
        name="product-readiness",
        env=env,
        timeout=45,
    )
    cli = readiness.get("checks", {}).get("cli", {}) if isinstance(readiness.get("checks"), dict) else {}
    version = cli.get("version")
    if not version:
        raise SystemExit("product-readiness smoke did not report a CLI version")
    summary["cli_version"] = version
    summary["product_readiness_overall"] = readiness.get("overall_status")

    run_command(
        [str(codex_waked), "--wake-root", str(surface_root), "--once", "--no-dispatch"],
        artifact_dir=artifact_dir,
        name="codex-waked-once-no-dispatch",
        env=env,
    )
    monitor = run_json(
        [str(codex_wake), "--wake-root", str(surface_root), "monitor", "check", "--json"],
        artifact_dir=artifact_dir,
        name="monitor-check",
        env=env,
        allow_returncodes=(0, 1),
    )
    summary["monitor_ready"] = bool(monitor.get("monitor_ready"))

    run_command(
        [
            str(codex_wake),
            "supervisor",
            "enroll",
            "--wake-root",
            str(surface_root),
            "--repo-root",
            str(root),
            "--registry-dir",
            str(surface_registry),
            "--state-dir",
            str(surface_state),
            "--root-id",
            "product-smoke-surface",
        ],
        artifact_dir=artifact_dir,
        name="supervisor-enroll",
        env=env,
    )
    supervisor = run_json(
        [
            str(codex_wake),
            "supervisor",
            "run",
            "--once",
            "--no-dispatch",
            "--json",
            "--registry-dir",
            str(surface_registry),
            "--state-dir",
            str(surface_state),
        ],
        artifact_dir=artifact_dir,
        name="supervisor-run-once-no-dispatch",
        env=env,
        expect_object=False,
    )
    summary["supervisor_once_roots"] = len(supervisor) if isinstance(supervisor, list) else 0
    run_json(
        [str(codex_wake), "--wake-root", str(surface_root), "status", "--json"],
        artifact_dir=artifact_dir,
        name="status",
        env=env,
    )
    signal_env = dict(env)
    signal_env.update({"TMUX_PANE": "%smoke", "TMUX": "/tmp/codex-wake-smoke,1,0"})
    signal_work = artifact_dir / "signal-work"
    signal_work.mkdir(parents=True, exist_ok=True)
    daemon_stdout_path = artifact_dir / "commands" / "signal-monitor.stdout"
    daemon_stderr_path = artifact_dir / "commands" / "signal-monitor.stderr"
    daemon_stdout_path.parent.mkdir(parents=True, exist_ok=True)
    with daemon_stdout_path.open("w", encoding="utf-8") as daemon_stdout, daemon_stderr_path.open(
        "w", encoding="utf-8"
    ) as daemon_stderr:
        signal_monitor = subprocess.Popen(
            [
                str(codex_waked), "--wake-root", str(surface_root),
                "--interval", "0.1", "--no-dispatch",
            ],
            stdout=daemon_stdout,
            stderr=daemon_stderr,
            text=True,
            env=signal_env,
            cwd=signal_work,
        )
        try:
            deadline = time.monotonic() + 10
            while True:
                if signal_monitor.poll() is not None:
                    raise SystemExit("installed signal monitor exited before readiness")
                monitor_state = run_json(
                    [str(codex_wake), "--wake-root", str(surface_root), "monitor", "check", "--json"],
                    artifact_dir=artifact_dir,
                    name="signal-monitor-readiness",
                    env=signal_env,
                    cwd=signal_work,
                    allow_returncodes=(0, 1),
                )
                if monitor_state.get("monitor_ready"):
                    break
                if time.monotonic() >= deadline:
                    raise SystemExit("installed signal monitor did not become ready")
                time.sleep(0.1)
            created = run_command(
                [
                    str(codex_wake), "--wake-root", str(surface_root),
                    "filesystem", "created", "--idempotency-key", "product-smoke-signal",
                    "ready.flag", "--", "provider-free signal smoke",
                ],
                artifact_dir=artifact_dir,
                name="signal-create",
                env=signal_env,
                cwd=signal_work,
            )
            signal_wake_id = parse_wake_id(created.stdout)
            if upgrade_wheel is not None:
                run_command(
                    [
                        str(codex_wake.parent / "python"), "-m", "pip", "install",
                        "--force-reinstall", str(upgrade_wheel.resolve()),
                    ],
                    artifact_dir=artifact_dir,
                    name="signal-upgrade-wheel",
                    env=signal_env,
                    cwd=signal_work,
                    timeout=240,
                )
                signal_monitor.terminate()
                try:
                    signal_monitor.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    signal_monitor.kill()
                    signal_monitor.wait(timeout=5)
                signal_monitor = subprocess.Popen(
                    [
                        str(codex_waked), "--wake-root", str(surface_root),
                        "--interval", "0.1", "--no-dispatch",
                    ],
                    stdout=daemon_stdout,
                    stderr=daemon_stderr,
                    text=True,
                    env=signal_env,
                    cwd=signal_work,
                )
            write_text(signal_work / "ready.flag", "fixture-only\n")
            deadline = time.monotonic() + 10
            while True:
                signal_record = run_json(
                    [str(codex_wake), "--wake-root", str(surface_root), "show", signal_wake_id],
                    artifact_dir=artifact_dir,
                    name="signal-show-firing",
                    env=signal_env,
                    cwd=signal_work,
                )
                if signal_record.get("status") == "firing":
                    break
                if signal_monitor.poll() is not None:
                    raise SystemExit("installed signal monitor exited before observation")
                if time.monotonic() >= deadline:
                    raise SystemExit("installed signal lifecycle did not reach firing without dispatch")
                time.sleep(0.1)
        finally:
            signal_monitor.terminate()
            try:
                signal_monitor.wait(timeout=5)
            except subprocess.TimeoutExpired:
                signal_monitor.kill()
                signal_monitor.wait(timeout=5)
    if signal_record.get("status") != "firing":
        raise SystemExit("installed signal lifecycle did not reach firing without dispatch")
    run_json(
        [
            str(codex_wake), "--wake-root", str(surface_root),
            "show", signal_wake_id, "--signal-state",
        ],
        artifact_dir=artifact_dir,
        name="signal-authority",
        env=signal_env,
        cwd=signal_work,
    )
    support_path = artifact_dir / "signal-support.json"
    support_receipt = run_json(
        [
            str(codex_wake), "--wake-root", str(surface_root), "support", "export",
            "--output", str(support_path), "--max-wakes", "10", "--max-bytes", "32768", "--json",
        ],
        artifact_dir=artifact_dir,
        name="signal-support-export",
        env=signal_env,
        cwd=signal_work,
    )
    run_command(
        [str(codex_wake), "--wake-root", str(surface_root), "cancel", signal_wake_id],
        artifact_dir=artifact_dir,
        name="signal-cancel",
        env=signal_env,
        cwd=signal_work,
    )
    run_command(
        [str(codex_wake), "--wake-root", str(surface_root), "archive", signal_wake_id],
        artifact_dir=artifact_dir,
        name="signal-archive",
        env=signal_env,
        cwd=signal_work,
    )
    time.sleep(1.1)
    cleanup = run_json(
        [
            str(codex_wake), "--wake-root", str(surface_root), "cleanup",
            "--older-than", "1s", "--delete", "--json",
        ],
        artifact_dir=artifact_dir,
        name="signal-retention-cleanup",
        env=signal_env,
        cwd=signal_work,
    )
    if cleanup.get("matched_count") != 1 or cleanup.get("protected_count") != 0:
        raise SystemExit("installed signal retirement was not eligible for bounded cleanup")
    summary["signal_lifecycle"] = {
        "wake_id": signal_wake_id,
        "observed_status": signal_record.get("status"),
        "dispatch_attempted": False,
        "support_size_bytes": support_receipt.get("size_bytes"),
        "retired_status": "archived",
        "cleanup_deleted": bool(cleanup.get("matched", [{}])[0].get("deleted")),
        "upgrade_reinstall": upgrade_wheel is not None,
        "upgrade_restart": upgrade_wheel is not None,
    }
    github_fixture_code = textwrap.dedent(
        """
        import json, tempfile
        from datetime import UTC, datetime, timedelta
        from pathlib import Path
        from codex_wake.event_wake import EventWake
        from codex_wake.github_polling import GitHubPollingAdapter, GitHubPollingConfig, RunPage, WorkflowRun
        from codex_wake.signal_records import ManagedReaderCapability, WakeRecordPublisher, signal_journal_path
        from codex_wake.signal_store import SQLiteSignalModule
        from codex_wake.signals import EvaluationLimits, Resume, WakeIntent
        from codex_wake.signal_support import github_source_readiness
        from codex_wake.github_source_config import GitHubSourceStore

        now = datetime(2026, 9, 14, 18, 0, tzinfo=UTC)
        run = WorkflowRun('example/project', 42, 7, 101, 1, 'refs/heads/main', 'a' * 40,
                          'completed', 'success', None, now + timedelta(seconds=1),
                          'github_attempt_started_or_job_completed_lower_bound')
        class FixtureClient:
            def list_runs(self, query):
                return RunPage((run,), None, now - timedelta(days=1), query.until)
            def get_run_attempt(self, repository, run_id, run_attempt):
                return run
        config = GitHubPollingConfig(
            source_instance='github-ci', repository='example/project', repository_id=42,
            workflow_id=7, refs=frozenset({'refs/heads/main'}),
            conclusions=frozenset({'success'}), credential_ref='fixture-only',
            evidence_mode='positive_only'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'wake'
            source_store = GitHubSourceStore(root)
            source_store.configure(config)
            reloaded_config = GitHubSourceStore(root).registry().select('github-ci')
            if reloaded_config != config:
                raise SystemExit('GitHub source configuration did not survive reload')
            runtime = SQLiteSignalModule(
                signal_journal_path(root),
                record_publisher=WakeRecordPublisher(
                    root, ManagedReaderCapability(root, 'fixture-reader', 1, frozenset({1, 2}), True)
                ),
            )
            adapter = GitHubPollingAdapter(reloaded_config, FixtureClient())
            registration = EventWake(runtime, adapters=(adapter,), clock=lambda: now,
                                     id_factory=lambda: 'wake_github_fixture').register(
                WakeIntent(adapter.request(ref='refs/heads/main', conclusions=('success',)),
                           Resume('continue', Path(tmp), {'transport': 'tmux'})),
                idempotency_key='github-fixture'
            )
            armed = runtime.load_armed_signal(registration.wake_id)
            ingested = adapter.poll_into(runtime, armed.anchor, checkpoints=runtime,
                                         now=now + timedelta(seconds=2))
            matched = runtime.evaluate(registration.wake_id, armed,
                                       now + timedelta(seconds=2), EvaluationLimits(20))
            if getattr(matched, 'outcome', '') != 'matched':
                raise SystemExit('fixture-backed GitHub signal did not match')
            readiness = github_source_readiness(
                reloaded_config, health={'credential_capability': 'ready',
                                'checked_at': now.isoformat(),
                                'checkpoint_present': True,
                                'replay_lag_seconds': 0},
                checkpoint=runtime.source_checkpoint('github', 'github-ci'))
            if readiness['status'] != 'ready' or readiness['credential_capability']['status'] != 'ready':
                raise SystemExit('GitHub readiness projection did not report the fixture lifecycle as ready')
            print(json.dumps({'status': matched.outcome, 'source': armed.spec.source,
                              'receipts': len(ingested.receipts),
                              'readiness': readiness}))
        """
    )
    github_fixture = run_json(
        [str(codex_wake.parent / "python"), "-c", github_fixture_code],
        artifact_dir=artifact_dir,
        name="signal-github-fixture",
        env=signal_env,
    )
    summary["github_fixture_lifecycle"] = github_fixture
    return summary


def run_live_monitor_check(
    *,
    codex_wake: Path,
    wake_root: Path,
    artifact_dir: Path,
    env: dict[str, str],
) -> dict[str, Any]:
    monitor = run_json(
        [str(codex_wake), "--wake-root", str(wake_root), "monitor", "check", "--json"],
        artifact_dir=artifact_dir,
        name="live-monitor-check",
        env=env,
        allow_returncodes=(0,),
    )
    if not monitor.get("monitor_ready"):
        raise SystemExit(f"live wake root is not monitor-ready: {wake_root}")
    return {
        "status": "ready",
        "wake_root": str(wake_root),
        "monitor_source": monitor.get("monitor_source"),
    }


def run_live_codex_smoke(
    *,
    codex_wake: Path,
    wake_root: Path,
    thread_id: str,
    codex_path: str,
    artifact_dir: Path,
    env: dict[str, str],
    due_after: str,
    timeout_seconds: float,
) -> dict[str, Any]:
    marker = f"CODEX_WAKE_PRODUCT_SMOKE_CODEX_{utc_stamp()}"
    prompt = f"Product smoke marker: {marker}. Echo the marker, then stop."
    command = [
        str(codex_wake),
        "--wake-root",
        str(wake_root),
        "app",
        "after",
        "--require-monitor",
    ]
    if codex_path:
        command.extend(["--codex-path", codex_path])
    command.extend([thread_id, due_after, "--", prompt])
    result = run_command(command, artifact_dir=artifact_dir, name="live-codex-create", env=env)
    wake_id = parse_wake_id(result.stdout)
    final = wait_for_wake(
        codex_wake=codex_wake,
        wake_root=wake_root,
        wake_id=wake_id,
        artifact_dir=artifact_dir,
        name="live-codex",
        timeout_seconds=timeout_seconds,
        env=env,
    )
    return {"wake_id": wake_id, "marker": marker, "status": final.get("status")}


def run_live_openclaw_smoke(
    *,
    codex_wake: Path,
    wake_root: Path,
    args: argparse.Namespace,
    artifact_dir: Path,
    env: dict[str, str],
) -> dict[str, Any]:
    marker = f"CODEX_WAKE_PRODUCT_SMOKE_OPENCLAW_{utc_stamp()}"
    prompt = f"Product smoke marker: {marker}. Echo the marker or record it in the transcript, then stop."
    command = [
        str(codex_wake),
        "--wake-root",
        str(wake_root),
        "openclaw",
        "after",
        "--require-monitor",
        "--agent",
        args.live_openclaw_agent,
        "--session-key",
        args.live_openclaw_session_key,
    ]
    optional_pairs = [
        ("--gateway-url", args.live_openclaw_gateway_url),
        ("--token-env", args.live_openclaw_token_env),
        ("--password-env", args.live_openclaw_password_env),
        ("--openclaw-path", args.live_openclaw_path),
        ("--workspace", args.live_openclaw_workspace),
        ("--channel", args.live_openclaw_channel),
        ("--thread-ts", args.live_openclaw_thread_ts),
        ("--reply-channel", args.live_openclaw_reply_channel),
        ("--reply-to", args.live_openclaw_reply_to),
        ("--reply-account", args.live_openclaw_reply_account),
        ("--model", args.live_openclaw_model),
        ("--thinking", args.live_openclaw_thinking),
    ]
    for flag, value in optional_pairs:
        if value:
            command.extend([flag, value])
    if args.live_openclaw_deliver:
        command.append("--deliver")
    command.extend([args.due_after, "--", prompt])
    result = run_command(command, artifact_dir=artifact_dir, name="live-openclaw-create", env=env)
    wake_id = parse_wake_id(result.stdout)
    final = wait_for_wake(
        codex_wake=codex_wake,
        wake_root=wake_root,
        wake_id=wake_id,
        artifact_dir=artifact_dir,
        name="live-openclaw",
        timeout_seconds=args.live_timeout,
        env=env,
    )
    return {"wake_id": wake_id, "marker": marker, "status": final.get("status")}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run codex-wake productization smoke checks")
    parser.add_argument("--codex-wake-bin", default=os.environ.get("CODEX_WAKE_BIN", "codex-wake"))
    parser.add_argument("--codex-waked-bin", default=os.environ.get("CODEX_WAKED_BIN", "codex-waked"))
    parser.add_argument("--public-tag", help="install codex-wake from this public Git tag into a temporary venv before smoking")
    parser.add_argument("--upgrade-wheel", type=Path, help="force-reinstall this wheel after signal arm and before observation")
    parser.add_argument("--artifact-dir", type=Path, default=None, help="directory for smoke artifacts")
    parser.add_argument("--wake-root", type=Path, default=None, help="live wake root; defaults to .codex/wake under the repo")
    parser.add_argument("--allow-source", action="store_true", help="allow smoke against a binary inside this source checkout")
    parser.add_argument("--use-user-state", action="store_true", help="do not isolate XDG_CONFIG_HOME/XDG_STATE_HOME for surface checks")
    parser.add_argument("--expect-monitor-ready", action="store_true", help="require monitor check to report ready during surface smoke")
    parser.add_argument("--due-after", default="5s", help="delay used for live wake smoke registrations")
    parser.add_argument("--live-timeout", type=float, default=120.0, help="seconds to wait for live wake terminal status")
    parser.add_argument("--live-codex-thread-id", help="run a real Codex app-server wake against this thread id")
    parser.add_argument("--live-codex-path", default="", help="Codex CLI command/path to persist in the live app-server wake")
    parser.add_argument("--live-openclaw-agent", help="run a real OpenClaw Gateway wake for this agent id")
    parser.add_argument("--live-openclaw-session-key", help="OpenClaw session key for the live Gateway wake")
    parser.add_argument("--live-openclaw-gateway-url", default="")
    parser.add_argument("--live-openclaw-token-env", default="")
    parser.add_argument("--live-openclaw-password-env", default="")
    parser.add_argument("--live-openclaw-path", default="")
    parser.add_argument("--live-openclaw-workspace", default="")
    parser.add_argument("--live-openclaw-channel", default="")
    parser.add_argument("--live-openclaw-thread-ts", default="")
    parser.add_argument("--live-openclaw-deliver", action="store_true")
    parser.add_argument("--live-openclaw-reply-channel", default="")
    parser.add_argument("--live-openclaw-reply-to", default="")
    parser.add_argument("--live-openclaw-reply-account", default="")
    parser.add_argument("--live-openclaw-model", default="")
    parser.add_argument("--live-openclaw-thinking", default="")
    parser.add_argument("--json", action="store_true", dest="as_json")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    root = repo_root()
    artifact_dir = (args.artifact_dir or (root / ".codex" / "wake" / "smoke" / utc_stamp())).resolve()
    artifact_dir.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    temp_public_work = ""

    if args.public_tag:
        codex_wake, codex_waked, public_work = install_public_tag(args.public_tag, artifact_dir)
        temp_public_work = str(public_work)
    else:
        codex_wake = resolve_command(args.codex_wake_bin)
        codex_waked = resolve_command(args.codex_waked_bin)

    reject_source_tree_binary(codex_wake, root, allow_source=args.allow_source)
    reject_source_tree_binary(codex_waked, root, allow_source=args.allow_source)
    path_entries = [str(codex_wake.parent)]
    if codex_waked.parent != codex_wake.parent:
        path_entries.append(str(codex_waked.parent))
    env["PATH"] = os.pathsep.join([*path_entries, env.get("PATH", "")])

    live_wake_root = (args.wake_root or (root / ".codex" / "wake")).resolve()
    summary: dict[str, Any] = {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "repo_root": str(root),
        "artifact_dir": str(artifact_dir),
        "codex_wake_bin": str(codex_wake),
        "codex_waked_bin": str(codex_waked),
        "public_tag": args.public_tag or "",
        "public_tag_work_dir": temp_public_work,
        "live_wake_root": str(live_wake_root),
        "checks": {},
    }

    summary["checks"]["surface"] = run_surface_smoke(
        codex_wake=codex_wake,
        codex_waked=codex_waked,
        artifact_dir=artifact_dir,
        root=root,
        source_env=env,
        use_user_state=args.use_user_state,
        upgrade_wheel=args.upgrade_wheel,
    )

    if args.expect_monitor_ready:
        summary["checks"]["live_monitor"] = run_live_monitor_check(
            codex_wake=codex_wake,
            wake_root=live_wake_root,
            artifact_dir=artifact_dir,
            env=env,
        )
    else:
        summary["checks"]["live_monitor"] = {
            "status": "skipped",
            "reason": "--expect-monitor-ready was not provided",
        }

    if args.live_codex_thread_id:
        summary["checks"]["live_codex_app_server"] = run_live_codex_smoke(
            codex_wake=codex_wake,
            wake_root=live_wake_root,
            thread_id=args.live_codex_thread_id,
            codex_path=args.live_codex_path,
            artifact_dir=artifact_dir,
            env=env,
            due_after=args.due_after,
            timeout_seconds=args.live_timeout,
        )
    else:
        summary["checks"]["live_codex_app_server"] = {
            "status": "skipped",
            "reason": "--live-codex-thread-id was not provided",
        }

    if args.live_openclaw_agent or args.live_openclaw_session_key:
        if not (args.live_openclaw_agent and args.live_openclaw_session_key):
            raise SystemExit("live OpenClaw smoke requires both --live-openclaw-agent and --live-openclaw-session-key")
        summary["checks"]["live_openclaw_gateway"] = run_live_openclaw_smoke(
            codex_wake=codex_wake,
            wake_root=live_wake_root,
            args=args,
            artifact_dir=artifact_dir,
            env=env,
        )
    else:
        summary["checks"]["live_openclaw_gateway"] = {
            "status": "skipped",
            "reason": "--live-openclaw-agent and --live-openclaw-session-key were not provided",
        }

    summary["checks"]["tmux"] = {
        "status": "manual_only",
        "reason": "tmux smoke can paste into the active pane and requires operator-visible pane evidence",
        "tmux_pane_present": bool(env.get("TMUX_PANE")),
        "tmux_env_present": bool(env.get("TMUX")),
    }
    write_json(artifact_dir / "summary.json", summary)
    if args.as_json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print(f"artifact_dir={artifact_dir}")
        print(f"cli_version={summary['checks']['surface']['cli_version']}")
        print(f"schema_version={summary['checks']['surface']['schema_version']}")
        print(f"monitor_ready={str(summary['checks']['surface']['monitor_ready']).lower()}")
        print(f"supervisor_once_roots={summary['checks']['surface']['supervisor_once_roots']}")
        print(f"live_codex_app_server={summary['checks']['live_codex_app_server']['status']}")
        print(f"live_openclaw_gateway={summary['checks']['live_openclaw_gateway']['status']}")
        print("tmux=manual_only")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
