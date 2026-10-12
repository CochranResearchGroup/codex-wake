"""Opt-in isolated installed handoff/preflight/goal probe; never shared services."""
from __future__ import annotations
import argparse
from datetime import UTC,datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time
import tomllib

from codex_wake.native_clock import snapshot
from codex_wake.native_protocol import native_request
from agent_handoff_writer_acceptance import write


def execute(root,prefix,repo,parent_deadline):
    root.mkdir(mode=0o700,parents=True,exist_ok=False)
    workspace=root/'workspace';workspace.mkdir();home=root/'codex-home';home.mkdir(mode=0o700)
    codex=Path(subprocess.check_output(['which','codex'],text=True).strip()).resolve()
    config=tomllib.loads((Path.home()/'.codex/config.toml').read_text())
    selected={k:config[k] for k in ('model','model_reasoning_effort','model_provider') if k in config}
    lines=[f'{k} = {json.dumps(v)}' for k,v in selected.items()]
    lines+=['approval_policy = "never"','sandbox_mode = "workspace-write"',f'[projects.{json.dumps(str(workspace))}]','trust_level = "trusted"']
    (home/'config.toml').write_text('\n'.join(lines)+'\n');(home/'auth.json').symlink_to(Path.home()/'.codex/auth.json')
    skill=home/'skills/codex-wake';shutil.copytree(repo/'skills/codex-wake',skill)
    workflow=Path.home()/'.codex/plugins/cache/created-by-me-remote/chatgpt-github-engineering/0.1.0/skills/github-handoff/SKILL.md'
    guide=skill/'SKILL.md';helper=workspace/'preflight.py';profiles=root/'profiles.json'
    head=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()
    receipt=dict(state='preparing',root=str(root),prefix=str(prefix),source_commit=head,
        selected_model=selected,authority='operator execute Plan0156; isolated bounded continuation fixture',
        token_cap=250000,time_cap_seconds=600,manual_assignment_limit=2)
    env=dict(os.environ,CODEX_HOME=str(home),XDG_STATE_HOME=str(root/'state'))
    for k in ('CODEX_THREAD_ID','TMUX','TMUX_PANE','CODEX_WAKE_A2A_CAPABILITY','CODEX_WAKE_A2A_BUS_ROOT','CODEX_WAKE_SENDER_RECEIPT_AUTHORITY','PYTHONPATH'):env.pop(k,None)
    socket=root/'tmux.sock';session='owned-handoff';locator=root/'native.sock';server=None;monitor=None;created=False
    log=(root/'server.log').open('w');mlog=(root/'monitor.log').open('w')
    def launch_server():
        proc=subprocess.Popen([str(codex),'app-server','--listen','unix://'+str(locator)],env=env,stdout=log,stderr=log,start_new_session=True)
        deadline=time.monotonic()+15
        while not locator.exists() and proc.poll() is None and time.monotonic()<deadline:time.sleep(.1)
        if not locator.exists():raise RuntimeError('owned native socket unavailable')
        return proc
    def invoke(args):
        p=subprocess.run([str(prefix/'bin/codex-wake'),'--wake-root',str(root/'wake'),*args],env=env,text=True,capture_output=True,timeout=40)
        if not p.stdout:raise RuntimeError('installed CLI empty response '+p.stderr[-300:])
        return p.returncode,json.loads(p.stdout)
    def usage(thread):
        native=request('thread/read',dict(threadId=thread,includeTurns=True))['thread']
        path=Path(native['path']).resolve();path.relative_to(home/'sessions')
        values=[]
        for line in path.read_text().splitlines():
            e=json.loads(line);p=e.get('payload',{});i=p.get('info') or {}
            if e.get('type')=='event_msg' and p.get('type')=='token_count' and i.get('total_token_usage'):values.append(i['total_token_usage'])
        if not values:raise RuntimeError('native cumulative usage unavailable')
        return native,values[-1]
    try:
        bounds=snapshot().get('utc')
        if not bounds:raise RuntimeError('admissible UTC unavailable')
        started=bounds['upper'];end=min(started+600,parent_deadline-60)
        if end-started<480:raise RuntimeError('parent deadline leaves insufficient fixed fixture window')
        expiry=datetime.fromtimestamp(end,UTC).isoformat();receipt.update(started_at=started,deadline=end)
        # Resolve the owned listener before configuring MCP, without creating a thread.
        server=launch_server();endpoint=locator.resolve(strict=True)
        os.killpg(server.pid,signal.SIGTERM);server.wait(timeout=15)
        lines+=['[mcp_servers.codex-wake]',f'command = {json.dumps(str(prefix/"bin/codex-wake-mcp"))}',
            'args = '+json.dumps(['--wake-root',str(root/'wake'),'--lifecycle-profiles',str(profiles),
                '--app-server','unix://'+str(endpoint),'--tmux-socket',str(socket),'--tmux-session',session]),
            'startup_timeout_sec = 20','tool_timeout_sec = 20']
        (home/'config.toml').write_text('\n'.join(lines)+'\n');server=launch_server()
        if locator.resolve()!=endpoint:raise RuntimeError('owned endpoint changed')
        def request(method,params):return native_request('unix://'+str(endpoint),str(codex),method,params,10)
        subprocess.run(['tmux','-S',str(socket),'new-session','-d','-s',session,'-x','160','-y','40','sleep 700'],env=env,check=True,capture_output=True,timeout=10);created=True
        profile=dict(cwd=str(workspace),codex_home=str(home),codex_path=str(codex),app_server='unix://'+str(endpoint),tmux_socket=str(socket),tmux_session=session,timeout=10)
        write(profiles,dict(version=1,profiles={'worker':profile}))
        objective=f'Operator-approved Plan0156 disposable continuation: execute {prefix}/bin/python {helper} --continue exactly once, record actual result, then mark this goal complete. No other work, actors, resource renewal or goal budget change.'
        constants=dict(repo=str(repo),head=head,guide=str(guide),workflow=str(workflow),prefix=str(prefix),codex=str(codex),endpoint='unix://'+str(endpoint))
        helper.write_text('C='+repr(constants)+'\n'+'''import os,sys,json,pathlib,hashlib,subprocess
from codex_wake.native_protocol import native_request
cid=os.environ['CODEX_THREAD_ID']
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
if sys.argv[1:]==['--instructions']:
    for kind in ('guide','workflow'):
        print('SELECTED_INSTRUCTIONS:'+kind+':'+sha(C[kind]))
        print(pathlib.Path(C[kind]).read_text())
    raise SystemExit(0)
if sys.argv[1:]==['--continue']:
    proof=json.loads(pathlib.Path('preflight.json').read_text())
    assert proof['successor_thread_id']==cid and proof['state']=='passed'
    assert not pathlib.Path('continued.json').exists(),'continuation already executed'
    p=subprocess.run([C['prefix']+'/bin/codex-wake','--version'],capture_output=True,text=True,check=True)
    pathlib.Path('continued.json').write_text(json.dumps(dict(state='passed',thread_id=cid,checkpoint_sha256=proof['checkpoint_sha256'],version=p.stdout.strip())))
    print('CONTINUATION_CHECK:'+cid+':'+proof['checkpoint_sha256'])
    raise SystemExit(0)
source,nonce,digest=sys.argv[1:]
assert sha('checkpoint.json')==digest
body=json.loads(pathlib.Path('checkpoint.json').read_text());assert body['source_thread_id']==source
assert subprocess.check_output(['git','-C',C['repo'],'rev-parse','HEAD'],text=True).strip()==C['head']
assert not subprocess.check_output(['git','-C',C['repo'],'status','--porcelain'],text=True).strip()
checks={}
for name in ('canonical_sources','selected_skill','selected_workflow'):
    paths=([C['repo']+'/docs/dev/plans/0156-2026-10-12-agent-lifecycle-delivery.md',C['repo']+'/docs/dev/plans/0159-2026-10-12-agent-handoff.md'] if name=='canonical_sources' else [C['guide']] if name=='selected_skill' else [C['workflow']])
    checks[name]=dict(state='passed',sources=[dict(path=p,sha256=sha(p)) for p in paths])
skills=native_request(C['endpoint'],C['codex'],'skills/list',dict(cwds=[str(pathlib.Path.cwd())],forceReload=True),10)
assert any(s['path']==C['guide'] and s.get('enabled') is True for d in skills['data'] for s in d['skills'])
resource=native_request(C['endpoint'],C['codex'],'thread/mcp/tool/call',dict(threadId=cid,server='codex-wake',tool='wake_sessions_show',arguments={'selector':'thread:'+source}),20)
assert not resource.get('isError',False)
observed=json.loads(resource['content'][0]['text']);assert observed['session']['thread_id']==source and observed['complete'] is True
checks['native_resource']=dict(state='passed',tool='wake_sessions_show',source_thread_id=source,content_sha256=hashlib.sha256(json.dumps(resource,sort_keys=True).encode()).hexdigest())
version=subprocess.check_output([C['prefix']+'/bin/codex-wake','--version'],text=True).strip()
checks['installed_cli']=dict(state='passed',version=version)
ref=subprocess.check_output(['git','-C',C['repo'],'ls-remote','--exit-code','origin','refs/heads/feat/agent-lifecycle'],text=True,timeout=15).split()[0]
assert ref==C['head']
validation=[C['prefix']+'/bin/python','-m','unittest','discover','-s',C['repo']+'/tests','-p','test_agent_handoff.py','-q']
p=subprocess.run(validation,cwd=C['repo'],env=dict(os.environ,CODEX_WAKE_STABLE_TIME_CONFIG='',PYTHONWARNINGS='ignore'),capture_output=True,text=True,timeout=30)
assert p.returncode==0,p.stderr
checks['focused_validation']=dict(state='passed',command=validation,exit_code=p.returncode,result=p.stderr[-500:])
packet=('Objective: '+body['objective']+'\\nNon-goals: other actors, sends, claims, resource renewal, shared service changes.\\n'
    +'Repository: CochranResearchGroup/codex-wake at '+ref+'\\n'
    +'Canonical plan: https://github.com/CochranResearchGroup/codex-wake/blob/'+ref+'/docs/dev/plans/0159-2026-10-12-agent-handoff.md\\n'
    +'GitHub ref verified by git ls-remote. Local/native evidence is separately sourced from this executed preflight; no connector health claim.\\n'
    +'Completed fixture work: exact source checkpoint read and hash verified; installed selected instructions read, native read-only MCP resource and focused public installed validation passed.\\n'
    +'Next authorized packet: execute only the bounded continuation check named by the preserved objective after external goal activation.\\n'
    +'Remaining full Plan0156 acceptance: same-tab, rollback, final review, integration/release and clean main. Fixture success does not close the program.\\n'
    +'Validation command: '+repr(validation)+'\\n'
    +'Authority: '+body['authority']+'; original expiry and cumulative counters remain externally enforced.\\n')
pathlib.Path('successor-handoff.md').write_text(packet)
checks['selected_workflow'].update(packet='successor-handoff.md',packet_sha256=sha('successor-handoff.md'),verified_ref=ref)
pathlib.Path('preflight.json').write_text(json.dumps(dict(version=1,state='passed',source_thread_id=source,successor_thread_id=cid,checkpoint_sha256=digest,intent_fingerprint=nonce,selected_workflow='github-handoff',checks=checks)))
print('preflight:'+cid+':'+nonce+':'+digest)
''')
        (workspace/'AGENTS.md').write_text(f'For handoff preflight, first run {prefix}/bin/python {helper} --instructions with max_output_tokens=20000 and read both selected skill instructions completely. Then apply their checkpoint/live-state validation through the exact host preflight command. This private fixture has no GitHub connector; use the root-selected github-handoff workflow and canonical frozen repository evidence. Do not claim GitHub connector health. For the outgoing writer, execute only its supplied Python checkpoint script. No A2A enrollment, sends, claims or resource renewal.\n')
        script="import os,json,hashlib,pathlib\np=pathlib.Path('checkpoint.json')\np.write_text(json.dumps(dict(source_thread_id=os.environ['CODEX_THREAD_ID'],objective="+repr(objective)+",authority='operator execute Plan0156; fixed bounded disposable continuation',repo="+repr(str(repo))+",commit="+repr(head)+",next_packet='Read selected skill instructions and run host preflight before authorized bounded continuation',pending_obligations=[]),sort_keys=True)+'\\n')\nprint('checkpoint:'+os.environ['CODEX_THREAD_ID']+':'+hashlib.sha256(p.read_bytes()).hexdigest())\n"
        task='Execute only this Python script to write your own outgoing checkpoint, then report checkpoint ready. Do not change any goal.\n```python\n'+script+'```'
        spawn=['sessions','spawn','--profiles',str(profiles),'--profile','worker','--intent','source-1','--name','checkpoint-source','--task',task,'--expires-at',expiry,'--json']
        deadline=time.monotonic()+180
        while True:
            code,state=invoke(spawn);receipt['source']=state;write(root/'state.json',receipt)
            if state['state']=='completed':break
            if state['state'] in ('blocked','expired') or time.monotonic()>deadline or (state['state']=='uncertain' and not(state.get('thread_id') and state.get('submission_id'))):raise RuntimeError('source held: '+state['state'])
            time.sleep(.5)
        source=state['thread_id'];native,spent=usage(source);receipt['source_usage']=spent;write(root/'native-source.json',native)
        if spent['total_tokens']>=100000:raise RuntimeError('source exceeded fixture suballowance')
        receipt['source_goal']=request('thread/goal/set',dict(threadId=source,objective=objective,tokenBudget=250000-spent['total_tokens'],status='paused',origin='automatic'))['goal']
        policy=dict(objective=objective,approval=receipt['authority'],token_cap=250000,time_cap_seconds=int(end-started),tokens_before_source=spent['total_tokens'],seconds_before_source=0,started_at=datetime.fromtimestamp(started,UTC).isoformat(),preflight=dict(script=str(helper),sha256=hashlib.sha256(helper.read_bytes()).hexdigest(),receipt='preflight.json',workflow='github-handoff',required_checks=['canonical_sources','selected_skill','selected_workflow','native_resource','installed_cli','focused_validation'],token_allowance=150000),activation=dict(approved=True,max_poll_seconds=1,deadline_margin_seconds=45))
        write(profiles,dict(version=1,profiles={'worker':profile},continuations={source:policy},callers={source:['worker']}))
        checkpoint=workspace/'checkpoint.json';digest=hashlib.sha256(checkpoint.read_bytes()).hexdigest()
        handoff=['sessions','handoff','--profiles',str(profiles),'--profile','worker','--intent','handoff-1','--thread-id',source,'--checkpoint','checkpoint.json','--checkpoint-sha256',digest,'--expires-at',expiry,'--mode','new-tab','--json']
        deadline=time.monotonic()+240
        while True:
            code,state=invoke(handoff);receipt['handoff']=state;write(root/'state.json',receipt)
            if state['state']=='awaiting_activation':break
            if state['state'] in ('blocked','expired') or time.monotonic()>deadline or (state['state']=='uncertain' and not(state.get('successor_thread_id') and state.get('successor',{}).get('submission_id'))):raise RuntimeError('handoff held: '+state.get('reason',state['state']))
            time.sleep(.5)
        target=state['successor_thread_id'];native,spent=usage(target);receipt['preflight_usage']=spent;write(root/'native-preflight.json',native)
        instructions=[i for t in native['turns'] for i in t['items'] if i['type']=='commandExecution' and '--instructions' in i.get('command','') and i.get('exitCode')==0]
        if len(instructions)!=1 or not all('SELECTED_INSTRUCTIONS:'+k+':' in instructions[0].get('aggregatedOutput','') for k in ('guide','workflow')):raise RuntimeError('actual selected instruction read unverified')
        receipt['instruction_read_item']=instructions[0]['id']
        mcp_args=dict(profile='worker',intent='handoff-1',thread_id=source,checkpoint='checkpoint.json',checkpoint_sha256=digest,expires_at=expiry,mode='new-tab',caller_thread_id=source)
        receipt['native_handoff_mcp_prepared']=native_request('unix://'+str(endpoint),str(codex),'thread/mcp/tool/call',dict(threadId=source,server='codex-wake',tool='wake_sessions_handoff',arguments=mcp_args),70)
        monitor=subprocess.Popen([str(prefix/'bin/codex-waked'),'--wake-root',str(root/'wake'),'--no-dispatch','--interval','1'],env=env,stdout=mlog,stderr=mlog,start_new_session=True)
        deadline=time.monotonic()+min(180,max(0,end-snapshot()['utc']['upper']-50))
        while time.monotonic()<deadline and monitor.poll() is None:
            code,state=invoke(handoff);receipt['continuation']=state;write(root/'state.json',receipt)
            if (workspace/'continued.json').exists():break
            if state['state'] in ('expired','blocked'):raise RuntimeError('continuation held: '+state['reason'])
            time.sleep(1)
        if not (workspace/'continued.json').exists():raise RuntimeError('actual goal continuation command not observed')
        # Read the exact native turn; a filesystem result alone is insufficient.
        deadline=time.monotonic()+20
        while True:
            native,spent=usage(target)
            matching=[t for t in native['turns'] if any(i.get('type')=='commandExecution' and 'CONTINUATION_CHECK:'+target+':'+digest in (i.get('aggregatedOutput') or '') and i.get('exitCode')==0 for i in t['items'])]
            if len(matching)==1 and matching[0]['status']=='completed':break
            if time.monotonic()>deadline:raise RuntimeError('native continuation completion unverified')
            time.sleep(.5)
        receipt.update(state='passed_continuation_axis',successor_usage=spent,continuation_turn_id=matching[0]['id'],final_source_goal=request('thread/goal/get',dict(threadId=source))['goal'],final_successor_goal=request('thread/goal/get',dict(threadId=target))['goal'])
        receipt['native_handoff_mcp_result']=native_request('unix://'+str(endpoint),str(codex),'thread/mcp/tool/call',dict(threadId=source,server='codex-wake',tool='wake_sessions_handoff',arguments=mcp_args),70)
        write(root/'native-continuation.json',native)
    except Exception as exc:receipt.update(state='failed',error=str(exc))
    finally:
        if monitor is not None and monitor.poll() is None:
            os.killpg(monitor.pid,signal.SIGINT)
            try:monitor.wait(timeout=30)
            except subprocess.TimeoutExpired:receipt['monitor_shutdown']='timed_out'
        receipt['monitor_exit']=monitor.poll() if monitor else None
        if 'target' in locals():
            try:
                _,receipt['successor_usage']=usage(target)
                receipt['cleanup_successor_goal']=request('thread/goal/get',dict(threadId=target))['goal']
            except Exception as exc:receipt['final_readback_error']=type(exc).__name__
        if created:subprocess.run(['tmux','-S',str(socket),'kill-session','-t',session],env=env,capture_output=True,timeout=10)
        if server is not None and server.poll() is None:
            os.killpg(server.pid,signal.SIGTERM)
            try:server.wait(timeout=20)
            except subprocess.TimeoutExpired:receipt['server_shutdown']='timed_out'
        log.close();mlog.close();receipt['server_exit']=server.poll() if server else None
        matches=[];denied=[]
        for p in Path('/proc').iterdir():
            if not p.name.isdigit():continue
            try:
                if p.stat().st_uid==os.getuid() and ('CODEX_HOME='+str(home)).encode() in (p/'environ').read_bytes().split(b'\0'):matches.append(int(p.name))
            except PermissionError:denied.append(int(p.name))
            except (FileNotFoundError,ProcessLookupError):pass
        receipt['cleanup']=dict(private_readable_environment_matches=matches,denied_environment_pids=denied)
        if matches or receipt['server_exit'] is None or receipt.get('monitor_shutdown'):receipt.update(state='failed',cleanup_error='owned processes remain or shutdown unverified')
        write(root/'state.json',receipt)
    print(json.dumps({k:receipt.get(k) for k in ('state','error','root','source_usage','successor_usage','cleanup')}))
    return 0 if receipt['state']=='passed_continuation_axis' else 1


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execute',action='store_true');p.add_argument('--root',type=Path,required=True);p.add_argument('--prefix',type=Path,required=True);p.add_argument('--repo',type=Path,required=True);p.add_argument('--parent-deadline',type=float,required=True)
    args=p.parse_args()
    if not args.execute:p.error('--execute required for two owned assignments and bounded native goal effects')
    return execute(args.root.resolve(),args.prefix.resolve(),args.repo.resolve(),args.parent_deadline)
if __name__=='__main__':raise SystemExit(main())
