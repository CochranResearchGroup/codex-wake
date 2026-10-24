"""Resolve host-approved lifecycle defaults and objective overrides before effects."""
from datetime import timedelta
import hashlib
import json
from pathlib import Path

from .records import WakeError, parse_timestamp


def effective_configuration(config, thread_id, profile_name, caller_thread_id=None, *, native_self=False):
    from .session_permissions import profile_granted
    try:
        profile = config['profiles'][profile_name]
        policy = config['continuations'][thread_id]
        if caller_thread_id and (caller_thread_id != thread_id or not profile_granted(
                config, profile_name, caller_thread_id, native_self=native_self)):
            raise ValueError('ungranted caller')
        if not policy['approval'] or not policy['objective']:
            raise ValueError('unapproved objective')
        defaults = config.get('lifecycle_defaults', {})
        overrides = policy.get('configuration', {})
        fields = {'handoff_writer', 'preflight_reviewer', 'session_token_limit',
                  'session_time_limit_seconds', 'objective_token_limit',
                  'objective_time_limit_seconds', 'max_correction_cycles'}
        if (not isinstance(defaults, dict) or not isinstance(overrides, dict)
                or set(defaults) - fields or set(overrides) - fields):
            raise ValueError('unknown configuration')
        effective = {**defaults, **overrides}
        for key in fields - {'handoff_writer', 'preflight_reviewer'}:
            value = effective[key]
            if type(value) is not int or value < 0 or (value == 0 and key != 'max_correction_cycles'):
                raise ValueError('invalid limit')
        if effective['max_correction_cycles'] > 2:
            raise ValueError('correction limit exceeds approved maximum')
        for key in ('handoff_writer', 'preflight_reviewer'):
            selection = effective[key]
            path = Path(selection['path'])
            if not path.is_absolute() or not isinstance(selection['name'], str) or not selection['name'].strip():
                raise ValueError('instruction identity missing')
            path = path.resolve(strict=True)
            content = path.read_bytes()
            instructions = content.decode('utf-8')
            if not instructions.strip():
                raise ValueError('empty instructions')
            effective[key] = dict(name=selection['name'], path=str(path),
                sha256=hashlib.sha256(content).hexdigest(), instructions=instructions)
        if 'strict_execution' in profile:
            from .strict_policy import strict_policy
            effective['strict_execution']=strict_policy(profile['strict_execution'],effective)
        started = parse_timestamp(policy['started_at'])
        effective.update(objective=policy['objective'], source_thread_id=thread_id,
            profile=profile_name, started_at=policy['started_at'],
            objective_deadline=(started + timedelta(seconds=effective['objective_time_limit_seconds'])).isoformat())
        identity = {key: value for key, value in effective.items()
                    if key not in ('source_thread_id', 'profile')}
        effective['revision'] = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
        return effective
    except (OSError, UnicodeError, KeyError, TypeError, ValueError, OverflowError):
        raise WakeError('lifecycle configuration or selected instructions unavailable; no substitution permitted') from None


def configuration_command(args, root):
    from .sessions_cli import emit
    try:
        config = json.loads(Path(args.profiles).read_text())
        if config.get('profiles', {}).get(args.profile, {}).get('refresh_mode') == 'shared_mcp_idle':
            from .shared_refresh import configuration
            if args.apply_budget_authorization:
                raise WakeError('shared refresh never authorizes a budget reset or extension')
            emit(configuration(config, args.profile, args.thread_id, args.caller_thread_id), args.as_json)
            return 0
        effective = effective_configuration(config, args.thread_id, args.profile, args.caller_thread_id)
        from .lifecycle_budget import objective_identity, trusted_upper
        from .objective_ledger import ObjectiveLedger
        identity = objective_identity(config['continuations'][args.thread_id])
        path = Path(root) / 'objective-ledgers' / (hashlib.sha256(identity.encode()).hexdigest() + '.json')
        if args.apply_budget_authorization:
            authorization = config['continuations'][args.thread_id].get('budget_authorization', {})
            if (args.caller_thread_id or authorization.get('revision') != effective['revision']
                    or not authorization.get('approval') or authorization.get('action') not in ('extend', 'reset')):
                raise WakeError('exact host operator budget authorization unavailable')
            selected = {key: value for key, value in effective.items()
                        if key not in ('source_thread_id', 'profile')}
            ledger = ObjectiveLedger(root, identity)
            operation = ledger.extend if authorization['action'] == 'extend' else ledger.reset
            operation(selected, authorization['approval'], now=trusted_upper())
        effective['objective_budget'] = (ObjectiveLedger(root, identity).inspect(now=trusted_upper())
                                         if path.exists() else None)
        if effective.get('strict_execution'):
            from .strict_runtime import location,read_execution
            directory=location(root,identity)
            effective['execution_layout']=dict(home=str(directory/'home'),app_server='unix://'+str(directory/'app-server.sock'))
            effective['objective_execution']=read_execution(root,identity)
    except (OSError, ValueError, RuntimeError, WakeError) as exc:
        emit({'error': {'code': 'configuration_unavailable', 'message': str(exc)}}, args.as_json)
        return 2
    emit(effective, args.as_json)
    return 0
