"""Checkpoint-bound fresh-context continuation; unknown allowance holds effects."""
from __future__ import annotations

import fcntl
import hashlib
import json
from pathlib import Path

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
        receipt['source_goal']=goal
        known=bool(goal) and all(isinstance(goal.get(k),int) and not isinstance(goal[k],bool)
            and goal[k]>=0 for k in ('tokensUsed','timeUsedSeconds'))
        receipt.update(state='blocked',reason=('successor_preflight_not_verified' if known
                                              else 'source_usage_unknown'))
        if known:
            used=policy['tokens_before_source']+goal['tokensUsed']
            receipt['cumulative_tokens_used']=used
            receipt['remaining_tokens']=max(0,policy['token_cap']-used)
            if used>=policy['token_cap']:
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
            else:receipt['checkpoint_writer']=writers[0]
        save(path,receipt)
        from .sessions_cli import emit
        emit(receipt,args.as_json)
        return 5
