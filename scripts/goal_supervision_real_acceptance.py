"""Opt-in single real-agent acceptance on an existing native gateway.

No daemon startup, policy writes, identity retries, allocation resets or budget
increases. This dispatches real provider work only with --approve-real-agent.

Example (all paths are operator-approved existing installation/authority):
  <installed-python> scripts/goal_supervision_real_acceptance.py \
    --approve-real-agent --output /tmp/new-private-acceptance \
    --token-limit 100000 --seconds 180 --sandbox danger-full-access \
    --approval-policy never --codex /absolute/codex --wake-python /installed/python \
    --app-server unix:///existing/physical.sock --policy /private/goal-limits.json \
    --wake-root /private/wake-root --expected-version 0.18.6 --model <approved-model>

The new conversation is retained for its controller/accounting history. Cleanup
pauses only its goal, interrupts only its turns and terminates only its native
background-terminal handles; it never archives a live accounting source.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import socket
import stat
import struct
import subprocess
import time


class AcceptanceFailure(ValueError):
    pass


def _require(condition, reason):
    if not condition:
        raise AcceptanceFailure(reason)


def _save(output, name, value):
    path=output/name
    path.write_text(json.dumps(value,indent=2)+'\n');path.chmod(0o600)


def _turns(request, thread):
    rows=[];cursor=None;seen=set()
    for _ in range(32):
        params=dict(threadId=thread,limit=128,itemsView='notLoaded')
        if cursor is not None:params['cursor']=cursor
        page=request('thread/turns/list',params)
        rows.extend(page['data']);cursor=page.get('nextCursor')
        if cursor is None:return rows
        _require(isinstance(cursor,str) and cursor and cursor not in seen,'cleanup_cursor_ambiguous')
        seen.add(cursor)
    raise AcceptanceFailure('cleanup_page_bound')


def _cleanup(request, thread):
    proof=dict(thread_id=thread,verified=False,interrupted_turns=[],terminated_processes=[])
    try:
        goal=request('thread/goal/get',dict(threadId=thread))['goal']
        if goal and goal['status']=='active':
            request('thread/goal/set',dict(threadId=thread,status='paused',origin='user'))
        for turn in _turns(request,thread):
            if turn['status']=='inProgress':
                request('turn/interrupt',dict(threadId=thread,turnId=turn['id']))
                proof['interrupted_turns'].append(turn['id'])
        terminals=request('thread/backgroundTerminals/list',dict(threadId=thread))
        _require(terminals.get('nextCursor') is None,'cleanup_terminals_incomplete')
        for terminal in terminals['data']:
            identity=terminal.get('processId')
            _require(isinstance(identity,str) and identity,'cleanup_process_identity_unknown')
            request('thread/backgroundTerminals/terminate',dict(threadId=thread,processId=identity))
            proof['terminated_processes'].append(identity)
        _require(not any(t['status']=='inProgress' for t in _turns(request,thread)),'cleanup_turn_still_active')
        remaining=request('thread/backgroundTerminals/list',dict(threadId=thread))
        _require(not remaining['data'] and remaining.get('nextCursor') is None,'cleanup_process_still_active')
        after=request('thread/goal/get',dict(threadId=thread))['goal']
        _require(not after or after['status']!='active','cleanup_goal_still_active')
        proof.update(verified=True,goal=after)
    except Exception as exc:proof['error']=str(exc)
    return proof


def _qualified_receipt(proof, options, first=None):
    exhausted=(proof.get('state')=='stopped' and proof.get('reason')=='allocation_exhausted'
        and proof.get('stop_proof') is True)
    normal=(proof.get('state') in ('armed','checkpoint_requested')
        and not proof.get('stop_latched') and proof.get('reason') in (None,'checkpoint_reserve'))
    _require((normal or exhausted) and proof.get('controller',{}).get('fresh') is True
        and proof.get('accounting',{}).get('state')=='qualified','resource_receipt_unqualified')
    _require(proof.get('token_accounting')=='fresh' and proof.get('token_limit')==options.token_limit
        and proof.get('time_limit_seconds')==options.seconds,'enrollment_caps_or_basis_changed')
    if first is not None:
        _require(all(proof.get(k)==first[k] for k in ('allocation_id','generation','deadline')),
            'allowance_identity_or_deadline_changed')


def run(options, request, read_status=None, *, sleep=time.sleep, observe_raw=None):
    """Public orchestration seam; native RPC and public status are I/O boundaries."""
    output=options.output.absolute();output.mkdir(mode=0o700,parents=True,exist_ok=False)
    result=dict(verdict='FAIL',failure_stage='setup',model_dispatch_attempted=False,
        workspace=str(output),permissions=dict(sandbox=options.sandbox,approval_policy=options.approval_policy),
        token_limit=options.token_limit,time_limit_seconds=options.seconds,
        shared_daemon_modified=False,host_policy_modified=False,identity_retries=0)
    thread=None;end=time.monotonic()+max(1,options.seconds)
    try:
        _require(options.approved,'explicit_real_agent_approval_required')
        _require(type(options.token_limit) is int and options.token_limit>0 and
                 type(options.seconds) is int and options.seconds>0,'positive_explicit_caps_required')
        _require(options.sandbox=='danger-full-access' and options.approval_policy=='never',
                 'unattended_mcp_permissions_unqualified')
        prompt=('Owned Wake acceptance. Use only the wake_acceptance MCP server. First enroll this actual native caller using wake_goal_limits_set, '
            f'token_limit={options.token_limit},time_limit_seconds={options.seconds}, fresh accounting, no allocation_id. '
            'Do no product work before armed/qualified/fresh controller proof. Never retry enrollment under another '
            'identity, enlarge/reset allowance, edit host policy, or start background work. After armed enrollment, '
            'perform useful prime-algorithm checks with local Python until Wake requests a checkpoint. Then write '
            'checkpoint.md in this workspace with enrollment identity, deadline, evidence and restart instructions, '
            'pause the goal using update_goal(status="paused"), and finish. Keep operator replies available. '
            'Do not mark the goal complete or resume automatically. No messages or external effects beyond this test.')
        (output/'acceptance.txt').write_text(prompt+'\n')
        started=request('thread/start',dict(cwd=str(output),model=options.model,
            approvalPolicy=options.approval_policy,sandbox=options.sandbox,developerInstructions=prompt,
            config={'mcp_servers':{'wake_acceptance':{'command':str(options.wake_python),
                'args':['-m','codex_wake.mcp_server','--goal-limits-policy',str(options.policy),
                        '--goal-limits-root',str(options.wake_root)]}}}))
        thread=started['thread']['id'];result['thread_id']=thread
        _save(output,'native-start.json',started)
        _require(started.get('approvalPolicy')=='never' and started.get('sandbox',{}).get('type')=='dangerFullAccess',
                 'native_permissions_do_not_match_approval')
        catalog=request('mcpServerStatus/list',dict(threadId=thread,serverName='wake_acceptance',detail='toolsAndAuthOnly'))
        _save(output,'native-mcp-readback.json',catalog)
        rows=[r for r in catalog['data'] if r['name']=='wake_acceptance']
        _require(len(rows)==1 and rows[0]['serverInfo']['version']==options.expected_version,'installed_mcp_version_unqualified')
        tools=rows[0]['tools']
        _require(all(name in tools for name in ('wake_goal_limits_set','wake_goal_limits_show')),'installed_mcp_tools_unqualified')
        _require({'caller_thread_id','token_limit','time_limit_seconds'}<=set(tools['wake_goal_limits_set']['inputSchema']['properties']),
                 'installed_mcp_schema_unqualified')
        _require(Path(started['thread'].get('path','')).is_absolute() and
            Path(started['thread']['path']).resolve().is_relative_to(options.codex_home.resolve()),
            'native_history_home_unqualified')
        before_status=read_status(thread)
        _save(output,'status-before-dispatch.json',before_status)
        _require(before_status.get('controller',{}).get('fresh') is True,'independent_controller_not_fresh')
        goal=request('thread/goal/set',dict(threadId=thread,objective=prompt,status='blocked',origin='user',tokenBudget=options.token_limit))['goal']
        actual=request('thread/goal/get',dict(threadId=thread))['goal']
        _require(actual==goal and actual['threadId']==thread and actual['status']=='blocked','native_goal_setup_unqualified')
        _save(output,'goal-before-dispatch.json',actual)
        result['failure_stage']='enrollment';result['model_dispatch_attempted']=True
        request('thread/goal/set',dict(threadId=thread,status='active',origin='user'))
        first=None;last_used=0;checkpoint=False
        while time.monotonic()<end:
            proof=read_status(thread)
            _save(output,'latest-status.json',proof)
            if first is None:
                if proof.get('state')=='held' and proof.get('reason')=='not_enrolled':sleep(.2);continue
                _require(proof.get('state') in ('armed','checkpoint_requested') and
                    proof.get('accounting',{}).get('state')=='qualified' and proof.get('controller',{}).get('fresh') is True,
                    'enrollment_not_armed')
                _require(proof.get('token_accounting')=='fresh' and proof.get('token_limit')==options.token_limit
                    and proof.get('time_limit_seconds')==options.seconds,'enrollment_caps_or_basis_changed')
                first=proof;result.update(allocation_id=proof['allocation_id'],generation=proof['generation'],deadline=proof['deadline'])
                _save(output,'enrollment.json',proof);result['failure_stage']='enforcement'
            _qualified_receipt(proof,options,first)
            _require(type(proof.get('used_tokens')) is int and proof['used_tokens']>=last_used,'accounting_decreased')
            last_used=proof['used_tokens']
            checkpoint=checkpoint or (proof.get('checkpoint') or {}).get('state')=='acknowledged'
            goal=request('thread/goal/get',dict(threadId=thread))['goal']
            native=request('thread/read',dict(threadId=thread,includeTurns=True))['thread']
            _save(output,'native-final.json',native)
            if goal['status']=='paused' and not any(t['status']=='inProgress' for t in native['turns']):
                _require(checkpoint and (output/'checkpoint.md').is_file(),'pause_without_acknowledged_checkpoint')
                result['checkpoint_sha256']=hashlib.sha256((output/'checkpoint.md').read_bytes()).hexdigest()
                _save(output,'pause-receipt.json',dict(goal=goal))
                operator=request('turn/start',dict(threadId=thread,input=[dict(type='text',text='Operator status check only. Reply exactly REAL_DEMO_CHAT_OK; keep the goal paused.')]))['turn']['id']
                while time.monotonic()<end:
                    native=request('thread/read',dict(threadId=thread,includeTurns=True))['thread']
                    current=next((t for t in native['turns'] if t['id']==operator),None)
                    if current and current['status']=='completed':
                        _require(any(i.get('type')=='agentMessage' and i.get('text','').strip()=='REAL_DEMO_CHAT_OK'
                            for i in current['items']),'operator_reply_missing')
                        _require(request('thread/goal/get',dict(threadId=thread))['goal']['status']=='paused','operator_reply_resumed_goal')
                        _save(output,'operator-reply.json',current)
                        final_status=read_status(thread)
                        _qualified_receipt(final_status,options,first)
                        result['raw_usage_replay_verified']=False
                        if observe_raw is not None:
                            audit_end=min(end,time.monotonic()+5)
                            while time.monotonic()<audit_end:
                                replay=observe_raw(thread,actual['createdAt']);final_status=read_status(thread)
                                _qualified_receipt(final_status,options,first)
                                if replay.get('state')=='qualified' and replay['used_tokens']==final_status.get('used_tokens'):
                                    _save(output,'raw-usage-replay.json',replay)
                                    result['raw_usage_replay_verified']=True
                                    break
                                sleep(.2)
                            _require(result['raw_usage_replay_verified'],'final_usage_replay_not_reconciled')
                        _require(all(final_status.get(k)==first[k] for k in ('allocation_id','generation','deadline')),
                            'allowance_identity_or_deadline_changed')
                        _save(output,'final-status.json',final_status)
                        result.update(verdict='PASS',failure_stage=None,operator_reply_completed=True,used_tokens=final_status['used_tokens'])
                        break
                    sleep(.2)
                else:raise AcceptanceFailure('operator_reply_timeout')
                break
            sleep(.2)
        else:raise AcceptanceFailure('fixed_acceptance_deadline_reached')
    except Exception as exc:result['reason']=str(exc)
    finally:
        if thread:
            result['cleanup']=_cleanup(request,thread)
            if not result['cleanup']['verified']:
                result.update(verdict='FAIL',failure_stage='cleanup',reason='owned_thread_cleanup_unverified')
        else:result['cleanup']=dict(verified=True,owned_thread_created=False)
        _save(output,'result.json',result)
    return result


def _main(options):
    # Read-only host preflight before any native thread/model dispatch.
    _require(options.approved,'explicit_real_agent_approval_required')
    _require(options.sandbox=='danger-full-access' and options.approval_policy=='never','unattended_mcp_permissions_unqualified')
    _require(options.app_server.startswith('unix:///'),'existing_exact_unix_endpoint_required')
    physical=Path(options.app_server[7:]).resolve(strict=True);info=physical.stat()
    _require(stat.S_ISSOCK(info.st_mode) and info.st_uid==os.geteuid(),'owned_native_socket_required')
    def peer_identity():
        with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as connection:
            connection.settimeout(3);connection.connect(str(physical))
            pid,uid,_=struct.unpack('3i',connection.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))
        from codex_wake.process import process_identity
        identity=process_identity(pid)
        _require(uid==os.geteuid() and identity,'native_peer_identity_unavailable')
        return dict(pid=pid,identity=identity)
    original_peer=peer_identity()
    for path in (options.policy,options.wake_root):
        _require(path.is_absolute() and path==path.resolve(strict=True),'canonical_private_host_path_required')
        identity=path.stat()
        _require(identity.st_uid==os.geteuid() and not identity.st_mode&0o077,'private_host_authority_required')
    policy_before=options.policy.read_bytes();policy=json.loads(policy_before)
    template=policy.get('self_enrollment',{})
    options.codex_home=Path(template.get('codex_home',''))
    _require(policy.get('version')==2 and policy.get('native_caller_binding') is True and not policy.get('default_allocation'),
             'independent_first_enrollment_host_setup_required')
    _require(template.get('app_server')=='unix://'+str(physical) and template.get('codex_path')==str(options.codex)
        and 0<options.token_limit<=template.get('max_tokens',0) and 0<options.seconds<=template.get('max_seconds',0),'host_caps_or_endpoint_mismatch')
    from codex_wake.native_protocol import native_request
    def request(method,params):
        _require(peer_identity()==original_peer,'native_gateway_identity_changed')
        return native_request('unix://'+str(physical),str(options.codex),method,params,3)
    def read_status(thread):
        completed=subprocess.run([str(options.wake_python),'-m','codex_wake','--wake-root',str(options.wake_root),
            'goal-limits','show','--policy',str(options.policy),'--caller-thread-id',thread,'--json'],
            capture_output=True,text=True,timeout=5,env={k:v for k,v in os.environ.items() if k!='PYTHONPATH'})
        return json.loads(completed.stdout)
    from codex_wake.goal_usage import observe_usage
    result=run(options,request,read_status,observe_raw=lambda thread,created:observe_usage(
        options.codex_home,thread,created,token_accounting='fresh'))
    result.update(wake_root=str(options.wake_root),policy_sha256=hashlib.sha256(policy_before).hexdigest(),
        native_endpoint='unix://'+str(physical),expected_mcp_version=options.expected_version,
        usage_verification='installed usage observer compared with public status; not independent arithmetic')
    result['native_peer_before']=original_peer
    try:result['native_peer_after']=peer_identity()
    except Exception as exc:result.update(verdict='FAIL',failure_stage='cleanup',reason=str(exc))
    result['host_policy_modified']=options.policy.read_bytes()!=policy_before
    if result['host_policy_modified']:result.update(verdict='FAIL',reason='host_policy_changed_during_acceptance')
    _save(options.output,'result.json',result)
    print(json.dumps(result,indent=2));return 0 if result['verdict']=='PASS' else 1


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--approve-real-agent',dest='approved',action='store_true')
    parser.add_argument('--output',type=Path,required=True,help='new private workspace; never reused')
    parser.add_argument('--token-limit',type=int,required=True);parser.add_argument('--seconds',type=int,required=True)
    parser.add_argument('--sandbox',required=True);parser.add_argument('--approval-policy',required=True)
    parser.add_argument('--codex',type=Path,required=True);parser.add_argument('--wake-python',type=Path,required=True)
    parser.add_argument('--app-server',required=True,help='existing exact Unix socket; never starts daemon')
    parser.add_argument('--policy',type=Path,required=True);parser.add_argument('--wake-root',type=Path,required=True)
    parser.add_argument('--expected-version',required=True);parser.add_argument('--model',required=True)
    options=parser.parse_args(argv)
    try:return _main(options)
    except Exception as exc:
        # Setup failures have a receipt too; never overwrite an earlier run.
        if not options.output.exists():
            options.output.mkdir(mode=0o700,parents=True)
            result=dict(verdict='FAIL',failure_stage='setup',reason=str(exc),
                model_dispatch_attempted=False,identity_retries=0,token_limit=options.token_limit,
                time_limit_seconds=options.seconds,shared_daemon_modified=False,host_policy_modified=False,
                cleanup=dict(verified=True,owned_thread_created=False))
            _save(options.output,'result.json',result)
            print(json.dumps(result,indent=2))
        else:print(json.dumps(dict(verdict='FAIL',reason='existing_run_requires_reconciliation',detail=str(exc))))
        return 1


if __name__=='__main__':raise SystemExit(main())
