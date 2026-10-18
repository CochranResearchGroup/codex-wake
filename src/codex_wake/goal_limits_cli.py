"""CLI adapter for host-scoped existing-session resource supervision."""
from __future__ import annotations

import json
import math
from pathlib import Path


def add_goal_limits_parser(subparsers):
    parser = subparsers.add_parser('goal-limits', help='supervise resource limits in an existing native session')
    commands = parser.add_subparsers(dest='goal_limits_command', required=True)
    for name in ('set', 'show'):
        command = commands.add_parser(name, help='enroll limits' if name == 'set' else 'read enforcement evidence')
        command.add_argument('--policy', type=Path, required=True, help='private host-approved caller allocations')
        command.add_argument('--caller-thread-id', required=True)
        command.add_argument('--json', action='store_true', dest='as_json')
        if name == 'set':
            command.add_argument('--token-limit', type=int, required=True)
            command.add_argument('--time-limit-seconds', type=int, required=True)
            command.add_argument('--checkpoint-token-percent', type=float, default=5)
            command.add_argument('--checkpoint-seconds', type=int, default=60)
    watcher = commands.add_parser('watch', help='run the independent resource-limit controller; keep alive as a service')
    watcher.add_argument('--interval', type=float, default=1)


def goal_limits_command(args, root):
    if args.goal_limits_command == 'watch':
        if not math.isfinite(args.interval) or not .05 <= args.interval <= 5:
            from .records import WakeError
            raise WakeError('goal-limit watcher interval must be between 0.05 and 5 seconds')
        from .goal_supervision import watch
        watch(root, interval=args.interval)
        return 0
    try:
        from .goal_supervision import enroll, show
        if args.goal_limits_command == 'show':
            result = show(root, args.policy, args.caller_thread_id)
        else:
            result = enroll(root, args.policy, args.caller_thread_id,
                args.token_limit, args.time_limit_seconds,
                checkpoint_token_percent=args.checkpoint_token_percent,
                checkpoint_seconds=args.checkpoint_seconds)
    except Exception as exc:
        from .records import WakeError
        message = str(exc) if isinstance(exc, (ValueError, WakeError)) else 'Host filesystem, socket or controller unavailable; inspect operator setup.'
        result = {'error': {'code': 'goal_limits_unavailable', 'reason': type(exc).__name__, 'message': message},
                  'state': 'held', 'armed': False}
        print(json.dumps(result))
        return 2
    print(json.dumps(result))
    return 0 if args.goal_limits_command == 'show' or result.get('state') in ('armed', 'checkpoint_requested') else 2
