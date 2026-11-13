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

    def test_opted_in_worker_discovers_missing_recipient_binding_before_dispatch(self):
        from unittest.mock import patch
        from dataclasses import replace
        from codex_wake.a2a_delivery import binding_dict
        original = next(iter(load_bindings(self.bindings).values()))
        # Keep one unrelated explicit binding; the intended recipient is absent.
        self.bindings.write_text(json.dumps(dict(schema_version=1,
            bindings=[binding_dict(replace(original, thread_id='unrelated',
                socket_path=str(self.private / 'unrelated.sock')))])))
        identifier = self.send()
        dispatcher = NotificationDispatcher(self.scheduler, self.bindings,
                                            discover_tmux_socket='/owned/tmux/socket')
        def bind_discovered(*args):
            data = json.loads(self.bindings.read_text())
            data['bindings'].append(binding_dict(original))
            self.bindings.write_text(json.dumps(data))
        with patch('codex_wake.a2a_tmux_delivery.bind_tmux', side_effect=bind_discovered) as bind, \
             patch('codex_wake.a2a_cli.resolve_identity', return_value=self.identities[1]):
            outcome = dispatcher.tick()
        self.assertEqual(outcome['submitted'], 1, outcome)
        self.assertEqual(self.deliveries[0]['message_id'], identifier)
        self.assertEqual(bind.call_args.args[2], self.identities[1])
        self.assertEqual(dispatcher.tick()['results'], [])

    def test_opted_in_worker_starts_without_seed_binding_file(self):
        from unittest.mock import patch
        from codex_wake.a2a_delivery import binding_dict
        original = next(iter(load_bindings(self.bindings).values()))
        self.bindings.unlink()
        self.send()
        dispatcher = NotificationDispatcher(self.scheduler, self.bindings,
                                            discover_tmux_socket='/owned/tmux/socket')
        def bind_discovered(*args):
            self.bindings.write_text(json.dumps(dict(schema_version=1, bindings=[binding_dict(original)])))
        with patch('codex_wake.a2a_tmux_delivery.bind_tmux', side_effect=bind_discovered), \
             patch('codex_wake.a2a_cli.resolve_identity', return_value=self.identities[1]):
            outcome = dispatcher.tick()
        self.assertEqual(outcome['submitted'], 1, outcome)

    def test_opted_in_worker_refreshes_replaced_tmux_client_generation(self):
        from unittest.mock import patch
        from codex_wake.a2a_delivery import binding_dict
        from codex_wake.a2a_tmux_delivery import TmuxBinding
        from codex_wake.process import boot_id_value, process_start_time_ticks
        original = next(iter(load_bindings(self.bindings).values()))
        stale = TmuxBinding(original.namespace, original.thread_id, original.root,
            '/owned/tmux/socket', os.getpid(), process_start_time_ticks(os.getpid()) + 1,
            boot_id_value(), 'old-generation')
        self.bindings.write_text(json.dumps(dict(schema_version=1, bindings=[binding_dict(stale)])))
        identifier = self.send()
        dispatcher = NotificationDispatcher(self.scheduler, self.bindings,
                                            discover_tmux_socket='/owned/tmux/socket')
        def bind_discovered(*args):
            self.bindings.write_text(json.dumps(dict(schema_version=1, bindings=[binding_dict(original)])))
        with patch('codex_wake.a2a_tmux_delivery.bind_tmux', side_effect=bind_discovered) as bind, \
             patch('codex_wake.a2a_cli.resolve_identity', return_value=self.identities[1]):
            outcome = dispatcher.tick()
        self.assertEqual(outcome['submitted'], 1, outcome)
        self.assertEqual(self.deliveries[0]['message_id'], identifier)
        bind.assert_called_once()

    def test_discovery_rejects_changed_identity_without_binding_or_delivery(self):
        from unittest.mock import patch
        from dataclasses import replace
        from codex_wake.a2a_delivery import binding_dict
        original = next(iter(load_bindings(self.bindings).values()))
        self.bindings.write_text(json.dumps(dict(schema_version=1,
            bindings=[binding_dict(replace(original, thread_id='unrelated'))])))
        self.send()
        dispatcher = NotificationDispatcher(self.scheduler, self.bindings,
                                            discover_tmux_socket='/owned/tmux/socket')
        with patch('codex_wake.a2a_tmux_delivery.bind_tmux') as bind, \
             patch('codex_wake.a2a_cli.resolve_identity', return_value=replace(self.identities[1], namespace='other')):
            outcome = dispatcher.tick()
        self.assertEqual(outcome['submitted'], 0)
        bind.assert_not_called()
        self.assertEqual(self.deliveries, [])

    def test_discovery_source_failure_defers_without_stopping_worker(self):
        from unittest.mock import patch
        from codex_wake.shared_app_server import SharedSourceError
        self.send()
        self.bindings.unlink()
        dispatcher = NotificationDispatcher(self.scheduler, self.bindings,
                                            discover_tmux_socket='/owned/tmux/socket')
        with patch('codex_wake.a2a_cli.resolve_identity', side_effect=SharedSourceError('unavailable')), \
             patch('codex_wake.a2a_tmux_delivery.bind_tmux') as bind:
            outcome = dispatcher.tick()
        self.assertEqual(outcome['submitted'], 0)
        self.assertEqual(outcome['results'][0]['reason'], 'runtime_unavailable')
        bind.assert_not_called()
        self.assertEqual(self.deliveries, [])

    def test_explicit_mode_does_not_discover_missing_bindings(self):
        from unittest.mock import patch
        from dataclasses import replace
        from codex_wake.a2a_delivery import binding_dict
        original = next(iter(load_bindings(self.bindings).values()))
        self.bindings.write_text(json.dumps(dict(schema_version=1,
            bindings=[binding_dict(replace(original, thread_id='unrelated'))])))
        self.send()
        with patch('codex_wake.a2a_tmux_delivery.bind_tmux') as bind:
            outcome = self.dispatcher.tick()
        self.assertEqual(outcome['results'][0]['reason'], 'capability_unavailable')
        bind.assert_not_called()

    def test_wrapped_footer_survives_every_native_pre_submit_check(self):
        from unittest.mock import patch
        from types import SimpleNamespace
        from codex_wake.a2a_delivery import binding_dict
        from codex_wake.a2a_tmux_delivery import TmuxBinding
        from codex_wake.process import boot_id_value, process_start_time_ticks
        binding = TmuxBinding('fixture', 'recipient', str(self.repo), '/owned/tmux/socket',
            os.getpid(), process_start_time_ticks(os.getpid()), boot_id_value(), 'native-generation')
        self.bindings.write_text(json.dumps(dict(schema_version=1, bindings=[binding_dict(binding)])))
        identifier = self.send()
        thread = dict(name='Wake P230 recipient', status=dict(type='idle'), canAcceptDirectInput=True)
        screen = ('› Ask Codex to do anything\nGPT-6.1-Sol low · /owned/repo · Wake P230\n'
                  'recipient\n← for agents · ? for shortcuts        ⚠ 1 warning · f2 to view\n')
        queued = SimpleNamespace(returncode=0, stdout='Queued message 00000000-0000-7000-8000-000000000099 for thread recipient.\n')
        with patch.object(TmuxBinding, 'locate', return_value=(thread, dict(pane_id='%1'))), \
             patch('codex_wake.a2a_tmux_delivery.SubprocessTmuxRunner') as runner, \
             patch('codex_wake.a2a_tmux_delivery.notification_expired', return_value=False), \
             patch('codex_wake.app_server.resolve_codex_cmd', return_value='/qualified/codex'), \
             patch('codex_wake.a2a_tmux_delivery.locate_shared_endpoint', return_value='unix:///owned/server'), \
             patch('codex_wake.a2a_tmux_delivery.subprocess.run', return_value=queued) as queue:
            runner.return_value.capture_pane.return_value = screen
            outcome = self.dispatcher.tick()
        self.assertEqual(outcome['submitted'], 1, outcome)
        queue.assert_called_once()
        self.assertEqual(self.mailbox.show(self.actors[0], identifier)['state']['notification'], 'submitted')

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
