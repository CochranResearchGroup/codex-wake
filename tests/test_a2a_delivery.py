import json
import os
from pathlib import Path
import socket
import tempfile
import threading
import time
import unittest

from codex_wake.a2a_bus import BusStore
from codex_wake.a2a_delivery import NotificationDispatcher, bind_client, load_bindings
from codex_wake.a2a_identity import RuntimeIdentity
from codex_wake.a2a_mailbox import Mailbox
from codex_wake.a2a_scheduler import MailScheduler


class OwningClientDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.repo = self.root / 'repo'; self.repo.mkdir()
        self.private = self.root / 'client'; self.private.mkdir(mode=0o700)
        self.bus, self.operator = BusStore.configure(self.root / 'bus')
        self.bus.enroll(self.repo, self.operator, notify=True)
        self.identities = [RuntimeIdentity('fixture', x, str(self.repo)) for x in ('sender', 'recipient')]
        self.actors = []
        for identity in self.identities:
            capability, _ = self.bus.issue_actor(identity, self.repo, self.operator)
            self.actors.append(self.bus.authenticate(capability, identity, invoking_cwd=self.repo))
        Mailbox.migrate(self.bus, self.operator)
        # Transport tests pin clocks; clock continuity has separate mailbox tests.
        self.wall_clock, self.monotonic_clock = time.time(), time.monotonic()
        self.mailbox = Mailbox(self.bus, clock=lambda: self.wall_clock,
                              monotonic=lambda: self.monotonic_clock)
        self.scheduler = MailScheduler(self.mailbox, self.operator, lease_seconds=60)
        self.bus.set_paused(False, self.operator)
        self.bindings = self.private / 'bindings.json'
        self.socket_path = self.private / 'client.sock'
        self.status = 'ready'
        self.deliver_status = 'submitted'
        self.thread_id = 'recipient'
        self.deliveries = []
        self.generation = 'owned-process-generation'
        self.server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.server.bind(str(self.socket_path)); self.socket_path.chmod(0o600)
        self.server.listen(); self.server.settimeout(.1)
        self.stop = threading.Event()
        self.worker = threading.Thread(target=self.serve, daemon=True)
        self.worker.start()
        self.addCleanup(self.close)
        bind_client(self.bindings, self.socket_path, self.identities[1])
        self.dispatcher = NotificationDispatcher(self.scheduler, self.bindings)

    def close(self):
        self.stop.set(); self.worker.join(2); self.server.close()
        self.assertFalse(self.worker.is_alive())

    def serve(self):
        while not self.stop.is_set():
            try:
                connection, _ = self.server.accept()
            except socket.timeout:
                continue
            with connection:
                with connection.makefile('rb') as stream:
                    request = json.loads(stream.readline())
                identity = dict(thread_id=self.thread_id, root=str(self.repo), namespace='fixture')
                reply = dict(protocol=1, pid=os.getpid(), generation=self.generation, identity=identity)
                if request['action'] == 'probe':
                    reply.update(status=self.status, reason='busy' if self.status != 'ready' else None,
                                 idle_only_method='turn/startIfIdle')
                else:
                    self.deliveries.append(request)
                    if self.deliver_status == 'lost':
                        continue
                    reply.update(status=self.deliver_status, request_id=request['request_id'],
                                 receipt_id='actual-client-contract-turn', reason='busy')
                connection.sendall((json.dumps(reply) + '\n').encode())

    def send(self):
        return self.mailbox.send(self.actors[0], self.identities[1], body='Untrusted test body',
                                 idempotency_key='test')['message']['message_id']

    def test_actual_unix_binding_dispatches_pointer_and_keeps_consumption_separate(self):
        identifier = self.send()
        outcome = self.dispatcher.tick()
        self.assertEqual(outcome['submitted'], 1)
        self.assertEqual(self.deliveries[0]['message_id'], identifier)
        self.assertNotIn('Untrusted test body', json.dumps(self.deliveries))
        self.assertEqual(self.mailbox.show(self.actors[0], identifier)['state'],
                         dict(admission='accepted', notification='submitted', recipient='unread'))
        self.assertEqual(self.dispatcher.tick()['results'], [])
        self.assertEqual(len(self.deliveries), 1)

    def test_busy_owned_client_does_not_consume_a_send_attempt(self):
        identifier = self.send(); self.status = 'deferred'
        outcome = self.dispatcher.tick()
        self.assertEqual(outcome['results'][0]['reason'], 'busy')
        self.assertEqual(self.deliveries, [])
        with self.bus.connection() as database:
            self.assertEqual(database.execute('SELECT count(*) FROM mail_attempts').fetchone()[0], 0)
        self.assertEqual(self.mailbox.show(self.actors[0], identifier)['state']['notification'], 'deferred')

    def test_lost_response_is_uncertain_and_never_automatically_replayed(self):
        identifier = self.send(); self.deliver_status = 'lost'
        self.assertEqual(self.dispatcher.tick()['results'][0]['status'], 'uncertain')
        self.assertEqual(self.mailbox.show(self.actors[0], identifier)['state']['notification'], 'uncertain')
        self.assertEqual(self.dispatcher.tick()['results'], [])
        self.assertEqual(len(self.deliveries), 1)

    def test_bound_process_cannot_retarget_another_selected_thread(self):
        self.send(); self.thread_id = 'other-thread'
        outcome = self.dispatcher.tick()
        self.assertEqual(outcome['results'][0]['reason'], 'identity_changed')
        self.assertEqual(self.deliveries, [])

    def test_busy_race_is_explicit_unsent_not_submission(self):
        identifier = self.send(); self.deliver_status = 'unsent'
        result = self.dispatcher.tick()['results'][0]
        self.assertEqual(result['status'], 'unsent')
        self.assertEqual(self.mailbox.show(self.actors[0], identifier)['state']['notification'], 'deferred')
        with self.bus.connection() as database:
            evidence = json.loads(database.execute('SELECT evidence FROM mail_attempts').fetchone()[0])
        self.assertEqual(evidence['reason'], 'explicit_not_sent')

    def test_changed_generation_fences_a_cached_binding(self):
        binding = next(iter(load_bindings(self.bindings).values()))
        self.generation = 'new-process-binding'
        self.send()
        result = self.dispatcher.tick()['results'][0]
        self.assertEqual(result['reason'], 'offline')
        self.assertEqual(self.deliveries, [])
        self.assertNotEqual(binding.generation, self.generation)

    def test_common_receive_revocation_blocks_restarted_dispatcher_without_transport(self):
        from codex_wake.session_permissions import PermissionStore,Principal
        policy=PermissionStore(self.root/'wake')
        policy.configure({'version':1},Principal('operator','operator'),expected_revision=0)
        self.bus.bind_permissions(policy.root,self.operator)
        admitted=self.mailbox.send(self.actors[0],self.identities[1],body='request',idempotency_key='policy-restart')
        policy.configure({'version':1,'sessions':{'recipient':{'actions':{'a2a.receive':'deny'}}}},
                         Principal('operator','operator'),expected_revision=1)
        reopened=Mailbox(BusStore(self.bus.root),clock=lambda:self.wall_clock,monotonic=lambda:self.monotonic_clock)
        restarted=NotificationDispatcher(MailScheduler(reopened,self.operator,lease_seconds=60),self.bindings)
        result=restarted.tick()
        self.assertEqual(result['submitted'],0)
        self.assertEqual(self.deliveries,[])
        saved=reopened.show(self.actors[0],admitted['message']['message_id'])
        self.assertEqual(saved['idempotency_key'],'policy-restart')
        self.assertEqual(saved['expires_at'],admitted['message']['expires_at'])
        self.assertEqual(saved['state']['notification'],'pending')

    def test_permission_revoked_after_claim_is_checked_before_client_io(self):
        from codex_wake.session_permissions import PermissionStore,Principal
        from unittest.mock import patch
        policy=PermissionStore(self.root/'wake')
        policy.configure({'version':1},Principal('operator','operator'),expected_revision=0)
        self.bus.bind_permissions(policy.root,self.operator)
        sent=self.mailbox.send(self.actors[0],self.identities[1],body='request',idempotency_key='policy-race')
        claim=self.scheduler.claim
        def revoke(*args,**kwargs):
            admitted=claim(*args,**kwargs)
            policy.configure({'version':1,'mandatory':['a2a.send']},Principal('op','operator'),expected_revision=1)
            return admitted
        with patch.object(self.scheduler,'claim',side_effect=revoke):result=self.dispatcher.tick()
        self.assertEqual(result['submitted'],0)
        self.assertEqual(self.deliveries,[])
        saved=self.mailbox.show(self.actors[0],sent['message']['message_id'])
        self.assertEqual(saved['state']['notification'],'deferred')
        self.assertEqual(saved['expires_at'],sent['message']['expires_at'])
