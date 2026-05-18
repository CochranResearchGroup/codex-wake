from __future__ import annotations

import json
import os
import re
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1
ACTIVE_STATUS_DIRS = ("pending", "firing", "submitted", "failed", "cancelled", "expired")
VALID_STATUSES = set(ACTIVE_STATUS_DIRS) | {"archived"}


class WakeError(ValueError):
    """Raised for invalid wake input."""


@dataclass(frozen=True)
class WakePath:
    path: Path
    record: dict[str, Any]


def utc_now() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def format_utc(value: datetime) -> str:
    return value.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_duration(value: str) -> timedelta:
    text = value.strip().lower()
    if not text:
        raise WakeError("duration is required")
    pattern = re.compile(r"(\d+)([smhd])")
    pos = 0
    total = timedelta()
    for match in pattern.finditer(text):
        if match.start() != pos:
            raise WakeError(f"invalid duration: {value}")
        amount = int(match.group(1))
        unit = match.group(2)
        if unit == "s":
            total += timedelta(seconds=amount)
        elif unit == "m":
            total += timedelta(minutes=amount)
        elif unit == "h":
            total += timedelta(hours=amount)
        elif unit == "d":
            total += timedelta(days=amount)
        pos = match.end()
    if pos != len(text) or total <= timedelta():
        raise WakeError(f"invalid duration: {value}")
    return total


def parse_timestamp(value: str) -> datetime:
    text = value.strip()
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise WakeError(f"invalid timestamp: {value}") from exc
    if parsed.tzinfo is None:
        raise WakeError("timestamp must include a timezone offset or Z")
    return parsed.astimezone(UTC).replace(microsecond=0)


def parse_utc_timestamp(value: str) -> datetime:
    parsed = parse_timestamp(value)
    return parsed.astimezone(UTC).replace(microsecond=0)


def make_wake_id(now: datetime | None = None) -> str:
    current = now or utc_now()
    stamp = current.astimezone(UTC).strftime("%Y%m%d_%H%M%S")
    return f"wake_{stamp}_{secrets.token_hex(2)}"


def default_wake_root(cwd: Path | None = None) -> Path:
    base = cwd or Path.cwd()
    return base / ".codex" / "wake"


def normalize_prompt(parts: list[str]) -> str:
    cleaned = list(parts)
    if cleaned and cleaned[0] == "--":
        cleaned = cleaned[1:]
    prompt = " ".join(cleaned).strip()
    if not prompt:
        raise WakeError("prompt is required after --")
    return prompt


def capture_tmux_target(env: dict[str, str] | None = None) -> dict[str, str]:
    source = env if env is not None else os.environ
    pane = source.get("TMUX_PANE")
    tmux_env = source.get("TMUX")
    if not pane:
        raise WakeError("TMUX_PANE is required to create a tmux-targeted wake")
    if not tmux_env:
        raise WakeError("TMUX is required to resolve the tmux socket")
    socket = tmux_env.split(",", 1)[0]
    if not socket:
        raise WakeError("TMUX did not contain a socket path")
    return {
        "transport": "tmux",
        "tmux_socket": socket,
        "pane": pane,
    }


def make_event(event_type: str, message: str, now: datetime | None = None) -> dict[str, Any]:
    return {
        "at": format_utc(now or utc_now()),
        "type": event_type,
        "message": message,
    }


def build_record(
    *,
    predicate: dict[str, Any],
    prompt: str,
    cwd: Path,
    target: dict[str, str],
    now: datetime | None = None,
) -> dict[str, Any]:
    current = now or utc_now()
    wake_id = make_wake_id(current)
    timestamp = format_utc(current)
    return {
        "schema_version": SCHEMA_VERSION,
        "id": wake_id,
        "created_at": timestamp,
        "updated_at": timestamp,
        "cwd": str(cwd.resolve()),
        "target": target,
        "predicate": predicate,
        "prompt": prompt,
        "status": "pending",
        "attempts": 0,
        "max_attempts": 3,
        "ack_timeout_seconds": 30,
        "next_attempt_at": predicate.get("due_at", timestamp),
        "events": [make_event("created", "Wake record created", current)],
    }


def ensure_runtime_dirs(root: Path) -> None:
    for name in ACTIVE_STATUS_DIRS + ("acks", "logs", "locks", "archive"):
        (root / name).mkdir(parents=True, exist_ok=True)


def write_record(root: Path, record: dict[str, Any]) -> Path:
    ensure_runtime_dirs(root)
    status = record.get("status")
    wake_id = record.get("id")
    if status not in VALID_STATUSES:
        raise WakeError(f"invalid wake status: {status}")
    if not isinstance(wake_id, str) or not wake_id:
        raise WakeError("wake record missing id")
    target_dir = root / status
    target_dir.mkdir(parents=True, exist_ok=True)
    final_path = target_dir / f"{wake_id}.json"
    temp_path = final_path.with_suffix(".json.tmp")
    temp_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temp_path.replace(final_path)
    return final_path


def iter_records(root: Path) -> list[WakePath]:
    results: list[WakePath] = []
    for status in ACTIVE_STATUS_DIRS:
        directory = root / status
        if not directory.exists():
            continue
        for path in sorted(directory.glob("*.json")):
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            results.append(WakePath(path=path, record=record))
    return sorted(results, key=lambda item: (item.record.get("created_at", ""), item.record.get("id", "")))


def find_record(root: Path, wake_id: str) -> WakePath:
    for item in iter_records(root):
        if item.record.get("id") == wake_id:
            return item
    raise WakeError(f"wake not found: {wake_id}")


def cancel_record(root: Path, wake_id: str, now: datetime | None = None) -> Path:
    found = find_record(root, wake_id)
    record = dict(found.record)
    status = record.get("status")
    if status in {"submitted", "failed", "cancelled", "expired", "archived"}:
        raise WakeError(f"cannot cancel wake in status {status}")
    current = now or utc_now()
    record["status"] = "cancelled"
    record["updated_at"] = format_utc(current)
    events = list(record.get("events") or [])
    events.append(make_event("cancelled", "Wake cancelled by operator", current))
    record["events"] = events
    destination = write_record(root, record)
    if found.path != destination and found.path.exists():
        found.path.unlink()
    return destination


def move_record(
    root: Path,
    found: WakePath,
    status: str,
    *,
    event_type: str,
    message: str,
    now: datetime | None = None,
    last_error: str | None = None,
) -> Path:
    if status not in VALID_STATUSES:
        raise WakeError(f"invalid wake status: {status}")
    current = now or utc_now()
    record = dict(found.record)
    record["status"] = status
    record["updated_at"] = format_utc(current)
    if last_error:
        record["last_error"] = last_error
    events = list(record.get("events") or [])
    events.append(make_event(event_type, message, current))
    record["events"] = events
    destination = write_record(root, record)
    if found.path != destination and found.path.exists():
        found.path.unlink()
    return destination
