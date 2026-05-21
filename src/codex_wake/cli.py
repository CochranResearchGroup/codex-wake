from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import UTC
from pathlib import Path

from .app_server import read_app_server_thread_status
from .hook_config import DEFAULT_HOOK_COMMAND, check_hook_config, hook_review_note, hook_runtime_evidence, install_hook_config
from .process import process_exists, process_identity
from .records import (
    WakeError,
    all_records,
    archive_record,
    archive_terminal_records,
    build_record,
    cancel_record,
    cleanup_archived_records,
    capture_tmux_target,
    default_wake_root,
    find_record,
    format_utc,
    iter_records,
    normalize_prompt,
    parse_duration,
    parse_timestamp,
    schema_summary,
    status_summary,
    utc_now,
    write_record,
)
from .service import build_service_config, install_service, read_log_tail, service_status, stop_service, uninstall_service


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="codex-wake")
    parser.add_argument(
        "--wake-root",
        type=Path,
        default=None,
        help="wake runtime root; defaults to .codex/wake under the current directory",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    after = subparsers.add_parser("after", help="create a wake after a duration such as 45m or 1h30m")
    after.add_argument("duration")
    after.add_argument("prompt", nargs=argparse.REMAINDER)
    add_target_options(after)

    at = subparsers.add_parser("at", help="create a wake at an ISO-8601 timestamp with timezone")
    at.add_argument("timestamp")
    at.add_argument("prompt", nargs=argparse.REMAINDER)
    add_target_options(at)

    app = subparsers.add_parser("app", help="create an app-server-targeted wake")
    app_subparsers = app.add_subparsers(dest="app_command", required=True)

    app_after = app_subparsers.add_parser("after", help="create an app-server wake after a duration")
    app_after.add_argument("--endpoint", default="stdio://", help="app-server endpoint; only stdio:// is currently implemented")
    app_after.add_argument("thread_id")
    app_after.add_argument("duration")
    app_after.add_argument("prompt", nargs=argparse.REMAINDER)

    app_at = app_subparsers.add_parser("at", help="create an app-server wake at an ISO-8601 timestamp")
    app_at.add_argument("--endpoint", default="stdio://", help="app-server endpoint; only stdio:// is currently implemented")
    app_at.add_argument("thread_id")
    app_at.add_argument("timestamp")
    app_at.add_argument("prompt", nargs=argparse.REMAINDER)

    app_status = app_subparsers.add_parser("status", help="read an app-server thread status without starting a turn")
    app_status.add_argument("--endpoint", default="stdio://", help="app-server endpoint; only stdio:// is currently implemented")
    app_status.add_argument("--json", action="store_true", dest="as_json")
    app_status.add_argument("--resume", action="store_true", help="resume the thread before reading status; does not start a turn")
    app_status.add_argument("thread_id")

    file_cmd = subparsers.add_parser("file", help="create a wake when a file exists")
    file_cmd.add_argument("path")
    file_cmd.add_argument("prompt", nargs=argparse.REMAINDER)
    add_target_options(file_cmd)

    changed = subparsers.add_parser("changed", help="create a wake when a file is created or changes mtime/size")
    changed.add_argument("path")
    changed.add_argument("prompt", nargs=argparse.REMAINDER)
    add_target_options(changed)

    pid = subparsers.add_parser("pid", help="create a wake when a process id exits")
    pid.add_argument("pid", type=int)
    pid.add_argument("prompt", nargs=argparse.REMAINDER)
    add_target_options(pid)

    list_cmd = subparsers.add_parser("list", help="list wake records")
    list_cmd.add_argument("--json", action="store_true", dest="as_json")
    list_cmd.add_argument("--archived", action="store_true", help="include archived wake records")

    status = subparsers.add_parser("status", help="summarize wake records by state")
    status.add_argument("--json", action="store_true", dest="as_json")

    show = subparsers.add_parser("show", help="show one wake record")
    show.add_argument("wake_id")

    cancel = subparsers.add_parser("cancel", help="cancel a pending or firing wake")
    cancel.add_argument("wake_id")

    archive = subparsers.add_parser("archive", help="archive terminal wake records")
    archive.add_argument("wake_id", nargs="?", help="specific wake id to archive")
    archive.add_argument("--all-terminal", action="store_true", help="archive all submitted, failed, cancelled, and expired wakes")

    cleanup = subparsers.add_parser("cleanup", help="preview or delete old archived wake records")
    cleanup.add_argument("--older-than", default="30d", help="archive retention window; defaults to 30d")
    cleanup.add_argument("--delete", action="store_true", help="delete matching archived records; default is dry-run")
    cleanup.add_argument("--archive-terminal", action="store_true", help="archive terminal records before evaluating cleanup")
    cleanup.add_argument("--json", action="store_true", dest="as_json")

    schema = subparsers.add_parser("schema", help="show wake record schema version and compatibility policy")
    schema.add_argument("--json", action="store_true", dest="as_json")

    service = subparsers.add_parser("service", help="manage a user-scoped codex-waked service")
    service_subparsers = service.add_subparsers(dest="service_command", required=True)

    service_install = service_subparsers.add_parser("install", help="install and start a user systemd service")
    add_service_options(service_install)
    service_install.add_argument("--no-start", action="store_true", help="write the unit but do not enable or start it")

    service_status_cmd = service_subparsers.add_parser("status", help="show user service state")
    add_service_options(service_status_cmd)

    service_logs = service_subparsers.add_parser("logs", help="print recent service log lines")
    add_service_options(service_logs)
    service_logs.add_argument("--lines", type=int, default=50)

    service_stop = service_subparsers.add_parser("stop", help="stop and disable the user service")
    add_service_options(service_stop)

    service_uninstall = service_subparsers.add_parser("uninstall", help="stop, disable, and remove the user service")
    add_service_options(service_uninstall)

    hook = subparsers.add_parser("hook", help="install or check repo-local Codex hook config")
    hook_subparsers = hook.add_subparsers(dest="hook_command", required=True)

    hook_install = hook_subparsers.add_parser("install", help="write .codex/hooks.json for codex-wake-hook")
    add_hook_options(hook_install)

    hook_check = hook_subparsers.add_parser("check", help="check .codex/hooks.json for codex-wake-hook")
    add_hook_options(hook_check)

    doctor = subparsers.add_parser("doctor", help="report Codex Wake readiness for this repo")
    doctor.add_argument("--hook-command", default=DEFAULT_HOOK_COMMAND, help="expected UserPromptSubmit hook command")
    doctor.add_argument("--json", action="store_true", dest="as_json")
    add_service_options(doctor)

    return parser


def add_target_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--app-server-thread-id",
        help="create an app-server-targeted wake for the given Codex thread id instead of capturing tmux",
    )
    parser.add_argument(
        "--app-server-endpoint",
        default="stdio://",
        help="app-server endpoint for --app-server-thread-id; only stdio:// is currently implemented",
    )


def add_service_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--name", help="systemd user unit name; defaults to codex-wake-<repo>.service")
    parser.add_argument("--repo-root", type=Path, default=None, help="repo root for the service; defaults to current directory")
    parser.add_argument("--interval", type=float, default=1.0, help="daemon poll interval in seconds")
    parser.add_argument("--daemon-path", help="path to codex-waked; defaults to PATH resolution")
    parser.add_argument("--log-path", type=Path, default=None, help="service log path")


def add_hook_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--repo-root", type=Path, default=None, help="repo root to update; defaults to current directory")
    parser.add_argument("--command", dest="hook_command_text", default=DEFAULT_HOOK_COMMAND, help="hook command to install or check")


def resolve_root(args: argparse.Namespace) -> Path:
    return (args.wake_root or default_wake_root()).resolve()


def create_after(args: argparse.Namespace, root: Path) -> int:
    now = utc_now()
    due = now + parse_duration(args.duration)
    predicate = {"type": "not_before", "due_at": format_utc(due)}
    return create_record(args.prompt, predicate, root, now, args)


def create_at(args: argparse.Namespace, root: Path) -> int:
    due = parse_timestamp(args.timestamp)
    predicate = {"type": "not_before", "due_at": format_utc(due)}
    return create_record(args.prompt, predicate, root, utc_now(), args)


def create_app(args: argparse.Namespace, root: Path) -> int:
    if args.app_command == "status":
        return app_status(args)
    now = utc_now()
    if args.app_command == "after":
        due = now + parse_duration(args.duration)
    elif args.app_command == "at":
        due = parse_timestamp(args.timestamp)
    else:
        raise WakeError(f"unknown app command: {args.app_command}")
    if args.endpoint != "stdio://":
        raise WakeError("only app-server endpoint stdio:// is currently implemented")
    predicate = {"type": "not_before", "due_at": format_utc(due)}
    target = {
        "transport": "app-server",
        "endpoint": args.endpoint,
        "thread_id": args.thread_id,
    }
    return create_record(args.prompt, predicate, root, now, args, target=target)


def app_status(args: argparse.Namespace) -> int:
    if args.endpoint != "stdio://":
        raise WakeError("only app-server endpoint stdio:// is currently implemented")
    summary = read_app_server_thread_status(args.thread_id, resume=args.resume)
    if args.as_json:
        print(json.dumps(summary, indent=2, sort_keys=True))
        return 0
    print(f"thread_id={summary['thread_id']}")
    print(f"status_type={summary['status_type']}")
    print(f"source={'thread/resume' if args.resume else 'thread/read'}")
    active_flags = summary.get("active_flags")
    if isinstance(active_flags, list):
        print("active_flags=" + ",".join(str(flag) for flag in active_flags))
    if summary.get("cwd"):
        print(f"cwd={summary['cwd']}")
    if summary.get("sessionId"):
        print(f"session_id={summary['sessionId']}")
    return 0


def create_file(args: argparse.Namespace, root: Path) -> int:
    path = args.path.strip()
    if not path:
        raise WakeError("file path is required")
    predicate = {"type": "file_exists", "path": path}
    return create_record(args.prompt, predicate, root, utc_now(), args)


def create_changed(args: argparse.Namespace, root: Path) -> int:
    path_text = args.path.strip()
    if not path_text:
        raise WakeError("file path is required")
    path = Path(path_text)
    resolved = path if path.is_absolute() else Path.cwd() / path
    try:
        stat = resolved.stat()
    except FileNotFoundError:
        predicate = {
            "type": "file_changed",
            "path": path_text,
            "registered_exists": False,
            "registered_mtime_ns": None,
            "registered_size": None,
        }
    else:
        predicate = {
            "type": "file_changed",
            "path": path_text,
            "registered_exists": True,
            "registered_mtime_ns": stat.st_mtime_ns,
            "registered_size": stat.st_size,
        }
    return create_record(args.prompt, predicate, root, utc_now(), args)


def create_pid(args: argparse.Namespace, root: Path) -> int:
    pid = args.pid
    if pid <= 0:
        raise WakeError("pid must be a positive integer")
    if not process_exists(pid):
        raise WakeError(f"process does not exist: {pid}")
    predicate = {"type": "process_done", "pid": pid}
    identity = process_identity(pid)
    if identity:
        predicate["registered_start_time_ticks"] = identity["start_time_ticks"]
        if "boot_id" in identity:
            predicate["registered_boot_id"] = identity["boot_id"]
    return create_record(args.prompt, predicate, root, utc_now(), args)


def create_record(
    prompt_parts: list[str],
    predicate: dict,
    root: Path,
    now,
    args: argparse.Namespace,
    *,
    target: dict[str, str] | None = None,
) -> int:
    prompt = normalize_prompt(prompt_parts)
    record = build_record(
        predicate=predicate,
        prompt=prompt,
        cwd=Path.cwd(),
        target=target or target_for_args(args),
        now=now,
    )
    path = write_record(root, record)
    print(f"{record['id']} {path}")
    return 0


def target_for_args(args: argparse.Namespace) -> dict[str, str]:
    if getattr(args, "app_server_thread_id", None):
        endpoint = getattr(args, "app_server_endpoint", "stdio://")
        if endpoint != "stdio://":
            raise WakeError("only app-server endpoint stdio:// is currently implemented")
        return {
            "transport": "app-server",
            "endpoint": endpoint,
            "thread_id": args.app_server_thread_id,
        }
    return capture_tmux_target()


def list_records(args: argparse.Namespace, root: Path) -> int:
    records = all_records(root, include_archive=args.archived)
    if args.as_json:
        print(json.dumps([item.record for item in records], indent=2, sort_keys=True))
        return 0
    if not records:
        print("No wakes.")
        return 0
    print("ID\tSTATUS\tPREDICATE\tNEXT")
    for item in records:
        record = item.record
        predicate = record.get("predicate") or {}
        predicate_type = predicate.get("type", "unknown")
        next_attempt = record.get("next_attempt_at", "")
        print(f"{record.get('id')}\t{record.get('status')}\t{predicate_type}\t{next_attempt}")
    return 0


def status_command(args: argparse.Namespace, root: Path) -> int:
    summary = status_summary(root)
    if args.as_json:
        print(json.dumps(summary, indent=2, sort_keys=True))
        return 0
    print(f"wake_root={summary['wake_root']}")
    print(f"total={summary['total']}")
    print(f"active_total={summary['active_total']}")
    print(f"terminal_total={summary['terminal_total']}")
    print(f"archived_total={summary['archived_total']}")
    counts_by_status = summary["counts_by_status"]
    counts_by_predicate = summary["counts_by_predicate"]
    counts_by_target = summary["counts_by_target_transport"]
    assert isinstance(counts_by_status, dict)
    assert isinstance(counts_by_predicate, dict)
    assert isinstance(counts_by_target, dict)
    print("counts_by_status=" + ",".join(f"{key}:{counts_by_status[key]}" for key in sorted(counts_by_status)))
    print("counts_by_predicate=" + ",".join(f"{key}:{counts_by_predicate[key]}" for key in sorted(counts_by_predicate)))
    print("counts_by_target_transport=" + ",".join(f"{key}:{counts_by_target[key]}" for key in sorted(counts_by_target)))
    print(f"earliest_next_attempt_at={summary['earliest_next_attempt_at']}")
    return 0


def show_record(args: argparse.Namespace, root: Path) -> int:
    found = find_record(root, args.wake_id)
    print(json.dumps(found.record, indent=2, sort_keys=True))
    return 0


def cancel(args: argparse.Namespace, root: Path) -> int:
    path = cancel_record(root, args.wake_id)
    print(f"cancelled {args.wake_id} {path}")
    return 0


def archive(args: argparse.Namespace, root: Path) -> int:
    if bool(args.wake_id) == bool(args.all_terminal):
        raise WakeError("provide either a wake id or --all-terminal")
    if args.all_terminal:
        paths = archive_terminal_records(root)
        for path in paths:
            print(f"archived {path.stem} {path}")
        if not paths:
            print("No terminal wakes to archive.")
        return 0
    path = archive_record(root, args.wake_id)
    print(f"archived {args.wake_id} {path}")
    return 0


def cleanup(args: argparse.Namespace, root: Path) -> int:
    older_than = parse_duration(args.older_than)
    archived = []
    if args.archive_terminal:
        archived = archive_terminal_records(root)
    results = cleanup_archived_records(root, older_than=older_than, delete=args.delete)
    if args.as_json:
        print(
            json.dumps(
                {
                    "wake_root": str(root),
                    "mode": "delete" if args.delete else "dry-run",
                    "older_than": args.older_than,
                    "archive_terminal": bool(args.archive_terminal),
                    "archived_terminal_count": len(archived),
                    "archived_terminal": [{"wake_id": path.stem, "path": str(path)} for path in archived],
                    "matched_count": len(results),
                    "matched": [
                        {
                            "wake_id": result.wake_id,
                            "path": str(result.path),
                            "retention_at": result.retention_at,
                            "deleted": result.deleted,
                        }
                        for result in results
                    ],
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    for path in archived:
        print(f"archived {path.stem} {path}")
    action = "deleted" if args.delete else "would-delete"
    for result in results:
        print(f"{action} {result.wake_id} {result.path} retention_at={result.retention_at}")
    mode = "delete" if args.delete else "dry-run"
    print(f"cleanup mode={mode} older_than={args.older_than} archived={len(archived)} matched={len(results)}")
    return 0


def schema_command(args: argparse.Namespace) -> int:
    summary = schema_summary()
    if args.as_json:
        print(json.dumps(summary, indent=2, sort_keys=True))
        return 0
    print(f"schema_version={summary['schema_version']}")
    print(f"compatibility={summary['compatibility']}")
    print(f"schema_doc={summary['schema_doc']}")
    print(f"statuses={','.join(summary['active_statuses'] + summary['terminal_statuses'] + [summary['archived_status']])}")
    print(f"predicate_types={','.join(summary['predicate_types'])}")
    print(f"target_transports={','.join(summary['target_transports'])}")
    print(f"required_fields={','.join(summary['required_fields'])}")
    print(f"optional_fields={','.join(summary['optional_fields'])}")
    print(f"schema_bump_required_for={','.join(summary['schema_bump_required_for'])}")
    return 0


def service_config_for_args(args: argparse.Namespace, root: Path):
    return build_service_config(
        repo_root=args.repo_root,
        wake_root=root,
        name=args.name,
        interval=args.interval,
        daemon_path=args.daemon_path,
        log_path=args.log_path,
    )


def service_command(args: argparse.Namespace, root: Path) -> int:
    config = service_config_for_args(args, root)
    if args.service_command == "install":
        install_service(config, start=not args.no_start)
        action = "installed" if args.no_start else "installed and started"
        print(f"{action} {config.name}")
        print(f"unit={config.unit_path}")
        print(f"log={config.log_path}")
        return 0
    if args.service_command == "status":
        active, enabled = service_status(config)
        print(f"name={config.name}")
        print(f"active={active}")
        print(f"enabled={enabled}")
        print(f"unit={config.unit_path}")
        print(f"log={config.log_path}")
        return 0
    if args.service_command == "logs":
        print(f"log={config.log_path}")
        text = read_log_tail(config.log_path, args.lines)
        if text:
            print(text)
        return 0
    if args.service_command == "stop":
        stop_service(config)
        print(f"stopped {config.name}")
        return 0
    if args.service_command == "uninstall":
        uninstall_service(config)
        print(f"uninstalled {config.name}")
        print(f"removed={config.unit_path}")
        return 0
    raise WakeError(f"unknown service command: {args.service_command}")


def print_hook_runtime_evidence(root: Path) -> None:
    evidence = hook_runtime_evidence(root)
    print(f"hook_ack_count={evidence.ack_count}")
    print(f"hook_active_session_loaded={evidence.active_session_loaded}")
    print(f"hook_latest_ack_path={evidence.latest_ack_path or ''}")
    print(f"hook_latest_ack_submitted_at={evidence.latest_ack_submitted_at}")
    print(f"hook_latest_ack_wake_id={evidence.latest_ack_wake_id}")
    print(f"hook_latest_ack_session_id={evidence.latest_ack_session_id}")
    print("hook_loaded_note=ack evidence proves a hook ran only after a wake prompt was submitted")


def hook_command(args: argparse.Namespace, root: Path) -> int:
    repo_root = (args.repo_root or Path.cwd()).resolve()
    if args.hook_command == "install":
        path = install_hook_config(repo_root, args.hook_command_text)
        print(f"installed hook config: {path}")
        print(f"command={args.hook_command_text}")
        print(f"note={hook_review_note()}")
        return 0
    if args.hook_command == "check":
        check = check_hook_config(repo_root, args.hook_command_text)
        print(f"path={check.path}")
        print(f"exists={str(check.exists).lower()}")
        print(f"valid_json={str(check.valid_json).lower()}")
        print(f"installed={str(check.installed).lower()}")
        print(f"command={check.command}")
        print(f"message={check.message}")
        print(f"trust={hook_review_note()}")
        print_hook_runtime_evidence(root)
        return 0 if check.installed else 1
    raise WakeError(f"unknown hook command: {args.hook_command}")


def doctor_summary(args: argparse.Namespace, root: Path) -> dict[str, object]:
    repo_root = (args.repo_root or Path.cwd()).resolve()
    hook_check = check_hook_config(repo_root, args.hook_command)
    config = service_config_for_args(args, root)
    codex_wake = shutil.which("codex-wake") or ""
    codex_waked = shutil.which("codex-waked") or ""
    codex_wake_hook = shutil.which("codex-wake-hook") or ""
    tmux = shutil.which("tmux") or ""
    try:
        active, enabled = service_status(config)
    except Exception as exc:
        active, enabled = "unknown", f"unknown ({exc})"
    hook_evidence = hook_runtime_evidence(root)
    return {
        "repo_root": str(repo_root),
        "wake_root": str(root),
        "commands": {
            "codex_wake": codex_wake or "",
            "codex_waked": codex_waked or "",
            "codex_wake_hook": codex_wake_hook or "",
            "tmux": tmux or "",
        },
        "hook_config": {
            "path": str(hook_check.path),
            "exists": hook_check.exists,
            "valid_json": hook_check.valid_json,
            "installed": hook_check.installed,
            "command": hook_check.command,
            "message": hook_check.message,
        },
        "hook_runtime": {
            "ack_count": hook_evidence.ack_count,
            "active_session_loaded": hook_evidence.active_session_loaded,
            "latest_ack_path": str(hook_evidence.latest_ack_path) if hook_evidence.latest_ack_path else "",
            "latest_ack_submitted_at": hook_evidence.latest_ack_submitted_at,
            "latest_ack_wake_id": hook_evidence.latest_ack_wake_id,
            "latest_ack_session_id": hook_evidence.latest_ack_session_id,
            "loaded_note": "ack evidence proves a hook ran only after a wake prompt was submitted",
        },
        "service": {
            "name": config.name,
            "active": active,
            "enabled": enabled,
            "unit": str(config.unit_path),
            "log": str(config.log_path),
        },
        "trust": hook_review_note(),
    }


def doctor_command(args: argparse.Namespace, root: Path) -> int:
    summary = doctor_summary(args, root)
    if args.as_json:
        print(json.dumps(summary, indent=2, sort_keys=True))
        return 0
    commands = summary["commands"]
    hook_config = summary["hook_config"]
    hook_runtime = summary["hook_runtime"]
    service = summary["service"]
    assert isinstance(commands, dict)
    assert isinstance(hook_config, dict)
    assert isinstance(hook_runtime, dict)
    assert isinstance(service, dict)
    print(f"repo_root={summary['repo_root']}")
    print(f"wake_root={summary['wake_root']}")
    print(f"codex_wake={commands['codex_wake'] or 'missing'}")
    print(f"codex_waked={commands['codex_waked'] or 'missing'}")
    print(f"codex_wake_hook={commands['codex_wake_hook'] or 'missing'}")
    print(f"tmux={commands['tmux'] or 'missing'}")
    print(f"hook_config={hook_config['path']}")
    print(f"hook_config_exists={str(hook_config['exists']).lower()}")
    print(f"hook_config_valid_json={str(hook_config['valid_json']).lower()}")
    print(f"hook_config_installed={str(hook_config['installed']).lower()}")
    print(f"hook_command={hook_config['command']}")
    print(f"hook_ack_count={hook_runtime['ack_count']}")
    print(f"hook_active_session_loaded={hook_runtime['active_session_loaded']}")
    print(f"hook_latest_ack_path={hook_runtime['latest_ack_path']}")
    print(f"hook_latest_ack_submitted_at={hook_runtime['latest_ack_submitted_at']}")
    print(f"hook_latest_ack_wake_id={hook_runtime['latest_ack_wake_id']}")
    print(f"hook_latest_ack_session_id={hook_runtime['latest_ack_session_id']}")
    print(f"hook_loaded_note={hook_runtime['loaded_note']}")
    print(f"service_name={service['name']}")
    print(f"service_active={service['active']}")
    print(f"service_enabled={service['enabled']}")
    print(f"service_unit={service['unit']}")
    print(f"service_log={service['log']}")
    print(f"trust={summary['trust']}")
    return 0


def run(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    root = resolve_root(args)
    if args.command == "after":
        return create_after(args, root)
    if args.command == "at":
        return create_at(args, root)
    if args.command == "app":
        return create_app(args, root)
    if args.command == "file":
        return create_file(args, root)
    if args.command == "changed":
        return create_changed(args, root)
    if args.command == "pid":
        return create_pid(args, root)
    if args.command == "list":
        return list_records(args, root)
    if args.command == "status":
        return status_command(args, root)
    if args.command == "show":
        return show_record(args, root)
    if args.command == "cancel":
        return cancel(args, root)
    if args.command == "archive":
        return archive(args, root)
    if args.command == "cleanup":
        return cleanup(args, root)
    if args.command == "schema":
        return schema_command(args)
    if args.command == "service":
        return service_command(args, root)
    if args.command == "hook":
        return hook_command(args, root)
    if args.command == "doctor":
        return doctor_command(args, root)
    raise WakeError(f"unknown command: {args.command}")


def main(argv: list[str] | None = None) -> int:
    try:
        return run(argv)
    except WakeError as exc:
        print(f"codex-wake: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
