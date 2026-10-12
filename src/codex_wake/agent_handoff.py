"""Checkpoint-bound fresh-context continuation; unknown allowance holds effects."""
from __future__ import annotations

import fcntl
import hashlib
import json
from pathlib import Path
from contextlib import redirect_stdout
from datetime import UTC,datetime
from io import StringIO
import sys
from types import SimpleNamespace

from .agent_lifecycle import save
from .app_server import resolve_codex_cmd
from .native_protocol import native_request
from .records import WakeError, parse_timestamp


def handoff_command(args, root):
    try:
        config=json.loads(Path(args.profiles).read_text())
        profile=config['profiles'][args.profile]
        policy=config['continuations'][args.thread_id]
        workspace=Path(profile['cwd']).resolve(strict=True)
        checkpoint=(workspace/args.checkpoint).resolve(strict=True)
        checkpoint.relative_to(workspace)
        content=checkpoint.read_bytes()
        body=json.loads(content)
        if (config['version']!=1 or body['source_thread_id']!=args.thread_id
                or body['objective']!=policy['objective']
                or not policy['approval'] or not body['authority'] or not body['next_packet']
                or body.get('pending_obligations')!=[]):raise ValueError
    except (OSError,ValueError,KeyError,TypeError):
        raise WakeError('handoff requires an approved continuation and source checkpoint') from None
    if hashlib.sha256(content).hexdigest()!=args.checkpoint_sha256:
        raise WakeError('checkpoint hash changed; original checkpoint must be preserved')
    fields=('token_cap','time_cap_seconds','tokens_before_source','seconds_before_source')
    if (any(not isinstance(policy.get(k),int) or isinstance(policy[k],bool)
            or policy[k]<0 for k in fields)
            or policy['token_cap']==0 or policy['time_cap_seconds']==0):
        raise WakeError('host continuation allowance must contain explicit bounded counters')
    parse_timestamp(policy.get('started_at',''))
    if args.caller_thread_id and (args.caller_thread_id!=args.thread_id or args.profile not in
            config.get('callers',{}).get(args.caller_thread_id,[])):
        raise WakeError('handoff requires the host-granted source caller')
    parse_timestamp(args.expires_at)
    intent=dict(operation='handoff',source_thread_id=args.thread_id,launch=profile,
        continuation=policy,checkpoint=str(checkpoint),checkpoint_sha256=args.checkpoint_sha256,
        mode=args.mode,expires_at=args.expires_at)
    fingerprint=hashlib.sha256(json.dumps(intent,sort_keys=True).encode()).hexdigest()
    journal=Path(root)/'lifecycle';journal.mkdir(mode=0o700,parents=True,exist_ok=True)
    key=hashlib.sha256(args.intent.encode()).hexdigest();path=journal/(key+'.json')
    with (journal/(key+'.lock')).open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        if path.exists():
            receipt=json.loads(path.read_text())
            if receipt['fingerprint']!=fingerprint:
                raise WakeError('intent key already binds a different lifecycle assignment')
        else:
            receipt=dict(version=1,intent_key=args.intent,fingerprint=fingerprint,
                intent=intent,thread_id=args.thread_id,state='prepared')
        goal=native_request(profile['app_server'],resolve_codex_cmd(profile['codex_path'],required=True),
            'thread/goal/get',{'threadId':args.thread_id},profile['timeout'])['goal']
        previous=receipt.get('source_goal')
        receipt['observed_source_goal']=goal
        known=bool(goal) and all(isinstance(goal.get(k),int) and not isinstance(goal[k],bool)
            and goal[k]>=0 for k in ('tokensUsed','timeUsedSeconds'))
        receipt.update(state='blocked',reason=('successor_preflight_not_verified' if known
                                              else 'source_usage_unknown'))
        if known and (goal.get('threadId')!=args.thread_id or goal.get('objective')!=policy['objective']
                or goal.get('status') not in ('active','paused')
                or type(goal.get('tokenBudget')) is not int or not 0<goal['tokenBudget']<=policy['token_cap']):
            receipt['reason']='source_goal_authority_changed'
        if known and previous:
            if any(goal.get(k)!=previous.get(k) for k in ('threadId','objective','tokenBudget','createdAt')):
                receipt['reason']='source_goal_authority_changed'
            elif any(type(previous.get(k)) is int and goal[k]<previous[k] for k in ('tokensUsed','timeUsedSeconds')):
                receipt['reason']='source_goal_accounting_changed'
        if not previous or receipt['reason']=='successor_preflight_not_verified':receipt['source_goal']=goal
        if known and receipt['reason']=='successor_preflight_not_verified':
            used=policy['tokens_before_source']+goal['tokensUsed']
            receipt['cumulative_tokens_used']=used
            receipt['remaining_tokens']=max(0,min(policy['token_cap']-used,goal['tokenBudget']-goal['tokensUsed']))
            receipt['source_remaining_tokens']=receipt['remaining_tokens']
            if receipt['remaining_tokens']==0:
                receipt['reason']='cumulative_token_budget_exhausted'
            else:
                from .native_clock import snapshot
                bounds=snapshot().get('utc')
                if not bounds:
                    receipt['reason']='admissible_time_unavailable'
                else:
                    deadline=min(parse_timestamp(args.expires_at).timestamp(),
                        parse_timestamp(policy['started_at']).timestamp()+policy['time_cap_seconds'])
                    receipt['continuation_deadline']=deadline
                    receipt['remaining_seconds']=max(0,deadline-bounds['upper'])
                    if bounds['upper']>=deadline:
                        receipt['reason']='continuation_time_exhausted'
        if receipt['reason']=='successor_preflight_not_verified':
            thread=native_request(profile['app_server'],resolve_codex_cmd(profile['codex_path'],required=True),
                'thread/read',{'threadId':args.thread_id,'includeTurns':True},profile['timeout'])['thread']
            marker='checkpoint:'+args.thread_id+':'+args.checkpoint_sha256
            writers=[{'turn_id':turn['id'],'item_id':item['id']}
                for turn in thread.get('turns',[]) for item in turn.get('items',[])
                if turn.get('status')=='completed' and item.get('type')=='commandExecution'
                and item.get('status')=='completed' and item.get('exitCode')==0
                and item.get('cwd')==str(workspace) and marker in (item.get('aggregatedOutput') or '')]
            if thread.get('id')!=args.thread_id or len(writers)!=1:
                receipt['reason']='checkpoint_writer_unverified'
            else:
                receipt['checkpoint_writer']=writers[0]
                source_guard(receipt,profile,root)
        if receipt['reason']=='successor_preflight_not_verified' and receipt.get('source_attachment'):
            advance_handoff(path,receipt,profile,policy,args,root)
        save(path,receipt)
        from .sessions_cli import emit
        emit(receipt,args.as_json)
        return 5


def source_guard(receipt,profile,root):
    from .sessions import observe,revalidate_attachment
    from .session_lifecycle import pending_thread_work,tmux_command
    from types import SimpleNamespace
    snapshot=observe(endpoint=profile['app_server'],socket_path=profile.get('tmux_socket'),
        timeout=profile['timeout'])
    rows=[r for r in snapshot['sessions'] if r['thread_id']==receipt['thread_id']]
    if (not snapshot['complete'] or len(rows)!=1 or rows[0]['runtime_state']!='idle'
            or rows[0]['cwd']!=str(Path(profile['cwd']).resolve()) or rows[0]['active_flags']
            or rows[0]['can_accept_direct_input'] is not True or len(rows[0]['attachments'])!=1):
        receipt['reason']='source_client_not_uniquely_ready'
        return
    attachment=rows[0]['attachments'][0]
    if attachment['session_name']!=profile['tmux_session'] or not revalidate_attachment(attachment):
        receipt['reason']='source_client_not_uniquely_ready'
        return
    work=pending_thread_work(rows[0],root)
    receipt['pending_work']=work
    if work['pending'] or work['messages']:
        receipt['reason']='pending_thread_work'
        return
    runtime=SimpleNamespace(tmux_socket=profile.get('tmux_socket'),timeout=profile['timeout'])
    panes=tmux_command(runtime,'list-panes','-t',attachment['window_id'],'-F','#{pane_id}')
    if panes.splitlines()!=[attachment['pane_id']]:
        receipt['reason']='split_or_changed_source_tab'
        return
    frame=tmux_command(runtime,'capture-pane','-e','-p','-t',attachment['pane_id'],preserve_output=True)
    cursor=tmux_command(runtime,'display-message','-p','-t',attachment['pane_id'],'#{cursor_x},#{cursor_y}')
    lines=frame.splitlines()
    try:
        x,y=map(int,cursor.strip().split(','))
        empty=x==2 and 0<=y<len(lines) and lines[y]=='\x1b[1m›\x1b[0m \x1b[2mAsk Codex to do anything\x1b[0m'
    except ValueError:empty=False
    if not empty:
        receipt['reason']='local_composer_not_proven_empty'
        return
    receipt['source_attachment']=attachment


def advance_handoff(path,receipt,profile,policy,args,root):
    """One fenced successor assignment; activation stays independently held."""
    from .agent_lifecycle import spawn_command
    preflight=policy.get('preflight',{})
    try:
        script=Path(preflight['script'])
        output=(Path(profile['cwd'])/preflight['receipt']).resolve()
        output.relative_to(Path(profile['cwd']).resolve())
        if (not script.is_absolute() or hashlib.sha256(script.read_bytes()).hexdigest()!=preflight['sha256']
                or preflight['workflow']!='github-handoff' or not preflight['required_checks']):raise ValueError
    except (OSError,ValueError,KeyError,TypeError):
        receipt.update(state='blocked',reason='preflight_policy_unavailable')
        return
    if (type(preflight.get('token_allowance')) is not int or preflight['token_allowance']<=0
            or preflight['token_allowance']>receipt['source_remaining_tokens']):
        receipt.update(state='blocked',reason='preflight_allowance_insufficient')
        return
    if args.mode!='new-tab':
        receipt.update(state='blocked',reason='same_tab_transition_not_implemented')
        return
    key=hashlib.sha256(receipt['thread_id'].encode()).hexdigest()
    owner_path=path.parent/('owner-'+key+'.json')
    with (path.parent/('owner-'+key+'.lock')).open('a') as owner_lock:
        fcntl.flock(owner_lock,fcntl.LOCK_EX)
        if owner_path.exists():
            owner=json.loads(owner_path.read_text())
            if owner['intent_fingerprint']!=receipt['fingerprint']:
                receipt.update(state='blocked',reason='source_owned_by_another_transition')
                return
        else:
            owner=dict(version=1,state='prepared',intent_fingerprint=receipt['fingerprint'],
                source_thread_id=receipt['thread_id'],state_history=['prepared'])
            save(owner_path,owner)
        def request(method,params):
            return native_request(profile['app_server'],resolve_codex_cmd(profile['codex_path'],required=True),
                method,params,profile['timeout'])
        try:
            source_goal=receipt['source_goal']
            if receipt.get('successor_thread_id') and source_goal['status']!='paused':
                receipt.update(state='blocked',reason='source_resumed_after_transfer')
                return
            if source_goal['status']!='paused':
                if receipt.get('uncertain_effect')=='thread/goal/pause':
                    receipt.update(state='uncertain',reason='source_pause_unobserved')
                    return
                if not before_handoff_effect(path,receipt):return
                receipt.update(state='pausing_source',uncertain_effect='thread/goal/pause');save(path,receipt)
                request('thread/goal/set',dict(threadId=receipt['thread_id'],status='paused',origin='automatic'))
                paused=request('thread/goal/get',{'threadId':receipt['thread_id']})['goal']
                if (paused is None or paused['status']!='paused' or paused['objective']!=source_goal['objective']
                        or paused['tokenBudget']!=source_goal['tokenBudget']):
                    receipt.update(state='blocked',reason='source_pause_unverified');return
                receipt['source_goal']=paused
            if receipt.get('uncertain_effect')=='thread/goal/pause':receipt.pop('uncertain_effect',None)
            receipt.update(state='starting_successor');save(path,receipt)
            contract=dict(source_thread_id=receipt['thread_id'],checkpoint=str(Path(profile['cwd'])/args.checkpoint),
                checkpoint_sha256=args.checkpoint_sha256,intent_fingerprint=receipt['fingerprint'],
                selected_workflow=preflight['workflow'],script=str(script),receipt=str(output),
                token_allowance=preflight['token_allowance'])
            receipt.setdefault('preflight_task',
                'Preflight only. Apply the selected github-handoff workflow and read the exact source checkpoint. '
                'Run the host-approved Python preflight script with source_thread_id, intent_fingerprint and '
                'checkpoint_sha256 as its three arguments. Read its actual checks; do not fabricate results. '
                'Do not create/activate a goal, enroll in A2A, copy claims or send to another actor. '
                'Continuation requires a separate verified deadline fence.\nPREFLIGHT_CONTRACT='+
                json.dumps(contract,sort_keys=True)+'\nPython executable: '+sys.executable)
            save(path,receipt)
            if not before_handoff_effect(path,receipt):return
            child=SimpleNamespace(profiles=args.profiles,profile=args.profile,
                intent='handoff-preflight:'+receipt['fingerprint'],name='handoff-'+receipt['fingerprint'][:12],
                task=receipt['preflight_task'],expires_at=datetime.fromtimestamp(receipt['continuation_deadline'],UTC).isoformat(),
                caller_thread_id=args.caller_thread_id,as_json=True)
            emitted=StringIO()
            with redirect_stdout(emitted):spawn_command(child,root)
            worker=json.loads(emitted.getvalue());receipt['successor']=worker
            receipt['successor_thread_id']=worker.get('thread_id')
            if worker['state']!='completed':
                receipt.update(state=worker['state'],reason='successor_assignment_'+worker['state']);return
            target=worker['thread_id']
            native=request('thread/read',{'threadId':target,'includeTurns':True})['thread']
            proof=json.loads(output.read_text())
            required=dict(source_thread_id=receipt['thread_id'],successor_thread_id=target,
                checkpoint_sha256=args.checkpoint_sha256,intent_fingerprint=receipt['fingerprint'],
                selected_workflow=preflight['workflow'],state='passed')
            marker='preflight:'+target+':'+receipt['fingerprint']+':'+args.checkpoint_sha256
            executions=[i for turn in native['turns'] for i in turn['items']
                if turn['status']=='completed' and i.get('type')=='commandExecution' and i.get('status')=='completed'
                and i.get('exitCode')==0 and i.get('cwd')==str(Path(profile['cwd']).resolve())
                and str(script) in i.get('command','') and marker in (i.get('aggregatedOutput') or '')]
            if (any(proof.get(k)!=v for k,v in required.items()) or len(executions)!=1
                    or any(proof.get('checks',{}).get(k,{}).get('state')!='passed' for k in preflight['required_checks'])):
                receipt.update(state='blocked',reason='successor_preflight_unverified');return
            rollout=Path(native['path']).resolve(strict=True)
            rollout.relative_to(Path(profile.get('codex_home',Path.home()/'.codex'))/'sessions')
            usage=None
            for line in rollout.read_text().splitlines():
                event=json.loads(line);payload=event.get('payload',{});info=payload.get('info') or {}
                if event.get('type')=='event_msg' and payload.get('type')=='token_count' and info.get('total_token_usage'):
                    usage=info['total_token_usage'].get('total_tokens')
            if type(usage) is not int or usage<0:
                receipt.update(state='blocked',reason='successor_usage_unknown');return
            if usage>preflight['token_allowance']:
                receipt.update(state='blocked',reason='preflight_allowance_exhausted',preflight_tokens_used=usage);return
            receipt.update(preflight=proof,preflight_tokens_used=usage,
                remaining_tokens=max(0,receipt['source_remaining_tokens']-usage))
            if receipt['remaining_tokens']==0:
                receipt.update(state='blocked',reason='cumulative_token_budget_exhausted');return
            goal=request('thread/goal/get',{'threadId':target})['goal']
            if goal is None:
                if receipt.get('uncertain_effect')=='thread/goal/prepare_successor':
                    receipt.update(state='uncertain',reason='successor_goal_creation_unobserved');return
                if not before_handoff_effect(path,receipt):return
                receipt['uncertain_effect']='thread/goal/prepare_successor';save(path,receipt)
                goal=request('thread/goal/set',dict(threadId=target,objective=policy['objective'],
                    status='paused',tokenBudget=receipt['remaining_tokens'],origin='automatic'))['goal']
            if (goal['objective']!=policy['objective'] or goal['status']!='paused'
                    or goal['tokenBudget']!=receipt['remaining_tokens']):
                receipt.update(state='blocked',reason='successor_goal_authority_changed');return
            receipt.pop('uncertain_effect',None);receipt['successor_goal']=goal
            receipt.update(state='awaiting_activation',reason='deadline_fence_unverified')
            owner.update(state='successor_prepared',successor_thread_id=target);save(owner_path,owner)
        except Exception as exc:
            receipt.update(state='uncertain' if receipt.get('uncertain_effect') else 'blocked',reason=type(exc).__name__)


def before_handoff_effect(path,receipt):
    from .native_clock import snapshot
    bounds=snapshot().get('utc')
    if not bounds or bounds['upper']>=receipt['continuation_deadline']:
        receipt.update(state='expired' if bounds else 'blocked',reason=(
            'continuation_time_exhausted' if bounds else 'admissible_time_unavailable'))
        save(path,receipt)
        return False
    return True
