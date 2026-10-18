"""Opt-in real Codex idle-goal stop proof; zero model turns or provider calls.

Creates only an owned private app-server and blocked disposable goal. Active-turn
checkpoint/interrupt and live delegated accounting are NOT proven by this script.
"""
import argparse
import json
import os
from pathlib import Path
import signal
import stat
import subprocess
import sys
import time

from codex_wake.native_protocol import native_request


def qualify(base, codex):
    base.mkdir(mode=0o700, parents=True, exist_ok=False)
    home = base / 'home'; home.mkdir(mode=0o700)
    alias = base / 'native.sock'
    environment = dict(os.environ, CODEX_HOME=str(home))
    environment.pop('CODEX_THREAD_ID', None)
    environment.pop('PYTHONPATH', None)
    log = (base / 'native.log').open('w')
    watcher_log = (base / 'watcher.log').open('w')
    native = subprocess.Popen([str(codex), 'app-server', '--listen', 'unix://' + str(alias)],
        env=environment, cwd=base, stdout=log, stderr=log, start_new_session=True)
    watcher = None
    receipt = dict(native_pid=native.pid, model_calls=0, verdict='INCOMPLETE', python=sys.executable)
    try:
        deadline = time.monotonic() + 10
        while not (alias.exists() and stat.S_ISSOCK(alias.stat().st_mode)):
            if native.poll() is not None or time.monotonic() > deadline:
                raise RuntimeError('Owned native app-server startup unavailable')
            time.sleep(.05)
        physical = alias.resolve(strict=True)
        info = physical.lstat()
        assert info.st_uid == os.geteuid() and stat.S_ISSOCK(info.st_mode)
        assert physical.parent.stat().st_uid == os.geteuid() and physical.parent.stat().st_mode & 0o077 == 0
        endpoint = 'unix://' + str(physical)
        def rpc(method, params):
            return native_request(endpoint, str(codex), method, params, 5)
        thread = rpc('thread/start', dict(cwd=str(base), historyMode='legacy', experimentalRawEvents=True))['thread']['id']
        goal = rpc('thread/goal/set', dict(threadId=thread,
            objective='Disposable idle goal resource stop qualification', status='blocked',
            origin='user', tokenBudget=100))['goal']
        root = base / 'runtime'
        policy = base / 'policy.json'
        policy.write_text(json.dumps(dict(version=1, callers={thread: dict(
            app_server=endpoint, codex_path=str(codex), codex_home=str(home),
            allocation_id='explicit-disposable-qualification', max_tokens=100, max_seconds=60, rpc_timeout=2)})))
        policy.chmod(0o600)
        watcher = subprocess.Popen([sys.executable, '-m', 'codex_wake', '--wake-root', str(root),
            'goal-limits', 'watch', '--interval', '0.1'], env=environment,
            stdout=watcher_log, stderr=watcher_log)
        def cli(verb, *extra):
            result = subprocess.run([sys.executable, '-m', 'codex_wake', '--wake-root', str(root),
                'goal-limits', verb, '--policy', str(policy), '--caller-thread-id', thread, '--json', *extra],
                env=environment, capture_output=True, text=True, timeout=15)
            return json.loads(result.stdout)
        deadline = time.monotonic() + 8
        while not cli('show').get('controller', {}).get('fresh'):
            if watcher.poll() is not None or time.monotonic() > deadline:
                raise RuntimeError('Independent watcher unavailable')
            time.sleep(.05)
        # Let the one-second original allowance expire; never activate a model.
        time.sleep(1.1)
        enrolled = cli('set', '--token-limit', '100', '--time-limit-seconds', '1')
        deadline = time.monotonic() + 8
        while True:
            stopped = cli('show')
            if stopped.get('state') == 'stopped':
                break
            if time.monotonic() > deadline:
                raise AssertionError(stopped)
            time.sleep(.05)
        final = rpc('thread/goal/get', dict(threadId=thread))['goal']
        assert final['status'] == 'paused' and stopped['stop_proof'] is True
        assert stopped['used_tokens'] == 0 and stopped['reason'] == 'allocation_exhausted'
        assert any(e['method'] == 'thread/goal/set' and e['state'] == 'acknowledged'
                   for e in stopped['effects'].values())
        receipt.update(verdict='PASS_NATIVE_IDLE_CONTROLLER_STOP', thread_id=thread,
            goal_before=goal, goal_after=final, enrollment=enrolled, stopped=stopped,
            physical_endpoint=endpoint, watcher_pid=watcher.pid)
    finally:
        if watcher is not None and watcher.poll() is None:
            watcher.terminate()
            try: watcher.wait(timeout=8)
            except subprocess.TimeoutExpired: watcher.kill(); watcher.wait(); raise
        if native.poll() is None:
            os.killpg(native.pid, signal.SIGTERM)
            try: native.wait(timeout=5)
            except subprocess.TimeoutExpired: os.killpg(native.pid, signal.SIGKILL); native.wait(); raise
        log.close(); watcher_log.close()
        receipt.update(native_exit=native.returncode,
            native_process_present=Path('/proc', str(native.pid)).exists(),
            watcher_process_present=watcher is not None and Path('/proc', str(watcher.pid)).exists())
        (base / 'result.json').write_text(json.dumps(receipt, indent=2))
    print(json.dumps(dict(verdict=receipt['verdict'], result=str(base / 'result.json'))))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--codex', type=Path, required=True)
    args = parser.parse_args()
    qualify(args.output.resolve(), args.codex.resolve(strict=True))
