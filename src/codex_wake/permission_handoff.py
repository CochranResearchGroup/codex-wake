"""Common-policy handoff admission and durable same-task approval continuity.

Identity enters only through a host-attested private RPC or an existing local
operator/actor capability. This module neither issues grants nor renews budgets.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

from .records import WakeError
from .session_permissions import PermissionDenied,PermissionStore,Principal,check_operation

TRIGGERS={'manual','context_limit','update','resource_warning'}


def task_open(root,task_id):
    """A recorded explicit task completion ends task approvals; missing tabs do not."""
    if task_id is None:return
    owner_root=PermissionStore(root).root
    path=owner_root/'wake-owners.json'
    if not path.exists() and not path.is_symlink():return
    from .wake_policy import _owners,_owner_key
    owner=dict(kind='task',id=task_id)
    value=_owners(owner_root)['owners'].get(_owner_key(owner))
    if value is not None:
        if (not isinstance(value,dict) or value.get('owner')!=owner
                or value.get('state')!='completed' or not value.get('event_id') or not value.get('actor')):
            raise PermissionDenied('permission_task_completion_unverified')
        raise PermissionDenied('permission_task_completed')


def validated_task(root,body):
    if body.get('task_brief') is None:return None
    from .task_briefs import TaskBriefStore
    pin=TaskBriefStore(PermissionStore(root).root).validate_pin(body['task_brief'])
    task_open(root,pin['task_id'])
    return pin['task_id']


def verified_successor_principal(root,subject,task_id):
    """Follow private same-task provenance; claims, missing links and cycles refuse."""
    if task_id is None:return Principal(subject)
    from .wake_policy import _read
    from .task_briefs import TaskBriefStore
    graph={}
    for path in (Path(root)/'lifecycle').glob('*.json'):
        receipt=_read(path)
        proof=receipt.get('permission_succession')
        if not isinstance(proof,dict) or proof.get('task_id')!=task_id:
            continue
        intent=receipt.get('intent',{})
        digest=hashlib.sha256(json.dumps(intent,sort_keys=True).encode()).hexdigest()
        pin=intent.get('task_brief');context=receipt.get('permission_context',{})
        if (digest!=receipt.get('fingerprint') or proof.get('source')!=receipt.get('thread_id')
                or receipt.get('successor_thread_id')!=proof.get('successor') or not isinstance(pin,dict)
                or pin.get('task_id')!=task_id or proof.get('pin')!=pin
                or proof.get('state')!='verified' or context.get('subject')!=proof['source']
                or context.get('task_id')!=task_id):
            raise PermissionDenied('permission_succession_unverified')
        TaskBriefStore(PermissionStore(root).root).validate_pin(pin)
        inherited=([context['predecessor']] if context.get('predecessor') else [])+list(context.get('ancestors',[]))
        value=dict(source=proof['source'],inherited=inherited)
        if proof['successor'] in graph and graph[proof['successor']]!=value:
            raise PermissionDenied('permission_succession_ambiguous')
        graph[proof['successor']]=value
    def chain(target,visited):
        if target in visited or len(visited)>=256:
            raise PermissionDenied('permission_succession_cycle_or_limit')
        if target not in graph:return []
        entry=graph[target]
        parents=chain(entry['source'],visited|{target})
        if parents!=entry['inherited']:
            raise PermissionDenied('permission_succession_missing_or_changed')
        return [entry['source'],*parents]
    ancestors=chain(subject,set())
    task_open(root,task_id)
    return Principal(subject,tasks=(task_id,),predecessor=ancestors[0] if ancestors else None,
                     ancestors=tuple(ancestors[1:]))


def caller_principal(args):
    principal=getattr(args,'_permission_principal',None)
    if not isinstance(principal,Principal):
        from .permission_commands import verified_cli_principal
        try:principal=verified_cli_principal(args)
        except (AttributeError,TypeError,OSError,ValueError) as exc:
            raise PermissionDenied('permission_identity_unverified') from exc
    if principal.role!='operator' and principal.subject!=args.thread_id:
        raise PermissionDenied('permission_identity_unverified')
    return principal


def admission_context(root,args,policy,body):
    if not PermissionStore(root).active():return None
    caller_principal(args)
    from .permission_migration import profile_ceiling
    from .wake_policy import _read
    profile_ceiling(_read(Path(args.profiles)),args.profile,args.thread_id)
    trigger=getattr(args,'trigger','manual') or 'manual'
    allowed=policy.get('handoff_triggers',[])
    if (trigger not in TRIGGERS or not isinstance(allowed,list) or any(x not in TRIGGERS for x in allowed)
            or (trigger!='manual' and trigger not in allowed)):
        raise PermissionDenied('handoff_trigger_not_authorized')
    task_id=validated_task(root,body)
    verified=verified_successor_principal(root,args.thread_id,task_id)
    decision=check_operation(root,'handoff.self',verified,target=args.thread_id,
        task_id=task_id,operation_id=args.intent,launch_profile=args.profile)
    context=dict(action='handoff.self',subject=args.thread_id,target=args.thread_id,
        relationship='self',task_id=task_id,operation_id=args.intent,
        predecessor=verified.predecessor,ancestors=list(verified.ancestors),trigger=trigger,approval_id=decision['approval_id'],
        revision=decision['revision'])
    if getattr(args,'profiles',None) is not None:
        context.update(profiles=str(Path(args.profiles).absolute()),profile_name=args.profile)
    return context


def revalidate(root,receipt):
    context=receipt.get('permission_context')
    if context is None:
        if PermissionStore(root).active():
            raise PermissionDenied('permission_handoff_adoption_required')
        return None
    if (not isinstance(context,dict) or context.get('action')!='handoff.self'
            or context.get('subject')!=receipt['intent'].get('source_thread_id')
            or context.get('target')!=context.get('subject')):
        raise PermissionDenied('permission_handoff_context_unverified')
    task_id=context.get('task_id')
    pin=receipt['intent'].get('task_brief')
    if (pin or {}).get('task_id')!=task_id:
        raise PermissionDenied('permission_task_scope_unverified')
    if pin:
        from .task_briefs import TaskBriefStore
        TaskBriefStore(PermissionStore(root).root).validate_pin(pin)
    principal=verified_successor_principal(root,context['subject'],task_id)
    if (principal.predecessor!=context.get('predecessor')
            or list(principal.ancestors)!=context.get('ancestors',[])):
        raise PermissionDenied('permission_succession_changed')
    trigger=context.get('trigger')
    continuation=receipt['intent'].get('continuation',{})
    if context.get('profiles'):
        from .wake_policy import _read
        profile_path=Path(context['profiles'])
        if profile_path!=profile_path.resolve():raise PermissionDenied('permission_profile_changed')
        current=_read(profile_path)
        from .permission_migration import profile_ceiling
        profile_ceiling(current,context['profile_name'],context['subject'])
        current_continuation=current.get('continuations',{}).get(context['subject'])
        if (current_continuation!=continuation or current.get('profiles',{}).get(context['profile_name'])!=receipt['intent'].get('launch')):
            raise PermissionDenied('permission_handoff_authority_changed')
    if trigger not in TRIGGERS or (trigger!='manual' and trigger not in continuation.get('handoff_triggers',[])):
        raise PermissionDenied('handoff_trigger_not_authorized')
    return check_operation(root,'handoff.self',principal,target=context['target'],
        task_id=task_id,operation_id=context['operation_id'],launch_profile=context.get('profile_name'))


def before_effect(path,receipt):
    try:
        revalidate(path.parent.parent,receipt)
        return True
    except (WakeError,OSError,ValueError,KeyError,TypeError) as exc:
        receipt.update(state='uncertain' if receipt.get('uncertain_effect') else 'blocked',
            reason=getattr(exc,'code','permission_handoff_unavailable'))
        from .agent_lifecycle import save
        save(path,receipt)
        return False


def record_succession(root,receipt,target):
    """Called only after exact native successor and goal/brief preflight verification."""
    context=receipt.get('permission_context')
    if not context or not context.get('task_id'):return
    pin=receipt['intent'].get('task_brief')
    if (receipt.get('successor_thread_id')!=target or not pin
            or pin.get('task_id')!=context['task_id']):
        raise PermissionDenied('permission_succession_unverified')
    from .task_briefs import TaskBriefStore
    TaskBriefStore(PermissionStore(root).root).validate_pin(pin)
    task_open(root,pin['task_id'])
    receipt['permission_succession']=dict(state='verified',source=context['subject'],
        successor=target,task_id=pin['task_id'],pin=pin)


def read_only_reconcile(root,args,error):
    """An authenticated retry may observe its exact retained effect, never replay it."""
    caller_principal(args)
    from .wake_policy import _read
    import fcntl
    path=Path(root)/'lifecycle'/(hashlib.sha256(args.intent.encode()).hexdigest()+'.json')
    if not path.exists():return None
    with path.with_suffix('.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        receipt=_read(path);intent=receipt.get('intent',{});context=receipt.get('permission_context',{})
        if (not context or receipt.get('thread_id')!=args.thread_id
                or context.get('profile_name')!=args.profile
                or context.get('profiles')!=str(Path(args.profiles).absolute())
                or intent.get('checkpoint_sha256')!=args.checkpoint_sha256
                or intent.get('mode')!=args.mode or intent.get('expires_at')!=args.expires_at
                or receipt.get('fingerprint')!=hashlib.sha256(json.dumps(intent,sort_keys=True).encode()).hexdigest()
                or not (receipt.get('uncertain_effect') or receipt.get('state')=='uncertain'
                        or receipt.get('successor_thread_id'))):
            return None
        from .native_protocol import native_request
        from .app_server import resolve_codex_cmd
        from .agent_lifecycle import save
        profile=intent['launch'];observed={}
        for thread in filter(None,(receipt['thread_id'],receipt.get('successor_thread_id'))):
            goal=native_request(profile['app_server'],resolve_codex_cmd(profile['codex_path'],required=True),
                'thread/goal/get',dict(threadId=thread),profile['timeout'])['goal']
            native=native_request(profile['app_server'],resolve_codex_cmd(profile['codex_path'],required=True),
                'thread/read',dict(threadId=thread,includeTurns=False),profile['timeout'])['thread']
            if native.get('id')!=thread or (goal is not None and goal.get('threadId')!=thread):
                raise PermissionDenied('permission_reconciliation_identity_changed')
            observed[thread]=dict(goal=goal,native_state=native.get('status'))
        receipt['permission_observation']=dict(read_only=True,observed=observed,
            reason=getattr(error,'code','permission_denied'),uncertainty='retained')
        save(path,receipt)
        return dict(error=dict(code=getattr(error,'code','permission_denied'),message=str(error)),
                    read_only=True,receipt=receipt)


def request(packet):
    """Private bounded-child RPC. Parent must attest native transport first."""
    try:
        arguments=dict(packet['arguments']);binding=packet['binding']
        if (packet.get('verb')!='handoff' or set(binding)!={'thread_id','turn_id','call_id'}
                or any(not isinstance(x,str) or not x for x in binding.values())
                or arguments['thread_id']!=arguments['caller_thread_id']
                or arguments['thread_id']!=binding['thread_id']):
            raise PermissionDenied('permission_identity_unverified')
        from .goal_supervision import _private
        root=Path(packet['root']).absolute()
        if root!=root.resolve():raise PermissionDenied('permission_root_not_canonical')
        root.mkdir(parents=True,exist_ok=True,mode=0o700);_private(root,True)
        profiles=Path(packet['profiles']).absolute();_private(profiles)
        if profiles!=profiles.resolve():raise PermissionDenied('permission_profile_not_canonical')
        args=SimpleNamespace(**arguments,profiles=str(profiles),as_json=True,
            _permission_principal=Principal(binding['thread_id']))
        args.rollback=getattr(args,'rollback',False)
        from .agent_handoff import handoff_command
        from contextlib import redirect_stdout
        from io import StringIO
        output=StringIO()
        with redirect_stdout(output):status=handoff_command(args,root)
        return json.loads(output.getvalue()),status!=0
    except (WakeError,OSError,ValueError,KeyError,TypeError,AttributeError) as exc:
        return dict(error=dict(code=getattr(exc,'code','handoff_unavailable'),message=str(exc))),True


def main():
    import sys
    try:
        raw=sys.stdin.buffer.read(65537)
        if len(raw)>65536:raise ValueError('private handoff packet exceeds limit')
        packet=json.loads(raw)
        if not isinstance(packet,dict):raise ValueError('private handoff packet must be an object')
        value,failed=request(packet)
    except (ValueError,TypeError) as exc:
        value,failed=dict(error=dict(code='invalid_argument',message=str(exc))),True
    print(json.dumps(value))
    return 2 if failed else 0


if __name__=='__main__':raise SystemExit(main())
