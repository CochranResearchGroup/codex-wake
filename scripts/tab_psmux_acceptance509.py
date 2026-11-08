#!/usr/bin/env python3
"""Owned Windows psmux and actual PowerShell acceptance for the finite bridge.

Run with the exact installed prefix's Python. Caller supplies a private output
root and existing native Windows Python path; only a new unique psmux namespace
is created or stopped. No provider, production tabs, or credentials are used.
"""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

from codex_wake.controller_tab_adapters import ConfiguredBridge, PsmuxAttachmentTransport
from codex_wake import tab_psmux_bridge


POWERSHELL = '/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state', type=Path, required=True)
    parser.add_argument('--windows-python', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.state.mkdir(mode=0o700, parents=True, exist_ok=False)
    namespace = 'wake509-' + uuid.uuid4().hex[:12]
    bridge_path = Path(tab_psmux_bridge.__file__).resolve()
    native_bridge = subprocess.check_output(['wslpath', '-w', str(bridge_path)], text=True).strip()
    helper = args.state / 'native_fixture.py'
    helper.write_text('''import json,os,subprocess,sys\nfrom pathlib import Path\np=str(Path(os.environ['LOCALAPPDATA'])/'Microsoft/WinGet/Links/psmux.exe')\na=sys.argv[1]\nnamespace=sys.argv[2]\nif a=='start':\n for session in ('source','holding'):\n  subprocess.run([p,'-L',namespace,'new-session','-d','-s',session,'-n',session+'-anchor','--','cmd.exe','/d','/k'],capture_output=True,check=True,timeout=5)\n print('started')\nelif a=='error':\n subprocess.run([p,'-L',namespace,'send-keys','-t',sys.argv[3],'-l','echo Error: fixture-current-visible-error'],capture_output=True,check=True,timeout=5)\n subprocess.run([p,'-L',namespace,'send-keys','-t',sys.argv[3],'Enter'],capture_output=True,check=True,timeout=5)\n print('marked')\nelif a=='census':\n r=subprocess.run([p,'-L',namespace,'list-sessions','-F','#{session_id}'],capture_output=True,text=True,timeout=5)\n print(json.dumps({'returncode':r.returncode,'sessions':r.stdout.splitlines()}))\nelif a=='stop':\n r=subprocess.run([p,'-L',namespace,'kill-server'],capture_output=True,timeout=5)\n print('stopped',r.returncode)\n''')
    native_helper = subprocess.check_output(['wslpath', '-w', str(helper)], text=True).strip()
    python = args.windows_python
    owned = False
    checks = []
    started = time.monotonic()
    def native(*values):
        return subprocess.check_output([python, native_helper, *values], text=True, timeout=15).strip()
    def invoke(owner, action, arguments):
        return owner.lifecycle(action, arguments, time.monotonic() + 15)
    try:
        native('start', namespace)
        owned = True
        base = [python, native_bridge, '--namespace', namespace, '--session', 'source']
        description = json.loads(subprocess.check_output(base + ['--describe'], text=True, timeout=15))
        identity = description['identity']
        fixed = ['--server-pid', str(identity['pid']), '--server-birth', str(identity['creation_filetime'])]
        bridge = ConfiguredBridge(base + fixed)
        source = PsmuxAttachmentTransport(bridge, generation=description['generation'])
        holding_base = [python, native_bridge, '--namespace', namespace, '--session', 'holding']
        holding_description = json.loads(subprocess.check_output(holding_base + ['--describe'], text=True, timeout=15))
        holding_identity = holding_description['identity']
        holding_command = holding_base + ['--server-pid', str(holding_identity['pid']), '--server-birth', str(holding_identity['creation_filetime'])]
        holding = PsmuxAttachmentTransport(ConfiguredBridge(holding_command), generation=holding_description['generation'])
        initial = source.snapshot(time.monotonic() + 15)
        assert initial['server_identity'] == identity
        assert all(pane['platform'] == 'windows' and pane['windows_creation_filetime'] > 0
                   and pane['windows_processes'] for window in initial['windows'] for pane in window['panes'])
        assert not source.same_server(holding)
        assert identity['pid'] != holding_identity['pid']
        source_session = initial['session_id']
        holding_session = holding.snapshot(time.monotonic() + 15)['session_id']
        assert len(bridge('discover', {}, time.monotonic() + 15)['result']['sessions']) == 2
        checks.append('pinned-native-process-and-session-discovery')
        created = invoke(source, 'create', dict(name='managed-509'))
        wid = created['window_id']
        original = next(w for w in created['snapshot']['windows'] if w['window_id'] == wid)
        renamed = invoke(source, 'rename', dict(window=wid, name='renamed-509'))
        assert next(w for w in renamed['snapshot']['windows'] if w['window_id'] == wid)['name'] == 'renamed-509'
        focused = invoke(source, 'focus', dict(window=wid))
        assert next(w for w in focused['snapshot']['windows'] if w['window_id'] == wid)['focused']
        native('error', namespace, 'source:' + str(original['index']) + '.' + str(original['panes'][0]['pane_index']))
        screen = source.visible_screen(original['panes'][0]['pane_id'], time.monotonic() + 15)
        assert 'fixture-current-visible-error' in screen
        checks.append('create-rename-focus-current-visible-screen')
        from codex_wake.managed_inventory import InventoryError
        try:
            invoke(source, 'park', dict(window=wid, destination_session=holding_session))
            raise AssertionError('native unsupported cross-session move was accepted')
        except InventoryError as error:
            assert error.code == 'unsupported_target'
        preserved = source.snapshot(time.monotonic() + 15)
        assert next(w for w in preserved['windows'] if w['window_id'] == wid)['panes'] == original['panes']
        checks.append('cross-session-movement-explicitly-unsupported-source-preserved')
        # Actual native PowerShell invokes the same finite bridge; no profile or
        # per-process PowerShell census, one bounded process with private stdin.
        command = '''$ErrorActionPreference='Stop'; $r=[Console]::In.ReadToEnd() | ConvertFrom-Json; $body='{"action":"snapshot","arguments":{}}'; $body | & $r.python $r.bridge --namespace $r.namespace --session source --server-pid $r.pid --server-birth $r.birth; if ($LASTEXITCODE -ne 0) {exit $LASTEXITCODE}'''
        encoded = base64.b64encode(command.encode('utf-16-le')).decode()
        payload = json.dumps(dict(python=python.replace('/mnt/c/', 'C:/') if python.startswith('/mnt/c/') else python,
            bridge=native_bridge, namespace=namespace, pid=identity['pid'], birth=str(identity['creation_filetime'])))
        # Convert executable paths with wslpath rather than relying on slash mapping.
        native_python = subprocess.check_output(['wslpath', '-w', python], text=True).strip()
        value = json.loads(payload); value['python'] = native_python
        reply = subprocess.run([POWERSHELL, '-NoLogo', '-NoProfile', '-NonInteractive', '-EncodedCommand', encoded],
            input=json.dumps(value), text=True, capture_output=True, timeout=20, check=True)
        observed = json.loads(reply.stdout.lstrip('\ufeff'))
        assert observed['generation'] == description['generation']
        checks.append('actual-powershell-native-bridge-client')
        unsupported = bridge('lifecycle', dict(action='execute', argv=['never']), time.monotonic() + 15)
        assert unsupported['error']['code'] == 'unsupported_operation'
        wrong = base + ['--server-pid', str(identity['pid']), '--server-birth', str(identity['creation_filetime'] + 1)]
        stale = subprocess.run(wrong, input='{"action":"snapshot","arguments":{}}', text=True, capture_output=True, timeout=15)
        assert json.loads(stale.stdout)['error']['code'] == 'stale_target'
        checks.append('unsupported-action-and-replaced-process-generation-refused')
        closed = invoke(source, 'close', dict(window=wid))
        assert not any(w['window_id'] == wid for w in closed['snapshot']['windows'])
        native('stop', namespace)
        owned = False
        census = json.loads(native('census', namespace))
        assert not census['sessions'], census
        missing = subprocess.run(base + fixed, input='{"action":"snapshot","arguments":{}}', text=True, capture_output=True, timeout=15)
        assert json.loads(missing.stdout).get('error')
        checks.append('owned-namespace-cleanup-and-unavailable-result')
        receipt = dict(status='passed', checks=checks, namespace=namespace,
            identity=identity, bridge_sha256=hashlib.sha256(bridge_path.read_bytes()).hexdigest(),
            bridge_module=str(bridge_path), python=sys.version.split()[0], windows_python=python,
            elapsed_seconds=round(time.monotonic() - started, 3), provider_calls=0,
            native_windows_owner=False, actual_powershell=True, final_owned_namespace=census,
            boundary='Actual native presentation/finite transport; parent public CLI/API/MCP lifecycle integration remains separate.')
        args.output.write_text(json.dumps(receipt, indent=2) + '\n')
        print(json.dumps(dict(status='passed', checks=len(checks), receipt=str(args.output))))
    except Exception as error:
        args.output.write_text(json.dumps(dict(status='failed', namespace=namespace, checks=checks,
            error_type=type(error).__name__, message=str(error), provider_calls=0), indent=2) + '\n')
        raise
    finally:
        if owned:
            native('stop', namespace)


if __name__ == '__main__':
    main()
