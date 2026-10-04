#!/usr/bin/env python3
"""Hermetic bounded mailbox qualification; never enroll a real runtime thread."""
from dataclasses import asdict
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

from codex_wake.a2a_bus import BusStore
from codex_wake.a2a_identity import Actor, BusError, RuntimeIdentity
from codex_wake.a2a_mailbox import Mailbox

THRESHOLDS = dict(requests=100, replies=20, reopen_processes=10,
                  elapsed_seconds=30, store_bytes=10 * 1024 * 1024,
                  fd_growth=2, residual_children=0)


def census():
    return dict(fd_count=len(os.listdir('/proc/self/fd')),
                children=Path('/proc/self/task/%s/children' % os.getpid()).read_text().split())


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def pages(mailbox, actor):
    values, cursor = [], 0
    for _ in range(10):
        page = mailbox.list(actor, cursor=cursor, limit=17)
        values.extend(page['messages'])
        if page['next_cursor'] is None:
            return values
        require(page['next_cursor'] > cursor, 'cursor did not advance')
        cursor = page['next_cursor']
    raise AssertionError('pagination exceeded fixed bound')


def reopen(path):
    state = json.loads(path.read_text())
    actor = Actor(**state['actor'])
    require(actor.namespace == 'p63-resource-fixture', 'only synthetic actors allowed')
    bus = BusStore(Path(state['bus']))
    mailbox = Mailbox(bus, clock=lambda: state['now'], monotonic=lambda: state['now'])
    rows = pages(mailbox, actor)
    require([row['message_id'] for row in rows] == state['ids'], 'restart changed inbox identity/FIFO')
    require([row['recipient_sequence'] for row in rows] == list(range(1, 101)), 'FIFO sequence gap')
    print(json.dumps(dict(reopened=True, messages=len(rows))))


def qualify():
    os.urandom(1)  # Warm standard-library entropy before baseline descriptor census.
    before = census()
    started = time.monotonic()
    clock = [1000.0]
    now = lambda: clock[0]
    with tempfile.TemporaryDirectory(prefix='codex-wake-p63-resource-') as directory:
        root = Path(directory)
        roots = [root / name for name in ('sender', 'recipient')]
        for repo in roots:
            repo.mkdir(mode=0o700)
        identities = [RuntimeIdentity('p63-resource-fixture', name, str(repo))
                      for name, repo in zip(('sender', 'recipient'), roots)]
        def configure(path, cross_root):
            bus, operator = BusStore.configure(path, bus_id='resource-fixture', allow_cross_root=cross_root)
            actors = []
            for identity, repo in zip(identities, roots):
                bus.enroll(repo, operator)
                capability, _ = bus.issue_actor(identity, repo, operator)
                actors.append(bus.authenticate(capability, identity, invoking_cwd=repo))
            Mailbox.migrate(bus, operator)
            return bus, actors, Mailbox(bus, clock=now, monotonic=now)
        denied_bus, denied_actors, denied_mailbox = configure(root / 'deny-bus', False)
        try:
            denied_mailbox.send(denied_actors[0], identities[1], body='Synthetic fixture.',
                                idempotency_key='denied', delivery='inbox')
            raise AssertionError('cross-root send unexpectedly allowed')
        except BusError as exc:
            require(exc.code == 'cross_root_denied', 'wrong cross-root rejection')
        with denied_bus.connection() as database:
            require(database.execute('SELECT count(*) FROM mail_envelopes').fetchone()[0] == 0,
                    'denied route left an envelope')
        bus, actors, mailbox = configure(root / 'allow-bus', True)
        ids = []
        for index in range(THRESHOLDS['requests']):
            clock[0] += 7
            value = mailbox.send(actors[0], identities[1], body='Synthetic fixture.',
                                 idempotency_key='request-%s' % index, delivery='inbox')
            ids.append(value['message']['message_id'])
            retry = mailbox.send(actors[0], identities[1], body='Synthetic fixture.',
                                 idempotency_key='request-%s' % index, delivery='inbox')
            require(retry['deduplicated'] and retry['message']['message_id'] == ids[-1],
                    'retry changed accepted identity')
        require([row['message_id'] for row in pages(mailbox, actors[1])] == ids,
                'paginated inbox changed accepted order')
        for index in range(THRESHOLDS['replies']):
            clock[0] += 7
            mailbox.read(actors[1], ids[index])
            mailbox.ack(actors[1], ids[index], outcome='accepted')
            reply = mailbox.reply(actors[1], ids[index], body='Synthetic result.',
                idempotency_key='reply-%s' % index, delivery='inbox', outcome='completed')
            identifier = reply['message']['message_id']
            require(mailbox.read(actors[0], identifier)['body'] == 'Synthetic result.', 'reply body mismatch')
            require(mailbox.replies(actors[0], ids[index])[0]['message_id'] == identifier,
                    'reply correlation lost')
        state = root / 'reopen.json'
        state.write_text(json.dumps(dict(bus=str(bus.root), actor=asdict(actors[1]), now=clock[0], ids=ids)))
        state.chmod(0o600)
        for _ in range(THRESHOLDS['reopen_processes']):
            remaining = THRESHOLDS['elapsed_seconds'] - (time.monotonic() - started)
            require(remaining > 0, 'elapsed budget exhausted before reopen')
            result = subprocess.run([sys.executable, str(Path(__file__).resolve()), '--reopen', str(state)],
                capture_output=True, text=True, timeout=min(15, remaining))
            require(result.returncode == 0, 'fresh process reopen failed: ' + result.stderr)
            require(json.loads(result.stdout) == dict(reopened=True, messages=100), 'unexpected reopen proof')
        copied = root / 'copied-bus'
        shutil.copytree(bus.root, copied)
        try:
            BusStore(copied)
            raise AssertionError('copied bus activated at different root')
        except BusError as exc:
            require(exc.code == 'bus_identity_mismatch', 'wrong copied-root rejection: ' + exc.code)
        store_bytes = sum(p.stat().st_size for p in bus.root.glob('mailbox.sqlite*'))
        require(store_bytes <= THRESHOLDS['store_bytes'], 'store exceeded declared ceiling')
        with bus.connection() as database:
            require(database.execute('SELECT count(*) FROM mail_envelopes').fetchone()[0] == 120,
                    'envelope count differs from bounded workload')
            require(database.execute('SELECT count(*) FROM mail_attempts').fetchone()[0] == 0,
                    'inbox-only fixture produced a dispatch attempt')
    after = census()
    elapsed = time.monotonic() - started
    require(after['fd_count'] <= before['fd_count'] + THRESHOLDS['fd_growth'], 'descriptor growth')
    require(after['children'] == before['children'] == [], 'residual child process')
    require(elapsed <= THRESHOLDS['elapsed_seconds'], 'elapsed budget exceeded')
    return dict(schema_version=1, accepted=True, synthetic=True, live_delivery_qualified=False,
                thresholds=THRESHOLDS, before=before, after=after, elapsed_seconds=round(elapsed, 3),
                store_bytes=store_bytes, cross_root_denied=True, copied_root_denied=True,
                dispatch_attempts=0, fixture_removed=True)


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--reopen':
        reopen(Path(sys.argv[2]))
    else:
        require(len(sys.argv) == 1, 'no user runtime inputs accepted')
        print(json.dumps(qualify(), sort_keys=True))
