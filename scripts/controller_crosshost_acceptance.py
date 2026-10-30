#!/usr/bin/env python3
"""Real Windows/WSL/Bastion controller caller matrix in owned test namespaces."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import signal
import socket
import subprocess
import sys
import time
import uuid

SSH=['ssh','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','ConnectTimeout=5']
WSL=['/mnt/c/Windows/System32/wsl.exe','--distribution','wsl-test','--exec']
WINDOWS='/mnt/c/Users/ecoch/AppData/Local/codex-wake-test/controller405-20261030/venv/Scripts'
ROOTS={'bastion':'/home/ecochran76/.local/state/codex-wake/testing/controller405-20261030','wsl-test':'/root/.local/state/codex-wake/testing/controller405-20261030'}


def execute(role,argv,*,data=None,check=True,timeout=20):
    command=SSH+['bastion',shlex.join(argv)] if role=='bastion' else WSL+argv
    return subprocess.run(command,input=data,capture_output=True,check=check,timeout=timeout)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--state',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();args.state.mkdir(mode=0o700,parents=True,exist_ok=True)
    run='matrix-'+uuid.uuid4().hex[:8];metadata={};tunnels=[];checks=[];windows_tokens={}
    script=(Path(__file__).parent/'controller_crosshost_fixture.py').read_bytes()
    def private(path,data):path.write_bytes(data);path.chmod(0o600)
    def portable(role,endpoint,token,operation,arguments=None,transport='api',expected=0):
        if role=='windows':command=[WINDOWS+'/codex-wake.exe','controller','remote','--transport',transport]
        else:command=[sys.executable,'-m','codex_wake.controller_client','controller','remote','--transport',transport]
        result=subprocess.run(command+['--endpoint',endpoint,'--token-file',str(token),operation,'--arguments',json.dumps(arguments or {})],text=True,capture_output=True,timeout=45)
        assert result.returncode==expected,(role,operation,result.returncode,result.stdout,result.stderr)
        return json.loads(result.stdout)
    def forward(local,remote,reverse=False):
        option='-R' if reverse else '-L'
        process=subprocess.Popen(SSH+['-o','ExitOnForwardFailure=yes','-N',option,'127.0.0.1:'+str(local)+':127.0.0.1:'+str(remote),'bastion'],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        tunnels.append(process)
        time.sleep(.3)
        assert process.poll() is None,'owned SSH forwarding failed'
    def freeport():
        with socket.socket() as sock:sock.bind(('127.0.0.1',0));return sock.getsockname()[1]
    try:
        for role,root in ROOTS.items():
            path=root+'/'+run+'.py'
            writer='from pathlib import Path;import sys;p=Path('+repr(path)+');p.write_bytes(sys.stdin.buffer.read());p.chmod(0o600)'
            execute(role,[root+'/venv/bin/python','-c',writer],data=script)
            launch="from pathlib import Path;import subprocess;root=Path("+repr(root)+");log=(root/"+repr(run+'.log')+").open('w');p=subprocess.Popen([str(root/'venv/bin/python'),"+repr(path)+",'--root',str(root/"+repr(run)+"),'--role',"+repr(role)+"],stdout=log,stderr=log,start_new_session=True);print(p.pid)"
            execute(role,[root+'/venv/bin/python','-c',launch])
            for unused in range(50):
                response=execute(role,['cat',root+'/'+run+'/ready.json'],check=False)
                if response.returncode==0:break
                time.sleep(.1)
            else:raise RuntimeError((role,execute(role,['cat',root+'/'+run+'.log']).stdout.decode()))
            metadata[role]=json.loads(response.stdout)
            private(args.state/(role+'-ready.json'),response.stdout)
            token=execute(role,['cat',metadata[role]['token_file']]).stdout
            private(args.state/(role+'.token'),token)
        port=freeport();forward(port,int(metadata['bastion']['endpoint'].rsplit(':',1)[1]))
        metadata['bastion']['client_endpoint']='http://127.0.0.1:'+str(port)
        metadata['wsl-test']['client_endpoint']=metadata['wsl-test']['endpoint']
        writer=r'''import json,os,subprocess,sys
from pathlib import Path
payload=json.loads(sys.stdin.buffer.read());root=Path(os.environ['LOCALAPPDATA'])/'codex-wake-test/controller405-20261030';path=root/payload['name'];path.touch()
ps=Path(os.environ['SystemRoot'])/'System32/WindowsPowerShell/v1.0/powershell.exe';sid=subprocess.check_output([str(ps),'-NoProfile','-NonInteractive','-Command','[System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value'],text=True).strip()
icacls=Path(os.environ['SystemRoot'])/'System32/icacls.exe';subprocess.run([str(icacls),str(path),'/inheritance:r','/grant:r','*'+sid+':(F)','*S-1-5-18:(F)','*S-1-5-32-544:(F)'],capture_output=True,check=True)
path.write_text(payload['token'],encoding='utf-8');print(str(path))
'''
        for role in ROOTS:
            token=args.state/(role+'.token')
            payload=json.dumps(dict(name=run+'-'+role+'.token',token=token.read_text())).encode()
            staged=subprocess.run([WINDOWS+'/python.exe','-c',writer],input=payload,capture_output=True,check=True,timeout=20)
            win_token=staged.stdout.decode().strip();windows_tokens[role]=win_token
            for caller in ('wsl','windows'):
                for transport in ('api','mcp'):
                    result=portable(caller,metadata[role]['client_endpoint'],win_token if caller=='windows' else token,'inventory.list',transport=transport)
                    assert [row['target']['namespace'] for row in result['result']['resources']]==['account:alice'],result
                    assert result['actor']['grant_id']==metadata[role]['actor']['grant_id']
                    checks.append(dict(caller=caller,target=role,transport=transport,operation='inventory.list',filtered=True,original_principal=True))
            tabs=portable('windows',metadata[role]['client_endpoint'],win_token,'tabs.list')['result']['resources']
            assert len(tabs)==2 and {row['window']['name'] for row in tabs}=={'alpha','beta'},tabs
            target=tabs[0]['target'];pane=tabs[0]['window']['panes'][0]['pane_id']
            request=dict(operation_id=run+'-'+role+'-capture',idempotency_key=run+'-'+role+'-capture',correlation_id=run,binding='original-windows',target=target)
            body=dict(workspace=role,expected_target=target,pane=pane,lines=5,_request=request)
            captured=portable('windows',metadata[role]['client_endpoint'],win_token,'tabs.capture',body)
            assert captured['result']['operation']['execution']=='completed',captured
            stale=dict(body,expected_target=dict(target,generation='replaced-generation'),_request=dict(request,operation_id=run+'-'+role+'-stale',idempotency_key=run+'-'+role+'-stale',target=dict(target,generation='replaced-generation')))
            denied=portable('windows',metadata[role]['client_endpoint'],win_token,'tabs.capture',stale)
            assert denied['result']['operation']['reason']=='stale_target' and denied['result']['operation']['execution']=='unknown',denied
            checks.append(dict(caller='windows',target=role,transport='api',operation='actual_byobu_capture',safe_disposable_panes=True,stale_generation_refused=True))
            # Real target-local Linux CLI also reaches that target's OAuth API.
            remote=execute(role,[ROOTS[role]+'/venv/bin/codex-wake','controller','remote','--endpoint',metadata[role]['endpoint'],'--token-file',metadata[role]['token_file'],'inventory.list'])
            assert json.loads(remote.stdout)['actor']['grant_id']==metadata[role]['actor']['grant_id']
        # Existing actual OpenSSH key transport, fixed destination-side mapping.
        from codex_wake.controller_hosts import HostRegistry,HostOperations
        source=args.state/run;registry=HostRegistry(source/'controller-hosts/registry.sqlite');remote=metadata['bastion']
        target=remote['ssh_target']
        wrapper=ROOTS['bastion']+'/'+run+'-ssh.py'
        mode=ROOTS['bastion']+'/'+run+'-ssh.mode';log=ROOTS['bastion']+'/'+run+'-ssh.calls'
        program='import json,pathlib,shlex,subprocess,sys\n'
        program+='pathlib.Path('+repr(log)+').open("a").write("received\\n")\n'
        program+='reply=subprocess.run(shlex.split('+repr(remote['ssh_command'])+'),input=sys.stdin.buffer.read(65537),capture_output=True)\n'
        program+='mode=pathlib.Path('+repr(mode)+').read_text()\n'
        program+='if mode=="withhold":sys.exit(255)\n'
        program+='sys.stdout.buffer.write(reply.stdout);sys.exit(reply.returncode)\n'
        write='from pathlib import Path;import sys;p=Path('+repr(wrapper)+');p.write_bytes(sys.stdin.buffer.read());p.chmod(0o600);Path('+repr(mode)+').write_text("normal")'
        execute('bastion',[ROOTS['bastion']+'/venv/bin/python','-c',write],data=program.encode())
        registry.register(target['host'],target['environment'],kind='remote',authority=target['authority'],generation=target['generation'],destination='bastion',command=shlex.join([ROOTS['bastion']+'/venv/bin/python',wrapper]),operator=True)
        owner=HostOperations(registry,local_operator=True)
        def route(arguments):
            # A fixture host observation may expire while this busy WSL host is
            # descheduled. Re-observe the same live, birth-pinned test receiver
            # before admission; never replay an admitted/uncertain exchange.
            for attempt in range(2):
                try:return owner.execute('hosts.route',arguments)
                except ValueError as error:
                    if getattr(error,'code',None)!='stale_target' or 'observation expired' not in str(error) or attempt:raise
                    probe='from codex_wake.process import process_identity;v='+repr(remote['process'])+';p=process_identity(v["pid"]);assert p["start_time_ticks"]==v["start_ticks"] and p["boot_id"]==v["boot_id"]'
                    execute('bastion',[ROOTS['bastion']+'/venv/bin/python','-c',probe])
                    registry.observe(target,online=True,operator=True)
        body=dict(target=target,operation='inventory.list',arguments={},operation_id=run+'-ssh',idempotency_key=run+'-ssh')
        original=route(body)['route']
        assert original['execution']=='completed' and [row['target']['namespace'] for row in original['result']['result']['resources']]==['account:alice'],original
        assert route(body)['route']==original
        def receiver_count():return len(execute('bastion',['cat',log]).stdout.splitlines())
        assert receiver_count()==1
        execute('bastion',[ROOTS['bastion']+'/venv/bin/python','-c','from pathlib import Path;Path('+repr(mode)+').write_text("withhold")'])
        uncertain_body=dict(body,operation_id=run+'-uncertain',idempotency_key=run+'-uncertain')
        uncertain=route(uncertain_body)['route']
        assert uncertain['execution']=='unknown' and uncertain['delivery']=='uncertain',uncertain
        count=receiver_count();assert count==2
        execute('bastion',[ROOTS['bastion']+'/venv/bin/python','-c','from pathlib import Path;Path('+repr(mode)+').write_text("normal")'])
        assert route(uncertain_body)['route']==uncertain and receiver_count()==count
        registry.observe(target,online=False,operator=True)
        try:owner.execute('hosts.route',dict(body,operation_id=run+'-offline',idempotency_key=run+'-offline'))
        except ValueError as error:assert error.code=='offline_target'
        else:raise AssertionError('offline destination admitted')
        registry.observe(target,online=True,operator=True)
        reconnected=route(dict(body,operation_id=run+'-reconnected',idempotency_key=run+'-reconnected'))['route']
        assert reconnected['execution']=='completed' and receiver_count()==3
        execute('bastion',[ROOTS['bastion']+'/venv/bin/codex-wake','--wake-root',ROOTS['bastion']+'/'+run,'hosts','revoke-principal','controller405-key'])
        denied=route(dict(body,operation_id=run+'-revoked',idempotency_key=run+'-revoked'))['route']
        assert denied['execution']=='failed' and denied['result']['error']['code']=='invalid_token' and receiver_count()==4,denied
        checks.append(dict(caller='wsl',target='bastion',transport='actual_OpenSSH',fixed_principal=True,original_key_replay_returns_original=True,offline_refused=True,reconnect=True,revoked_mapping_refused=True,actual_ssh_withheld_reply_stays_uncertain=True,uncertain_reconnect_not_replayed=True))
        for role,meta in metadata.items():
            code='from pathlib import Path;from codex_wake.controller_auth import OAuthAuthority;root=Path('+repr(ROOTS[role]+'/'+run)+');auth=OAuthAuthority(root/"oauth.sqlite",issuer='+repr(meta['endpoint'])+',resource='+repr(meta['endpoint']+'/controller')+');auth.revoke_grant('+repr(meta['actor']['grant_id'])+')'
            execute(role,[ROOTS[role]+'/venv/bin/python','-c',code])
            for transport in ('api','mcp'):
                rejected=portable('windows',meta['client_endpoint'],windows_tokens[role],'inventory.list',transport=transport,expected=2)
                assert rejected['error']['code']=='invalid_token',rejected
            checks.append(dict(caller='windows',target=role,transport='API_and_OAuthMCP',original_oauth_grant_revoked=True))
        result=dict(status='passed',ticket=405,run=run,checks=checks,roles={role:{key:value for key,value in meta.items() if key not in ('token_file','actor','ssh_command')} for role,meta in metadata.items()},
                    boundary='Actual native Windows caller and actual WSL/remote Linux execution authorities; synthetic inventory accounts, real isolated Byobu panes. Native Windows owner, psmux bridge, staged upgrade and Bots health acceptance remain separate evidence.',provider_calls=0)
        args.output.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n');print(json.dumps(dict(status='passed',checks=len(checks),receipt=str(args.output))))
    finally:
        for process in tunnels:
            if process.poll() is None:process.terminate()
            process.communicate(timeout=10)
        for role,meta in metadata.items():
            root=ROOTS[role]
            code="import json,os,signal;from codex_wake.process import process_identity;v="+repr(meta['process'])+";p=process_identity(v['pid']);assert p['start_time_ticks']==v['start_ticks'] and p['boot_id']==v['boot_id'];os.kill(v['pid'],signal.SIGTERM)"
            execute(role,[root+'/venv/bin/python','-c',code],check=False)


if __name__=='__main__':main()
