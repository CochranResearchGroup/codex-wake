"""Public governor controls shared by local operators and machine transports."""
from functools import partial
import json

from .managed_inventory import InventoryError


VERBS = ('status', 'activate', 'extend', 'reset', 'disable', 'resume', 'advisory')


def schemas():
    text = {'type': 'string', 'minLength': 1, 'maxLength': 4096}
    positive = {'type': 'integer', 'minimum': 1}
    common = dict(selector=text, endpoint=text)
    result = {}
    for verb in VERBS:
        properties = dict(common)
        required = []
        if verb != 'status':
            properties.update(request_id=text, expected_revision={'type': 'integer', 'minimum': 0})
        if verb in ('activate', 'reset'):
            properties.update(token_limit=positive, time_limit_seconds=positive)
        if verb == 'activate':
            required = ['token_limit', 'time_limit_seconds']
        if verb == 'extend':
            properties.update(add_tokens=positive, add_seconds=positive)
        if verb in ('extend', 'reset'):
            properties['resume'] = {'type': 'boolean'}
        result[verb] = dict(type='object', properties=properties, required=required, additionalProperties=False)
    return result


def execute(verb, arguments, root, *, principal=None):
    from .governor import execute as governor
    if principal is None and verb == 'activate':
        # Same-user private API has no native model metadata. It may engage or
        # tighten an exactly resolved owned task, never acquire operator powers.
        import os
        from .local_sessions import resolve
        from .session_permissions import Principal
        selector = arguments.get('selector') or os.environ.get('CODEX_THREAD_ID')
        if not selector:
            raise InventoryError('invalid_argument', 'Choose a session selector for governor activation.')
        row = resolve(root, selector, endpoint=arguments.get('endpoint', 'unix://'))
        principal = Principal(row['thread_id'])
    return governor(root, verb, dict(arguments), principal=principal)


def definitions():
    descriptions = {
        'status': 'Show task limits, consumption and actual enforcement readiness without activating work.',
        'activate': 'Activate or tighten own-task time and token limits without per-session provisioning.',
        'extend': 'Increase an existing allowance under qualified operator authority; retain usage.',
        'reset': 'Start a new authorized budget window, preserving lifetime accounting and stop history.',
        'disable': 'Disable this governor under qualified operator authority; do not resume work.',
        'resume': 'Resume the exact affected task only when its allowance and enforcement are qualified.',
        'advisory': 'Explicitly select advisory operation under qualified operator authority.',
    }
    return {'local.governor.' + verb: ('wake_governor_' + verb, descriptions[verb], schema,
            partial(execute, verb), verb == 'status') for verb, schema in schemas().items()}


def register_parser(subparsers):
    parser = subparsers.add_parser('governor', help='inspect and control task limits; current session is automatic')
    commands = parser.add_subparsers(dest='governor_verb', required=True)
    for verb, schema in schemas().items():
        command = commands.add_parser(verb, help=definitions()['local.governor.' + verb][1])
        command.add_argument('selector', nargs='?', help='owned thread selector; defaults to CODEX_THREAD_ID')
        command.add_argument('--json', action='store_true', help='emit the complete structured status or result')
        for name, value in schema['properties'].items():
            if name == 'selector':
                continue
            options = dict(default=None)
            if value['type'] == 'integer':
                options['type'] = int
            elif value['type'] == 'boolean':
                options = dict(action='store_true', default=None)
            options['required'] = name in schema['required']
            command.add_argument('--' + name.replace('_', '-'), **options)


def command(args, root):
    from jsonschema import Draft202012Validator
    from .governor import local_operator_principal
    verb = args.governor_verb
    arguments = {key: getattr(args, key) for key in schemas()[verb]['properties']
                 if getattr(args, key, None) is not None}
    try:
        if not Draft202012Validator(schemas()[verb]).is_valid(arguments):
            raise InventoryError('invalid_argument', 'Use positive limits and a valid request identity.')
        result = execute(verb, arguments, root, principal=local_operator_principal())
        if args.json:
            print(json.dumps(result, sort_keys=True))
        else:
            print(render(result))
        return 2 if result.get('error') or result.get('status') in ('failed', 'held') else 0
    except (ValueError, OSError, InventoryError) as error:
        value = dict(status='failed', error=dict(code=getattr(error, 'code', 'governor_unavailable'), message=str(error)))
        print(json.dumps(value) if args.json else 'Governor unavailable: ' + str(error))
        return 2


def render(value):
    """Readable operator view; machine clients always retain the complete result."""
    lines = ['Governor: ' + str(value.get('state', 'unknown'))]
    for key in ('scope', 'usage', 'limits', 'deadline', 'watcher', 'reason'):
        item = value.get(key)
        if item is not None:
            lines.append(key.replace('_', ' ').capitalize() + ': ' +
                         (json.dumps(item, sort_keys=True) if isinstance(item, (dict, list)) else str(item)))
    actions = value.get('actions')
    if actions:
        lines.append('Actions: ' + (', '.join(actions) if isinstance(actions, list) else json.dumps(actions)))
    return '\n'.join(lines)


def protected_execute(root, verb, arguments, actor, *, authorize):
    """OAuth owner controls require both operator provenance and exact target scope."""
    from jsonschema import Draft202012Validator
    from .controller_http import permitted
    from .controller_auth import AuthError
    from .local_sessions import resolve
    from .session_permissions import Principal
    from .governor import local_operator_principal
    if not Draft202012Validator(schemas()[verb]).is_valid(arguments):
        raise InventoryError('invalid_argument', 'Arguments do not match the governor operation schema.')
    selector = arguments.get('selector')
    if not selector:
        raise InventoryError('invalid_argument', 'Remote governor controls require an explicit session selector.')
    row = resolve(root, selector, endpoint=arguments.get('endpoint', 'unix://'))
    target = dict(row['target'], thread_id=row['thread_id'])
    actor = authorize()
    # A host-wide target grant is insufficient for task accounting or renewal.
    if not any(scope.get('thread_id') == row['thread_id'] and
               all(target.get(key) == value for key, value in scope.items()) for scope in actor.targets):
        raise AuthError('insufficient_scope')
    if not permitted(actor, target):
        raise AuthError('insufficient_scope')
    operator = actor.principal_kind == 'owner' and 'admin' in actor.scopes
    if verb in ('extend', 'reset', 'disable', 'advisory') and not operator:
        raise AuthError('insufficient_scope', 'An authenticated owner with task-scoped admin authority is required.')
    principal = local_operator_principal() if operator else Principal(row['thread_id'])
    return execute(verb, dict(arguments, selector='thread:' + row['thread_id']), root, principal=principal)
