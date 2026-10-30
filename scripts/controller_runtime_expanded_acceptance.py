#!/usr/bin/env python3
"""Installed provider-free operation acceptance with real Mailbox/BackgroundJobs owners."""
import argparse
import hashlib
import base64
import socket
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import shutil
from contextlib import contextmanager
import time
from urllib.request import Request,urlopen
from urllib.error import HTTPError


def prepare(root):
    from codex_wake.a2a_bus import BusStore
    from codex_wake.a2a_identity import RuntimeIdentity
    from codex_wake.a2a_mailbox import Mailbox
    from codex_wake.managed_inventory import ManagedInventory, Observation
    from codex_wake.controller_operations import ControllerOperations
    root.mkdir(mode=0o700)
    work = root.parent / 'work'; work.mkdir(mode=0o700)
    bus, operator = BusStore.configure(root.parent / 'bus')
    bus.enroll(work, operator)
    natives, caps, actors = [], [], []
    for who,thread in (('sender','11111111-1111-4111-8111-111111111111'),('recipient','recipient')):
        native = RuntimeIdentity('account:' + who, thread, str(work))
        capability, _ = bus.issue_actor(native, work, operator)
        natives.append(native); caps.append(capability)
        actors.append(bus.authenticate(capability, native, invoking_cwd=work))
    Mailbox.migrate(bus, operator)
    inventory = ManagedInventory(root)
    enrolled = inventory.enroll(Observation('codex', 'account:recipient', 'recipient', str(work), 'ready', time.time(), 'native_metadata', {'pid': 123, 'start_ticks': 42, 'boot_id': 'synthetic'}, [], {}), operator=True)
    target = ControllerOperations(inventory, host='synthetic-host', environment='synthetic-linux').execute('inventory.resolve', {'selector':'recipient'})['result']['resource']['target']
    scope = {k:v for k,v in target.items() if k != 'process'}
    caller = dict(subject='synthetic-caller',client_id='synthetic-client',grant_id='synthetic-local-grant',issuer='local://fixture',resource='wake:controller',scopes=['control','observe'],targets=[scope],expires_at=time.time()+600)
    config = dict(version=1,host='synthetic-host',environment='synthetic-linux',local_caller=caller,
        bindings={'native-sender':dict(subject=caller['subject'],client_id=caller['client_id'],bus_root=str(bus.root),capability=str(caps[0]),identity=natives[0].__dict__)},
        recipients=[dict(target=target,identity=natives[1].__dict__)])
    path = root / 'controller-messaging.json'; path.write_text(json.dumps(config)); path.chmod(0o600)
    return dict(target=target,config=config,bus=bus,operator=operator,natives=natives,caps=caps,actors=actors,work=work,inventory=inventory,enrolled=enrolled)


@contextmanager
def fixture_directory(retain_on_failure):
    path = Path(tempfile.mkdtemp(prefix='wake-runtime401-'))
    try:
        yield str(path)
    except BaseException:
        if retain_on_failure:
            print('retained_private_disposable_fixture=' + str(path), file=sys.stderr)
        else:
            shutil.rmtree(path)
        raise
    else:
        shutil.rmtree(path)


def main(shared=False, retain_on_failure=False):
    import codex_wake
    from codex_wake.a2a_mailbox import Mailbox
    env = dict(os.environ); env.pop('PYTHONPATH', None)
    executable = str(Path(sys.executable).parent / 'codex-wake')
    prefix = [executable] if shared else [sys.executable,'-m','codex_wake.operation_commands']
    with fixture_directory(retain_on_failure) as directory:
        base = Path(directory); root = base / 'wake'
        fixture = prepare(root); target = fixture['target']
        def command(*args, expected=0):
            completed = subprocess.run([*prefix,'--wake-root',str(root),'operations',*args],env=env,cwd=base,text=True,capture_output=True,timeout=35)
            assert completed.returncode == expected,(completed.returncode,completed.stdout,completed.stderr)
            return completed
        body = base / 'question.txt'; body.write_text('native question')
        request = dict(operation_id='native-operation',idempotency_key='native-intent',correlation_id='native-correlation',binding='opaque-source-correlation',target=target)
        send = ['send','--request',json.dumps(request),'--sender-binding','native-sender','--body-file',str(body),'--delivery','inbox','--queue','--no-wait','--json']
        submitted = json.loads(command(*send).stdout)
        operation = submitted['result']['operation']; message_id = operation['result']['message_id']
        assert operation['execution'] == 'queued' and 'answer' not in operation
        timed = json.loads(command('wait','native-operation','--timeout','0','--json').stdout)
        assert timed['result']['wait'] == {'status':'timeout','ends_work':False}
        ready, release = base / 'worker-ready', base / 'release-worker'
        worker = base / 'recipient.py'
        worker.write_text('''import json,pathlib,sys,time
from codex_wake.a2a_bus import BusStore
from codex_wake.a2a_identity import RuntimeIdentity
from codex_wake.a2a_mailbox import Mailbox
bus=BusStore(sys.argv[1]); identity=RuntimeIdentity(**json.loads(sys.argv[3])); actor=bus.authenticate(pathlib.Path(sys.argv[2]),identity,invoking_cwd=pathlib.Path(identity.cwd)); mailbox=Mailbox(bus)
message=mailbox.list(actor)['messages'][0]; body=mailbox.read(actor,message['message_id'])['body']; mailbox.ack(actor,message['message_id'],outcome='accepted')
mailbox.reply(actor,message['message_id'],body='Recipient is processing actual native request',idempotency_key='native-progress',kind='notice',delivery='inbox')
pathlib.Path(sys.argv[4]).write_text('ready')
deadline=time.monotonic()+10
while not pathlib.Path(sys.argv[5]).exists():
 if time.monotonic()>deadline: raise RuntimeError('fixture release deadline')
 time.sleep(.01)
mailbox.reply(actor,message['message_id'],body='NATIVE ANSWER: '+body.upper(),idempotency_key='native-final',kind='result',delivery='inbox',outcome='completed')
''')
        recipient = subprocess.Popen([sys.executable,str(worker),str(fixture['bus'].root),str(fixture['caps'][1]),json.dumps(fixture['natives'][1].__dict__),str(ready),str(release)],env=env,cwd=base,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        try:
            deadline = time.monotonic()+5
            while not ready.exists():
                if time.monotonic()>deadline: raise AssertionError('native recipient did not process request')
                time.sleep(.01)
            stream = json.loads(command('stream','native-operation','--json').stdout)
            assert any(e.get('text')=='Recipient is processing actual native request' for e in stream['result']['events'])
            assert 'answer' not in stream['result']['operation']
            waiting = subprocess.Popen([*prefix,'--wake-root',str(root),'operations','wait','native-operation','--timeout','30','--json'],env=env,cwd=base,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            waiting.terminate(); waiting.wait(timeout=5)
            assert recipient.poll() is None  # Caller loss leaves the native owner alive.
            release.write_text('finish')
            out, err = recipient.communicate(timeout=5)
            assert recipient.returncode==0,(out,err)
            answered = command('wait','native-operation','--timeout','5')
            assert answered.stdout=='NATIVE ANSWER: NATIVE QUESTION\n',answered.stdout
            status = json.loads(answered.stderr)
            assert status['event']=='operation_status' and status['correlation_id']=='native-correlation'
            assert 'NATIVE ANSWER' not in answered.stderr
            final = json.loads(command('result','native-operation','--json').stdout)
            assert final['result']['operation']['answer']['text']=='NATIVE ANSWER: NATIVE QUESTION'
            assert command(*send).returncode==0
            assert len(Mailbox(fixture['bus']).list(fixture['actors'][0],outbox=True)['messages'])==1
            assert Mailbox(fixture['bus']).replies(fixture['actors'][0],message_id)[-1]['recipient']['thread_id']==fixture['natives'][0].thread_id
            cursor=stream['result']['next_cursor']
            events=json.loads(command('stream','native-operation','--cursor',str(cursor),'--json').stdout)['result']['events']
            assert [e['kind'] for e in events]==['answer']
        finally:
            if recipient.poll() is None: recipient.kill(); recipient.wait()
        job_target = prepare_job(root, fixture)
        job_request = dict(operation_id='job-operation',idempotency_key='job-intent',correlation_id='job-correlation',binding='opaque-job-caller',target=job_target)
        launched=json.loads(command('send','--request',json.dumps(job_request),'--sender-binding','native-job','--backend','job','--job-profile','synthetic','--no-wait','--json').stdout)
        assert launched['result']['operation']['result']['kind']=='background_job'
        answer=command('wait','job-operation','--timeout','5')
        assert answer.stdout=='SUPERVISED FINAL ANSWER\n',answer.stdout
        assert 'SUPERVISED FINAL ANSWER' not in answer.stderr
        default_request=dict(job_request,operation_id='default-job',idempotency_key='default-job',correlation_id='default-job')
        default_answer=command('send','--request',json.dumps(default_request),'--sender-binding','native-job','--backend','job','--job-profile','synthetic')
        assert default_answer.stdout=='SUPERVISED FINAL ANSWER\n' and 'SUPERVISED FINAL ANSWER' not in default_answer.stderr
        if shared: qualify_public(root,fixture,job_target,env,base)
        print(json.dumps(dict(status='passed',package=codex_wake.__file__,python=sys.executable,shared_cli=shared,
            command=[*prefix,'--wake-root','<private-disposable-root>','operations'],
            checks=['actual native Mailbox admission and result reply body','queue/acceptance is not answer','caller timeout and process loss preserve target work','late native answer returns stdout, progress stderr','native reply routes to original sending identity with correlation','same intent has one native message','bounded stream cursor suppresses duplicate progress','actual existing BackgroundJobs supervisor returns stdout after submitter exit','default response-requested send waits for actual final stdout'] + (['actual installed stdio MCP native sender verification and result','actual OAuth API/MCP/remote CLI send/wait/result','same-grant refresh retrieves retained answer','revocation cancels only original queued messages and supervised jobs, peer survives'] if shared else []),
            source_sha256={name:hashlib.sha256((Path(codex_wake.__file__).parent/name).read_bytes()).hexdigest() for name in ('controller_runtime.py','controller_mailbox.py','controller_job_adapter.py','operation_commands.py','controller_http.py','controller_auth.py','mcp_server.py','cli.py')},
            live_provider=False,provider_credentials=False,shared_service=False),sort_keys=True))


def prepare_job(root, fixture):
    from codex_wake.background_jobs import BackgroundJobs
    from codex_wake.session_permissions import Principal, PermissionStore
    from codex_wake.task_briefs import TaskBriefStore, BriefAuthority
    operator=Principal('synthetic-operator','operator')
    PermissionStore(root).configure({'version':1,'global':{'actions':{'job.launch':'allow','job.cancel':'allow'}}},operator,expected_revision=0)
    authority=BriefAuthority('synthetic-operator','operator'); briefs=TaskBriefStore(root)
    briefs.propose('synthetic-task',dict(objective='Bounded synthetic command',phase='test',non_goals=['No providers'],acceptance=['Actual stdout retained'],context=[],workspace=str(fixture['work']),allocation_ref='synthetic',permission_ref='synthetic'),authority=authority)
    briefs.approve('synthetic-task',1,authority=authority);briefs.admit('synthetic-task','synthetic-assignment',authority=authority)
    profile=BackgroundJobs(root).approve_command('synthetic',[sys.executable,'-c',"import time;time.sleep(1.5);print('SUPERVISED FINAL ANSWER')"],fixture['work'],principal=operator,task_pin=briefs.assignment_pin('synthetic-task','synthetic-assignment'),owner='synthetic-worker',max_seconds=4,max_log_bytes=1024)
    target=dict(host='synthetic-host',environment='synthetic-linux',namespace='jobs',conversation_id='synthetic',configuration_revision=profile['sha256'])
    path=root/'controller-messaging.json';config=json.loads(path.read_text());config['local_caller']['targets'].append(target)
    config['job_bindings']={'native-job':dict(subject=config['local_caller']['subject'],client_id=config['local_caller']['client_id'],native_subject='synthetic-worker',tasks=['synthetic-task'],profile='synthetic',target=target)}
    path.write_text(json.dumps(config))
    return target


def qualify_public(root,fixture,job_target,env,base):
    import asyncio
    from codex_wake.a2a_mailbox import Mailbox
    from codex_wake.background_jobs import BackgroundJobs
    executable=str(Path(sys.executable).parent/'codex-wake')
    mailbox=Mailbox(fixture['bus'])
    sender=fixture['natives'][0].thread_id
    def meta():return dict(threadId=sender,sessionId=sender,callId='synthetic-call',**{'x-codex-turn-metadata':dict(thread_id=sender,session_id=sender,turn_id='synthetic-turn')})
    def request(identifier,target):return dict(operation_id=identifier,idempotency_key=identifier,correlation_id='correlation-'+identifier,binding='opaque-'+identifier,target=target)
    def mail_args(identifier,binding='native-sender'):
        return dict(_request=request(identifier,fixture['target']),sender_binding=binding,expected_target=fixture['target'],body='actual '+identifier,delivery='inbox',queue=True,response_requested=False)
    def answer(operation,text_prefix):
        message_id=operation['result']['message_id'];body=mailbox.read(fixture['actors'][1],message_id)['body']
        mailbox.ack(fixture['actors'][1],message_id,outcome='accepted')
        mailbox.reply(fixture['actors'][1],message_id,body=text_prefix+body.upper(),idempotency_key='answer-'+operation['operation_id'],kind='result',delivery='inbox',outcome='completed')
        return text_prefix+body.upper()
    async def native():
        from mcp import ClientSession,StdioServerParameters
        from mcp.client.stdio import stdio_client
        parameters=StdioServerParameters(command=str(Path(sys.executable).parent/'codex-wake-mcp'),args=['--wake-root',str(root)],env=env)
        async with stdio_client(parameters) as (reader,writer):
            async with ClientSession(reader,writer) as session:
                await session.initialize()
                assert {'wake_operations_send','wake_operations_result','wake_operations_wait','wake_operations_stream','wake_operations_cancel','wake_operations_rebind'} <= {t.name for t in (await session.list_tools()).tools}
                denied=await session.call_tool('wake_operations_send',mail_args('mcp-no-identity'))
                assert denied.is_error
                sent=await session.call_tool('wake_operations_send',mail_args('mcp-native'),meta=meta())
                assert not sent.is_error,sent
                operation=json.loads(sent.content[0].text)['result']['operation']
                assert mailbox.show(fixture['actors'][0],operation['result']['message_id'])['sender']['thread_id']==sender
                timed=await session.call_tool('wake_operations_wait',dict(operation_id='mcp-native',timeout=0))
                assert json.loads(timed.content[0].text)['result']['wait']['status']=='timeout'
                expected=answer(operation,'MCP ANSWER: ')
                result=await session.call_tool('wake_operations_result',dict(operation_id='mcp-native'))
                assert not result.is_error and json.loads(result.content[0].text)['result']['operation']['answer']['text']==expected
    asyncio.run(native())
    sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1];sock.close()
    endpoint='http://127.0.0.1:'+str(port);resource=endpoint+'/controller'
    def controller(*args):
        process=subprocess.run([executable,'--wake-root',str(root),'controller',*args],env=env,cwd=base,text=True,capture_output=True,timeout=35)
        assert process.returncode==0,(process.returncode,process.stdout,process.stderr)
        return json.loads(process.stdout)
    controller('auth-configure','--issuer',endpoint,'--resource',resource,'--owner','synthetic-caller')
    server=subprocess.Popen([executable,'--wake-root',str(root),'controller','serve','--port',str(port)],env=env,cwd=base,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    def http(path,body=None,token=None):
        headers={'Content-Type':'application/json'}
        if token:headers['Authorization']='Bearer '+token
        req=Request(endpoint+path,data=None if body is None else json.dumps(body).encode(),headers=headers)
        try:
            with urlopen(req,timeout=35) as response:return response.status,json.load(response)
        except HTTPError as error:return error.code,json.load(error)
    try:
        for _ in range(100):
            try:
                if http('/.well-known/oauth-protected-resource')[0]==200:break
            except OSError:pass
            time.sleep(.02)
        else:raise AssertionError('private listener unavailable')
        client=http('/register',{'redirect_uris':['http://127.0.0.1:45000/callback']})[1]
        path=root/'controller-messaging.json';config=json.loads(path.read_text())
        config['bindings']['oauth-sender']=dict(config['bindings']['native-sender'],client_id=client['client_id'])
        config['job_bindings']['oauth-job']=dict(config['job_bindings']['native-job'],client_id=client['client_id'])
        path.write_text(json.dumps(config))
        verifier='x'*43;challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
        scopes=[{k:v for k,v in fixture['target'].items() if k!='process'},job_target]
        def tokens():
            code=controller('authorize-client','--client-id='+client['client_id'],'--redirect-uri',client['redirect_uris'][0],'--subject','synthetic-caller','--principal-kind','service','--scope','control','--scope','observe','--targets',json.dumps(scopes),'--code-challenge',challenge)['code']
            status,value=http('/token',dict(grant_type='authorization_code',client_id=client['client_id'],redirect_uri=client['redirect_uris'][0],code=code,code_verifier=verifier,resource=resource));assert status==200,value
            return value
        original=tokens();token=original['access_token']
        def api(operation,args,bearer=None):return http('/operations',dict(operation=operation,arguments=args),token if bearer is None else bearer)
        initialized=http('/mcp',dict(jsonrpc='2.0',id=1,method='initialize',params={'protocolVersion':'2025-03-26','capabilities':{},'clientInfo':{'name':'synthetic','version':'1'}}),token)
        assert initialized[0]==200
        def mcp_call(name,arguments):
            status,value=http('/mcp',dict(jsonrpc='2.0',id=2,method='tools/call',params={'name':name,'arguments':arguments}),token)
            assert status==200 and not value['result']['isError'],value
            return value['result']['structuredContent']
        private=base/'oauth.token';private.write_text(token);private.chmod(0o600)
        def remote(operation,args):return controller('remote','--endpoint',endpoint,'--token-file',str(private),operation,'--arguments',json.dumps(args))
        before=len(mailbox.list(fixture['actors'][0],outbox=True)['messages'])
        send_args=mail_args('oauth-native','oauth-sender')
        sent=api('operations.send',send_args)
        assert sent[0]==200,sent
        operation=sent[1]['result']['operation']
        assert mcp_call('wake_operations_send',send_args)['result']['operation']['result']['message_id']==operation['result']['message_id']
        assert remote('operations.send',send_args)['result']['operation']['result']['message_id']==operation['result']['message_id']
        assert len(mailbox.list(fixture['actors'][0],outbox=True)['messages'])==before+1
        timed=api('operations.wait',dict(operation_id='oauth-native',timeout=0))
        assert timed[1]['result']['wait']==dict(status='timeout',ends_work=False)
        assert mcp_call('wake_operations_wait',dict(operation_id='oauth-native',timeout=0))['result']['wait']['status']=='timeout'
        assert remote('operations.wait',dict(operation_id='oauth-native',timeout=0))['result']['wait']['status']=='timeout'
        expected=answer(operation,'API ANSWER: ')
        result=api('operations.result',dict(operation_id='oauth-native'))
        assert result[0]==200 and result[1]['result']['operation']['answer']['text']==expected,result
        initialized=http('/mcp',dict(jsonrpc='2.0',id=1,method='initialize',params={'protocolVersion':'2025-03-26','capabilities':{},'clientInfo':{'name':'synthetic','version':'1'}}),token)
        assert initialized[0]==200
        mcp=http('/mcp',dict(jsonrpc='2.0',id=2,method='tools/call',params={'name':'wake_operations_result','arguments':{'operation_id':'oauth-native'}}),token)
        assert mcp[0]==200 and mcp[1]['result']['structuredContent']['result']['operation']['answer']['text']==expected,mcp
        private=base/'oauth.token';private.write_text(token);private.chmod(0o600)
        remote=controller('remote','--endpoint',endpoint,'--token-file',str(private),'operations.result','--arguments',json.dumps({'operation_id':'oauth-native'}))
        assert remote['result']['operation']['answer']['text']==expected
        status,rotated=http('/token',dict(grant_type='refresh_token',client_id=client['client_id'],refresh_token=original['refresh_token'],resource=resource));assert status==200
        assert api('operations.result',dict(operation_id='oauth-native'))[0]==401
        token=rotated['access_token']
        assert api('operations.result',dict(operation_id='oauth-native'))[1]['result']['operation']['answer']['text']==expected
        peer=tokens()['access_token']
        original_queue=api('operations.send',mail_args('revoked-queue','oauth-sender'))[1]['result']['operation']
        peer_queue=api('operations.send',mail_args('peer-queue','oauth-sender'),peer)[1]['result']['operation']
        def job_args(key):return dict(_request=request(key,job_target),expected_target=job_target,sender_binding='oauth-job',backend='job',job_profile='synthetic',response_requested=False)
        original_job=api('operations.send',job_args('revoked-job'))[1]['result']['operation']
        peer_job=api('operations.send',job_args('peer-job'),peer)[1]['result']['operation']
        status,_=http('/revoke',dict(token=token,client_id=client['client_id']));assert status==200
        assert mailbox.show(fixture['actors'][0],original_queue['result']['message_id'])['state']['admission']=='cancelled'
        assert mailbox.show(fixture['actors'][0],peer_queue['result']['message_id'])['state']['admission']=='accepted'
        assert api('operations.result',dict(operation_id='revoked-job'))[0]==401
        jobs=BackgroundJobs(root);deadline=time.monotonic()+5
        while jobs.inspect(original_job['result']['job_id'])['status'] not in ('cancelled','completed','failed','timed_out') and time.monotonic()<deadline:time.sleep(.02)
        assert jobs.inspect(original_job['result']['job_id'])['status']=='cancelled'
        surviving=api('operations.wait',dict(operation_id='peer-job',timeout=5),peer)
        assert surviving[0]==200 and surviving[1]['result']['operation']['answer']['text']=='SUPERVISED FINAL ANSWER\n',surviving
    finally:
        server.terminate();server.wait(timeout=5)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--shared-cli',action='store_true');parser.add_argument('--retain-on-failure',action='store_true');args=parser.parse_args();main(args.shared_cli, args.retain_on_failure)
