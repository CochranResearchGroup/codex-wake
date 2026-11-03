"""History CLI/MCP adapters; authenticated context is never an operation input."""
import json
import os
from pathlib import Path
import socket
import tomllib

from .controller_history import ControllerHistory, ManagedHistoryResume
from .managed_inventory import InventoryError
from .records import WakeError


def execute(operation, arguments, root, *, authorized_accounts=(), principal=None, runtime=None, now=None, authorization_guard=None):
    try:
        if root is None:
            raise InventoryError('host_wake_root_required', 'host Wake root is required')
        root = Path(root)
        resume = ManagedHistoryResume(root, principal, runtime=runtime, now=now) if principal is not None else None
        owner = ControllerHistory(root / 'controller-accounts.toml', root=root,
            host=socket.gethostname(), environment=os.environ.get('WSL_DISTRO_NAME') or os.name,
            authorized_accounts=authorized_accounts, resume_owner=resume, authorization_guard=authorization_guard)
        result = owner.execute(operation, arguments)
        status = 'completed'
        if operation == 'history.resume' and result.get('resume', {}).get('status') != 'resumed':
            status = 'held'
        return dict(schema_version=1, operation=operation, status=status, result=result)
    except InventoryError as error:
        return dict(schema_version=1, operation=operation, status='failed',
                    error=dict(code=error.code, message=str(error)))


def policy(root):
    try:
        from .controller_registry import resolve_registry
        path = resolve_registry(Path(root) / 'controller-accounts.toml', root=root)
        return tomllib.loads(path.read_text()).get('history', {})
    except (OSError, ValueError, TypeError):
        raise InventoryError('configuration_unavailable', 'host history policy is unavailable') from None


def register_parser(subparsers):
    parser = subparsers.add_parser('history', help='read permitted native history and resume its exact owner')
    verbs = parser.add_subparsers(dest='history_verb', required=True)
    search = verbs.add_parser('search')
    search.add_argument('--owner', action='append', dest='owners')
    search.add_argument('--query', default='')
    search.add_argument('--json', dest='as_json', action='store_true')
    transfer = verbs.add_parser('import', help='copy a pinned saved conversation into another account through native fork')
    transfer.add_argument('thread_id')
    transfer.add_argument('--owner', required=True)
    transfer.add_argument('--destination', required=True)
    transfer.add_argument('--channel', choices=('stock', 'modded'), default='modded')
    transfer.add_argument('--expected-source', type=json.loads)
    transfer.add_argument('--expected-target', type=json.loads)
    transfer.add_argument('--idempotency-key')
    transfer.add_argument('--yes', action='store_true', dest='confirm', help='Confirm the displayed interactive source-preserving copy; does not relax target pins.')
    transfer.add_argument('--json', dest='as_json', action='store_true')
    for verb in ('read', 'resume'):
        command = verbs.add_parser(verb)
        command.add_argument('thread_id')
        command.add_argument('--owner', required=True)
        command.add_argument('--expected-target', type=json.loads, required=verb == 'resume')
        command.add_argument('--json', dest='as_json', action='store_true')
        if verb == 'resume':
            command.add_argument('--intent', required=True)
            command.add_argument('--expires-at', required=True)
            command.add_argument('--bus-root', required=True)
            command.add_argument('--operator-capability', required=True)
            command.set_defaults(actor_capability=None)
            command.add_argument('--app-server', default='unix://')


def command(args, root, *, runtime=None, now=None):
    if args.history_verb == 'import':
        return import_command(args, root)
    try:
        allowed = policy(root).get('readable_accounts', [])
        principal = None
        if args.history_verb == 'resume':
            from .permission_commands import verified_cli_principal
            principal = verified_cli_principal(args)
        arguments = {key: value for key, value in vars(args).items()
            if key in ('owners', 'query', 'owner', 'thread_id', 'expected_target', 'intent', 'expires_at') and value is not None}
        value = execute('history.' + args.history_verb, arguments, root,
                        authorized_accounts=allowed, principal=principal, runtime=runtime, now=now)
    except (WakeError, ValueError, OSError) as error:
        value = dict(schema_version=1, operation='history.' + args.history_verb, status='failed',
                     error=dict(code=getattr(error, 'code', 'unauthorized_target'), message='history caller could not be authorized'))
    print(json.dumps(value, sort_keys=True))
    return 0 if value['status'] == 'completed' else 2


def tool_specs():
    text = {'type': 'string', 'minLength': 1, 'maxLength': 1024}
    identity = {'caller_thread_id': text}
    return {
        'wake_controller_history_search': ('controller-history', 'search',
            'Search explicitly permitted native history metadata without changing its ownership.',
            dict(identity, owners={'type': 'array', 'items': text, 'maxItems': 256}, query=text), ['caller_thread_id'], True),
        'wake_controller_history_read': ('controller-history', 'read',
            'Read bounded native JSONL from the exact permitted owning account.',
            dict(identity, owner=text, thread_id=text, expected_target={'type': 'object'}),
            ['caller_thread_id', 'owner', 'thread_id'], True),
        'wake_controller_history_resume': ('controller-history', 'resume',
            'Resume an enrolled exact saved owner through existing attachment/permission authority. No work or allowance renewal.',
            dict(identity, owner=text, thread_id=text, expected_target={'type': 'object'}, intent=text, expires_at=text),
            ['caller_thread_id', 'owner', 'thread_id', 'expected_target', 'intent', 'expires_at'], False),
    }


def mcp_call(runner, arguments, native_context, verb, *, runtime=None, now=None):
    from .goal_supervision import verified_native_caller
    from .session_permissions import Principal, PermissionStore
    try:
        caller = arguments.get('caller_thread_id')
        verified_native_caller(native_context, caller)
        host_policy = policy(runner.wake_root)
        allowed = host_policy.get('callers', {}).get(caller, [])
        if not allowed:
            raise InventoryError('unauthorized_target', 'history caller has no account read scope')
        principal = None
        if verb == 'resume':
            store = PermissionStore(runner.wake_root)
            delegated = caller in store._read()['policy'].get('delegations', {})
            principal = Principal(caller, 'controller' if delegated else 'session')
        selected = {key: value for key, value in arguments.items() if key != 'caller_thread_id'}
        result = execute('history.' + verb, selected, runner.wake_root,
            authorized_accounts=allowed, principal=principal, runtime=runtime, now=now)
    except (WakeError, ValueError, TypeError, KeyError, OSError) as error:
        result = dict(schema_version=1, operation='history.' + verb, status='failed',
            error=dict(code=getattr(error, 'code', 'unauthorized_target'), message='history caller could not be authorized'))
    return result, result['status'] != 'completed'


def import_tool_specs():
    text = {'type': 'string', 'minLength': 1, 'maxLength': 200}
    properties = dict(owner=text, thread_id=text, destination=text,
        channel={'type': 'string', 'enum': ['stock', 'modded']}, expected_source={'type': 'object'},
        expected_target={'type': 'object'}, _request={'type': 'object'})
    return {'wake_controller_history_import': ('controller-history-import', 'history.import',
        'Copy a pinned goal-free saved conversation into another account; source remains unchanged. No model turn or allowance renewal.',
        properties, list(properties), False)}


def protected_import(arguments, root, *, actor=None, authorize=None):
    from .controller_history_import import ControllerHistoryImport
    from .operation_commands import local_actor
    if actor is None:
        actor = local_actor(root)
        authorize = lambda: local_actor(root)
    return ControllerHistoryImport(root).execute(actor, 'history.import', arguments, authorize=authorize)


def import_command(args, root):
    try:
        from dataclasses import replace
        import hashlib
        from .daemon_commands import local_operator
        from .cli_targets import require_terminal, show_intent, confirm_intent, intent_key
        arguments = {key: getattr(args, key) for key in (
            'owner', 'thread_id', 'destination', 'channel', 'expected_source', 'expected_target')}
        key = args.idempotency_key
        missing = [flag for flag, value in (('--expected-source', args.expected_source),
            ('--expected-target', args.expected_target), ('--idempotency-key', key)) if value is None]
        require_terminal(missing)
        if missing:
            if arguments['expected_source'] is None:
                view = execute('history.read', dict(owner=args.owner, thread_id=args.thread_id), root,
                               authorized_accounts=policy(root).get('readable_accounts', []))
                if view['status'] != 'completed':
                    raise InventoryError(view['error']['code'], view['error']['message'])
                arguments['expected_source'] = view['result']['session']['target']
            if arguments['expected_target'] is None:
                from .daemon_commands import execute as daemon_execute
                view = daemon_execute(root, 'daemons.status', dict(account=args.destination, channel=args.channel))
                arguments['expected_target'] = view['result']['daemon']['target']
            key = key if key is not None else intent_key()
            show_intent('history.import', arguments['expected_target'], key, source=arguments['expected_source'])
            confirm_intent('Copy this saved conversation to the selected destination; preserve the source and transfer no credentials or allowance.',
                           getattr(args, 'confirm', False))
        identifier = 'history-import-' + hashlib.sha256(key.encode()).hexdigest()[:32]
        arguments['_request'] = dict(operation_id=identifier, idempotency_key=key,
            correlation_id=identifier, binding='local-cli', target=arguments['expected_target'])
        actor = local_operator(arguments['expected_target'], {'control', 'observe', 'history.observe'})
        actor = replace(actor, targets=[arguments['expected_source'], arguments['expected_target']])
        value = protected_import(arguments, root, actor=actor, authorize=lambda: actor)
    except (WakeError, ValueError, OSError, TypeError) as error:
        value = dict(schema_version=1, operation='history.import', status='failed',
            error=dict(code=getattr(error, 'code', 'invalid_argument'), message=str(error)))
    print(json.dumps(value, sort_keys=True))
    return 0 if value['status'] == 'completed' and value.get('result', {}).get('operation', {}).get('execution') == 'completed' else 2
