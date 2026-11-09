#!/usr/bin/env python3
"""Qualify formatting on a disposable namespace of the installed native psmux.

Runs only explicit owned test namespaces. Never discovers or changes production
sessions, launchers, model processes or themes. Invoke with source PYTHONPATH or
an installed package; receipt records the module hashes actually exercised.
"""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import shutil
import sys
import time
import uuid

from codex_wake import tab_psmux_bridge
from codex_wake.controller_tab_adapters import ConfiguredBridge, PsmuxAttachmentTransport
from codex_wake.controller_tabs import controller_tabs_from_root
from codex_wake.mcp_server import CommandRunner

POWERSHELL='/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state',type=Path,required=True)
    parser.add_argument('--windows-python',required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    args.state.mkdir(mode=0o700,parents=True,exist_ok=False)
    namespace='wake519-'+uuid.uuid4().hex[:12]
    native_directory=Path('/mnt/c/Users/ecoch/AppData/Local/codex-wake-test')/namespace
    native_directory.mkdir(parents=True,exist_ok=False)
    helper=native_directory/'native_fixture.py'
    helper.write_text('''import json,os,subprocess,sys
from pathlib import Path
p=str(Path(os.environ['LOCALAPPDATA'])/'Microsoft/WinGet/Links/psmux.exe')
r=subprocess.run([p,'-L',sys.argv[1],*sys.argv[2:]],capture_output=True,text=True,timeout=8)
print(json.dumps(dict(rc=r.returncode,out=r.stdout,err=r.stderr)))
''')
    def winpath(path):return subprocess.check_output(['wslpath','-w',str(path)],text=True).strip()
    copied_bridge=native_directory/'tab_psmux_bridge.py'
    shutil.copyfile(Path(tab_psmux_bridge.__file__).resolve(),copied_bridge)
    native_helper=winpath(helper);native_bridge=winpath(copied_bridge)
    py=args.windows_python
    def native(*values,check=True):
        r=json.loads(subprocess.check_output([py,native_helper,namespace,*values],text=True,timeout=12))
        if check:assert r['rc']==0,r
        return r
    checks=[];owned=False;started=time.monotonic();identity=None
    try:
        native('new-session','-d','-s','source','-n','manual baseline','--','cmd.exe','/d','/k');owned=True
        native('new-window','-d','-t','source:','-n','inherited peer','--','cmd.exe','/d','/k')
        native('set-option','-w','-t','source:0','window-status-format','original #I: #W')
        base=[py,native_bridge,'--namespace',namespace,'--session','source']
        description=json.loads(subprocess.check_output(base+['--describe'],text=True,timeout=15));identity=description['identity']
        fixed=base+['--server-pid',str(identity['pid']),'--server-birth',str(identity['creation_filetime'])]
        transport=PsmuxAttachmentTransport(ConfiguredBridge(fixed),generation=description['generation'])
        initial=transport.snapshot(time.monotonic()+15)
        windows=initial['windows'];assert len(windows)==2
        originals={w['window_id']:transport.formatting('read',dict(window=w['window_id']),time.monotonic()+15) for w in windows}
        batch=transport.formatting_batch([dict(action='read',window=w['window_id']) for w in windows],time.monotonic()+15)
        assert batch==list(originals.values())
        assert originals[windows[0]['window_id']]['window-status-format']['explicit']
        assert not originals[windows[1]['window_id']]['window-status-format']['explicit']
        checks.append('native-explicit-vs-inherited-baseline-read')
        root=args.state/'wake';root.mkdir(mode=0o700)
        config=root/'controller-tabs.json'
        config.write_text(json.dumps(dict(schema_version=1,workspaces={'work':dict(kind='psmux',bridge_command=fixed,bridge_generation=description['generation'])})))
        config.chmod(0o600)
        def cli(verb):
            r=subprocess.run([sys.executable,'-m','codex_wake.entrypoint','--wake-root',str(root),'tabs','format-'+verb,'--workspace','work'],text=True,capture_output=True,timeout=30)
            assert r.returncode==0,(r.stdout,r.stderr)
            envelope=json.loads(r.stdout)
            return envelope['result']['operation']['result'] if verb not in ('status','inspect') else envelope
        assert cli('enable')['status']=='applied'
        for wid in originals:
            changed=transport.formatting('read',dict(window=wid),time.monotonic()+15)
            assert changed['window-status-format']['value']!=originals[wid]['window-status-format']['value']
        checks.append('wsl-public-cli-applies-native-formatting')
        assert cli('rollback')['status']=='rolled_back'
        for wid,original in originals.items():assert transport.formatting('read',dict(window=wid),time.monotonic()+15)==original
        assert cli('reenable')['status']=='applied'
        # Native PowerShell uses the exact same pinned finite bridge protocol.
        command="""$ErrorActionPreference='Stop';$r=[Console]::In.ReadToEnd()|ConvertFrom-Json;$r.body|& $r.python $r.bridge --namespace $r.namespace --session source --server-pid $r.pid --server-birth $r.birth;if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}"""
        encoded=base64.b64encode(command.encode('utf-16-le')).decode()
        request=dict(python=winpath(py),bridge=native_bridge,namespace=namespace,pid=identity['pid'],birth=str(identity['creation_filetime']),body=json.dumps(dict(action='formatting',arguments=dict(action='read',window=windows[0]['window_id']))))
        reply=subprocess.run([POWERSHELL,'-NoLogo','-NoProfile','-NonInteractive','-EncodedCommand',encoded],input=json.dumps(request),text=True,capture_output=True,timeout=25,check=True)
        observed=json.loads(reply.stdout.lstrip('\ufeff'));assert observed['generation']==description['generation'] and 'result' in observed,observed
        checks.append('actual-powershell-pinned-native-formatting-read')
        command="$ErrorActionPreference='Stop';$r=[Console]::In.ReadToEnd()|ConvertFrom-Json;& wsl.exe --distribution $r.distro --user $r.user --exec /usr/bin/env ('PYTHONPATH='+$r.source) $r.python -m codex_wake.entrypoint --wake-root $r.root tabs format-rollback --workspace work;if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}"
        import pwd
        distro=os.environ.get('WSL_DISTRO_NAME') or 'Ubuntu'
        payload=dict(distro=distro,user=pwd.getpwuid(os.getuid()).pw_name,source=str(Path(tab_psmux_bridge.__file__).resolve().parents[1]),python=sys.executable,root=str(root))
        encoded=base64.b64encode(command.encode('utf-16-le')).decode()
        reply=subprocess.run([POWERSHELL,'-NoLogo','-NoProfile','-NonInteractive','-EncodedCommand',encoded],input=json.dumps(payload),text=True,capture_output=True,timeout=35,check=True)
        value=json.loads(reply.stdout.lstrip('\ufeff'));assert value['result']['operation']['result']['status']=='rolled_back',value
        for wid,original in originals.items():assert transport.formatting('read',dict(window=wid),time.monotonic()+15)==original
        assert cli('reenable')['status']=='applied'
        checks.append('actual-powershell-public-cli-exact-rollback')
        # Native MCP uses existing controller public execution, with exact pins.
        owner=controller_tabs_from_root(root)
        target=owner.execute('tabs.list',{})['resources'][0]['target']
        payload=dict(workspace='work',expected_target=target)
        payload['_request']=dict(operation_id='format-rollback',idempotency_key='format-rollback',correlation_id='format-rollback',binding='fixture',target=target)
        result,failed=CommandRunner(wake_root=root).call('wake_tabs_format_rollback',payload)
        assert not failed and result['result']['operation']['result']['status']=='rolled_back',result
        for wid,original in originals.items():assert transport.formatting('read',dict(window=wid),time.monotonic()+15)==original
        checks.append('public-mcp-exact-original-restoration-and-reenable')
        # Full local listings must be exact after restoring; changing inheritance
        # into an equal explicit value would fail these readbacks.
        final=transport.snapshot(time.monotonic()+15)
        def continuity(snapshot):
            return [(w['window_id'],w['name'],[(p['pid'],p['windows_creation_filetime']) for p in w['panes']]) for w in snapshot['windows']]
        assert continuity(final)==continuity(initial)
        transport.formatting('refresh',{},time.monotonic()+15)
        checks.append('names-pane-process-births-and-peer-continuity')
        # No additional per-window clock for this installed psmux: @ values are
        # in the session store. Native T: expansion allows passive TTL rendering.
        session=transport.formatting('read-session',{},time.monotonic()+15)
        transport.formatting('write-session',dict(values={'@wake-format-clock':'%s','status-interval':'5'}),time.monotonic()+15)
        value=native('display-message','-p','-t','source:','#{?#{>=:#{T:@wake-format-clock},1},STALE,current}')['out'].strip()
        assert value=='STALE',value
        wanted={k:v['value'] if v['explicit'] else None for k,v in session.items()}
        assert transport.formatting('write-session',dict(values=wanted),time.monotonic()+15)==session
        restored=transport.formatting_batch([dict(action='write',window=wid,values={k:v['value'] if v['explicit'] else None for k,v in original.items()}) for wid,original in originals.items()],time.monotonic()+15)
        assert restored==list(originals.values())
        checks.append('native-clock-expression-session-baseline-and-restore')
        checks.append('finite-batch-read-write-readback')
        wrong=fixed[:-1]+[str(identity['creation_filetime']+1)]
        stale=subprocess.run(wrong,input='{"action":"formatting","arguments":{"action":"read-session"}}',text=True,capture_output=True,timeout=15)
        assert json.loads(stale.stdout)['error']['code']=='stale_target'
        checks.append('replaced-server-generation-refused')
        native('kill-server');owned=False
        census=native('list-sessions','-F','#{session_id}',check=False)
        assert not census['out'].strip(),census
        receipt=dict(status='passed',ticket=519,checks=checks,namespace=namespace,identity=identity,
            bridge_sha256=hashlib.sha256(Path(tab_psmux_bridge.__file__).read_bytes()).hexdigest(),
            elapsed_seconds=round(time.monotonic()-started,3),provider_calls=0,production_touched=False,
            actual_powershell=True,final_owned_namespace=census,
            qualification='Installed native psmux and source-exact public WSL CLI/MCP; rendered pixel fidelity and final installed-package HTTP/PowerShell CLI acceptance belong to integrated tickets523/524.')
        args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(receipt,indent=2)+'\n')
        print(json.dumps(dict(status='passed',checks=len(checks),receipt=str(args.output))))
    except Exception as error:
        args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(dict(status='failed',namespace=namespace,checks=checks,error_type=type(error).__name__,message=str(error),provider_calls=0,production_touched=False),indent=2)+'\n');raise
    finally:
        if owned:native('kill-server',check=False)
        shutil.rmtree(native_directory)


if __name__=='__main__':main()
