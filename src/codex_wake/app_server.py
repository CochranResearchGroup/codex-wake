from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol

from .injector import canonical_prompt
from .records import WakeError, WakePath, append_event, format_utc, replace_record, utc_now


class AppServerClient(Protocol):
    def initialize(self) -> dict[str, Any]:
        ...

    def resume_thread(self, thread_id: str, cwd: str | None = None) -> dict[str, Any]:
        ...

    def start_turn(self, thread_id: str, prompt: str, cwd: str | None = None) -> dict[str, Any]:
        ...

    def close(self) -> None:
        ...


@dataclass(frozen=True)
class AppServerDispatchResult:
    status: str
    message: str


class StdioAppServerClient:
    def __init__(self, command: list[str] | None = None, timeout_seconds: float = 30.0) -> None:
        self.command = command or ["codex", "app-server", "--listen", "stdio://"]
        self.timeout_seconds = timeout_seconds
        self._next_id = 1
        self.process = subprocess.Popen(
            self.command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    def close(self) -> None:
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.kill()

    def request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        if self.process.stdin is None or self.process.stdout is None:
            raise WakeError("app-server stdio pipes are unavailable")
        request_id = self._next_id
        self._next_id += 1
        payload = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params,
        }
        self.process.stdin.write(json.dumps(payload) + "\n")
        self.process.stdin.flush()
        while True:
            line = self.process.stdout.readline()
            if not line:
                raise WakeError(f"app-server closed stdout while waiting for {method}")
            message = json.loads(line)
            if message.get("id") != request_id:
                continue
            if "error" in message:
                raise WakeError(f"app-server {method} failed: {message['error']}")
            result = message.get("result")
            if not isinstance(result, dict):
                raise WakeError(f"app-server {method} returned non-object result")
            return result

    def initialize(self) -> dict[str, Any]:
        return self.request(
            "initialize",
            {
                "clientInfo": {
                    "name": "codex-wake",
                    "title": "Codex Wake",
                    "version": "0.1.0",
                },
                "capabilities": {"experimentalApi": True},
            },
        )

    def resume_thread(self, thread_id: str, cwd: str | None = None) -> dict[str, Any]:
        params: dict[str, Any] = {"threadId": thread_id, "persistExtendedHistory": False}
        if cwd:
            params["cwd"] = cwd
        return self.request("thread/resume", params)

    def start_turn(self, thread_id: str, prompt: str, cwd: str | None = None) -> dict[str, Any]:
        params: dict[str, Any] = {
            "threadId": thread_id,
            "input": [{"type": "text", "text": prompt, "text_elements": []}],
        }
        if cwd:
            params["cwd"] = cwd
        return self.request("turn/start", params)


def app_server_target(record: dict[str, Any]) -> dict[str, Any]:
    target = record.get("target")
    if not isinstance(target, dict):
        raise WakeError("record target must be an object")
    if target.get("transport") != "app-server":
        raise WakeError(f"unsupported target transport: {target.get('transport')}")
    endpoint = target.get("endpoint", "stdio://")
    if endpoint != "stdio://":
        raise WakeError("only app-server stdio:// transport is implemented")
    thread_id = target.get("thread_id")
    if not isinstance(thread_id, str) or not thread_id:
        raise WakeError("app-server target requires thread_id")
    return target


def dispatch_app_server_record(
    root: Path,
    found: WakePath,
    *,
    client: AppServerClient | None = None,
    now: datetime | None = None,
) -> AppServerDispatchResult:
    current = now or utc_now()
    record = dict(found.record)
    if record.get("status") != "firing":
        return AppServerDispatchResult("skipped", "record is not firing")
    wake_id = record.get("id")
    if not isinstance(wake_id, str) or not wake_id:
        raise WakeError("wake record missing id")
    try:
        target = app_server_target(record)
        thread_id = target["thread_id"]
        cwd = record.get("cwd") if isinstance(record.get("cwd"), str) else None
        app_client = client or StdioAppServerClient(command=target.get("command"))
        try:
            app_client.initialize()
            app_client.resume_thread(thread_id, cwd=cwd)
            app_client.start_turn(thread_id, canonical_prompt(wake_id), cwd=cwd)
        finally:
            if client is None:
                app_client.close()
    except WakeError as exc:
        record["status"] = "failed"
        record["updated_at"] = format_utc(current)
        record["last_error"] = str(exc)
        record = append_event(record, "failed", str(exc), current)
        replace_record(root, found, record)
        return AppServerDispatchResult("failed", str(exc))
    record["status"] = "submitted"
    record["updated_at"] = format_utc(current)
    record = append_event(record, "dispatch_attempt", "Starting app-server wake turn", current)
    record = append_event(record, "ack_observed", "App-server turn/start accepted wake prompt", current)
    replace_record(root, found, record)
    return AppServerDispatchResult("submitted", "turn/start accepted")
