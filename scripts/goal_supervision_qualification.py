"""Opt-in public MCP/controller qualification with injected native protocol.

Uses the configured trusted clock; creates no model calls, tabs or native sessions.
Run with the candidate installed Python and --output pointing at a new directory.
"""
import argparse
import asyncio
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time

from mcp import Client, StdioServerParameters
from websockets.sync.server import unix_serve

from codex_wake.lifecycle_budget import trusted_upper


async def qualify(directory):
    directory.mkdir(mode=0o700, parents=True, exist_ok=False)
    root = directory / 'runtime'
    home = directory / 'home'
    (home / 'sessions').mkdir(parents=True, mode=0o700)
    thread = '00000000-0000-7000-8000-000000000279'
    created = int(trusted_upper()) - 2
    timestamp = datetime.fromtimestamp(created, timezone.utc).isoformat()
    goal = dict(threadId=thread, createdAt=created, status='active', objective='Qualification')
    native = {'thread': {'id': thread, 'turns': [{'id': 'owned-turn', 'status': 'inProgress', 'items': []}]}}
    requests = []
    mutex = threading.Lock()

    def row(kind, payload):
        return dict(type=kind, timestamp=timestamp, payload=payload)

    def usage(response_id, tokens):
        return row('token_usage_record', dict(thread_id=thread, turn_id='owned-turn',
            root_turn_id='owned-turn', session_id=thread, response_id=response_id,
            usage=dict(input_tokens=tokens-2, cached_input_tokens=tokens-3,
                       output_tokens=2, total_tokens=tokens), turn_token_usage={}, thread_token_usage={}))

    rollout = home / 'sessions' / 'rollout.jsonl'
    rows = [row('session_meta', dict(id=thread, session_id=thread, source='cli')),
            row('event_msg', dict(type='thread_goal_updated', threadId=thread, goal=dict(goal))),
            row('event_msg', dict(type='task_started', turn_id='owned-turn')), usage('first', 40)]
    rollout.write_text(''.join(json.dumps(r) + '\n' for r in rows))

    def handler(ws):
        for raw in ws:
            request = json.loads(raw)
            if 'id' not in request:
                continue
            method, params = request['method'], request.get('params', {})
            with mutex:
                if method != 'initialize':
                    assert params['threadId'] == thread, 'Foreign thread targeted'
                    requests.append(dict(method=method, params=params))
                if method == 'initialize':
                    result = {}
                elif method == 'thread/goal/get':
                    result = {'goal': dict(goal)}
                elif method == 'thread/read':
                    result = json.loads(json.dumps(native))
                elif method == 'thread/goal/set':
                    goal['status'] = params['status']; result = {'goal': dict(goal)}
                elif method == 'turn/interrupt':
                    assert params['turnId'] == 'owned-turn'
                    native['thread']['turns'][0]['status'] = 'interrupted'; result = {}
                elif method == 'turn/steer':
                    assert params['expectedTurnId'] == 'owned-turn'; result = {'turnId': 'owned-turn'}
                else:
                    raise AssertionError('Unexpected native method: ' + method)
            ws.send(json.dumps({'id': request['id'], 'result': result}))

    endpoint = directory / 'native.sock'
    policy = directory / 'policy.json'
    policy.write_text(json.dumps(dict(version=1, callers={thread: dict(
        app_server='unix://' + str(endpoint), codex_path=str(Path(sys.executable).resolve()),
        codex_home=str(home.resolve()), allocation_id='user-approved-original',
        max_tokens=1000, max_seconds=600, rpc_timeout=1)})))
    policy.chmod(0o600)
    environment = dict(os.environ)
    environment.pop('PYTHONPATH', None)
    log = (directory / 'watcher.log').open('w')
    watcher = None
    with unix_serve(handler, str(endpoint)) as server:
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()
        try:
            parameters = StdioServerParameters(command=sys.executable,
                args=['-m', 'codex_wake.mcp_server', '--wake-root', str(root),
                      '--goal-limits-policy', str(policy)], env=environment)
            async with Client(parameters, mode='legacy') as client:
                async def call(name, body):
                    result = await client.call_tool(name, dict(caller_thread_id=thread, **body))
                    return json.loads(result.content[0].text), result.is_error

                watcher = subprocess.Popen([sys.executable, '-m', 'codex_wake', '--wake-root', str(root),
                    'goal-limits', 'watch', '--interval', '0.1'], env=environment, stdout=log, stderr=log)
                async def until(predicate, seconds=8):
                    deadline = time.monotonic() + seconds
                    while time.monotonic() < deadline:
                        value, failed = await call('wake_goal_limits_show', {})
                        if not failed and predicate(value):
                            return value
                        if watcher.poll() is not None:
                            raise AssertionError('Independent watcher exited; see watcher.log')
                        await asyncio.sleep(.05)
                    raise AssertionError('Qualification condition timed out')

                await until(lambda v: v.get('controller', {}).get('fresh'))
                enrolled, failed = await call('wake_goal_limits_set', dict(
                    token_limit=100, time_limit_seconds=300, checkpoint_seconds=299))
                assert not failed and enrolled['state'] == 'armed', enrolled
                checkpoint = await until(lambda v: v['state'] == 'checkpoint_requested')
                with mutex:
                    assert sum(r['method'] == 'turn/steer' for r in requests) == 1
                    goal.update(createdAt=created+1, objective='Replacement same-session goal')
                repeated, failed = await call('wake_goal_limits_set', dict(
                    token_limit=100, time_limit_seconds=300, checkpoint_seconds=299))
                assert not failed and repeated['deadline'] == enrolled['deadline'], repeated
                with rollout.open('a') as stream:
                    stream.write(json.dumps(usage('second', 70)) + '\n')
                stopped = await until(lambda v: v['state'] == 'stopped')
                assert stopped['used_tokens'] == 110 and stopped['stop_proof'] is True, stopped
                with mutex:
                    methods = [r['method'] for r in requests]
                    assert methods.index('turn/steer') < methods.index('thread/goal/set') < methods.index('turn/interrupt')
                    assert goal['status'] == 'paused'
                receipt = dict(verdict='PASS', native_controls='injected_unix_protocol',
                    clock='configured_trusted_clock', model_calls=0, python=sys.executable,
                    watcher_pid=watcher.pid, enrolled=enrolled, checkpoint=checkpoint,
                    stopped=stopped, requests=requests)
                (directory / 'result.json').write_text(json.dumps(receipt, indent=2))
        finally:
            if watcher is not None and watcher.poll() is None:
                watcher.terminate()
                try:
                    watcher.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    watcher.kill(); watcher.wait(); raise
            log.close()
            server.shutdown(); server_thread.join(timeout=2)
    assert watcher.poll() is not None
    print(json.dumps(dict(verdict='PASS', result=str(directory / 'result.json'), watcher_exit=watcher.returncode)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    asyncio.run(qualify(parser.parse_args().output.resolve()))
