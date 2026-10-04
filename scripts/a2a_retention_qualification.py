#!/usr/bin/env python3
"""Owned installed old/new retention fixtures; no agent or transport effects."""
import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

from codex_wake.a2a_bus import BusStore
from codex_wake.a2a_identity import BusError, RuntimeIdentity
from codex_wake.a2a_mailbox import Mailbox, MAILBOX_SCHEMA
from codex_wake.a2a_operations import MailOperations
from codex_wake.a2a_receipt_authority import ConfiguredReceiptAuthority
from codex_wake.a2a_receipt_signals import ReceiptSignalAdapter
from codex_wake.event_wake import EventWake
from codex_wake.signal_records import ManagedReaderCapability, WakeRecordPublisher, signal_journal_path
from codex_wake.signal_store import SQLiteSignalModule
from codex_wake.signals import Resume, WakeIntent, Registration, Ingested


def require(value, message):
    if not value:
        raise AssertionError(message)


def census():
    return dict(fd_count=len(os.listdir('/proc/self/fd')),
        children=Path('/proc/self/task/%s/children' % os.getpid()).read_text().split())


def state(root):
    return json.loads((root / 'fixture.json').read_text())


def prepare(root, age_days):
    require(root.name.startswith('case-') and root.parent.name.startswith('codex-wake-p63-retention-'), 'owned fixture root required')
    require(not list(root.iterdir()), 'prepare requires an empty fixture root')
    require(MAILBOX_SCHEMA == 1, 'legacy installed schema must be one')
    repo = root / 'repo'; repo.mkdir(mode=0o700)
    bus, operator = BusStore.configure(root / 'bus', bus_id='retention-fixture')
    bus.enroll(repo, operator)
    identities = [RuntimeIdentity('p63-retention-fixture', name, str(repo)) for name in ('sender','recipient')]
    capabilities, actors = [], []
    for identity in identities:
        capability, _ = bus.issue_actor(identity, repo, operator)
        capabilities.append(str(capability))
        actors.append(bus.authenticate(capability, identity, invoking_cwd=repo))
    Mailbox.migrate(bus, operator)
    # Both clock coordinates move together. Later unmodified installed CLI
    # observations remain valid; this is fixture aging, not a thirty-day soak.
    offset = age_days * 86400
    mailbox = Mailbox(bus, clock=lambda: time.time() - offset,
        monotonic=lambda: time.monotonic() - offset)
    ids, grants = [], []
    for key in ('large','small'):
        identifier = mailbox.send(actors[0], identities[1], body='x' * (32768 if key == 'large' else 20),
            idempotency_key=key, delivery='inbox')['message']['message_id']
        mailbox.ack(actors[1], identifier, outcome='declined')
        ids.append(identifier)
        adapter = ReceiptSignalAdapter(mailbox, actors[0], identifier)
        grants.append(dict(source_instance=adapter.source_instance, bus_root=str(bus.root), bus_id=bus.bus_id,
            operator_capability=str(operator), actor=asdict(actors[0]), message_id=identifier))
    config = root / 'authority.json'
    config.write_text(json.dumps(dict(schema_version=1, wake_root=str(root/'wake'), grants=grants)))
    config.chmod(0o600)
    (root/'fixture.json').write_text(json.dumps(dict(operator=str(operator), capabilities=capabilities,
        identifiers=ids, source_instances=[g['source_instance'] for g in grants], age_days=age_days)))
    (root/'fixture.json').chmod(0o600)
    return dict(prepared_schema=MAILBOX_SCHEMA, messages=len(ids))


def inspect(root):
    value = state(root)
    bus = BusStore(root/'bus')
    identity = RuntimeIdentity('p63-retention-fixture','sender',str(root/'repo'))
    actor = bus.authenticate(Path(value['capabilities'][0]), identity, invoking_cwd=root/'repo')
    mailbox = Mailbox(bus)
    messages = [mailbox.show(actor, identifier) for identifier in value['identifiers']]
    require(all(item.get('compacted') and not item['body_retained'] for item in messages), 'fresh process lost compact identity')
    require([m['message_id'] for m in messages] == value['identifiers'], 'message identity changed')
    require(len(mailbox.list(actor,outbox=True)['messages']) == 2, 'metadata listing lost tombstones')
    retry = mailbox.send(actor, RuntimeIdentity('p63-retention-fixture','recipient',str(root/'repo')),
        body='x'*32768, idempotency_key='large', delivery='inbox')
    require(retry['deduplicated'] and retry['message']['message_id']==value['identifiers'][0], 'installed duplicate identity changed')
    return dict(schema=MAILBOX_SCHEMA, compacted=2, duplicate_identity_preserved=True)


def qualify(cli, legacy_python):
    require(MAILBOX_SCHEMA == 2, 'qualification must run from new installed package')
    legacy_cli = str(Path(legacy_python).parent/'codex-wake')
    started, before = time.monotonic(), census()
    environment = dict(os.environ); environment.pop('PYTHONPATH',None)
    def run(command, cwd, expected=0):
        remaining = 35 - (time.monotonic()-started)
        require(remaining > 0, 'qualification exceeded total deadline')
        completed = subprocess.run(command, cwd=cwd, env=environment, capture_output=True,
            text=True, timeout=min(10,remaining))
        require(completed.returncode==expected, 'installed process failed: '+completed.stdout[:1500]+completed.stderr[:1500])
        return json.loads(completed.stdout)
    cases = []
    with tempfile.TemporaryDirectory(prefix='codex-wake-p63-retention-') as directory:
        for age in (31,91):
            root=Path(directory)/('case-'+str(age));root.mkdir(mode=0o700)
            prepared=run([legacy_python,str(Path(__file__).resolve()),'--prepare',str(root),'--age-days',str(age)],root)
            require(prepared['prepared_schema']==1,'legacy fixture did not originate in old wheel')
            value=state(root);operator=Path(value['operator']);bus=BusStore(root/'bus')
            def invoke(executable,verb,extra=(),expected=0):
                return run([executable,'a2a',verb,'--bus-root',str(bus.root),
                    '--operator-capability',str(operator),'--json',*extra],root,expected)
            require(invoke(legacy_cli,'doctor')['success'],'old installed reader failed before migration')
            require(invoke(cli,'doctor',expected=8)['error']['code']=='unsupported_mailbox_schema','new reader silently migrated old store')
            require(invoke(cli,'migrate')['success'],'explicit installed migration failed')
            require(invoke(legacy_cli,'doctor',expected=8)['error']['code']=='unsupported_mailbox_schema','old binary accepted schema two')
            mailbox=Mailbox(bus)
            capability=ManagedReaderCapability(wake_root=root/'wake', reader_id='p63-fixture-reader',
                generation=1,schema_versions=frozenset({1,2}),active=True)
            module=SQLiteSignalModule(signal_journal_path(root/'wake'),
                record_publisher=WakeRecordPublisher(root/'wake',capability))
            pins=invoke(cli,'compact')['compact']
            require(not pins['eligible'] and all('unprojected_receipt_signal' in c['pins'] for c in pins['candidates']), 'migration lost receipt pins')
            for index, source in enumerate(value['source_instances']):
                adapter=ConfiguredReceiptAuthority(root/'authority.json',root/'wake').adapter(source)
                now=datetime.now(timezone.utc)
                wake=EventWake(module,adapters=[adapter],clock=lambda:now,id_factory=lambda:'wake-retention-'+str(index))
                registered=wake.register(WakeIntent(when=adapter.request('declined'),
                    resume=Resume(prompt='Synthetic retention fixture.',cwd=root/'repo',
                        target=dict(transport='tmux',tmux_socket='/tmp/retention-fixture',pane='%1'))),idempotency_key='retention-'+str(index))
                require(isinstance(registered,Registration),'fixture source arm failed')
                require(isinstance(adapter.mirror(module),Ingested),'production receipt mirror failed')
                ack=invoke(cli,'ack-projections',('--wake-root',str(root/'wake'),'--receipt-authority',str(root/'authority.json'),'--source-instance',source))
                require(ack['projection']['acknowledged']==3,'production projection acknowledgement lost receipts')
            preview=invoke(cli,'compact')['compact']
            require(preview['eligible']==value['identifiers'],'installed compact eligibility changed')
            compact=invoke(cli,'compact',('--apply-fingerprint',preview['fingerprint']))['compact']
            require(compact['compacted']==2,'installed compaction failed')
            maintenance=invoke(cli,'reclaim-space',('--apply',))['maintenance']
            require(maintenance['after_bytes']<maintenance['before_bytes'],'physical file reduction not observed')
            if age==31:
                proof=run([sys.executable,str(Path(__file__).resolve()),'--inspect',str(root)],root)
                require(proof['duplicate_identity_preserved'],'fresh installed inspection failed')
            else:
                preview=invoke(cli,'compact')['compact']
                require(all(c['action']=='retire' for c in preview['candidates']),'old tombstone did not age out')
                retired=invoke(cli,'compact',('--apply-fingerprint',preview['fingerprint']))['compact']
                require(retired['retired']==2,'installed retirement failed')
                identity=RuntimeIdentity('p63-retention-fixture','sender',str(root/'repo'))
                actor=bus.authenticate(Path(value['capabilities'][0]),identity,invoking_cwd=root/'repo')
                try:
                    Mailbox(bus).send(actor,RuntimeIdentity('p63-retention-fixture','recipient',str(root/'repo')),
                        body='x'*32768,idempotency_key='large',delivery='inbox')
                    raise AssertionError('old key silently became a new message')
                except BusError as exc:
                    require(exc.code=='idempotency_horizon','wrong retired intent refusal')
            with bus.connection() as database:
                require(database.execute('PRAGMA integrity_check').fetchone()[0]=='ok','integrity check failed')
                require(not database.execute('PRAGMA foreign_key_check').fetchall(),'migration violated references')
                require(database.execute('SELECT count(*) FROM mail_attempts').fetchone()[0]==0,'unexpected dispatch attempt')
            cases.append(dict(age_days=age,messages=2,reclaimed_bytes=maintenance['reclaimed_bytes']))
    after=census(); elapsed=time.monotonic()-started
    require(after['fd_count']<=before['fd_count']+2 and not after['children'],'resource census failed')
    require(elapsed<35,'qualification deadline exceeded')
    return dict(status='accepted_synthetic',cases=cases,elapsed_seconds=round(elapsed,3),before=before,after=after,
        dispatch_attempts=0,real_delivery_qualified=False,real_soak_qualified=False,
        clock_fixture='historical wall and monotonic offsets; real fresh CLI observations',
        installed_module=__import__('codex_wake.a2a_mailbox',fromlist=['']).__file__)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--cli');parser.add_argument('--legacy-python')
    parser.add_argument('--prepare',type=Path);parser.add_argument('--age-days',type=int,choices=(31,91))
    parser.add_argument('--inspect',type=Path)
    args=parser.parse_args()
    if args.prepare:
        result=prepare(args.prepare,args.age_days)
    elif args.inspect:
        result=inspect(args.inspect)
    else:
        if not args.cli or not args.legacy_python:parser.error('--cli and --legacy-python required')
        result=qualify(args.cli,args.legacy_python)
    print(json.dumps(result,sort_keys=True))
