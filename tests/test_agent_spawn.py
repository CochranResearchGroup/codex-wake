"""Public lifecycle behavior; fixture profiles never grant live authority."""
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import json
import os
import pty
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

from websockets.sync.server import unix_serve

from codex_wake.cli import run
from codex_wake.records import WakeError


class AgentSpawnTests(unittest.TestCase):
    def test_unapproved_profile_is_rejected_before_runtime_effects(self):
        with tempfile.TemporaryDirectory() as tmp:
            profiles = Path(tmp) / 'profiles.json'
            profiles.write_text(json.dumps({'version': 1, 'profiles': {}}))
            with redirect_stdout(StringIO()), self.assertRaisesRegex(WakeError, 'approved launch profile'):
                run(['--wake-root', tmp, 'sessions', 'spawn', '--profiles', str(profiles),
                     '--profile', 'unapproved', '--intent', 'first-worker', '--name', 'worker',
                     '--task', 'Report readiness.', '--expires-at', '2030-01-01T00:00:00Z', '--json'])

    def test_unknown_thread_creation_is_retained_without_duplicate_retry(self):
        starts = []
        def handler(ws):
            for raw in ws:
                request = json.loads(raw)
                if 'id' not in request:
                    continue
                if request['method'] == 'thread/start':
                    starts.append(request['params'])
                    ws.close()
                    return
                ws.send(json.dumps({'id': request['id'], 'result': {}}))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            endpoint = root / 'native.sock'
            profiles = root / 'profiles.json'
            profiles.write_text(json.dumps({'version': 1, 'profiles': {'worker': {
                'cwd': tmp, 'app_server': 'unix://' + str(endpoint),
                'codex_path': '/bin/true', 'tmux_session': 'fixture', 'timeout': 1,
            }}}))
            argv = ['--wake-root', tmp, 'sessions', 'spawn', '--profiles', str(profiles),
                    '--profile', 'worker', '--intent', 'one-worker', '--name', 'worker',
                    '--task', 'Report readiness.', '--expires-at', '2030-01-01T00:00:00Z', '--json']
            with unix_serve(handler, str(endpoint)) as server:
                worker = threading.Thread(target=server.serve_forever, daemon=True)
                worker.start()
                try:
                    with patch('subprocess.run') as command, patch(
                            'codex_wake.native_clock.snapshot', return_value={
                                'utc': {'lower': 1000, 'upper': 1001}, 'counter': None}):
                        command.return_value.stdout = ''
                        for _ in range(2):
                            output = StringIO()
                            with redirect_stdout(output):
                                self.assertEqual(run(argv), 5)
                            receipt = json.loads(output.getvalue())
                            self.assertEqual(receipt['state'], 'uncertain')
                            self.assertEqual(receipt['uncertain_effect'], 'thread/start')
                        self.assertEqual(len(starts), 1)
                finally:
                    server.shutdown()
                    worker.join(timeout=2)

    def test_peer_cannot_select_profile_without_host_caller_grant(self):
        with tempfile.TemporaryDirectory() as tmp:
            profiles = Path(tmp) / 'profiles.json'
            profiles.write_text(json.dumps({'version': 1, 'profiles': {'worker': {
                'cwd': tmp, 'app_server': 'unix:///missing.sock', 'codex_path': '/bin/true',
                'tmux_session': 'fixture', 'timeout': 1,
            }}, 'callers': {'00000000-0000-7000-8000-000000000011': ['worker']}}))
            with redirect_stdout(StringIO()), self.assertRaisesRegex(WakeError, 'caller grant'):
                run(['--wake-root', tmp, 'sessions', 'spawn', '--profiles', str(profiles),
                     '--profile', 'worker', '--intent', 'unauthorized', '--name', 'worker',
                     '--task', 'Report readiness.', '--expires-at', '2030-01-01T00:00:00Z',
                     '--caller-thread-id', '00000000-0000-7000-8000-000000000099', '--json'])

    def test_spawn_executes_exact_assignment_once_across_pending_observation(self):
        self.spawn_scenario()

    def test_lost_task_admission_response_reconciles_exact_queue_without_resend(self):
        self.spawn_scenario(loss='queue/add')

    def test_lost_tab_creation_response_reconciles_owned_generation_without_replacement(self):
        self.spawn_scenario(loss='new-window')

    def test_spawn_does_not_inherit_parent_actor_or_mailbox_capability(self):
        with patch.dict(os.environ, {'CODEX_THREAD_ID': 'parent', 'TMUX_PANE': '%parent',
                                    'CODEX_WAKE_A2A_CAPABILITY': '/parent/capability',
                                    'CODEX_WAKE_A2A_BUS_ROOT': '/parent/bus',
                                    'CODEX_WAKE_SENDER_RECEIPT_AUTHORITY': '/parent/authority'}):
            self.spawn_scenario(check_environment=True)

    def test_fixed_expiry_survives_startup_and_prevents_late_task_admission(self):
        self.spawn_scenario(expire_at_task=True)

    def test_reconciled_completion_keeps_original_uncertain_effect_history(self):
        self.spawn_scenario(loss='queue/add', check_history=True)

    def test_host_profile_uses_exact_isolated_socket_and_codex_home(self):
        self.spawn_scenario(isolated_profile=True)

    def test_native_default_text_elements_do_not_make_exact_admission_uncertain(self):
        self.spawn_scenario(normalized_input=True)

    def test_tui_auto_start_is_observed_without_starting_another_turn(self):
        self.spawn_scenario(auto_start=True)

    def spawn_scenario(self, *, loss=None, check_environment=False, expire_at_task=False,
                       check_history=False, isolated_profile=False, normalized_input=False, auto_start=False):
        thread_id = '00000000-0000-7000-8000-000000000157'
        starts, tasks, windows = [], [], []
        turn_starts = []
        state = {'name': None, 'turns': [], 'loaded': False}
        def handler(ws):
            for raw in ws:
                request = json.loads(raw)
                if 'id' not in request:
                    continue
                method, params = request['method'], request.get('params', {})
                thread = dict(id=thread_id, name=state['name'], cwd=tmp, status={'type': 'idle'},
                              canAcceptDirectInput=True, turns=state['turns'])
                if method == 'thread/start':
                    starts.append(params)
                    result = {'thread': thread}
                elif method == 'thread/name/set':
                    state['name'] = params['name']
                    result = {}
                elif method == 'thread/loaded/list':
                    result = {'data': [thread_id] if state['loaded'] else [], 'nextCursor': None}
                elif method == 'thread/read':
                    result = {'thread': thread}
                elif method == 'thread/queue/add':
                    tasks.append(params)
                    result = {'queuedSubmission': dict(id='queue157', **params)}
                    if normalized_input:
                        result['queuedSubmission']['input'] = [
                            dict(params['input'][0], text_elements=[])]
                    if auto_start:
                        state['turns'] = [dict(id='turn157', status='inProgress', items=[
                            dict(id='user157', type='userMessage', clientId=params['clientUserMessageId'],
                                 content=params['input'])])]
                    if loss == 'queue/add':
                        ws.close()
                        return
                elif method == 'thread/queue/start':
                    turn_starts.append(params)
                    task = tasks[-1]
                    state['turns'] = [dict(id='turn157',
                        status='completed' if loss else 'inProgress', items=[
                        dict(id='user157', type='userMessage', clientId=task['clientUserMessageId'],
                             content=task['input'])])]
                    result = {'turn': state['turns'][0]}
                elif method == 'thread/queue/list':
                    result = {'data': [dict(id='queue157', **tasks[-1])]
                              if tasks and not state['turns'] else [], 'nextCursor': None}
                else:
                    result = {}
                ws.send(json.dumps({'id': request['id'], 'result': result}))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            endpoint = root / 'native.sock'
            profiles = root / 'profiles.json'
            client_script = root / 'codex'
            client_script.write_text(f'#!{sys.executable}\n'
                'import ctypes,time,os,json,pathlib\n'
                "ctypes.CDLL(None).prctl(15,b'codex',0,0,0)\n"
                f'pathlib.Path({str(root / "client-env.json")!r}).write_text(json.dumps('
                '{k:v for k,v in os.environ.items() if k.startswith("CODEX_WAKE_") '
                'or k in ("CODEX_THREAD_ID","TMUX_PANE","CODEX_HOME")}))\n'
                "print('ready',flush=True)\ntime.sleep(60)\n")
            client_script.chmod(0o700)
            profile = {
                'cwd': tmp, 'app_server': 'unix://' + str(endpoint), 'codex_path': str(client_script),
                'tmux_session': 'fixture', 'timeout': 1,
            }
            if isolated_profile:
                (root / 'codex-home').mkdir()
                profile.update(tmux_socket=str(root / 'tmux.sock'), codex_home=str(root / 'codex-home'))
            profiles.write_text(json.dumps({'version': 1, 'profiles': {'worker': profile}}))
            master, slave = pty.openpty()
            client = None
            tty = os.ttyname(slave)
            def command(argv, **kwargs):
                nonlocal client
                if isolated_profile:
                    self.assertEqual(argv[:3], ['tmux', '-S', str(root / 'tmux.sock')])
                if 'new-window' in argv:
                    windows.append(argv)
                    client = subprocess.Popen(['sh', '-c', 'exec ' + argv[-1]],
                                              stdin=slave, stdout=subprocess.PIPE)
                    self.assertEqual(client.stdout.readline(), b'ready\n')
                    state['loaded'] = True
                    if loss == 'new-window':
                        raise subprocess.TimeoutExpired(argv, 1)
                    output = '@157\t%157'
                elif 'list-panes' in argv:
                    output = ('%157' if '-a' not in argv else '\t'.join([
                        '$1', 'fixture', '@157', '1', 'worker', '%157', '0', state['name'], tmp, tty]))
                else:
                    output = ''
                return subprocess.CompletedProcess(argv, 0, output, '')
            argv = ['--wake-root', tmp, 'sessions', 'spawn', '--profiles', str(profiles),
                    '--profile', 'worker', '--intent', 'one-worker', '--name', 'worker',
                    '--task', 'Calculate 6 * 7 and report 42.',
                    '--expires-at', '2030-01-01T00:00:00Z', '--json']
            def clock():
                upper = 1893456001 if expire_at_task and state['loaded'] else 1001
                return {'utc': {'lower': upper - 1, 'upper': upper}, 'counter': None}
            try:
                with unix_serve(handler, str(endpoint)) as server:
                    worker = threading.Thread(target=server.serve_forever, daemon=True)
                    worker.start()
                    try:
                        with patch('subprocess.run', side_effect=command), patch(
                                'codex_wake.native_clock.snapshot', side_effect=clock):
                            pending = StringIO()
                            with redirect_stdout(pending):
                                self.assertEqual(run(argv), 5, pending.getvalue())
                            if normalized_input:
                                self.assertEqual(json.loads(pending.getvalue())['state'], 'awaiting_preflight')
                            if expire_at_task:
                                self.assertEqual(json.loads(pending.getvalue())['state'], 'expired')
                                with redirect_stdout(StringIO()):
                                    self.assertEqual(run(argv), 5)
                                self.assertEqual(len(starts), 1)
                                self.assertEqual(len(windows), 1)
                                self.assertEqual(tasks, [])
                                return
                            if state['turns']:
                                state['turns'][0]['status'] = 'completed'
                            for _ in range(2):
                                output = StringIO()
                                with redirect_stdout(output):
                                    self.assertEqual(run(argv), 0, output.getvalue())
                                receipt = json.loads(output.getvalue())
                                self.assertEqual(receipt['state'], 'completed')
                                self.assertEqual(receipt['thread_id'], thread_id)
                                self.assertEqual(receipt['execution']['turn_id'], 'turn157')
                                if check_history:
                                    self.assertIn({'state': 'uncertain', 'effect': 'thread/queue/add',
                                                   'reason': 'ConnectionClosedOK'}, receipt['history'])
                                    self.assertIsNone(receipt.get('reason'))
                            self.assertEqual(len(starts), 1)
                            self.assertEqual(len(tasks), 1)
                            self.assertEqual(len(windows), 1)
                            if auto_start:
                                self.assertEqual(turn_starts, [])
                            self.assertEqual(tasks[0]['input'], [
                                {'type': 'text', 'text': 'Calculate 6 * 7 and report 42.'}])
                            if check_environment:
                                variables = json.loads((root / 'client-env.json').read_text())
                                self.assertFalse(set(variables) & {
                                    'CODEX_THREAD_ID', 'TMUX_PANE', 'CODEX_WAKE_A2A_CAPABILITY',
                                    'CODEX_WAKE_A2A_BUS_ROOT', 'CODEX_WAKE_SENDER_RECEIPT_AUTHORITY'})
                            if isolated_profile:
                                self.assertEqual(json.loads((root / 'client-env.json').read_text())['CODEX_HOME'],
                                                 str(root / 'codex-home'))
                    finally:
                        server.shutdown()
                        worker.join(timeout=2)
            finally:
                if client:
                    client.terminate()
                    client.wait(timeout=2)
                    client.stdout.close()
                os.close(master)
                os.close(slave)
