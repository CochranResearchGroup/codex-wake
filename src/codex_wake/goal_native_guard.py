"""Native loss leases projected into the existing supervision receipt.

The native app server owns expiry and exact-turn interruption. This module never
creates a goal or turn, and a lease acknowledgement is not stop proof.
"""
import math
import time

from . import goal_supervision as supervision


def _identity(receipt):
    return receipt['thread_id']+':'+receipt['generation']+':'+str(receipt['enrollment_revision'])


def matches(receipt):
    return receipt.get('native_guard',{}).get('lease_id')==_identity(receipt)


def qualified(receipt):
    guard=receipt.get('native_guard',{})
    age=time.clock_gettime(time.CLOCK_BOOTTIME)-guard.get('ack_boottime',-1e30)
    return (guard.get('status')=='armed' and guard.get('lease_id')==_identity(receipt)
        and 0<=age<guard.get('ttl_ms',0)/1000)


def arm(path,receipt,*,force=False,stop=False):
    """Caller holds the existing member lock; renew only qualified live work."""
    if not receipt.get('requires_native_guard'):return True
    identifier=_identity(receipt)
    prior=receipt.get('native_guard',{})
    if prior.get('lease_id') and prior['lease_id']!=identifier:
        history=receipt.setdefault('native_guard_history',[])
        if not history or history[-1]!=prior:history.append(dict(prior))
    if (not force and prior.get('lease_id')==identifier
            and prior.get('status') in ('unsupported','expired','lost','released')):
        return False
    controller=supervision._heartbeat(path.parent)
    generation=controller.get('generation')
    if not generation:
        receipt['native_guard']=dict(status='unavailable',reason='watcher_identity_unavailable',lease_id=identifier)
        supervision._save(path,receipt);return False
    from .goal_time import upper
    remaining=receipt['deadline']-upper(receipt)
    if receipt.get('shared_limits'):
        remaining=min(remaining,receipt['shared_limits']['deadline']-upper(receipt))
    if remaining<=0 and not stop:return False
    members=[]
    intent=dict(prior)
    try:
        identities=receipt.get('qualified_task_members')
        if not identities or receipt['thread_id'] not in identities:
            raise ValueError('qualified task membership unavailable')
        for thread in identities:
            goal,active=supervision._native(receipt['grant'],thread)
            # A paused goal's later operator reply is outside campaign work.
            turns=list(active) if not goal or goal.get('status')=='active' else []
            if goal is None and not force and prior.get('lease_id')==identifier:
                captured=next((item['turnIds'] for item in prior.get('member_turns',[]) if item['threadId']==thread),None)
                if captured is not None:turns=[turn for turn in turns if turn in captured]
            members.append(dict(threadId=thread,turnIds=turns,
                goalCreatedAt=goal.get('createdAt') if goal else None))
        if not any(item['goalCreatedAt'] is not None or item['turnIds'] for item in members):
            receipt['native_guard']=dict(status='unsupported',lease_id=identifier,
                reason='idle_session_future_task_isolation_unsupported')
            supervision._save(path,receipt);return False
        ttl=1 if stop else max(1,min(10000,math.floor(remaining*1000)))
        params=dict(threadId=receipt['thread_id'],leaseId=identifier,
            controllerGeneration=generation,enrollmentRevision=receipt['enrollment_revision'],
            ttlMs=ttl,memberTurns=members)
        intent=dict(prior,status='arming',lease_id=identifier,controller_generation=generation,
            enrollment_revision=receipt['enrollment_revision'],ttl_ms=ttl,member_turns=members)
        receipt['native_guard']=intent
        supervision._save(path,receipt)
        sent=time.clock_gettime(time.CLOCK_BOOTTIME)
        acknowledgement=supervision._request(receipt['grant'],'thread/governorLease/set',params)
        if acknowledgement.get('leaseId')!=identifier:
            raise ValueError('native governor lease acknowledgement changed identity')
        if acknowledgement.get('expired'):
            receipt['native_guard']=dict(prior,status='expired',lease_id=identifier,
                reason='native_guard_expired',stop_verified=acknowledgement.get('stopVerified') is True)
            supervision._save(path,receipt);return False
        if acknowledgement.get('armed') is not True:
            raise ValueError('native governor lease was not armed')
        receipt['native_guard']=dict(status='armed',lease_id=identifier,
            controller_generation=generation,enrollment_revision=receipt['enrollment_revision'],
            ttl_ms=ttl,member_turns=members,ack_boottime=sent)
        supervision._save(path,receipt)
        return True
    except Exception as error:
        from .native_protocol import NativeCapabilityUnavailable
        unsupported=isinstance(error,(NativeCapabilityUnavailable,NotImplementedError))
        receipt['native_guard']=dict(intent,status='unsupported' if unsupported else 'lost',
            lease_id=identifier,reason='native_guard_capability_unavailable' if unsupported else 'native_guard_connection_lost',
            error=type(error).__name__)
        supervision._save(path,receipt)
        return False


def release(path,receipt):
    guard=receipt.get('native_guard',{})
    if not guard.get('lease_id'):return
    params=dict(threadId=receipt['thread_id'],leaseId=guard['lease_id'],
        controllerGeneration=guard.get('controller_generation'),
        enrollmentRevision=guard.get('enrollment_revision',receipt.get('enrollment_revision')),release=True)
    try:
        result=supervision._request(receipt['grant'],'thread/governorLease/set',params)
        if result.get('leaseId')!=guard['lease_id'] or result.get('armed') is not False:
            raise ValueError('native lease release unverified')
        receipt['native_guard']=dict(guard,status='released',release_verified=True)
    except Exception as error:
        receipt['native_guard']=dict(guard,release_verified=False,release_error=type(error).__name__)
    supervision._save(path,receipt)


def reconcile_expiry(path,receipt):
    """Read native expiry without adopting a later operator turn as task work."""
    guard=receipt.get('native_guard',{})
    params=dict(threadId=receipt['thread_id'],leaseId=guard['lease_id'],
        controllerGeneration=guard.get('controller_generation'),
        enrollmentRevision=guard.get('enrollment_revision',receipt.get('enrollment_revision')),query=True)
    try:
        result=supervision._request(receipt['grant'],'thread/governorLease/set',params)
        expired=result.get('leaseId')==guard['lease_id'] and result.get('expired') is True
        receipt['native_guard']=dict(guard,status='expired' if expired else 'lost',
            reason='native_guard_expired' if expired else 'native_guard_lease_unqualified',
            stop_verified=expired and result.get('stopVerified') is True,
            member_outcomes=result.get('memberOutcomes',[]))
    except Exception as error:
        receipt['native_guard']=dict(guard,status='lost',reason='native_guard_connection_lost',error=type(error).__name__)
    exhausted=receipt.get('stop_latched') and receipt.get('first_stop',{}).get('reason') in ('allocation_exhausted','task_exhausted','continuation_held')
    if receipt.get('stop_latched') and receipt['native_guard'].get('stop_verified'):
        receipt.update(state='stopped',stop_proof=True,pause_observed=True)
    elif not exhausted:receipt.update(state='held',reason=receipt['native_guard']['reason'])
    supervision._save(path,receipt)


def expire(path,receipt,reason='controller_stopped'):
    """Graceful watcher exit shortens its last native scope, never recaptures."""
    guard=receipt.get('native_guard',{})
    if guard.get('status')=='released':return
    if guard.get('status')=='unsupported':
        receipt.update(state='held',reason='native_guard_capability_unavailable')
        supervision._save(path,receipt);return
    if not guard.get('controller_generation') or not guard.get('member_turns'):
        receipt.update(state='held',reason='native_guard_unqualified')
        supervision._save(path,receipt);return
    try:
        supervision._request(receipt['grant'],'thread/governorLease/set',dict(
            threadId=receipt['thread_id'],leaseId=guard['lease_id'],
            controllerGeneration=guard['controller_generation'],
            enrollmentRevision=guard['enrollment_revision'],ttlMs=1,memberTurns=guard['member_turns']))
        receipt['native_guard']=dict(guard,status='lost',reason=reason,ttl_ms=1)
    except Exception as error:
        receipt['native_guard']=dict(guard,status='lost',reason=reason,error=type(error).__name__)
    receipt.update(state='stop_unverified' if receipt.get('stop_latched') else 'held',reason=reason)
    supervision._save(path,receipt)
