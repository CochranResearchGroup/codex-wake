from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import tempfile
import unittest

from codex_wake.a2a_bus import BusStore
from codex_wake.a2a_identity import BusError, RuntimeIdentity
from codex_wake.a2a_mailbox import Mailbox
from codex_wake.a2a_scheduler import MailScheduler, publish_job


class SchedulerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.repo = self.root / 'repo'; self.repo.mkdir()
        self.bus, self.operator = BusStore.configure(self.root / 'bus')
        self.bus.enroll(self.repo, self.operator, notify=True)
        self.identities = [RuntimeIdentity('fixture', name, str(self.repo)) for name in ('sender','recipient')]
        self.actors = []
        for identity in self.identities:
            capability, _ = self.bus.issue_actor(identity, self.repo, self.operator)
            self.actors.append(self.bus.authenticate(capability, identity, invoking_cwd=self.repo))
        Mailbox.migrate(self.bus, self.operator)
        self.now = 1000.
        self.mailbox = Mailbox(self.bus, clock=lambda: self.now, monotonic=lambda: self.now)
        self.scheduler = MailScheduler(self.mailbox, self.operator, owner='first')
        self.other = MailScheduler(self.mailbox, self.operator, owner='second')
        self.bus.set_paused(False, self.operator)

    def send(self, key='intent', **kwargs):
        return self.mailbox.send(self.actors[0], self.identities[1], body='Fixture only', idempotency_key=key, **kwargs)['message']['message_id']

    def leases(self, scheduler=None):
        scheduler = scheduler or self.scheduler
        return scheduler.acquire(), scheduler.acquire('recipient:' + self.actors[1].key)

    def test_concurrent_owners_and_generation_fences(self):
        with ThreadPoolExecutor(max_workers=2) as pool:
            leases = list(pool.map(lambda s: s.acquire(), (self.scheduler, self.other)))
        self.assertEqual(sum(lease is not None for lease in leases), 1)
        index = next(i for i, lease in enumerate(leases) if lease)
        previous = (self.scheduler, self.other)[index]
        successor = (self.other, self.scheduler)[index]
        self.now += 31
        newer = successor.acquire()
        self.assertEqual(newer.generation, leases[index].generation + 1)
        with self.assertRaises(BusError) as error: previous.jobs(leases[index])
        self.assertEqual(error.exception.code, 'stale_lease')

    def test_projection_is_private_body_free_and_idempotent(self):
        self.send()
        dispatcher = self.scheduler.acquire()
        jobs = self.scheduler.jobs(dispatcher)
        path = publish_job(self.root / 'jobs', jobs[0])
        self.assertEqual(publish_job(self.root / 'jobs', jobs[0]), path)
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertNotIn('Fixture only', path.read_text())
        changed = dict(jobs[0], recipient_key='foreign')
        with self.assertRaises(BusError): publish_job(self.root / 'jobs', changed)
        self.mailbox.cancel(self.actors[0], jobs[0]['message_id'])
        recipient = self.scheduler.acquire('recipient:' + self.actors[1].key)
        with self.assertRaises(BusError): self.scheduler.claim(dispatcher, recipient, [jobs[0]['job_id']])

    def test_expired_dispatch_is_uncertain_never_retried(self):
        identifier = self.send()
        dispatcher, recipient = self.leases()
        claim = self.scheduler.claim(dispatcher, recipient, ['notify_' + identifier])
        self.now += 31
        new_dispatcher = self.other.acquire()
        self.assertEqual(self.other.recover(new_dispatcher), 1)
        self.assertEqual(self.other.jobs(new_dispatcher), [])
        self.assertEqual(self.mailbox.show(self.actors[0], identifier)['state']['notification'], 'uncertain')
        with self.assertRaises(BusError): self.scheduler.finish(dispatcher, recipient, claim['attempt_id'], outcome='submitted', evidence={'receipt_id':'late'})
        with self.assertRaises(BusError): self.mailbox.cancel(self.actors[0], identifier)

    def test_reopening_request_cannot_use_replaced_recipient_capability(self):
        identifier = self.send(resume_missing=True)
        self.bus.rotate_actor(self.actors[1].actor_id, self.operator)
        dispatcher, recipient = self.leases()
        with self.assertRaises(BusError) as error:
            self.scheduler.claim(dispatcher, recipient, ['notify_' + identifier])
        self.assertEqual(error.exception.code, 'authorization_denied')
        self.assertEqual(self.mailbox.show(self.actors[0], identifier)['state']['notification'], 'pending')

    def test_effect_context_rejects_replaced_recipient_lease_before_original_expiry(self):
        identifier = self.send(resume_missing=True)
        dispatcher, recipient = self.leases()
        job = self.scheduler.jobs(dispatcher)[0]
        claim = self.scheduler.claim(dispatcher, recipient, [job['job_id']])
        self.scheduler.release(recipient)
        self.assertIsNotNone(self.other.acquire('recipient:' + self.actors[1].key))
        with self.assertRaises(BusError) as error:
            self.scheduler.notification_context(job, attempt_id=claim['attempt_id'])
        self.assertEqual(error.exception.code, 'stale_lease')

    def test_provably_unsent_backoff_and_attempt_bound(self):
        identifier = self.send()
        for count in range(3):
            dispatcher, recipient = self.leases()
            claim = self.scheduler.claim(dispatcher, recipient, ['notify_' + identifier])
            self.scheduler.finish(dispatcher, recipient, claim['attempt_id'], outcome='unsent', evidence={'reason':'fixture_pre_io'})
            state = self.mailbox.show(self.actors[0], identifier)['state']['notification']
            self.assertEqual(state, 'failed' if count == 2 else 'deferred')
            self.scheduler.release(dispatcher); self.scheduler.release(recipient)
            self.now += (5, 30, 120)[count]
        with self.bus.connection() as database:
            self.assertEqual(database.execute('SELECT attempts FROM mail_outbox WHERE kind=?', ('notification',)).fetchone()[0], 3)
        self.assertEqual(self.scheduler.jobs(self.scheduler.acquire()), [])

    def test_fifo_batch_cannot_overtake_deferred_or_uncertain_head(self):
        first, second = self.send('first'), self.send('second')
        dispatcher, recipient = self.leases()
        with self.assertRaises(BusError) as error: self.scheduler.claim(dispatcher, recipient, ['notify_' + second])
        self.assertEqual(error.exception.code, 'fifo_conflict')
        claim = self.scheduler.claim(dispatcher, recipient, ['notify_' + first, 'notify_' + second])
        self.scheduler.finish(dispatcher, recipient, claim['attempt_id'], outcome='submitted', evidence={'receipt_id':'fixture','transport':'fixture','exact_thread_id':'recipient'})
        for identifier in (first, second):
            state = self.mailbox.show(self.actors[0], identifier)['state']
            self.assertEqual(state['notification'], 'submitted')
            self.assertEqual(state['recipient'], 'unread')

    def test_pause_revocation_expiry_and_non_notify_grants(self):
        identifier = self.send(ttl=60)
        dispatcher, recipient = self.leases()
        self.bus.set_paused(True, self.operator)
        with self.assertRaises(BusError) as error: self.scheduler.claim(dispatcher, recipient, ['notify_' + identifier])
        self.assertEqual(error.exception.code, 'paused')
        self.bus.set_paused(False, self.operator)
        self.bus.enroll(self.repo, self.operator, notify=False)
        with self.assertRaises(BusError) as error: self.scheduler.claim(dispatcher, recipient, ['notify_' + identifier])
        self.assertEqual(error.exception.code, 'authorization_denied')
        self.now += 61
        dispatcher = self.scheduler.acquire()
        self.assertEqual(self.scheduler.jobs(dispatcher), [])
        self.assertEqual(self.mailbox.show(self.actors[0], identifier)['state']['admission'], 'expired')

    def test_busy_deferral_does_not_consume_attempts_or_repeat_receipts(self):
        identifier = self.send()
        dispatcher = self.scheduler.acquire()
        self.scheduler.defer(dispatcher, 'notify_' + identifier, 'busy')
        self.now += 5
        self.scheduler.defer(dispatcher, 'notify_' + identifier, 'busy')
        with self.bus.connection() as database:
            self.assertEqual(database.execute("SELECT attempts FROM mail_outbox WHERE kind='notification'").fetchone()[0], 0)
            self.assertEqual(database.execute("SELECT count(*) FROM mail_receipts WHERE kind='deferred'").fetchone()[0], 1)
        self.assertEqual(self.mailbox.show(self.actors[0], identifier)['state']['recipient'], 'unread')
