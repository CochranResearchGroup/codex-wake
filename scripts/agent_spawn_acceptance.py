"""Opt-in owned installed spawn proof. No production peers or shared services."""
from __future__ import annotations

import argparse
import asyncio
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time
import tomllib


def write(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + '\n')
    path.chmod(0o600)


def execute(root, prefix, via_mcp=False):
    root.mkdir(mode=0o700, parents=True, exist_ok=False)
    workspace, home = root / 'workspace', root / 'codex-home'
    workspace.mkdir()
    home.mkdir(mode=0o700)
    config = tomllib.loads((Path.home() / '.codex/config.toml').read_text())
    selected = {k: config[k] for k in ('model', 'model_reasoning_effort', 'model_provider') if k in config}
    (home / 'config.toml').write_text('\n'.join(f'{k} = {json.dumps(v)}' for k, v in selected.items())
        + '\napproval_policy = "never"\nsandbox_mode = "workspace-write"\n'
        + f'\n[projects.{json.dumps(str(workspace))}]\ntrust_level = "trusted"\n')
    (home / 'auth.json').symlink_to(Path.home() / '.codex/auth.json')
    codex = Path(subprocess.check_output(['which', 'codex'], text=True).strip()).resolve()
    socket, endpoint = root / 'tmux.sock', root / 'native.sock'
    session = 'plan0157-owned'
    env = dict(os.environ, CODEX_HOME=str(home))
    caller = os.environ.get('CODEX_THREAD_ID') if via_mcp else None
    if via_mcp and not caller:
        raise RuntimeError('MCP acceptance requires the invoking native thread identity')
    for name in ('CODEX_THREAD_ID', 'TMUX', 'TMUX_PANE', 'CODEX_WAKE_A2A_CAPABILITY',
                 'CODEX_WAKE_A2A_BUS_ROOT', 'CODEX_WAKE_SENDER_RECEIPT_AUTHORITY', 'PYTHONPATH'):
        env.pop(name, None)
    receipt = dict(state='preparing', root=str(root), prefix=str(prefix),
                   codex=str(codex), selected_model=selected, model_turn_limit=1,
                   authority='operator execute Plan0156; bounded disposable Plan0157 proof')
    python = prefix / 'bin/python'
    identity = subprocess.check_output([str(python), '-I', '-c',
        'import codex_wake,hashlib,json,pathlib; p=pathlib.Path(codex_wake.__file__).parent; '
        'print(json.dumps({"module":str(p),"files":{n:hashlib.sha256((p/n).read_bytes()).hexdigest() '
        'for n in ("agent_lifecycle.py","mcp_server.py","sessions_cli.py","cli.py")}}))'], env=env, text=True)
    receipt['installed'] = json.loads(identity)
    write(root / 'state.json', receipt)
    server = None
    started_session = False
    server_log = (root / 'server.log').open('w')
    try:
        server = subprocess.Popen([str(codex), 'app-server', '--listen', 'unix://' + str(endpoint)],
            env=env, stdout=server_log, stderr=subprocess.STDOUT, start_new_session=True)
        receipt['server_pid'] = server.pid
        deadline = time.monotonic() + 15
        while not endpoint.exists() and server.poll() is None and time.monotonic() < deadline:
            time.sleep(.1)
        if server.poll() is not None or not endpoint.exists():
            raise RuntimeError('owned app-server did not expose its socket')
        endpoint = endpoint.resolve()
        subprocess.run(['tmux', '-S', str(socket), 'new-session', '-d', '-s', session,
                        '-n', 'controller', 'sleep 600'], env=env, check=True, timeout=10)
        started_session = True
        clock = json.loads(subprocess.check_output([str(python), '-I', '-c',
            'import json; from codex_wake.native_clock import snapshot; print(json.dumps(snapshot()))'],
            env=env, text=True, timeout=15))
        if not clock.get('utc'):
            raise RuntimeError('admissible UTC unavailable before spawn')
        expiry = datetime.fromtimestamp(clock['utc']['upper'] + 300, UTC).isoformat()
        profiles = root / 'profiles.json'
        write(profiles, dict(version=1, callers={caller: ['worker']} if caller else {},
            profiles=dict(worker=dict(cwd=str(workspace),
            codex_home=str(home), codex_path=str(codex), app_server='unix://' + str(endpoint),
            tmux_session=session, tmux_socket=str(socket), timeout=10))))
        argv = [str(prefix / 'bin/codex-wake'), '--wake-root', str(root / 'wake'), 'sessions', 'spawn',
                '--profiles', str(profiles), '--profile', 'worker', '--intent', 'installed-spawn-01',
                '--name', 'spawn-worker', '--expires-at', expiry, '--task',
                'This is one bounded disposable acceptance assignment. Use the shell to write result.json '
                'in your current directory containing answer 42 and thread_id from your actual native '
                'shell CODEX_THREAD_ID. Then report completion and stop. Do not create goals, messages, '
                'wakes, other agents or change services; do not edit outside this workspace.', '--json']
        if caller:
            argv += ['--caller-thread-id', caller]
        def invoke():
            if not via_mcp:
                return subprocess.run(argv, env=env, capture_output=True, text=True, timeout=45)
            from mcp import Client, StdioServerParameters
            async def call():
                parameters = StdioServerParameters(command=str(prefix / 'bin/codex-wake-mcp'),
                    args=['--cli', str(prefix / 'bin/codex-wake'), '--wake-root', str(root / 'wake'),
                          '--lifecycle-profiles', str(profiles), '--call-timeout', '45'], env=env)
                async with Client(parameters, mode='legacy') as client:
                    value = await client.call_tool('wake_sessions_spawn', dict(profile='worker',
                        intent='installed-spawn-01', name='spawn-worker', expires_at=expiry,
                        task=argv[argv.index('--task') + 1], caller_thread_id=caller))
                    return subprocess.CompletedProcess(argv, 5 if value.is_error else 0,
                                                       value.content[0].text, '')
            return asyncio.run(call())
        receipt.update(state='spawning', expires_at=expiry, argv=argv, interface='MCP' if via_mcp else 'CLI')
        write(root / 'state.json', receipt)
        deadline = time.monotonic() + 240
        for observation in range(60):
            result = invoke()
            write(root / f'observation-{observation:02}.json', dict(returncode=result.returncode,
                  stdout=result.stdout, stderr=result.stderr))
            lifecycle = json.loads(result.stdout)
            receipt['lifecycle'] = lifecycle
            write(root / 'state.json', receipt)
            if lifecycle['state'] == 'completed':
                value = json.loads((workspace / 'result.json').read_text())
                if value != dict(answer=42, thread_id=lifecycle['thread_id']):
                    raise RuntimeError('worker output disagrees with exact native identity')
                duplicate = invoke()
                write(root / 'duplicate-readback.json', dict(returncode=duplicate.returncode,
                      stdout=duplicate.stdout, stderr=duplicate.stderr))
                if json.loads(duplicate.stdout)['submission_id'] != lifecycle['submission_id']:
                    raise RuntimeError('duplicate intent changed its native submission')
                receipt.update(state='passed', result=value)
                break
            uncertain_submission = (lifecycle['state'] == 'uncertain' and lifecycle.get('submission_id'))
            if lifecycle['state'] in ('blocked', 'expired') or (lifecycle['state'] == 'uncertain' and not uncertain_submission):
                raise RuntimeError('lifecycle held: ' + lifecycle.get('reason', lifecycle['state']))
            if time.monotonic() >= deadline:
                raise RuntimeError('bounded spawn observation elapsed')
            time.sleep(1)
        else:
            raise RuntimeError('spawn observation count exhausted')
    except Exception as exc:
        receipt.update(state='failed', error=str(exc))
    finally:
        if started_session:
            subprocess.run(['tmux', '-S', str(socket), 'kill-session', '-t', session], env=env,
                           check=False, capture_output=True, timeout=10)
        if server is not None and server.poll() is None:
            os.killpg(server.pid, signal.SIGTERM)
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                # Codex can finish draining after the initial shutdown window.
                # Preserve that delay and still produce an OS cleanup receipt.
                receipt['shutdown_first_wait'] = 'timed_out'
                try:
                    server.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    receipt['shutdown_second_wait'] = 'timed_out'
        server_log.close()
        remaining = []
        for process in Path('/proc').iterdir():
            if not process.name.isdigit():
                continue
            try:
                variables = (process / 'environ').read_bytes().split(b'\0')
                if ('CODEX_HOME=' + str(home)).encode() in variables:
                    remaining.append(int(process.name))
            except (FileNotFoundError, PermissionError, ProcessLookupError):
                continue
        receipt['remaining_private_processes'] = remaining
        if remaining:
            receipt.update(state='failed', cleanup_error='private processes remain')
        write(root / 'state.json', receipt)
    print(json.dumps({k: receipt.get(k) for k in ('state', 'error', 'remaining_private_processes', 'root')}))
    return 0 if receipt['state'] == 'passed' else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true', required=True)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--prefix', type=Path, required=True)
    parser.add_argument('--via-mcp', action='store_true')
    args = parser.parse_args()
    raise SystemExit(execute(args.root.resolve(), args.prefix.resolve(), args.via_mcp))
