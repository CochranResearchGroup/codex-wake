from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .records import (
    WakeError,
    WakeLifecycleLock,
    WakePath,
    classify_record,
    default_wake_root,
    find_record,
    iter_records,
    move_record,
    parse_utc_timestamp,
    utc_now,
)
from .injector import TmuxRunner, dispatch_firing_record
from .signal_store import SQLiteSignalModule
from .signal_records import WakeRecordPublisher, current_reader_capability, signal_journal_path
from .signals import Degraded, EvaluationLimits, Expired, Matched
from .monitor import write_monitor_health
from .process import boot_id_value, process_exists, process_identity


@dataclass(frozen=True)
class PollResult:
    checked: int = 0
    fired: int = 0
    failed: int = 0
    pending: int = 0
    dispatched: int = 0
    requeued: int = 0
    submitted: int = 0


def format_poll_result(result: PollResult) -> str:
    return (
        f"checked={result.checked} fired={result.fired} "
        f"failed={result.failed} pending={result.pending} "
        f"dispatched={result.dispatched} submitted={result.submitted} requeued={result.requeued}"
    )


def poll_result_has_activity(result: PollResult) -> bool:
    return any(
        (
            result.checked,
            result.fired,
            result.failed,
            result.dispatched,
            result.submitted,
            result.requeued,
        )
    )


def poll_result_dict(result: PollResult) -> dict[str, int]:
    return {
        "checked": result.checked,
        "fired": result.fired,
        "failed": result.failed,
        "pending": result.pending,
        "dispatched": result.dispatched,
        "submitted": result.submitted,
        "requeued": result.requeued,
    }


def pending_records(root: Path) -> list[WakePath]:
    return [item for item in iter_records(root) if item.record.get("status") == "pending"]


def firing_records(root: Path) -> list[WakePath]:
    return [item for item in iter_records(root) if item.record.get("status") == "firing"]


def next_attempt_is_due(record: dict, now: datetime) -> tuple[bool, str]:
    next_attempt = record.get("next_attempt_at")
    if not isinstance(next_attempt, str) or not next_attempt:
        return True, ""
    try:
        due_at = parse_utc_timestamp(next_attempt)
    except WakeError:
        return True, ""
    if due_at > now:
        return False, next_attempt
    return True, next_attempt


def predicate_is_ready(record: dict, now: datetime) -> tuple[bool, str]:
    predicate = record.get("predicate")
    if not isinstance(predicate, dict):
        raise WakeError("predicate must be an object")
    predicate_type = predicate.get("type")
    if predicate_type == "not_before":
        due_at = predicate.get("due_at")
        if not isinstance(due_at, str) or not due_at:
            raise WakeError("not_before predicate requires due_at")
        return parse_utc_timestamp(due_at) <= now, f"not_before due_at {due_at} matched"
    if predicate_type == "file_exists":
        raw_path = predicate.get("path")
        if not isinstance(raw_path, str) or not raw_path:
            raise WakeError("file_exists predicate requires path")
        path = resolve_record_path(record, raw_path, "file_exists")
        return path.exists(), f"file_exists path {path} matched"
    if predicate_type == "file_changed":
        raw_path = predicate.get("path")
        if not isinstance(raw_path, str) or not raw_path:
            raise WakeError("file_changed predicate requires path")
        path = resolve_record_path(record, raw_path, "file_changed")
        try:
            stat = path.stat()
        except FileNotFoundError:
            return False, f"file_changed path {path} matched"
        registered_exists = bool(predicate.get("registered_exists"))
        registered_mtime_ns = predicate.get("registered_mtime_ns")
        registered_size = predicate.get("registered_size")
        if not registered_exists:
            return True, f"file_changed path {path} was created"
        if not isinstance(registered_mtime_ns, int) or not isinstance(registered_size, int):
            raise WakeError("file_changed predicate requires registered_mtime_ns and registered_size")
        changed = stat.st_mtime_ns != registered_mtime_ns or stat.st_size != registered_size
        return changed, f"file_changed path {path} changed"
    if predicate_type == "process_done":
        pid = predicate.get("pid")
        if not isinstance(pid, int) or pid <= 0:
            raise WakeError("process_done predicate requires positive integer pid")
        if not process_exists(pid):
            return True, f"process_done pid {pid} exited"
        registered_boot_id = predicate.get("registered_boot_id")
        if registered_boot_id is not None and not isinstance(registered_boot_id, str):
            raise WakeError("process_done registered_boot_id must be a string when present")
        if registered_boot_id:
            current_boot_id = boot_id_value()
            if current_boot_id and current_boot_id != registered_boot_id:
                return True, f"process_done pid {pid} was from previous boot"
        registered_start_time_ticks = predicate.get("registered_start_time_ticks")
        if registered_start_time_ticks is None:
            return False, f"process_done pid {pid} still exists"
        if not isinstance(registered_start_time_ticks, int):
            raise WakeError("process_done registered_start_time_ticks must be an integer when present")
        current_identity = process_identity(pid)
        if current_identity is None:
            return False, f"process_done pid {pid} still exists; process identity unavailable"
        if current_identity.get("start_time_ticks") != registered_start_time_ticks:
            return True, f"process_done pid {pid} no longer matches registered process"
        return False, f"process_done pid {pid} still matches registered process"
    raise WakeError(f"unsupported predicate type: {predicate_type}")


def resolve_record_path(record: dict, raw_path: str, predicate_type: str) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path
    cwd = record.get("cwd")
    if not isinstance(cwd, str) or not cwd:
        raise WakeError(f"relative {predicate_type} predicate requires record cwd")
    return Path(cwd) / path


def poll_once(
    root: Path,
    now: datetime | None = None,
    *,
    dispatch: bool = True,
    runner: TmuxRunner | None = None,
    ack_timeout_override: float | None = None,
    signal_runtime: SQLiteSignalModule | None = None,
) -> PollResult:
    current = now or utc_now()
    checked = fired = failed = pending = dispatched = requeued = submitted = 0
    if signal_runtime is None:
        journal = signal_journal_path(root)
        if journal.is_file():
            try:
                signal_runtime = SQLiteSignalModule.open_existing(
                    journal,
                    record_publisher=WakeRecordPublisher(
                        root,
                        current_reader_capability(root),
                    ),
                )
            except Exception:
                signal_runtime = None
    if signal_runtime is not None:
        firing_before = {item.record.get("id") for item in firing_records(root)}
        signal_runtime.reconcile_publications(limit=100, include_matches=False)
        firing_after = {item.record.get("id") for item in firing_records(root)}
        fired += len(firing_after - firing_before)
    terminal_signal_ids: set[str] = set()
    if signal_runtime is not None:
        for terminal in iter_records(root):
            status = terminal.record.get("status")
            wake_id = terminal.record.get("id")
            if (
                classify_record(terminal.record) == "signal_v2"
                and status in {"submitted", "failed", "cancelled", "expired", "archived"}
                and isinstance(wake_id, str)
            ):
                terminal_signal_ids.add(wake_id)
                signal_runtime.retire_terminal_record(terminal.record, now=current)
    for item in pending_records(root):
        checked += 1
        classification = classify_record(item.record)
        if classification == "hold":
            pending += 1
            continue
        if classification == "signal_v2":
            if signal_runtime is None:
                pending += 1
                continue
            wake_id = item.record.get("id")
            if wake_id in terminal_signal_ids:
                pending += 1
                continue
            with WakeLifecycleLock(root, wake_id):
                try:
                    current_item = find_record(root, wake_id)
                except WakeError:
                    continue
                if (
                    classify_record(current_item.record) != "signal_v2"
                    or current_item.record.get("status") != "pending"
                ):
                    continue
                armed = signal_runtime.load_armed_signal(wake_id)
                if armed is None:
                    terminal_status = signal_runtime.terminal_status(wake_id)
                    if terminal_status in {"cancelled", "expired", "failed", "submitted"}:
                        move_record(
                            root,
                            current_item,
                            terminal_status,
                            event_type=terminal_status,
                            message=f"Signal wake reconciled to durable {terminal_status} state",
                            now=current,
                        )
                    else:
                        pending += 1
                    continue
                outcome = signal_runtime.evaluate(
                    wake_id,
                    armed,
                    current,
                    EvaluationLimits(100),
                )
                if isinstance(outcome, Matched):
                    signal_runtime.reconcile_match_publication(wake_id)
                    if (root / "firing" / f"{wake_id}.json").is_file():
                        fired += 1
                    else:
                        pending += 1
                elif isinstance(outcome, Expired):
                    expired = signal_runtime.expire_unreserved(wake_id, now=current)
                    if expired is True:
                        move_record(
                            root,
                            current_item,
                            "expired",
                            event_type="expired",
                            message="Signal wake expired before a match was reserved",
                            now=current,
                        )
                    else:
                        pending += 1
                else:
                    pending += 1
            continue
        due_for_attempt, _next_attempt = next_attempt_is_due(item.record, current)
        if not due_for_attempt:
            pending += 1
            continue
        try:
            ready, message = predicate_is_ready(item.record, current)
        except WakeError as exc:
            move_record(
                root,
                item,
                "failed",
                event_type="failed",
                message=str(exc),
                now=current,
                last_error=str(exc),
            )
            failed += 1
            continue
        if ready:
            move_record(
                root,
                item,
                "firing",
                event_type="predicate_matched",
                message=message,
                now=current,
            )
            fired += 1
        else:
            pending += 1
    if dispatch:
        for item in firing_records(root):
            result = dispatch_firing_record(
                root,
                item,
                runner=runner,
                now=current,
                ack_timeout_override=ack_timeout_override,
                signal_authorizer=(
                    signal_runtime.authorize_firing_record
                    if signal_runtime is not None
                    else None
                ),
            )
            if result.status == "skipped":
                continue
            dispatched += 1
            if result.status == "submitted":
                submitted += 1
            elif result.status == "requeued":
                requeued += 1
            elif result.status == "failed":
                failed += 1
    return PollResult(
        checked=checked,
        fired=fired,
        failed=failed,
        pending=pending,
        dispatched=dispatched,
        requeued=requeued,
        submitted=submitted,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="codex-waked")
    parser.add_argument(
        "--wake-root",
        type=Path,
        default=None,
        help="wake runtime root; defaults to .codex/wake under the current directory",
    )
    parser.add_argument("--once", action="store_true", help="run one polling pass and exit")
    parser.add_argument("--interval", type=float, default=5.0, help="poll interval in seconds")
    parser.add_argument("--no-dispatch", action="store_true", help="evaluate predicates but do not dispatch firing records")
    parser.add_argument(
        "--ack-timeout",
        type=float,
        default=None,
        help="override ack wait timeout in seconds",
    )
    return parser


def run(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    root = (args.wake_root or default_wake_root()).resolve()
    if args.once:
        result = poll_once(root, dispatch=not args.no_dispatch, ack_timeout_override=args.ack_timeout)
        write_monitor_health(
            wake_root=root,
            repo_root=Path.cwd(),
            source="codex-waked",
            mode="once",
            poll_result=poll_result_dict(result),
        )
        print(format_poll_result(result))
        return 0
    if args.interval <= 0:
        raise WakeError("--interval must be greater than zero")
    while True:
        result = poll_once(root, dispatch=not args.no_dispatch, ack_timeout_override=args.ack_timeout)
        write_monitor_health(
            wake_root=root,
            repo_root=Path.cwd(),
            source="codex-waked",
            mode="loop",
            poll_result=poll_result_dict(result),
        )
        if poll_result_has_activity(result):
            print(format_poll_result(result), flush=True)
        time.sleep(args.interval)


def main(argv: list[str] | None = None) -> int:
    try:
        return run(argv)
    except WakeError as exc:
        print(f"codex-waked: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
