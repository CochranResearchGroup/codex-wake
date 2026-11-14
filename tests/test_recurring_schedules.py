"""Durable schedule behavior through registration/inspection and polling."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from codex_wake.cli import run
from codex_wake.records import all_records

THREAD = '11111111-1111-4111-8111-111111111111'
def request(**changes):
    value = dict(idempotency_key='twice', thread_id=THREAD, prompt='Check status', session_mode='background',
        cadence=dict(kind='interval', seconds=43200, start_at='2033-05-18T03:33:20Z'),
        end=dict(kind='count', count=3), missed=dict(policy='latest', max_lateness_seconds=86400),
        overlap=dict(policy='queue', limit=2), delivery_window_seconds=3600)
    value.update(changes)
    return value

class RecurringSchedules(unittest.TestCase):
    def cli(self, root, *args):
        out = io.StringIO()
        with patch("codex_wake.sessions.observe", return_value={"complete": False, "sessions": []}), contextlib.redirect_stdout(out):
            code = run(['--wake-root', str(root), 'schedules', *args])
        self.assertEqual(code, 0)
        return json.loads(out.getvalue())
    def test_interval_occurrences_survive_restart_without_rearming_or_duplicate(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); spec=root/'request.json'; spec.write_text(json.dumps(request()))
            registered=self.cli(root, 'register', '--request', str(spec), '--codex-path', sys.executable)
            self.assertEqual(registered['session_mode'], 'background')
            self.assertFalse(registered['armed'])
            from codex_wake.recurring_schedules import poll_schedules
            clock={'utc': {'lower':2000000000,'upper':2000000000,'status':'network','sources':['clock-a','clock-b']}, 'counter':None}
            poll_schedules(root, clock)
            first=self.cli(root, 'show', registered['id'])
            self.assertEqual(len(first['occurrences']),1)
            self.assertEqual(first['occurrences'][0]['due_at'],'2033-05-18T03:33:20Z')
            poll_schedules(root, clock)
            self.assertEqual(len(all_records(root)),1)
            self.assertEqual(self.cli(root, 'show', registered['id'])['occurrences'],first['occurrences'])
            poll_schedules(root, {'utc':dict(clock['utc'],lower=2000043200,upper=2000043200),'counter':None})
            self.assertEqual(len(self.cli(root,'show',registered['id'])['occurrences']),2)
    def test_missing_explicit_mode_rejected_without_creating_schedule(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); spec=root/'request.json'; value=request();value.pop('session_mode');spec.write_text(json.dumps(value))
            from codex_wake.records import WakeError
            with self.assertRaisesRegex(WakeError,'session_mode'):
                self.cli(root,'register','--request',str(spec),'--codex-path',sys.executable)
    def test_downtime_counts_misses_and_latest_keeps_original_deadline(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); spec=root/'request.json'
            spec.write_text(json.dumps(request(delivery_window_seconds=172800, missed=dict(policy='latest',max_lateness_seconds=172800))))
            registered=self.cli(root,'register','--request',str(spec),'--codex-path',sys.executable)
            from codex_wake.recurring_schedules import poll_schedules
            clock={'utc':{'lower':2000086400,'upper':2000086400,'status':'network','sources':['a','b']},'counter':None}
            poll_schedules(root,clock)
            value=self.cli(root,'show',registered['id'])
            self.assertEqual([x['state'] for x in value['occurrences']],['coalesced','coalesced','pending'])
            self.assertEqual(value['next_index'],3)
            self.assertEqual(len(all_records(root)),1)
            self.assertEqual(value['occurrences'][-1]['due_at'],'2033-05-19T03:33:20Z')
    def test_daemon_registers_due_occurrence_and_cancel_preserves_history(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); spec=root/'request.json'; spec.write_text(json.dumps(request()))
            registered=self.cli(root,'register','--request',str(spec),'--codex-path',sys.executable)
            from codex_wake.daemon import poll_once
            clock={'utc':{'lower':2000000000,'upper':2000000000,'status':'network','sources':['a','b']},'counter':None}
            with patch('codex_wake.native_clock.snapshot',return_value=clock):
                poll_once(root,dispatch=False)
            self.assertEqual(len(all_records(root)),1)
            value=request();value['cadence']['seconds']=86400;spec.write_text(json.dumps(value))
            changed=self.cli(root,'revise',registered['id'],'--request',str(spec),'--expected-revision','1','--codex-path',sys.executable)
            self.assertEqual(changed['revision'],2)
            self.assertEqual(changed['occurrences'][0]['due_at'],'2033-05-18T03:33:20Z')
            cancelled=self.cli(root,'cancel',registered['id'],'--expected-revision','2')
            self.assertEqual(cancelled['state'],'cancelled')
            self.assertEqual(all_records(root)[0].record['status'],'cancelled')
            with patch('codex_wake.native_clock.snapshot',return_value=clock):
                poll_once(root,dispatch=False)
            self.assertEqual(len(all_records(root)),1)
    def test_native_mcp_schedule_tools_bind_exact_caller_and_hide_peer(self):
        from codex_wake.mcp_server import CommandRunner
        with tempfile.TemporaryDirectory() as d:
            runner=CommandRunner(wake_root=Path(d))
            meta=dict(threadId=THREAD,sessionId=THREAD,callId='schedule',**{'x-codex-turn-metadata':dict(thread_id=THREAD,session_id=THREAD,turn_id='test-turn')})
            with patch('codex_wake.app_server.resolve_codex_cmd',return_value=sys.executable), patch('codex_wake.sessions.observe',return_value={'complete':False,'sessions':[]}):
                value,failed=runner.call('wake_schedules_register',dict(caller_thread_id=THREAD,request=request()),native_context=meta)
            self.assertFalse(failed,value)
            self.assertFalse(value['armed'])
            other='22222222-2222-4222-8222-222222222222'
            othermeta=dict(threadId=other,sessionId=other,callId='peer',**{'x-codex-turn-metadata':dict(thread_id=other,session_id=other,turn_id='test-turn')})
            denied,failed=runner.call('wake_schedules_show',dict(caller_thread_id=other,schedule_id=value['id']),native_context=othermeta)
            self.assertTrue(failed,denied)
    def test_large_prompt_backlog_remains_inspectable_without_copying_prompt_per_occurrence(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); spec=root/'request.json'
            value=request(prompt='x'*32000,cadence=dict(kind='interval',seconds=1,start_at='2033-05-18T03:33:20Z'),end=dict(kind='count',count=130),missed=dict(policy='latest',max_lateness_seconds=600),delivery_window_seconds=600)
            spec.write_text(json.dumps(value))
            registered=self.cli(root,'register','--request',str(spec),'--codex-path',sys.executable)
            from codex_wake.recurring_schedules import poll_schedules
            poll_schedules(root,{'utc':{'lower':2000000129,'upper':2000000129,'status':'network','sources':['a','b']},'counter':None})
            saved=self.cli(root,'show',registered['id'])
            self.assertEqual(len(saved['occurrences']),130)
            self.assertEqual(saved['request']['prompt'],'x'*32000)
