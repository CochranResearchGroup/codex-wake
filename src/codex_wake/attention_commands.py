"""Public CLI/host adapter; no model can assign operator authority or live context."""
import json
from pathlib import Path
import time

from .attention_queue import AttentionQueue, AttentionError, MAX_BYTES
from .goal_supervision import verified_native_caller
from .permission_commands import verified_cli_principal
from .records import WakeError
from .session_permissions import Principal


def execute(action, arguments, root, *, principal, native_context=None,
            context_validator=None, mcp=False, now=time.time):
    if (not isinstance(principal, Principal) or type(mcp) is not bool
            or any(key in arguments for key in ('operator', 'role', 'principal', 'context_validator'))):
        raise AttentionError('attention_authority_denied', 'authority and current context are host supplied')
    if mcp:
        if action not in ('request', 'list', 'show') or principal.role == 'operator':
            raise AttentionError('attention_operator_required', 'human responses require local operator CLI')
        verified_native_caller(native_context, principal.subject)
    store = AttentionQueue(root, now=now, context_validator=context_validator)
    if action == 'list':
        return store.inspect(principal, include_closed=arguments.get('include_closed', False))
    if action == 'show':
        return store.inspect(principal, arguments['request_id'])
    if action == 'request':
        return store.request(principal, arguments['request'])
    expected = dict(expected_revision=arguments['expected_revision'],
                    expected_fingerprint=arguments['fingerprint'])
    if action == 'respond':
        return store.respond(principal, arguments['request_id'], arguments['choice'],
            approval_id=arguments.get('approval_id'), **expected)
    if action == 'consume':
        return store.consume(principal, arguments['request_id'], **expected)
    if action == 'close':
        return store.close(principal, arguments['request_id'], disposition=arguments['disposition'],
            reason=arguments['reason'], **expected)
    raise AttentionError('attention_invalid_argument', 'unsupported attention operation')


def register_parser(subparsers):
    parser = subparsers.add_parser('attention', help='inspect and respond to the shared durable human-attention queue')
    verbs = parser.add_subparsers(dest='attention_command', required=True)
    for action in ('list', 'show', 'request', 'respond', 'consume', 'close'):
        command = verbs.add_parser(action)
        command.add_argument('--bus-root', type=Path, required=True)
        command.add_argument('--operator-capability', type=Path)
        command.add_argument('--actor-capability', type=Path)
        command.add_argument('--app-server', default='unix://')
        command.add_argument('--json', dest='as_json', action='store_true')
        if action == 'list':
            command.add_argument('--include-closed', action='store_true')
        if action == 'request':
            command.add_argument('--file', type=Path, required=True)
        if action in ('show', 'respond', 'consume', 'close'):
            command.add_argument('--request-id', required=True)
        if action in ('respond', 'consume', 'close'):
            command.add_argument('--expected-revision', type=int, required=True)
            command.add_argument('--fingerprint', required=True)
        if action == 'respond':
            command.add_argument('--choice', choices=('accept', 'decline', 'acknowledge'), required=True)
            command.add_argument('--approval-id')
        if action == 'close':
            command.add_argument('--disposition', choices=('closed', 'unknown'), required=True)
            command.add_argument('--reason', required=True)
    return parser


def run(args, root, *, context_validator=None, now=time.time):
    try:
        principal = verified_cli_principal(args)
        names = ('request_id', 'expected_revision', 'fingerprint', 'choice', 'approval_id',
                 'disposition', 'reason', 'include_closed')
        arguments = {name: getattr(args, name) for name in names if getattr(args, name, None) is not None}
        if args.attention_command == 'request':
            with args.file.open() as source:
                raw = source.read(MAX_BYTES + 1)
            if len(raw.encode()) > MAX_BYTES:
                raise AttentionError('request_invalid', 'request packet too large')
            from .attention_queue import _unique
            arguments['request'] = json.loads(raw, object_pairs_hook=_unique)
        if principal.role != 'operator' and args.attention_command not in ('list', 'show'):
            from .session_permissions import PermissionStore
            policy = PermissionStore(root)
            if policy.active():
                from .permission_enforcement import verified_tasks
                if args.attention_command == 'request':
                    task_id = arguments['request']['context']['task_id']
                else:
                    task_id = AttentionQueue(root, now=now).inspect(principal, arguments['request_id'])['request']['context']['task_id']
                tasks = verified_tasks(policy.root, principal.subject, task_id, None,
                    actor_id=getattr(args, 'permission_actor_id', None))
                principal = Principal(principal.subject, tasks=tasks)
        result = execute(args.attention_command, arguments, root, principal=principal,
            context_validator=context_validator, now=now)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (WakeError, ValueError, TypeError, KeyError, OSError) as error:
        print(json.dumps(dict(status='held', error=dict(code=getattr(error, 'code', 'attention_unavailable'),
            message=str(error) if isinstance(error, WakeError) else 'Attention authority or evidence unavailable.')), sort_keys=True))
        return 2
