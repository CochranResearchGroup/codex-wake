import hashlib
import os
from pathlib import Path
import tempfile
import unittest

from codex_wake.process import process_identity


class LocalHealthTests(unittest.TestCase):
    def binding(self, directory):
        identity = process_identity(os.getpid())
        home = str(Path(directory).resolve())
        namespace = hashlib.sha256(__import__('json').dumps([home, 'test'], separators=(',', ':')).encode()).hexdigest()
        return dict(target=dict(host='local', environment='linux', runtime='codex',
            namespace='codex:' + namespace, build_sha256=hashlib.sha256(Path('/proc/self/exe').read_bytes()).hexdigest(),
            conversation_id='thread-one', home=home, provider='test', backend_id='test', channel='native_tui',
            process=dict(pid=os.getpid(), start_ticks=str(identity['start_time_ticks']), boot_id=identity['boot_id']),
            connection_generation='one'), endpoint='unix:///fixture.sock', codex_cmd=[str(Path('/proc/self/exe').resolve())])

    def test_same_user_binding_observes_fresh_exact_loop_without_registry_or_grant(self):
        from codex_wake.controller_health import ControllerHealth
        def request(endpoint, command, method, arguments, timeout):
            return dict(state='responsive', evidence='tui_main_loop_ack', challenge=arguments['challenge'],
                        binding=arguments['binding'], threadId=arguments['threadId'], loopTid=os.getpid())
        with tempfile.TemporaryDirectory() as directory:
            binding = self.binding(directory)
            result = ControllerHealth(directory, request=request).observe_binding(binding['target'], binding, timeout=.5)
            self.assertEqual(result['observation']['status'], 'responsive', result)
            self.assertEqual(result['observation']['loop_tid'], os.getpid())
            self.assertFalse(result['application_effects'])
            self.assertFalse(result['grants_recovery'])

    def test_local_row_derives_tui_identity_instead_of_using_daemon_identity(self):
        from codex_wake.local_health import observe_row
        def request(endpoint, command, method, arguments, timeout):
            if method == 'tui/health/describe':
                return {'bindings': [dict(home=directory, provider='test', backendId='test', channel='native_tui',
                    pid=os.getpid(), startTicks=str(process_identity(os.getpid())['start_time_ticks']),
                    bootId=process_identity(os.getpid())['boot_id'], connectionGeneration='fresh')]}
            return dict(state='responsive', evidence='tui_main_loop_ack', challenge=arguments['challenge'],
                binding=arguments['binding'], threadId=arguments['threadId'], loopTid=os.getpid())
        with tempfile.TemporaryDirectory() as directory:
            binding = self.binding(directory)
            target = dict(binding['target'], executable=str(Path('/proc/self/exe').resolve()))
            row = dict(model_provider='test', target=dict(target, provider='codex'), endpoint=binding['endpoint'], codex_cmd=binding['codex_cmd'],
                       attachments=[dict(client_pid=os.getpid())])
            result = observe_row(directory, row, timeout=1, request=request)
            self.assertEqual(result['observation']['status'], 'responsive', result)
            self.assertEqual(result['target']['connection_generation'], 'fresh')

    def test_wrong_conversation_candidate_or_transport_timeout_never_becomes_stuck(self):
        from codex_wake.local_health import observe_row
        from codex_wake.native_protocol import NativeHealthDeadline
        with tempfile.TemporaryDirectory() as directory:
            binding = self.binding(directory)
            row = dict(target=dict(binding['target'], executable=str(Path('/proc/self/exe').resolve())),
                       endpoint=binding['endpoint'], codex_cmd=binding['codex_cmd'], attachments=[dict(client_pid=os.getpid())])
            for error, expected in [(NativeHealthDeadline('native candidate deadline'), 'unknown'), (TimeoutError(), 'unknown')]:
                def request(endpoint, command, method, arguments, timeout):
                    if method == 'tui/health/describe':
                        target = binding['target']
                        return {'bindings': [dict(home=directory, provider='test', backendId='test', channel='native_tui',
                            pid=os.getpid(), startTicks=target['process']['start_ticks'], bootId=target['process']['boot_id'], connectionGeneration='one')]}
                    raise error
                result = observe_row(directory, row, timeout=1, request=request)
                self.assertEqual(result['observation']['status'], expected)
                self.assertFalse(result['observation']['responsive'])

    def test_gone_pinned_runtime_is_offline_without_claiming_responsiveness(self):
        import subprocess
        from codex_wake.local_health import observe_row
        with tempfile.TemporaryDirectory() as directory:
            binding = self.binding(directory)
            child = subprocess.Popen(['/bin/true'])
            child.wait()
            target = dict(binding['target'], executable=str(Path('/proc/self/exe').resolve()),
                          process=dict(pid=child.pid, start_ticks='1', boot_id='fixture'))
            row = dict(target=target, endpoint=binding['endpoint'], codex_cmd=binding['codex_cmd'])
            result = observe_row(directory, row)
            self.assertEqual(result['observation']['status'], 'offline')
            self.assertFalse(result['observation']['responsive'])

    def test_only_exact_native_probe_deadline_code_and_method_qualify(self):
        import json
        import threading
        from websockets.sync.server import unix_serve
        from codex_wake.native_protocol import native_request, NativeHealthDeadline
        from codex_wake.records import WakeError
        for method, code, qualified in [('tui/health/probe', -32001, True),
                                         ('tui/health/probe', -32603, False),
                                         ('thread/read', -32001, False)]:
            with self.subTest(method=method, code=code), tempfile.TemporaryDirectory() as directory:
                def handler(ws):
                    for raw in ws:
                        request = json.loads(raw)
                        if 'id' not in request: continue
                        response = dict(id=request['id'])
                        if request['method'] == 'initialize': response['result'] = {}
                        else: response['error'] = dict(code=code, message='foreground loop deadline expired')
                        ws.send(json.dumps(response))
                        if request['method'] != 'initialize': return
                endpoint = str(Path(directory) / 'server.sock')
                with unix_serve(handler, endpoint) as server:
                    worker = threading.Thread(target=server.serve_forever, daemon=True)
                    worker.start()
                    try:
                        with self.assertRaises(WakeError) as caught:
                            native_request('unix://' + endpoint, ['unused'], method, {}, 1)
                        self.assertEqual(isinstance(caught.exception, NativeHealthDeadline), qualified)
                    finally:
                        server.shutdown()
                        worker.join(timeout=2)
