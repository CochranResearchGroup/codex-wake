#!/usr/bin/env python3
"""Installed pause rollback contract on owned synthetic state; no transport I/O."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

from codex_wake.a2a_bus import BusStore
from codex_wake.a2a_identity import BusError, RuntimeIdentity
from codex_wake.a2a_mailbox import Mailbox
from codex_wake.a2a_scheduler import MailScheduler


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def census():
    return dict(fd_count=len(os.listdir('/proc/self/fd')),
                children=Path('/proc/self/task/%s/children' % os.getpid()).read_text().split())


def qualify(cli):
    os.urandom(1)
    started = time.monotonic()
    before = census()
    thresholds = dict(elapsed_seconds=20, fd_growth=2, residual_children=0,
                      messages=2, dispatch_io=0, cli_timeout_seconds=10)
    with tempfile.TemporaryDirectory(prefix='codex-wake-p63-rollback-') as directory:
        root = Path(directory)
        repo = root / 'repo'; repo.mkdir(mode=0o700)
        bus, operator = BusStore.configure(root / 'bus', bus_id='rollback-fixture')
        bus.enroll(repo, operator, notify=True)
        identities = [RuntimeIdentity('p63-rollback-fixture', name, str(repo))
                      for name in ('sender', 'recipient')]
        actors = []
        for identity in identities:
            capability, _ = bus.issue_actor(identity, repo, operator)
            actors.append(bus.authenticate(capability, identity, invoking_cwd=repo))
        Mailbox.migrate(bus, operator)
        clock = [1000.0]
        now = lambda: clock[0]
        mailbox = Mailbox(bus, clock=now, monotonic=now)
        bus.set_paused(False, operator)
        scheduler = MailScheduler(mailbox, operator, owner='fixture-before-rollback')
        identifiers = [mailbox.send(actors[0], identities[1], body='Synthetic rollback fixture.',
            idempotency_key=key)['message']['message_id'] for key in ('unknown', 'pending')]
        dispatcher = scheduler.acquire()
        recipient = scheduler.acquire('recipient:' + actors[1].key)
        claim = scheduler.claim(dispatcher, recipient, ['notify_' + identifiers[0]])
        # This is an intent claim only: no adapter/network/TUI operation exists here.
        def invoke(verb):
            result = subprocess.run([cli, 'a2a', verb, '--bus-root', str(bus.root),
                '--operator-capability', str(operator), '--json'], capture_output=True,
                text=True, timeout=10)
            require(result.returncode == 0, 'installed ' + verb + ' failed: ' + result.stderr)
            require('Synthetic rollback fixture.' not in result.stdout, 'body leaked to operator output')
            return json.loads(result.stdout)
        paused = invoke('pause')
        require(paused['paused'], 'rollback did not pause dispatcher')
        require(invoke('status')['bus']['paused'], 'fresh CLI did not observe pause')
        clock[0] += 31  # Controlled expired lease; no actual delay or daemon restart claim.
        reopened = Mailbox(BusStore(bus.root), clock=now, monotonic=now)
        successor = MailScheduler(reopened, operator, owner='fixture-after-rollback')
        newer = successor.acquire()
        require(successor.recover(newer) == 1, 'expired unknown claim was not held')
        require(reopened.show(actors[0], identifiers[0])['state']['notification'] == 'uncertain',
                'rollback reclassified unknown notification as safely unsent')
        require([job['message_id'] for job in successor.jobs(newer)] == [identifiers[1]],
                'unknown claim was retried or pending record disappeared')
        recipient = successor.acquire('recipient:' + actors[1].key)
        try:
            successor.claim(newer, recipient, ['notify_' + identifiers[1]])
            raise AssertionError('paused dispatcher accepted another claim')
        except BusError as exc:
            require(exc.code == 'paused', 'wrong rollback claim refusal')
        returned = reopened.read(actors[1], identifiers[1])
        require(returned['body'] == 'Synthetic rollback fixture.', 'pause removed accepted body')
        retry = reopened.send(actors[0], identities[1], body='Synthetic rollback fixture.',
                              idempotency_key='pending')
        require(retry['deduplicated'] and retry['message']['message_id'] == identifiers[1],
                'rollback reset accepted idempotency')
        reopened_again = Mailbox(BusStore(bus.root), clock=now, monotonic=now)
        require(reopened_again.read(actors[1], identifiers[1])['receipt_id'] == returned['receipt_id'],
                'canonical reopen lost idempotent recipient receipt')
        with bus.connection() as database:
            preserved = dict(envelopes=database.execute('SELECT count(*) FROM mail_envelopes').fetchone()[0],
                attempts=database.execute('SELECT count(*) FROM mail_attempts').fetchone()[0],
                attempt_state=database.execute('SELECT state FROM mail_attempts WHERE attempt_id=?',
                                              (claim['attempt_id'],)).fetchone()[0])
        require(preserved == dict(envelopes=2, attempts=1, attempt_state='uncertain'),
                'rollback deleted or replayed unknown admission/attempt history')
        copied = root / 'copied-bus'; shutil.copytree(bus.root, copied)
        try:
            BusStore(copied)
            raise AssertionError('copied backup became a concurrent writer')
        except BusError as exc:
            require(exc.code == 'bus_identity_mismatch', 'wrong copied backup refusal')
        clock[0] = 1000.0 + 90 * 86400
        require(reopened_again.send(actors[0], identities[1], body='Synthetic rollback fixture.',
                idempotency_key='pending')['message']['message_id'] == identifiers[1],
                'retry identity lost inside advertised horizon')
        clock[0] += 1
        try:
            reopened_again.send(actors[0], identities[1], body='Synthetic rollback fixture.',
                                idempotency_key='pending')
            raise AssertionError('dedup implied infinite horizon')
        except BusError as exc:
            require(exc.code == 'idempotency_horizon', 'wrong finite horizon refusal')
    elapsed = time.monotonic() - started
    after = census()
    require(elapsed <= thresholds['elapsed_seconds'], 'elapsed budget exceeded')
    require(after['fd_count'] <= before['fd_count'] + thresholds['fd_growth'], 'descriptor growth')
    require(after['children'] == before['children'] == [], 'residual child process')
    return dict(schema_version=1, accepted=True, synthetic=True, real_delivery_qualified=False,
        binary_downgrade_qualified=False, backup_activation_qualified=False, thresholds=thresholds,
        elapsed_seconds=round(elapsed, 3), before=before, after=after, paused=True,
        preserved=preserved, copied_root_denied=True, finite_dedup_horizon=True,
        transport_io=0, fixture_removed=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cli', required=True, help='explicit installed codex-wake executable')
    args = parser.parse_args()
    print(json.dumps(qualify(args.cli), sort_keys=True))
