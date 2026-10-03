#!/usr/bin/env python3
"""Installed, provider-free Unix WebSocket session discovery acceptance."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading

from websockets.sync.server import unix_serve


def run(cli: str) -> dict:
    methods = []
    closed = []
    threads = {
        '00000000-0000-7000-8000-000000000001': dict(name='Fixture root', cwd='/fixture', status={'type': 'idle'}, parentThreadId=None),
        '00000000-0000-7000-8000-000000000002': dict(name='Fixture child', cwd='/fixture', status={'type': 'active', 'activeFlags': ['waitingOnApproval']}, parentThreadId='00000000-0000-7000-8000-000000000001'),
    }
    def handle(connection):
        try:
            for raw in connection:
                request = json.loads(raw)
                method = request['method']
                methods.append(method)
                if method == 'initialized':
                    continue
                if method == 'initialize':
                    result = {}
                elif method == 'thread/loaded/list':
                    result = dict(data=list(threads), nextCursor=None)
                elif method == 'thread/read':
                    assert request['params']['includeTurns'] is False
                    thread_id = request['params']['threadId']
                    result = dict(thread=dict(id=thread_id, preview='PRIVATE_PREVIEW', turns=['PRIVATE_TRANSCRIPT'], **threads[thread_id]))
                else:
                    raise AssertionError('unexpected mutating method: ' + method)
                connection.send(json.dumps(dict(id=request['id'], result=result)))
        finally:
            closed.append(True)

    with tempfile.TemporaryDirectory(prefix='wake-session-smoke-') as temporary:
        root = Path(temporary)
        tools = root / 'bin'
        tools.mkdir()
        fake_tmux = tools / 'tmux'
        fake_tmux.write_text('#!/bin/sh\nexit 0\n')
        fake_tmux.chmod(0o700)
        environment = dict(os.environ, PATH=str(tools) + os.pathsep + os.environ.get('PATH', ''))
        for name in ['TMUX', 'TMUX_PANE', 'PYTHONPATH']:
            environment.pop(name, None)
        environment['CODEX_THREAD_ID'] = next(iter(threads))
        socket_path = root / 'server.sock'
        with unix_serve(handle, path=str(socket_path)) as server:
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            def invoke(arguments, expected=0):
                command = [cli, 'sessions', *arguments, '--json', '--app-server', 'unix://' + str(socket_path)]
                result = subprocess.run(command, env=environment, capture_output=True, text=True, timeout=15)
                assert result.returncode == expected, (arguments, result.returncode, result.stderr, result.stdout)
                assert 'PRIVATE_' not in result.stdout
                return [json.loads(line) for line in result.stdout.splitlines()]
            try:
                inventory = invoke(['list'])[0]
                assert inventory['complete'] and len(inventory['sessions']) == 2
                assert len(invoke(['list', '--roots-only'])[0]['sessions']) == 1
                exact = 'thread:' + next(iter(threads))
                assert invoke(['resolve', exact])[0]['session']['thread_id'] == next(iter(threads))
                assert invoke(['show', exact])[0]['session']['attachments'] == []
                assert invoke(['current'])[0]['session']['thread_id'] == next(iter(threads))
                watch = invoke(['watch', exact, '--duration', '1s', '--interval', '1'])
                assert watch[0]['event'] == 'initial' and watch[-1]['event'] == 'summary'
                assert invoke(['resolve', exact, '--require-attested'], 5)[0]['code'] == 5
                resource_code = '''
import json,sys,threading
from pathlib import Path
from codex_wake.shared_app_server import SharedAppServerReader
before=len(list(Path('/proc/self/fd').iterdir()))
threads_before=threading.active_count()
for _ in range(10):
    with SharedAppServerReader(sys.argv[1]) as reader:
        reader.loaded_threads()
after=len(list(Path('/proc/self/fd').iterdir()))
assert after <= before, (before, after)
assert threading.active_count() <= threads_before
print(json.dumps(dict(descriptors_before=before, descriptors_after=after,
                     threads_before=threads_before, threads_after=threading.active_count())))
'''
                resource_result = subprocess.run([str(Path(cli).parent / 'python'), '-c', resource_code,
                                                  'unix://' + str(socket_path)], env=environment,
                                                 capture_output=True, text=True, timeout=15)
                assert resource_result.returncode == 0, resource_result.stderr
                resources = json.loads(resource_result.stdout)
            finally:
                server.shutdown()
                worker.join(timeout=5)
                assert not worker.is_alive()
    allowed = {'initialize', 'initialized', 'thread/loaded/list', 'thread/read'}
    assert set(methods) <= allowed
    assert len(closed) == methods.count('initialize')
    return dict(schema_version=1, status='accepted', installed_cli=cli,
                method_counts={method: methods.count(method) for method in sorted(set(methods))},
                connections_closed=len(closed), no_transcript_output=True,
                no_lifecycle_methods=True, **resources)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--cli', required=True)
    arguments = parser.parse_args()
    print(json.dumps(run(arguments.cli), sort_keys=True))
