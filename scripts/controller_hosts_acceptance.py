#!/usr/bin/env python3
"""Installed synthetic SSH-shaped transport qualification, not a real SSH/OS matrix."""
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import time


def main():
    import codex_wake
    from codex_wake.managed_inventory import ManagedInventory, Observation
    env = dict(os.environ); env.pop('PYTHONPATH', None)
    with tempfile.TemporaryDirectory(prefix='wake-host400-') as directory:
        base = Path(directory)
        source, remote = base / 'source', base / 'remote'
        def cli(root, *args, expected=0):
            result = subprocess.run([sys.executable, '-m', 'codex_wake.host_commands', '--wake-root', str(root), 'hosts', *args], env=env, cwd=base, text=True, capture_output=True, timeout=20)
            assert result.returncode == expected, (result.returncode, result.stdout, result.stderr)
            return json.loads(result.stdout)
        destination = cli(remote, 'register', 'synthetic-host', 'synthetic-wsl', '--kind', 'wsl', '--authority', 'synthetic-authority', '--destination', 'synthetic-fixture')['result']['environment']
        target = destination['target']
        inventory = ManagedInventory(remote)
        for account in ('alice', 'bob'):
            inventory.enroll(Observation('codex', 'account:' + account, account, '/synthetic', 'ready', time.time(), 'native_metadata', {'pid': 123, 'start_ticks': 42, 'boot_id': 'synthetic'}, [], {}), operator=True)
        mapping = cli(remote, 'map-principal', 'fixed-key', '--subject', 'synthetic-service', '--scope', 'observe', '--targets', json.dumps([{'host': target['host'], 'environment': target['environment'], 'namespace': 'account:alice'}]), '--expires-at', str(time.time() + 600))
        assert mapping['result']['subject'] == 'synthetic-service'
        log, mode = base / 'fixture.calls', base / 'fixture.mode'
        mode.write_text('normal')
        fixture = base / 'synthetic-ssh'
        fixture.write_text('#!' + sys.executable + '\n' + '''import json, os, pathlib, shlex, subprocess, sys
assert sys.argv[1:6] == ['-T', '-oBatchMode=yes', '-oConnectTimeout=5', '-oStrictHostKeyChecking=yes', '--']
assert sys.argv[-2] == 'synthetic-fixture'
with open(''' + repr(str(log)) + ''', 'a') as stream: stream.write('synthetic SSH-shaped subprocess\\n')
mode = pathlib.Path(''' + repr(str(mode)) + ''').read_text()
result = subprocess.run(shlex.split(sys.argv[-1]), input=sys.stdin.buffer.read(65537), capture_output=True)
if mode == 'disconnect': sys.exit(255)
sys.stdout.buffer.write(result.stdout)
sys.exit(result.returncode)
''')
        fixture.chmod(0o700)
        receiver_command = shlex.join([sys.executable, '-m', 'codex_wake.host_commands', '--wake-root', str(remote), 'hosts', 'ssh-serve', '--principal-id', 'fixed-key', '--target', json.dumps(target)])
        source_row = cli(source, 'register', target['host'], target['environment'], '--kind', 'wsl', '--authority', target['authority'], '--generation', target['generation'], '--destination', 'synthetic-fixture', '--ssh-executable', str(fixture), '--command', receiver_command)['result']['environment']
        assert source_row['target'] == target
        windows = cli(source, 'register', target['host'], 'synthetic-windows', '--kind', 'windows', '--authority', 'synthetic-windows-authority', '--destination', 'synthetic-fixture')['result']['environment']
        fleet = cli(source, 'list')['result']['environments']
        assert len(fleet) == 2 and {r['kind'] for r in fleet} == {'windows', 'wsl'}
        def route(key, operation='inventory.list', pinned=target, expected=0):
            return cli(source, 'route', '--target', json.dumps(pinned), '--operation', operation, '--operation-id', 'operation-' + key, '--idempotency-key', key, expected=expected)
        original = route('first')['result']['route']
        assert (original['execution'], original['delivery'], original['effect']) == ('completed', 'received', 'none_read_only')
        result = original['result']
        assert result['actor']['subject'] == 'synthetic-service'
        assert [r['target']['namespace'] for r in result['result']['resources']] == ['account:alice']
        count = len(log.read_text().splitlines())
        assert route('first')['result']['route'] == original
        assert len(log.read_text().splitlines()) == count
        assert route('bad-mutation', 'runtime.input', expected=2)['error']['code'] == 'unsupported_operation'
        assert route('stale', pinned=dict(target, generation='replaced-generation'), expected=2)['error']['code'] == 'stale_target'
        assert len(log.read_text().splitlines()) == count
        mode.write_text('disconnect')
        uncertain = route('disconnect')['result']['route']
        assert uncertain['execution'] == 'unknown' and uncertain['delivery'] == 'uncertain'
        count = len(log.read_text().splitlines())
        mode.write_text('normal')
        # New CLI processes are the restart/reconnect boundary; durable admission
        # returns the original uncertain result without executing the transport.
        assert route('disconnect')['result']['route'] == uncertain
        assert len(log.read_text().splitlines()) == count
        cli(source, 'observe', '--target', json.dumps(target), '--online', 'false')
        assert route('offline', expected=2)['error']['code'] == 'offline_target'
        assert len(log.read_text().splitlines()) == count
        cli(source, 'observe', '--target', json.dumps(target), '--online', 'true')
        cli(remote, 'revoke-principal', 'fixed-key')
        denied = route('revoked')['result']['route']
        assert denied['execution'] == 'failed' and denied['result']['error']['code'] == 'invalid_token'
        print(json.dumps(dict(status='passed', package=codex_wake.__file__, python=sys.executable,
            command=[sys.executable, '-m', 'codex_wake.host_commands', '--wake-root', '<private-disposable-root>', 'hosts'],
            transport='synthetic executable emulating OpenSSH argv and invoking the installed fixed-principal receiver; no SSH server or real Windows/WSL host',
            checks=['separate host/environment/authority IDs', 'explicit imported authority generation', 'installed mapped-principal read and target filtering', 'durable same-key delivery without replay', 'unsupported mutation and stale generation before transport', 'uncertain disconnect/restart without replay', 'offline refusal without queue', 'revoked SSH mapping refuses read'],
            source_sha256={name: hashlib.sha256((Path(codex_wake.__file__).parent / name).read_bytes()).hexdigest() for name in ('controller_hosts.py', 'host_commands.py')},
            production_effects=False, provider_credentials=False, real_crossplatform_matrix=False), sort_keys=True))


if __name__ == '__main__': main()
