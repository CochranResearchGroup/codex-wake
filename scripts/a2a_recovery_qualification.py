"""Installed held recovery and explicit crash-cut reconciliation in disposable buses."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import time
from unittest.mock import patch

from codex_wake.a2a_backup import MailBackup
from codex_wake.a2a_bus import BusStore
from codex_wake.a2a_identity import BusError, RuntimeIdentity
from codex_wake.a2a_mailbox import Mailbox
from codex_wake.a2a_recovery import MailRecovery
from codex_wake.a2a_scheduler import MailScheduler


def require(value, message):
    if not value:
        raise AssertionError(message)


def census():
    return dict(fd_count=len(os.listdir('/proc/self/fd')),
        children=Path('/proc/self/task/%s/children' % os.getpid()).read_text().split())


def qualify(cli, legacy_python):
    os.urandom(1); started = time.monotonic(); before = census(); cases = []
    with tempfile.TemporaryDirectory(prefix='codex-wake-p63-recovery-') as temporary:
        for interrupted in (False, True):
            base = Path(temporary) / ('cut' if interrupted else 'damaged'); base.mkdir(mode=0o700)
            repo = base / 'repo'; repo.mkdir(mode=0o700)
            bus, operator = BusStore.configure(base / 'bus', bus_id='recovery-fixture')
            bus.enroll(repo, operator, notify=True)
            identities = [RuntimeIdentity('p63-recovery-fixture', name, str(repo)) for name in ('sender', 'recipient')]
            actors = []
            for identity in identities:
                capability, _ = bus.issue_actor(identity, repo, operator)
                actors.append(bus.authenticate(capability, identity, invoking_cwd=repo))
            Mailbox.migrate(bus, operator); mailbox = Mailbox(bus)
            bus.set_paused(False, operator)
            body = 'Private synthetic recovery fixture.'
            ids = [mailbox.send(actors[0], identities[1], body=body, idempotency_key=key)['message']['message_id'] for key in ('unknown', 'pending')]
            scheduler = MailScheduler(mailbox, operator, owner='recovery-fixture')
            dispatcher = scheduler.acquire(); recipient = scheduler.acquire('recipient:' + actors[1].key)
            claim = scheduler.claim(dispatcher, recipient, ['notify_' + ids[0]])
            bus.set_paused(True, operator)
            snapshot = base / 'snapshot'; created = MailBackup(bus, operator).create(snapshot)
            retained = {}
            with bus.connection() as database:
                for table in ('mail_metadata','mail_state','mail_receipts','mail_attempts','mail_bodies','mail_outbox'):
                    retained[table] = [tuple(row) for row in database.execute('SELECT * FROM ' + table)]
            with bus.path.open('r+b') as stream:
                stream.write(b'Damaged fixture!')
            # Deliberately malformed inactive sidecars: artifact preservation,
            # not a claim that these represent real newer business commits.
            for suffix in ('-wal','-shm'):
                path = Path(str(bus.path) + suffix)
                path.write_bytes(('Synthetic damaged sidecar ' + suffix).encode()); path.chmod(0o600)
            source = {name: hashlib.sha256((bus.root / name).read_bytes()).hexdigest()
                for name in ('mailbox.sqlite','mailbox.sqlite-wal','mailbox.sqlite-shm')}
            def invoke(verb, capability=operator, success=True):
                remaining = 30 - (time.monotonic() - started)
                require(remaining > 0, 'qualification deadline exceeded')
                command = [cli, 'a2a', verb, '--bus-root', str(bus.root), '--operator-capability', str(capability), '--json']
                if verb in ('recover-backup','reconcile-recovery'):
                    command += ['--expected-database-sha256', created['database_sha256'], '--apply']
                if verb == 'recover-backup':
                    command += ['--snapshot', str(snapshot), '--accept-unbacked-state-hold']
                completed = subprocess.run(command, capture_output=True, text=True, timeout=min(10, remaining))
                require((completed.returncode == 0) == success, 'installed ' + verb + ' status differs')
                require(body not in completed.stdout, 'body leaked to operator output')
                return json.loads(completed.stdout)
            if interrupted:
                replace = os.replace
                def cut(source_path, destination):
                    if Path(source_path).name == 'recovered.sqlite':
                        raise OSError('synthetic cut before canonical activation')
                    return replace(source_path, destination)
                with patch('codex_wake.a2a_recovery.os.replace', side_effect=cut):
                    try:
                        MailRecovery(bus.root, operator).recover(snapshot, expected_sha256=created['database_sha256'], acknowledge_gap=True)
                        raise AssertionError('cut did not interrupt')
                    except BusError as exc:
                        require(exc.code == 'recovery_incomplete', 'wrong interrupted state')
                        pointer = exc.details['receipt_id']
                blocked = invoke('doctor', success=False)
                require(blocked['error']['code'] == 'recovery_incomplete' and blocked['reconciliation_pointer']['receipt_id'] == pointer, 'fresh reader lost intent pointer')
                result = invoke('reconcile-recovery')['recovery']
                require(result['receipt_id'] == pointer, 'reconciliation changed attributable receipt')
            else:
                result = invoke('recover-backup')['recovery']
            fresh = Path(result['operator_capability_file'])
            require(result['completed'] and result['recovery_hold'] and result['gap_unknown'], 'wrong recovered held verdict')
            quarantine = Path(result['quarantine'])
            for name, expected in source.items():
                require(hashlib.sha256((quarantine / name).read_bytes()).hexdigest() == expected, 'source artifact was changed: ' + name)
            report = invoke('doctor', fresh)
            require(report['bus']['store_schema'] == 2 and report['bus']['paused'] and report['bus']['recovery_hold'], 'fresh inspection did not observe held schema2')
            require(invoke('resume', fresh, success=False)['error']['code'] == 'recovery_hold', 'held recovery resumed')
            require(invoke('doctor', operator, success=False)['error']['code'] == 'authorization_denied', 'old operator authority revived')
            require(invoke('recover-backup', operator, success=False)['error']['code'] == 'authorization_denied', 'old operator could start another recovery')
            current = BusStore(bus.root)
            with current.connection() as database:
                for table, expected in retained.items():
                    require([tuple(row) for row in database.execute('SELECT * FROM ' + table)] == expected, 'snapshot state changed: ' + table)
                require(database.execute('SELECT count(*) FROM actors WHERE revoked=0').fetchone()[0] == 0, 'actor authority revived')
                require(database.execute('SELECT count(*) FROM mail_leases').fetchone()[0] == 0, 'old lease revived')
                require(database.execute('SELECT state FROM mail_attempts WHERE attempt_id=?', (claim['attempt_id'],)).fetchone()[0] == 'dispatching', 'unknown intent was classified as unsent')
            try:
                Mailbox(current).show(actors[0], ids[0])
                raise AssertionError('cached actor bypassed hold')
            except BusError as exc:
                require(exc.code == 'recovery_hold', 'cached actor refusal differs')
            remaining = 30 - (time.monotonic() - started)
            legacy = subprocess.run([legacy_python, '-c',
                'from pathlib import Path; from codex_wake.a2a_bus import BusStore; from codex_wake.a2a_identity import BusError; import sys\ntry: BusStore(Path(sys.argv[1]))\nexcept BusError as e:\n print(e.code); sys.exit(0 if e.code == "unsupported_schema" else 1)\nsys.exit(2)', str(bus.root)],
                capture_output=True, text=True, timeout=min(10, remaining))
            require(legacy.returncode == 0 and legacy.stdout.strip() == 'unsupported_schema', 'actual old reader accepted recovered schema2')
            new_snapshot = base / 'fresh-held-snapshot'
            MailBackup(current, fresh).create(new_snapshot)
            require(MailBackup(current, fresh).verify(new_snapshot)['verified'], 'current schema2 held backup did not verify')
            cases.append(dict(interrupted=interrupted, schema_version=2, source_files_preserved=3,
                messages=2, unknown_attempts=1, old_reader_refused=True, held=True, gap_unknown=True))
    after = census(); elapsed = time.monotonic() - started
    require(elapsed <= 30 and after['fd_count'] <= before['fd_count'] + 2 and before['children'] == after['children'] == [], 'resource budget failed')
    return dict(accepted=True, synthetic=True, cases=cases, elapsed_seconds=round(elapsed, 3),
        before=before, after=after, transport_io=0, fixture_removed=True, automatic_replay=False,
        gap_reconciliation_qualified=False, live_service_qualified=False,
        thresholds=dict(elapsed_seconds=30, cli_timeout_seconds=10, fd_growth=2, residual_children=0))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cli', required=True); parser.add_argument('--legacy-python', required=True)
    args = parser.parse_args()
    print(json.dumps(qualify(args.cli, args.legacy_python), sort_keys=True))
