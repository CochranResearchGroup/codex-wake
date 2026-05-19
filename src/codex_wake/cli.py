from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC
from pathlib import Path

from .records import (
    WakeError,
    all_records,
    archive_record,
    archive_terminal_records,
    build_record,
    cancel_record,
    capture_tmux_target,
    default_wake_root,
    find_record,
    format_utc,
    iter_records,
    normalize_prompt,
    parse_duration,
    parse_timestamp,
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

    file_cmd = subparsers.add_parser("file", help="create a wake when a file exists")
    file_cmd.add_argument("path")
    file_cmd.add_argument("prompt", nargs=argparse.REMAINDER)
    add_target_options(file_cmd)

    list_cmd = subparsers.add_parser("list", help="list wake records")
    list_cmd.add_argument("--json", action="store_true", dest="as_json")
    list_cmd.add_argument("--archived", action="store_true", help="include archived wake records")

    show = subparsers.add_parser("show", help="show one wake record")
    show.add_argument("wake_id")

    cancel = subparsers.add_parser("cancel", help="cancel a pending or firing wake")
    cancel.add_argument("wake_id")

    archive = subparsers.add_parser("archive", help="archive terminal wake records")
    archive.add_argument("wake_id", nargs="?", help="specific wake id to archive")
    archive.add_argument("--all-terminal", action="store_true", help="archive all submitted, failed, cancelled, and expired wakes")

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


def create_file(args: argparse.Namespace, root: Path) -> int:
    path = args.path.strip()
    if not path:
        raise WakeError("file path is required")
    predicate = {"type": "file_exists", "path": path}
    return create_record(args.prompt, predicate, root, utc_now(), args)


def create_record(prompt_parts: list[str], predicate: dict[str, str], root: Path, now, args: argparse.Namespace) -> int:
    prompt = normalize_prompt(prompt_parts)
    record = build_record(
        predicate=predicate,
        prompt=prompt,
        cwd=Path.cwd(),
        target=target_for_args(args),
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


def run(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    root = resolve_root(args)
    if args.command == "after":
        return create_after(args, root)
    if args.command == "at":
        return create_at(args, root)
    if args.command == "file":
        return create_file(args, root)
    if args.command == "list":
        return list_records(args, root)
    if args.command == "show":
        return show_record(args, root)
    if args.command == "cancel":
        return cancel(args, root)
    if args.command == "archive":
        return archive(args, root)
    if args.command == "service":
        return service_command(args, root)
    raise WakeError(f"unknown command: {args.command}")


def main(argv: list[str] | None = None) -> int:
    try:
        return run(argv)
    except WakeError as exc:
        print(f"codex-wake: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
