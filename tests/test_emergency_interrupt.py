import json
import hashlib
from types import SimpleNamespace
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from codex_wake.emergency_interrupt import interrupt_owned


class EmergencyInterruptTests(unittest.TestCase):
    def scenario(self, *, lost=False, foreign=False, wrong_payload=False):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        (root/'lifecycle').mkdir()
        (root/'lifecycle/spawn.json').write_text(json.dumps(dict(thread_id='thread', submission_id='submission',
            intent=dict(operation='spawn',task='task',launch=dict(app_server='unix:///fixture',codex_path='/fixture/codex')))))
        state = dict(status='inProgress')
        calls=[]
        def provider(endpoint, command, method, params, timeout):
            calls.append((method,params))
            if method=='turn/interrupt':
                if lost:raise TimeoutError()
                state['status']='interrupted'
                return {}
            turn=dict(id='turn',status=state['status'],items=[dict(type='userMessage',clientId='submission',
                content=[dict(type='text',text='different' if wrong_payload else 'task')])])
            turns=[turn]
            if foreign:turns.append(dict(id='foreign',status='inProgress',items=[]))
            return dict(thread=dict(id='thread',turns=turns))
        return root,provider,calls,state

    def test_interrupt_requires_exact_identity_and_verified_terminal_readback(self):
        root,provider,calls,state=self.scenario()
        with patch('codex_wake.emergency_interrupt.native_request',side_effect=provider):
            result=interrupt_owned(root)
        self.assertEqual(result[0]['state'],'interrupted')
        self.assertEqual([p for m,p in calls if m=='turn/interrupt'],[dict(threadId='thread',turnId='turn')])

    def test_lost_response_is_not_retried_and_later_terminal_state_reconciles(self):
        root,provider,calls,state=self.scenario(lost=True)
        with patch('codex_wake.emergency_interrupt.native_request',side_effect=provider):
            self.assertEqual(interrupt_owned(root)[0]['state'],'uncertain')
            self.assertEqual(interrupt_owned(root)[0]['state'],'uncertain')
            state['status']='interrupted'
            self.assertEqual(interrupt_owned(root)[0]['state'],'settled')
        self.assertEqual(sum(m=='turn/interrupt' for m,p in calls),1)

    def test_foreign_running_turn_is_preserved(self):
        root,provider,calls,state=self.scenario(foreign=True)
        with patch('codex_wake.emergency_interrupt.native_request',side_effect=provider):
            self.assertEqual(interrupt_owned(root)[0]['state'],'held')
        self.assertFalse(any(m=='turn/interrupt' for m,p in calls))

    def test_same_submission_with_changed_payload_does_not_authorize_interrupt(self):
        root,provider,calls,state=self.scenario(wrong_payload=True)
        with patch('codex_wake.emergency_interrupt.native_request',side_effect=provider):
            self.assertEqual(interrupt_owned(root)[0]['state'],'held')
        self.assertFalse(any(m=='turn/interrupt' for m,p in calls))

    def test_handoff_is_delegated_without_native_effect(self):
        root,provider,calls,state=self.scenario()
        (root/'lifecycle/spawn.json').write_text(json.dumps(dict(intent=dict(operation='handoff'))))
        with patch('codex_wake.emergency_interrupt.native_request',side_effect=provider):
            self.assertEqual(interrupt_owned(root)[0]['state'],'monitor_required')
        self.assertEqual(calls,[])

    def test_ordinary_native_wake_correlates_actual_client_message_identity(self):
        root,provider,calls,state=self.scenario()
        (root/'lifecycle/spawn.json').unlink()
        record=dict(id='wake_one',prompt='task',status='submitted',
            target=dict(transport='native',endpoint='unix:///fixture',codex_cmd='/fixture/codex',thread_id='thread'),
            native_delivery=dict(submission_id='durable-prompt-marker',
                prompt_sha256=hashlib.sha256(b'task').hexdigest()))
        with patch('codex_wake.records.iter_records',return_value=[SimpleNamespace(record=record)]), \
             patch('codex_wake.native_delivery.native_prompt',return_value='task'), \
             patch('codex_wake.native_delivery.native_evidence',return_value=(dict(source='native_turn',client_message_id='submission'),None)), \
             patch('codex_wake.emergency_interrupt.native_request',side_effect=provider):
            self.assertEqual(interrupt_owned(root)[0]['state'],'interrupted')

    def test_submitted_unsupported_transport_is_explicit(self):
        root,provider,calls,state=self.scenario()
        (root/'lifecycle/spawn.json').unlink()
        with patch('codex_wake.records.iter_records',return_value=[SimpleNamespace(record=dict(id='old',status='submitted'))]), \
             patch('codex_wake.emergency_interrupt.native_request',side_effect=provider):
            self.assertEqual(interrupt_owned(root)[0]['state'],'unsupported')
        self.assertEqual(calls,[])

    def test_permissive_journal_refuses_before_native_observation(self):
        root,provider,calls,state=self.scenario()
        (root/'emergency-interrupt').mkdir(mode=0o755)
        (root/'emergency-interrupt').chmod(0o755)
        with patch('codex_wake.emergency_interrupt.native_request',side_effect=provider):
            self.assertEqual(interrupt_owned(root)[0]['state'],'held')
        self.assertEqual(calls,[])

    def test_symlink_journal_refuses_before_native_observation(self):
        root,provider,calls,state=self.scenario()
        (root/'other').mkdir()
        (root/'emergency-interrupt').symlink_to(root/'other',target_is_directory=True)
        with patch('codex_wake.emergency_interrupt.native_request',side_effect=provider):
            self.assertEqual(interrupt_owned(root)[0]['state'],'held')
        self.assertEqual(calls,[])

    def test_ordinary_queued_only_assignment_holds_without_interrupt(self):
        root,provider,calls,state=self.scenario()
        (root/'lifecycle/spawn.json').unlink()
        record=dict(id='wake_one',prompt='task',status='submitted',
            target=dict(transport='native',endpoint='unix:///fixture',codex_cmd='/fixture/codex',thread_id='thread'),
            native_delivery=dict(submission_id='marker',prompt_sha256=hashlib.sha256(b'task').hexdigest()))
        with patch('codex_wake.records.iter_records',return_value=[SimpleNamespace(record=record)]), \
             patch('codex_wake.native_delivery.native_prompt',return_value='task'), \
             patch('codex_wake.native_delivery.native_evidence',return_value=(dict(source='native_queue',client_message_id='submission'),None)), \
             patch('codex_wake.emergency_interrupt.native_request',side_effect=provider):
            self.assertEqual(interrupt_owned(root)[0]['state'],'held')
        self.assertEqual(calls,[])

    def test_symlink_actor_lock_is_held_without_native_effect(self):
        root,provider,calls,state=self.scenario()
        journal=root/'emergency-interrupt';journal.mkdir(mode=0o700)
        other=root/'other';other.write_text('preserved')
        key=hashlib.sha256(str(root/'lifecycle/spawn.json').encode()).hexdigest()
        (journal/(key+'.lock')).symlink_to(other)
        with patch('codex_wake.emergency_interrupt.native_request',side_effect=provider):
            self.assertEqual(interrupt_owned(root)[0]['state'],'held')
        self.assertEqual(other.read_text(),'preserved')
        self.assertEqual(calls,[])

    def test_daemon_pause_preserves_running_handoff_but_explicit_interrupt_stops_owned_turn(self):
        self.handoff_control_scenario(False)

    def test_explicit_interrupt_does_not_take_over_unavailable_handoff_owner(self):
        self.handoff_control_scenario(True)

    def test_explicit_interrupt_preserves_live_foreign_handoff_owner(self):
        self.handoff_control_scenario('live')

    def handoff_control_scenario(self, foreign_owner):
        import os
        from codex_wake.daemon import poll_once
        from codex_wake.process import process_identity
        from codex_wake.wake_control import change_control, read_control
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);directory=root/'lifecycle';directory.mkdir(mode=0o700)
            source=dict(threadId='source',objective='fixture',tokenBudget=100,tokensUsed=0,timeUsedSeconds=0,createdAt=1,status='paused')
            target=dict(source,threadId='target',status='active')
            goals={'source':source,'target':target};calls=[];running={'status':'inProgress'}
            # An unavailable owner generation must not be adopted by an emergency caller.
            fence=dict(pid=99999999 if foreign_owner else os.getpid(),identity=process_identity(os.getpid()))
            receipt=dict(intent=dict(operation='handoff',launch=dict(app_server='unix:///fixture',codex_path='/fixture/codex',timeout=1),
                continuation=dict(activation=dict(deadline_margin_seconds=10))),state='active',thread_id='source',successor_thread_id='target',
                fingerprint='assignment',source_goal=dict(source),successor_goal=dict(target),deadline_fence=fence,continuation_deadline=2000)
            path=directory/'handoff.json';path.write_text(json.dumps(receipt))
            owner_path=directory/('owner-'+hashlib.sha256(b'source').hexdigest()+'.json')
            owner_path.write_text(json.dumps(dict(intent_fingerprint='assignment',source_thread_id='source',successor_thread_id='target',state='active')))
            def request(endpoint, command, method, params, timeout):
                calls.append((method,params))
                if method=='thread/goal/get':return dict(goal=dict(goals[params['threadId']]))
                if method=='thread/goal/set':
                    goals[params['threadId']]['status']=params['status']
                    return dict(goal=dict(goals[params['threadId']]))
                if method=='turn/interrupt':
                    running['status']='interrupted';return {}
                if method=='thread/read':
                    return dict(thread=dict(id='target',turns=[dict(id='owned-turn',status=running['status'],items=[])]))
                raise AssertionError(method)
            with patch('codex_wake.agent_handoff.native_request',side_effect=request), \
                 patch('codex_wake.agent_handoff.resolve_codex_cmd',return_value='/fixture/codex'), \
                 patch('codex_wake.native_clock.snapshot',return_value=dict(utc=dict(lower=1000,upper=1001))), \
                 patch('codex_wake.process.process_exists',return_value=foreign_owner == 'live'), \
                 patch('codex_wake.process.process_identity',return_value=fence['identity']):
                change_control(root,'pause')
                # Keep original owner's lease for the second call even when testing unavailable generation.
                original=path.read_text()
                poll_once(root,dispatch=False,lifecycle_supervision=dict(interval=1))
                self.assertEqual(goals['target']['status'],'active')
                self.assertFalse(any(m in ('thread/goal/set','turn/interrupt') for m,p in calls))
                if foreign_owner:path.write_text(original)
                change_control(root,'interrupt')
                poll_once(root,dispatch=False,lifecycle_supervision=dict(interval=1))
            if foreign_owner:
                self.assertEqual(goals['target']['status'],'active')
                self.assertFalse(any(m in ('thread/goal/set','turn/interrupt') for m,p in calls))
                self.assertTrue(read_control(root)['interrupt_requested'])
            else:
                self.assertEqual(goals['target']['status'],'paused')
                self.assertEqual([p for m,p in calls if m=='turn/interrupt'],[dict(threadId='target',turnId='owned-turn')])
                self.assertEqual(json.loads(path.read_text())['reason'],'emergency_interrupt')
            self.assertEqual(goals['source']['status'],'paused')

    def test_fulfilled_handoff_interrupt_reconciles_only_exact_stopped_owner(self):
        root,provider,calls,state=self.scenario()
        path=root/'lifecycle/spawn.json'
        receipt=dict(intent=dict(operation='handoff'),fingerprint='assignment',thread_id='source',successor_thread_id='target',
            state='blocked',continuation_stop_reason='emergency_interrupt',
            successor_goal=dict(threadId='target',objective='fixture',tokenBudget=100,createdAt=1,status='paused'))
        path.write_text(json.dumps(receipt))
        owner=root/'lifecycle'/('owner-'+hashlib.sha256(b'source').hexdigest()+'.json')
        owner.write_text(json.dumps(dict(intent_fingerprint='assignment',source_thread_id='source',successor_thread_id='target',state='stopped')))
        with patch('codex_wake.emergency_interrupt.native_request',side_effect=provider):
            self.assertEqual(interrupt_owned(root)[0]['state'],'settled')
            receipt['uncertain_effect']='turn/interrupt';path.write_text(json.dumps(receipt))
            self.assertEqual(interrupt_owned(root)[0]['state'],'monitor_required')
            receipt.pop('uncertain_effect');receipt['fingerprint']='different';path.write_text(json.dumps(receipt))
            self.assertEqual(interrupt_owned(root)[0]['state'],'monitor_required')
        self.assertEqual(calls,[])
