"""Operator-owned governor switch, independent of watcher health and budgets."""

from contextlib import ExitStack
import hashlib
import json
from pathlib import Path
import time

from . import goal_supervision as supervision
from .permission_enforcement import authorize
from .session_permissions import PermissionDenied, Principal


def sync(receipt, *, locked_allocation=None):
    """Allocation state is authoritative, including after a partial member write."""
    # A campaign caller already holds this exact allocation lock through effect
    # admission; use its authoritative snapshot instead of locking it again.
    source = locked_allocation if locked_allocation is not None else receipt
    if locked_allocation is None and receipt.get("allocation_path"):
        path = Path(receipt["allocation_path"])
        with supervision._lock(path.parent, path.stem):
            supervision._private(path)
            source = json.loads(path.read_text())
    shared_enabled=source.get('governor_enabled',True)
    task=source.get('members',{}).get(receipt.get('task_owner_thread_id',receipt['thread_id']),{}).get('task_window')
    if task:
        receipt['task_window']=task
        for key in ('token_limit','deadline','time_limit_seconds','time_origin','lifetime_tokens_before_window','generation'):
            if key in task:receipt[key]=task[key]
        receipt['budget_revision']=task.get('revision',1)
        if shared_enabled:source=task
    for key in ("governor_enabled", "governor_revision", "governor_control", "governor_mode", "request_accounting"):
        if key in source:
            receipt[key] = source[key]
        elif task and key=='governor_enabled':receipt[key]=True
        elif task and key=='governor_mode':receipt[key]='enforced'
    if task:
        receipt['task_governor_enabled']=task.get('governor_enabled',True)
        receipt['governor_enabled']=shared_enabled
    return receipt.get("governor_enabled", True) is False


def native_operator(root, receipt, native_context, enabled):
    """Only a whole native user message in the exact live caller turn authorizes.

    Claimed roles, tool outputs, quoted instructions and historical user messages
    never confer operator authority. The model mechanically consumes this action.
    """
    caller = supervision.verified_native_caller(native_context, receipt["thread_id"])
    native = supervision._request(
        receipt["grant"],
        "thread/read",
        dict(threadId=receipt["thread_id"], includeTurns=True),
    )["thread"]
    if native.get("id") != receipt["thread_id"]:
        raise PermissionDenied("governor_operator_required")
    turns = [
        turn for turn in native.get("turns", []) if turn.get("id") == caller["turn_id"]
    ]
    command = "Reactivate governor" if enabled else "Deactivate governor"
    if len(turns) != 1 or turns[0].get("status") != "inProgress":
        raise PermissionDenied("governor_operator_required")
    users = [
        item for item in turns[0].get("items", []) if item.get("type") == "userMessage"
    ]
    content = users[0].get("content") if len(users) == 1 else None
    if (
        not isinstance(content, list)
        or len(content) != 1
        or not isinstance(content[0], dict)
        or content[0].get("type") != "text"
        or content[0].get("text") != command
    ):
        raise PermissionDenied("governor_operator_required")
    # A stale caller packet cannot consume an old directive after another turn.
    _, active = supervision._native(receipt["grant"], receipt["thread_id"])
    if active != [caller["turn_id"]]:
        raise PermissionDenied("governor_operator_required")
    return dict(
        source="native_user_message",
        turn_id=caller["turn_id"],
        call_id=caller["call_id"],
    )


def change(
    root, thread, *, enabled, principal=None, native_context=None, allocation_id=None, mode=None, task_only=False
):
    """Commit one scope switch under the same locks as every controller effect.

    Maintenance fences enrollment/membership. All member locks precede the shared
    ledger lock (the existing poll order), so pending polls either precede the
    durable switch or observe it before any effect. No native work is resumed.
    """
    if mode not in (None, 'advisory') or mode == 'advisory' and enabled:
        raise ValueError('invalid governor control mode')
    selected_mode = 'enforced' if enabled else mode or 'disabled'
    if type(enabled) is not bool:
        raise ValueError("boolean governor state required")
    directory = supervision._directory(root)
    path = directory / (supervision._name(thread) + ".json")
    notices = []
    with (
        supervision._lock(directory, "recovery"),
        supervision._lock(directory, "maintenance"),
    ):
        supervision._private(path)
        first = json.loads(path.read_text())
        allocation_path = (
            Path(first["allocation_path"]) if first.get("allocation_path") else None
        )
        if allocation_id is not None and allocation_id != first["allocation_id"]:
            raise ValueError("governor selected scope does not match session")
        allocation = None
        if allocation_path:
            expected = supervision._allocation_path(directory, first["allocation_id"])
            if allocation_path != expected:
                raise ValueError("governor allocation scope path changed")
            supervision._private(allocation_path)
            allocation = json.loads(allocation_path.read_text())
            if (
                allocation["allocation_id"] != first["allocation_id"]
                or thread not in allocation["members"]
            ):
                raise ValueError("governor allocation membership changed")
        scope_members=sorted((allocation or {}).get("members", {thread: {}}))
        task_owner=first.get('task_owner_thread_id',thread)
        if task_only and allocation and not independent_constraint(directory,first):task_only=False
        members=([member for member in scope_members if member==task_owner or allocation['members'][member].get('task_owner_thread_id')==task_owner]
            if task_only and allocation and first.get('task_window') else scope_members)
        if task_only and not first.get('task_window'):raise ValueError('qualified task fence required')
        with ExitStack() as locks:
            for member in members:
                locks.enter_context(
                    supervision._lock(directory, supervision._name(member))
                )
            if allocation_path:
                locks.enter_context(
                    supervision._lock(allocation_path.parent, allocation_path.stem)
                )
                allocation = json.loads(allocation_path.read_text())
                if sorted(allocation["members"]) != scope_members:
                    raise ValueError(
                        "governor scope changed; inspect current allocation"
                    )
            first = json.loads(path.read_text())
            if first["thread_id"] != thread:
                raise ValueError("governor target identity changed")
            if native_context is not None:
                control = native_operator(root, first, native_context, enabled)
                principal = Principal(thread, "operator")
            else:
                if (
                    not isinstance(principal, Principal)
                    or principal.role != "operator"
                    or principal.subject != thread
                ):
                    raise PermissionDenied("governor_operator_required")
                control = dict(source="authenticated_operator")
            permission = authorize(root, "enforcement.disable", principal)
            for member in members:
                authorize(root, "enforcement.disable", Principal(member, "operator"))
            authority = (allocation['members'][task_owner]['task_window'] if task_only else
                allocation if allocation is not None else first)
            revision = authority.get("governor_revision", 0)
            changed = (authority.get("governor_enabled", True) != enabled or
                authority.get("governor_mode", "enforced" if authority.get("governor_enabled", True) else "disabled") != selected_mode)
            if changed:
                revision += 1
                control.update(
                    at=time.time(),
                    revision=revision,
                    enabled=enabled,
                    scope=first["allocation_id"],
                    members=members,
                )
            else:
                control = authority.get("governor_control", control)
            state = dict(
                governor_enabled=enabled, governor_mode=selected_mode,
                governor_revision=revision,
                governor_control=control,
            )
            # Commit scope authority first. A crash leaves disabled member copies
            # repairable from this record, never an active orphaned member.
            if allocation_path:
                if task_only:allocation['members'][task_owner]['task_window'].update(state)
                else:allocation.update(state)
                supervision._save(allocation_path, allocation)
            for member in members:
                member_path = directory / (supervision._name(member) + ".json")
                if not member_path.exists():
                    continue
                supervision._private(member_path)
                receipt = json.loads(member_path.read_text())
                if receipt["allocation_id"] != first["allocation_id"]:
                    continue  # historical finalized member, now in another scope
                receipt.update(state)
                if not enabled:
                    try:
                        control_goal,control_active=supervision._native(receipt['grant'],member)
                        receipt['control_goal_created_at']=control_goal.get('createdAt') if control_goal else None
                        receipt['control_active_turn_ids']=list(control_active) if not control_goal or control_goal.get('status')!='paused' else []
                    except Exception:receipt['control_scope_unavailable']=True
                if receipt.get('requires_native_guard'):
                    if changed and (enabled or task_only):
                        receipt['enrollment_revision']=receipt.get('enrollment_revision',1)+1
                        receipt.pop('poll_ack',None)
                    elif not enabled and not task_only:
                        from .goal_native_guard import release
                        release(member_path,receipt)
                if task_only:receipt['task_window']=allocation['members'][task_owner]['task_window']
                if not enabled and task_only and receipt.get('first_stop',{}).get('reason')=='task_exhausted' and not allocation.get('stop_latched'):
                    receipt.setdefault('suspended_task_stops',[]).append(receipt['first_stop'])
                    receipt.update(stop_latched=False,state='armed',reason=None)
                kind = "reactivation" if enabled else "deactivation"
                # Record/reconcile the same revision notice on an idempotent retry.
                if revision:
                    supervision._record_supervision_notice(member_path, receipt, kind)
                    event = receipt.get("notice_ids", {}).get(kind)
                    if event:
                        notices.append(event)
                supervision._save(member_path, receipt)
                if member == thread:
                    first = receipt
    # Delivery is separate from effective state and needs no running watcher.
    from .goal_notices import present_notice, governor_status

    presentation = []
    for event in notices:
        try:
            notice = present_notice(root, event)
            presentation.append(dict(event_id=event, state=notice["delivery"]["state"]))
        except Exception as error:
            presentation.append(
                dict(event_id=event, state="unavailable", error=type(error).__name__)
            )
    return dict(
        supervision._public(first),
        governor=governor_status(root, first),
        changed=changed,
        permission=permission,
        notices=presentation,
        members=members,
        resumed=False,
        renewed_resources=False,
        controller=supervision._heartbeat(directory),
        message=(
            "Governor inactive in this scope. Drop stale governor checkpoint/stop instructions; "
            "independent platform controls remain. Accounting and checkpoints are preserved; "
            "no work is resumed and no resources renewed."
            if not enabled
            else f"Governor reactivated in this scope in {first.get('request_accounting',{}).get('mode','sampled_stop')} mode; no work resumed or resources renewed."
        ),
    )


def snapshot(root, thread_id):
    """Read-only host snapshot for a first dispatch intent, never a work gate.

    Callers retain this original snapshot on retry; fresh scope authority wins at
    effect boundaries. Unknown availability neither enables nor disables work.
    """
    try:
        name = supervision._name(thread_id)
        root = Path(root).absolute()
        if root != root.resolve():
            raise ValueError("noncanonical root")
        supervision._private(root, True)
        directory = root / "goal-supervision"
        supervision._private(directory, True)
        path = directory / (name + ".json")
        supervision._private(path)
        receipt = json.loads(path.read_text())
        if receipt["thread_id"] != thread_id:
            raise ValueError("session identity changed")
        authority, source = receipt, "session_receipt"
        if receipt.get("allocation_path"):
            expected = (
                directory
                / "allocations"
                / (
                    hashlib.sha256(receipt["allocation_id"].encode()).hexdigest()
                    + ".json"
                )
            )
            if (
                Path(receipt["allocation_path"]) != expected
                or expected.resolve() != expected
            ):
                raise ValueError("allocation scope path changed")
            supervision._private(expected)
            authority = json.loads(expected.read_text())
            if (
                authority["allocation_id"] != receipt["allocation_id"]
                or thread_id not in authority["members"]
            ):
                raise ValueError("allocation membership changed")
            source = "allocation_ledger"
            if authority.get('governor_enabled',True):
                task=authority['members'].get(receipt.get('task_owner_thread_id',thread_id),{}).get('task_window')
                if task:
                    authority=dict(task,governor_enabled=True,task_governor_enabled=task.get('governor_enabled',True))
                    source='allocation_task_member'
        enabled = authority.get("governor_enabled", True)
        if type(enabled) is not bool:
            raise ValueError("invalid governor control state")
        return dict(
            state="available",
            enabled=enabled,
            mode=authority.get("request_accounting",{}).get("mode","sampled_stop") if enabled else "inactive",
            revision=authority.get("governor_revision", 0),
            scope=receipt["allocation_id"],
            thread_id=thread_id,
            source=source,
            observed_at=time.time(),
        )
    except (OSError, ValueError, KeyError, TypeError) as error:
        return dict(
            state="unavailable",
            enabled=None,
            mode="unknown",
            thread_id=thread_id,
            reason=type(error).__name__,
            observed_at=time.time(),
        )


def independent_constraint(directory,receipt):
    """Admission envelopes are not funded independent spending allocations."""
    grant=receipt['grant']
    if grant.get('requires_enforcement') or receipt.get('request_accounting'):
        return 'advisory_hard_host_policy_requires_enforcement'
    allocation_path=Path(receipt['allocation_path']) if receipt.get('allocation_path') else supervision._allocation_path(directory,receipt['allocation_id'])
    if not allocation_path.exists():return None
    supervision._private(allocation_path);allocation=json.loads(allocation_path.read_text())
    if allocation.get('request_accounting'):return 'advisory_independent_request_accounting_remains'
    if allocation.get('governor_enabled',True) is False:return None
    task_owner=receipt.get('task_owner_thread_id',receipt['thread_id'])
    owners={member.get('task_owner_thread_id',thread) for thread,member in allocation['members'].items()}
    if not grant.get('auto_enrolled') or owners!={task_owner}:
        return 'advisory_independent_shared_cap_requires_enforcement'
    return None


def admit_advisory(root,policy,thread,*,principal,intended_limits=None,mode='advisory'):
    """Record an explicit non-enforcing choice without inventing a budget."""
    if not isinstance(principal,Principal) or principal.role!='operator' or principal.subject!=thread:
        raise PermissionDenied('governor_operator_required')
    if mode not in ('disabled','advisory'):raise ValueError('invalid inactive governor mode')
    authorize(root,'enforcement.disable',principal)
    directory=supervision._directory(root);path=control_path(root,thread,create=True)
    with supervision._lock(directory,'maintenance'),supervision._lock(directory,path.stem):
        if (directory/(supervision._name(thread)+'.json')).exists():raise ValueError('governor scope changed; inspect current state before choosing advisory')
        grant=supervision._grant(policy,thread,root=root)
        probe=dict(grant=grant,allocation_id=grant['allocation_id'],thread_id=thread)
        restriction=independent_constraint(directory,probe)
        from .goal_usage import observe_session_usage
        observation=observe_session_usage(grant['codex_home'],thread)
        prior=None
        if path.exists():supervision._private(path);prior=json.loads(path.read_text())
        try:goal,active=supervision._native(grant,thread)
        except Exception:
            if prior is None:raise
            goal=dict(createdAt=prior['control_goal_created_at'],status='paused') if prior.get('control_goal_created_at') is not None else None
            active=prior.get('control_active_turn_ids',[])
        from uuid import uuid4
        generation=uuid4().hex;limits=intended_limits or {}
        lifetime=observation.get('used_tokens') if observation.get('state')=='qualified' else None
        receipt=dict(thread_id=thread,generation=generation,allocation_id=grant['allocation_id'],grant=grant,
            policy_path=str(Path(policy).absolute()),session_scope=True,goal_created_at=None,
            token_limit=limits.get('token_limit'),time_limit_seconds=limits.get('time_limit_seconds'),
            deadline=None,time_origin=None,started_upper=None,started_boottime=None,
            token_accounting='fresh',boot_id=supervision.boot_id_value(),used_tokens=None,
            lifetime_used_tokens=lifetime,lifetime_tokens_before_window=0,accounting=observation,
            advisory_without_window=True,state='inactive',reason=restriction or 'operator_'+mode,
            governor_enabled=False,governor_mode=mode,governor_revision=1,
            governor_control=dict(source='authenticated_operator',enabled=False,mode=mode),
            control_goal_created_at=goal.get('createdAt') if goal else None,
            control_active_turn_ids=list(active) if not goal or goal.get('status')!='paused' else [],
            enrollment_revision=0,budget_revision=0,effects={},checkpoint=None,
            last_verified_usage=dict(generation=generation,used_tokens=None,lifetime_used_tokens=lifetime,elapsed_seconds=None))
        if path.exists():
            supervision._private(path);old=json.loads(path.read_text())
            receipt['generation']=old['generation']
            receipt['governor_revision']=old.get('governor_revision',0)+(old.get('governor_mode')!=mode)
            receipt['prior_control']=old if old.get('governor_mode')!=mode else old.get('prior_control')
        supervision._save(path,receipt)
    return control_snapshot(root,thread)


def control_path(root,thread,*,create=False):
    directory=Path(root).absolute()/'goal-supervision'/'controls'
    if create:
        directory.mkdir(mode=0o700,exist_ok=True);supervision._private(directory,True)
    return directory/(supervision._name(thread)+'.json')


def control_snapshot(root,thread):
    path=control_path(root,thread);supervision._private(path)
    receipt=json.loads(path.read_text())
    if receipt['thread_id']!=thread:raise ValueError('inactive governor target identity changed')
    from .goal_usage import observe_session_usage
    observation=observe_session_usage(receipt['grant']['codex_home'],thread)
    receipt['accounting']=observation
    receipt['lifetime_used_tokens']=observation.get('used_tokens') if observation.get('state')=='qualified' else None
    receipt['controller']=supervision._heartbeat(path.parent.parent)
    receipt['accounting_on_read']=True
    if observation.get('state')=='qualified':receipt['last_verified_usage']=dict(generation=receipt['generation'],used_tokens=None,lifetime_used_tokens=observation['used_tokens'],elapsed_seconds=None)
    restriction=independent_constraint(path.parent.parent,receipt)
    if restriction:receipt['reason']=restriction
    return supervision._public(receipt)
