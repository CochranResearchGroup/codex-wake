"""Exact runtime identity for operator-enrolled local messaging."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

from .records import WakeError


class BusError(WakeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class RuntimeIdentity:
    namespace: str
    thread_id: str
    cwd: str

    @classmethod
    def from_metadata(cls, thread: dict, server: dict) -> RuntimeIdentity:
        home, provider = server.get('codexHome'), thread.get('modelProvider')
        identifier, cwd = thread.get('id'), thread.get('cwd')
        if not all(isinstance(value, str) and value for value in [home, provider, identifier, cwd]):
            raise BusError('identity_unavailable', 'runtime identity metadata is incomplete')
        if not Path(home).is_absolute() or not Path(cwd).is_absolute():
            raise BusError('identity_unavailable', 'runtime identity paths must be absolute')
        key = json.dumps([str(Path(home).resolve()), provider], separators=(',', ':'))
        namespace = 'codex:' + hashlib.sha256(key.encode()).hexdigest()
        return cls(namespace, identifier, str(Path(cwd).resolve()))


@dataclass(frozen=True)
class Actor:
    bus_id: str
    namespace: str
    thread_id: str
    root: str
    generation: int
    actor_id: str

    @property
    def key(self) -> str:
        return json.dumps([self.namespace, self.thread_id], separators=(',', ':'))
