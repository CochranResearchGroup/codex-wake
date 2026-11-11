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
    from .governor import execute as governor, local_operator_principal
    from .governor_context import configured
    root, host_policy = configured(root)
    arguments = dict(arguments)
    if host_policy is not None:
        if principal is local_operator_principal():
            arguments['policy'] = str(host_policy)
        elif principal is not None:
            from .governor import native_principal
            from .session_permissions import Principal
            if isinstance(principal, Principal):
                principal = native_principal(principal.subject, policy=host_policy, principal=principal)
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
        if host_policy is not None:
            from .governor import native_principal
            principal = native_principal(row['thread_id'], policy=host_policy, principal=principal)
    result = governor(root, verb, dict(arguments), principal=principal)
    requested_resume = verb == 'resume' or arguments.get('resume') is True
    held = (verb == 'activate' and result.get('state') != 'enforced' or
            requested_resume and result.get('operation', {}).get('resumed') is not True)
    result['status'] = 'held' if held else 'completed'
    return result


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
    """Readable operator view; machine clients retain the complete structured result."""
    import math
    from datetime import datetime
    def number(item):
        return str(item) if type(item) in (int, float) and math.isfinite(item) else 'unknown'
    def duration(item):
        if type(item) not in (int, float) or not math.isfinite(item):
            return 'unknown'
        seconds = max(0, int(item))
        hours, seconds = divmod(seconds, 3600)
        minutes, seconds = divmod(seconds, 60)
        return ' '.join(([str(hours) + 'h'] if hours else []) +
                        ([str(minutes) + 'm'] if minutes else []) + [str(seconds) + 's'])
    scope, usage, limits = (value.get(key) or {} for key in ('scope', 'usage', 'limits'))
    lines = ['Governor: ' + str(value.get('state', 'unknown')),
             'Task: ' + str(scope.get('thread_id', 'unknown'))]
    lines.append('Tokens: ' + number(usage.get('used_tokens')) + ' of ' + number(limits.get('token_limit')) +
                 ' used; ' + number(usage.get('remaining_tokens')) + ' tokens remaining')
    elapsed = usage.get('elapsed_seconds')
    remaining = usage.get('remaining_seconds')
    if remaining is None and type(elapsed) in (int, float) and type(limits.get('time_limit_seconds')) in (int, float):
        remaining = max(0, limits['time_limit_seconds'] - elapsed)
    lines.append('Time: ' + duration(elapsed) + ' elapsed; ' + duration(remaining) + ' remaining')
    basis = value.get('owner_receipt', {}).get('time_basis')
    deadline = value.get('deadline')
    if basis == 'authenticated_host_counter':
        lines.append('Deadline: host elapsed counter; wall-clock deadline unavailable')
    elif type(deadline) in (int, float) and math.isfinite(deadline):
        try:
            lines.append('Deadline: ' + datetime.fromtimestamp(deadline).astimezone().strftime('%Y-%m-%d %H:%M:%S %Z'))
        except (ValueError, OSError, OverflowError):
            lines.append('Deadline: unavailable')
    shared = limits.get('shared')
    if isinstance(shared, dict):
        lines.append('Shared allowance: ' + number(shared.get('used_tokens')) + ' of ' +
                     number(shared.get('token_limit')) + ' tokens used; also applies to this task')
    if scope.get('limiting_scope'):
        lines.append('Limiting scope: ' + str(scope['limiting_scope']))
    watcher = value.get('watcher') or {}
    lines.append('Watcher: ' + ('fresh' if watcher.get('fresh') else 'unavailable or unverified'))
    if value.get('reason'):
        lines.append('Reason: ' + str(value['reason']).replace('_', ' '))
    actions = value.get('actions')
    if isinstance(actions, list) and actions:
        lines.append('Actions: ' + ', '.join(str(action) for action in actions))
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
