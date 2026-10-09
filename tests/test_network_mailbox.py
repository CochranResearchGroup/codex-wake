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

    def test_reply_waits_for_another_bounded_network_acquisition(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Event, Timer
        self.activate()
        sent=self.mailbox.send(self.actors[0],self.identities[1],body='request',idempotency_key='request')
        identifier=sent['message']['message_id']
        self.mailbox.read(self.actors[1],identifier)
        self.mailbox.ack(self.actors[1],identifier,outcome='accepted')
        entered,release=Event(),Event()
        def slow_provider():
            entered.set()
            if not release.wait(5): raise RuntimeError('acquisition control timed out')
            return self.reading
        competing=Mailbox(self.bus,time_provider=slow_provider)
        with ThreadPoolExecutor(max_workers=1) as pool:
            future=pool.submit(competing.read,self.actors[0],identifier)
            self.assertTrue(entered.wait(2))
            # Controlled acquisition latency exceeds the old one-second lock wait.
            timer=Timer(1.3,release.set);timer.start()
            try:
                reply=self.mailbox.reply(self.actors[1],identifier,body='result',idempotency_key='reply',outcome='completed')
            finally:
                release.set();timer.cancel()
            future.result(timeout=2)
        self.assertEqual(reply['message']['in_reply_to'],identifier)
        self.assertEqual(self.mailbox.show(self.actors[0],identifier)['state']['recipient'],'completed')

    def test_reply_transport_time_cannot_bypass_persisted_regression_guard(self):
        from codex_wake.a2a_time import mailbox_time
        self.activate()
        with self.bus.connection(read_only=True) as database:
            checkpoint=database.execute("SELECT value FROM meta WHERE key='mail_network_clock'").fetchone()[0]
        self.reading=TimeDecision('network',('a','b'),900,900.1)
        with self.assertRaises(BusError) as error:
            mailbox_time(self.mailbox,upper=True)
        self.assertEqual(error.exception.code,'clock_anomaly')
        with self.bus.connection(read_only=True) as database:
            self.assertEqual(database.execute("SELECT value FROM meta WHERE key='mail_network_clock'").fetchone()[0],checkpoint)

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

    def test_native_worker_holds_outage_then_recovers_without_restart(self):
        import contextlib
        import io
        from unittest.mock import patch
        from codex_wake.cli import main
        self.activate()
        bindings = self.root/'bindings.json'
        bindings.write_text(json.dumps(dict(schema_version=1, bindings=[dict(transport='tmux_notification_v1', namespace='fixture', thread_id='recipient', root=str(self.repo), tmux_socket='/fixture/socket', pid=1, process_start_ticks=1, boot_id='fixture', generation='fixture')])))
        bindings.chmod(0o600)
        calls = []
        def acquisition():
            calls.append(1)
            return TimeDecision('uncertain', reason='outage') if len(calls) == 1 else self.reading
        output = io.StringIO()
        with patch('codex_wake.time_inspection.network_time_decision', side_effect=acquisition), contextlib.redirect_stdout(output):
            code = main(['a2a','worker','--bus-root',str(self.bus.root),'--operator-capability',str(self.operator),
                         '--bindings-file',str(bindings),'--duration','1','--interval','0.1','--max-dispatches','1'])
        rows = [json.loads(line) for line in output.getvalue().splitlines()]
        self.assertEqual(code, 0, rows)
        self.assertEqual(rows[0]['dispatch']['reason'], 'time_uncertain')
        self.assertGreater(len(calls), 1)
        self.assertEqual(rows[-1]['worker']['status'], 'finished')

    def test_tmux_transport_checks_network_expiry_instead_of_guest_wall(self):
        from unittest.mock import patch
        from codex_wake.a2a_tmux_delivery import TmuxBinding
        self.activate()
        binding = TmuxBinding('fixture','recipient',str(self.repo),'/fixture/socket',1,1,'fixture','fixture')
        claim = dict(attempt_id='attempt_'+'a'*32)
        job = dict(message_id='msg_'+'b'*32, expires_at=1060)
        empty = '› Ask Codex to do anything\n GPT-6 · /repo · session\n ← for agents · ? for shortcuts\n'
        with patch('codex_wake.time_inspection.network_time_decision', return_value=self.reading), \
             patch.object(TmuxBinding, 'locate', return_value=({}, dict(pane_id='%fixture'))), \
             patch.object(TmuxBinding, 'probe', return_value=dict(status='ready')), \
             patch('codex_wake.a2a_tmux_delivery.SubprocessTmuxRunner') as runner:
            runner.return_value.capture_pane.side_effect = [empty,'A2A_NOTIFICATION='+job['message_id']]
            result = binding.deliver(claim,job,self.bus.root)
        self.assertEqual(result['status'],'submitted',result)
