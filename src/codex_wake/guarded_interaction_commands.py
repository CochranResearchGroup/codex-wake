"""Public operator CLI and read-only model inspection seam for guarded menus."""
from pathlib import Path
import json
from .guarded_interactions import GuardedInteractions, MenuError
from .session_permissions import Principal


def execute(action, arguments, root, *, operator=False, host=None):
    if any(key in arguments for key in ('operator', 'role', 'principal')):
        raise MenuError('authority_must_be_host_supplied')
    service = GuardedInteractions(root, host=host)
    name = arguments['profile']
    if action == 'inspect':
        return service.inspect(name)
    if action == 'reconcile':
        return service.reconcile(name, arguments['operation'])
    if operator is not True:
        raise MenuError('operator_required_menu_execution_not_model_attested')
    principal = Principal('local-operator', 'operator')
    if action == 'configure':
        return service.configure(name, arguments['binding'], principal=principal, reason=arguments['reason'])
    token = arguments['token']
    if action in ('takeover', 'return'):
        return service.change_owner(name, token, principal=principal, human=action == 'takeover', reason=arguments['reason'])
    if action == 'run':
        return service.run(name, token, principal=principal, operation=arguments['operation'])
    raise MenuError('unknown_menu_action')


def register_parser(subparsers):
    parser = subparsers.add_parser('interactions', help='guarded local menu and human input custody')
    commands = parser.add_subparsers(dest='interaction_command', required=True)
    for action in ('configure', 'inspect', 'run', 'reconcile', 'takeover', 'return'):
        command = commands.add_parser(action)
        command.add_argument('--profile', required=True)
        command.add_argument('--json', dest='as_json', action='store_true')
        if action not in ('inspect', 'reconcile'):
            command.add_argument('--operator', action='store_true')
        if action == 'configure':
            command.add_argument('--binding-file', required=True, help='private host-selected menu-only binding JSON')
        if action in ('run', 'reconcile'):
            command.add_argument('--operation', required=True)
        if action in ('run', 'takeover', 'return'):
            command.add_argument('--token', required=True, help='exact ownership token JSON from inspect')
        if action in ('configure', 'takeover', 'return'):
            command.add_argument('--reason', required=True)
    return parser


def run(args, root):
    try:
        arguments = dict(profile=args.profile)
        for name in ('operation', 'reason'):
            if getattr(args, name, None) is not None:
                arguments[name] = getattr(args, name)
        if getattr(args, 'token', None):
            arguments['token'] = json.loads(args.token)
        if args.interaction_command == 'configure':
            from .guarded_interactions import _private
            path = Path(args.binding_file)
            _private(path)
            arguments['binding'] = json.loads(path.read_text())
        value = execute(args.interaction_command, arguments, root, operator=getattr(args, 'operator', False))
        print(json.dumps(value, sort_keys=True))
        return 0 if value.get('state') not in ('uncertain', 'held') else 5
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(json.dumps(dict(error=dict(code=getattr(exc, 'code', 'guarded_interaction_refused'), message=str(exc)))))
        return 5


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wake-root', type=Path, required=True)
    commands = parser.add_subparsers(dest='command', required=True)
    register_parser(commands)
    args = parser.parse_args(argv)
    return run(args, args.wake_root)


if __name__ == '__main__':
    raise SystemExit(main())
