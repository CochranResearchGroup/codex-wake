"""CLI/MCP caller adapter for approved task briefs; no model-supplied roles."""
from __future__ import annotations

import json
from pathlib import Path

from .records import WakeError
from .task_briefs import BriefAuthority, MAX_BRIEF_BYTES, TaskBriefError, TaskBriefStore


def register_parser(subparsers):
    parser = subparsers.add_parser('task-briefs', help='propose, approve and pin revisioned task scope')
    commands = parser.add_subparsers(dest='task_brief_command', required=True)
    for verb in ('propose', 'approve', 'inspect', 'admit', 'pin'):
        command = commands.add_parser(verb)
        command.add_argument('--task-id', required=True)
        command.add_argument('--bus-root', type=Path)
        command.add_argument('--operator-capability', type=Path)
        command.add_argument('--actor-capability', type=Path)
        command.add_argument('--app-server', default='unix://')
        command.add_argument('--json', dest='as_json', action='store_true')
        if verb == 'propose':
            content = command.add_mutually_exclusive_group(required=True)
            content.add_argument('--brief-file', type=Path)
            content.add_argument('--brief-json')
        if verb in ('approve', 'admit'):
            command.add_argument('--revision', type=int, required=verb == 'approve')
        if verb in ('admit', 'pin'):
            command.add_argument('--assignment-id', required=True)
    return parser


def _capability_authority(args, store):
    from .a2a_bus import BusStore
    from .a2a_cli import invoking_actor
    if not args.bus_root or bool(args.operator_capability) == bool(args.actor_capability):
        raise TaskBriefError('authority_denied', 'use a trusted caller adapter or one existing bus capability')
    bus = BusStore(args.bus_root)
    if args.operator_capability:
        with bus.connection() as database:
            bus.operator(database, args.operator_capability)
        return BriefAuthority('operator:' + bus.bus_id, 'operator')
    actor = invoking_actor(bus, args.actor_capability, endpoint=args.app_server)
    with bus.connection() as database:
        bus.validate_actor(database, actor)
    # The capability authorizes worker operations in its enrolled workspace.
    # It cannot approve scope or become a controller via command arguments.
    workspace = None
    if args.task_brief_command == 'propose':
        content = _content(args)
        workspace = content.get('workspace')
    else:
        existing = store.inspect(args.task_id)
        if existing['revisions']:
            workspace = existing['revisions'][0]['content']['workspace']
    if type(workspace) is not str or not Path(workspace).is_relative_to(Path(actor.root)):
        raise TaskBriefError('authority_denied', 'brief workspace is outside the actor enrollment')
    return BriefAuthority(actor.actor_id, 'worker', (args.task_id,))


def _read_brief(path):
    with Path(path).open('rb') as stream:
        raw = stream.read(MAX_BRIEF_BYTES + 1)
    if len(raw) > MAX_BRIEF_BYTES:
        raise TaskBriefError('invalid_argument', 'brief file exceeds size limit')
    value = json.loads(raw)
    if type(value) is not dict:
        raise TaskBriefError('invalid_argument', 'brief file must contain an object')
    return value


def _content(args):
    inline = getattr(args, 'brief_json', None)
    if inline is None:
        return _read_brief(args.brief_file)
    if type(inline) is not str or len(inline.encode()) > MAX_BRIEF_BYTES:
        raise TaskBriefError('invalid_argument', 'inline brief exceeds size limit')
    value = json.loads(inline)
    if type(value) is not dict:
        raise TaskBriefError('invalid_argument', 'brief must contain an object')
    return value


def execute_task_briefs(args, root, *, authority=None):
    """Return the shared public result; injected authority must be host-verified."""
    store = TaskBriefStore(root)
    caller = authority if authority is not None else _capability_authority(args, store)
    if type(caller) is not BriefAuthority:
        raise TaskBriefError('authority_denied', 'verified brief authority is required')
    verb = args.task_brief_command
    if verb == 'propose':
        return store.propose(args.task_id, _content(args), authority=caller)
    if verb == 'approve':
        return store.approve(args.task_id, args.revision, authority=caller)
    if verb == 'inspect':
        return store.inspect(args.task_id, authority=caller)
    if verb == 'admit':
        return store.admit(args.task_id, args.assignment_id, authority=caller, revision=args.revision)
    if verb == 'pin':
        return store.assignment_pin(args.task_id, args.assignment_id, authority=caller)
    raise TaskBriefError('invalid_argument', 'unknown task brief operation')


def task_briefs_command(args, root, *, authority=None):
    try:
        result = execute_task_briefs(args, root, authority=authority)
        print(json.dumps(dict(schema_version=1, success=True, brief=result), sort_keys=True))
        return 0
    except (WakeError, OSError, ValueError, KeyError, TypeError) as error:
        code = getattr(error, 'code', 'brief_unavailable')
        message = str(error) if isinstance(error, WakeError) else 'task brief data or evidence is unavailable'
        print(json.dumps(dict(schema_version=1, success=False, error=dict(code=code, message=message)), sort_keys=True))
        return 5
