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

    def test_spawn_executes_exact_assignment_once_across_pending_observation(self):
        thread_id = '00000000-0000-7000-8000-000000000157'
        starts, tasks, windows = [], [], []
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
                elif method == 'thread/queue/start':
                    task = tasks[-1]
                    state['turns'] = [dict(id='turn157', status='inProgress', items=[
                        dict(id='user157', type='userMessage', clientId=task['clientUserMessageId'],
                             content=task['input'])])]
                    result = {'turn': state['turns'][0]}
                elif method == 'thread/queue/list':
                    result = {'data': [], 'nextCursor': None}
                else:
                    result = {}
                ws.send(json.dumps({'id': request['id'], 'result': result}))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            endpoint = root / 'native.sock'
            profiles = root / 'profiles.json'
            profiles.write_text(json.dumps({'version': 1, 'profiles': {'worker': {
                'cwd': tmp, 'app_server': 'unix://' + str(endpoint), 'codex_path': '/bin/true',
                'tmux_session': 'fixture', 'timeout': 1,
            }}}))
            master, slave = pty.openpty()
            client = subprocess.Popen([sys.executable, '-c',
                "import ctypes,time; ctypes.CDLL(None).prctl(15,b'codex',0,0,0); "
                "print('ready',flush=True); time.sleep(60)"], stdin=slave, stdout=subprocess.PIPE)
            self.assertEqual(client.stdout.readline(), b'ready\n')
            tty = os.ttyname(slave)
            def command(argv, **kwargs):
                if 'new-window' in argv:
                    windows.append(argv)
                    state['loaded'] = True
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
            try:
                with unix_serve(handler, str(endpoint)) as server:
                    worker = threading.Thread(target=server.serve_forever, daemon=True)
                    worker.start()
                    try:
                        with patch('subprocess.run', side_effect=command), patch(
                                'codex_wake.native_clock.snapshot', return_value={
                                    'utc': {'lower': 1000, 'upper': 1001}, 'counter': None}):
                            pending = StringIO()
                            with redirect_stdout(pending):
                                self.assertEqual(run(argv), 5, pending.getvalue())
                            state['turns'][0]['status'] = 'completed'
                            for _ in range(2):
                                output = StringIO()
                                with redirect_stdout(output):
                                    self.assertEqual(run(argv), 0, output.getvalue())
                                receipt = json.loads(output.getvalue())
                                self.assertEqual(receipt['state'], 'completed')
                                self.assertEqual(receipt['thread_id'], thread_id)
                                self.assertEqual(receipt['execution']['turn_id'], 'turn157')
                            self.assertEqual(len(starts), 1)
                            self.assertEqual(len(tasks), 1)
                            self.assertEqual(len(windows), 1)
                            self.assertEqual(tasks[0]['input'], [
                                {'type': 'text', 'text': 'Calculate 6 * 7 and report 42.'}])
                    finally:
                        server.shutdown()
                        worker.join(timeout=2)
            finally:
                client.terminate()
                client.wait(timeout=2)
                client.stdout.close()
                os.close(master)
                os.close(slave)
