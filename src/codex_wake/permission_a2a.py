"""Common session action policy over existing authenticated mailbox actors.

The bus pins its operator-selected policy root. Message/model arguments cannot
choose the root, claim roles, or assert trusted task scope.
"""
from __future__ import annotations

import json
from pathlib import Path

from .a2a_identity import Actor, BusError
from .session_permissions import PermissionDenied, PermissionStore, Principal, check_operation
from .records import WakeError

BINDING_KEY = 'session_permissions'


def binding(bus, database):
    row=database.execute('SELECT value FROM meta WHERE key=?',(BINDING_KEY,)).fetchone()
    if row is None:
        return None
    try:
        value=json.loads(row[0])
        if (type(value) is not dict or set(value)!={'version','root','tasks'}
                or type(value['version']) is not int or value['version']!=1
                or type(value['root']) is not str or type(value['tasks']) is not dict):
            raise ValueError()
        root=Path(value['root'])
        if not root.is_absolute() or root!=root.resolve():raise ValueError()
        store=PermissionStore(root)
        if not store.active():
            raise BusError('permission_policy_unavailable','the bus-pinned common permission policy is unavailable')
        # An adopted bus never silently returns to legacy behavior after policy loss.
        store._read()
        return value
    except BusError:
        raise
    except (ValueError,OSError,KeyError,TypeError,WakeError) as exc:
        raise BusError('permission_policy_unavailable','the bus-pinned permission policy is invalid') from exc


def bind(bus, root, operator_capability):
    from .a2a_bus import private_path
    root=Path(root).absolute()
    if root!=root.resolve():raise BusError('permission_binding_invalid','policy root must be canonical')
    private_path(root,directory=True)
    store=PermissionStore(root)
    if not store.active():raise BusError('permission_policy_unavailable','configure the common policy before binding a bus')
    store._read()
    root=store.root
    with bus.connection() as database:
        database.execute('BEGIN IMMEDIATE')
        bus.operator(database,Path(operator_capability))
        current=binding(bus,database)
        if current and current['root']!=str(root):
            raise BusError('permission_binding_conflict','policy root is already pinned; migrate existing authority explicitly')
        value=current or dict(version=1,root=str(root),tasks={})
        database.execute('INSERT INTO meta VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',
                         (BINDING_KEY,json.dumps(value,sort_keys=True)))
        receipt=bus.event(database,'operator','bind_session_permissions',dict(policy_root=str(root)))
        database.execute('COMMIT')
        return dict(receipt_id=receipt,policy_root=str(root),bound=True)


def bind_tasks(bus, actor_id, task_ids, operator_capability):
    from .task_briefs import TaskBriefStore
    if (type(task_ids) is not list or len(task_ids)>64 or len(set(task_ids))!=len(task_ids)
            or any(type(t) is not str or not t for t in task_ids)):
        raise BusError('invalid_argument','task references must be a bounded unique list')
    with bus.connection() as database:
        database.execute('BEGIN IMMEDIATE')
        bus.operator(database,Path(operator_capability))
        configured=binding(bus,database)
        if configured is None:raise BusError('permission_policy_unavailable','bind the common policy first')
        actor=database.execute('SELECT * FROM actors WHERE actor_id=? AND revoked=0',(actor_id,)).fetchone()
        if not actor:raise BusError('authorization_denied','exact active actor is required')
        references=[]
        store=TaskBriefStore(PermissionStore(configured['root']).root)
        for task in task_ids:
            brief=store.inspect(task)
            revision=brief['approved_revision']
            if revision is None:
                raise BusError('permission_task_unapproved','A2A task binding requires an approved brief')
            selected=brief['revisions'][revision-1]
            if not Path(selected['content']['workspace']).is_relative_to(Path(actor['root'])):
                raise BusError('permission_task_scope_denied','task workspace is outside actor enrollment')
            references.append(dict(task_id=task,revision=revision,digest=selected['digest']))
        configured['tasks'][actor_id]=dict(generation=actor['generation'],references=references)
        database.execute('UPDATE meta SET value=? WHERE key=?',(json.dumps(configured,sort_keys=True),BINDING_KEY))
        receipt=bus.event(database,'operator','bind_permission_tasks',dict(actor_id=actor_id,task_ids=task_ids))
        database.execute('COMMIT')
        return dict(receipt_id=receipt,actor_id=actor_id,task_ids=task_ids)


def _principal(configured, actor):
    from .task_briefs import TaskBriefStore
    grant=configured['tasks'].get(actor.actor_id)
    tasks=[]
    if grant is not None:
        if (type(grant) is not dict or set(grant)!={'generation','references'}
                or type(grant['generation']) is not int or type(grant['references']) is not list):
            raise BusError('permission_task_scope_unverified','stored task binding is invalid')
        if grant['generation']!=actor.generation:
            return Principal(actor.thread_id)
        store=TaskBriefStore(PermissionStore(configured['root']).root)
        for ref in grant['references']:
            if type(ref) is not dict or set(ref)!={'task_id','revision','digest'}:
                raise BusError('permission_task_scope_unverified','stored task reference is invalid')
            brief=store.inspect(ref['task_id'])
            revision=ref['revision']
            if (type(revision) is not int or not 1<=revision<=len(brief['revisions'])
                    or str(revision) not in brief['approvals']
                    or brief['revisions'][revision-1]['digest']!=ref['digest']
                    or not Path(brief['revisions'][revision-1]['content']['workspace']).is_relative_to(Path(actor.root))):
                raise BusError('permission_task_scope_unverified','approved task reference changed')
            tasks.append(ref['task_id'])
    return Principal(actor.thread_id,tasks=tuple(tasks))


def check_pair(bus,database,sender,recipient,*,task_id=None,action='a2a.send'):
    """Both actor objects must already be authenticated/revalidated by the bus."""
    configured=binding(bus,database)
    if configured is None:
        if task_id is not None:
            raise BusError('permission_task_scope_unverified','tasked messages require an adopted common policy')
        return None
    if not isinstance(sender,Actor) or not isinstance(recipient,Actor):
        raise BusError('permission_identity_unverified','exact enrolled actors are required')
    try:
        # Task references originate in operator bindings, not message parameters.
        left,right=_principal(configured,sender),_principal(configured,recipient)
        if task_id is not None and (task_id not in left.tasks or task_id not in right.tasks):
            raise BusError('permission_task_scope_unverified','both actors must be bound to the exact approved task')
        first=check_operation(configured['root'],action,left,target=recipient.thread_id,
                              relationship='peer',task_id=task_id)
        second=check_operation(configured['root'],'a2a.receive',right,target=sender.thread_id,
                               relationship='peer',task_id=task_id)
        return dict(sender_revision=first['revision'],recipient_revision=second['revision'])
    except PermissionDenied as exc:
        error=BusError(exc.code,str(exc));error.details=dict(permission=exc.decision)
        raise error from exc
    except (OSError,ValueError,KeyError,TypeError,WakeError) as exc:
        raise BusError('permission_policy_unavailable','common permission or task authority is unavailable') from exc


def actors_for_message(bus,database,row):
    envelope=json.loads(row['envelope'])
    actors=[]
    for role in ('sender','recipient'):
        identity=envelope[role]
        saved=database.execute('SELECT * FROM actors WHERE namespace=? AND thread_id=?',
            (identity['namespace'],identity['thread_id'])).fetchone()
        if not saved or saved['revoked'] or saved['root']!=identity['root']:
            raise BusError('authorization_denied','original message actor is no longer enrolled')
        actor=Actor(bus.bus_id,saved['namespace'],saved['thread_id'],saved['root'],saved['generation'],saved['actor_id'])
        bus.validate_actor(database,actor,permission='send' if role=='sender' else 'receive')
        actors.append(actor)
    return actors,envelope.get('task_id')


def check_message(bus,database,row,*,action='a2a.send'):
    if binding(bus,database) is None:return None
    (sender,recipient),task=actors_for_message(bus,database,row)
    check_pair(bus,database,sender,recipient,task_id=task)
    if action=='a2a.claim':
        configured=binding(bus,database)
        try:
            check_operation(configured['root'],action,_principal(configured,recipient),
                            target=sender.thread_id,relationship='peer',task_id=task)
        except PermissionDenied as exc:
            raise BusError(exc.code,str(exc)) from exc
