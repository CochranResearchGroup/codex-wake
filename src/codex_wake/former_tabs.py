"""Retain read-only locators from verified terminal inventory."""
from contextlib import closing, contextmanager
import hashlib
import json
import math
import os
from pathlib import Path
import sqlite3
import stat
from uuid import UUID

from .shortcut_store import private_directory


_RETENTION_SETTING = 'CODEX_WAKE_FORMER_TAB_RETENTION_LIMIT'


def bounded_tab_text(value, limit=4096):
    return isinstance(value, str) and 0 < len(value) <= limit and not any(ord(c) < 32 for c in value)


def _binding(resource, observed_at, basis):
    if resource.get('monitor_unavailable') or resource.get('presentation_source', {}).get('available') is False:
        return None
    target = resource.get('target') or {}
    window = resource.get('window') or {}
    traits = resource.get('traits') or {}
    attached = [p for p in traits.get('panes', []) if p.get('binding')]
    if len(attached) != 1:
        return None
    evidence = attached[0]
    presence = evidence.get('traits', {}).get('session_presence', {})
    if presence.get('status') == 'stale':
        return None
    binding = evidence['binding']
    source = binding.get('native_source') or {}
    process = binding.get('process') or {}
    panes = [p for p in window.get('panes', []) if p.get('pane_id') == evidence.get('pane_id')]
    fields = ('host', 'environment', 'workspace', 'presentation')
    if (binding.get('runtime') != 'codex' or binding.get('fresh') is not True
            or binding.get('source') not in ('native_metadata', 'verified_managed_reattachment')
            or len(panes) != 1 or type(process.get('pid')) is not int or process['pid'] <= 0
            or not bounded_tab_text(str(process.get('start_ticks') or ''), 64)
            or not bounded_tab_text(process.get('boot_id'), 128)
            or not all(bounded_tab_text(target.get(key), 256) for key in fields)
            or not bounded_tab_text(window.get('name'), 1024) or not bounded_tab_text(window.get('window_id'), 128)
            or type(window.get('index')) is not int or window['index'] < 0
            or not bounded_tab_text(source.get('home')) or not bounded_tab_text(source.get('home_generation'), 128)):
        return None
    conversation = binding.get('conversation_id')
    try:
        if str(UUID(conversation)) != conversation:
            return None
    except (TypeError, ValueError, AttributeError):
        return None
    cwd = panes[0].get('pane_current_path')
    if not bounded_tab_text(cwd):
        return None
    row = {key: target[key] for key in fields}
    row.update(name=window['name'], window_id=window['window_id'],
               position=window['index'], conversation_id=conversation,
               home=source['home'], home_generation=source['home_generation'])
    token = dict(row, process={k: str(process[k]) for k in ('pid', 'start_ticks', 'boot_id')})
    row.update(binding_id=hashlib.sha256(json.dumps(token, sort_keys=True).encode()).hexdigest(),
               last_observed_cwd=cwd, last_observed_at=observed_at,
               observed_at_time_basis=basis)
    return row


class FormerTabs:
    def __init__(self, root):
        self.directory = Path(root) / 'former-tabs'
        self.path = self.directory / 'bindings.sqlite'

    @contextmanager
    def _connection(self, *, create=False):
        if not self.path.exists() and not create:
            yield None
            return
        directory = private_directory(self.directory)
        fd = os.open(directory / self.path.name,
                     os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK | (os.O_CREAT if create else 0), 0o600)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077 or info.st_nlink != 1:
                raise ValueError('private former-tab store required')
            with closing(sqlite3.connect(self.path, timeout=.2)) as db, db:
                if create:
                    db.execute('''CREATE TABLE IF NOT EXISTS bindings (
                        sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                        binding_id TEXT NOT NULL UNIQUE, selector TEXT NOT NULL,
                        present INTEGER NOT NULL, payload TEXT NOT NULL,
                        host TEXT NOT NULL, environment TEXT NOT NULL,
                        home TEXT NOT NULL, home_generation TEXT NOT NULL
                    )''')
                    db.execute('CREATE INDEX IF NOT EXISTS former_tab_name ON bindings(host, environment, selector, sequence)')
                    db.execute('CREATE TABLE IF NOT EXISTS forgotten(binding_id TEXT PRIMARY KEY)')
                yield db
        finally:
            os.close(fd)

    def observe(self, snapshot, resources):
        """Only a complete presentation observation can mark a tab absent."""
        observed_at = snapshot.get('observed_at')
        if type(observed_at) not in (float, int) or not math.isfinite(observed_at):
            return
        basis = snapshot.get('observed_at_time_basis', 'unqualified_display')
        scope = snapshot.get('observation_scope') or {}
        host, environment = scope.get('host'), scope.get('environment')
        unavailable = {r.get('workspace') for r in snapshot.get('unavailable', [])}
        complete = set(snapshot.get('workspaces', [])) - unavailable if None not in unavailable else set()
        bindings, visible, verified = {}, set(), set()
        for resource in resources:
            target = resource.get('target') or {}
            window = resource.get('window') or {}
            workspace = target.get('workspace')
            if resource.get('monitor_unavailable'):
                complete.discard(workspace)
                continue
            if workspace in complete and (target.get('host'), target.get('environment')) == (host, environment):
                visible.add((workspace, window.get('window_id'), window.get('name'), window.get('index')))
            captured_at = resource.get('monitor_observed_at', observed_at)
            if type(captured_at) not in (int, float) or not math.isfinite(captured_at):
                continue
            row = _binding(resource, captured_at, basis)
            if row:
                bindings[row['binding_id']] = row
                verified.add((workspace, row['window_id'], row['name'], row['position']))
        if not bindings and not self.path.exists():
            return
        configured = os.environ.get(_RETENTION_SETTING)
        retention = None if configured is None else int(configured)
        if retention is not None and not 0 <= retention <= 1_000_000:
            raise ValueError('former-tab retention limit must be 0–1000000')
        with self._connection(create=True) as db:
            if retention is not None:
                db.execute('PRAGMA secure_delete=ON')
            db.execute('BEGIN IMMEDIATE')
            for binding_id, payload in db.execute('''SELECT binding_id, payload FROM bindings
                    WHERE present=1 AND host=? AND environment=?''', (host, environment)):
                row = json.loads(payload)
                appearance = (row['workspace'], row['window_id'], row['name'], row['position'])
                if (row['workspace'] in complete and binding_id not in bindings
                        and (appearance not in visible or appearance in verified)):
                    db.execute('UPDATE bindings SET present=0 WHERE binding_id=?', (binding_id,))
            for binding_id, row in bindings.items():
                db.execute('''INSERT INTO bindings(binding_id, selector, present, payload,
                        host, environment, home, home_generation)
                    SELECT ?, ?, 1, ?, ?, ?, ?, ? WHERE NOT EXISTS (
                        SELECT 1 FROM forgotten WHERE binding_id=?
                    )
                    ON CONFLICT(binding_id) DO UPDATE SET present=1, payload=excluded.payload,
                        sequence=excluded.sequence
                    WHERE present=0 OR bindings.payload<>excluded.payload''',
                    (binding_id, row['name'].casefold(), json.dumps(row), row['host'],
                     row['environment'], row['home'], row['home_generation'], binding_id))
            if retention is not None and complete:
                db.execute('''DELETE FROM bindings WHERE sequence IN (
                    SELECT sequence FROM bindings WHERE present=0 AND host=? AND environment=?
                    ORDER BY sequence DESC LIMIT -1 OFFSET ?)''', (host, environment, retention))

    def find(self, selector, *, host, environment, homes, limit):
        """Return bounded name matches within authorized owning account generations."""
        home_pins = tuple(homes)
        if not home_pins:
            return [], False
        selectors = ','.join('(?,?)' for _ in home_pins)
        pins = [value for pair in home_pins for value in pair]
        with self._connection() as db:
            if db is None:
                return [], False
            rows = db.execute(f'''SELECT payload, present FROM bindings
                WHERE host=? AND environment=? AND selector=?
                    AND (home, home_generation) IN (VALUES {selectors})
                ORDER BY sequence DESC LIMIT ?''', (host, environment, selector.casefold(), *pins, limit + 1))
            result = [dict(json.loads(payload), last_known_presentation='present' if present else 'absent')
                      for payload, present in rows]
        return result[:limit], len(result) > limit

    def forget(self, binding_id):
        """Remove metadata and prevent the same observed binding from reappearing."""
        if not isinstance(binding_id, str) or len(binding_id) != 64 or any(c not in '0123456789abcdef' for c in binding_id):
            raise ValueError('exact former-tab binding ID required')
        with self._connection() as db:
            if db is None:
                return False
            db.execute('PRAGMA secure_delete=ON')
            if db.execute('DELETE FROM bindings WHERE binding_id=?', (binding_id,)).rowcount:
                db.execute('INSERT OR IGNORE INTO forgotten(binding_id) VALUES(?)', (binding_id,))
                return True
            return db.execute('SELECT 1 FROM forgotten WHERE binding_id=?', (binding_id,)).fetchone() is not None
