from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Mapping, Protocol

from .records import WakeError, WakePath, append_event, format_utc, replace_record, utc_now


OPENCLAW_GATEWAY_BACKOFF_SECONDS = (60, 300)
OPENCLAW_CMD_ENV = "CODEX_WAKE_OPENCLAW_CMD"
DEFAULT_OPENCLAW_TIMEOUT_SECONDS = 600
DEFAULT_GATEWAY_TIMEOUT_MS = 180_000

_ENV_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_PLACEHOLDER_TOKENS = (
    "noop-smoke-test",
    "placeholder",
    "dummy-session",
    "fake-session",
    "test-session",
    "session_abc",
    "thread_abc",
)


@dataclass(frozen=True)
class OpenClawGatewayDispatchResult:
    status: str
    message: str


class OpenClawGatewayRunner(Protocol):
    def run(self, command: list[str], *, timeout: float) -> subprocess.CompletedProcess[str]:
        ...


class SubprocessOpenClawGatewayRunner:
    def run(self, command: list[str], *, timeout: float) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            command,
            check=False,
            text=True,
            capture_output=True,
            timeout=timeout,
        )


def resolve_openclaw_cmd(
    raw: str | None = None,
    *,
    env: Mapping[str, str] | None = None,
    path: str | None = None,
    required: bool = False,
) -> str:
    source_env = env if env is not None else os.environ
    candidate = raw or source_env.get(OPENCLAW_CMD_ENV) or ""
    if candidate:
        if "/" in candidate:
            resolved = Path(candidate).expanduser()
            if resolved.exists():
                return str(resolved.resolve())
            if required:
                raise WakeError(f"configured OpenClaw CLI path does not exist: {candidate}")
            return ""
        found = shutil.which(candidate, path=path)
        if found:
            return str(Path(found).resolve())
        if required:
            raise WakeError(f"OpenClaw CLI command not found: {candidate}")
        return ""
    found = shutil.which("openclaw", path=path)
    if found:
        return str(Path(found).resolve())
    if required:
        raise WakeError(f"OpenClaw CLI command not found: openclaw; configure {OPENCLAW_CMD_ENV}")
    return ""


def build_openclaw_gateway_target(
    *,
    agent_id: str,
    session_key: str,
    gateway_url: str | None = None,
    token_env: str | None = None,
    password_env: str | None = None,
    openclaw_cmd: str | None = None,
    workspace: str | None = None,
    channel_id: str | None = None,
    thread_ts: str | None = None,
    channel_provider: str = "slack",
    deliver: bool = False,
    timeout_seconds: int = DEFAULT_OPENCLAW_TIMEOUT_SECONDS,
    gateway_timeout_ms: int = DEFAULT_GATEWAY_TIMEOUT_MS,
    reply_channel: str | None = None,
    reply_to: str | None = None,
    reply_account_id: str | None = None,
    model: str | None = None,
    thinking: str | None = None,
) -> dict[str, Any]:
    target: dict[str, Any] = {
        "transport": "openclaw_gateway",
        "gateway": {},
        "openclaw": {
            "agent_id": agent_id,
            "session_key": session_key,
        },
        "dispatch": {
            "deliver": bool(deliver),
            "timeout_seconds": int(timeout_seconds),
            "gateway_timeout_ms": int(gateway_timeout_ms),
        },
    }
    if gateway_url:
        target["gateway"]["url"] = gateway_url
    if token_env:
        target["gateway"]["token_env"] = token_env
    if password_env:
        target["gateway"]["password_env"] = password_env
    if openclaw_cmd:
        target["openclaw_cmd"] = resolve_openclaw_cmd(openclaw_cmd, required=True)
    channel: dict[str, Any] = {}
    if channel_provider:
        channel["provider"] = channel_provider
    if workspace:
        channel["workspace"] = workspace
    if channel_id:
        channel["channel_id"] = channel_id
    if thread_ts:
        channel["thread_ts"] = thread_ts
    if channel:
        target["openclaw"]["channel"] = channel
    dispatch = target["dispatch"]
    if reply_channel:
        dispatch["reply_channel"] = reply_channel
    if reply_to:
        dispatch["reply_to"] = reply_to
    if reply_account_id:
        dispatch["reply_account_id"] = reply_account_id
    if model:
        dispatch["model"] = model
    if thinking:
        dispatch["thinking"] = thinking
    openclaw_gateway_target({"target": target})
    return target


def openclaw_gateway_target(record: dict[str, Any]) -> dict[str, Any]:
    target = record.get("target")
    if not isinstance(target, dict):
        raise WakeError("record target must be an object")
    if target.get("transport") != "openclaw_gateway":
        raise WakeError(f"unsupported target transport: {target.get('transport')}")
    gateway = target.get("gateway", {})
    openclaw = target.get("openclaw")
    dispatch = target.get("dispatch", {})
    if not isinstance(gateway, dict):
        raise WakeError("openclaw_gateway target gateway must be an object")
    if not isinstance(openclaw, dict):
        raise WakeError("openclaw_gateway target openclaw must be an object")
    if not isinstance(dispatch, dict):
        raise WakeError("openclaw_gateway target dispatch must be an object")
    agent_id = _required_text(openclaw, "agent_id", "openclaw_gateway target requires openclaw.agent_id")
    session_key = _required_text(openclaw, "session_key", "openclaw_gateway target requires openclaw.session_key")
    _validate_agent_session(agent_id, session_key)
    _validate_optional_text(gateway, "url", "gateway.url")
    _validate_env_ref(gateway, "token_env")
    _validate_env_ref(gateway, "password_env")
    _validate_optional_text(target, "openclaw_cmd", "openclaw_cmd")
    _validate_bool(dispatch, "deliver")
    _validate_positive_int(dispatch, "timeout_seconds")
    _validate_positive_int(dispatch, "gateway_timeout_ms")
    for key in ("reply_channel", "reply_to", "reply_account_id", "model", "thinking"):
        _validate_optional_text(dispatch, key, f"dispatch.{key}")
    channel = openclaw.get("channel")
    if channel is not None:
        if not isinstance(channel, dict):
            raise WakeError("openclaw_gateway target openclaw.channel must be an object")
        for key in ("provider", "workspace", "channel_id", "thread_ts"):
            _validate_optional_text(channel, key, f"openclaw.channel.{key}")
    return target


def openclaw_wake_prompt(root: Path, record: dict[str, Any]) -> str:
    wake_id = record.get("id")
    if not isinstance(wake_id, str) or not wake_id:
        raise WakeError("wake record missing id")
    cwd = record.get("cwd")
    cwd_line = cwd if isinstance(cwd, str) and cwd else ""
    return "\n".join(
        [
            f"WAKE_TRIGGER_ID={wake_id}",
            "Resume the scheduled wake task.",
            f"Wake root: {root.resolve()}",
            f"Record cwd: {cwd_line}",
            "First inspect the wake record, verify the predicate is still true, and continue idempotently.",
            "",
        ]
    )


def dispatch_openclaw_gateway_record(
    root: Path,
    found: WakePath,
    *,
    runner: OpenClawGatewayRunner | None = None,
    now: datetime | None = None,
) -> OpenClawGatewayDispatchResult:
    current = now or utc_now()
    record = dict(found.record)
    if record.get("status") != "firing":
        return OpenClawGatewayDispatchResult("skipped", "record is not firing")
    wake_id = record.get("id")
    if not isinstance(wake_id, str) or not wake_id:
        raise WakeError("wake record missing id")
    try:
        target = openclaw_gateway_target(record)
    except WakeError as exc:
        record["status"] = "failed"
        record["updated_at"] = format_utc(current)
        record["last_error"] = str(exc)
        record = append_event(record, "failed", str(exc), current)
        replace_record(root, found, record)
        return OpenClawGatewayDispatchResult("failed", str(exc))

    gateway_runner = runner or SubprocessOpenClawGatewayRunner()
    attempt = int(record.get("attempts") or 0) + 1
    record["attempts"] = attempt
    record["updated_at"] = format_utc(current)
    record = append_event(
        record,
        "openclaw_gateway_dispatch_attempt",
        "Starting OpenClaw Gateway wake turn",
        current,
        attempt=attempt,
        agent_id=target["openclaw"]["agent_id"],
        session_key=target["openclaw"]["session_key"],
    )
    replace_record(root, found, record)
    active_path = WakePath(root / "firing" / f"{wake_id}.json", record)
    try:
        preflight_payload = run_openclaw_gateway_preflight(target, gateway_runner)
        preflight = openclaw_gateway_preflight_metadata(preflight_payload)
        record = dict(record)
        record["openclaw_gateway_preflight"] = preflight
        record = append_event(
            record,
            "openclaw_gateway_preflight",
            "OpenClaw Gateway RPC preflight succeeded",
            current,
            **preflight,
        )
        replace_record(root, active_path, record)
        active_path = WakePath(root / "firing" / f"{wake_id}.json", record)
        dispatch_payload = run_openclaw_gateway_agent_call(root, record, target, gateway_runner)
        metadata = openclaw_gateway_dispatch_metadata(dispatch_payload, record)
    except subprocess.TimeoutExpired as exc:
        return requeue_openclaw_gateway_record(root, active_path, record, f"OpenClaw Gateway command timed out after {exc.timeout} seconds", current, "openclaw_gateway_timeout")
    except WakeError as exc:
        return requeue_openclaw_gateway_record(root, active_path, record, str(exc), current, "openclaw_gateway_dispatch_failed")

    record["status"] = "submitted"
    record["updated_at"] = format_utc(current)
    record["dispatch_result"] = metadata
    record = append_event(
        record,
        "openclaw_gateway_dispatch_result",
        "OpenClaw Gateway agent call accepted wake prompt",
        current,
        **metadata,
    )
    replace_record(root, active_path, record)
    return OpenClawGatewayDispatchResult("submitted", "OpenClaw Gateway agent call accepted")


def run_openclaw_gateway_preflight(
    target: dict[str, Any],
    runner: OpenClawGatewayRunner,
) -> dict[str, Any]:
    timeout_ms = int(target["dispatch"].get("gateway_timeout_ms") or DEFAULT_GATEWAY_TIMEOUT_MS)
    command = openclaw_gateway_status_command(target)
    result = runner.run(command, timeout=command_timeout_seconds(timeout_ms))
    if result.returncode != 0:
        raise WakeError(f"OpenClaw Gateway preflight failed: {_compact_output(result.stderr or result.stdout)}")
    return parse_json_output(result.stdout, "OpenClaw Gateway preflight")


def run_openclaw_gateway_agent_call(
    root: Path,
    record: dict[str, Any],
    target: dict[str, Any],
    runner: OpenClawGatewayRunner,
) -> dict[str, Any]:
    timeout_ms = int(target["dispatch"].get("gateway_timeout_ms") or DEFAULT_GATEWAY_TIMEOUT_MS)
    command = openclaw_gateway_call_command(root, record, target)
    result = runner.run(command, timeout=command_timeout_seconds(timeout_ms))
    if result.returncode != 0:
        raise WakeError(f"OpenClaw Gateway agent call failed: {_compact_output(result.stderr or result.stdout)}")
    payload = parse_json_output(result.stdout, "OpenClaw Gateway agent call")
    status = str(payload.get("status") or "").lower()
    if payload.get("ok") is not True and status not in {"ok", "success"}:
        raise WakeError(f"OpenClaw Gateway agent call returned status {payload.get('status') or payload.get('ok')}")
    return payload


def openclaw_gateway_status_command(target: dict[str, Any]) -> list[str]:
    timeout_ms = int(target["dispatch"].get("gateway_timeout_ms") or DEFAULT_GATEWAY_TIMEOUT_MS)
    command = [
        openclaw_command_name(target),
        "gateway",
        "status",
        "--require-rpc",
        "--json",
        "--timeout",
        str(timeout_ms),
    ]
    command.extend(gateway_cli_args(target))
    return command


def openclaw_gateway_call_command(root: Path, record: dict[str, Any], target: dict[str, Any]) -> list[str]:
    timeout_ms = int(target["dispatch"].get("gateway_timeout_ms") or DEFAULT_GATEWAY_TIMEOUT_MS)
    params = openclaw_gateway_agent_params(root, record, target)
    command = [
        openclaw_command_name(target),
        "gateway",
        "call",
        "--expect-final",
        "--json",
        "--timeout",
        str(timeout_ms),
    ]
    command.extend(gateway_cli_args(target))
    command.extend(["agent", "--params", json.dumps(params, separators=(",", ":"), sort_keys=True)])
    return command


def openclaw_gateway_agent_params(root: Path, record: dict[str, Any], target: dict[str, Any]) -> dict[str, Any]:
    wake_id = record.get("id")
    if not isinstance(wake_id, str) or not wake_id:
        raise WakeError("wake record missing id")
    dispatch = target["dispatch"]
    params: dict[str, Any] = {
        "message": openclaw_wake_prompt(root, record),
        "agentId": target["openclaw"]["agent_id"],
        "sessionKey": target["openclaw"]["session_key"],
        "deliver": bool(dispatch.get("deliver", False)),
        "timeout": int(dispatch.get("timeout_seconds") or DEFAULT_OPENCLAW_TIMEOUT_SECONDS),
        "idempotencyKey": str(dispatch.get("idempotency_key") or f"codex-wake:{wake_id}"),
        "expectFinal": True,
    }
    optional_mapping = {
        "reply_channel": "replyChannel",
        "reply_to": "replyTo",
        "reply_account_id": "replyAccountId",
        "model": "model",
        "thinking": "thinking",
    }
    for source, destination in optional_mapping.items():
        value = dispatch.get(source)
        if isinstance(value, str) and value:
            params[destination] = value
    return params


def openclaw_command_name(target: dict[str, Any]) -> str:
    configured = target.get("openclaw_cmd")
    if isinstance(configured, str) and configured:
        return configured
    return resolve_openclaw_cmd() or "openclaw"


def gateway_cli_args(target: dict[str, Any]) -> list[str]:
    gateway = target.get("gateway") or {}
    args: list[str] = []
    url = gateway.get("url")
    if isinstance(url, str) and url:
        args.extend(["--url", url])
    token_env = gateway.get("token_env")
    if isinstance(token_env, str) and token_env:
        token = os.environ.get(token_env)
        if not token:
            raise WakeError(f"OpenClaw Gateway token env var is not set: {token_env}")
        args.extend(["--token", token])
    password_env = gateway.get("password_env")
    if isinstance(password_env, str) and password_env:
        password = os.environ.get(password_env)
        if not password:
            raise WakeError(f"OpenClaw Gateway password env var is not set: {password_env}")
        args.extend(["--password", password])
    return args


def command_timeout_seconds(timeout_ms: int) -> float:
    return max(1.0, (timeout_ms / 1000.0) + 5.0)


def parse_json_output(text: str, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(text.strip() or "{}")
    except json.JSONDecodeError as exc:
        raise WakeError(f"{label} returned non-JSON output") from exc
    if not isinstance(payload, dict):
        raise WakeError(f"{label} returned non-object JSON")
    return payload


def openclaw_gateway_preflight_metadata(payload: dict[str, Any]) -> dict[str, Any]:
    metadata: dict[str, Any] = {"transport": "openclaw_gateway"}
    for key in ("version", "url", "status"):
        value = payload.get(key)
        if isinstance(value, str):
            metadata[key] = value
    rpc = payload.get("rpc")
    if isinstance(rpc, dict):
        ok = rpc.get("ok")
        if isinstance(ok, bool):
            metadata["rpc_ok"] = ok
        capability = rpc.get("capability")
        if isinstance(capability, str):
            metadata["rpc_capability"] = capability
    if "rpc_ok" not in metadata:
        ok = payload.get("ok")
        if isinstance(ok, bool):
            metadata["rpc_ok"] = ok
    return metadata


def openclaw_gateway_dispatch_metadata(payload: dict[str, Any], record: dict[str, Any]) -> dict[str, Any]:
    wake_id = str(record.get("id") or "")
    target = openclaw_gateway_target(record)
    metadata: dict[str, Any] = {
        "transport": "openclaw_gateway",
        "gateway_method": "agent",
        "agent_id": target["openclaw"]["agent_id"],
        "session_key": target["openclaw"]["session_key"],
    }
    run_id = payload.get("runId") or payload.get("run_id")
    if isinstance(run_id, str):
        metadata["run_id"] = run_id
    status = payload.get("status")
    if isinstance(status, str):
        metadata["status"] = status
    summary = payload.get("summary")
    if isinstance(summary, str):
        metadata["summary"] = summary
    result = payload.get("result")
    if isinstance(result, dict):
        _merge_result_metadata(metadata, result, wake_id)
    return metadata


def _merge_result_metadata(metadata: dict[str, Any], result: dict[str, Any], wake_id: str) -> None:
    meta = result.get("meta")
    if isinstance(meta, dict):
        agent_meta = meta.get("agentMeta")
        if isinstance(agent_meta, dict):
            session_id = agent_meta.get("sessionId")
            if isinstance(session_id, str):
                metadata["session_id"] = session_id
        for key in ("provider", "model"):
            value = meta.get(key)
            if isinstance(value, str):
                metadata[key] = value
    final_text = result.get("finalAssistantVisibleText")
    metadata["final_text_summary"] = text_summary(final_text, wake_id)
    payloads = result.get("payloads")
    if isinstance(payloads, list):
        metadata["payload_count"] = len(payloads)
        metadata["payload_text_summary"] = payload_text_summary(payloads, wake_id)


def text_summary(value: object, wake_id: str) -> dict[str, Any]:
    if not isinstance(value, str):
        return {"present": False}
    return {
        "present": True,
        "length": len(value),
        "wake_marker_present": wake_id in value,
    }


def payload_text_summary(payloads: list[object], wake_id: str) -> dict[str, Any]:
    text_count = 0
    total_length = 0
    wake_marker_present = False
    for payload in payloads:
        if not isinstance(payload, dict):
            continue
        text = payload.get("text")
        if not isinstance(text, str):
            continue
        text_count += 1
        total_length += len(text)
        wake_marker_present = wake_marker_present or wake_id in text
    return {
        "text_count": text_count,
        "total_length": total_length,
        "wake_marker_present": wake_marker_present,
    }


def requeue_openclaw_gateway_record(
    root: Path,
    found: WakePath,
    record: dict[str, Any],
    message: str,
    now: datetime,
    event_type: str,
) -> OpenClawGatewayDispatchResult:
    attempts = int(record.get("attempts") or 0)
    max_attempts = int(record.get("max_attempts") or 3)
    record["updated_at"] = format_utc(now)
    record["last_error"] = message
    record = append_event(record, event_type, message, now, attempt=attempts)
    if attempts >= max_attempts:
        record["status"] = "failed"
        record = append_event(record, "failed", "Maximum OpenClaw Gateway dispatch attempts reached", now, attempt=attempts)
        replace_record(root, found, record)
        return OpenClawGatewayDispatchResult("failed", message)
    delay = openclaw_gateway_backoff_for_attempt(attempts)
    record["status"] = "pending"
    record["next_attempt_at"] = format_utc(now + timedelta(seconds=delay))
    record = append_event(record, "requeued", f"Wake requeued after {delay} seconds", now, attempt=attempts)
    replace_record(root, found, record)
    return OpenClawGatewayDispatchResult("requeued", message)


def openclaw_gateway_backoff_for_attempt(attempt: int) -> int:
    if attempt <= 1:
        return OPENCLAW_GATEWAY_BACKOFF_SECONDS[0]
    return OPENCLAW_GATEWAY_BACKOFF_SECONDS[min(attempt - 1, len(OPENCLAW_GATEWAY_BACKOFF_SECONDS) - 1)]


def _required_text(source: dict[str, Any], key: str, message: str) -> str:
    value = source.get(key)
    if not isinstance(value, str) or not value.strip():
        raise WakeError(message)
    _reject_placeholder(value, key)
    return value.strip()


def _validate_optional_text(source: dict[str, Any], key: str, label: str) -> None:
    value = source.get(key)
    if value is not None and (not isinstance(value, str) or not value.strip()):
        raise WakeError(f"{label} must be a non-empty string when provided")
    if isinstance(value, str):
        _reject_placeholder(value, label)


def _validate_env_ref(source: dict[str, Any], key: str) -> None:
    value = source.get(key)
    if value is None:
        return
    if not isinstance(value, str) or not _ENV_NAME_RE.match(value):
        raise WakeError(f"gateway.{key} must be an environment variable name")


def _validate_bool(source: dict[str, Any], key: str) -> None:
    value = source.get(key)
    if value is not None and not isinstance(value, bool):
        raise WakeError(f"dispatch.{key} must be a boolean")


def _validate_positive_int(source: dict[str, Any], key: str) -> None:
    value = source.get(key)
    if value is None:
        return
    if not isinstance(value, int) or value <= 0:
        raise WakeError(f"dispatch.{key} must be a positive integer")


def _validate_agent_session(agent_id: str, session_key: str) -> None:
    if not session_key.startswith("agent:"):
        raise WakeError("openclaw_gateway session_key must use the durable agent:<agent_id>:... form")
    parts = session_key.split(":")
    if len(parts) < 3 or not parts[2]:
        raise WakeError("openclaw_gateway session_key must include a session suffix")
    if parts[1] != agent_id:
        raise WakeError("openclaw_gateway session_key agent id does not match openclaw.agent_id")
    if session_key.startswith("thread_"):
        raise WakeError("openclaw_gateway session_key must not be an app-server thread id")


def _reject_placeholder(value: str, label: str) -> None:
    lowered = value.strip().lower()
    for token in _PLACEHOLDER_TOKENS:
        if token in lowered:
            raise WakeError(f"{label} contains unsupported placeholder value: {token}")


def _compact_output(text: str, limit: int = 500) -> str:
    cleaned = " ".join(text.strip().split())
    if not cleaned:
        return "no output"
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3] + "..."
