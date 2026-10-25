"""CLI adapter for host-scoped existing-session resource supervision."""
from __future__ import annotations

import json
import math
from pathlib import Path


def add_goal_limits_parser(subparsers):
    parser = subparsers.add_parser('goal-limits', help='supervise resource limits in an existing native session')
    commands = parser.add_subparsers(dest='goal_limits_command', required=True)
    for name in ('set', 'show', 'readiness', 'diagnose', 'notices', 'recover', 'disable', 'watcher-status', 'start-watcher'):
        command = commands.add_parser(name, help='enroll limits' if name == 'set' else 'read enforcement evidence')
        command.add_argument('--policy', type=Path, required=True, help='private host-approved caller allocations')
        command.add_argument('--caller-thread-id', required=True)
        command.add_argument('--allocation-id', help='existing host objective allocation')
        command.add_argument('--json', action='store_true', dest='as_json')
        command.add_argument('--bus-root',type=Path)
        command.add_argument('--operator-capability',type=Path)
        command.add_argument('--actor-capability',type=Path)
        command.add_argument('--app-server',default='unix://')
        command.add_argument('--task-id')
        command.add_argument('--assignment-id')
        command.add_argument('--operation-id')
        if name=='notices':command.add_argument('--event-id')
        if name == 'set':
            command.add_argument('--token-limit', type=int, required=True)
            command.add_argument('--time-limit-seconds', type=int, required=True)
            command.add_argument('--checkpoint-token-percent', type=float, default=5)
            command.add_argument('--checkpoint-seconds', type=int, default=60)
            command.add_argument('--token-accounting', choices=('fresh','cache_inclusive'),
                                 help='new enrollments default to fresh input plus output, excluding cache')
    from .goal_renewal_commands import register_parser as renewal_parser
    renewal_parser(commands)
    maintenance = commands.add_parser('prepare-maintenance', help='host-only bounded graceful controller handover; never renews resources')
    maintenance.add_argument('--policy', type=Path, required=True, help='private operator maintenance authorization, separate from allocation policy')
    maintenance.add_argument('--seconds', type=int, required=True)
    maintenance.add_argument('--json', action='store_true', dest='as_json')
    watcher = commands.add_parser('watch', help='run the independent resource-limit controller; keep alive as a service')
    watcher.add_argument('--interval', type=float, default=1)


def goal_limits_command(args, root):
    if args.goal_limits_command in ('extend','reset','apply-renewal'):
        from .goal_renewal_commands import command
        return command(args,root)
    if args.goal_limits_command == 'watch':
        if not math.isfinite(args.interval) or not .05 <= args.interval <= 5:
            from .records import WakeError
            raise WakeError('goal-limit watcher interval must be between 0.05 and 5 seconds')
        from .goal_supervision import watch
        watch(root, interval=args.interval)
        return 0
    try:
        from .goal_supervision import enroll, show
        from .session_permissions import PermissionStore
        principal=None
        if args.goal_limits_command!='prepare-maintenance' and (PermissionStore(root).active() or args.goal_limits_command in ('recover','disable','start-watcher')):
            from .permission_enforcement import cli_principal
            principal=cli_principal(args,root)
        if args.goal_limits_command in ('watcher-status','start-watcher'):
            from .goal_watcher import watcher_status,start_watcher
            result=(watcher_status(root) if args.goal_limits_command=='watcher-status' else
                start_watcher(root,principal=principal,task_id=args.task_id,operation_id=args.operation_id))
        elif args.goal_limits_command == 'prepare-maintenance':
            from .goal_maintenance import prepare
            result = prepare(root,args.policy,args.seconds)
        elif args.goal_limits_command=='notices':
            from .goal_notice_commands import execute
            result=execute(root,args.policy,args.caller_thread_id,event_id=args.event_id,
                allocation_id=args.allocation_id,permission_principal=principal)
        elif args.goal_limits_command=='diagnose':
            from .goal_supervision import diagnose
            result=diagnose(root,args.policy,args.caller_thread_id,args.allocation_id,permission_principal=principal)
        elif args.goal_limits_command in ('show','readiness'):
            result = show(root, args.policy, args.caller_thread_id,args.allocation_id,permission_principal=principal)
        elif args.goal_limits_command=='recover':
            from .goal_recovery import recover
            result=recover(root,args.policy,args.caller_thread_id,principal=principal,
                task_id=args.task_id,operation_id=args.operation_id,allocation_id=args.allocation_id)
        elif args.goal_limits_command=='disable':
            from .permission_enforcement import diagnostic
            result=diagnostic(root,args.caller_thread_id,'enforcement.'+args.goal_limits_command,
                principal=principal,task_id=args.task_id,operation_id=args.operation_id)
        else:
            result = enroll(root, args.policy, args.caller_thread_id,
                args.token_limit, args.time_limit_seconds,
                checkpoint_token_percent=args.checkpoint_token_percent,
                checkpoint_seconds=args.checkpoint_seconds,token_accounting=args.token_accounting,allocation_id=args.allocation_id,
                permission_principal=principal,task_id=args.task_id,operation_id=args.operation_id)
    except Exception as exc:
        from .records import WakeError
        message = str(exc) if isinstance(exc, (ValueError, WakeError)) else 'Host filesystem, socket or controller unavailable; inspect operator setup.'
        from .goal_readiness import explain_error
        result = explain_error(exc)
        result['error']['message']=message
        from .goal_supervision import CallerGrantMissing
        if isinstance(exc, CallerGrantMissing):
            result.update(reason='caller_grant_missing', effect_attempted=False,
                caller_thread_id=args.caller_thread_id,
                missing_evidence=['caller_identity', 'operator_allocation_authority'],
                operator_interaction='available', campaign_continuation='held',
                next_action='The host must bind trusted caller identity and operator allocation '
                    'authority before provisioning. Agents cannot issue their own grants. '
                    'Preserve the allocation; setup diagnosis, checkpointing and operator replies '
                    'remain available. Do not retry with another caller or copy a grant.')
        if getattr(exc,'decision',None) is not None:result['permission']=exc.decision
        if type(exc).__name__=='PermissionDenied':result['effect_attempted']=False
        if getattr(exc,'code',None):result['error']['code']=exc.code
        print(json.dumps(result))
        return 2
    if args.goal_limits_command=='readiness' and not args.as_json:
        readiness=result['engagement']
        print('External goal watcher: '+readiness['status'].replace('_',' '))
        card=readiness.get('card')
        if card:
            print(f"Tokens: {card['used_tokens']}/{card['token_limit']} {card['token_accounting']}; {card['remaining_tokens']} remaining.")
            print(f"Stop at {card['deadline_utc']} ({card['timezone']}). Checkpoint reserve: {card['checkpoint_tokens']:g} tokens / {card['checkpoint_seconds']:g} seconds.")
            print(f"Scope: {card['scope']} {card['allocation_id']}; watcher: {card['watcher_health']}.")
            print('Conversation presentation: '+readiness['presentation']+'; operator reading: unverified.')
        print(readiness['next_action'])
    else:print(json.dumps(result))
    return 0 if args.goal_limits_command in ('show','readiness','diagnose','notices','watcher-status') or result.get('state') in ('armed', 'checkpoint_requested', 'prepared') or result.get('reason')=='watcher_running' else 2
