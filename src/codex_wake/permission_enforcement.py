"""Common-policy boundary for existing-goal enforcement and qualified recovery.

Host adapters construct Principal after native/capability verification. A policy
result never clears a stop, renews a resource envelope, or qualifies accounting.
"""
from __future__ import annotations

import json
from pathlib import Path

from .session_permissions import PermissionStore, Principal, PermissionDenied

RECOVERY_REQUIREMENTS = (
    'explicit_operator_recovery_authority', 'qualified_nondecreasing_accounting',
    'verified_current_exact_native_state', 'fresh_controller',
    'same_boot_continuity', 'remaining_original_resources',
)


def principal_for(root, thread, *, native_context=None, principal=None):
    """Accept only private host proof; caller UUIDs remain untrusted claims."""
    if not PermissionStore(root).active():
        return None
    if principal is None:
        from .goal_supervision import verified_native_caller
        verified_native_caller(native_context, thread)
        principal = Principal(thread)
    if not isinstance(principal, Principal) or principal.subject != thread:
        raise PermissionDenied('permission_identity_unverified')
    return principal


def authorize(root, action, principal, *, task_id=None, operation_id=None):
    """Operator CLI request is exact operation authority, never a deny override."""
    store = PermissionStore(root)
    if not store.active():
        return {'permission': 'legacy', 'action': action}
    decision = store.evaluate(action, principal, target=principal.subject,
                              task_id=task_id, operation_id=operation_id)
    if decision['permission'] == 'approval_required' and principal.role == 'operator':
        decision = dict(decision, permission='allow', approval_id='explicit_operator_request',
                        approval_scope='operation', rule='explicit_operator_request')
    if decision['permission'] != 'allow':
        raise PermissionDenied('permission_' + decision['permission'], decision)
    return decision


def enrollment_action(previous, token_limit, seconds, token_accounting, allocation_id):
    if previous is not None and (
            token_limit > previous['token_limit'] or seconds > previous['time_limit_seconds']
            or allocation_id != previous['allocation_id']
            or (token_accounting is not None and
                token_accounting != previous.get('token_accounting', 'cache_inclusive'))):
        return 'enforcement.increase'
    return 'enforcement.enroll'


def diagnostic(root, thread, action, *, principal, task_id=None, operation_id=None):
    """Classify unavailable control without writing the existing campaign."""
    from .goal_supervision import _name, _private, _public
    decision = authorize(root, action, principal, task_id=task_id, operation_id=operation_id)
    path = Path(root) / 'goal-supervision' / (_name(thread) + '.json')
    receipt = None
    if path.exists():
        _private(path)
        receipt = json.loads(path.read_text())
        if receipt.get('thread_id') != thread:
            raise PermissionDenied('permission_target_mismatch')
    if action!='enforcement.disable':
        raise PermissionDenied('recovery_requires_qualified_command')
    result=dict(state='held',armed=False,effect_attempted=False,permission=decision,
        capability='unsupported',
        readiness='stop_latched' if receipt and receipt.get('stop_latched') else 'not_observed',
        reason='enforcement_disable_unsupported',
        next_action='Keep existing safety enforcement active; disabling is not implemented by this policy check.')
    if receipt is not None:
        result['campaign'] = _public(receipt)
    return result


def describe(root, thread, *, principal):
    store = PermissionStore(root)
    if not store.active():
        return None
    actions = ('enforcement.enroll', 'enforcement.increase', 'enforcement.disable', 'enforcement.recover')
    return {action: store.evaluate(action, principal, target=thread,
        capability='unsupported' if action=='enforcement.disable' else 'supported',
        readiness='not_observed') for action in actions}


def tool_specs():
    from .harness_mcp import CALLER, TEXT
    result = {}
    for verb in ('recover', 'disable'):
        result['wake_goal_limits_' + verb] = ('goal-limits', verb,
            ('Recover an observation-fault stop only with explicit approval, repeated exact native observations, '
             'qualified accounting, fresh controller, same boot and original remaining resources. Does not resume the goal or renew limits.'
             if verb=='recover' else 'Check explicit disable authority; disabling runtime enforcement remains unsupported.'),
            dict(caller_thread_id=CALLER, allocation_id=TEXT, task_id=TEXT,
                 assignment_id=TEXT, operation_id=TEXT), ['caller_thread_id'], False)
    return result


def verified_tasks(root, subject, task_id, assignment_id, *, controller_tasks=(), actor_id=None):
    if task_id is None:
        return ()
    if task_id in controller_tasks:
        return (task_id,)
    if assignment_id is None:
        raise PermissionDenied('permission_task_scope_unverified')
    from .task_briefs import TaskBriefStore
    store = TaskBriefStore(PermissionStore(root).root)
    state = store.inspect(task_id)
    admission = next((item for item in state['admissions'] if item['assignment_id']==assignment_id),None)
    if not admission or admission['actor_id'] != (actor_id or 'native:' + subject):
        raise PermissionDenied('permission_task_scope_unverified')
    store.assignment_pin(task_id, assignment_id)
    return (task_id,)


def mcp_call(runner, verb, arguments, native_context):
    from .goal_supervision import verified_native_caller, enroll, show
    from .harness_mcp import controller_tasks
    root = runner.goal_limits_root if runner.goal_limits_root is not None else runner.wake_root
    if root is None or runner.goal_limits_policy is None:
        raise PermissionDenied('goal_limits_host_scope_unavailable')
    thread = arguments['caller_thread_id']
    verified_native_caller(native_context, thread)
    tasks = verified_tasks(root, thread, arguments.get('task_id'), arguments.get('assignment_id'),
                           controller_tasks=controller_tasks(runner, thread))
    principal = Principal(thread, tasks=tasks)
    if verb == 'show':
        return show(root, runner.goal_limits_policy, thread, arguments.get('allocation_id'),
                    permission_principal=principal)
    if verb=='recover':
        from .goal_recovery import recover
        return recover(root,runner.goal_limits_policy,thread,principal=principal,
            task_id=arguments.get('task_id'),operation_id=arguments.get('operation_id'),
            allocation_id=arguments.get('allocation_id'))
    if verb=='disable':
        return diagnostic(root, thread, 'enforcement.' + verb, principal=principal,
                          task_id=arguments.get('task_id'), operation_id=arguments.get('operation_id'))
    options = {k: v for k, v in arguments.items() if k not in ('assignment_id',)}
    return enroll(root, runner.goal_limits_policy, native_context=native_context,
                  permission_principal=principal, **options)


def cli_principal(args, root):
    if not args.bus_root or bool(args.operator_capability)==bool(args.actor_capability):
        raise PermissionDenied('permission_identity_unverified')
    from .permission_commands import verified_cli_principal
    principal = verified_cli_principal(args)
    thread = args.caller_thread_id
    if principal.role == 'operator':
        return Principal(thread, 'operator')
    if principal.subject != thread:
        raise PermissionDenied('permission_target_mismatch')
    # The CLI capability has already verified the exact actor/native context.
    from .a2a_bus import BusStore
    from .a2a_cli import invoking_actor
    bus = BusStore(args.bus_root)
    actor = invoking_actor(bus, Path(args.actor_capability), endpoint=args.app_server)
    tasks = verified_tasks(root, thread, args.task_id, args.assignment_id, actor_id=actor.actor_id)
    return Principal(thread, tasks=tasks)


def controller_permission(root, receipt):
    """Recheck future continuation, without revoking committed safety stops.

    A permission change alone is not a native turn-interrupt request. The original
    resource envelope still owns its pause/interrupt obligation when exhausted.
    """
    store=PermissionStore(root)
    if not store.active():
        return {'permission':'legacy','action':'enforcement.enroll'}
    try:
        admitted=receipt.get('enforcement_permission',{})
        task_id=admitted.get('task_id')
        principal=Principal(receipt['thread_id'],tasks=(task_id,) if task_id else ())
        return store.evaluate('enforcement.enroll',principal,
                              target=receipt['thread_id'],task_id=task_id,
                              operation_id=admitted.get('operation_id'))
    except (OSError,ValueError,KeyError,TypeError,PermissionDenied) as error:
        return dict(permission='deny',action='enforcement.enroll',
                    reason='permission_policy_unavailable',error=type(error).__name__)


def main():
    import sys
    from types import SimpleNamespace
    from .records import WakeError
    try:
        raw=sys.stdin.buffer.read(65537)
        if len(raw)>65536:raise ValueError('private enforcement packet exceeds limit')
        packet=json.loads(raw)
        runner=SimpleNamespace(**{k:Path(v) if v is not None else None for k,v in packet['runner'].items()})
        value=mcp_call(runner,packet['verb'],packet['arguments'],packet['native_context'])
        failed=packet['verb']!='show' and value.get('state') not in ('armed','checkpoint_requested')
    except (ValueError,OSError,KeyError,TypeError,WakeError) as exc:
        from .goal_readiness import explain_error
        value=explain_error(exc)
        if isinstance(exc,PermissionDenied):
            value.update(permission=exc.decision,effect_attempted=False,state='held',armed=False)
        failed=True
    print(json.dumps(value))
    return 2 if failed else 0


if __name__=='__main__':raise SystemExit(main())
