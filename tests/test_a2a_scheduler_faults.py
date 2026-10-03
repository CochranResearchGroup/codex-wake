"""Disposable journal/projection interruption and dispatch fault fixtures."""
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from codex_wake.a2a_bus import BusStore
from codex_wake.a2a_identity import BusError, RuntimeIdentity
from codex_wake.a2a_mailbox import Mailbox
from codex_wake.a2a_scheduler import MailScheduler, publish_job


class SchedulerFaultTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.repo = self.root / 'repo'
        self.repo.mkdir()
        self.bus, self.operator = BusStore.configure(self.root / 'bus')
        self.bus.enroll(self.repo, self.operator, notify=True)
        identities = [RuntimeIdentity('fixture-runtime', name, str(self.repo))
                      for name in ('sender', 'recipient')]
        actors = []
        for identity in identities:
            capability, _ = self.bus.issue_actor(identity, self.repo, self.operator)
            actors.append(self.bus.authenticate(capability, identity, invoking_cwd=self.repo))
        self.sender, self.recipient = actors
        self.target = identities[1]
        Mailbox.migrate(self.bus, self.operator)
        self.now = 1000.0
        self.mailbox = Mailbox(self.bus, clock=lambda: self.now, monotonic=lambda: self.now,
                               rate_limit=100)
        self.scheduler = MailScheduler(self.mailbox, self.operator, owner='fixture-owner')
        self.other = MailScheduler(self.mailbox, self.operator, owner='fixture-other')
        self.bus.set_paused(False, self.operator)

    def send(self, key='fixture'):
        return self.mailbox.send(self.sender, self.target, body='private fixture body',
                                 idempotency_key=key, delivery='notify')['message']['message_id']

    def leases(self):
        return self.scheduler.acquire(), self.scheduler.acquire('recipient:' + self.recipient.key)

    def notification(self, identifier):
        with self.bus.connection() as database:
            return dict(database.execute("SELECT * FROM mail_outbox WHERE message_id=? AND kind='notification'",
                                         (identifier,)).fetchone())

    def attempt_count(self):
        with self.bus.connection() as database:
            return database.execute('SELECT count(*) FROM mail_attempts').fetchone()[0]

    def test_publication_before_journal_cut_reconciles_identical_projection(self):
        identifier = self.send()
        dispatcher = self.scheduler.acquire()
        jobs = self.scheduler.jobs(dispatcher)
        projection_root = self.root / 'jobs'
        paths = []

        def interrupted_publication(root, job):
            paths.append(publish_job(root, job))
            raise OSError('fixture interruption after atomic publication')

        with patch('codex_wake.a2a_scheduler.publish_job', side_effect=interrupted_publication):
            with self.assertRaises(OSError):
                self.scheduler.publish(dispatcher, projection_root)
        self.assertEqual(len(paths), 1)
        original = paths[0].read_bytes()
        self.assertEqual(json.loads(original), jobs[0])
        self.assertEqual(self.notification(identifier)['status'], 'pending')
        self.assertEqual(self.attempt_count(), 0)
        published = self.scheduler.publish(dispatcher, projection_root)
        self.assertEqual(len(published), 1)
        self.assertEqual(paths[0].read_bytes(), original)
        self.assertEqual(self.notification(identifier)['status'], 'published')
        self.scheduler.publish(dispatcher, projection_root)
        with self.bus.connection() as database:
            count = database.execute("SELECT count(*) FROM mail_receipts WHERE message_id=? AND kind='job_published'",
                                     (identifier,)).fetchone()[0]
        self.assertEqual(count, 1)

    def test_stale_published_projection_after_cancel_has_no_dispatch_authority(self):
        identifier = self.send()
        dispatcher, recipient = self.leases()
        published = self.scheduler.publish(dispatcher, self.root / 'jobs')
        path = Path(published[0]['path'])
        stale = json.loads(path.read_text())
        self.mailbox.cancel(self.sender, identifier)
        self.assertTrue(path.exists())
        with self.assertRaises(BusError) as caught:
            self.scheduler.claim(dispatcher, recipient, [stale['job_id']])
        self.assertEqual(caught.exception.code, 'not_processable')
        self.assertEqual(self.notification(identifier)['status'], 'suppressed')
        self.assertEqual(self.attempt_count(), 0)
        self.assertEqual(self.scheduler.jobs(dispatcher), [])

    def test_hourly_limit_counts_actual_attempts_and_reopens_after_window(self):
        identifiers = [self.send('hourly-' + str(index)) for index in range(11)]
        dispatcher, recipient = self.leases()
        for identifier in identifiers[:10]:
            claim = self.scheduler.claim(dispatcher, recipient, ['notify_' + identifier])
            self.scheduler.finish(dispatcher, recipient, claim['attempt_id'], outcome='submitted',
                                  evidence={'transport': 'fixture', 'receipt_id': 'fixture-' + identifier,
                                            'exact_thread_id': self.target.thread_id})
        self.assertEqual(self.attempt_count(), 10)
        with self.assertRaises(BusError) as caught:
            self.scheduler.claim(dispatcher, recipient, ['notify_' + identifiers[-1]])
        self.assertEqual(caught.exception.code, 'rate_limit')
        self.assertEqual(self.attempt_count(), 10)
        self.assertEqual(self.notification(identifiers[-1])['attempts'], 0)
        self.now += 3601
        dispatcher, recipient = self.leases()
        claim = self.scheduler.claim(dispatcher, recipient, ['notify_' + identifiers[-1]])
        self.assertTrue(claim['attempt_id'])
        self.assertEqual(self.attempt_count(), 11)

    def test_other_owner_cannot_use_valid_lease_to_claim_or_finish(self):
        identifier = self.send()
        dispatcher, recipient = self.leases()
        with self.assertRaises(BusError) as caught:
            self.other.claim(dispatcher, recipient, ['notify_' + identifier])
        self.assertEqual(caught.exception.code, 'stale_lease')
        self.assertEqual(self.attempt_count(), 0)
        self.assertEqual(self.notification(identifier)['attempts'], 0)
        claim = self.scheduler.claim(dispatcher, recipient, ['notify_' + identifier])
        with self.assertRaises(BusError) as caught:
            self.other.finish(dispatcher, recipient, claim['attempt_id'], outcome='submitted',
                              evidence={'receipt_id': 'foreign-owner'})
        self.assertEqual(caught.exception.code, 'stale_lease')
        self.assertEqual(self.notification(identifier)['status'], 'dispatching')
        self.scheduler.finish(dispatcher, recipient, claim['attempt_id'], outcome='submitted',
                              evidence={'transport': 'fixture', 'receipt_id': 'right-owner',
                                        'exact_thread_id': self.target.thread_id})

    def assert_revocation_blocks_dispatch(self, actor):
        identifier = self.send()
        dispatcher, recipient = self.leases()
        self.scheduler.publish(dispatcher, self.root / 'jobs')
        self.bus.revoke_actor(actor.actor_id, self.operator)
        with self.assertRaises(BusError) as caught:
            self.scheduler.claim(dispatcher, recipient, ['notify_' + identifier])
        self.assertEqual(caught.exception.code, 'authorization_denied')
        self.assertEqual(self.attempt_count(), 0)
        self.assertEqual(self.notification(identifier)['attempts'], 0)

    def test_sender_revocation_after_publication_blocks_dispatch(self):
        self.assert_revocation_blocks_dispatch(self.sender)

    def test_recipient_revocation_after_publication_blocks_dispatch(self):
        self.assert_revocation_blocks_dispatch(self.recipient)

    def test_sql_failure_before_claim_commit_rolls_back_attempt_and_receipts(self):
        identifier = self.send()
        dispatcher, recipient = self.leases()
        before = self.notification(identifier)
        with self.bus.connection() as database:
            receipts_before = database.execute('SELECT count(*) FROM mail_receipts').fetchone()[0]
        stages = []

        def disk_full(stage):
            stages.append(stage)
            if stage == 'before_commit':
                raise sqlite3.OperationalError('database or disk is full')

        self.mailbox.fault = disk_full
        with self.assertRaises(BusError) as caught:
            self.scheduler.claim(dispatcher, recipient, ['notify_' + identifier])
        self.assertEqual(caught.exception.code, 'store_unavailable')
        self.assertEqual(stages, ['before_commit'])
        self.assertEqual(self.attempt_count(), 0)
        self.assertEqual(self.notification(identifier), before)
        self.assertEqual(self.mailbox.show(self.sender, identifier)['state']['notification'], 'pending')
        with self.bus.connection() as database:
            self.assertEqual(database.execute('SELECT count(*) FROM mail_receipts').fetchone()[0], receipts_before)
        self.mailbox.fault = None
        self.scheduler.claim(dispatcher, recipient, ['notify_' + identifier])
        self.assertEqual(self.attempt_count(), 1)
        self.assertEqual(self.notification(identifier)['attempts'], 1)

    def test_scanning_respects_bound_and_fifo_without_consuming_attempts(self):
        identifiers = [self.send('scan-' + str(index)) for index in range(5)]
        dispatcher = self.scheduler.acquire()
        jobs = self.scheduler.jobs(dispatcher, limit=3)
        self.assertEqual([job['message_id'] for job in jobs], identifiers[:3])
        self.assertEqual(self.attempt_count(), 0)
        for invalid in (0, 101, True):
            with self.subTest(limit=invalid):
                with self.assertRaises(BusError) as caught:
                    self.scheduler.jobs(dispatcher, limit=invalid)
                self.assertEqual(caught.exception.code, 'invalid_argument')
        self.assertEqual([job['message_id'] for job in self.scheduler.jobs(dispatcher, limit=100)], identifiers)
