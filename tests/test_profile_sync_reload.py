"""Sync can reload only its selected, verified native profile."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

from codex_wake.account_commands import execute

SERVER = r'''import json,os,sys
from pathlib import Path
from websockets.sync.server import unix_serve
home=Path(os.environ['CODEX_HOME']);event=home/'reload-events'
def handle(ws):
    for raw in ws:
        req=json.loads(raw)
        if 'id' not in req:continue
        method=req['method']
        if method=='initialize': result={'codexHome':str(home)}
        elif method=='thread/loaded/list': result={'data':[]}
        elif method=='config/mcpServer/reload':
            with event.open('a') as out:out.write('reload\n')
            result={}
        else:
            ws.send(json.dumps({'id':req['id'],'error':{'code':-32601,'message':'unsupported'}}));continue
        ws.send(json.dumps({'id':req['id'],'result':result}))
with unix_serve(handle,path=str(home/'app-server-control/app-server-control.sock')) as server:
    (home/'ready').touch();server.serve_forever()
'''


class ProfileSyncReloadTests(unittest.TestCase):
    def test_public_sync_reloads_selected_profile_once_and_preserves_peer(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);stock=root/'stock';stock.mkdir(mode=0o700)
            (stock/'config.toml').write_text('model="first"\n')
            execute('accounts.init',{},root)
            execute('stores.register',dict(selector='stock',home=str(stock)),root)
            homes={}
            for name in ('alice','bob'):
                created=execute('accounts.create',dict(selector=name,mode='independent',source='stock'),root)
                homes[name]=Path(created['result']['account']['home'])
            home=homes['alice'];(home/'app-server-control').mkdir(mode=0o700)
            script=root/'native.py';script.write_text(SERVER)
            executable=Path(sys.executable).resolve();manifest=root/'builds.json'
            manifest.write_text(json.dumps(dict(schema_version=1,builds=dict(modded=dict(executable=str(executable),sha256=hashlib.sha256(executable.read_bytes()).hexdigest(),upstream_version='fixture',revision='fixture',source='test',read_schemas=[5],backend='managed')))))
            registry=root/'controller-accounts.toml'
            with registry.open('a') as f:f.write('\n[builds]\nmanifest='+json.dumps(str(manifest))+'\n')
            child=subprocess.Popen([sys.executable,str(script)],env=dict(os.environ,CODEX_HOME=str(home)),stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
            try:
                deadline=time.monotonic()+8
                while not(home/'ready').exists():
                    if child.poll() is not None:raise RuntimeError(child.stderr.read().decode())
                    if time.monotonic()>deadline:raise RuntimeError('native fixture readiness timeout')
                    time.sleep(.01)
                (stock/'config.toml').write_text('model="second"\n')
                args=dict(source='stock',destinations=['alice'],categories=['settings'],operation_id='selected-reload',reload=True)
                preview=execute('configuration.sync.preview',args,root)
                args['expected_snapshot']=preview['result']['snapshot']
                result=execute('configuration.sync.apply',args,root)
                self.assertEqual(result['status'],'completed',result)
                self.assertEqual(result['result']['destinations'][0]['reload'],'requested_selected_profile')
                self.assertEqual((home/'reload-events').read_text(),'reload\n')
                self.assertIn('second',(home/'config.toml').read_text())
                self.assertIn('first',(homes['bob']/'config.toml').read_text())
                self.assertFalse((homes['bob']/'reload-events').exists())
                self.assertEqual(execute('configuration.sync.apply',args,root),result)
                self.assertEqual((home/'reload-events').read_text(),'reload\n')
                # The same selected native owner is reached from API and native MCP.
                import socket
                from types import SimpleNamespace
                from codex_wake.controller_accounts import ControllerAccounts
                from codex_wake.controller_auth import Actor
                from codex_wake.controller_http import ProtectedOperations
                from codex_wake.controller_operations import ControllerOperations
                from codex_wake.managed_inventory import ManagedInventory
                from codex_wake.mcp_server import CommandRunner
                host=socket.gethostname();environment=os.environ.get('WSL_DISTRO_NAME') or os.name
                accounts=ControllerAccounts(registry,host=host,environment=environment)
                targets=[dict(host=host,environment=environment,**{k:store[k] for k in ('store_id','home','home_generation')})
                         for store in accounts.execute('stores.list',{})['stores']]
                actor=Actor('fixture','service','fixture','grant','fixture','fixture',frozenset({'configuration.observe','control'}),targets,time.time()+60)
                protected=ProtectedOperations(SimpleNamespace(authenticate=lambda token:actor),ControllerOperations(ManagedInventory(root),host=host,environment=environment,accounts=accounts))
                config=dict(version=1,local_caller=dict(subject=actor.subject,client_id=actor.client_id,grant_id=actor.grant_id,issuer=actor.issuer,resource=actor.resource,scopes=sorted(actor.scopes),targets=targets,expires_at=actor.expires_at))
                (root/'controller-messaging.json').write_text(json.dumps(config))
                for index,transport in enumerate(('api','mcp'),start=2):
                    (stock/'config.toml').write_text('model="revision-'+transport+'"\n')
                    request=dict(source='stock',destinations=['alice'],categories=['settings'],operation_id=transport+'-reload',reload=True)
                    if transport=='api':
                        def dispatch(verb,arguments):return protected.execute('token','configuration.sync.'+verb,arguments)
                    else:
                        def dispatch(verb,arguments):
                            value,failed=CommandRunner(wake_root=root).call('wake_controller_configuration_sync_'+verb,arguments)
                            self.assertFalse(failed,value);return value
                    planned=dispatch('preview',request);request['expected_snapshot']=planned['result']['snapshot']
                    applied=dispatch('apply',request)
                    self.assertEqual(applied['result']['destinations'][0]['reload'],'requested_selected_profile')
                    self.assertEqual((home/'reload-events').read_text(),'reload\n'*index)
                    self.assertEqual(dispatch('apply',request),applied)
                    self.assertEqual((home/'reload-events').read_text(),'reload\n'*index)
                    self.assertIn('first',(homes['bob']/'config.toml').read_text())
            finally:
                child.terminate();child.wait(timeout=5);child.stderr.close()
