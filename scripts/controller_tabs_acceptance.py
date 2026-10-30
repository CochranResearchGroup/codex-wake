#!/usr/bin/env python3
"""Installed-only public presentation acceptance on an isolated tmux server.

Generated OAuth credential stays in the private disposable fixture. No provider,
production terminal, native shared service or running peer is touched.
"""
import base64
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def main():
    from codex_wake.controller_auth import OAuthAuthority
    import codex_wake.controller_tabs as source
    executable = str(Path(sys.executable).parent / 'codex-wake')
    env = dict(os.environ)
    env.pop('PYTHONPATH',None)
    with tempfile.TemporaryDirectory(prefix='wake-tabs402-') as directory:
        root = Path(directory)/'wake'
        root.mkdir(mode=0o700)
        mux = str(Path(directory)/'tmux.sock')
        subprocess.run(['tmux','-S',mux,'new-session','-d','-s','fixture','sleep 60'],check=True)
        listener = None
        def cli(*args):
            result = subprocess.run([executable,'--wake-root',str(root),*args],env=env,cwd=directory,text=True,capture_output=True,timeout=30)
            assert result.returncode==0,(result.stdout,result.stderr)
            return json.loads(result.stdout)
        try:
            config = root/'controller-tabs.json'
            config.write_text(json.dumps(dict(schema_version=1,workspaces={'fixture':dict(kind='byobu',socket_path=mux,session_id='$0',evidence_scope='disposable_fixture',privacy='safe')})))
            config.chmod(0o600)
            local = cli('tabs','list')
            target = local['resources'][0]['target']
            assert cli('tabs','show','--arguments',json.dumps(dict(workspace='fixture',selector='@0')))['resources'][0]['target']==target
            reserve = socket.socket();reserve.bind(('127.0.0.1',0));port=reserve.getsockname()[1];reserve.close()
            base = f'http://127.0.0.1:{port}'
            cli('controller','auth-configure','--issuer',base,'--resource',base+'/controller','--owner','fixture')
            auth = OAuthAuthority(root/'controller-auth/authority.sqlite',issuer=base,resource=base+'/controller')
            client = auth.register(dict(redirect_uris=['http://127.0.0.1/callback']))
            def token(scopes):
                verifier='v'*43
                challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
                grant={k:v for k,v in target.items() if k!='generation'}
                code=auth.authorize(subject='fixture',principal_kind='owner',client_id=client['client_id'],redirect_uri=client['redirect_uris'][0],resource=auth.resource,scopes=scopes,targets=[grant],code_challenge=challenge)
                return auth.token(dict(grant_type='authorization_code',client_id=client['client_id'],code=code,code_verifier=verifier,redirect_uri=client['redirect_uris'][0],resource=auth.resource))['access_token']
            access=token(['observe','control'])
            observe=token(['observe'])
            token_file=Path(directory)/'caller.token';token_file.write_text(access);token_file.chmod(0o600)
            listener=subprocess.Popen([executable,'--wake-root',str(root),'controller','serve','--port',str(port)],env=env,cwd=directory,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
            def http(path,value,bearer=access):
                try:
                    with urlopen(Request(base+path,data=json.dumps(value).encode(),headers={'Content-Type':'application/json','Authorization':'Bearer '+bearer}),timeout=5) as response:
                        return response.status,json.load(response)
                except HTTPError as error:return error.code,json.load(error)
            for _ in range(100):
                try:
                    status,api=http('/operations',dict(operation='tabs.list',arguments={}));break
                except OSError:time.sleep(.02)
            else:raise AssertionError('listener did not start')
            assert status==200 and api['result']['resources'][0]['target']==target,api
            remote=cli('controller','remote','--endpoint',base,'--token-file',str(token_file),'tabs.list')
            assert remote['result']['resources'][0]['target']==target
            def mcp(name,args):
                status,result=http('/mcp',dict(jsonrpc='2.0',id=1,method='tools/call',params=dict(name=name,arguments=args)))
                assert status==200,result
                return result['result']['structuredContent']
            assert mcp('wake_tabs_show',dict(workspace='fixture',selector='@0'))['result']['resources'][0]['target']==target
            payload=dict(workspace='fixture',expected_target=target,pane='%0',lines=5)
            payload['_request']=dict(operation_id='capture',idempotency_key='capture',correlation_id='capture',binding='fixture',target=target)
            assert http('/operations',dict(operation='tabs.capture',arguments=payload),observe)[0]==403
            captured=mcp('wake_tabs_capture',payload)
            record=captured['result']['operation']
            assert record['phase']=='terminal' and record['result']['fallback'] is True,record
            same=http('/operations',dict(operation='tabs.capture',arguments=payload))[1]
            assert same['result']['operation']['operation_id']==record['operation_id']
            print(json.dumps(dict(status='passed',module=source.__file__,local_cli=True,remote_cli=True,oauth_api=True,mcp=True,observe_cannot_capture=True,retained_intent=True,real_isolated_tmux=True,windows_matrix=False),sort_keys=True))
        finally:
            if listener:
                listener.terminate()
                try:listener.wait(timeout=5)
                except subprocess.TimeoutExpired:listener.kill();listener.wait()
            subprocess.run(['tmux','-S',mux,'kill-server'],check=False)


if __name__=='__main__': main()
