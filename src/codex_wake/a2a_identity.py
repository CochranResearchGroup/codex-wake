"""Exact runtime identity for operator-enrolled local messaging."""
from __future__ import annotations

from dataclasses import dataclass
import json

from .records import WakeError
from .runtime_identity_key import codex_identity


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
        try:
            return cls(*codex_identity(thread, server))
        except ValueError as exc:
            raise BusError('identity_unavailable', str(exc)) from None


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
