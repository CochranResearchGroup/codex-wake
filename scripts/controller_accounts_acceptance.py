#!/usr/bin/env python3
"""Installed, provider-free account/configuration acceptance (all state temporary)."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import select
import subprocess
import tempfile

from codex_wake.mcp_server import CommandRunner

parser = argparse.ArgumentParser()
parser.add_argument('--bin-dir', type=Path, required=True)
args = parser.parse_args()
with tempfile.TemporaryDirectory(prefix='wake-accounts-acceptance-') as directory:
    root = Path(directory)
    state = root / 'homes'
    for name in ('alice', 'bob'):
        home = state / ('codex-' + name)
        home.mkdir(parents=True)
        (home / 'auth.json').write_text(json.dumps({'synthetic_account': name}))
    executable = root / 'fixture'
    executable.write_text('#!' + str(args.bin_dir / 'python') + '\n'
        'import json,os,sys\nprint(json.dumps({"account":os.environ["CODEX_PROFILE_NAME"],"home":os.environ["CODEX_HOME"],"args":sys.argv[1:]}),flush=True)\nsys.stdin.readline()\n')
    executable.chmod(0o700)
    manifest = root / 'builds.json'
    manifest.write_text(json.dumps({'schema_version': 1, 'builds': {'stock': {
        'executable': str(executable), 'sha256': hashlib.sha256(executable.read_bytes()).hexdigest(),
        'upstream_version': '0.164.0', 'revision': 'fixture', 'read_schemas': [5],
        'source': 'https://github.com/openai/codex/releases/download/rust-v0.164.0/codex'}}}))
    config = root / 'controller-accounts.toml'
    config.write_text(f'''[profiles]
state_root="{state}"
source_root="{root / 'seed'}"
known_profiles=["alice","bob"]
check_upstream_releases=false
[profiles.aliases]
work="alice"
[configuration.base]
model="base"
[configuration.account.codex-alice]
model="account"
''')
    env = dict(os.environ, CODEX_WAKE_ACCOUNTS_CONFIG=str(config), CODEX_BUILD_MANIFEST=str(manifest))
    env.pop('PYTHONPATH', None)
    def invoke(*command):
        result = subprocess.run([str(args.bin_dir / command[0]), *command[1:]],
            env=env, text=True, capture_output=True, timeout=10)
        assert result.returncode == 0, result.stderr
        return json.loads(result.stdout)
    cli = invoke('codex-wake', '--wake-root', str(root), 'accounts', 'resolve', 'work', '--json')
    mcp, failed = CommandRunner(wake_root=root).call('wake_controller_account_resolve', {'selector': 'work'})
    assert not failed and cli == mcp
    explain = invoke('codex-wake', '--wake-root', str(root), 'configuration', 'explain', 'work', '--json')
    assert explain['result']['effective']['model'] == 'account'
    assert explain['result']['provenance']['model'] == 'account:codex-alice'
    children = []
    def start(name):
        process = subprocess.Popen([str(args.bin_dir / 'codex-stock'), name], env=env,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        children.append(process)
        assert select.select([process.stdout], [], [], 5)[0], 'fixture startup timeout'
        line = process.stdout.readline()
        assert line, process.stderr.read()
        record = json.loads(line)
        assert record['account'] == 'codex-' + ('alice' if name == 'work' else name)
        return process, record
    try:
        alice, first = start('work')
        bob, second = start('bob')
        assert first['home'] != second['home']
        assert '"model"="account"' in first['args']
        assert '"model"="base"' in second['args']
        alice.communicate('stop\n', timeout=5)
        restarted, _ = start('work')
        assert bob.poll() is None
        restarted.communicate('stop\n', timeout=5)
        bob.communicate('stop\n', timeout=5)
        assert all(child.returncode == 0 for child in children)
    finally:
        for child in children:
            if child.poll() is None:
                child.kill()
            child.communicate(timeout=5)
    for name in ('alice', 'bob'):
        assert json.loads((state / ('codex-' + name) / 'auth.json').read_text()) == {'synthetic_account': name}
    print(json.dumps({'status': 'passed', 'package': 'codex-wake', 'provider_calls': 0,
        'cli_mcp_parity': True, 'concurrent_accounts': True, 'restart_preserved_peer': True,
        'credential_files_unchanged': True, 'production_activation': False}))
