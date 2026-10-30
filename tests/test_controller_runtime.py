import tempfile
import unittest
from pathlib import Path
from codex_wake.controller_auth import Actor, AuthError
from codex_wake.managed_inventory import InventoryError


class RuntimeTests(unittest.TestCase):
    def actor(self):
        return Actor('caller', 'service', 'client', 'grant', 'https://wake.test', 'https://wake.test/controller', frozenset({'observe', 'control'}), [{'host': 'fixture', 'environment': 'linux', 'runtime': 'codex', 'namespace': 'account:alice', 'conversation_id': 'recipient', 'process': {'pid': 1}}], 1000)

    def test_intent_precedes_effect_and_uncertain_dispatch_is_never_replayed(self):
        from codex_wake.controller_runtime import ControllerRuntime
        with tempfile.TemporaryDirectory() as directory:
            runtime = ControllerRuntime(Path(directory), now=lambda: 100)
            actor = self.actor()
            meta = dict(operation_id='operation-one', idempotency_key='intent-one', correlation_id='correlation-one', binding='opaque-binding', target=actor.targets[0])
            arguments = dict(expected_target=actor.targets[0], value='original', _request=meta)
            effect = Path(directory) / 'effect'
            def dispatch(operation, args):
                self.assertNotIn('_request', args)
                admitted = runtime.operation(actor, 'operations.result', {'operation_id': 'operation-one'}, authorize=lambda: actor)
                self.assertEqual(admitted['result']['operation']['execution'], 'unknown')
                effect.write_text('one effect')
                raise RuntimeError('synthetic response lost after effect')
            first = runtime.execute(actor, 'fixture.effect', arguments, authorize=lambda: actor, dispatch=dispatch)
            self.assertEqual(first['result']['operation']['execution'], 'unknown')
            self.assertEqual(first['result']['operation']['delivery'], 'uncertain')
            def forbidden(*args): self.fail('uncertain dispatch replayed')
            again = ControllerRuntime(Path(directory), now=lambda: 100).execute(actor, 'fixture.effect', arguments, authorize=lambda: actor, dispatch=forbidden)
            self.assertEqual(first, again)
            with self.assertRaises(InventoryError): runtime.execute(actor, 'fixture.effect', dict(arguments, value='changed'), authorize=lambda: actor, dispatch=forbidden)
            with self.assertRaises(AuthError): runtime.operation(Actor('other', *tuple(actor.__dict__.values())[1:]), 'operations.result', {'operation_id': 'operation-one'}, authorize=lambda: actor)
            self.assertEqual(effect.read_text(), 'one effect')

    def fixture(self, directory, *, fault=None, observed_at=None, sender_id="sender"):
        import json,time
        from codex_wake.a2a_bus import BusStore
        from codex_wake.a2a_identity import RuntimeIdentity
        from codex_wake.a2a_mailbox import Mailbox
        from codex_wake.managed_inventory import ManagedInventory, Observation
        from codex_wake.controller_mailbox import ControllerMailbox
        from codex_wake.controller_runtime import ControllerRuntime
        root = Path(directory) / 'wake'
        work = Path(directory) / 'work'; work.mkdir()
        bus, operator = BusStore.configure(Path(directory) / 'bus')
        bus.enroll(work, operator)
        natives, actors, caps = [], [], []
        for who, thread_id in (('sender', sender_id), ('recipient', 'recipient')):
            native = RuntimeIdentity('account:' + who, thread_id, str(work))
            cap, _ = bus.issue_actor(native, work, operator)
            natives.append(native); caps.append(cap)
            actors.append(bus.authenticate(cap, native, invoking_cwd=work))
        Mailbox.migrate(bus, operator)
        observed_at = time.time() if observed_at is None else observed_at
        inventory = ManagedInventory(root, now=lambda:observed_at)
        inventory.enroll(Observation('codex', 'account:recipient', 'recipient', str(work), 'ready', observed_at, 'native_metadata', {'pid': 123, 'start_ticks': 42, 'boot_id': 'fixture'}, [], {}), operator=True)
        from codex_wake.controller_operations import ControllerOperations
        target = ControllerOperations(inventory, host='fixture', environment='linux').execute('inventory.resolve', {'selector': 'recipient'})['result']['resource']['target']
        actor = Actor('caller', 'service', 'client', 'grant', 'https://wake.test', 'https://wake.test/controller', frozenset({'control', 'observe'}), [{k:v for k,v in target.items() if k != 'process'}], time.time()+600)
        config = dict(version=1, host='fixture', environment='linux', bindings={'native-sender': dict(subject='caller', client_id='client', bus_root=str(bus.root), capability=str(caps[0]), identity=natives[0].__dict__)}, recipients=[dict(target=target, identity=natives[1].__dict__)])
        path = root / 'controller-messaging.json'; path.write_text(json.dumps(config)); path.chmod(0o600)
        adapter = ControllerMailbox(root, mailbox_factory=lambda bus: Mailbox(bus, fault=fault))
        runtime = ControllerRuntime(root, adapter=adapter)
        args = dict(_request=dict(operation_id='mail-operation', idempotency_key='mail-intent', correlation_id='mail-correlation', binding='opaque-caller-context', target=target), expected_target=target, sender_binding='native-sender', body='Synthetic question', delivery='inbox', queue=True, response_requested=False)
        return runtime, actor, args, Mailbox(bus), actors

    def test_timeout_is_not_cancellation_and_only_real_correlated_reply_is_answer(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime, actor, args, mailbox, natives = self.fixture(directory)
            sent = runtime.operation(actor, 'operations.send', args, authorize=lambda: actor)
            operation = sent['result']['operation']; message_id = operation['result']['message_id']
            mailbox.ack(natives[1], message_id, outcome='accepted')
            mailbox.ack(natives[1], message_id, outcome='completed')
            waited = runtime.operation(actor, 'operations.wait', {'operation_id': 'mail-operation', 'timeout': 0}, authorize=lambda: actor)
            self.assertEqual(waited['result']['wait'], {'status': 'timeout', 'ends_work': False})
            self.assertNotIn('answer', waited['result']['operation'])
            mailbox.reply(natives[1], message_id, body='Real progress', idempotency_key='progress', kind='notice', delivery='inbox')
            first = runtime.operation(actor, 'operations.stream', {'operation_id':'mail-operation'}, authorize=lambda: actor)
            self.assertTrue(any(e.get('text')=='Real progress' for e in first['result']['events']))
            mailbox.reply(natives[1], message_id, body='Actual final answer', idempotency_key='final', kind='result', delivery='inbox')
            second = runtime.operation(actor, 'operations.stream', {'operation_id':'mail-operation', 'cursor':first['result']['next_cursor']}, authorize=lambda: actor)
            self.assertEqual(second['result']['operation']['answer']['text'], 'Actual final answer')
            self.assertEqual(second['result']['operation']['answer']['correlation_id'], 'mail-correlation')
            self.assertFalse(any(e.get('text')=='Real progress' for e in second['result']['events']))
            self.assertEqual(mailbox.replies(natives[0], message_id)[-1]['recipient']['thread_id'], 'sender')
            restarted = type(runtime)(runtime.root, adapter=runtime.adapter)
            retained = restarted.operation(actor, 'operations.result', {'operation_id':'mail-operation'}, authorize=lambda: actor)
            self.assertEqual(retained['result']['operation']['answer']['text'], 'Actual final answer')

    def test_uncertain_mailbox_commit_reconciles_original_message_without_resend(self):
        def fault(point):
            if point == 'after_commit': raise RuntimeError('synthetic caller loss')
        with tempfile.TemporaryDirectory() as directory:
            runtime, actor, args, mailbox, natives = self.fixture(directory, fault=fault)
            uncertain = runtime.operation(actor, 'operations.send', args, authorize=lambda: actor)
            self.assertEqual(uncertain['result']['operation']['execution'], 'unknown')
            runtime.adapter.mailbox_factory = type(mailbox)
            reconciled = runtime.operation(actor, 'operations.result', {'operation_id':'mail-operation'}, authorize=lambda: actor)
            self.assertEqual(reconciled['result']['operation']['execution'], 'queued')
            self.assertEqual(len(mailbox.list(natives[0], outbox=True)['messages']), 1)
            repeated = runtime.operation(actor, 'operations.send', args, authorize=lambda: actor)
            self.assertEqual(repeated['result']['operation']['result']['message_id'], reconciled['result']['operation']['result']['message_id'])
            self.assertEqual(len(mailbox.list(natives[0], outbox=True)['messages']), 1)

    def test_background_owner_survives_submitter_and_returns_actual_command_stdout(self):
        import json,sys,time
        from codex_wake.background_jobs import BackgroundJobs
        from codex_wake.session_permissions import Principal, PermissionStore
        from codex_wake.task_briefs import TaskBriefStore, BriefAuthority
        from codex_wake.controller_job_adapter import ControllerEffects
        with tempfile.TemporaryDirectory() as directory:
            runtime, actor, args, mailbox, natives = self.fixture(directory)
            operator = Principal('operator', 'operator')
            PermissionStore(runtime.root).configure({'version':1,'global':{'actions':{'job.launch':'allow','job.cancel':'allow'}}}, operator, expected_revision=0)
            authority = BriefAuthority('operator', 'operator'); briefs = TaskBriefStore(runtime.root)
            work = Path(directory) / 'work'
            briefs.propose('fixture-task', dict(objective='Synthetic bounded command',phase='test', non_goals=['No providers'],acceptance=['Actual stdout'],context=[],workspace=str(work),allocation_ref='fixture',permission_ref='fixture'), authority=authority)
            briefs.approve('fixture-task', 1, authority=authority); briefs.admit('fixture-task','fixture-assignment',authority=authority)
            jobs = BackgroundJobs(runtime.root)
            profile = jobs.approve_command('synthetic', [sys.executable,'-c',"import time;time.sleep(.2);print('Actual supervised answer')"], work,
                principal=operator,task_pin=briefs.assignment_pin('fixture-task','fixture-assignment'),owner='native-worker',max_seconds=3,max_log_bytes=1024)
            target = dict(host='fixture',environment='linux',namespace='jobs',conversation_id='synthetic',configuration_revision=profile['sha256'])
            actor = Actor(actor.subject, actor.principal_kind, actor.client_id, actor.grant_id, actor.issuer, actor.resource, actor.scopes, [target], actor.expires_at)
            config_path = runtime.root / 'controller-messaging.json'; config = json.loads(config_path.read_text())
            config['job_bindings'] = {'native-job':dict(subject=actor.subject,client_id=actor.client_id,native_subject='native-worker',tasks=['fixture-task'],profile='synthetic',target=target)}
            config_path.write_text(json.dumps(config))
            runtime.adapter = ControllerEffects(runtime.root)
            request = dict(operation_id='job-operation',idempotency_key='job-intent',correlation_id='job-correlation',binding='opaque-job-binding',target=target)
            sent = runtime.operation(actor,'operations.send',dict(_request=request,expected_target=target,sender_binding='native-job',backend='job',job_profile='synthetic',response_requested=False),authorize=lambda:actor)
            self.assertEqual(sent['result']['operation']['result']['kind'],'background_job')
            waited = runtime.operation(actor,'operations.wait',dict(operation_id='job-operation',timeout=5),authorize=lambda:actor)
            self.assertEqual(waited['result']['operation']['answer']['text'],'Actual supervised answer\n')
            self.assertEqual(waited['result']['wait']['status'],'completed')

    def test_explicit_successor_rebind_is_not_lost_when_owner_finishes_concurrently(self):
        import threading
        from dataclasses import replace
        from codex_wake.controller_runtime import ControllerRuntime, identity
        with tempfile.TemporaryDirectory() as directory:
            runtime = ControllerRuntime(Path(directory), now=lambda:100)
            actor = self.actor(); successor = replace(actor, grant_id='successor-grant')
            started, finish = threading.Event(), threading.Event()
            args = dict(expected_target=actor.targets[0],_request=dict(operation_id='concurrent',idempotency_key='concurrent',correlation_id='concurrent',binding='original-opaque',target=actor.targets[0]))
            def dispatch(*args):
                started.set(); self.assertTrue(finish.wait(3)); return {'actual_result':'retained'}
            thread = threading.Thread(target=lambda:runtime.execute(actor,'fixture.effect',args,authorize=lambda:actor,dispatch=dispatch))
            thread.start(); self.assertTrue(started.wait(3))
            runtime.operation(actor,'operations.rebind',dict(operation_id='concurrent',successor=identity(successor),binding='successor-opaque'),authorize=lambda:actor)
            finish.set(); thread.join(3); self.assertFalse(thread.is_alive())
            result = runtime.operation(successor,'operations.result',{'operation_id':'concurrent'},authorize=lambda:successor)
            self.assertEqual(result['result']['operation']['binding'],'successor-opaque')
            self.assertEqual(result['result']['operation']['result'],{'actual_result':'retained'})

    def test_queue_cancel_consumption_uncertainty_and_explicit_successor_rotation(self):
        from dataclasses import replace
        from codex_wake.controller_runtime import identity
        with tempfile.TemporaryDirectory() as directory:
            runtime, actor, args, mailbox, natives = self.fixture(directory)
            rejected = dict(args, queue=False)
            with self.assertRaises(InventoryError): runtime.operation(actor,'operations.send',rejected,authorize=lambda:actor)
            with self.assertRaises(InventoryError): runtime.operation(replace(actor,client_id='unmapped-client'),'operations.send',args,authorize=lambda:replace(actor,client_id='unmapped-client'))
            self.assertEqual(mailbox.list(natives[0],outbox=True)['messages'],[])
            sent = runtime.operation(actor,'operations.send',args,authorize=lambda:actor)
            message = sent['result']['operation']['result']['message_id']
            cancelled = runtime.operation(actor,'operations.cancel',{'operation_id':'mail-operation'},authorize=lambda:actor)
            self.assertEqual(cancelled['result']['operation']['cancellation'],'confirmed')
            self.assertEqual(mailbox.show(natives[0],message)['state']['admission'],'cancelled')
        with tempfile.TemporaryDirectory() as directory:
            runtime, actor, args, mailbox, natives = self.fixture(directory)
            message = runtime.operation(actor,'operations.send',args,authorize=lambda:actor)['result']['operation']['result']['message_id']
            mailbox.read(natives[1],message); mailbox.ack(natives[1],message,outcome='accepted')
            uncertain = runtime.operation(actor,'operations.cancel',{'operation_id':'mail-operation'},authorize=lambda:actor)
            self.assertEqual(uncertain['result']['operation']['cancellation'],'uncertain')
            mailbox.reply(natives[1],message,body='Late answer after consumption',idempotency_key='late',kind='result',delivery='inbox')
            rotated = replace(actor,expires_at=actor.expires_at+300)
            retained = runtime.operation(rotated,'operations.result',{'operation_id':'mail-operation'},authorize=lambda:rotated)
            self.assertEqual(retained['result']['operation']['answer']['text'],'Late answer after consumption')
            successor = replace(rotated,grant_id='successor')
            with self.assertRaises(AuthError): runtime.operation(successor,'operations.result',{'operation_id':'mail-operation'},authorize=lambda:successor)
            with self.assertRaises(AuthError): runtime.operation(actor,'operations.rebind',dict(operation_id='mail-operation',successor=identity(replace(successor,client_id='other')),binding='spoofed-native'),authorize=lambda:actor)
            runtime.operation(actor,'operations.rebind',dict(operation_id='mail-operation',successor=identity(successor),binding='explicit-successor-correlation'),authorize=lambda:actor)
            final = runtime.operation(successor,'operations.result',{'operation_id':'mail-operation'},authorize=lambda:successor)['result']['operation']
            self.assertEqual(final['binding'],'explicit-successor-correlation')
            self.assertEqual(final['original_binding'],'opaque-caller-context')
            self.assertEqual(final['answer']['text'],'Late answer after consumption')
            self.assertEqual(mailbox.replies(natives[0],message)[0]['recipient']['thread_id'],'sender')

    def test_explicit_queue_reaches_retained_stale_identity_but_never_reenables_suppression(self):
        import time
        from codex_wake.managed_inventory import ManagedInventory
        with tempfile.TemporaryDirectory() as directory:
            runtime, actor, args, mailbox, natives = self.fixture(directory, observed_at=time.time()-60)
            with self.assertRaises(InventoryError): runtime.operation(actor,'operations.send',dict(args,delivery='notify',queue=False),authorize=lambda:actor)
            queued = runtime.operation(actor,'operations.send',args,authorize=lambda:actor)['result']['operation']
            message = mailbox.show(natives[0],queued['result']['message_id'])
            self.assertEqual(message['state']['notification'],'suppressed')
            self.assertEqual(message['state']['recipient'],'unread')
            self.assertEqual(message['selector_observation']['target'],args['expected_target'])
            inventory=ManagedInventory(runtime.root)
            identifier=inventory.inspect()['agents'][0]['managed_agent_id']
            inventory.set_enrollment(identifier,enabled=False)
            changed=dict(args,_request=dict(args['_request'],operation_id='suppressed-op',idempotency_key='suppressed-intent'))
            with self.assertRaises(InventoryError): runtime.operation(actor,'operations.send',changed,authorize=lambda:actor)
            self.assertEqual(inventory.inspect(identifier)['agent']['enrollment'],'suppressed')
            self.assertEqual(len(mailbox.list(natives[0],outbox=True)['messages']),1)

    def test_native_mcp_cannot_choose_other_sender_or_claim_identity_in_request_binding(self):
        import json
        from types import SimpleNamespace
        from codex_wake.operation_commands import mcp_call
        with tempfile.TemporaryDirectory() as directory:
            sender='11111111-1111-4111-8111-111111111111'
            runtime, actor, args, mailbox, natives = self.fixture(directory, sender_id=sender)
            config_path=runtime.root/'controller-messaging.json';config=json.loads(config_path.read_text())
            config['local_caller']=dict(subject=actor.subject,client_id=actor.client_id,grant_id=actor.grant_id,issuer=actor.issuer,resource=actor.resource,scopes=list(actor.scopes),targets=actor.targets,expires_at=actor.expires_at)
            config_path.write_text(json.dumps(config))
            context=dict(threadId=sender,sessionId=sender,callId='native-call',**{'x-codex-turn-metadata':dict(thread_id=sender,session_id=sender,turn_id='native-turn')})
            runner=SimpleNamespace(wake_root=runtime.root)
            with self.assertRaises(InventoryError): mcp_call(runner,'send',args,None)
            other='22222222-2222-4222-8222-222222222222'
            wrong=dict(context,threadId=other,sessionId=other)
            wrong['x-codex-turn-metadata']=dict(thread_id=other,session_id=other,turn_id='wrong-turn')
            spoof=dict(args,_request=dict(args['_request'],binding=sender))
            with self.assertRaises(InventoryError): mcp_call(runner,'send',spoof,wrong)
            self.assertEqual(mailbox.list(natives[0],outbox=True)['messages'],[])
            accepted=mcp_call(runner,'send',args,context)
            self.assertEqual(accepted['result']['operation']['execution'],'queued')
            message=mailbox.show(natives[0],accepted['result']['operation']['result']['message_id'])
            self.assertEqual(message['sender']['thread_id'],sender)
