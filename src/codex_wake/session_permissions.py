"""Own-session defaults beneath native identity and host effect-scope checks."""
from .records import WakeError


def profile_granted(config, profile_name, caller_thread_id, *, native_self=False):
    """Explicit caller entries override the native-self default, including [].

    native_self is internal evidence from the private MCP transport, never an
    agent argument or an environment-derived claim. It grants no profile scope,
    objective allowance, or permission to act on another session.
    """
    callers = config.get('callers', {})
    if not isinstance(callers, dict):
        raise WakeError('session caller permissions are malformed')
    if caller_thread_id in callers:
        grants = callers[caller_thread_id]
        if not isinstance(grants, list) or any(not isinstance(x, str) for x in grants):
            raise WakeError('session caller permissions are malformed')
        return profile_name in grants
    defaults = config.get('session_permissions', {})
    if (not isinstance(defaults, dict) or set(defaults) - {'self_access'}
            or type(defaults.get('self_access', True)) is not bool):
        raise WakeError('default session permissions are malformed')
    return native_self is True and defaults.get('self_access', True)


def native_request(packet):
    """Private child RPC from CommandRunner after native attestation.

    This is not an authentication protocol for hostile stdin or same-UID code,
    just as native MCP metadata relies on ownership of its private transport.
    There is no public CLI switch or agent argument for supplying this evidence.
    Keeping this work in a child preserves lock/read/RPC timeout enforcement.
    """
    import hashlib
    import json
    from pathlib import Path
    from types import SimpleNamespace
    from .goal_supervision import _private
    from .shared_refresh import configuration, command, MODE, CLIENT_MODE
    from .wake_control import delivery_guard
    verb = packet.get('verb')
    try:
        if verb not in ('configuration', 'refresh'):
            raise WakeError('unsupported native self operation')
        arguments, binding = packet['arguments'], packet['binding']
        if (not isinstance(binding, dict) or set(binding) != {'thread_id', 'turn_id', 'call_id'}
                or any(not isinstance(x, str) or not x for x in binding.values())
                or arguments['thread_id'] != arguments['caller_thread_id']
                or arguments['thread_id'] != binding['thread_id']):
            raise WakeError('private native self binding mismatch')
        policy = Path(packet['profiles']).absolute()
        _private(policy)
        if policy != policy.resolve():
            raise WakeError('lifecycle policy must be canonical')
        config = json.loads(policy.read_text())
        profile = config['profiles'][arguments['profile']]
        if profile.get('refresh_mode') not in (MODE, CLIENT_MODE):
            return {'_legacy_session_profile': True}, False
        value = configuration(config, arguments['profile'], arguments['thread_id'],
                              arguments['caller_thread_id'], native_self=True)
        if verb == 'configuration':
            return value, False
        workspace = Path(profile['cwd']).resolve(strict=True)
        checkpoint = (workspace / arguments['checkpoint']).resolve(strict=True)
        checkpoint.relative_to(workspace)
        content = checkpoint.read_bytes()
        if hashlib.sha256(content).hexdigest() != arguments['checkpoint_sha256']:
            raise WakeError('checkpoint hash changed; original checkpoint must be preserved')
        options = dict(arguments)
        options['resource'] = options.pop('resources')
        options.update(profiles=str(policy), as_json=True)
        options.setdefault('rollback', False)
        emitted = []
        root = Path(packet['root']).absolute()
        if root != root.resolve():
            raise WakeError('refresh root must be canonical')
        root.mkdir(mode=0o700, parents=True, exist_ok=True)
        _private(root, directory=True)
        with delivery_guard(root):
            code = command(SimpleNamespace(**options), root, config, profile,
                checkpoint, content, native_self=True,
                emit_result=lambda item, _as_json: emitted.append(item))
        return emitted[-1], code != 0
    except (OSError, ValueError, TypeError, KeyError, AttributeError, WakeError) as exc:
        return {'error': {'code': 'configuration_unavailable' if verb == 'configuration'
                         else 'shared_refresh_unavailable', 'message': str(exc)}}, True


def main():
    import json
    import sys
    try:
        raw = sys.stdin.buffer.read(65537)
        if len(raw) > 65536:
            raise ValueError('private self request exceeds 64 KiB')
        packet = json.loads(raw)
        if not isinstance(packet, dict):
            raise ValueError('private self request must be an object')
        value, failed = native_request(packet)
    except (ValueError, TypeError) as exc:
        value, failed = {'error': {'code': 'invalid_argument', 'message': str(exc)}}, True
    print(json.dumps(value))
    return 2 if failed else 0


if __name__ == '__main__':
    raise SystemExit(main())
