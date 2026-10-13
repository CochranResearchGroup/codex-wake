"""Provider-free qualification of recorded sandbox/host lifecycle observation boundaries."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile


def execute(rollout, receipt_path):
    context = next(json.loads(line)['payload'] for line in rollout.read_text().splitlines()
                   if json.loads(line)['type'] == 'turn_context')
    workspace = Path(context['cwd'])
    state = dict(permissionProfile=context['permission_profile'], sandboxCwd=workspace.as_uri())
    result = dict(model_assignments=0, permission_profile_sha256=hashlib.sha256(
        json.dumps(state, sort_keys=True).encode()).hexdigest(), workspace=str(workspace))
    daemon_dir = Path('/tmp') / ('codex-daemon-' + str(os.getuid()))
    # Create only our disposable socket; never touch existing native endpoints.
    with tempfile.TemporaryDirectory(prefix='plan156-transport-', dir=daemon_dir) as tmp:
        path = Path(tmp) / 'native.sock'
        with socket.socket(socket.AF_UNIX) as listener:
            listener.bind(str(path)); listener.listen(1)
            probe = 'import os,socket,sys; p=sys.argv[1]; os.lstat(p); s=socket.socket(socket.AF_UNIX); s.connect(p); print("connected")'
            host = subprocess.run(['python3', '-c', probe, str(path)], capture_output=True, text=True, timeout=10)
            child = subprocess.run(['codex', 'sandbox', '--sandbox-state-json', json.dumps(state),
                                    'python3', '-c', probe, str(path)], capture_output=True, text=True, timeout=10)
            result['socket'] = dict(host_exit=host.returncode, sandbox_exit=child.returncode,
                                    sandbox_permission_denied='PermissionError' in child.stderr)
    with tempfile.TemporaryDirectory(prefix='plan156-observation-', dir=workspace.parent.parent) as tmp:
        path = Path(tmp) / 'host-observation.json'
        path.write_text(json.dumps(dict(source_thread_id='source', successor_thread_id='successor', state='passed')))
        probe = ("import json,pathlib,sys; p=pathlib.Path(sys.argv[1]); d=json.loads(p.read_text()); "
                 "assert d['source_thread_id']=='source' and d['successor_thread_id']=='successor' and d['state']=='passed'; "
                 "print('host_read_verified');\ntry:p.write_text('{}')\n"
                 "except OSError as e:assert e.errno in (1,13,30);print('host_write_denied')\n"
                 "else:raise AssertionError('sandbox can forge host evidence')")
        child = subprocess.run(['codex', 'sandbox', '--sandbox-state-json', json.dumps(state),
                                'python3', '-c', probe, str(path)], capture_output=True, text=True, timeout=10)
        result['observation_bridge'] = dict(exit_code=child.returncode,
            read_verified='host_read_verified' in child.stdout, write_denied='host_write_denied' in child.stdout)
    result['state'] = 'passed' if (result['socket'] == dict(host_exit=0, sandbox_exit=1, sandbox_permission_denied=True)
        and result['observation_bridge'] == dict(exit_code=0, read_verified=True, write_denied=True)) else 'failed'
    if receipt_path: receipt_path.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
    return 0 if result['state'] == 'passed' else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--rollout', type=Path, required=True)
    parser.add_argument('--receipt', type=Path)
    args = parser.parse_args()
    if not args.execute: parser.error('--execute required for owned temporary socket and sandbox probes')
    raise SystemExit(execute(args.rollout, args.receipt))
