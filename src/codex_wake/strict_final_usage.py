"""Offline final usage proof for an exact, already-empty strict executor.

A sampled counter is never final by itself. Only a complete matching native turn
terminal after the last cumulative counter can release an actor's reservation.
"""
import json
from itertools import islice
import os
from pathlib import Path
import stat

from .objective_ledger import ObjectiveLedger
from .records import WakeError


def fence_final_usage(ledger, actor_ids, *, now):
    """Preserve sampled floors, but invalidate unsettled final usage on stop."""
    fenced=[]
    try:
        view=ledger.inspect(now=now)
        for actor_id in actor_ids:
            actor=view['actors'].get(actor_id)
            if actor and not (actor['settled'] and actor['known']):
                view=ledger.record(actor_id,None,settled=False,now=now)
                fenced.append(actor_id)
        return dict(state='accounting_unknown' if fenced or not view['accounting_known'] else 'settled',fenced=fenced,
            accounting_known=view['accounting_known'])
    except BlockingIOError:
        return dict(state='accounting_unknown',reason='ledger_lock_busy',fenced=fenced)
    except (OSError,ValueError,KeyError,TypeError):
        return dict(state='accounting_unknown',reason='ledger_unavailable',fenced=fenced)


def _read(path, remaining, *, private=False):
    from .strict_runtime import _private
    if private:_private(path)
    descriptor=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    with os.fdopen(descriptor,'rb') as stream:
        info=os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid!=os.geteuid():
            raise ValueError('accounting artifact must be an owned regular file')
        data=stream.read(remaining+1)
    if len(data)>remaining:raise ValueError('accounting_capacity_exceeded')
    return data


def _terminal_usage(data):
    if not data.endswith(b'\n'):raise ValueError('incomplete_native_log')
    rows=[json.loads(line) for line in data.decode('utf-8').splitlines()]
    if any(not isinstance(row,dict) or not isinstance(row.get('payload',{}),dict) for row in rows):
        raise ValueError('accounting_invalid')
    identities={row.get('payload',{}).get('id') for row in rows if row.get('type')=='session_meta'}
    if len(identities)!=1 or not next(iter(identities)):raise ValueError('rollout_identity_unknown')
    active=None; last_usage=None; last_usage_turn=None; terminal=False
    for row in rows:
        payload=row.get('payload',{})
        if row.get('type')!='event_msg':continue
        kind=payload.get('type')
        if kind=='task_started':
            if active is not None:raise ValueError('overlapping_native_turn')
            active=payload.get('turn_id')
            if not active:raise ValueError('native_turn_identity_unknown')
            terminal=False
        elif kind=='token_count':
            info=payload.get('info')
            if info is None or (isinstance(info,dict) and not info.get('total_token_usage')):continue
            if not isinstance(info,dict):raise ValueError('accounting_invalid')
            if not isinstance(info.get('total_token_usage'),dict):raise ValueError('accounting_invalid')
            usage=info['total_token_usage'].get('total_tokens')
            if type(usage) is not int or usage<0 or (last_usage is not None and usage<last_usage):
                raise ValueError('accounting_invalid')
            last_usage=usage;last_usage_turn=active;terminal=False
        elif kind in {'task_complete','turn_aborted'}:
            if active is None or payload.get('turn_id')!=active:raise ValueError('native_terminal_identity_unknown')
            terminal=last_usage is not None and last_usage_turn==active
            active=None
    return next(iter(identities)),last_usage,terminal and active is None


def reconcile_final_usage(root, binding):
    """Return explicit unknown until all prior actors have final native proof.

    Caller holds the execution binding lock. This function independently checks
    the saved host invocation is empty before touching the offline ledger.
    """
    from .strict_runtime import location,_private
    from .strict_executor import MAX_ACCOUNTING_BYTES
    from .host_execution import SystemdExecution
    from .lifecycle_budget import objective_identity,trusted_upper
    objective=binding['objective_id'];directory=location(root,objective)
    result=dict(state='accounting_unknown',settled=[],unknown=[],objective_id=objective)
    ledger=None
    try:
        identity=binding.get('identity')
        if not identity:raise ValueError('executor_identity_unavailable')
        host=SystemdExecution().inspect(identity)
        if host['populated'] or host['members']:raise ValueError('executor_not_empty')
        _private(directory,True)
        generation=binding['generation']
        if not isinstance(generation,str) or not generation.isalnum():raise ValueError('guard_generation_invalid')
        config_data=_read(directory/('guard-'+generation+'.json'),MAX_ACCOUNTING_BYTES,private=True)
        config=json.loads(config_data)
        home=directory/'home';endpoint='unix://'+str(directory/'app-server.sock')
        if (config['generation']!=generation or config['objective_id']!=objective
                or config['configuration']['revision']!=binding['configuration_revision']
                or Path(config['wake_root'])!=Path(root).resolve()
                or Path(config['codex_home'])!=home or config['endpoint']!=endpoint):
            raise ValueError('guard_configuration_changed')
        _private(home,True)
        ledger=ObjectiveLedger(root,objective);now=trusted_upper();view=ledger.inspect(now=now)
        actors=view['actors']
        fence_final_usage(ledger,list(actors),now=now)
        bindings={};remaining=MAX_ACCOUNTING_BYTES-len(config_data)
        receipts=list(islice((Path(root)/'lifecycle').glob('*.json'),513))
        if len(receipts)>512:raise ValueError('accounting_capacity_exceeded')
        for path in receipts:
            if path.name=='supervision.json' or path.name.startswith('owner-'):continue
            data=_read(path,remaining,private=True);remaining-=len(data)
            receipt=json.loads(data)
            if not isinstance(receipt,dict) or not isinstance(receipt.get('intent',{}),dict):raise ValueError('receipt_invalid')
            intent=receipt.get('intent',{});operation=intent.get('operation')
            if operation not in {'spawn','handoff'}:continue
            launch=intent.get('launch',{});cfg=receipt.get('configuration') if operation=='handoff' else intent.get('configuration')
            historical=config.get('historical_actors',{})
            historical_receipt=receipt.get('budget_actor') in historical
            approved={entry['configuration']['revision'] for entry in view['authorization_history']}
            if not isinstance(launch,dict) or not isinstance(cfg,dict):raise ValueError('receipt_invalid')
            if (not cfg or cfg.get('revision') not in approved or (cfg.get('revision')!=config['configuration']['revision'] and not historical_receipt)
                    or objective_identity(intent.get('continuation',{}))!=objective
                    or launch.get('app_server')!=endpoint or Path(launch.get('codex_home',''))!=home):continue
            actor=receipt.get('budget_actor');thread=receipt.get('successor_thread_id') if operation=='handoff' else receipt.get('thread_id')
            if actor and thread:
                if actor not in actors:raise ValueError('actor_binding_unknown')
                if thread in bindings and bindings[thread]!=actor:raise ValueError('actor_binding_changed')
                bindings[thread]=actor
            if operation=='handoff' and receipt.get('source_goal'):
                source=receipt['source_goal'];key='goal:'+source['threadId']+':'+str(source['createdAt'])
                source_actor=view['goal_aliases'].get(key,{}).get('actor_id',key)
                if source_actor in actors:
                    if source['threadId'] in bindings and bindings[source['threadId']]!=source_actor:raise ValueError('actor_binding_changed')
                    bindings[source['threadId']]=source_actor
        sessions=home/'sessions'
        if sessions.exists():
            info=sessions.lstat()
            if not stat.S_ISDIR(info.st_mode) or info.st_uid!=os.geteuid():
                raise ValueError('native sessions must be an owned directory without symlinks')
        paths=list(islice(sessions.rglob('*.jsonl'),513)) if sessions.exists() else []
        if len(paths)+len(receipts)>512:raise ValueError('accounting_capacity_exceeded')
        observations={}
        for path in paths:
            path.resolve().relative_to(sessions.resolve())
            data=_read(path,remaining);remaining-=len(data)
            thread,usage,terminal=_terminal_usage(data)
            if thread not in bindings:raise ValueError('unattributed_native_work')
            actor=bindings[thread]
            if actor in observations:raise ValueError('rollout_binding_ambiguous')
            observations[actor]=(usage,terminal)
        for actor_id,actor in actors.items():
            usage,terminal=observations.get(actor_id,(None,False))
            if actor['settled'] and actor['known']:
                if usage is not None and usage!=actor['used']:
                    ledger.record(actor_id,None,settled=False,now=now)
                    raise ValueError('settled_actor_usage_changed')
                if usage is None and config.get('historical_actors',{}).get(actor_id)==actor['used']:
                    continue
                if not terminal:result['unknown'].append(actor_id)
                continue
            if terminal and usage is not None and usage>=actor['used']:
                ledger.record(actor_id,usage,settled=True,now=now)
                result['settled'].append(actor_id)
            else:
                if usage is not None:
                    ledger.record_sampled_floor(actor_id,usage,now=now)
                result['unknown'].append(actor_id)
        after=ledger.inspect(now=now)
        result.update(state='settled' if not result['unknown'] and all(a['known'] and a['settled'] for a in after['actors'].values()) else 'accounting_unknown',
            objective_budget=after)
    except (OSError,ValueError,KeyError,TypeError,RuntimeError,WakeError) as exc:
        result['reason']=str(exc)
        if ledger is not None:
            # A partial proof never turns an unresolved actor into known usage.
            try:result['objective_budget']=ledger.inspect(now=trusted_upper())
            except (OSError,ValueError,KeyError,TypeError):pass
    return result
