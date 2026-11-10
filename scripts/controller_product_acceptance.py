#!/usr/bin/env python3
"""Installed Wake account/daemon/import demonstration; synthetic history, no model turns.

Run under the separate Linux test user inside unshare -Urn. The caller supplies
complete public packages and a NEW retained artifact directory. Never use a live
Wake root. Native seed RPCs only prepare declared synthetic saved conversations;
all lifecycle and cross-account transfer effects go through installed Wake.
"""
import argparse
import base64
from datetime import datetime, timezone
import hashlib
import json
import os
import pty
import select
import signal
import struct
import fcntl
import termios
from pathlib import Path
import socket
import subprocess
import sys
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from uuid import uuid4


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--modded', type=Path, required=True)
    p.add_argument('--stock', type=Path, required=True)
    p.add_argument('--outer-netns', required=True, help='network namespace identity read by the outer launcher')
    args = p.parse_args()
    root = args.root.absolute()
    root.mkdir(mode=0o700, exist_ok=False)
    if os.readlink('/proc/self/ns/net') == args.outer_netns:
        raise RuntimeError('external network must be isolated with unshare -Urn')
    subprocess.run(['ip','link','set','lo','up'],check=True,timeout=5)
    cli = str(Path(sys.executable).parent / 'codex-wake')
    env = {k: os.environ[k] for k in ('PATH', 'LANG', 'TERM') if k in os.environ}
    for key in ('HOME','XDG_CONFIG_HOME','XDG_DATA_HOME','XDG_STATE_HOME','XDG_CACHE_HOME'):
        directory = root / key.lower()
        directory.mkdir(mode=0o700)
        env[key] = str(directory)
    os.environ.clear()
    os.environ.update(env)
    os.environ.pop('PYTHONPATH', None)
    events, server, owned, clients = [], None, [], []
    def record(kind, value):
        events.append(dict(kind=kind, value=value))
        with (root / 'events.jsonl').open('a') as stream:
            stream.write(json.dumps(events[-1], sort_keys=True) + '\n')
    def call(*command, check=True):
        if command and command[0] in ('daemons', 'builds', 'history') and '--json' not in command:
            command = (*command, '--json')
        result = subprocess.run([cli, '--wake-root', str(root), *command], env=env,
            capture_output=True, text=True, timeout=125)
        value = json.loads(result.stdout)
        # Auth codes are temporary secrets, never retained in command receipts.
        if command[:2] != ('controller','authorize-client'):
            record('cli', dict(command=command, exit_code=result.returncode, result=value, stderr=result.stderr[-2000:]))
        if check:
            assert result.returncode == 0, value
        return value
    def daemon(name, channel='modded'):
        return call('daemons','status',name,'--channel',channel)['result']['daemon']
    def mutate(verb, name, key, channel='modded'):
        before = daemon(name, channel)
        arguments = ('daemons',verb,name,'--channel',channel,'--expected-target',json.dumps(before['target']),
                     '--idempotency-key',key,'--yes')
        value = call(*arguments)
        operation = value['result']['operation']
        assert operation['execution'] == 'completed', operation
        return operation['result']['daemon'], arguments, operation
    from codex_wake.native_protocol import native_request
    def rpc(daemon, method, params):
        value = native_request(daemon['endpoint'],daemon['target']['executable'],method,params,10)
        record('native_saved_history',dict(account=daemon['account'],method=method,result=value))
        return value
    def read(daemon, thread):
        return rpc(daemon,'thread/read',dict(threadId=thread,includeTurns=True))['thread']
    def seed(daemon, who):
        thread = str(uuid4());stamp=datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
        turn = str(uuid4())
        question, answer = 'SYNTHETIC '+who+' question', 'SYNTHETIC '+who+' saved answer'
        rows=[dict(type='session_meta',payload=dict(id=thread,timestamp=stamp,cwd=str(root),originator='codex_cli_rs',cli_version='0.166.0',source='cli',model_provider='openai'))]
        for payload in (dict(type='task_started',turn_id=turn,model_context_window=200000),
            dict(type='user_message',message=question,images=[],local_images=[],text_elements=[]),
            dict(type='agent_message',message=answer,phase='final_answer'),
            dict(type='task_complete',turn_id=turn,last_agent_message=answer)):
            rows.append(dict(type='event_msg',payload=payload))
        path=root/(who+'-seed.jsonl')
        path.write_text(''.join(json.dumps(dict(timestamp=stamp,**row))+'\n' for row in rows))
        result=rpc(daemon,'thread/fork',dict(threadId=thread,path=str(path),ephemeral=False,approvalPolicy='never',sandbox='read-only'))
        child=result['thread']['id']
        native=read(daemon,child)
        assert answer in json.dumps(native['turns']), native
        return child
    def open_tui(name, thread, marker, label):
        target = next(row['target'] for row in call('builds','list','--arguments',json.dumps({'account':name}))['result']['builds'] if row['name']=='modded')
        master, slave = pty.openpty()
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH',45,140,0,0))
        arguments=dict(account=name,channel='modded',expected_target=target,
                       args=['--no-alt-screen','-C',str(root),'resume',thread])
        process=subprocess.Popen([cli,'--wake-root',str(root),'builds','launch','--arguments',json.dumps(arguments)],
            env=dict(env,TERM='xterm-256color'),stdin=slave,stdout=slave,stderr=slave,start_new_session=True)
        os.close(slave)
        client=dict(process=process,master=master,label=label,content=b'')
        clients.append(client)
        deadline=time.monotonic()+25
        while time.monotonic()<deadline:
            if select.select([master],[],[],.1)[0]:
                try:chunk=os.read(master,65536)
                except OSError:break
                if not chunk:break
                client['content']+=chunk
                if b'\x1b[6n' in chunk:os.write(master,b'\x1b[1;1R')
                if marker.encode() in client['content']:
                    record('tui',dict(account=name,thread_id=thread,pid=process.pid,visible=marker,label=label))
                    return client
            if process.poll() is not None:break
        (root/(label+'.ansi')).write_bytes(client['content'])
        raise AssertionError('native TUI did not display saved history: '+label)
    def close_tui(client):
        process=client['process']
        if process.poll() is None:
            for unused in range(2):
                os.write(client['master'],b'\x03')
                try:process.wait(timeout=2);break
                except subprocess.TimeoutExpired:pass
        if process.poll() is None:
            os.killpg(process.pid,signal.SIGTERM)
            try:process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid,signal.SIGKILL);process.wait(timeout=3)
        (root/(client['label']+'.ansi')).write_bytes(client['content'])
        os.close(client['master']);clients.remove(client)
    receipt = dict(status='incomplete',provider_model_turns=0,real_authenticated_accounts=False,
                   host_uid=int(Path('/proc/self/uid_map').read_text().split()[1]),namespace_uid=os.getuid(),root=str(root))
    try:
        call('accounts','init','--json')
        call('accounts','create','alice','--alias','work','--json')
        call('accounts','create','bob','--json')
        shared=root/'accounts/shared/config.toml'
        shared.write_text('model="gpt-5.1"\nmodel_provider="offline_demo"\ncheck_for_update_on_startup=false\n[analytics]\nenabled=false\n[model_providers.offline_demo]\nname="Provider-free saved-history demonstration"\nbase_url="http://127.0.0.1:9/v1"\nwire_api="responses"\nrequires_openai_auth=false\n[projects.'+json.dumps(str(root))+']\ntrust_level="trusted"\n')
        manifest = dict(schema_version=1,builds={})
        for channel,package in (('modded',args.modded),('stock',args.stock)):
            binary=package.absolute()/'bin/codex'
            manifest['builds'][channel]=dict(executable=str(binary),sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),
                upstream_version='0.166.0',revision=channel+'-166',source=('https://github.com/openai/codex/releases/download/rust-v0.166.0/codex-package-x86_64-unknown-linux-musl.tar.gz' if channel=='stock' else 'qualified-modified166'),read_schemas=[5],backend='managed')
        (root/'builds.json').write_text(json.dumps(manifest))
        with (root/'controller-accounts.toml').open('a') as stream:
            stream.write(f'\n[builds]\nmanifest={json.dumps(str(root/"builds.json"))}\n[history]\nreadable_accounts=["alice","bob"]\n')
        config=call('configuration','explain','work','--json')['result']
        assert config['configuration']['settings']['shared'] and config['configuration']['skills']['shared']
        receipt['configuration_provenance']=config['configuration']
        a,unused,unused_op=mutate('start','alice','start-alice');owned.append('alice')
        b,unused,unused_op=mutate('start','bob','start-bob');owned.append('bob')
        assert a['target']['process'] != b['target']['process'] and a['endpoint']!=b['endpoint']
        first,second=seed(a,'alice'),seed(b,'bob')
        source_path=Path(read(a,first)['path']);source_bytes=source_path.read_bytes()
        source=call('history','read',first,'--owner','alice')['result']['session']['target']
        import_args=('history','import',first,'--owner','alice','--destination','bob','--channel','modded',
                     '--expected-source',json.dumps(source),'--expected-target',json.dumps(b['target']),'--idempotency-key','cli-import')
        imported=call(*import_args)['result']['operation']
        assert imported['execution']=='completed',imported
        child=imported['result']['thread_id']
        assert child not in (first,second)
        assert 'SYNTHETIC alice saved answer' in json.dumps(read(b,child)['turns'])
        listing=rpc(b,'thread/list',dict(limit=100,archived=False))
        assert child in [r['id'] for r in listing['data']]
        assert call(*import_args)['result']['operation']['result']['thread_id']==child
        assert source_path.read_bytes()==source_bytes
        receipt['import']=dict(source=first,destination=child,source_unchanged=True,native_destination_visible=True,native_destination_opened=True,repeat_same_child=True)
        # Real OAuth listener and grants exercise the same protected owner via API and MCP.
        sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1];sock.close()
        base='http://127.0.0.1:'+str(port);resource=base+'/controller'
        call('controller','auth-configure','--issuer',base,'--resource',resource,'--owner','synthetic-owner')
        server_log=(root/'controller.log').open('w')
        server=subprocess.Popen([cli,'--wake-root',str(root),'controller','serve','--port',str(port)],env=env,stdout=server_log,stderr=server_log)
        def http(path,body=None,token=None):
            headers={'Content-Type':'application/json'}
            if token:headers['Authorization']='Bearer '+token
            try:
                with urlopen(Request(base+path,data=json.dumps(body).encode() if body is not None else None,headers=headers),timeout=120) as response:return response.status,json.load(response)
            except HTTPError as error:return error.code,json.load(error)
        until=time.monotonic()+10
        while True:
            try:
                assert http('/.well-known/oauth-authorization-server')[0]==200;break
            except OSError:
                if time.monotonic()>until:raise
                time.sleep(.05)
        client=http('/register',{'redirect_uris':['http://127.0.0.1:45000/callback']})[1]
        def token(targets,scopes):
            verifier='x'*43;challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
            command=['controller','authorize-client','--client-id',client['client_id'],'--redirect-uri',client['redirect_uris'][0],
                '--subject','synthetic-owner','--principal-kind','owner','--targets',json.dumps(targets),'--code-challenge',challenge]
            for scope in scopes:command+=['--scope',scope]
            code=call(*command)['code']
            return http('/token',dict(grant_type='authorization_code',client_id=client['client_id'],redirect_uri=client['redirect_uris'][0],
                resource=resource,code=code,code_verifier=verifier))[1]['access_token']
        bearer=token([a['target'],b['target'],source],['control','observe','history.observe'])
        def api(op,arguments):
            status,value=http('/operations',dict(operation=op,arguments=arguments),bearer)
            assert status==200,value
            record('api',dict(operation=op,result=value));return value
        def mcp(name,arguments):
            status,value=http('/mcp',dict(jsonrpc='2.0',id=1,method='tools/call',params=dict(name=name,arguments=arguments)),bearer)
            assert status==200 and not value['result']['isError'],value
            value=value['result']['structuredContent'];record('oauth_mcp',dict(tool=name,result=value));return value
        assert api('daemons.status',dict(account='bob'))['result']['daemon']==b
        assert mcp('wake_daemons_status',dict(account='bob'))['result']['daemon']==b
        transfer=dict(owner='alice',thread_id=first,destination='bob',channel='modded',expected_source=source,expected_target=b['target'],
            _request=dict(operation_id='oauth-import',idempotency_key='oauth-import',correlation_id='oauth-import',binding='demo',target=b['target']))
        api_copy=api('history.import',transfer)['result']['operation']
        assert api_copy['execution']=='completed',api_copy
        assert mcp('wake_controller_history_import',transfer)['result']['operation']==api_copy
        receipt['oauth_api_mcp_parity']=True
        # Native stdio MCP uses the explicit host-local grant, not caller text.
        local=dict(subject='synthetic-stdio',client_id='demo',grant_id='demo',issuer='local://demo',resource='wake:controller',
                   scopes=['observe'],targets=[b['target']],expires_at=time.time()+600)
        grant=root/'controller-messaging.json'
        grant.write_text(json.dumps(dict(version=1,local_caller=local)))
        grant.chmod(0o600)
        async def stdio_observation():
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client
            parameters=StdioServerParameters(command=str(Path(sys.executable).parent/'codex-wake-mcp'),args=['--wake-root',str(root)],env=env)
            async with stdio_client(parameters) as (reader,writer):
                async with ClientSession(reader,writer) as session:
                    await session.initialize()
                    result=await session.call_tool('wake_daemons_status',{'account':'bob'})
                    assert not result.is_error,result
                    value=json.loads(result.content[0].text)
                    assert value['result']['daemon']==b
                    record('native_stdio_mcp',value)
        import asyncio
        asyncio.run(stdio_observation())
        receipt['native_stdio_mcp_parity']=True

        first_client=open_tui('alice',first,'SYNTHETIC alice saved answer','alice-before-restart')
        peer_client=open_tui('bob',second,'SYNTHETIC bob saved answer','bob-concurrent')
        imported_client=open_tui('bob',child,'SYNTHETIC alice saved answer','bob-imported')
        close_tui(imported_client)
        receipt['concurrent_native_tuis']=True
        observed_peer=daemon('bob')
        assert {k:v for k,v in observed_peer['target'].items() if k!='configuration_revision'} == {k:v for k,v in b['target'].items() if k!='configuration_revision'}
        if observed_peer['target']['configuration_revision']!=b['target']['configuration_revision']:
            record('native_shared_configuration_update',dict(reason='native TUI persisted screen-reader detection setting; process/home/socket/build unchanged'))
        b=observed_peer
        # Scoped restart then native reconnect/history, preserving the peer generation.
        a,arguments,restarted=mutate('restart','alice','restart-alice')
        assert call(*arguments)['result']['operation']==restarted
        assert daemon('bob')['target']==b['target']
        assert 'SYNTHETIC alice saved answer' in json.dumps(read(a,first)['turns'])
        assert 'SYNTHETIC bob saved answer' in json.dumps(read(b,second)['turns'])
        assert peer_client['process'].poll() is None
        close_tui(first_client)
        reconnected=open_tui('alice',first,'SYNTHETIC alice saved answer','alice-reconnected')
        close_tui(reconnected)
        receipt['restart_reconnect_peer_preserved']=True
        # Supported native package update supplies explicit stock fallback and return.
        stock,unused,unused_op=mutate('update','alice','stock-fallback','stock')
        assert stock['running_sha256']==manifest['builds']['stock']['sha256']
        assert 'SYNTHETIC alice saved answer' in json.dumps(read(stock,first)['turns'])
        assert daemon('bob')['target']==b['target']
        mutate('stop','alice','stop-stock-before-compatible-return','stock')
        mutate('update','alice','compatible-return','modded')
        a,unused,unused_op=mutate('start','alice','start-compatible-return','modded')
        assert a['running_sha256']==manifest['builds']['modded']['sha256']
        assert 'SYNTHETIC alice saved answer' in json.dumps(read(a,first)['turns'])
        assert daemon('bob')['target']==b['target']
        receipt.update(status='passed',accounts=2,actual_daemons=2,stock_modded_rollback=True,
                       build_hashes={key:value['sha256'] for key,value in manifest['builds'].items()},
                       conversations=dict(alice=first,bob=second,imported=child))
    except BaseException as error:
        receipt.update(status='failed',error=type(error).__name__+': '+str(error))
        raise
    finally:
        if server is not None:
            server.terminate();server.wait(timeout=10);server_log.close()
        for client in clients[:]:close_tui(client)
        cleanup=[]
        for name in reversed(owned):
            try:
                current=daemon(name)
                if current['state']=='running':
                    channel='modded' if current['selected_build_running'] else 'stock'
                    final,unused,op=mutate('stop',name,'cleanup-'+name,channel)
                    cleanup.append(dict(account=name,state=final['state'],execution=op['execution']))
            except Exception as error:cleanup.append(dict(account=name,error=str(error)))
        receipt['cleanup']=cleanup
        (root/'receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
        print(json.dumps(dict(status=receipt['status'],receipt=str(root/'receipt.json'),cleanup=cleanup)),flush=True)


if __name__=='__main__':main()
