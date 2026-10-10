"""Opt-in installed fresh-process recovery disposition, with no transport bindings."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

import codex_wake
from codex_wake.a2a_backup import MailBackup
from codex_wake.a2a_bus import BusStore
from codex_wake.a2a_identity import BusError, RuntimeIdentity
from codex_wake.a2a_mailbox import Mailbox
from codex_wake.a2a_scheduler import MailScheduler


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--legacy-cli', type=Path, required=True)
    args = parser.parse_args()
    if not Path(codex_wake.__file__).is_relative_to(Path(sys.prefix)):
        raise SystemExit('Use an immutable installed candidate with source PYTHONPATH unset')
    cli = Path(sys.executable).with_name('codex-wake')
    env = dict(os.environ)
    env.pop('PYTHONPATH', None)
    children = Path('/proc/self/task/' + str(os.getpid()) + '/children')
    descriptor_count = lambda: len(list(Path('/proc/self/fd').iterdir()))
    before = descriptor_count()
    report = dict(version=codex_wake.__version__, prefix=sys.prefix, checks=[],
                  transports=0, production_store_changes=0, fd_before=before,
                  clock_basis='fixed fixture1000; not a UTC/time-provider qualification')
    try:
        with tempfile.TemporaryDirectory(prefix='wake-recovery-disposition-') as directory:
            root = Path(directory)
            bus, old = BusStore.configure(root / 'bus')
            Mailbox.migrate(bus, old)
            repo = root / 'repo'
            repo.mkdir()
            bus.enroll(repo, old, notify=True)
            identities = [RuntimeIdentity('qualification', name, str(repo)) for name in ['sender', 'recipient']]
            actors = []
            for identity in identities:
                cap, _ = bus.issue_actor(identity, repo, old)
                actors.append(bus.authenticate(cap, identity, invoking_cwd=repo))
            original = Mailbox(bus, clock=lambda: 1000.0, monotonic=lambda: 1000.0).send(actors[0], identities[1], body='Unknown prior work.',
                idempotency_key='original-owned-intent', delivery='notify')['message']['message_id']
            Mailbox(bus, clock=lambda: 1000.0, monotonic=lambda: 1000.0).ack(actors[1], original, outcome='accepted')
            snapshot = root / 'snapshot'
            backup = MailBackup(bus, old).create(snapshot)
            with bus.path.open('r+b') as stream:
                stream.write(b'Damaged fixture!')
            damaged_hash = hashlib.sha256(bus.path.read_bytes()).hexdigest()
            def command(executable, verb, *arguments, authority=old, expected=0):
                completed = subprocess.run([str(executable), 'a2a', verb, '--bus-root', str(bus.root),
                    '--operator-capability', str(authority), '--json', *map(str, arguments)],
                    env=env, capture_output=True, text=True, timeout=10)
                value = json.loads(completed.stdout)
                if completed.returncode != expected:
                    raise RuntimeError(dict(verb=verb, code=completed.returncode, value=value))
                return value
            recovered = command(cli, 'recover-backup', '--snapshot', snapshot,
                '--expected-database-sha256', backup['database_sha256'], '--accept-unbacked-state-hold', '--apply')['recovery']
            fresh = Path(recovered['operator_capability_file'])
            pins = ['--recovery-epoch', recovered['recovery_epoch'], '--expected-database-sha256', backup['database_sha256']]
            held = command(cli, 'recovery-status', authority=fresh)['recovery']
            assert held['hold'] and held['gap_unknown'] and held['disposition'] is None
            assert command(args.legacy_cli, 'status', authority=fresh)['bus']['store_schema'] == 2
            denied = command(cli, 'status', expected=7)
            assert denied['error']['code'] == 'authorization_denied'
            report['checks'].append('actual damaged-source recovery; original operator fenced; original0.11.2 reads held schema2')
            intent = [*pins, '--accept-missing-state-unknown', '--reason', 'Retain unknown history; no legacy replay.',
                      '--idempotency-key', 'owned-one-disposition']
            disposed = command(cli, 'dispose-recovery', *intent, authority=fresh)
            repeated = command(cli, 'dispose-recovery', *intent, authority=fresh)
            assert repeated['deduplicated'] and repeated['receipt_id'] == disposed['receipt_id']
            refused = command(args.legacy_cli, 'status', authority=fresh, expected=8)
            assert refused['error']['code'] == 'unsupported_schema'
            release = command(cli, 'release-recovery', *pins, '--disposition-receipt', disposed['receipt_id'], authority=fresh)
            again = command(cli, 'release-recovery', *pins, '--disposition-receipt', disposed['receipt_id'], authority=fresh)
            assert again['deduplicated'] and again['receipt_id'] == release['receipt_id']
            status = command(cli, 'status', authority=fresh)['bus']
            assert status['paused'] and not status['recovery_hold'] and status['store_schema'] == 3 and status['active_actors'] == 0
            report['checks'].append('fresh CLI disposition/release/reconciliation; old0.11.2 explicitly refuses schema3; release stays paused')
            assert hashlib.sha256((Path(recovered['quarantine']) / 'mailbox.sqlite').read_bytes()).hexdigest() == damaged_hash
            command(cli, 'enroll', repo, '--notify', authority=fresh)
            fresh_actors = []
            for identity in identities:
                actor = next(a for a in disposed['recovery']['revoked_actors'] if a['thread_id'] == identity.thread_id)
                rotated = command(cli, 'rotate', actor['actor_id'], authority=fresh)
                fresh_actors.append(bus.authenticate(Path(rotated['actor_capability_file']), identity, invoking_cwd=repo))
            mailbox = Mailbox(bus, clock=lambda: 1000.0, monotonic=lambda: 1000.0)
            try:
                mailbox.ack(fresh_actors[1], original, outcome='accepted')
            except BusError as error:
                assert error.code == 'recovery_legacy_held'
            else:
                raise AssertionError('fresh credentials acquired legacy work')
            command(cli, 'resume', authority=fresh)
            scheduler = MailScheduler(mailbox, fresh)
            lease = scheduler.acquire()
            assert scheduler.jobs(lease) == []
            new = mailbox.send(fresh_actors[0], identities[1], body='Fresh owned work.',
                idempotency_key='fresh-owned-intent', delivery='inbox')['message']['message_id']
            assert mailbox.ack(fresh_actors[1], new, outcome='accepted')['claimed']
            assert mailbox.ack(fresh_actors[1], new, outcome='completed')['message']['state']['recipient'] == 'completed'
            command(cli, 'pause', authority=fresh)
            report['checks'].append('quarantine bytes preserved; explicit fresh grants required; legacy claims/notifications held; new inbox work completes')
            report.update(original_message_id=original, new_message_id=new, disposition_receipt=disposed['receipt_id'],
                          release_receipt=release['receipt_id'], recovery_epoch=recovered['recovery_epoch'])
        report.update(fd_after=descriptor_count(), children=children.read_text().strip(), roots_removed=True)
        assert report['fd_after'] <= before + 2 and not report['children']
        report['status'] = 'passed'
    except Exception as error:
        report.update(status='failed', error=str(error))
        raise
    finally:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(status=report['status'], checks=len(report['checks']), output=str(args.output))))


if __name__ == '__main__':
    main()
