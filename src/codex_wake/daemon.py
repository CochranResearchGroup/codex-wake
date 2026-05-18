from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .records import (
    WakeError,
    WakePath,
    default_wake_root,
    iter_records,
    move_record,
    parse_utc_timestamp,
    utc_now,
)


@dataclass(frozen=True)
class PollResult:
    checked: int = 0
    fired: int = 0
    failed: int = 0
    pending: int = 0


def pending_records(root: Path) -> list[WakePath]:
    return [item for item in iter_records(root) if item.record.get("status") == "pending"]


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
        path = Path(raw_path)
        if not path.is_absolute():
            cwd = record.get("cwd")
            if not isinstance(cwd, str) or not cwd:
                raise WakeError("relative file_exists predicate requires record cwd")
            path = Path(cwd) / path
        return path.exists(), f"file_exists path {path} matched"
    raise WakeError(f"unsupported predicate type: {predicate_type}")


def poll_once(root: Path, now: datetime | None = None) -> PollResult:
    current = now or utc_now()
    checked = fired = failed = pending = 0
    for item in pending_records(root):
        checked += 1
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
    return PollResult(checked=checked, fired=fired, failed=failed, pending=pending)


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
    return parser


def run(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    root = (args.wake_root or default_wake_root()).resolve()
    if args.once:
        result = poll_once(root)
        print(
            f"checked={result.checked} fired={result.fired} "
            f"failed={result.failed} pending={result.pending}"
        )
        return 0
    if args.interval <= 0:
        raise WakeError("--interval must be greater than zero")
    while True:
        poll_once(root)
        time.sleep(args.interval)


def main(argv: list[str] | None = None) -> int:
    try:
        return run(argv)
    except WakeError as exc:
        print(f"codex-waked: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
