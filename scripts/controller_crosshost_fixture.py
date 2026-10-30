#!/usr/bin/env python3
"""Private installed controller/Byobu fixture for actual cross-host acceptance.

This is test infrastructure: no provider credential, model process, service
installation or production controller is discovered or changed.
"""
import argparse
import base64
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


def private_json(path,value):
    path.write_text(json.dumps(value,sort_keys=True,indent=2)+'\n');path.chmod(0o600)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True);parser.add_argument('--role',required=True)
    args=parser.parse_args();root=args.root.absolute()
    root.mkdir(mode=0o700,parents=True,exist_ok=False)
    private_json(root/'controller405-fixture.json',dict(version=1,role=args.role,provider_effects=False))
    from codex_wake.controller_auth import OAuthAuthority
    from codex_wake.controller_http import ControllerHTTPServer
    from codex_wake.controller_operations import ControllerOperations
    from codex_wake.controller_hosts import HostRegistry
    from codex_wake.managed_inventory import ManagedInventory,Observation
    from codex_wake.operation_commands import owner
    from codex_wake.process import process_identity
    host=socket.gethostname();environment=os.environ.get('WSL_DISTRO_NAME') or os.name
    native=process_identity(os.getpid());generation=dict(pid=os.getpid(),start_ticks=native['start_time_ticks'],boot_id=native['boot_id'])
    inventory=ManagedInventory(root)
    for account in ('alice','bob'):
        home=root/'homes'/account;home.mkdir(parents=True,mode=0o700)
        inventory.enroll(Observation('codex','account:'+account,'controller405-'+account,str(home),'ready',time.time(),
            'native_metadata',generation,[],dict(input='not_qualified')),operator=True)
    tmux_socket=root/'presentation.sock';created=False;server=None
    try:
        env=dict(os.environ,BYOBU_CONFIG_DIR=str(root/'byobu'),BYOBU_BACKEND='tmux',HOME=str(root/'homes/alice'))
        env.pop('TMUX',None);env.pop('TMUX_PANE',None)
        subprocess.run(['byobu-tmux','-S',str(tmux_socket),'-f','/dev/null','new-session','-d','-s','controller405','-n','alpha','/bin/sh'],env=env,check=True,timeout=15,capture_output=True);created=True
        subprocess.run(['tmux','-S',str(tmux_socket),'new-window','-d','-t','controller405','-n','beta','/bin/sh'],check=True,timeout=10,capture_output=True)
        session=subprocess.check_output(['tmux','-S',str(tmux_socket),'display-message','-p','-t','controller405','#{session_id}'],text=True,timeout=10).strip()
        private_json(root/'controller-tabs.json',dict(schema_version=1,workspaces={args.role:dict(kind='byobu',socket_path=str(tmux_socket),session_id=session,evidence_scope='disposable_fixture',privacy='safe')}))
        free=socket.socket();free.bind(('127.0.0.1',0));port=free.getsockname()[1];free.close()
        endpoint='http://127.0.0.1:'+str(port)
        auth=OAuthAuthority(root/'oauth.sqlite',issuer=endpoint,resource=endpoint+'/controller',on_revoke=owner(root).revoke_grant)
        client=auth.register(dict(redirect_uris=['http://localhost/callback']))
        verifier='v'*43;challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
        targets=[dict(host=host,environment=environment,namespace='account:alice'),dict(host=host,environment=environment,workspace=args.role,presentation='byobu')]
        code=auth.authorize(subject='controller405-service',principal_kind='service',client_id=client['client_id'],redirect_uri='http://localhost/callback',resource=auth.resource,
            scopes=['observe','control'],targets=targets,code_challenge=challenge)
        token=auth.token(dict(grant_type='authorization_code',code=code,client_id=client['client_id'],redirect_uri='http://localhost/callback',resource=auth.resource,code_verifier=verifier))['access_token']
        token_path=root/'caller.token';token_path.write_text(token);token_path.chmod(0o600)
        actor=auth.authenticate(token);caller={k:v for k,v in vars(actor).items() if k!='principal_kind'};caller['scopes']=sorted(actor.scopes)
        private_json(root/'controller-messaging.json',dict(version=1,local_caller=caller))
        registry=HostRegistry(root/'controller-hosts/registry.sqlite')
        destination=registry.register(host,environment,kind='wsl' if os.environ.get('WSL_DISTRO_NAME') else 'remote',authority='controller405-'+args.role,destination='bastion',operator=True)
        mapping=registry.map_principal('controller405-key',subject='controller405-ssh',scopes=['observe'],targets=[targets[0]],expires_at=time.time()+1800,operator=True)
        command=shlex.join([sys.executable,'-m','codex_wake.cli','--wake-root',str(root),'hosts','ssh-serve','--principal-id','controller405-key','--target',json.dumps(destination['target'],sort_keys=True,separators=(',',':'))])
        from codex_wake.controller_tabs import controller_tabs_from_root
        server=ControllerHTTPServer(('127.0.0.1',port),auth,ControllerOperations(inventory,host=host,environment=environment,tabs=controller_tabs_from_root(root)))
        import codex_wake
        private_json(root/'ready.json',dict(status='ready',role=args.role,endpoint=endpoint,token_file=str(token_path),
            actor={k:v for k,v in caller.items() if k!='targets'},targets=targets,ssh_target=destination['target'],ssh_command=command,
            ssh_principal=mapping['principal_id'],process=generation,source_sha256={name:hashlib.sha256((Path(codex_wake.__file__).parent/name).read_bytes()).hexdigest() for name in ('controller_http.py','controller_auth.py','controller_runtime.py','controller_recovery.py','controller_health.py','controller_notices.py','controller_hosts.py','controller_tabs.py','controller_builds.py','controller_accounts.py','controller_flows.py','entrypoint.py','controller_client.py')},byobu=dict(socket=str(tmux_socket),session=session),package=codex_wake.__file__,python=sys.version))
        def terminate(*unused):raise SystemExit(0)
        signal.signal(signal.SIGTERM,terminate)
        server.serve_forever(poll_interval=.1)
    finally:
        if server:server.server_close()
        if created:subprocess.run(['tmux','-S',str(tmux_socket),'kill-server'],capture_output=True,timeout=10)
        private_json(root/'stopped.json',dict(status='stopped',pid=os.getpid(),provider_effects=False))


if __name__=='__main__':main()
