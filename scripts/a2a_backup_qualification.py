"""Installed CLI snapshot qualification in one disposable synthetic bus; no activation."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import tempfile
import time

from codex_wake.a2a_bus import BusStore
from codex_wake.a2a_identity import BusError, RuntimeIdentity
from codex_wake.a2a_mailbox import Mailbox
from codex_wake.a2a_scheduler import MailScheduler


def require(value, message):
    if not value:
        raise AssertionError(message)


def census():
    return dict(fd_count=len(os.listdir('/proc/self/fd')),
        children=Path('/proc/self/task/%s/children' % os.getpid()).read_text().split())


def qualify(cli):
    os.urandom(1)
    started = time.monotonic(); before = census()
    with tempfile.TemporaryDirectory(prefix='codex-wake-p63-backup-') as temporary:
        root = Path(temporary); repo = root / 'repo'; repo.mkdir(mode=0o700)
        bus, operator = BusStore.configure(root / 'bus', bus_id='backup-fixture')
        bus.enroll(repo, operator, notify=True)
        identities = [RuntimeIdentity('p63-backup-fixture', name, str(repo)) for name in ('sender', 'recipient')]
        actors = []
        for identity in identities:
            capability, _ = bus.issue_actor(identity, repo, operator)
            actors.append(bus.authenticate(capability, identity, invoking_cwd=repo))
        Mailbox.migrate(bus, operator); mailbox = Mailbox(bus)
        bus.set_paused(False, operator)
        body = 'Private synthetic backup fixture.'
        identifiers = [mailbox.send(actors[0], identities[1], body=body, idempotency_key=key)['message']['message_id']
            for key in ('unknown', 'pending')]
        scheduler = MailScheduler(mailbox, operator, owner='backup-fixture')
        lease = scheduler.acquire(); recipient = scheduler.acquire('recipient:' + actors[1].key)
        claim = scheduler.claim(lease, recipient, ['notify_' + identifiers[0]])
        # Claim records dispatch intent only. No transport or daemon is invoked.
        bus.set_paused(True, operator)
        def invoke(verb, snapshot, success=True):
            remaining = 20 - (time.monotonic() - started)
            require(remaining > 0, 'qualification deadline exceeded')
            completed = subprocess.run([cli, 'a2a', verb, '--bus-root', str(bus.root),
                '--operator-capability', str(operator), '--snapshot', str(snapshot), '--json'],
                capture_output=True, text=True, timeout=min(10, remaining))
            require((completed.returncode == 0) == success, 'unexpected installed ' + verb + ' status')
            require(body not in completed.stdout, 'operator output leaked body')
            return json.loads(completed.stdout)
        with bus.connection() as live:
            # WAL connection stays open across the actual installed copy.
            before_rows = {table: [tuple(row) for row in live.execute('SELECT * FROM ' + table)]
                for table in ('actors', 'mail_metadata', 'mail_state', 'mail_receipts', 'mail_attempts', 'mail_bodies', 'mail_outbox')}
            created = invoke('backup', root / 'snapshot')['backup']
            checked = invoke('verify-backup', root / 'snapshot')['backup']
            require(created['verified'] and checked['verified'] and not checked['activation_qualified'], 'wrong bounded verdict')
            require(created['database_sha256'] == checked['database_sha256'], 'fresh verification lost snapshot commitment')
            with sqlite3.connect(root / 'snapshot/mailbox.sqlite') as copied:
                for table, expected in before_rows.items():
                    require(copied.execute('SELECT * FROM ' + table).fetchall() == expected, table + ' snapshot differs')
                require(copied.execute('SELECT state FROM mail_attempts WHERE attempt_id=?', (claim['attempt_id'],)).fetchone()[0] == 'dispatching', 'unknown intent reclassified')
                require(copied.execute('PRAGMA integrity_check').fetchall() == [('ok',)], 'backup integrity')
            for table, expected in before_rows.items():
                require([tuple(row) for row in live.execute('SELECT * FROM ' + table)] == expected, 'source mutated: ' + table)
        snapshot = root / 'snapshot'
        require(not (snapshot / 'operator.json').exists() and not (snapshot / 'capabilities').exists(), 'credential files exported')
        for path in snapshot.iterdir():
            require(path.stat().st_mode & 0o777 == 0o600, 'snapshot file privacy')
        repeated = invoke('backup', snapshot, success=False)
        require(repeated['error']['code'] == 'backup_incomplete' and repeated['reconciliation_required'] and repeated['reconciliation_pointer']['receipt_id'], 'no-overwrite refusal lost audit pointer')
        copied_root = root / 'copied-bus'; copied_root.mkdir(mode=0o700)
        shutil.copy2(snapshot / 'mailbox.sqlite', copied_root / 'mailbox.sqlite')
        try:
            BusStore(copied_root)
            raise AssertionError('snapshot activated at copied root')
        except BusError as exc:
            require(exc.code == 'bus_identity_mismatch', 'copied-root guard differs')
        manifest_path = snapshot / 'manifest.json'
        original = manifest_path.read_text(); manifest = json.loads(original)
        manifest['format_version'] = 999; manifest_path.write_text(json.dumps(manifest))
        require(invoke('verify-backup', snapshot, success=False)['error']['code'] == 'backup_invalid', 'unsupported backup accepted')
        manifest_path.write_text(original)
        with (snapshot / 'mailbox.sqlite').open('r+b') as stream:
            stream.write(b'corrupt')
        require(invoke('verify-backup', snapshot, success=False)['error']['code'] == 'backup_invalid', 'corrupt backup accepted')
    after = census(); elapsed = time.monotonic() - started
    require(elapsed <= 20 and after['fd_count'] <= before['fd_count'] + 2 and before['children'] == after['children'] == [], 'resource budget failed')
    return dict(accepted=True, synthetic=True, activation_qualified=False, transport_io=0,
        messages=2, unknown_attempts=1, copied_root_denied=True, fresh_process_verified=True,
        database_bytes=checked['database_bytes'], elapsed_seconds=round(elapsed, 3), before=before, after=after,
        thresholds=dict(elapsed_seconds=20, cli_timeout_seconds=10, fd_growth=2, residual_children=0), fixture_removed=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cli', required=True)
    print(json.dumps(qualify(parser.parse_args().cli), sort_keys=True))
