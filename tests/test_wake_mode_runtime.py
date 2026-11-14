"""Mode routing at the native delivery boundary; no provider or live TUI effects."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
from codex_wake.codex_runtime import CodexRuntimeAdapter
from codex_wake.runtime_delivery import RuntimeReconciliation, RuntimeSubmission
from codex_wake.wake_mode_runtime import ModeRuntimeAdapter

THREAD = '11111111-1111-4111-8111-111111111111'
TARGET = dict(transport='native', thread_id=THREAD, endpoint='unix:///private/test.sock', codex_cmd='/verified/codex', session_mode='background')


def inventory(live=False, complete=True):
    return dict(complete=complete, sessions=[dict(thread_id=THREAD, binding_status='metadata_matched' if live else 'unbound', attachments=[dict(client_pid=1, client_start_time_ticks=1)] if live else [])])


class BackgroundMode(unittest.TestCase):
    def adapter(self, root, states):
        self.request = Mock(return_value={'thread': {'id': THREAD}})
        self.run = Mock()
        base = CodexRuntimeAdapter(read_thread=Mock(side_effect=[dict(id=THREAD, status={'type': s}) for s in states]), request=self.request, run=self.run, project_failure=Mock())
        return ModeRuntimeAdapter(root, base)

    def test_missing_tui_resumes_only_the_saved_conversation(self):
        with tempfile.TemporaryDirectory() as d, patch('codex_wake.sessions.observe', return_value=inventory()):
            adapter = self.adapter(Path(d), ['notLoaded', 'idle'])
            observed = adapter.observe(adapter.resolve(TARGET))
            self.assertEqual(observed.state, 'ready')
            self.assertTrue(observed.resumed)
            self.assertEqual(self.request.call_args.args[2:4], ('thread/resume', {'threadId': THREAD}))
            self.assertEqual(observed.capabilities['wake.background'].state, 'supported')

    def test_live_tui_is_reused_without_background_resume(self):
        with tempfile.TemporaryDirectory() as d, patch('codex_wake.sessions.observe', return_value=inventory(live=True)):
            adapter = self.adapter(Path(d), ['idle'])
            observed = adapter.observe(adapter.resolve(TARGET))
            self.assertEqual(observed.state, 'ready')
            self.assertEqual(observed.capabilities['active_tab'].state, 'supported')
            self.request.assert_not_called()

    def test_incomplete_inventory_never_starts_background_work(self):
        with tempfile.TemporaryDirectory() as d, patch('codex_wake.sessions.observe', return_value=inventory(complete=False)):
            adapter = self.adapter(Path(d), [])
            observed = adapter.observe(adapter.resolve(TARGET))
            self.assertEqual(observed.state, 'unavailable')
            self.assertEqual(observed.reason, 'recipient_ownership_unknown')
            self.request.assert_not_called()
            self.run.assert_not_called()

    def test_opening_a_tui_after_background_observation_does_not_submit_second_copy(self):
        with tempfile.TemporaryDirectory() as d, patch('codex_wake.sessions.observe', side_effect=[inventory(), inventory(live=True)]):
            adapter = self.adapter(Path(d), ['idle'])
            recipient = adapter.resolve(TARGET)
            self.assertEqual(adapter.observe(recipient).state, 'ready')
            result = adapter.submit(recipient, 'check')
            self.assertEqual(result.state, 'not_sent')
            self.assertTrue(result.pre_io)
            self.run.assert_not_called()

class ConversationAdmission(unittest.TestCase):
    def test_native_dispatch_serializes_checks_until_prior_turn_has_terminal_evidence(self):
        import contextlib
        import io
        import json
        import sys
        from codex_wake.cli import run
        from codex_wake.daemon import poll_once
        from codex_wake.injector import dispatch_firing_record
        from codex_wake.records import all_records
        from codex_wake.runtime_delivery import RuntimeObservation, RuntimeRecipient
        boundary = Mock()
        boundary.resolve.side_effect = lambda target: RuntimeRecipient('codex', target['thread_id'], target)
        boundary.observe.return_value = RuntimeObservation('ready', 'idle', {})
        boundary.submit.return_value = RuntimeSubmission('accepted', receipt_id='22222222-2222-4222-8222-222222222222', evidence_kind='native_queue_acceptance')
        boundary.reconcile.return_value = RuntimeReconciliation(reason='not_yet_observed')
        origin = dict(utc=dict(status="network", sources=["a", "b"], lower=2000000000, upper=2000000000), counter=None)
        due = dict(utc=dict(status="network", sources=["a", "b"], lower=2000000120, upper=2000000120), counter=None)
        with tempfile.TemporaryDirectory() as d, patch('codex_wake.sessions.observe', return_value=inventory(live=True)):
            root = Path(d)
            for key in ('first', 'second', 'third'):
                with patch('codex_wake.native_clock.snapshot', return_value=origin), contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(run(['--wake-root', d, 'native', 'after', '--json', '--session-mode', 'background', '--endpoint', 'unix:///private/test.sock', '--codex-path', sys.executable, '--idempotency-key', key, THREAD, '1m', '--', key]), 0)
            with patch('codex_wake.native_clock.snapshot', return_value=due):
                poll_once(root, dispatch=False)
                first, second, third = all_records(root)
                self.assertEqual(first.record["status"], "firing", first.record["time_recovery"])
                result = dispatch_firing_record(root, first, runtime_adapter=boundary)
                self.assertEqual(result.status, 'submitted', result)
                self.assertEqual(dispatch_firing_record(root, second, runtime_adapter=boundary).status, 'requeued')
                self.assertEqual(boundary.submit.call_count, 1)
                boundary.reconcile.return_value = RuntimeReconciliation(evidence=dict(source='native_turn', execution='turn_completed', turn_id='turn1', user_message_id='message1', client_message_id='client1'))
                poll_once(root, dispatch=False)
                pending = next(item for item in all_records(root) if item.record['status'] == 'firing')
                self.assertEqual(dispatch_firing_record(root, pending, runtime_adapter=boundary).status, 'submitted')
                self.assertEqual(boundary.submit.call_count, 2)
                poll_once(root, dispatch=False)
                pending = next(item for item in all_records(root) if item.record['status'] == 'firing')
                self.assertEqual(dispatch_firing_record(root, pending, runtime_adapter=boundary).status, 'submitted')
                self.assertEqual(boundary.submit.call_count, 3)
                self.assertEqual(boundary.reconcile.call_count, 3)


class QualifiedServerAbsence(unittest.TestCase):
    def test_missing_pinned_socket_and_closed_original_client_allow_saved_resume(self):
        import subprocess
        import sys
        from codex_wake.process import process_identity
        child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])
        try:
            identity = process_identity(child.pid)
            child.terminate(); child.wait(timeout=5)
            with tempfile.TemporaryDirectory() as d:
                root = Path(d)
                target = dict(TARGET, tmux_socket=str(root / 'original.sock'), session_owner=dict(pid=child.pid, identity=identity))
                snapshot = dict(complete=False, sources=dict(app_server=dict(availability='available'), tmux=dict(availability='unavailable')), sessions=[])
                read = Mock(side_effect=[dict(id=THREAD, status=dict(type='notLoaded')), dict(id=THREAD, status=dict(type='idle')), dict(id=THREAD, status=dict(type='idle'))])
                request = Mock(return_value={'thread': {'id': THREAD}})
                runner = Mock(return_value=type('Result', (), dict(returncode=0, stdout='Queued message 22222222-2222-4222-8222-222222222222 for thread ' + THREAD + '.\n'))())
                base = CodexRuntimeAdapter(read_thread=read, request=request, run=runner, project_failure=Mock())
                with patch('codex_wake.sessions.observe', return_value=snapshot), patch('codex_wake.native_protocol.native_request', return_value=dict(turn=dict(id='background-turn-1'))) as start:
                    adapter = ModeRuntimeAdapter(root, base)
                    recipient = adapter.resolve(target)
                    self.assertEqual(adapter.observe(recipient).state, 'ready')
                    snapshot['sessions'] = [dict(thread_id=THREAD, runtime_state='idle', attachments=[])]
                    submitted = adapter.submit(recipient, 'check')
                    self.assertEqual(submitted.state, 'accepted')
                    self.assertEqual(submitted.evidence_kind, 'native_turn_acceptance')
                    self.assertEqual(start.call_args.args[2], 'turn/start')
                    self.assertEqual(start.call_args.args[3]['threadId'], THREAD)
                    runner.assert_not_called()
                self.assertEqual(request.call_args.args[2], 'thread/resume')
        finally:
            if child.poll() is None: child.terminate(); child.wait(timeout=5)

class BackgroundDispatch(unittest.TestCase):
    def test_native_dispatch_starts_exact_background_turn_without_queue_subprocess(self):
        import contextlib
        import io
        import sys
        from codex_wake.cli import run
        from codex_wake.daemon import poll_once
        from codex_wake.injector import dispatch_firing_record
        from codex_wake.records import all_records
        origin = dict(utc=dict(status='network', sources=['a', 'b'], lower=2000000000, upper=2000000000), counter=None)
        due = dict(utc=dict(status='network', sources=['a', 'b'], lower=2000000120, upper=2000000120), counter=None)
        with tempfile.TemporaryDirectory() as d, patch('codex_wake.sessions.observe', return_value=inventory()):
            root = Path(d)
            with patch('codex_wake.native_clock.snapshot', return_value=origin), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(run(['--wake-root', d, 'native', 'after', '--json', '--session-mode', 'background', '--endpoint', TARGET['endpoint'], '--codex-path', sys.executable, THREAD, '1m', '--', 'check']), 0)
            runner = Mock()
            base = CodexRuntimeAdapter(read_thread=Mock(return_value=dict(id=THREAD, status=dict(type='idle'))), request=Mock(), run=runner, project_failure=Mock())
            with patch('codex_wake.native_clock.snapshot', return_value=due), patch('codex_wake.native_protocol.native_request', return_value=dict(threadId=THREAD, turn=dict(id='turn-background'))) as start:
                poll_once(root, dispatch=False)
                result = dispatch_firing_record(root, all_records(root)[0], runtime_adapter=base)
                self.assertEqual(result.status, 'submitted', result)
                self.assertEqual(start.call_args.args[2], 'turn/start')
                self.assertEqual(start.call_args.args[3]['threadId'], THREAD)
                self.assertIn('check', start.call_args.args[3]['input'][0]['text'])
                runner.assert_not_called()
                delivery = all_records(root)[0].record['native_delivery']
                self.assertEqual(delivery['turn_id'], 'turn-background')
                self.assertNotIn('queue_id', delivery)

class HistoricalAdmissionBudget(unittest.TestCase):
    def test_legacy_terminal_backlog_is_reconciled_one_peer_per_admission(self):
        import contextlib
        import io
        import sys
        from codex_wake.cli import run
        from codex_wake.daemon import poll_once
        from codex_wake.injector import dispatch_firing_record
        from codex_wake.records import all_records
        from codex_wake.runtime_delivery import RuntimeObservation, RuntimeRecipient
        boundary=Mock()
        boundary.resolve.side_effect=lambda target:RuntimeRecipient('codex',target['thread_id'],target)
        boundary.observe.return_value=RuntimeObservation('ready','idle',{})
        boundary.submit.return_value=RuntimeSubmission('accepted',receipt_id='22222222-2222-4222-8222-222222222222',evidence_kind='native_queue_acceptance')
        boundary.reconcile.return_value=RuntimeReconciliation(evidence=dict(source='native_turn',execution='turn_completed',turn_id='turn',user_message_id='message',client_message_id='client'))
        origin=dict(utc=dict(status='network',sources=['a','b'],lower=2000000000,upper=2000000000),counter=None)
        due=dict(utc=dict(status='network',sources=['a','b'],lower=2000000120,upper=2000000120),counter=None)
        with tempfile.TemporaryDirectory() as d,patch('codex_wake.sessions.observe',return_value=inventory(live=True)):
            root=Path(d)
            for key in ('legacy-a','legacy-b'):
                with patch('codex_wake.native_clock.snapshot',return_value=origin),contextlib.redirect_stdout(io.StringIO()):
                    run(['--wake-root',d,'native','after','--json','--endpoint',TARGET['endpoint'],'--codex-path',sys.executable,'--idempotency-key',key,THREAD,'1m','--',key])
            with patch('codex_wake.native_clock.snapshot',return_value=due):
                poll_once(root,dispatch=False)
                for found in all_records(root):
                    self.assertEqual(dispatch_firing_record(root,found,runtime_adapter=boundary).status,'submitted')
            with patch('codex_wake.native_clock.snapshot',return_value=origin),contextlib.redirect_stdout(io.StringIO()):
                run(['--wake-root',d,'native','after','--json','--session-mode','background','--endpoint',TARGET['endpoint'],'--codex-path',sys.executable,'--idempotency-key','new-mode',THREAD,'1m','--','check'])
            with patch('codex_wake.native_clock.snapshot',return_value=due):
                poll_once(root,dispatch=False)
                pending=next(x for x in all_records(root) if x.record['status']=='firing')
                self.assertEqual(dispatch_firing_record(root,pending,runtime_adapter=boundary).status,'requeued')
                self.assertEqual(boundary.reconcile.call_count,1)
                self.assertEqual(boundary.submit.call_count,2)
                poll_once(root,dispatch=False)
                pending=next(x for x in all_records(root) if x.record['status']=='firing')
                self.assertEqual(dispatch_firing_record(root,pending,runtime_adapter=boundary).status,'submitted')
                self.assertEqual(boundary.reconcile.call_count,2)
