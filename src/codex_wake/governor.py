"""Ordinary-session controls over Wake's existing supervision authority.

The local operator marker is a private adapter input, never a JSON role field.
Remote adapters must supply a verified session Principal and cannot loosen limits.
"""
import json
import os
from pathlib import Path

from . import goal_supervision as supervision
from .session_permissions import Principal


class _LocalOperator:
    pass


_LOCAL_OPERATOR = _LocalOperator()


def local_operator_principal():
    """Trusted local CLI/native operator adapter only; never expose as an RPC."""
    return _LOCAL_OPERATOR


def _normalize(receipt, thread):
    controller = receipt.get('controller', {})
    disabled = receipt.get('governor_enabled') is False
    reason = receipt.get('reason')
    exhausted = reason in ('token_limit', 'time_limit', 'token_limit_reached', 'deadline_reached', 'allocation_exhausted', 'continuation_held')
    engagement = receipt.get('engagement', {})
    state = ('advisory' if disabled and receipt.get('governor_mode') == 'advisory' else 'disabled' if disabled else 'limit_reached' if exhausted else
             'enforced' if engagement.get('engaged') else 'disconnected')
    used = receipt.get('used_tokens')
    limit = receipt.get('token_limit')
    return dict(schema_version=1, state=state,
        scope=dict(thread_id=thread, allocation_id=receipt.get('allocation_id'),
            members=receipt.get('accounting', {}).get('member_thread_ids', [thread]),
            kind='shared' if len(receipt.get('accounting', {}).get('member_thread_ids', [thread])) > 1 else 'task'),
        usage=dict(used_tokens=used, lifetime_used_tokens=receipt.get('lifetime_used_tokens'),
            remaining_tokens=max(0, limit-used) if type(used) is int and type(limit) is int else None,
            elapsed_seconds=receipt.get('elapsed_upper_seconds'), accounting=receipt.get('accounting', {})),
        limits=dict(token_limit=limit, time_limit_seconds=receipt.get('time_limit_seconds')),
        deadline=receipt.get('deadline'), watcher=controller,
        revision=receipt.get('budget_revision', receipt.get('enrollment_revision', 0)),
        actions=['activate'] if reason == 'not_enrolled' else ['extend', 'reset', 'disable', 'resume', 'advisory'],
        reason=reason, owner_receipt=receipt)


def execute(root, verb, arguments, *, principal=None):
    if not isinstance(arguments, dict):
        raise ValueError('governor arguments must be an object')
    allowed = {'selector', 'endpoint', 'policy', 'request_id', 'expected_revision'}
    allowed |= {'token_limit', 'time_limit_seconds'} if verb in ('activate', 'reset') else set()
    allowed |= {'add_tokens', 'add_seconds'} if verb == 'extend' else set()
    allowed |= {'resume'} if verb in ('extend', 'reset') else set()
    if verb not in ('status', 'activate', 'extend', 'reset', 'disable', 'resume', 'advisory') or set(arguments)-allowed:
        raise ValueError('unsupported governor verb or arguments; operator fields never authenticate authority')
    selector = arguments.get('selector') or os.environ.get('CODEX_THREAD_ID')
    if not selector:
        raise ValueError('choose a session selector, or run inside a session with CODEX_THREAD_ID')
    from .local_sessions import resolve
    row = resolve(root, selector, endpoint=arguments.get('endpoint', 'unix://'))
    thread = row['thread_id']
    if principal is not None and principal is not _LOCAL_OPERATOR:
        if not isinstance(principal, Principal) or principal.role != 'session' or principal.subject != thread:
            raise ValueError('verified exact-session principal required')
    path = Path(root) / 'goal-supervision' / (supervision._name(thread)+'.json')
    if not path.exists():
        receipt = dict(thread_id=thread, reason='not_enrolled')
    else:
        supervision._private(path)
        retained = json.loads(path.read_text())
        receipt = supervision.show(root, retained['policy_path'], thread,
            permission_principal=principal if isinstance(principal, Principal) else None)
    if verb == 'status':
        return _normalize(receipt, thread)
    if principal is None:
        raise ValueError('verified session identity or authenticated local operator required')
    expected = arguments.get('expected_revision')
    if expected is not None and (type(expected) is not int or expected != _normalize(receipt, thread)['revision']):
        raise ValueError('governor revision changed; inspect current status')
    operator = principal is _LOCAL_OPERATOR
    if verb != 'activate' and not operator:
        raise ValueError('authenticated operator required to extend, reset, disable, resume or choose advisory')
    if arguments.get('policy') is not None and not operator:
        raise ValueError('only the local operator may select an existing policy')
    if verb == 'activate':
        from .local_self_limits import policy_for
        from .self_limits import local_execute
        policy = retained['policy_path'] if path.exists() else policy_for(root, row, arguments.get('policy'))
        limits = {key: arguments.get(key) for key in ('token_limit', 'time_limit_seconds')}
        for value in limits.values():
            if type(value) is not int or value <= 0:
                raise ValueError('positive token_limit and time_limit_seconds required')
        result = local_execute(root, policy, 'set', limits, thread_id=thread, activation_baseline=True)
        return _normalize(result, thread)
    if not path.exists():
        raise ValueError('activate this session before changing its governor')
    authority = Principal(thread, 'operator')
    if verb in ('disable', 'advisory'):
        from .goal_governance import change
        result = change(root, thread, enabled=False, principal=authority, mode='advisory' if verb == 'advisory' else None)
        return _normalize(result, thread)
    if verb in ('extend', 'reset'):
        result = _renew(root, retained, verb, arguments, authority)
        current = supervision.show(root, retained['policy_path'], thread)
        normalized = _normalize(current, thread)
        normalized['operation'] = result
        return normalized
    if verb == 'resume':
        return _resume(root, retained, arguments, authority)
    raise ValueError('unsupported governor action')


def _renew(root, receipt, verb, arguments, principal):
    from . import goal_renewal as renewal
    from uuid import uuid4
    request = arguments.get('request_id') or uuid4().hex
    identifier = renewal._id(receipt['thread_id'], request)
    directory = supervision._directory(root)
    path = renewal._journal_path(directory, identifier)
    intent = {key: value for key, value in arguments.items() if key not in ('selector', 'endpoint', 'expected_revision')}
    if path.exists():
        journal = renewal._read(path)
        if journal.get('governor_intent') != dict(verb=verb, arguments=intent):
            raise ValueError('request_id already names a different governor operation')
        packet = journal
    else:
        if verb == 'extend':
            adds = [arguments.get('add_tokens', 0), arguments.get('add_seconds', 0)]
            if any(type(value) is not int or value < 0 for value in adds) or not any(adds):
                raise ValueError('extension requires positive add_tokens or add_seconds')
            tokens = receipt['token_limit'] + adds[0]
            deadline = receipt['deadline'] + adds[1]
            window = dict(deadline=deadline)
        else:
            tokens = arguments.get('token_limit', receipt['token_limit'])
            seconds = arguments.get('time_limit_seconds', receipt['time_limit_seconds'])
            window = dict(remaining_seconds=seconds)
        packet = renewal.propose(root, receipt['policy_path'], receipt['thread_id'],
            principal=principal, operation_id=request, mode=verb, token_limit=tokens,
            expires_at=renewal._now()+300, shared=False,
            resume=arguments.get('resume', False), **window)
        journal = renewal._read(path)
        journal['governor_intent'] = dict(verb=verb, arguments=intent)
        supervision._save(path, journal)
    return renewal.apply(root, receipt['policy_path'], receipt['thread_id'], packet['proposal_id'],
        principal=principal, expected_fingerprint=packet['fingerprint'], explicit=True)


def _resume(root, receipt, arguments, principal):
    # Resume consumes the existing approved renewal, never creates allowance.
    from . import goal_renewal as renewal
    request = arguments.get('request_id')
    if not request:
        raise ValueError('resume requires request_id of an explicitly approved also-resume renewal')
    path = renewal._journal_path(supervision._directory(root), renewal._id(receipt['thread_id'], request))
    journal = renewal._read(path)
    if not journal['proposal'].get('resume'):
        raise ValueError('this operation did not authorize continuation; extend/reset with resume explicitly')
    result = renewal.apply(root, receipt['policy_path'], receipt['thread_id'], journal['proposal_id'],
        principal=principal, expected_fingerprint=journal['fingerprint'], explicit=True)
    current = supervision.show(root, receipt['policy_path'], receipt['thread_id'])
    normalized = _normalize(current, receipt['thread_id'])
    normalized['operation'] = result
    return normalized
