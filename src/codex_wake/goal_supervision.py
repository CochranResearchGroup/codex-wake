"""Independent native supervision for one exact existing Codex session.

This module requests checkpoints, pauses goals and interrupts exact turns. It
never kills a shared executor, promises tool termination, or renews an allocation.
"""
from contextlib import contextmanager
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import stat
import tempfile
import time
from uuid import UUID, uuid4

from .native_protocol import native_request
from .process import boot_id_value, process_exists, process_identity

NATIVE_GOAL_STATUSES={'active','paused','blocked','complete','budgetLimited','usageLimited'}


def _private(path, directory=False):
    info=path.lstat()
    if path.is_symlink() or info.st_uid!=os.geteuid() or stat.S_IMODE(info.st_mode)&0o077:
        raise ValueError('goal supervision paths must be private and owned')
    if directory and not stat.S_ISDIR(info.st_mode):raise ValueError('goal supervision directory unavailable')
    if not directory and not stat.S_ISREG(info.st_mode):raise ValueError('goal supervision file unavailable')


def _directory(root):
    root=Path(root).absolute()
    if root!=root.resolve():raise ValueError('supervision root cannot traverse symlinks')
    root.mkdir(parents=True,exist_ok=True,mode=0o700);_private(root,True)
    directory=root/'goal-supervision';directory.mkdir(exist_ok=True,mode=0o700);_private(directory,True)
    return directory


def _save(path,value):
    descriptor,temporary=tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(descriptor,'w') as stream:
            json.dump(value,stream,sort_keys=True);stream.flush();os.fsync(stream.fileno())
        os.replace(temporary,path)
        descriptor=os.open(path.parent,os.O_RDONLY)
        try:os.fsync(descriptor)
        finally:os.close(descriptor)
    finally:
        if os.path.exists(temporary):os.unlink(temporary)


@contextmanager
def _lock(directory,name):
    descriptor=os.open(directory/(name+'.lock'),os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    with os.fdopen(descriptor,'a') as stream:
        fcntl.flock(stream,fcntl.LOCK_EX)
        yield


def _name(thread):
    if not isinstance(thread,str) or str(UUID(thread))!=thread:raise ValueError('exact caller UUID required')
    return hashlib.sha256(thread.encode()).hexdigest()


class CallerGrantMissing(ValueError):
    """The host policy has no authority for this caller; no effect was attempted."""


def _delegated_grant(policy,thread,allocation_id,root):
    allocations=policy['allocations']
    if not isinstance(allocations,dict):raise ValueError('host allocations must be an object')
    template=policy.get('self_enrollment')
    selected=allocation_id
    directory=None
    if root is not None:
        base=Path(root).absolute()
        if base!=base.resolve():raise ValueError('supervision root cannot traverse symlinks')
        directory=base/'goal-supervision'
        receipt=directory/(_name(thread)+'.json')
        if selected is None and template is not None and receipt.exists():
            _private(receipt);current=json.loads(receipt.read_text())
            if current['thread_id']!=thread:raise ValueError('stored caller identity changed')
            selected=current['allocation_id']
    selected=selected or policy.get('default_allocation')
    if selected in allocations:
        return dict(allocations[selected],allocation_id=selected,host_delegated=True)
    if template is None:raise ValueError('select an existing host objective allocation')
    fields={'app_server','codex_path','codex_home','max_tokens','max_seconds','rpc_timeout'}
    if not isinstance(template,dict) or set(template)-fields or not fields-{'rpc_timeout'}<=set(template):
        raise ValueError('host self-enrollment envelope is invalid')
    own='native-'+thread
    selected=selected or own
    if not isinstance(selected,str) or not selected.startswith('native-'):
        raise ValueError('select an existing host objective allocation')
    _name(selected[len('native-'):])
    grant=dict(template,allocation_id=selected,host_delegated=True,auto_enrolled=True)
    if selected!=own:
        if directory is None:raise ValueError('existing objective ledger required')
        path=directory/'allocations'/(hashlib.sha256(selected.encode()).hexdigest()+'.json')
        _private(path);existing=json.loads(path.read_text())
        if (existing['allocation_id']!=selected or
                existing['grant']!=dict(grant,rpc_timeout=grant.get('rpc_timeout',5))):
            raise ValueError('existing objective envelope changed')
    return grant


def _load_grant(policy_path,thread,allocation_id=None,root=None):
    path=Path(policy_path).absolute();_private(path)
    if path!=path.resolve():raise ValueError('policy cannot traverse symlinks')
    def unique(pairs):
        result={}
        for key,value in pairs:
            if key in result:raise ValueError('duplicate host policy key')
            result[key]=value
        return result
    policy=json.loads(path.read_text(),object_pairs_hook=unique)
    version=policy.get('version')
    if type(version) is not int or version not in (1,2):raise ValueError('unsupported goal limits policy')
    callers=policy['callers'] if version==1 else policy.get('callers',{})
    if not isinstance(callers,dict):raise ValueError('host callers must be an object')
    if version==1 or thread in callers:
        if thread not in callers:raise CallerGrantMissing('host caller grant unavailable or malformed')
        grant=callers[thread]
        if allocation_id is not None and allocation_id!=grant.get('allocation_id'):
            raise ValueError('explicit caller grant cannot select the requested allocation; qualified migration required for the selected allocation')
    else:
        if policy.get('native_caller_binding') is not True:
            raise ValueError('host must require native caller binding')
        grant=_delegated_grant(policy,thread,allocation_id,root)
    for key in ('max_tokens','max_seconds'):
        if type(grant[key]) is not int or grant[key]<=0:raise ValueError('invalid host allocation cap')
    if not isinstance(grant['allocation_id'],str) or not grant['allocation_id']:raise ValueError('allocation identity unavailable')
    for key in ('codex_path','codex_home'):
        selected=Path(grant[key])
        if not selected.is_absolute() or (key=='codex_home' and selected!=selected.resolve()):raise ValueError('host path must be exact and absolute')
    if not Path(grant['codex_path']).is_file():raise ValueError('host Codex executable unavailable')
    endpoint=grant['app_server']
    if not isinstance(endpoint,str) or not endpoint.startswith('unix:///') or not Path(endpoint[7:]).is_absolute():
        raise ValueError('host must approve an exact absolute Unix endpoint')
    timeout=grant.get('rpc_timeout',5)
    if type(timeout) not in (int,float) or not math.isfinite(timeout) or not 0<timeout<=5:raise ValueError('invalid RPC timeout')
    return dict(grant,rpc_timeout=timeout)


def _grant(policy_path,thread,allocation_id=None,root=None):
    try:return _load_grant(policy_path,thread,allocation_id,root)
    except (KeyError,TypeError,AttributeError) as exc:raise ValueError('host caller grant unavailable or malformed') from exc


def verified_native_caller(context,claimed):
    """Accept metadata from the host's private native MCP connection only.

    Transport ownership belongs to the host installation; this is not an
    authentication mechanism for arbitrary HTTP clients or hostile same-UID code.
    """
    if not isinstance(context,dict):raise ValueError('verified native caller metadata required')
    turn=context.get('x-codex-turn-metadata')
    if not isinstance(turn,dict):raise ValueError('verified native caller turn required')
    identities=[context.get('threadId'),context.get('sessionId'),
        turn.get('thread_id'),turn.get('session_id')]
    if any(identity!=claimed for identity in identities):
        raise ValueError('native caller identity does not match claim')
    _name(claimed)
    if not all(isinstance(value,str) and value for value in (context.get('callId'),turn.get('turn_id'))):
        raise ValueError('native caller call and turn required')
    return dict(thread_id=claimed,turn_id=turn['turn_id'],call_id=context['callId'])


def _public(receipt):
    return dict({key:value for key,value in receipt.items() if key not in ('grant','policy_path','prior_allocation')},
        stop_scope='registered_goal_campaign',descendant_stop_verified=False)


def _request(grant,method,params):
    return native_request(grant['app_server'],grant['codex_path'],method,params,grant['rpc_timeout'])


class NativeObservationUnavailable(ValueError):
    def __init__(self,method,cause,duration=None):
        super().__init__(method+': '+cause)
        self.method=method
        self.cause=cause
        self.duration=duration


def _native(grant,thread):
    started=time.monotonic();deadline=started+grant['rpc_timeout']
    def observe(method,params):
        remaining=deadline-time.monotonic()
        try:
            if remaining<=0:raise TimeoutError('native observation budget exhausted')
            return _request(dict(grant,rpc_timeout=remaining),method,params)
        except Exception as exc:
            raise NativeObservationUnavailable(method,type(exc).__name__,time.monotonic()-started) from exc
    goal=observe('thread/goal/get',dict(threadId=thread))['goal']
    native=observe('thread/read',dict(threadId=thread,includeTurns=False))['thread']
    if native.get('id')!=thread or (goal and goal.get('threadId')!=thread):raise ValueError('native thread identity changed')
    cursor=None;seen_cursors=set();seen_turns=set();active=[]
    for _ in range(32):
        params=dict(threadId=thread,limit=128,sortDirection='desc',itemsView='notLoaded')
        if cursor is not None:params['cursor']=cursor
        page=observe('thread/turns/list',params)
        turns=page.get('data')
        if not isinstance(turns,list):raise ValueError('native turn state unavailable')
        for turn in turns:
            identity=turn.get('id');status=turn.get('status')
            if (not isinstance(identity,str) or not identity or identity in seen_turns
                    or status not in ('completed','interrupted','failed','inProgress')):
                raise ValueError('native turn state ambiguous')
            seen_turns.add(identity)
            if status=='inProgress':active.append(identity)
        if len(active)>1:raise ValueError('native active turn ambiguous')
        cursor=page.get('nextCursor')
        if cursor is None:return goal,active
        if not isinstance(cursor,str) or not cursor or cursor in seen_cursors:
            raise ValueError('native turn cursor ambiguous')
        seen_cursors.add(cursor)
    raise ValueError('native turn observation page limit exceeded')


def _allocation_path(directory,allocation_id):
    child=directory/'allocations';child.mkdir(exist_ok=True,mode=0o700);_private(child,True)
    return child/(hashlib.sha256(allocation_id.encode()).hexdigest()+'.json')


def _allocation_admit(directory,receipt,old):
    renewal=bool(old and old['allocation_id']!=receipt['allocation_id'])
    anchor=None
    if renewal:
        if receipt['grant'].get('renews_allocation')!=old['allocation_id']:
            raise ValueError('changing allocation requires explicit host renewal of the prior allocation')
        from .goal_usage import observe_usage
        original=observe_usage(receipt['grant']['codex_home'],receipt['thread_id'],receipt['goal_created_at'],
            token_accounting=receipt['token_accounting'])
        if original.get('state')!='qualified' or not original.get('anchor'):
            raise ValueError('explicit host renewal requires qualified original history')
        anchor=original['anchor']
    path=_allocation_path(directory,receipt['allocation_id'])
    with _lock(path.parent,path.stem):
        if path.exists():
            _private(path);allocation=json.loads(path.read_text())
            if allocation['grant']!=receipt['grant']:raise ValueError('host allocation changed; explicit renewal required')
            if (receipt['token_limit']>allocation['token_limit'] or
                    receipt['time_limit_seconds']>allocation['time_limit_seconds']):
                raise ValueError('same allocation may only tighten limits')
            if receipt['token_accounting']!=allocation['token_accounting']:
                raise ValueError('allocation accounting basis cannot change during self enrollment')
        else:
            initial=receipt['grant'].get('initial_boundary')
            members={};origin=receipt['time_origin']
            if initial is not None:
                if not isinstance(initial,dict) or initial.get('token_accounting')!=receipt['token_accounting']:
                    raise ValueError('host initial boundary accounting basis unavailable')
                origin=initial.get('started_at');initial_anchor=initial.get('reset_anchor')
                if (type(origin) not in (int,float) or not math.isfinite(origin)
                        or not isinstance(initial_anchor,dict)):
                    raise ValueError('host initial boundary unavailable')
                root_thread=initial_anchor.get('thread_id');_name(root_thread)
                created=initial_anchor.get('goal_created_at')
                if (type(created) not in (int,float) or not math.isfinite(created)
                        or not created<=origin<=receipt['started_upper']):
                    raise ValueError('host initial boundary time is unqualified')
                from .goal_usage import observe_usage
                qualified=observe_usage(receipt['grant']['codex_home'],root_thread,created,
                    reset_anchor=initial_anchor,token_accounting=receipt['token_accounting'])
                if qualified.get('state')!='qualified':
                    raise ValueError('host initial boundary requires qualified original history')
                # Register the boundary owner even if a successor enrolls first;
                # otherwise spending between renewal and enrollment disappears.
                members[root_thread]=dict(goal_created_at=created,reset_anchor=initial_anchor)
            allocation=dict(version=1,allocation_id=receipt['allocation_id'],grant=receipt['grant'],
                token_limit=receipt['token_limit'],time_limit_seconds=receipt['time_limit_seconds'],
                token_accounting=receipt['token_accounting'],time_origin=origin,
                deadline=origin+receipt['time_limit_seconds'],members=members,charges={},used_tokens=0,stop_latched=False,boot_id=boot_id_value())
        if receipt['thread_id'] not in allocation['members'] and len(allocation['members'])>=32:
            raise ValueError('allocation member limit reached')
        allocation['token_limit']=min(receipt['token_limit'],allocation['token_limit'])
        allocation['time_limit_seconds']=min(receipt['time_limit_seconds'],allocation['time_limit_seconds'])
        allocation['deadline']=min(allocation['deadline'],allocation['time_origin']+allocation['time_limit_seconds'])
        allocation['members'].setdefault(receipt['thread_id'],dict(goal_created_at=receipt['goal_created_at'],reset_anchor=anchor))
        member=allocation['members'][receipt['thread_id']]
        if renewal and member.get('reset_anchor')!=anchor:
            raise ValueError('renewal boundary changed; reconcile the persisted target allocation before continuing')
        receipt.update(goal_created_at=member['goal_created_at'],time_origin=allocation['time_origin'],
            deadline=allocation['deadline'],token_limit=allocation['token_limit'],
            time_limit_seconds=allocation['time_limit_seconds'],allocation_path=str(path),
            used_tokens=allocation['used_tokens'])
        if allocation.get('boot_id')!=boot_id_value():allocation['stop_latched']=True
        if allocation['stop_latched']:receipt['stop_latched']=True
        if 'winddown_deadline' in allocation:
            receipt['allocation_winddown_deadline']=allocation['winddown_deadline']
        _save(path,allocation)
    if renewal:
        # Finalize the departed member, not the entire previous allocation.
        # Its qualified snapshot remains chargeable without charging new work
        # to both allowances. A crash before the caller receipt is replaced
        # makes that old receipt hold until the exact renewal is reconciled.
        previous=Path(old['allocation_path']);_private(previous)
        with _lock(previous.parent,previous.stem):
            prior=json.loads(previous.read_text());member=prior['members'][receipt['thread_id']]
            if 'finalized_charges' not in member:
                from .goal_usage import observe_usage
                final=observe_usage(old['grant']['codex_home'],receipt['thread_id'],member['goal_created_at'],
                    token_accounting=prior['token_accounting'],reset_anchor=member.get('reset_anchor'))
                if final.get('state')!='qualified' or any(
                        final['anchor'].get(key)!=anchor[key] for key in
                        ('version','thread_id','goal_created_at','boundary')) or any(
                        final['anchor']['response_hashes'].get(key)!=value
                        for key,value in anchor['response_hashes'].items()):
                    raise ValueError('renewal boundary changed; reconcile before continuing')
                # History can grow after target admission. Freeze old charges
                # at that admitted boundary; later responses belong to the new
                # allowance, even if another watcher sampled them in the old one.
                frozen={key:value for key,value in final['charges'].items()
                        if key in anchor['response_hashes']}
                transferred=set(final['charges'])-set(frozen)
                prior.setdefault('renewed_out_charges',{}).update(
                    {key:final['charges'][key] for key in transferred})
                prior['charges']={key:value for key,value in prior['charges'].items()
                                  if key not in transferred}
                prior['used_tokens']=sum(value['tokens'] for value in prior['charges'].values())
                member.update(finalized_charges=frozen,final_anchor=anchor,
                    renewed_into=receipt['allocation_id'])
                _save(previous,prior)


def _usage(receipt):
    from .goal_usage import observe_usage
    if not receipt.get('grant',{}).get('host_delegated'):
        return observe_usage(receipt['grant']['codex_home'],receipt['thread_id'],receipt['goal_created_at'],
            reset_anchor=receipt.get('reset_anchor'),token_accounting=receipt.get('token_accounting','cache_inclusive'))
    path=Path(receipt['allocation_path']);_private(path)
    with _lock(path.parent,path.stem):
        allocation=json.loads(path.read_text());charges={}
        if 'finalized_charges' in allocation['members'][receipt['thread_id']]:
            return dict(state='unknown',used_tokens=None,reason='member_renewal_pending')
        for thread,member in allocation['members'].items():
            if 'finalized_charges' in member:
                observation=dict(state='qualified',charges=member['finalized_charges'])
            else:
                observation=observe_usage(receipt['grant']['codex_home'],thread,member['goal_created_at'],
                token_accounting=allocation['token_accounting'],reset_anchor=member.get('reset_anchor'))
            if observation['state']!='qualified':
                return dict(state='unknown',used_tokens=None,reason='allocation_member_accounting_unknown',
                    member_thread_id=thread,member_reason=observation.get('reason'))
            for key,value in observation['charges'].items():
                if key in charges and charges[key]!=value:
                    return dict(state='unknown',used_tokens=None,reason='allocation_response_conflict')
                charges[key]=value
        if any(charges.get(key)!=value for key,value in allocation['charges'].items()):
            return dict(state='unknown',used_tokens=None,reason='allocation_history_changed')
        used=sum(value['tokens'] for value in charges.values())
        allocation.update(charges=charges,used_tokens=used)
        _save(path,allocation)
        receipt.update(token_limit=allocation['token_limit'],deadline=allocation['deadline'])
        if allocation.get('first_stop'):
            key='first_stop' if allocation['first_stop'].get('receipt_generation')==receipt['generation'] else 'allocation_first_stop'
            receipt.setdefault(key,allocation['first_stop'])
        if allocation['stop_latched']:receipt['stop_latched']=True
        if 'winddown_deadline' in allocation:
            receipt['allocation_winddown_deadline']=allocation['winddown_deadline']
        return dict(state='qualified',used_tokens=used,token_accounting=allocation['token_accounting'],
            renewed_out_tokens=sum(value['tokens'] for value in allocation.get('renewed_out_charges',{}).values()),
            member_thread_ids=sorted(allocation['members']),sampled=True,reason=None)


def _accounting_decreased(receipt,observation):
    # Net spending can fall only when explicit host renewal transfers response
    # charges out. Compare gross spending so each receipt consumes that durable
    # transfer once, without hiding an unexplained loss of accounting history.
    prior=receipt.get('accounting',{}).get('renewed_out_tokens',0)
    current=observation.get('renewed_out_tokens',0)
    if type(prior) is not int or type(current) is not int or not 0<=prior<=current:
        return True
    return observation['used_tokens']+current<receipt['used_tokens']+prior


def _heartbeat(directory):
    try:
        path=directory/'controller.json';_private(path)
        value=json.loads(path.read_text())
        age=time.clock_gettime(time.CLOCK_BOOTTIME)-value['observed_boottime']
        valid=(value['active'] is True and value['pid']!=os.getpid()
            and value['boot_id']==boot_id_value() and process_exists(value['pid'])
            and process_identity(value['pid'])==value['identity']
            and 0<=age<=max(3,3*value['interval']))
        return dict(value,fresh=valid,age_seconds=age,process_alive=process_exists(value['pid']) and process_identity(value['pid'])==value['identity'])
    except (OSError,ValueError,KeyError,TypeError):return dict(fresh=False,reason='controller_unavailable')


def show(root,policy_path,caller_thread_id,allocation_id=None,*,permission_principal=None,native_context=None):
    from .permission_enforcement import principal_for, authorize, describe
    principal=principal_for(root,caller_thread_id,native_context=native_context,principal=permission_principal)
    if principal:authorize(root,"session.inspect",principal)
    name=_name(caller_thread_id);grant=_grant(policy_path,caller_thread_id,allocation_id,root)
    directory=_directory(root);path=directory/(name+'.json')
    if not path.exists():
        controller=_heartbeat(directory)
        from .goal_readiness import engagement
        return dict(state='held',reason='not_enrolled',thread_id=caller_thread_id,controller=controller,
            engagement=engagement({},controller))
    with _lock(directory,name):
        _private(path);receipt=json.loads(path.read_text())
        if receipt['grant']!=grant:
            receipt.update(state='held',reason='host_policy_changed')
        receipt['controller']=_heartbeat(directory)
        if receipt['state'] in ('armed','checkpoint_requested') and not receipt['controller']['fresh']:
            receipt.update(state='held',reason='controller_unavailable')
        receipt['sampled']=True;receipt['maximum_token_overshoot']=None
        from .goal_readiness import engagement
        result=_public(receipt)
        result['engagement']=engagement(receipt,receipt['controller'])
        if principal:result['enforcement_permissions']=describe(root,caller_thread_id,principal=principal)
        return result


class AccountingUnavailable(ValueError):
    code='goal_accounting_unavailable'

    def __init__(self,message,observation):
        super().__init__(message)
        self.accounting_reason=observation.get('member_reason') or observation.get('reason') or 'unqualified_history'


def diagnose(root,policy_path,caller_thread_id,allocation_id=None,*,permission_principal=None,native_context=None):
    """Read original history and actual watcher without enrolling or changing authority."""
    from .permission_enforcement import principal_for,authorize
    principal=principal_for(root,caller_thread_id,native_context=native_context,principal=permission_principal)
    if principal:authorize(root,'session.inspect',principal)
    grant=_grant(policy_path,caller_thread_id,allocation_id,root)
    if grant.get('host_delegated'):verified_native_caller(native_context,caller_thread_id)
    goal,active=_native(grant,caller_thread_id)
    from .goal_usage import observe_usage
    if not goal:
        accounting=dict(state='unknown',reason='native_goal_missing')
    else:
        accounting=observe_usage(grant['codex_home'],caller_thread_id,goal['createdAt'],token_accounting='fresh')
    controller=_heartbeat(_directory(root))
    status=('accounting_unavailable' if accounting.get('state')!='qualified' else
            'watcher_ready' if controller.get('fresh') else 'watcher_unavailable')
    action=('Restore the original history identified by the accounting reason; do not reset its usage.'
            if status=='accounting_unavailable' else
            'Enroll the existing session with the user-approved limits; registration does not itself prove engagement.'
            if status=='watcher_ready' else
            'Run goal-limits watcher-status, then start-watcher with existing authority if the configured service is unmasked.')
    return dict(thread_id=caller_thread_id,allocation_id=grant['allocation_id'],
        enrolled=(_directory(root)/(_name(caller_thread_id)+'.json')).exists(),
        native_goal_status=goal.get('status') if goal else None,active_turn_count=len(active),
        accounting={key:accounting[key] for key in ('state','reason','used_tokens','token_accounting') if key in accounting},
        controller=controller,readiness=dict(status=status,next_action=action),effect_attempted=False)


def enroll(root,policy_path,caller_thread_id,token_limit,time_limit_seconds,
           checkpoint_token_percent=5,checkpoint_seconds=60,token_accounting=None,
           allocation_id=None,native_context=None,permission_principal=None,task_id=None,operation_id=None):
    from .permission_enforcement import principal_for,authorize,enrollment_action
    principal=principal_for(root,caller_thread_id,native_context=native_context,principal=permission_principal)
    name=_name(caller_thread_id);grant=_grant(policy_path,caller_thread_id,allocation_id,root)
    binding=verified_native_caller(native_context,caller_thread_id) if grant.get('host_delegated') else None
    for key,value,maximum in [('tokens',token_limit,grant['max_tokens']),('seconds',time_limit_seconds,grant['max_seconds'])]:
        if type(value) is not int or not 0<value<=maximum:raise ValueError('requested '+key+' exceed host allocation')
    if type(checkpoint_token_percent) not in (int,float) or not math.isfinite(checkpoint_token_percent) or not 0<=checkpoint_token_percent<=100:
        raise ValueError('invalid checkpoint token reserve')
    if type(checkpoint_seconds) not in (int,float) or not math.isfinite(checkpoint_seconds) or checkpoint_seconds<0:raise ValueError('invalid checkpoint time reserve')
    directory=_directory(root);path=directory/(name+'.json')
    # Configured service repair is a distinct common-policy action. Never undo a
    # mask or infer authority from enrollment permission alone.
    watcher_setup=None
    if principal and not _heartbeat(directory).get('fresh'):
        from .session_permissions import PermissionStore
        store=PermissionStore(root)
        if store.active() and store.evaluate('enforcement.watcher_start',principal,
                target=principal.subject,task_id=task_id,operation_id=operation_id)['permission']=='allow':
            from .goal_watcher import start_watcher
            watcher_setup=start_watcher(root,principal=principal,task_id=task_id,operation_id=operation_id)
    with _lock(directory,'maintenance'), _lock(directory,name):
        from .goal_maintenance import admission_guard
        admission_guard(directory)
        old=None
        if path.exists():_private(path);old=json.loads(path.read_text())
        permission=None
        if principal:
            action=enrollment_action(old,token_limit,time_limit_seconds,token_accounting,grant['allocation_id'])
            permission=authorize(root,action,principal,task_id=task_id,operation_id=operation_id)
        same=bool(old and old['allocation_id']==grant['allocation_id'])
        previous_basis=old.get('token_accounting','cache_inclusive') if old else None
        basis=token_accounting or (previous_basis if same else 'fresh')
        if basis not in ('fresh','cache_inclusive'):raise ValueError('unsupported token accounting')
        basis_changed=bool(same and previous_basis!=basis)
        if old and any(old['grant'][key]!=grant[key] for key in ('app_server','codex_home')):
            raise ValueError('cross-native session migration is unsupported')
        if same and (token_limit>old['token_limit'] or time_limit_seconds>old['time_limit_seconds']):
            raise ValueError('same allocation may only tighten limits')
        goal,active=_native(grant,caller_thread_id)
        if not goal:raise ValueError('existing native goal required')
        created=old['goal_created_at'] if old else goal['createdAt']
        if type(created) not in (int,float) or not math.isfinite(created):raise ValueError('native goal start unavailable')
        from .lifecycle_budget import trusted_upper
        now=trusted_upper();boottime=time.clock_gettime(time.CLOCK_BOOTTIME)
        if created>now:raise ValueError('native goal start is after qualified current time')
        receipt=dict(old) if same else dict(thread_id=caller_thread_id,generation=uuid4().hex,
            allocation_id=grant['allocation_id'],goal_created_at=created,used_tokens=0,
            started_upper=now,started_boottime=boottime,boot_id=boot_id_value(),
            time_origin=now if old else created,effects={},checkpoint=None,
            prior_allocation=old if old else None)
        receipt.update(caller_binding=binding,grant=grant,policy_path=str(Path(policy_path).absolute()),token_limit=token_limit,
            time_limit_seconds=time_limit_seconds,checkpoint_token_percent=checkpoint_token_percent,
            checkpoint_seconds=checkpoint_seconds)
        if basis_changed:
            receipt.setdefault('accounting_basis_history',[]).append(dict(
                token_accounting=previous_basis,used_tokens=old['used_tokens'],accounting=old.get('accounting')))
        receipt['token_accounting']=basis
        receipt['deadline']=receipt['time_origin']+time_limit_seconds
        authority_fields=('generation','token_limit','deadline','token_accounting','checkpoint_token_percent','checkpoint_seconds')
        if not same or any(old.get(key)!=receipt.get(key) for key in authority_fields):
            receipt['enrollment_revision']=old.get('enrollment_revision',0)+1 if same else 1
            receipt.pop('poll_ack',None)
        else:receipt.setdefault('enrollment_revision',1)
        if grant.get('auto_enrolled') and grant['allocation_id']=='native-'+caller_thread_id and not old:
            from .goal_usage import observe_usage
            first=observe_usage(grant['codex_home'],caller_thread_id,created,token_accounting=basis)
            if first.get('state')!='qualified':raise AccountingUnavailable('first enrollment requires qualified original history',first)
            if first.get('parent_thread_id'):raise ValueError('successor must select its existing objective allocation')
        if grant.get('host_delegated'):_allocation_admit(directory,receipt,old)
        observation=_usage(receipt)
        # Enrollment is not admitted until the first complete observation is
        # qualified. A transient setup scan must not publish a stop receipt that
        # only a resource renewal could clear. Existing campaigns still fail
        # closed through their normal accounting/winddown path.
        if (not old and observation.get('state')!='qualified' and
                (observation.get('reason')=='usage_scan_time_limit' or
                 observation.get('reason')=='allocation_member_accounting_unknown' and
                 observation.get('member_reason')=='usage_scan_time_limit')):
            raise AccountingUnavailable('initial accounting unavailable; enrollment not admitted',observation)
        if basis_changed and observation.get('state')!='qualified':
            raise ValueError('accounting basis change requires qualified original history')
        if old and not same and not grant.get('host_delegated'):
            if observation.get('state')!='qualified' or not observation.get('anchor'):
                raise ValueError('explicit reset requires qualified response history')
            receipt['reset_anchor']=observation['anchor']
            observation=_usage(receipt)
        def hold(reason):
            _first_stop(path,receipt,reason)
            receipt.update(state='held',reason=reason,stop_latched=True)
        if observation.get('state')=='qualified' and type(observation.get('used_tokens')) is int:
            if not basis_changed and _accounting_decreased(receipt,observation):
                receipt['accounting']=observation;hold('accounting_decreased')
            else:
                receipt.update(used_tokens=observation['used_tokens'],accounting=observation,state='armed',reason=None)
        else:
            receipt['accounting']=observation;hold('accounting_unknown')
        controller=_heartbeat(directory);receipt['controller_generation']=controller.get('generation')
        if not controller['fresh']:receipt.update(state='held',reason='controller_unavailable')
        if receipt.get('used_tokens',0)>=token_limit or now>=receipt['deadline']:
            hold('allocation_exhausted')
        if receipt.get('stop_latched') or (same and old['state'] in ('stopped','stop_unverified')):
            hold('continuation_held')
        if receipt['boot_id']!=boot_id_value():
            hold('boot_identity_changed')
        if permission:
            receipt['enforcement_permission']=permission
            receipt['permission_subject']=principal.subject
        receipt['native_goal_status']=goal.get('status')
        if watcher_setup is not None:receipt['watcher_setup']=watcher_setup
        if goal.get('status') not in NATIVE_GOAL_STATUSES:
            hold('native_goal_state_unknown')
        _save(path,receipt)
        from .goal_readiness import engagement
        return dict(_public(receipt),controller=controller,sampled=True,maximum_token_overshoot=None,
            engagement=engagement(receipt,controller))


def _effect(path,receipt,key,method,params):
    if method=='turn/steer':
        from .permission_enforcement import controller_permission
        permission=controller_permission(path.parent.parent,receipt)
        receipt['enforcement_continuation_permission']=permission
        if permission['permission'] not in ('allow','legacy'):
            receipt['permission_effect_blocked']=True
            _save(path,receipt)
            return False
    effects=receipt.setdefault('effects',{})
    if key in effects:return effects[key]['state']=='acknowledged'
    effects[key]=dict(state='intended',method=method,params=params)
    _save(path,receipt)
    try:
        _request(receipt['grant'],method,params)
        effects[key]['state']='acknowledged';_save(path,receipt)
        return True
    except Exception as exc:
        effects[key].update(state='uncertain',error=type(exc).__name__);_save(path,receipt)
        return False


def _allocation_latch(receipt,reason,deadline=None):
    if not receipt.get('allocation_path'):return deadline
    path=Path(receipt['allocation_path']);_private(path)
    with _lock(path.parent,path.stem):
        allocation=json.loads(path.read_text())
        if receipt.get('first_stop'):
            allocation.setdefault('first_stop',receipt['first_stop'])
        allocation.update(stop_latched=True,stop_reason=reason)
        if deadline is not None:
            deadline=min(deadline,allocation.get('winddown_deadline',deadline))
            allocation['winddown_deadline']=deadline
            receipt['allocation_winddown_deadline']=deadline
        _save(path,allocation)
    return deadline


def _first_stop(path,receipt,reason):
    if 'first_stop' in receipt:return
    original=None
    if receipt.get('allocation_path'):
        allocation_path=Path(receipt['allocation_path']);_private(allocation_path)
        with _lock(allocation_path.parent,allocation_path.stem):
            retained=json.loads(allocation_path.read_text()).get('first_stop')
            if retained and retained.get('receipt_generation')==receipt['generation']:
                original=retained
    now=time.clock_gettime(time.CLOCK_BOOTTIME)
    elapsed=now-receipt['started_boottime']
    qualified=receipt['boot_id']==boot_id_value() and elapsed>=0
    try:
        controller_path=path.parent/'controller.json';_private(controller_path)
        controller=json.loads(controller_path.read_text())
    except (OSError,ValueError):controller={}
    # Old latches cannot reveal their original fault retrospectively. Label the
    # first retained diagnostic explicitly instead of inventing that history.
    receipt['first_stop']=original or dict(version=1,reason=reason,
        provenance='existing_latch_observed' if receipt.get('stop_latched') else 'stop_decision',
        observed_boottime=now,boot_id=boot_id_value(),
        observed_upper=receipt['started_upper']+elapsed if qualified else None,
        clock_qualified=qualified,clock_reason='same_boot_elapsed' if qualified else
            ('boot_identity_changed' if receipt['boot_id']!=boot_id_value() else 'elapsed_time_invalid'),
        last_usage_observed_boottime=receipt.get('observed_boottime'),
        controller_observed_boottime=controller.get('observed_boottime'),
        controller_generation=controller.get('generation',receipt.get('controller_generation')),
        controller_pid=controller.get('pid'),controller_identity=controller.get('identity'),
        receipt_generation=receipt['generation'],allocation_id=receipt['allocation_id'],
        used_tokens=receipt.get('used_tokens'),token_limit=receipt['token_limit'],
        deadline=receipt['deadline'],token_accounting=receipt.get('token_accounting'),
        accounting_state=receipt.get('accounting',{}).get('state'),
        native_method=receipt.get('observation_method') if reason=='observation_unavailable' else None,
        cause=receipt.get('observation_error') if reason=='observation_unavailable' else None,
        observation_duration_seconds=receipt.get('observation_duration_seconds') if reason=='observation_unavailable' else None)
    receipt.update(stop_latched=True,state='stop_unverified',reason=reason)
    # The shared ledger is the authority for successor admission. Commit its
    # latch first, so a crash during the caller receipt write cannot reopen it.
    _allocation_latch(receipt,reason)
    _save(path,receipt)


def _stop(path,receipt,reason,goal=None,active=None):
    _first_stop(path,receipt,reason)
    receipt.update(reason=reason,state='stop_unverified',stop_latched=True)
    _allocation_latch(receipt,reason)
    try:
        if active is None:goal,active=_native(receipt['grant'],receipt['thread_id'])
        # Enforcement owns the campaign turn observed at stop, not every later
        # operator turn in this conversation. Persist before native effects.
        if 'stop_turns' not in receipt or (receipt.get('pause_observed') and goal and goal.get('status')=='active'):
            legacy_turns = {effect.get('params', {}).get('turnId') or
                effect.get('params', {}).get('expectedTurnId') for effect in receipt.get('effects', {}).values()
                if effect.get('method') in ('turn/interrupt', 'turn/steer')}
            receipt['stop_turns']=list(active) if goal and goal.get('status')=='active' else sorted(legacy_turns - {None})
            _save(path,receipt)
        if receipt.get('pause_observed') and goal and goal.get('status')!='paused':
            # Observed paused -> active is a new enforcement event, even if a
            # previous interrupt was unverified. Retain the old effect ledger.
            receipt['pause_epoch']=receipt.get('pause_epoch',0)+1
            receipt['pause_observed']=False
        if receipt.get('stop_proof') and ((goal and goal.get('status')!='paused') or active):
            receipt['stop_proof']=False
        thread=receipt['thread_id']
        if goal and goal.get('status')!='paused':
            _effect(path,receipt,'pause:'+str(goal['createdAt'])+':'+str(receipt.get('pause_epoch',0)),
                'thread/goal/set',dict(threadId=thread,status='paused',origin='automatic'))
        for turn in active:
            if turn not in receipt['stop_turns']:continue
            _effect(path,receipt,'interrupt:'+turn,'turn/interrupt',dict(threadId=thread,turnId=turn))
        final_goal,final_active=_native(receipt['grant'],thread)
        proven=(not final_goal or final_goal.get('status')=='paused') and not set(final_active).intersection(receipt['stop_turns'])
        receipt.update(state='stopped' if proven else 'stop_unverified',stop_proof=proven,
            pause_observed=not final_goal or final_goal.get('status')=='paused')
    except Exception as exc:receipt['control_error']=type(exc).__name__
    _save(path,receipt)
    return receipt


def _wind_down(path, receipt, reason, goal, active, upper):
    """Pause autonomous continuation, allow a bounded checkpoint, then stop work.

    Qualification loss cannot authorize more product work. The reserve permits
    only winddown, never extends the original deadline, and survives retries.
    """
    if 'winddown_deadline' not in receipt:
        _first_stop(path,receipt,reason)
        deadline=min(receipt['deadline'],upper+min(60,receipt['checkpoint_seconds']))
        receipt['winddown_deadline']=_allocation_latch(receipt,reason,deadline)
        receipt['stop_turns'] = list(active) if goal and goal.get('status') == 'active' else []
        receipt['winddown_reason'] = reason
        _save(path, receipt)
    owned = set(active).intersection(receipt['stop_turns'])
    if upper >= receipt['winddown_deadline'] or not owned:
        return _stop(path, receipt, reason, goal, active)
    receipt.update(state='winding_down', reason=reason, stop_latched=True)
    if not receipt.get('checkpoint'):
        receipt['checkpoint'] = dict(state='queued', message=
            'Campaign enforcement cannot qualify continuation. Stop product work and write a '
            'restart-safe checkpoint within the remaining grace period. The goal is paused; '
            'operator messages remain available. Do not reset or resume the allocation.')
        _save(path, receipt)
    if goal and goal.get('status') == 'active':
        if receipt.get('pause_observed'):
            receipt['pause_epoch'] = receipt.get('pause_epoch', 0) + 1
            receipt['pause_observed'] = False
            _save(path, receipt)
        _effect(path, receipt, 'pause:' + str(goal['createdAt']) + ':' + str(receipt.get('pause_epoch', 0)),
            'thread/goal/set', dict(threadId=receipt['thread_id'], status='paused', origin='automatic'))
        observed, _ = _native(receipt['grant'], receipt['thread_id'])
        receipt['pause_observed'] = not observed or observed.get('status') == 'paused'
        _save(path, receipt)
    if receipt['checkpoint']['state'] == 'queued':
        turn = next(turn for turn in active if turn in owned)
        delivered = _effect(path, receipt, 'checkpoint:' + turn, 'turn/steer',
            dict(threadId=receipt['thread_id'], expectedTurnId=turn,
                 input=[dict(type='text', text=receipt['checkpoint']['message'])]))
        receipt['checkpoint']['state'] = 'acknowledged' if delivered else 'uncertain'
    _save(path, receipt)
    return receipt


def poll(root):
    directory=_directory(root);results=[]
    for path in directory.glob('*.json'):
        if path.name=='controller.json':continue
        with _lock(directory,path.stem):
            _private(path);receipt=json.loads(path.read_text())
            try:
                from .permission_enforcement import controller_permission
                permission=controller_permission(root,receipt)
                receipt['enforcement_continuation_permission']=permission
                grant=_grant(receipt['policy_path'],receipt['thread_id'],receipt['allocation_id'],root)
                if grant!=receipt['grant']:
                    results.append(_stop(path,receipt,'host_policy_changed'));continue
                if boot_id_value()!=receipt['boot_id']:
                    results.append(_stop(path,receipt,'boot_identity_changed'));continue
                elapsed=time.clock_gettime(time.CLOCK_BOOTTIME)-receipt['started_boottime']
                if elapsed<0:
                    results.append(_stop(path,receipt,'elapsed_time_invalid'));continue
                upper=receipt['started_upper']+elapsed
                goal,active=_native(grant,receipt['thread_id'])
                receipt['native_goal_status']=goal.get('status') if goal else None
                if 'winddown_deadline' in receipt:
                    results.append(_wind_down(path,receipt,receipt['winddown_reason'],goal,active,upper));continue
                observation=_usage(receipt)
                used=observation.get('used_tokens')
                invalid=(observation.get('state')!='qualified' or type(used) is not int
                    or _accounting_decreased(receipt,observation))
                receipt['accounting']=observation
                if invalid:
                    results.append(_wind_down(path,receipt,'accounting_unknown',goal,active,upper));continue
                receipt['used_tokens']=used;receipt['observed_boottime']=time.clock_gettime(time.CLOCK_BOOTTIME)
                if used>=receipt['token_limit'] or upper>=receipt['deadline']:
                    results.append(_stop(path,receipt,'allocation_exhausted',goal,active));continue
                if receipt.get('stop_latched') or receipt.get('state') in ('stopped','stop_unverified'):
                    results.append(_stop(path,receipt,receipt.get('reason','continuation_held'),goal,active));continue
                if permission['permission'] not in ('allow','legacy'):
                    receipt.update(state='held',reason='permission_revoked',campaign_continuation='held')
                    _save(path,receipt);results.append(receipt);continue
                receipt.pop('campaign_continuation',None)
                checkpoint=(receipt['token_limit']-used<=receipt['token_limit']*receipt['checkpoint_token_percent']/100
                    or receipt['deadline']-upper<=receipt['checkpoint_seconds'])
                if checkpoint:
                    if not receipt.get('checkpoint'):
                        receipt['checkpoint']=dict(state='queued',message='Stop work and write a restart-safe checkpoint now. The original resource allowance remains in force.')
                        _save(path,receipt)
                    if active and receipt['checkpoint']['state']=='queued':
                        key='checkpoint:'+active[0]
                        delivered=_effect(path,receipt,key,'turn/steer',dict(threadId=receipt['thread_id'],expectedTurnId=active[0],
                            input=[dict(type='text',text=receipt['checkpoint']['message'])]))
                        receipt['checkpoint']['state']=('acknowledged' if delivered else
                            'blocked' if receipt.pop('permission_effect_blocked',False) else 'uncertain')
                    receipt.update(state='checkpoint_requested',reason='checkpoint_reserve')
                else:receipt.update(state='armed',reason=None)
                _save(path,receipt);results.append(receipt)
            except Exception as exc:
                receipt['observation_error']=exc.cause if isinstance(exc,NativeObservationUnavailable) else type(exc).__name__
                receipt['observation_method']=exc.method if isinstance(exc,NativeObservationUnavailable) else None
                receipt['observation_duration_seconds']=exc.duration if isinstance(exc,NativeObservationUnavailable) else None
                results.append(_stop(path,receipt,'observation_unavailable'))
    return results


def _acknowledge_enrollments(directory,controller,observations):
    for observed in observations:
        path=directory/(_name(observed['thread_id'])+'.json')
        with _lock(directory,path.stem):
            _private(path);receipt=json.loads(path.read_text())
            if any(receipt.get(key)!=observed.get(key) for key in
                    ('generation','enrollment_revision','token_limit','deadline','used_tokens')):continue
            if (observed.get('state') not in ('armed','checkpoint_requested') or
                    receipt.get('state') not in ('armed','checkpoint_requested') or receipt.get('stop_latched')
                    or (receipt.get('accounting') or {}).get('state')!='qualified'):
                continue
            receipt['poll_ack']=dict(enrollment_revision=receipt.get('enrollment_revision',1),
                receipt_generation=receipt['generation'],controller_generation=controller['generation'],
                observed_boottime=time.clock_gettime(time.CLOCK_BOOTTIME))
            _save(path,receipt)


def watch(root,interval=1):
    if type(interval) not in (int,float) or not .05<=interval<=5:raise ValueError('invalid controller interval')
    directory=_directory(root);generation=uuid4().hex
    descriptor=os.open(directory/'watch.lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    with os.fdopen(descriptor,'a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        running=True
        def finish(signum,frame):
            nonlocal running
            running=False
        prior={sig:signal.signal(sig,finish) for sig in (signal.SIGTERM,signal.SIGINT)}
        heartbeat=dict(generation=generation,pid=os.getpid(),identity=process_identity(os.getpid()),
            boot_id=boot_id_value(),interval=interval)
        try:
            while running:
                _save(directory/'controller.json',dict(heartbeat,active=True,observed_boottime=time.clock_gettime(time.CLOCK_BOOTTIME)))
                observations=poll(root)
                _acknowledge_enrollments(directory,heartbeat,observations)
                from .goal_maintenance import replacement_observed
                replacement_observed(directory,heartbeat)
                time.sleep(interval)
        finally:
            from .goal_maintenance import authorize_exit
            with _lock(directory,'maintenance'):
                maintained=not running and authorize_exit(directory,heartbeat)
                if not maintained:
                    for path in directory.glob('*.json'):
                        if path.name=='controller.json':continue
                        with _lock(directory,path.stem):
                            _private(path);receipt=json.loads(path.read_text());_stop(path,receipt,'controller_stopped')
            _save(directory/'controller.json',dict(heartbeat,active=False,observed_boottime=time.clock_gettime(time.CLOCK_BOOTTIME)))
            for sig,handler in prior.items():signal.signal(sig,handler)
