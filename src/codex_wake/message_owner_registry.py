"""Portable read-only access to pinned execution identities in HostRegistry."""
import json
from pathlib import Path
import sqlite3

from .windows_scope import scope_identity


def environment_record(db, host, environment):
    row = db.execute('SELECT record FROM environments WHERE host=? AND environment=?',
                     (host, environment)).fetchone()
    return json.loads(row[0]) if row else None


def resolve_owner_records(registry, local, peer):
    required = {'host', 'environment', 'authority', 'generation'}
    for target in (local, peer):
        if (not isinstance(target, dict) or set(target) != required
                or any(not isinstance(v, str) or not 0 < len(v) <= 128 for v in target.values())):
            raise ValueError('exact registered owner pins are required')
    if local['host'] != peer['host'] or local['environment'] == peer['environment']:
        raise ValueError('owners must be distinct execution environments on the same host')
    path = Path(registry).resolve(strict=True)
    with sqlite3.connect(path.as_uri() + '?mode=ro', uri=True) as db:
        rows = [environment_record(db, target['host'], target['environment']) for target in (local, peer)]
    if any(not row or row['target'] != target for row, target in zip(rows, (local, peer))):
        raise ValueError('pinned execution-owner registration changed')
    kinds = {row['kind'] for row in rows}
    if kinds not in ({'windows', 'wsl'}, {'windows', 'windows-elevated'}):
        raise ValueError('unsupported execution owner pair')
    for row in rows:
        pin = row.get('windows_identity')
        kind = row['kind']
        if 'windows-elevated' in kinds and pin is None:
            raise ValueError('both Windows owners require an exact Windows identity')
        if pin is not None and (kind == 'wsl' or scope_identity(pin)['elevated'] != (kind == 'windows-elevated')):
            raise ValueError('execution kind and Windows token pin differ')
    return rows


def resolve_owner_pair(registry, local, peer):
    return tuple(row['kind'] for row in resolve_owner_records(registry, local, peer))
