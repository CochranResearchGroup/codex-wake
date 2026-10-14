"""Opt-in installed source-checkpoint writer qualification; one owned assignment."""
from __future__ import annotations
import argparse
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time
import tomllib

from codex_wake.native_clock import snapshot
from codex_wake.native_protocol import native_request


def write(path,body):
    path.write_text(json.dumps(body,indent=2,sort_keys=True)+'\n');path.chmod(0o600)


def execute(root,prefix):
    root.mkdir(mode=0o700,parents=True,exist_ok=False)
    workspace=root/'workspace';workspace.mkdir()
    home=root/'codex-home';home.mkdir(mode=0o700)
    codex=Path(subprocess.check_output(['which','codex'],text=True).strip()).resolve()
    config=tomllib.loads((Path.home()/'.codex/config.toml').read_text())
    selected={k:config[k] for k in ('model','model_reasoning_effort','model_provider') if k in config}
    lines=[f'{k} = {json.dumps(v)}' for k,v in selected.items()]
    lines+=['approval_policy = "never"','sandbox_mode = "workspace-write"',
        f'[projects.{json.dumps(str(workspace))}]','trust_level = "trusted"']
    (home/'config.toml').write_text('\n'.join(lines)+'\n')
    (home/'auth.json').symlink_to(Path.home()/'.codex/auth.json')
    env=dict(os.environ,CODEX_HOME=str(home),XDG_STATE_HOME=str(root/'state'))
    for k in ('CODEX_THREAD_ID','TMUX','TMUX_PANE','CODEX_WAKE_A2A_CAPABILITY',
        'CODEX_WAKE_A2A_BUS_ROOT','CODEX_WAKE_SENDER_RECEIPT_AUTHORITY','PYTHONPATH'):env.pop(k,None)
    endpoint=root/'native.sock';socket=root/'tmux.sock';session='owned-handoff'
    profiles=root/'profiles.json';log=(root/'server.log').open('w');server=None;created=False
    receipt=dict(state='preparing',root=str(root),prefix=str(prefix),selected_model=selected,
        model_assignment_limit=1,authority='operator execute Plan0156; owned checkpoint writer probe')
    def invoke(args):
        p=subprocess.run([str(prefix/'bin/codex-wake'),'--wake-root',str(root/'wake'),*args],
            env=env,text=True,capture_output=True,timeout=30)
        if not p.stdout:raise RuntimeError('installed CLI empty response: '+p.stderr[-300:])
        return p.returncode,json.loads(p.stdout)
    try:
        clock=snapshot().get('utc')
        if not clock:raise RuntimeError('admissible UTC unavailable')
        started=clock['upper'];expiry=datetime.fromtimestamp(started+180,UTC).isoformat()
        server=subprocess.Popen([str(codex),'app-server','--listen','unix://'+str(endpoint)],
            env=env,stdout=log,stderr=log,start_new_session=True)
        deadline=time.monotonic()+15
        while not endpoint.exists() and server.poll() is None and time.monotonic()<deadline:time.sleep(.1)
        if not endpoint.exists():raise RuntimeError('owned native socket unavailable')
        endpoint=endpoint.resolve(strict=True)
        def request(method,params):return native_request('unix://'+str(endpoint),str(codex),method,params,10)
        subprocess.run(['tmux','-S',str(socket),'new-session','-d','-s',session,'-x','160','-y','40','sleep 600'],
            env=env,check=True,timeout=10,capture_output=True);created=True
        profile=dict(cwd=str(workspace),codex_home=str(home),codex_path=str(codex),
            app_server='unix://'+str(endpoint),tmux_socket=str(socket),tmux_session=session,timeout=10)
        write(profiles,dict(version=1,profiles={'worker':profile}))
        repo=Path(__file__).resolve().parents[1]
        checkpoint_contract=dict(repo=str(repo),worktree=str(workspace),
            commit=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip(),
            dirty_work='isolated writer fixture; source status must be reconciled before continuation',
            acceptance_remaining=['preflight qualification'],evidence=[str(root/'state.json')],
            pending_wakes=[],pending_messages=[],claim_holders=[],reply_route='root via '+str(root/'state.json'),
            hard_stops=['original token/time caps; no renewal'],expires_at=expiry,
            resources=dict(token_cap=150000,time_cap_seconds=180,tokens_before_source=0,
                seconds_before_source=0,started_at=datetime.fromtimestamp(started,UTC).isoformat()))
        script=f"""import os,json,hashlib,pathlib
source=os.environ['CODEX_THREAD_ID']
p=pathlib.Path('checkpoint.json')
p.write_text(json.dumps(dict(**{checkpoint_contract!r},source_thread_id=source,objective='Qualify owned handoff preflight',authority='operator execute Plan0156; disposable fixture',next_packet='Read canonical sources and execute selected preflight; no active goal yet',pending_obligations=[]),sort_keys=True)+'\\n')
print('checkpoint:'+source+':'+hashlib.sha256(p.read_bytes()).hexdigest())
"""
        task=('Operator-approved Plan0156 disposable fixture. Execute only the following Python script '
            'in this current workspace to write your outgoing checkpoint. Do not create or change any '
            'goal, contact any other actor or enroll in A2A. After success reply checkpoint ready.\n'
            '```python\n'+script+'```')
        argv=['sessions','spawn','--profiles',str(profiles),'--profile','worker','--intent','writer-1',
            '--name','checkpoint-writer','--task',task,'--expires-at',expiry,'--json']
        deadline=time.monotonic()+150
        while True:
            code,state=invoke(argv);receipt['spawn']=state;write(root/'state.json',receipt)
            if state['state']=='completed':break
            if (state['state'] in ('blocked','expired') or time.monotonic()>=deadline
                    or (state['state']=='uncertain' and
                        not (state.get('thread_id') and state.get('submission_id')))):
                raise RuntimeError('outgoing writer did not complete: '+state['state'])
            time.sleep(.5)
        thread=state['thread_id'];native=request('thread/read',{'threadId':thread,'includeTurns':True})['thread']
        write(root/'native-writer.json',native)
        if len(native['turns'])!=1:raise RuntimeError('unexpected model assignment count')
        checkpoint=workspace/'checkpoint.json';body=json.loads(checkpoint.read_text())
        if body['source_thread_id']!=thread:raise RuntimeError('outgoing checkpoint identity mismatch')
        marker='checkpoint:'+thread+':'+hashlib.sha256(checkpoint.read_bytes()).hexdigest()
        receipt['writer_items']=[dict(type=i['type'],id=i['id'],status=i.get('status'),cwd=i.get('cwd'),
            exitCode=i.get('exitCode'),marker_observed=marker in (i.get('aggregatedOutput') or ''))
            for turn in native['turns'] for i in turn['items'] if i['type']=='commandExecution']
        rollout=Path(native['path'])
        usages=[json.loads(line)['payload']['info']['total_token_usage'] for line in rollout.read_text().splitlines()
            if (lambda e:e.get('type')=='event_msg' and e.get('payload',{}).get('type')=='token_count'
                and (e['payload'].get('info') or {}).get('total_token_usage'))(json.loads(line))]
        if not usages:raise RuntimeError('actual source model usage unavailable')
        used=usages[-1]['total_tokens'];receipt['native_token_usage']=usages[-1]
        if used>=150000:raise RuntimeError('owned fixture allowance exhausted')
        receipt['goal_creation']=request('thread/goal/set',dict(threadId=thread,
            objective=body['objective'],tokenBudget=150000-used,status='paused',origin='automatic'))
        policy=dict(objective=body['objective'],approval='operator execute Plan0156; owned fixture only',
            token_cap=150000,time_cap_seconds=180,tokens_before_source=used,seconds_before_source=0,
            started_at=datetime.fromtimestamp(started,UTC).isoformat())
        write(profiles,dict(version=1,profiles={'worker':profile},continuations={thread:policy}))
        code,handoff=invoke(['sessions','handoff','--profiles',str(profiles),'--profile','worker',
            '--intent','handoff-1','--thread-id',thread,'--checkpoint','checkpoint.json',
            '--checkpoint-sha256',hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
            '--expires-at',expiry,'--mode','new-tab','--json'])
        receipt['handoff']=handoff
        if code!=5 or handoff.get('reason')!='successor_preflight_not_verified' or not handoff.get('checkpoint_writer'):
            raise RuntimeError('actual outgoing checkpoint writer did not qualify')
        receipt.update(state='passed',model_assignments=1)
    except Exception as exc:receipt.update(state='failed',error=str(exc))
    finally:
        if created:subprocess.run(['tmux','-S',str(socket),'kill-session','-t',session],env=env,capture_output=True,timeout=10)
        if server is not None and server.poll() is None:
            os.killpg(server.pid,signal.SIGTERM)
            try:server.wait(timeout=20)
            except subprocess.TimeoutExpired:receipt['shutdown']='timed_out'
        log.close();receipt['server_exit']=server.poll() if server else None
        matches=[];denied=[]
        for p in Path('/proc').iterdir():
            if not p.name.isdigit():continue
            try:
                if p.stat().st_uid==os.getuid() and ('CODEX_HOME='+str(home)).encode() in (p/'environ').read_bytes().split(b'\0'):matches.append(int(p.name))
            except PermissionError:denied.append(int(p.name))
            except (FileNotFoundError,ProcessLookupError):pass
        receipt['cleanup']=dict(private_readable_environment_matches=matches,denied_environment_pids=denied)
        if matches or receipt['server_exit'] is None:receipt.update(state='failed',cleanup_error='owned processes remain')
        write(root/'state.json',receipt)
    print(json.dumps({k:receipt.get(k) for k in ('state','error','root','native_token_usage','cleanup')}))
    return 0 if receipt['state']=='passed' else 1


def reconcile(root,prefix):
    """Read/reconcile the one saved assignment; never create or replay a task."""
    original=json.loads((root/'state.json').read_text());saved=original['spawn']
    if not saved.get('thread_id') or not saved.get('submission_id'):
        raise RuntimeError('known source/submission required; unknown creation cannot be replayed')
    profile=saved['intent']['launch'];home=Path(profile['codex_home']);codex=profile['codex_path']
    locator=root/'native.sock';env=dict(os.environ,CODEX_HOME=str(home),XDG_STATE_HOME=str(root/'state'))
    for k in ('CODEX_THREAD_ID','TMUX','TMUX_PANE','PYTHONPATH'):env.pop(k,None)
    log=(root/'reconcile.log').open('w');server=subprocess.Popen(
        [codex,'app-server','--listen','unix://'+str(locator)],env=env,stdout=log,stderr=log,start_new_session=True)
    result=dict(state='failed',scope='existing checkpoint writer axis only; no goal mutation/task replay')
    try:
        deadline=time.monotonic()+15
        while not locator.exists() and server.poll() is None and time.monotonic()<deadline:time.sleep(.1)
        if 'unix://'+str(locator.resolve(strict=True))!=profile['app_server']:
            raise RuntimeError('original approved endpoint changed; hold original intent')
        intent=saved['intent']
        args=[str(prefix/'bin/codex-wake'),'--wake-root',str(root/'wake'),'sessions','spawn',
            '--profiles',str(root/'profiles.json'),'--profile',intent['profile'],'--intent',saved['intent_key'],
            '--name',intent['name'],'--task',intent['task'],'--expires-at',intent['expires_at'],'--json']
        proc=subprocess.run(args,env=env,capture_output=True,text=True,timeout=30)
        observed=json.loads(proc.stdout);result['spawn']=observed
        if proc.returncode or observed.get('execution',{}).get('execution')!='turn_completed':
            raise RuntimeError('original exact native assignment not completed')
        thread=native_request(profile['app_server'],codex,'thread/read',
            {'threadId':saved['thread_id'],'includeTurns':True},10)['thread']
        checkpoint=Path(profile['cwd'])/'checkpoint.json';body=json.loads(checkpoint.read_text())
        digest=hashlib.sha256(checkpoint.read_bytes()).hexdigest()
        if body['source_thread_id']!=saved['thread_id']:raise RuntimeError('checkpoint source changed')
        marker='checkpoint:'+saved['thread_id']+':'+digest
        writers=[dict(turn_id=t['id'],item_id=i['id'],cwd=i.get('cwd'),exit_code=i.get('exitCode'))
            for t in thread['turns'] for i in t['items'] if t['status']=='completed'
            and i['type']=='commandExecution' and i.get('status')=='completed'
            and i.get('exitCode')==0 and i.get('cwd')==profile['cwd']
            and marker in (i.get('aggregatedOutput') or '')]
        if len(writers)!=1 or len(thread['turns'])!=1:raise RuntimeError('writer/assignment not uniquely observed')
        usages=[]
        for line in Path(thread['path']).read_text().splitlines():
            event=json.loads(line);payload=event.get('payload',{});info=payload.get('info') or {}
            if event.get('type')=='event_msg' and payload.get('type')=='token_count' and info.get('total_token_usage'):
                usages.append(info['total_token_usage'])
        if not usages:raise RuntimeError('source token usage unavailable')
        result.update(state='passed_checkpoint_axis',checkpoint_sha256=digest,writer=writers[0],
            native_token_usage=usages[-1],model_assignments=1,additional_model_assignments=0)
    except Exception as exc:result['error']=str(exc)
    finally:
        if server.poll() is None:os.killpg(server.pid,signal.SIGTERM)
        server.wait(timeout=20);log.close();result['server_exit']=server.returncode
        matches=[];denied=[]
        for p in Path('/proc').iterdir():
            if not p.name.isdigit():continue
            try:
                if p.stat().st_uid==os.getuid() and ('CODEX_HOME='+str(home)).encode() in (p/'environ').read_bytes().split(b'\0'):matches.append(int(p.name))
            except PermissionError:denied.append(int(p.name))
            except (FileNotFoundError,ProcessLookupError):pass
        result['cleanup']=dict(private_readable_environment_matches=matches,denied_environment_pids=denied)
        if matches:result.update(state='failed',error='owned processes remain')
        write(root/'writer-reconciliation.json',result)
    print(json.dumps({k:result.get(k) for k in ('state','error','native_token_usage','additional_model_assignments','cleanup')}))
    return 0 if result['state']=='passed_checkpoint_axis' else 1


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--execute',action='store_true',required=True)
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--prefix',type=Path,required=True)
    p.add_argument('--reconcile-existing',action='store_true')
    a=p.parse_args();operation=reconcile if a.reconcile_existing else execute
    raise SystemExit(operation(a.root.resolve(),a.prefix.resolve()))
