#!/usr/bin/env python3
"""Actual Windows psmux presentation through a WSL execution authority."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading
import time

from controller_crosshost_acceptance import WINDOWS,WSL,ROOTS


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--state',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--namespace',required=True)
    args=parser.parse_args();root=args.state/('psmux-wake-'+args.namespace);root.mkdir(mode=0o700,parents=True,exist_ok=False)
    script=subprocess.check_output(['wslpath','-w',str(Path(__file__).parent/'controller_psmux_bridge405.py')],text=True).strip()
    import re
    assert re.fullmatch(r'controller405-[A-Za-z0-9-]+',args.namespace)
    creation='from pathlib import Path;import os,subprocess;p=str(Path(os.environ["LOCALAPPDATA"])/"Microsoft/WinGet/Links/psmux.exe");namespace='+repr(args.namespace)+';subprocess.run([p,"-L",namespace,"new-session","-d","-s","controller405","-n","alpha","--","cmd.exe","/d","/k"],check=True,capture_output=True);subprocess.run([p,"-L",namespace,"new-window","-d","-t","controller405","-n","beta","--","cmd.exe","/d","/k"],check=True,capture_output=True)'
    subprocess.run([WINDOWS+'/python.exe','-c',creation],capture_output=True,check=True,timeout=15)
    base=[WINDOWS+'/python.exe',script,'--namespace',args.namespace,'--session','controller405']
    description=json.loads(subprocess.check_output(base+['--describe'],text=True,timeout=10));identity=description['identity']
    bridge=base+['--server-pid',str(identity['pid']),'--server-birth',str(identity['creation_filetime'])]
    path=root/'controller-tabs.json';path.write_text(json.dumps(dict(schema_version=1,workspaces={'windows405':dict(kind='psmux',bridge_command=bridge,bridge_generation=description['generation'],evidence_scope='disposable_fixture',privacy='safe')})));path.chmod(0o600)
    from codex_wake.controller_auth import OAuthAuthority
    from codex_wake.controller_http import ControllerHTTPServer
    from codex_wake.controller_operations import ControllerOperations
    from codex_wake.controller_tabs import controller_tabs_from_root
    from codex_wake.controller_client import invoke
    from codex_wake.managed_inventory import ManagedInventory
    host=socket.gethostname();environment=os.environ.get('WSL_DISTRO_NAME') or os.name
    with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    endpoint='http://127.0.0.1:'+str(port)
    auth=OAuthAuthority(root/'oauth.sqlite',issuer=endpoint,resource=endpoint+'/controller')
    client=auth.register(dict(redirect_uris=['http://localhost/callback']));verifier='v'*43
    challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
    grant=dict(host=host,environment=environment,workspace='windows405',presentation='psmux')
    code=auth.authorize(subject='controller405-psmux-service',principal_kind='service',client_id=client['client_id'],redirect_uri='http://localhost/callback',resource=auth.resource,scopes=['observe','control'],targets=[grant],code_challenge=challenge)
    token=auth.token(dict(grant_type='authorization_code',code=code,client_id=client['client_id'],redirect_uri='http://localhost/callback',resource=auth.resource,code_verifier=verifier))['access_token']
    token_path=root/'caller.token';token_path.write_text(token);token_path.chmod(0o600)
    server=ControllerHTTPServer(('127.0.0.1',port),auth,ControllerOperations(ManagedInventory(root),host=host,environment=environment,tabs=controller_tabs_from_root(root)))
    worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
    remote_token=ROOTS['wsl-test']+'/psmux405.token'
    code="from pathlib import Path;import sys;p=Path("+repr(remote_token)+");p.touch(mode=0o600);p.chmod(0o600);p.write_bytes(sys.stdin.buffer.read())"
    subprocess.run(WSL+[ROOTS['wsl-test']+'/venv/bin/python','-c',code],input=token.encode(),capture_output=True,check=True,timeout=10)
    def call(operation,args,transport='api'):
        value,failed=invoke(endpoint,token_path,operation,args,transport=transport);assert not failed,value;return value
    try:
        for transport in ('api','mcp'):
            value=call('tabs.list',{},transport)
            assert len(value['result']['resources'])==2 and all(row['target']['presentation']=='psmux' for row in value['result']['resources']),value
        remote=subprocess.run(WSL+[ROOTS['wsl-test']+'/venv/bin/codex-wake','controller','remote','--endpoint',endpoint,'--token-file',remote_token,'tabs.list'],text=True,capture_output=True,timeout=20)
        assert remote.returncode==0,(remote.stdout,remote.stderr)
        resources=json.loads(remote.stdout)['result']['resources'];target=resources[0]['target'];pane=resources[0]['window']['panes'][0]['pane_id']
        assert {row['window']['name'] for row in resources}=={'alpha','beta'}
        request=dict(operation_id='psmux405-capture',idempotency_key='psmux405-capture',correlation_id='psmux405',binding='original-wsl-caller',target=target)
        args_capture=dict(workspace='windows405',expected_target=target,pane=pane,lines=5,_request=request)
        captured=call('tabs.capture',args_capture)
        assert captured['result']['operation']['execution']=='completed',captured
        assert call('tabs.capture',args_capture)['result']['operation']==captured['result']['operation']
        denied=call('tabs.input',dict(workspace='windows405',expected_target=target,pane=pane,input='echo never-submitted',custody={},transport='terminal',_request=dict(request,operation_id='psmux405-input',idempotency_key='psmux405-input')))
        assert denied['result']['operation']['reason']=='input_custody_required',denied
        # Exact owned namespace only; this also proves unavailable bridge fails closed.
        command=[WINDOWS+'/python.exe','-c',"from pathlib import Path;import os,subprocess;subprocess.run([str(Path(os.environ['LOCALAPPDATA'])/'Microsoft/WinGet/Links/psmux.exe'),'-L',"+repr(args.namespace)+",'kill-server'],check=True)"]
        subprocess.run(command,capture_output=True,check=True,timeout=10)
        unavailable,failed=invoke(endpoint,token_path,'tabs.list',{})
        assert failed and unavailable['error']['code']=='attachment_unavailable',unavailable
        result=dict(status='passed',windows_presentation_identity=identity,bridge_generation=description['generation'],controller_execution_authority=dict(host=host,environment=environment,platform='WSL/Linux'),
            native_windows_owner='unsupported_explicit',actual_windows_capture=True,api_and_oauth_mcp=True,wsl_test_caller=True,same_intent_capture_no_replay=True,unowned_input_refused=True,
            exact_namespace_shutdown_then_unavailable=True,provider_calls=0,root=str(root),boundary='Actual native Windows psmux with WSL-owned finite bridge; no native Windows Wake owner or Windows TUI responsiveness claim')
        args.output.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n');print(json.dumps(dict(status='passed',receipt=str(args.output))))
    finally:server.shutdown();server.server_close();worker.join(timeout=2)


if __name__=='__main__':main()
