from __future__ import annotations

import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


WAKE_ID_RE = re.compile(r"\bWAKE_TRIGGER_ID=([A-Za-z0-9_.:-]+)\b")
WAKE_ROOT_RE = re.compile(r"^WAKE_TRIGGER_ROOT=(.+)$", re.MULTILINE)
NON_RESUMABLE_STATUSES = {"archived", "cancelled", "expired", "failed"}


def utc_timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def extract_wake_id(prompt: str) -> str | None:
    match = WAKE_ID_RE.search(prompt)
    return match.group(1) if match else None


def extract_wake_root(prompt: str) -> Path | None:
    match = WAKE_ROOT_RE.search(prompt)
    if match is None:
        return None
    path = Path(match.group(1).strip()).expanduser()
    if not path.is_absolute():
        return None
    return path.resolve()


def wake_root_for_payload(payload: dict[str, Any], prompt: str = "") -> Path:
    explicit_root = extract_wake_root(prompt)
    if explicit_root is not None:
        return explicit_root
    cwd = Path(payload.get("cwd") or ".").resolve()
    return cwd / ".codex" / "wake"


def find_trigger_path(wake_root: Path, wake_id: str) -> Path | None:
    for status in ("firing", "pending", "submitted", "failed", "cancelled", "expired", "archive"):
        path = wake_root / status / f"{wake_id}.json"
        if path.exists():
            return path
    return None


def write_ack(wake_root: Path, wake_id: str, payload: dict[str, Any]) -> Path:
    ack_path = wake_root / "acks" / f"{wake_id}.submitted"
    ack_path.parent.mkdir(parents=True, exist_ok=True)
    ack = {
        "wake_id": wake_id,
        "submitted_at": utc_timestamp(),
        "turn_id": payload.get("turn_id"),
        "session_id": payload.get("session_id"),
    }
    ack_path.write_text(json.dumps(ack, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return ack_path


def additional_context_for_trigger(wake_id: str, trigger: dict[str, Any]) -> str:
    predicate = json.dumps(trigger.get("predicate"), indent=2, sort_keys=True)
    context_paths = trigger.get("context_paths") or []
    evidence_paths = trigger.get("evidence_paths") or []
    return (
        "A scheduled wake trigger fired.\n\n"
        f"Wake id: {wake_id}\n"
        f"Predicate:\n{predicate}\n\n"
        f"Original wake prompt:\n{trigger.get('prompt', '')}\n\n"
        f"Context paths: {json.dumps(context_paths, sort_keys=True)}\n"
        f"Evidence paths: {json.dumps(evidence_paths, sort_keys=True)}\n\n"
        "Before editing files, verify the predicate is still true and inspect any referenced logs, "
        "event files, context paths, or evidence paths. If the task is already complete, report that "
        "and stop."
    )


def missing_trigger_context(wake_id: str, wake_root: Path) -> str:
    return (
        f"Wake trigger {wake_id} was submitted, but its trigger file was not found. "
        f"Inspected wake root: {wake_root}. "
        "Do not infer that the wake is active. Ask the user if the wake state remains ambiguous."
    )


def terminal_trigger_context(wake_id: str, trigger: dict[str, Any], trigger_path: Path) -> str:
    status = trigger.get("status")
    previous_status = trigger.get("previous_status")
    previous = f", previous_status={previous_status}" if isinstance(previous_status, str) and previous_status else ""
    return (
        f"Wake trigger {wake_id} is terminal (status={status}{previous}). "
        f"Retained record: {trigger_path}. Do not resume the scheduled task from this prompt. "
        "Inspect the retained record and current task state only if reconciliation is needed."
    )


def hook_output(additional_context: str) -> dict[str, Any]:
    return {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": additional_context,
        }
    }


def handle_payload(payload: dict[str, Any]) -> dict[str, Any] | None:
    prompt = payload.get("prompt") or ""
    if not isinstance(prompt, str):
        return None
    wake_id = extract_wake_id(prompt)
    if not wake_id:
        return None
    root_marker_present = WAKE_ROOT_RE.search(prompt) is not None
    explicit_root = extract_wake_root(prompt)
    if root_marker_present and explicit_root is None:
        return hook_output(
            f"Wake trigger {wake_id} supplied an invalid WAKE_TRIGGER_ROOT. "
            "The root must be an absolute path. No acknowledgment was written."
        )
    wake_root = wake_root_for_payload(payload, prompt)
    trigger_path = find_trigger_path(wake_root, wake_id)
    if trigger_path is None:
        if explicit_root is None:
            # Preserve acknowledgment behavior for prompts created by older
            # releases, which carried only the wake id and relied on cwd.
            write_ack(wake_root, wake_id, payload)
        return hook_output(missing_trigger_context(wake_id, wake_root))
    write_ack(wake_root, wake_id, payload)
    try:
        trigger = json.loads(trigger_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return hook_output(
            f"Wake trigger {wake_id} was submitted, but its trigger file is not valid JSON. "
            "Inspect .codex/wake before continuing."
        )
    if trigger.get("status") in NON_RESUMABLE_STATUSES:
        return hook_output(terminal_trigger_context(wake_id, trigger, trigger_path))
    return hook_output(additional_context_for_trigger(wake_id, trigger))


def main(argv: list[str] | None = None) -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"codex-wake hook: invalid JSON input: {exc}", file=sys.stderr)
        return 2
    output = handle_payload(payload)
    if output is not None:
        print(json.dumps(output, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
