#!/usr/bin/env python3
"""FOCUSED installed terminal-session acceptance in private native namespaces."""
import argparse
import asyncio
import base64
import hashlib
import json
import os
from pathlib import Path
import socket
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
import zipfile
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def unwrap(value):
    while isinstance(value, dict):
        if isinstance(value.get('result'), dict): value=value['result']
        elif isinstance(value.get('operation'), dict): value=value['operation']
        else: break
    return value


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--wheel', type=Path, required=True)
    platform=parser.add_mutually_exclusive_group(required=True)
    platform.add_argument('--windows-python')
    platform.add_argument('--wsl-only', action='store_true',
        help='Qualify WSL CLI/stdio/API/OAuth only; record Windows as not run.')
    args=parser.parse_args();os.umask(0o077);started=time.monotonic()
    import codex_wake
    prefix=Path(sys.prefix).resolve();package=Path(codex_wake.__file__).resolve().parent
    assert package.is_relative_to(prefix) and not os.environ.get('PYTHONPATH')
    env=dict(os.environ);env.pop('PYTHONPATH',None)
    cli=str(prefix/'bin/codex-wake');checks=[];server=None;windows=None;report={}
    with zipfile.ZipFile(args.wheel) as wheel:
        members=[n for n in wheel.namelist() if n.endswith('.py')]
        for name in members:assert (package.parent/name).read_bytes()==wheel.read(name),name
    with tempfile.TemporaryDirectory(prefix='wake-session534-') as directory:
        root=Path(directory)/'wake';root.mkdir(mode=0o700);sock=str(Path(directory)/'owned.sock')
        def tmux(*argv,check=True):
            return subprocess.run(['tmux','-S',sock,*argv],text=True,capture_output=True,timeout=8,check=check).stdout.strip()
        tmux('new-session','-d','-s','peer','-n','peer','exec sleep 600')
        tmux('set-option','-g','automatic-rename','off')
        config=root/'controller-tabs.json';config.write_text(json.dumps(dict(schema_version=1,workspaces=dict(peer=dict(kind='tmux',socket_path=sock,session_id='$0')))));config.chmod(0o600)
        def command(*argv,expected=0):
            if argv and argv[0] == 'tabs' and '--json' not in argv:
                argv = (*argv, '--json')
            p=subprocess.run([cli,'--wake-root',str(root),*argv],env=env,cwd=directory,text=True,capture_output=True,timeout=30)
            assert p.returncode==expected,(argv,p.returncode,p.stdout,p.stderr)
            return json.loads(p.stdout)
        def local(operation,arguments=None,expected=0):
            family,verb=operation.rsplit('.',1);family=family.rsplit('.',1)[1]
            return unwrap(command('tabs','sessions' if family=='session' else 'routing' if family=='route' else family,verb,'--json','--arguments',json.dumps(arguments or {}),expected=expected))
        def target():return local('tabs.session.list')['target']
        def request(arguments):
            pin=target();key='session534-'+uuid.uuid4().hex
            return dict(arguments,expected_target=pin,_request=dict(operation_id=key,idempotency_key=key,correlation_id=key,binding='private-534',target=pin))
        def births(name):
            rows=tmux('list-panes','-s','-t',name,'-F','#{pane_id}:#{pane_pid}').splitlines()
            return sorted((row,Path('/proc/'+row.split(':')[1]+'/stat').read_text().rsplit(')',1)[1].split()[19]) for row in rows)

        peer=births('peer')
        try:
            from codex_wake.completion import candidates
            for family,verbs in (('sessions',{'create','list','show','update','open','delete','ensure'}),('relocate',{'preview','apply','status','undo'}),('routing',{'save','enable','pin','unpin','hold','resume'})):
                help_text=subprocess.check_output([cli,'tabs',family,'--help'],env=env,text=True)
                assert all(verb in help_text for verb in verbs)
                assert verbs<=set(candidates(['tabs',family,''],2)),family
            for shell in ('bash','zsh'):
                assert 'codex-wake' in subprocess.check_output([cli,'completion',shell],env=env,text=True)
            checks.append('installed-generated-help-session-relocation-routing-and-bash-zsh-completion')
            source=local('tabs.session.create',dict(name='source',server=sock))['session'];assert source['state']=='empty'
            assert local('tabs.session.open',dict(session='source'))['session']['state']=='running'
            first=births('source');sid=source['id']
            changed=local('tabs.session.update',dict(session='source',changes=dict(name='workers',description='inert fixture',labels=['automation'],defaults=dict(cwd=directory,argv=['/bin/sleep','600']))))['session']
            assert changed['id']==sid and births('workers')==first
            # Saved defaults are resolved by the installed public tabs.create path.
            made=unwrap(command('tabs','create','--session',sock+'::workers','--name','inert-worker','--json'))
            assert made['status']=='applied',made
            assert directory in tmux('list-panes','-s','-t','workers','-F','#{pane_current_path}')
            checks.append('installed-cli-empty-open-rename-defaults-new-tab-existing-process-preserved')
            destination=local('tabs.session.create',dict(name='destination',server=sock))['session']
            before=births('workers')
            from codex_wake.tab_views import TabViews
            resources=command('tabs','list')['resources']
            member=next(r for r in resources if r['target']['workspace']==changed['workspace'])
            command('tabs','group-save','--arguments',json.dumps(dict(name='acceptance-category',members=[TabViews.identity(member)['id']],labels=['automation'])))
            for flag,value in (('--tab',sock+'::workers:'+member['window']['window_id']),('--group','acceptance-category'),('--label','automation')):
                preview=unwrap(command('tabs','relocate','preview','--destination',sock+'::destination',flag,value,'--json'))
                assert len(preview['outcomes'])==1,(flag,preview)
            checks.append('installed-human-explicit-tab-group-custom-label-frozen-selection')
            plan=local('tabs.relocate.preview',dict(session='workers',destination='destination'))
            moved=local('tabs.relocate.apply',dict(plan_id=plan['plan_id']))
            assert moved['status']=='completed' and all(x['status']=='moved' for x in moved['outcomes']),moved
            assert local('tabs.session.show',dict(session='workers'))['session']['state']=='empty'
            assert births('destination')==before
            assert local('tabs.relocate.apply',dict(plan_id=plan['plan_id']))['receipt_id']==moved['receipt_id']
            undone=local('tabs.relocate.undo',dict(receipt_id=moved['receipt_id']))
            assert all(x['status']=='undone' for x in undone['outcomes']),undone
            assert births('workers')==before
            selection={'field':'harness','unknown':True}
            for verb in ('pin','hold','resume','unpin'):local('tabs.route.'+verb,dict(selection=selection))
            rule=local('tabs.route.save',dict(name='retired-target',destination='workers',selection={'tabs':[]},stability_seconds=0))['rule']
            local('tabs.route.enable',dict(rule_id=rule['id']))
            assert command('tabs','monitor-status')['monitor']['status']=='running'
            local('tabs.route.pause',dict(rule_id=rule['id']))
            drained=local('tabs.session.delete',dict(session='workers',destination='destination'))
            assert drained['status']=='deleted' and births('destination')==before,drained
            retired=next(r for r in local('tabs.route.list')['rules'] if r['id']==rule['id'])
            assert not retired['enabled'] and retired['disabled_reason']=='destination_deleted',retired
            replacement=local('tabs.session.create',dict(name='workers',server=sock))['session'];assert replacement['id']!=sid
            local('tabs.session.delete',dict(session='workers'))
            assert local('tabs.session.delete',dict(session='destination',terminate=True))['status']=='deleted'
            checks.append('frozen-bulk-idempotent-apply-exact-pane-continuity-undo-holds-routing-monitor-drain-terminate-retired-rules-name-reuse')
            # Native external movement between preview and apply yields a partial
            # batch; retry/undo honors changed placement rather than stealing it.
            for name in ('partial','other','sink'):local('tabs.session.create',dict(name=name,server=sock,start=True))
            tmux('new-window','-d','-t','partial','exec sleep 600')
            plan=local('tabs.relocate.preview',dict(session='partial',destination='sink'))
            second=plan['outcomes'][1]['birth']['window_id'];tmux('move-window','-d','-s',second,'-t','other:')
            partial=local('tabs.relocate.apply',dict(plan_id=plan['plan_id']),expected=3)
            assert partial['status']=='partial' and [x['status'] for x in partial['outcomes']]==['moved','held'],partial
            assert local('tabs.relocate.status',dict(plan_id=plan['plan_id']),expected=3)['status']=='partial'
            checks.append('native-partial-frozen-selection-negative-cli-exit-status-reconcile')
            local('tabs.session.create',dict(name='uncertain',server=sock,start=True))
            plan=local('tabs.relocate.preview',dict(session='uncertain',destination='sink'))
            tools=Path(directory)/'fault-bin';tools.mkdir();attempts=Path(directory)/'move-attempts'
            real_tmux=shutil.which('tmux');wrapper=tools/'tmux'
            wrapper.write_text('#!'+sys.executable+'\nimport os,sys\nfrom pathlib import Path\n'
                +'if "move-window" in sys.argv and '+repr(sock)+' in sys.argv:\n'
                +' Path('+repr(str(attempts))+').open("a").write("attempt\\n")\n sys.exit(1)\n'
                +'os.execv('+repr(real_tmux)+',['+repr(real_tmux)+',*sys.argv[1:]])\n')
            wrapper.chmod(0o700);previous_path=env['PATH'];env['PATH']=str(tools)+os.pathsep+previous_path
            try:
                uncertain=local('tabs.relocate.apply',dict(plan_id=plan['plan_id']),expected=3)
                assert uncertain['status']=='uncertain' and uncertain['outcomes'][0]['status']=='uncertain',uncertain
                local('tabs.relocate.status',dict(plan_id=plan['plan_id']),expected=3)
                local('tabs.relocate.apply',dict(plan_id=plan['plan_id']),expected=3)
                assert attempts.read_text().count('attempt')==1,'uncertain effect replayed'
            finally:env['PATH']=previous_path
            checks.append('installed-cli-native-command-failure-uncertain-negative-exit-restart-reconcile-no-replay')
            async def stdio():
                from mcp import ClientSession,StdioServerParameters
                from mcp.client.stdio import stdio_client
                async with stdio_client(StdioServerParameters(command=str(prefix/'bin/codex-wake-mcp'),args=['--wake-root',str(root)],env=env)) as (reader,writer):
                    async with ClientSession(reader,writer) as session:
                        await session.initialize()
                        names={t.name for t in (await session.list_tools()).tools}
                        assert {'wake_tabs_session_create','wake_tabs_relocate_preview','wake_tabs_route_pin'}<=names
                        async def call(operation,arguments):
                            value=await session.call_tool('wake_'+operation.replace('.','_'),request(arguments));assert not value.is_error,value
                            return unwrap(json.loads(value.content[0].text))
                        created=await call('tabs.session.create',dict(name='stdio',server=sock));assert created['session']['state']=='empty'
                        await call('tabs.session.ensure',dict(name='stdio',server=sock,start=False))
                        assert (await call('tabs.session.open',dict(session='stdio')))['session']['state']=='running'
                        await call('tabs.session.update',dict(session='stdio',changes={'description':'stdio'}))
                        await call('tabs.relocate.preview',dict(destination='stdio',selection={'tabs':[]}))
                        for verb in ('pin','hold','resume','unpin'):await call('tabs.route.'+verb,dict(selection={'tabs':[]}))
                        assert (await call('tabs.session.delete',dict(session='stdio',terminate=True)))['status']=='deleted'
            asyncio.run(stdio());checks.append('real-sdk-installed-stdio-session-crud-relocation-routing-controls')
            port_socket=socket.socket();port_socket.bind(('127.0.0.1',0));port=port_socket.getsockname()[1];port_socket.close()
            endpoint='http://127.0.0.1:'+str(port);resource=endpoint+'/controller'
            command('controller','auth-configure','--issuer',endpoint,'--resource',resource,'--owner','synthetic-session-owner')
            server=subprocess.Popen([cli,'--wake-root',str(root),'controller','serve','--port',str(port)],env=env,cwd=directory,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
            def http(path,body=None,token=None):
                headers={'Content-Type':'application/json'}
                if token:headers['Authorization']='Bearer '+token
                try:
                    with urlopen(Request(endpoint+path,data=json.dumps(body).encode() if body is not None else None,headers=headers),timeout=20) as response:return response.status,json.loads(response.read() or b'{}')
                except HTTPError as error:return error.code,json.loads(error.read() or b'{}')
            deadline=time.monotonic()+8
            while True:
                try:
                    if http('/.well-known/oauth-authorization-server')[0]==200:break
                except OSError:pass
                assert time.monotonic()<deadline,'listener readiness deadline';time.sleep(.02)
            assert http('/operations',dict(operation='tabs.session.list',arguments={}))[0]==401
            client=http('/register',dict(redirect_uris=['http://127.0.0.1:45000/callback'],client_name='session534'))[1]
            verifier='s'*43;challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
            scope={k:v for k,v in target().items() if k!='generation'}
            code=command('controller','authorize-client','--client-id',client['client_id'],'--redirect-uri',client['redirect_uris'][0],'--subject','synthetic-session-service','--principal-kind','service','--scope','control','--scope','observe','--targets',json.dumps([scope]),'--code-challenge',challenge)['code']
            status,tokens=http('/token',dict(grant_type='authorization_code',client_id=client['client_id'],redirect_uri=client['redirect_uris'][0],code=code,code_verifier=verifier,resource=resource));assert status==200,tokens
            token=tokens['access_token']
            def remote(transport,operation,arguments):
                payload=request(arguments)
                if transport=='api':status,value=http('/operations',dict(operation=operation,arguments=payload),token)
                else:
                    status,value=http('/mcp',dict(jsonrpc='2.0',id=1,method='tools/call',params=dict(name='wake_'+operation.replace('.','_'),arguments=payload)),token)
                    value=value['result']['structuredContent']
                assert status==200,value
                return unwrap(value)
            def workflow(call,label):
                name='remote-'+label
                assert call('tabs.session.create',dict(name=name,server=sock))['session']['state']=='empty'
                original=call('tabs.session.ensure',dict(name=name,server=sock,start=False))['session']['id']
                assert call('tabs.session.open',dict(session=name))['session']['state']=='running'
                assert call('tabs.session.update',dict(session=name,changes={'description':label}))['session']['id']==original
                call('tabs.relocate.preview',dict(destination=name,selection={'tabs':[]}))
                for verb in ('pin','hold','resume','unpin'):call('tabs.route.'+verb,dict(selection={'tabs':[]}))
                assert call('tabs.session.delete',dict(session=name,terminate=True))['status']=='deleted'
            for transport in ('api','mcp'):workflow(lambda op,a:remote(transport,op,a),transport)
            checks.append('authenticated-api-oauth-mcp-session-crud-relocation-routing-parity')
            if args.windows_python:
                windows=windows_client(args.windows_python,args.wheel,endpoint,token,request,workflow)
                checks.append('native-powershell-portable-installed-api-mcp-session-crud-relocation-routing-parity')
            else:
                windows=dict(status='not_run',reason='explicit WSL-only qualification')
            assert births('peer')==peer,'unrelated peer pane/PID changed'
            loaded={name:str(Path(module.__file__).resolve()) for name,module in sys.modules.items() if name.startswith('codex_wake') and getattr(module,'__file__',None)}
            assert all(Path(path).is_relative_to(prefix) for path in loaded.values()),loaded
            report=dict(loaded_modules=loaded,status='PASS',tier='FOCUSED',checks=checks,python=sys.executable,prefix=str(prefix),package=str(package),wheel_sha256=hashlib.sha256(args.wheel.read_bytes()).hexdigest(),python_members_verified=len(members),windows=windows,provider_calls=0,production_touched=False,peer_preserved=True)
        finally:
            if server:
                server.terminate();server.wait(timeout=8)
                if server.stderr:server.stderr.close()
            try:
                stopped=unwrap(command('tabs','monitor-stop'))['monitor']
                stopped={k:stopped.get(k) for k in ('status','process','generation')}
                assert stopped['status']=='stopped',stopped
            finally:tmux('kill-server',check=False)
    report.update(elapsed_seconds=round(time.monotonic()-started,3),budget_seconds=180,budget_breach=time.monotonic()-started>180,owned_listener_terminated=server is None or server.poll() is not None,owned_monitor_stopped=stopped,owned_namespace_removed=True)
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(status='PASS',checks=len(checks),receipt=str(args.output))))


def windows_client(python,wheel,endpoint,token,request,workflow):
    helper=r'''
import hashlib,json,os,subprocess,sys,uuid,zipfile
from pathlib import Path
r=json.loads(sys.stdin.read());root=Path(os.environ['LOCALAPPDATA'])/'codex-wake-test'/('session534-'+uuid.uuid4().hex);root.mkdir()
prefix=root/'venv';subprocess.run([sys.executable,'-m','venv',str(prefix)],check=True,capture_output=True,timeout=60)
py=prefix/'Scripts/python.exe';subprocess.run([str(py),'-m','pip','install','--no-deps',r['wheel']],check=True,capture_output=True,timeout=60)
token=root/'caller.token';token.write_text(r['token'])
ps=Path(os.environ['SystemRoot'])/'System32/WindowsPowerShell/v1.0/powershell.exe'
sid=subprocess.check_output([str(ps),'-NoProfile','-NonInteractive','-Command','[System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value'],text=True,timeout=10).strip()
subprocess.run(['icacls',str(token),'/inheritance:r','/grant:r','*'+sid+':(F)','*S-1-5-18:(F)','*S-1-5-32-544:(F)'],check=True,capture_output=True,timeout=10)
with zipfile.ZipFile(r['wheel']) as z:
 members=[n for n in z.namelist() if n.endswith('.py')]
 for name in members:assert (prefix/'Lib/site-packages'/name).read_bytes()==z.read(name),name
print(json.dumps(dict(prefix=str(prefix),cli=str(prefix/'Scripts/codex-wake.exe'),python=str(py),token=str(token),python_members_verified=len(members),wheel_sha256=hashlib.sha256(Path(r['wheel']).read_bytes()).hexdigest())))
'''
    wp=subprocess.check_output(['wslpath','-w',str(wheel.resolve())],text=True).strip()
    p=subprocess.run([python,'-c',helper],input=json.dumps(dict(wheel=wp,token=token)),text=True,capture_output=True,timeout=150);assert p.returncode==0,(p.stdout,p.stderr)
    installed=json.loads(p.stdout);calls=[]
    script=r'''$ErrorActionPreference='Stop';$ProgressPreference='SilentlyContinue';$r=[Console]::In.ReadToEnd()|ConvertFrom-Json;& $r.cli controller remote --endpoint $r.endpoint --token-file $r.token --transport $r.transport $r.operation --arguments ($r.arguments.Replace('"','\"'));exit $LASTEXITCODE'''
    encoded=base64.b64encode(script.encode('utf-16-le')).decode()
    try:
        for transport in ('api','mcp'):
            def call(operation,arguments,expected=0):
                payload=dict(installed,endpoint=endpoint,transport=transport,operation=operation,arguments=json.dumps(request(arguments)))
                p=subprocess.run(['/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe','-NoLogo','-NoProfile','-NonInteractive','-EncodedCommand',encoded],input=json.dumps(payload),text=True,capture_output=True,timeout=35)
                assert p.returncode==expected,(p.returncode,p.stdout,p.stderr)
                value=unwrap(json.loads(p.stdout.lstrip('\ufeff')));calls.append(dict(transport=transport,operation=operation,status=value.get('status')));return value
            workflow(call,'windows-'+transport)
            rejected=call('tabs.route.pin',dict(selection={'bad':True}),expected=3)
            assert rejected['reason']=='invalid_argument',rejected
            calls[-1]['exit_code']=3;calls[-1]['reason']='invalid_argument'
    finally:
        subprocess.run([python,'-c','import json,sys;from pathlib import Path;Path(json.loads(sys.stdin.read())).unlink()'],input=json.dumps(installed['token']),text=True,capture_output=True,check=True,timeout=10)
    installed.pop('token');installed.update(calls=calls,token_removed=True);return installed


if __name__=='__main__':main()
