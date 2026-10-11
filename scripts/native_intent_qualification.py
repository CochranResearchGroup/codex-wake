"""Opt-in installed CLI/worker proof using an isolated clock and queue fixture.

No live recipient, service, global install, guest clock or production root is
used. The native runtime/clock boundaries are explicitly injected; acceptance
is queue-fixture acceptance, not proof of a completed model turn.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time

THREAD = 'c357309d-c209-4467-b757-e1488e6b1aaa'

WRAPPER = '''import json, os, runpy, sys
from pathlib import Path
from unittest.mock import patch
import codex_wake
import codex_wake.native_delivery as delivery
prefix = Path(os.environ['WAKE_FIXTURE_PREFIX']).resolve()
assert Path(codex_wake.__file__).resolve().is_relative_to(prefix)
def clock():
    return json.loads(Path(os.environ['WAKE_FIXTURE_CLOCK']).read_text())
command = sys.argv.pop(1)
sys.argv[0] = str(prefix / 'bin' / command)
original_replace = delivery.replace_record
def replace(root, found, record):
    if os.environ.get('WAKE_FIXTURE_CRASH_AFTER_ACCEPTANCE') and record['status'] == 'submitted':
        os._exit(73)
    return original_replace(root, found, record)
def request(endpoint, codex, method, params, timeout):
    return {'data': [], 'nextCursor': None} if method == 'thread/queue/list' else {'thread': {'id': os.environ['WAKE_FIXTURE_THREAD'], 'turns': []}}
with patch('codex_wake.native_clock.snapshot', side_effect=clock), patch('codex_wake.native_delivery.read_native_thread', return_value={'id': os.environ['WAKE_FIXTURE_THREAD'], 'status': {'type': 'idle'}}), patch('codex_wake.native_delivery.replace_record', side_effect=replace), patch('codex_wake.native_delivery.native_request', side_effect=request):
    runpy.run_path(sys.argv[0], run_name='__main__')
'''

QUEUE = '''#!/usr/bin/env python3
import os, sys
assert sys.argv[1] == 'queue'
thread = sys.argv[sys.argv.index('--thread') + 1]
assert thread == os.environ['WAKE_FIXTURE_THREAD']
with open(os.environ['WAKE_FIXTURE_EFFECTS'], 'a') as stream:
    stream.write('accepted\\n')
print('Queued message c357309d-c209-4467-b757-e1488e6b1bbb for thread ' + thread + '.')
'''


def qualify(prefix, legacy_python=None):
    prefix = Path(prefix).resolve()
    python = prefix / 'bin' / 'python'
    assert python.is_file() and (prefix / 'bin' / 'codex-waked').is_file()
    with tempfile.TemporaryDirectory(prefix='wake-intent-qualified-') as directory:
        base = Path(directory)
        root = base / 'wake'
        wrapper, queue, clock, effects = (base / name for name in ('entry.py', 'codex', 'clock.json', 'effects'))
        wrapper.write_text(WRAPPER)
        queue.write_text(QUEUE)
        queue.chmod(0o700)
        env = dict(os.environ, CODEX_WAKE_STABLE_TIME_CONFIG='', XDG_STATE_HOME=str(base / 'state'),
                   XDG_CONFIG_HOME=str(base / 'config'), WAKE_FIXTURE_PREFIX=str(prefix),
                   WAKE_FIXTURE_CLOCK=str(clock), WAKE_FIXTURE_THREAD=THREAD, WAKE_FIXTURE_EFFECTS=str(effects))
        env.pop('PYTHONPATH', None)
        env.pop('CODEX_THREAD_ID', None)
        anchor = {'epoch': 'fixture-epoch-a', 'counter': 1000000, 'frequency': 1000, 'rate_ppm': 5000}
        clock.write_text(json.dumps({'utc': None, 'counter': anchor, 'reason': 'uncertainty_exceeded'}))
        create = [str(python), str(wrapper), 'codex-wake', '--wake-root', str(root), 'native', 'after',
                  '--json', '--idempotency-key', 'qualified-original', '--ttl', '10m',
                  '--codex-path', str(queue), THREAD, '3h', '--', 'Inspect fixture outcome']
        children = [subprocess.Popen(create, env=env, cwd=base, stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE, text=True) for _ in range(2)]
        receipts = []
        for child in children:
            stdout, stderr = child.communicate(timeout=20)
            assert child.returncode == 0, (child.returncode, stderr)
            receipts.append(json.loads(stdout))
        assert receipts[0]['id'] == receipts[1]['id']
        assert sorted(item['deduplicated'] for item in receipts) == [False, True]
        rollback_held = None
        if legacy_python:
            path = Path(receipts[0]['path'])
            before = path.read_bytes()
            old = subprocess.run([str(Path(legacy_python).parent / 'codex-waked'), '--once',
                                  '--no-dispatch', '--wake-root', str(root)],
                                 env=env, cwd=base, capture_output=True, text=True, timeout=20)
            assert old.returncode == 0, old.stderr
            assert path.read_bytes() == before and not effects.exists()
            rollback_held = True

        def command(name, *args):
            result = subprocess.run([str(python), str(wrapper), name, '--wake-root', str(root), *args],
                                    env=env, cwd=base, capture_output=True, text=True, timeout=20)
            assert result.returncode == 0, (result.returncode, result.stderr)
            return result.stdout

        clock.write_text(json.dumps({'utc': None, 'counter': None, 'reason': 'outage'}))
        command('codex-waked', '--once')
        status = json.loads(command('codex-wake', 'status', '--json'))
        assert status['counts_by_time_recovery_state'] == {'pending_time': 1}
        assert not effects.exists()
        clock.write_text(json.dumps({'utc': None, 'counter': dict(anchor, counter=11855010)}))
        command('codex-waked', '--once')
        command('codex-waked', '--once')
        records = json.loads(command('codex-wake', 'list', '--json'))
        assert len(records) == 1 and records[0]['status'] == 'submitted'
        assert records[0]['attempts'] == 1 and records[0]['native_delivery']['accepted_at'] is None
        assert effects.read_text().splitlines() == ['accepted']
        retry = subprocess.run(create, env=env, cwd=base, capture_output=True, text=True, timeout=20)
        assert retry.returncode == 0 and json.loads(retry.stdout)['deduplicated'] is True
        # A compatible persistent worker must advertise its live process identity.
        loop = subprocess.Popen([str(python), str(wrapper), 'codex-waked', '--wake-root', str(root),
                                 '--interval', '0.1'], env=env, cwd=base,
                                stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        try:
            deadline = time.monotonic() + 5
            reader = None
            while time.monotonic() < deadline:
                probe = subprocess.run([str(python), '-c',
                    "import json,sys; from codex_wake.signal_records import probe_managed_reader_capability; r=probe_managed_reader_capability(__import__('pathlib').Path(sys.argv[1])); print(json.dumps({'pid':r.pid,'versions':sorted(r.schema_versions)} if r else None))", str(root)],
                    env=env, cwd=base, capture_output=True, text=True, timeout=2)
                assert probe.returncode == 0, probe.stderr
                reader = json.loads(probe.stdout)
                if reader:
                    break
            assert reader and reader['pid'] == loop.pid and 6 in reader['versions']
            checked = create[:create.index('--json')] + ['--require-monitor'] + create[create.index('--json'):]
            monitored = subprocess.run(checked, env=env, cwd=base, capture_output=True, text=True, timeout=20)
            assert monitored.returncode == 0 and json.loads(monitored.stdout)['deduplicated'] is True, monitored.stderr
            assert effects.read_text().splitlines() == ['accepted']
        finally:
            loop.terminate()
            loop.communicate(timeout=5)
        # Kill a separate worker after the queue effect, before its acceptance
        # publication. A fresh worker must reconcile the durable uncertain nonce.
        crash_root = base / 'crash-wake'
        clock.write_text(json.dumps({'utc': None, 'counter': anchor}))
        crash_create = list(create)
        crash_create[crash_create.index(str(root))] = str(crash_root)
        created = subprocess.run(crash_create, env=env, cwd=base, capture_output=True, text=True, timeout=20)
        assert created.returncode == 0, created.stderr
        clock.write_text(json.dumps({'utc': None, 'counter': dict(anchor, counter=11855010)}))
        crash_command = [str(python), str(wrapper), 'codex-waked', '--wake-root', str(crash_root), '--once']
        crashed = subprocess.run(crash_command, env=dict(env, WAKE_FIXTURE_CRASH_AFTER_ACCEPTANCE='1'),
                                 cwd=base, capture_output=True, text=True, timeout=20)
        assert crashed.returncode == 73 and len(effects.read_text().splitlines()) == 2
        clock.write_text(json.dumps({'utc': None, 'counter': None, 'reason': 'outage'}))
        recovered = subprocess.run(crash_command, env=env, cwd=base, capture_output=True, text=True, timeout=20)
        assert recovered.returncode == 0 and len(effects.read_text().splitlines()) == 2
        crashed_record = json.loads(Path(json.loads(created.stdout)['path']).read_text())
        assert crashed_record['attempts'] == 1 and crashed_record['native_delivery']['state'] == 'uncertain'
        return {'verdict': 'PASS', 'scope': 'installed_clock_and_native_queue_fixtures',
                'prefix': str(prefix), 'concurrent_creators': 2, 'retained_records': 1,
                'fresh_worker_processes': 6, 'fixture_queue_acceptances': 2,
                'recovery_chain_successors': 1, 'separate_crashed_request_acceptances': 1,
                'crash_replay_count': 0,
                'live_worker_schema6': True, 'owned_loop_worker_stopped': True,
                'legacy_worker_held_record_unchanged': rollback_held,
                'production_wakes': 0, 'global_install_changes': 0,
                'completed_model_turns': 0, 'wake_id': records[0]['id'],
                'qualification_script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prefix', required=True, type=Path)
    parser.add_argument('--receipt', required=True, type=Path)
    parser.add_argument('--legacy-python', type=Path)
    args = parser.parse_args()
    receipt = qualify(args.prefix, args.legacy_python)
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
    print(json.dumps(receipt, sort_keys=True))


if __name__ == '__main__':
    main()
