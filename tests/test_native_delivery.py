from datetime import UTC, datetime
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from codex_wake.cli import run
from codex_wake.daemon import poll_once
from codex_wake.records import all_records, build_record, write_record


class NativeDeliveryTests(unittest.TestCase):
    def test_file_wake_expires_even_if_file_never_appears(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.native_record(root, root / 'must-not-run')
            record = all_records(root)[0].record
            record['predicate'] = {'type': 'file_exists', 'path': str(root / 'missing')}
            from codex_wake.records import replace_record
            replace_record(root, all_records(root)[0], record)
            poll_once(root, datetime(2026, 10, 9, 0, 11, tzinfo=UTC))
            self.assertEqual(all_records(root)[0].record['status'], 'failed')

    def native_record(self, root, executable):
        record = build_record(predicate={'type': 'not_before', 'due_at': '2026-10-09T00:00:00Z'},
                              prompt='Execute the task', cwd=root,
                              target={'transport': 'native', 'thread_id': '01a1227e-a041-7b72-9c36-18349e7dd22c',
                                      'endpoint': 'unix://', 'codex_cmd': str(executable),
                                      'expires_at': '2026-10-09T00:10:00Z'})
        write_record(root, record)

    def test_busy_recipient_holds_until_expiry_without_submission(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.native_record(root, root / 'must-not-run')
            with patch('codex_wake.native_delivery.read_native_thread',
                       return_value={'id': '01a1227e-a041-7b72-9c36-18349e7dd22c', 'status': {'type': 'active'}}):
                result = poll_once(root, datetime(2026, 10, 9, tzinfo=UTC))
            self.assertEqual(result.requeued, 1)
            self.assertEqual(all_records(root)[0].record['status'], 'pending')
            result = poll_once(root, datetime(2026, 10, 9, 0, 11, tzinfo=UTC))
            self.assertEqual(result.failed, 1)
            self.assertNotIn('native_delivery', all_records(root)[0].record)

    def test_uncertain_acceptance_is_not_resubmitted_on_another_poll(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            executable = root / 'codex'
            counter = root / 'calls'
            executable.write_text('#!/usr/bin/env python3\nfrom pathlib import Path\nimport sys\n'
                                  'if sys.argv[1] != "queue": sys.exit(2)\n'
                                  f'with Path({str(counter)!r}).open("a") as f: f.write("call\\n")\n'
                                  'print("Unknown result")\n')
            executable.chmod(0o700)
            self.native_record(root, executable)
            with patch('codex_wake.native_delivery.read_native_thread',
                       return_value={'id': '01a1227e-a041-7b72-9c36-18349e7dd22c', 'status': {'type': 'idle'}}):
                poll_once(root, datetime(2026, 10, 9, tzinfo=UTC))
                poll_once(root, datetime(2026, 10, 9, 0, 1, tzinfo=UTC))
            self.assertEqual(counter.read_text(), 'call\n')
            self.assertEqual(all_records(root)[0].record['native_delivery']['state'], 'uncertain')
            self.assertEqual(all_records(root)[0].record['native_delivery']['reconciliation']['state'], 'unresolved')

    def test_persisted_due_wake_uses_native_queue_and_records_acceptance(self):
        thread = '01a1227e-a041-7b72-9c36-18349e7dd22c'
        queue = '01a12280-80ef-7772-a00a-c68bd32ecbba'
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'wake'
            executable = Path(tmp) / 'codex'
            executable.write_text('#!/usr/bin/env python3\nimport sys\n'
                                  'assert sys.argv[1] == "queue"\n'
                                  f'print("Queued message {queue} for thread {thread}.")\n')
            executable.chmod(0o700)
            self.assertEqual(run(['--wake-root', str(root), 'native', 'at',
                                  '--codex-path', str(executable), thread,
                                  '2026-10-09T00:00:00Z', '--', 'Do the scheduled task']), 0)
            with patch('codex_wake.native_delivery.read_native_thread',
                       return_value={'id': thread, 'status': {'type': 'idle'}}), patch(
                       'codex_wake.injector.SubprocessTmuxRunner') as tmux:
                result = poll_once(root, datetime(2026, 10, 9, tzinfo=UTC))
            tmux.assert_not_called()
            self.assertEqual(result.submitted, 1)
            record = all_records(root)[0].record
            self.assertEqual(record['native_delivery']['queue_id'], queue)
            self.assertEqual(record['native_delivery']['execution'], 'not_observed')
            self.assertEqual(record['native_delivery']['acknowledgment'], 'not_observed')

    def test_reconcile_recovers_exact_native_turn_without_resending(self):
        from codex_wake.records import replace_record
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.native_record(root, root/'must-not-submit')
            found = all_records(root)[0]
            record = dict(found.record, status='firing', native_delivery={
                'state':'uncertain','execution':'not_observed','acknowledgment':'not_observed'})
            replace_record(root, found, record)
            prompt = f"WAKE_TRIGGER_ID={record['id']}\nWAKE_TRIGGER_ROOT={root.resolve()}\nExecute the task"
            def native(endpoint, codex, method, params, timeout):
                if method == 'thread/queue/list':
                    return {'data':[], 'nextCursor':None}
                return {'thread':{'id':record['target']['thread_id'],'turns':[
                    {'id':'turn-exact','status':'completed','items':[{'type':'userMessage',
                     'id':'message-exact','clientId':'client-exact',
                     'content':[{'type':'text','text':prompt}]}]}]}}
            with patch('codex_wake.native_delivery.native_request', side_effect=native), patch(
                    'codex_wake.native_delivery.subprocess.run') as effect:
                self.assertEqual(run(['--wake-root',str(root),'native','reconcile',record['id']]),0)
            effect.assert_not_called()
            recovered = all_records(root)[0].record
            self.assertEqual(recovered['status'],'submitted')
            self.assertEqual(recovered['native_delivery']['state'],'accepted')
            self.assertEqual(recovered['native_delivery']['execution'],'turn_completed')
            self.assertEqual(recovered['native_delivery']['evidence']['turn_id'],'turn-exact')
            self.assertEqual(recovered['native_delivery']['acknowledgment'],'not_observed')

    def test_explicit_missing_resume_uses_same_thread_without_opening_a_tab(self):
        thread='01a1227e-a041-7b72-9c36-18349e7dd22c'
        queue='01a12280-80ef-7772-a00a-c68bd32ecbba'
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'wakes'; executable=Path(tmp)/'codex'
            executable.write_text('#!/usr/bin/env python3\n'+f'print("Queued message {queue} for thread {thread}.")\n')
            executable.chmod(0o700)
            self.assertEqual(run(['--wake-root',str(root),'native','at','--resume-missing',
                '--codex-path',str(executable),thread,'2026-10-09T00:00:00Z','--','Resume this exact thread']),0)
            with patch('codex_wake.native_delivery.read_native_thread',side_effect=[
                    {'id':thread,'status':{'type':'notLoaded'}},{'id':thread,'status':{'type':'idle'}}]), patch(
                    'codex_wake.native_delivery.native_request',return_value={'thread':{'id':thread}}) as native, patch(
                    'codex_wake.injector.SubprocessTmuxRunner') as tmux:
                result=poll_once(root,datetime(2026,10,9,tzinfo=UTC))
            self.assertEqual(result.submitted,1)
            self.assertEqual(native.call_args.args[2:4],('thread/resume',{'threadId':thread}))
            tmux.assert_not_called()
            self.assertEqual(all_records(root)[0].record['target']['thread_id'],thread)

    def test_duplicate_native_turns_remain_uncertain_even_with_same_client_identity(self):
        from codex_wake.records import replace_record
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.native_record(root,root/'must-not-submit')
            found=all_records(root)[0]
            record=dict(found.record,status='firing',native_delivery={'state':'uncertain'})
            replace_record(root,found,record)
            prompt=f"WAKE_TRIGGER_ID={record['id']}\nWAKE_TRIGGER_ROOT={root.resolve()}\nExecute the task"
            def native(endpoint,codex,method,params,timeout):
                if method=='thread/queue/list':return {'data':[]}
                return {'thread':{'id':record['target']['thread_id'],'turns':[
                    {'id':'turn-'+suffix,'status':'completed','items':[{'type':'userMessage',
                     'id':'message-'+suffix,'clientId':'same-client',
                     'content':[{'type':'text','text':prompt}]}]} for suffix in ('one','two')]}}
            with patch('codex_wake.native_delivery.native_request',side_effect=native), patch(
                    'codex_wake.native_delivery.subprocess.run') as effect:
                run(['--wake-root',str(root),'native','reconcile',record['id']])
            effect.assert_not_called()
            self.assertEqual(all_records(root)[0].record['native_delivery']['state'],'uncertain')
