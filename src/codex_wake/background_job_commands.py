"""CLI/MCP adapter for exact operator-configured background command profiles."""
from __future__ import annotations

import json
from pathlib import Path

from .background_jobs import BackgroundJobs, BackgroundJobError
from .permission_commands import verified_cli_principal
from .records import WakeError
from .task_briefs import TaskBriefStore


def register_parser(subparsers):
    parser = subparsers.add_parser('jobs', help='launch and await bounded approved local commands')
    commands = parser.add_subparsers(dest='job_command', required=True)
    for action in ('configure', 'profile', 'launch', 'show', 'cancel', 'await'):
        command = commands.add_parser(action)
        command.add_argument('--json', dest='as_json', action='store_true')
        command.add_argument('--bus-root', type=Path)
        command.add_argument('--operator-capability', type=Path)
        command.add_argument('--actor-capability', type=Path)
        command.add_argument('--actor-runtime', choices=('codex', 'grok'), default='codex')
        command.add_argument('--app-server', default='unix://')
        if action in ('configure', 'profile', 'launch'):
            command.add_argument('--profile', required=True)
        if action == 'configure':
            command.add_argument('--argv-json', required=True, help='operator-approved exact argv JSON list')
            command.add_argument('--cwd', type=Path, required=True)
            command.add_argument('--task-id', required=True)
            command.add_argument('--assignment-id', required=True)
            command.add_argument('--owner', required=True)
            command.add_argument('--max-seconds', type=float, default=300)
            command.add_argument('--max-log-bytes', type=int, default=1048576)
        if action == 'launch':
            command.add_argument('--idempotency-key', required=True)
        if action in ('show', 'cancel', 'await'):
            command.add_argument('--job-id', required=True)
        if action == 'cancel':
            command.add_argument('--generation', type=int, required=True)
    return parser


def execute(args, root, *, principal=None, register_wake=None):
    """The injected Principal and wake adapter are trusted host inputs only."""
    from .session_permissions import Principal
    caller = principal if principal is not None else verified_cli_principal(args)
    if type(caller) is not Principal:
        raise BackgroundJobError('job_identity_unverified', 'verified host caller required')
    # Task scopes are recovered by the host rather than accepted as CLI claims.
    store = BackgroundJobs(root)
    action = args.job_command
    if action == 'configure':
        return store.approve_command(args.profile, json.loads(args.argv_json), args.cwd,
            principal=caller, task_pin=TaskBriefStore(root).assignment_pin(args.task_id, args.assignment_id),
            owner=args.owner, max_seconds=args.max_seconds, max_log_bytes=args.max_log_bytes)
    if action == 'profile':
        profile = store.profile(args.profile)
        command = profile['command']
        if caller.role != 'operator' and caller.subject != command['owner']:
            raise BackgroundJobError('job_owner_denied', 'profile belongs to another exact owner')
        return profile
    if principal is None and caller.role != 'operator' and action in ('launch', 'cancel', 'await'):
        from .permission_enforcement import verified_tasks
        command = (store.profile(args.profile)['command'] if action == 'launch'
                   else store.inspect(args.job_id)['intent']['profile']['command'])
        pin = command['task_pin']
        caller = Principal(caller.subject, tasks=verified_tasks(root, caller.subject, pin['task_id'],
            pin['assignment_id'], actor_id=getattr(args, 'permission_actor_id', None)))
    if action == 'launch':
        return store.launch(args.profile, principal=caller, idempotency_key=args.idempotency_key)
    if action == 'show':
        value = store.inspect(args.job_id)
        store.authorize_inspection(value, caller)
        return value
    if action == 'cancel':
        return store.cancel(args.job_id, principal=caller, expected_generation=args.generation)
    if action == 'await':
        return store.await_result(args.job_id, principal=caller, register_wake=register_wake)
    raise BackgroundJobError('job_invalid_argument', 'unknown background job operation')


def jobs_command(args, root, *, principal=None, register_wake=None):
    try:
        value = execute(args, root, principal=principal, register_wake=register_wake)
        print(json.dumps(dict(schema_version=1, success=True, job=value), sort_keys=True))
        return 0
    except (WakeError, OSError, ValueError, KeyError, TypeError) as error:
        message = str(error) if isinstance(error, WakeError) else 'Job state or caller evidence unavailable.'
        print(json.dumps(dict(schema_version=1, success=False,
            error=dict(code=getattr(error, 'code', 'job_unavailable'), message=message)), sort_keys=True))
        return 5
