"""Public mailbox behavior with a controlled time-acquisition seam."""
import json
from pathlib import Path
import tempfile
import unittest

from codex_wake.a2a_bus import BusStore
from codex_wake.a2a_identity import BusError, RuntimeIdentity
from codex_wake.a2a_mailbox import Mailbox
from codex_wake.time_provider import TimeDecision


class NetworkMailboxTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory();self.addCleanup(self.temporary.cleanup)
        self.root=Path(self.temporary.name);self.repo=self.root/'repo';self.repo.mkdir()
        self.bus,self.operator=BusStore.configure(self.root/'bus')
        self.bus.enroll(self.repo,self.operator)
        self.identities=[RuntimeIdentity('fixture',s,str(self.repo)) for s in ('sender','recipient')]
        self.actors=[]
        for identity in self.identities:
            cap,_=self.bus.issue_actor(identity,self.repo,self.operator)
            self.actors.append(self.bus.authenticate(cap,identity,invoking_cwd=self.repo))
        Mailbox.migrate(self.bus,self.operator)
        self.reading=TimeDecision('network',('a','b'),1000,1000.1)

    def activate(self):
        Mailbox.activate_network_time(self.bus,self.operator,provider=lambda:self.reading)
        self.mailbox=Mailbox(self.bus,time_provider=lambda:self.reading)

    def test_uncertain_creation_is_retryable_and_creates_no_message(self):
        self.activate()
        self.reading=TimeDecision('uncertain',reason='outage')
        with self.assertRaises(BusError) as error:
            self.mailbox.send(self.actors[0],self.identities[1],body='fixture',idempotency_key='request')
        self.assertEqual(error.exception.code,'time_uncertain')
        self.assertEqual(self.mailbox.list(self.actors[0],outbox=True)['messages'],[])

    def test_inspection_and_cancellation_work_without_fabricated_utc(self):
        self.activate()
        sent=self.mailbox.send(self.actors[0],self.identities[1],body='fixture',idempotency_key='request')
        identifier=sent['message']['message_id']
        self.reading=TimeDecision('uncertain',reason='outage')
        self.assertEqual(self.mailbox.show(self.actors[0],identifier)['message_id'],identifier)
        self.assertEqual(len(self.mailbox.list(self.actors[1])['messages']),1)
        cancelled=self.mailbox.cancel(self.actors[0],identifier)
        self.assertEqual(cancelled['message']['state']['admission'],'cancelled')
        receipt=next(r for r in cancelled['message']['receipts'] if r['kind']=='cancelled')
        self.assertIsNone(receipt['created_at'])
        self.assertEqual(receipt['details']['time_status'],'uncertain')

    def test_deadline_boundary_pauses_delivery_then_expires_without_rewriting(self):
        self.activate()
        sent=self.mailbox.send(self.actors[0],self.identities[1],body='fixture',idempotency_key='request',ttl=60)
        identifier=sent['message']['message_id']
        self.assertEqual(sent['message']['expires_at'],1060.1)
        self.reading=TimeDecision('network',('a','b'),1059.9,1060.2)
        with self.assertRaises(BusError) as error:
            self.mailbox.read(self.actors[1],identifier)
        self.assertEqual(error.exception.code,'time_uncertain')
        self.assertEqual(self.mailbox.show(self.actors[0],identifier)['state']['recipient'],'unread')
        self.reading=TimeDecision('network',('a','b'),1060.2,1060.3)
        reopened=Mailbox(BusStore(self.bus.root),time_provider=lambda:self.reading)
        expired=reopened.read(self.actors[1],identifier)
        self.assertEqual(expired['message']['state']['admission'],'expired')
        self.assertEqual(expired['message']['expires_at'],1060.1)

    def test_network_schema_snapshot_reports_actual_version_and_preserves_deadlines(self):
        from codex_wake.a2a_backup import MailBackup
        self.activate()
        sent=self.mailbox.send(self.actors[0],self.identities[1],body='fixture',idempotency_key='request',ttl=60)
        snapshot=self.root/'snapshot'
        backup=MailBackup(self.bus,self.operator)
        backup.create(snapshot)
        self.assertEqual(backup.verify(snapshot)['mailbox_schema'],3)
        self.assertEqual(self.mailbox.show(self.actors[0],sent['message']['message_id'])['expires_at'],1060.1)

    def test_activation_refuses_legacy_clock_anomaly_without_reset(self):
        legacy=Mailbox(self.bus,clock=lambda:1000,monotonic=lambda:1000)
        legacy.send(self.actors[0],self.identities[1],body='legacy',idempotency_key='legacy')
        with self.bus.connection() as database:
            checkpoint=database.execute("SELECT value FROM meta WHERE key='mail_clock'").fetchone()[0]
        with self.assertRaises(BusError) as error:
            self.activate()
        self.assertEqual(error.exception.code,'clock_anomaly')
        with self.bus.connection() as database:
            self.assertEqual(json.loads(database.execute("SELECT value FROM meta WHERE key='mailbox_schema'").fetchone()[0]),2)
            self.assertEqual(database.execute("SELECT value FROM meta WHERE key='mail_clock'").fetchone()[0],checkpoint)

    def test_interrupted_commit_reconciles_original_intent_and_deadline(self):
        self.activate()
        def crash(stage):
            if stage=='after_commit': raise OSError('fixture exit after commit')
        mailbox=Mailbox(self.bus,time_provider=lambda:self.reading,fault=crash)
        with self.assertRaises(BusError) as error:
            mailbox.send(self.actors[0],self.identities[1],body='fixture',idempotency_key='request',ttl=60)
        self.assertEqual(error.exception.code,'effect_uncertain')
        self.reading=TimeDecision('network',('a','b'),1010,1010.1)
        retry=self.mailbox.send(self.actors[0],self.identities[1],body='fixture',idempotency_key='request',ttl=60)
        self.assertTrue(retry['deduplicated'])
        self.assertEqual(retry['message']['expires_at'],1060.1)

    def test_concurrent_admission_has_one_identity_and_preserves_deadline(self):
        from concurrent.futures import ThreadPoolExecutor
        self.activate()
        def send(_):
            return self.mailbox.send(self.actors[0],self.identities[1],body='fixture',idempotency_key='request',ttl=60)
        with ThreadPoolExecutor(max_workers=4) as executor:
            values=list(executor.map(send,range(4)))
        self.assertEqual(len({v['message']['message_id'] for v in values}),1)
        self.assertEqual({v['message']['expires_at'] for v in values},{1060.1})
        self.assertEqual(sum(not v['deduplicated'] for v in values),1)

    def test_fresh_process_can_inspect_during_uncertainty_without_network(self):
        import subprocess
        import sys
        self.activate()
        message=self.mailbox.send(self.actors[0],self.identities[1],body='fixture',idempotency_key='request',ttl=60)['message']
        completed=subprocess.run([sys.executable,'-m','codex_wake.cli','messages','show',message['message_id'],
                                  '--as-operator','--operator-capability',str(self.operator),'--bus-root',str(self.bus.root),'--json'],
                                  capture_output=True,text=True,timeout=5)
        self.assertEqual(completed.returncode,0,completed.stderr+completed.stdout)
        self.assertIn('1060.1',completed.stdout)
        self.assertEqual(self.mailbox.show(self.actors[0],message['message_id'])['expires_at'],1060.1)

    def test_scheduler_pauses_boundary_jobs_and_recovers_original_expiration(self):
        from codex_wake.a2a_scheduler import MailScheduler
        self.activate()
        message=self.mailbox.send(self.actors[0],self.identities[1],body='fixture',idempotency_key='request',ttl=60)['message']
        scheduler=MailScheduler(self.mailbox,self.operator)
        self.reading=TimeDecision('network',('a','b'),1059.9,1060.2)
        lease=scheduler.acquire()
        self.assertEqual(scheduler.jobs(lease),[])
        self.assertEqual(self.mailbox.show(self.actors[0],message['message_id'])['state']['admission'],'accepted')
        self.reading=TimeDecision('uncertain',reason='network_outage')
        with self.assertRaises(BusError) as error:
            scheduler.jobs(lease)
        self.assertEqual(error.exception.code,'time_uncertain')
        self.reading=TimeDecision('network',('a','b'),1061,1061.1)
        self.assertEqual(scheduler.jobs(lease),[])
        self.assertEqual(self.mailbox.show(self.actors[0],message['message_id'])['state']['admission'],'expired')

    def test_initial_consensus_is_a_persisted_regression_fence(self):
        self.activate()
        self.reading=TimeDecision('network',('a','b'),900,900.1)
        with self.assertRaises(BusError) as error:
            self.mailbox.send(self.actors[0],self.identities[1],body='fixture',idempotency_key='request')
        self.assertEqual(error.exception.code,'clock_anomaly')

    def test_reply_metadata_remains_inspectable_during_outage(self):
        self.activate()
        message = self.mailbox.send(self.actors[0], self.identities[1], body='request', idempotency_key='request')['message']
        self.mailbox.reply(self.actors[1], message['message_id'], body='reply', idempotency_key='reply')
        self.reading = TimeDecision('uncertain', reason='outage')
        self.assertEqual(len(self.mailbox.replies(self.actors[0], message['message_id'])), 1)

    def test_healthy_legacy_migration_preserves_existing_envelope_and_checkpoint(self):
        import time
        legacy = Mailbox(self.bus)
        original = legacy.send(self.actors[0], self.identities[1], body='legacy', idempotency_key='legacy', ttl=60)['message']
        with self.bus.connection() as database:
            checkpoint = database.execute("SELECT value FROM meta WHERE key='mail_clock'").fetchone()[0]
        current = time.time()
        self.reading = TimeDecision('network', ('a','b'), current-0.1, current+0.1)
        self.activate()
        shown = self.mailbox.show(self.actors[0], original['message_id'])
        self.assertEqual(shown['expires_at'], original['expires_at'])
        with self.bus.connection() as database:
            self.assertEqual(database.execute("SELECT value FROM meta WHERE key='mail_clock_before_network'").fetchone()[0], checkpoint)
            self.assertEqual(database.execute('PRAGMA foreign_key_check').fetchall(), [])
