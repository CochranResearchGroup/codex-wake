"""Actual immutable Bots -> installed Wake OAuth -> exact native TUI loop seam."""
import base64
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import time
from urllib.parse import urlencode
from urllib.request import Request, ProxyHandler, build_opener


class BotsHealthConsumer:
    def __init__(self,wake_cli,target,artifacts,env,bots_app,*,node):
        from codex_wake.controller_notices import flat_target
        self.root=Path(artifacts)/'bots-consumer';self.root.mkdir(mode=0o700)
        self.wake=self.root/'wake';self.wake.mkdir(mode=0o700)
        self.env=dict(env);self.env.pop('PYTHONPATH',None)
        self.cli=Path(wake_cli);self.processes=[];self.logs=[];self.proof=dict(states=[],qualified_boundary='immutable Bots public health API with actual OS receiver binding; no production SharedCodex enrollment')
        self.opener=build_opener(ProxyHandler({}))
        try:
            registry=Path(artifacts)/'wake'/'controller-health.json'
            binding=self.wake/'controller-health.json';binding.write_bytes(registry.read_bytes());binding.chmod(0o600)
            sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1];sock.close()
            self.base=f'http://127.0.0.1:{port}';resource=self.base+'/controller'
            self.run('controller','auth-configure','--issuer',self.base,'--resource',resource,'--owner','fixture-bots-owner')
            log=(self.root/'controller.log').open('wb');self.logs.append(log)
            self.controller=subprocess.Popen([str(self.cli),'--wake-root',str(self.wake),'controller','serve','--port',str(port)],env=self.env,cwd=self.root,stdout=log,stderr=subprocess.STDOUT);self.processes.append(self.controller)
            deadline=time.monotonic()+15
            while True:
                try:
                    if self.http(self.base+'/.well-known/oauth-authorization-server').get('issuer')==self.base:break
                except OSError:pass
                assert self.controller.poll() is None,'owned consumer Wake controller exited'
                assert time.monotonic()<deadline,'owned controller readiness deadline';time.sleep(.05)
            client=self.http(self.base+'/register',dict(redirect_uris=['http://127.0.0.1:45000/callback'],client_name='Bots exact-loop consumer'))
            verifier='b'*43;challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
            code=self.run('controller','authorize-client','--client-id='+client['client_id'],'--redirect-uri',client['redirect_uris'][0],
                '--subject','fixture-bots-observer','--principal-kind','service','--scope','observe','--targets',json.dumps([flat_target(target)]),'--code-challenge',challenge)['code']
            token=self.http(self.base+'/token',dict(grant_type='authorization_code',client_id=client['client_id'],redirect_uri=client['redirect_uris'][0],code=code,code_verifier=verifier,resource=resource),form=True)['access_token']
            token_path=self.root/'oauth.token';token_path.write_text(token);token_path.chmod(0o600)
            config=self.root/'consumer.json';config.write_text(json.dumps(dict(version=1,endpoint=self.base,tokenFile=str(token_path),targets=dict(fixture=target))));config.chmod(0o600)
            consumer_log=self.root/'bots.log';log=consumer_log.open('wb');self.logs.append(log)
            script=Path(__file__).with_name('controller_bots_health_consumer.mjs')
            self.bots=subprocess.Popen([str(node),str(script),str(bots_app),str(config)],env=self.env,cwd=self.root,stdout=log,stderr=subprocess.STDOUT);self.processes.append(self.bots)
            deadline=time.monotonic()+15
            while not consumer_log.read_text().strip():
                assert self.bots.poll() is None,'owned Bots candidate exited'
                assert time.monotonic()<deadline,'owned Bots readiness deadline';time.sleep(.05)
            value=json.loads(consumer_log.read_text().splitlines()[0]);self.url=value['url'];self.proof.update(candidate=value['candidate'],bots_source=value['sourceRevision'])
        except BaseException:
            self.close();raise

    def run(self,*args):
        value=subprocess.run([str(self.cli),'--wake-root',str(self.wake),*args],env=self.env,cwd=self.root,text=True,capture_output=True,timeout=30)
        assert value.returncode==0,(value.returncode,value.stdout,value.stderr)
        return json.loads(value.stdout)

    def http(self,url,body=None,*,form=False):
        headers={}
        if body is not None:
            headers['Content-Type']='application/x-www-form-urlencoded' if form else 'application/json'
            body=(urlencode(body) if form else json.dumps(body)).encode()
        with self.opener.open(Request(url,data=body,headers=headers),timeout=15) as response:return json.loads(response.read())

    def observe(self,expected):
        result=self.http(self.url+'/api/bots/fixture/health')['responsiveness']
        assert result['state']==expected,result
        assert result['grantsRecovery'] is False
        if expected=='responsive':
            assert result['evidence']=='tui_main_loop_ack'
            assert result['challenge'] not in [value.get('challenge') for value in self.proof['states']]
        self.proof['states'].append(result)
        return result

    def close(self):
        for process in reversed(self.processes):
            process.terminate()
            try:process.wait(timeout=8)
            except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
        for log in self.logs:log.close()
        self.proof['owned_pids']=[process.pid for process in self.processes]
        self.proof['owned_processes_exited']=all(process.poll() is not None for process in self.processes)
        (self.root/'receipt.json').write_text(json.dumps(self.proof,indent=2,sort_keys=True)+'\n')
