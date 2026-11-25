"""Portable derivation of a native Codex conversation namespace."""
import hashlib
import json
from pathlib import Path


def codex_identity(thread, server):
    home, provider = server.get('codexHome'), thread.get('modelProvider')
    identifier, cwd = thread.get('id'), thread.get('cwd')
    if not all(isinstance(value, str) and value for value in (home, provider, identifier, cwd)):
        raise ValueError('runtime identity metadata is incomplete')
    if not Path(home).is_absolute() or not Path(cwd).is_absolute():
        raise ValueError('runtime identity paths must be absolute')
    key = json.dumps([str(Path(home).resolve()), provider], separators=(',', ':'))
    return 'codex:' + hashlib.sha256(key.encode()).hexdigest(), identifier, str(Path(cwd).resolve())
