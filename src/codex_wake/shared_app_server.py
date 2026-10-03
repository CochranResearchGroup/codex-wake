"""Bounded read-only metadata access to an existing shared app-server.

This client deliberately has no lifecycle or turn API. Discovery must never
start a daemon, subscribe to a thread, or load a saved conversation.
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
import stat
import time
from typing import Any, Callable

from .records import WakeError


class SharedSourceError(WakeError):
    """The shared source cannot establish a complete observation."""


class SharedAppServerReader:
    ALLOWED_METHODS = frozenset({"initialize", "thread/loaded/list", "thread/read"})

    def __init__(self, endpoint: str, *, timeout: float = 10.0,
                 connector: Callable[..., Any] | None = None):
        if not math.isfinite(timeout) or timeout <= 0 or timeout > 60:
            raise WakeError("source timeout must be positive and at most 60 seconds")
        if not endpoint.startswith("unix://") or not endpoint[7:]:
            raise SharedSourceError("an explicit existing unix://PATH endpoint is required")
        self.path = Path(endpoint[7:])
        if not self.path.is_absolute():
            raise WakeError("shared app-server socket path must be absolute")
        self.timeout = timeout
        self.connector = connector
        self.connection: Any = None
        self.deadline = 0.0
        self.sequence = 0

    def __enter__(self) -> SharedAppServerReader:
        self.deadline = time.monotonic() + self.timeout
        try:
            info = self.path.lstat()
            if not stat.S_ISSOCK(info.st_mode) or info.st_uid != os.geteuid():
                raise SharedSourceError("shared endpoint must be an owned Unix socket")
            connector = self.connector
            if connector is None:
                from websockets.sync.client import unix_connect
                connector = unix_connect
            self.connection = connector(str(self.path), open_timeout=self.remaining(),
                                        close_timeout=min(1.0, self.timeout),
                                        compression=None, max_size=4 * 1024 * 1024)
            self.request("initialize", {
                "clientInfo": {"name": "codex_wake_discovery", "version": "0.6.0"},
                "capabilities": {"experimentalApi": True},
            })
            self.connection.send(json.dumps({"method": "initialized"}))
            return self
        except Exception as exc:
            self.close()
            if isinstance(exc, WakeError):
                raise
            raise SharedSourceError(f"shared app-server unavailable: {type(exc).__name__}") from None

    def remaining(self) -> float:
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise SharedSourceError("shared metadata observation timed out")
        return remaining

    def request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        if method not in self.ALLOWED_METHODS:
            raise WakeError("discovery method is not read-only")
        if self.connection is None:
            raise SharedSourceError("shared connection is not open")
        self.sequence += 1
        request_id = self.sequence
        try:
            self.remaining()
            self.connection.send(json.dumps({"id": request_id, "method": method, "params": params}))
            while True:
                response = json.loads(self.connection.recv(timeout=self.remaining()))
                if not isinstance(response, dict):
                    raise SharedSourceError("invalid shared app-server response")
                if "id" not in response:
                    continue  # Unsolicited notifications never establish metadata.
                if response.get("id") != request_id:
                    raise SharedSourceError("unexpected shared response identity")
                if "error" in response:
                    raise SharedSourceError(f"shared method unavailable: {method}")
                result = response.get("result")
                if not isinstance(result, dict):
                    raise SharedSourceError("invalid shared result")
                return result
        except WakeError:
            raise
        except Exception as exc:
            raise SharedSourceError(f"shared metadata read failed: {type(exc).__name__}") from None

    def loaded_threads(self, *, maximum: int = 10000) -> list[dict[str, Any]]:
        if maximum <= 0:
            raise WakeError("metadata population bound must be positive")
        ids: list[str] = []
        seen: set[str] = set()
        cursors: set[str] = set()
        cursor: str | None = None
        while True:
            page = self.request("thread/loaded/list", {"limit": 100, "cursor": cursor})
            data = page.get("data")
            if not isinstance(data, list) or any(not isinstance(x, str) or not x for x in data):
                raise SharedSourceError("invalid loaded-thread page")
            for thread_id in data:
                if thread_id in seen:
                    raise SharedSourceError("loaded-thread pagination changed or repeated")
                seen.add(thread_id)
                ids.append(thread_id)
                if len(ids) > maximum:
                    raise SharedSourceError("loaded-thread population exceeds observation bound")
            cursor = page.get("nextCursor")
            if cursor is None:
                break
            if not isinstance(cursor, str) or not cursor or cursor in cursors:
                raise SharedSourceError("invalid or repeated loaded-thread cursor")
            cursors.add(cursor)
        return [self.read_thread(thread_id) for thread_id in ids]

    def read_thread(self, thread_id: str) -> dict[str, Any]:
        result = self.request("thread/read", {"threadId": thread_id, "includeTurns": False})
        thread = result.get("thread")
        if not isinstance(thread, dict) or thread.get("id") != thread_id:
            raise SharedSourceError("shared thread identity mismatch")
        # Explicit allowlist prevents transcripts or future response fields leaking.
        return {key: thread.get(key) for key in (
            "id", "name", "cwd", "status", "source", "parentThreadId", "agentPath",
        )}

    def close(self) -> None:
        connection, self.connection = self.connection, None
        if connection is not None:
            try:
                connection.close()
            except Exception:
                pass

    def __exit__(self, *_: Any) -> None:
        self.close()
