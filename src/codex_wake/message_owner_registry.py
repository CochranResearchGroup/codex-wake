"""Portable read-only access to pinned execution identities in HostRegistry."""
import json
from pathlib import Path
import sqlite3


def environment_record(db, host, environment):
    row = db.execute('SELECT record FROM environments WHERE host=? AND environment=?',
                     (host, environment)).fetchone()
    return json.loads(row[0]) if row else None


def resolve_owner_pair(registry, local, peer):
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
    kinds = tuple(row['kind'] for row in rows)
    if set(kinds) != {'windows', 'wsl'}:
        raise ValueError('only the normal Windows and WSL owner pair is supported')
    return kinds
