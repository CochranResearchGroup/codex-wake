"""Ordinary-session controls over Wake's existing supervision authority.

The local operator marker is a private adapter input, never a JSON role field.
Remote adapters must supply a verified session Principal and cannot loosen limits.
"""
import json
import os
import time
from pathlib import Path

from . import goal_supervision as supervision
from .session_permissions import Principal


class _LocalOperator:
    pass


_LOCAL_OPERATOR = _LocalOperator()
_STATUS_ROWS = {}


class _NativePrincipal:
    def __init__(self, principal, policy):
        self.principal=principal
        self.policy=policy


def native_principal(thread, *, policy=None, principal=None):
    """Private verified native adapter binding; never deserialize from JSON."""
    actor=principal or Principal(thread)
    if not isinstance(actor,Principal) or actor.subject!=thread or actor.role!='session':
        raise ValueError('verified exact native session principal required')
    return _NativePrincipal(actor, str(Path(policy).absolute()) if policy is not None else None)



def local_operator_principal():
    """Trusted local CLI/native operator adapter only; never expose as an RPC."""
    return _LOCAL_OPERATOR


def _normalize(receipt, thread):
    controller = receipt.get('controller', {})
    disabled = receipt.get('governor_enabled') is False or receipt.get('task_governor_enabled') is False
    reason = receipt.get('reason')
    exhausted = reason in ('token_limit', 'time_limit', 'token_limit_reached', 'deadline_reached', 'allocation_exhausted', 'continuation_held', 'task_exhausted')
    engagement = receipt.get('engagement', {})
    state = ('advisory' if disabled and receipt.get('governor_mode') == 'advisory' else 'disabled' if disabled else 'limit_reached' if exhausted else
             'enforced' if engagement.get('engaged') else 'disconnected')
    elapsed = receipt.get('elapsed_upper_seconds')
    if elapsed is None and all(type(receipt.get(key)) in (int, float) for key in ('started_upper', 'started_boottime', 'time_origin')):
        elapsed = max(0, receipt['started_upper']-receipt['time_origin']+
            time.clock_gettime(time.CLOCK_BOOTTIME)-receipt['started_boottime'])
    if elapsed is not None and receipt.get('time_basis')=='authenticated_host_counter' and receipt.get('task_window'):
        elapsed=max(0,elapsed-receipt['task_window']['time_origin'])
    used = receipt.get('used_tokens')
    limit = receipt.get('token_limit')
    return dict(schema_version=1, state=state,
        scope=dict(thread_id=thread, allocation_id=receipt.get('allocation_id'),
            members=receipt.get('accounting', {}).get('member_thread_ids', [thread]),
            kind='task' if receipt.get('task_window') else 'shared' if len(receipt.get('accounting', {}).get('member_thread_ids', [thread])) > 1 else 'task',
            limiting_scope=receipt.get('limiting_scope'),shared=receipt.get('shared_limits')),
        usage=dict(used_tokens=used, lifetime_used_tokens=receipt.get('lifetime_used_tokens'),
            remaining_tokens=max(0, limit-used) if type(used) is int and type(limit) is int else None,
            elapsed_seconds=elapsed, accounting=receipt.get('accounting', {})),
        limits=dict(token_limit=limit, time_limit_seconds=receipt.get('time_limit_seconds'),shared=receipt.get('shared_limits')),
        deadline=receipt.get('deadline'), watcher=controller,
        revision=receipt.get('budget_revision', receipt.get('enrollment_revision', 0)),
        actions=['activate'] if reason == 'not_enrolled' else ['activate', 'extend', 'reset', 'resume'] if disabled else ['extend', 'reset', 'disable', 'resume', 'advisory'],
        reason=reason, owner_receipt=receipt)


def _execute(root, verb, arguments, *, principal=None):
    host_policy=None
    if isinstance(principal,_NativePrincipal):
        host_policy=principal.policy
        principal=principal.principal
    if not isinstance(arguments, dict):
        raise ValueError('governor arguments must be an object')
    allowed = {'selector', 'endpoint', 'policy', 'request_id', 'expected_revision'}
    allowed |= {'token_limit', 'time_limit_seconds'} if verb in ('activate', 'reset') else set()
    allowed |= {'add_tokens', 'add_seconds'} if verb == 'extend' else set()
    allowed |= {'resume'} if verb in ('extend', 'reset') else set()
    if verb not in ('status', 'activate', 'extend', 'reset', 'disable', 'resume', 'advisory') or set(arguments)-allowed:
        raise ValueError('unsupported governor verb or arguments; operator fields never authenticate authority')
    selector = arguments.get('selector') or os.environ.get('CODEX_THREAD_ID')
    if not isinstance(selector, str) or not selector:
        raise ValueError('choose a session selector, or run inside a session with CODEX_THREAD_ID')
    from .local_sessions import resolve
    row = None
    if verb == 'status':
        exact = selector[7:] if selector.startswith('thread:') else selector
        try:
            name = supervision._name(exact)
            retained_path = Path(root) / 'goal-supervision' / (name+'.json')
            if retained_path.exists():
                supervision._private(retained_path)
                retained_status = json.loads(retained_path.read_text())
                if retained_status.get('thread_id') != exact:
                    raise ValueError('retained governor target identity changed')
                row = dict(thread_id=exact)
        except ValueError:
            # Only a non-UUID selector may fall back to inventory discovery.
            from uuid import UUID
            try: UUID(exact)
            except ValueError: pass
            else: raise
    if row is None:
        row = _resolve_status(root, selector, arguments.get('endpoint', 'unix://')) if verb == 'status' else resolve(root, selector, endpoint=arguments.get('endpoint', 'unix://'))
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
        if host_policy is not None and Path(retained['policy_path']).absolute()!=Path(host_policy):
            raise ValueError('retained governor host policy differs from authenticated native binding; reconcile without renewing')
        receipt = supervision.show(root, retained['policy_path'], thread,
            permission_principal=Principal(thread,'operator') if principal is _LOCAL_OPERATOR else principal)
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
    if verb == 'activate' and path.exists() and (receipt.get('governor_enabled') is False or receipt.get('task_governor_enabled') is False):
        if not operator:
            raise ValueError('authenticated operator required to reactivate a disabled governor')
        from .goal_governance import change
        change(root, thread, enabled=True, principal=Principal(thread, 'operator'),task_only=bool(receipt.get('task_window')))
        return _normalize(supervision.show(root,retained['policy_path'],thread,permission_principal=Principal(thread,'operator')), thread)
    if verb == 'activate':
        from .local_self_limits import policy_for
        from .self_limits import local_execute
        policy = retained['policy_path'] if path.exists() else policy_for(root, row, host_policy or arguments.get('policy'))
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
        result = change(root, thread, enabled=False, principal=authority, mode='advisory' if verb == 'advisory' else None,task_only=bool(receipt.get('task_window')))
        return _normalize(result, thread)
    if verb in ('extend', 'reset'):
        result = _renew(root, retained, verb, arguments, authority)
        current = supervision.show(root, retained['policy_path'], thread,permission_principal=authority)
        normalized = _normalize(current, thread)
        normalized['operation'] = result
        if result.get('resumed') is False and result.get('resume_state'):normalized['reason']=result['resume_state']
        return normalized
    if verb == 'resume':
        return _resume(root, retained, arguments, authority)
    raise ValueError('unsupported governor action')


def _renew(root, receipt, verb, arguments, principal):
    from . import goal_renewal as renewal
    from uuid import uuid4
    request = arguments.get('request_id') or uuid4().hex
    if receipt.get('task_window'):
        result=renewal.renew_task_window(root,receipt['policy_path'],receipt['thread_id'],
            principal=principal,operation_id=request,mode=verb,
            token_limit=arguments.get('token_limit'),time_limit_seconds=arguments.get('time_limit_seconds'),
            add_tokens=arguments.get('add_tokens',0),add_seconds=arguments.get('add_seconds',0),resume=arguments.get('resume',False))
        if arguments.get('resume') and result.get('resume_state')=='awaiting_first_poll':
            result.update(renewal.resume_existing(root,receipt['policy_path'],receipt['thread_id'],
                principal=principal,operation_id=request+':resume'))
        return result
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
    from .goal_renewal import resume_existing
    from uuid import uuid4
    result = resume_existing(root, receipt['policy_path'], receipt['thread_id'],
        principal=principal, operation_id=arguments.get('request_id') or uuid4().hex)
    normalized = _normalize(supervision.show(root, receipt['policy_path'], receipt['thread_id'],permission_principal=principal), receipt['thread_id'])
    normalized['operation'] = result
    if result.get('resumed') is False and result.get('resume_state'):normalized['reason']=result['resume_state']
    return normalized


def execute(root, verb, arguments, *, principal=None):
    """Execute one qualified intent; request IDs reconcile the owner receipt."""
    if verb == 'status' or not isinstance(arguments, dict) or arguments.get('request_id') is None:
        return _execute(root, verb, arguments, principal=principal)
    identifier = arguments['request_id']
    if not isinstance(identifier, str) or not identifier or len(identifier) > 256:
        raise ValueError('bounded nonempty request_id required')
    if principal is None:
        raise ValueError('verified session identity or authenticated local operator required')
    from .local_sessions import resolve
    selector = arguments.get('selector') or os.environ.get('CODEX_THREAD_ID')
    if not isinstance(selector, str) or not selector:
        raise ValueError('choose a session selector, or run inside a session with CODEX_THREAD_ID')
    row = resolve(root, selector, endpoint=arguments.get('endpoint', 'unix://'))
    thread = row['thread_id']
    actor=principal.principal if isinstance(principal,_NativePrincipal) else principal
    if actor is not _LOCAL_OPERATOR and (not isinstance(actor, Principal) or actor.role != 'session' or actor.subject != thread):
        raise ValueError('verified exact-session principal required')
    import hashlib
    digest = hashlib.sha256(json.dumps(dict(verb=verb, arguments=arguments), sort_keys=True, default=str).encode()).hexdigest()
    directory = supervision._directory(root)
    path = directory / (supervision._name(thread)+'.json')
    with supervision._lock(directory, 'governor-request-'+supervision._name(thread)):
        if path.exists():
            supervision._private(path)
            retained = json.loads(path.read_text())
            prior = retained.get('governor_requests', {}).get(identifier)
            if prior:
                if prior['fingerprint'] != digest:
                    raise ValueError('request_id already names a different governor operation')
                # Resume may wait for the existing watcher acknowledgement.
                # Reconcile only that same approved operation, never new budget.
                if prior['operation'].get('resume_state') == 'awaiting_first_poll':
                    retry = {key: value for key, value in arguments.items() if key != 'expected_revision'}
                    result = _execute(root, verb, retry, principal=principal)
                    with supervision._lock(directory, supervision._name(thread)):
                        retained = json.loads(path.read_text())
                        retained['governor_requests'][identifier]['operation'] = result.get('operation', prior['operation'])
                        supervision._save(path, retained)
                else:
                    result = _execute(root, 'status', {'selector': thread, 'endpoint': row['endpoint']}, principal=principal)
                    result['operation'] = prior['operation']
                    if prior['operation'].get('resumed') is False and prior['operation'].get('resume_state'):result['reason']=prior['operation']['resume_state']
                result['request_id'] = identifier
                return result
        result = _execute(root, verb, arguments, principal=principal)
        if result['scope']['thread_id'] != thread:
            raise ValueError('selected target changed during governor operation; inspect retained owner receipts')
        with supervision._lock(directory, supervision._name(thread)):
            if path.exists():
                supervision._private(path)
                retained = json.loads(path.read_text())
                retained.setdefault('governor_requests', {})[identifier] = dict(fingerprint=digest,
                    operation=result.get('operation', dict(state=result['state'], revision=result['revision'])))
                supervision._save(path, retained)
        result['request_id'] = identifier
        return result


def _status_identity(row):
    """Cheap current owner identity, never a mutation or liveness promise."""
    from .process import process_identity
    target = row['target']
    process = target['process']
    birth = process_identity(process['pid'])
    if not birth or birth.get('boot_id') != process['boot_id'] or birth.get('start_time_ticks') != process['start_ticks']:
        raise ValueError('cached native peer exited or changed identity')
    home = Path(target['home']).stat()
    endpoint = Path(row['endpoint'][7:]).stat()
    image = Path('/proc', str(process['pid']), 'exe')
    executable = image.stat()
    if (home.st_uid != os.getuid() or endpoint.st_uid != os.getuid()
            or f'{home.st_dev}:{home.st_ino}' != target['home_generation']
            or f'{endpoint.st_dev}:{endpoint.st_ino}' != target['socket_generation']
            or str(image.resolve()) != target['executable']):
        raise ValueError('cached native target ownership changed')
    return (executable.st_dev, executable.st_ino, executable.st_mtime_ns, executable.st_size)


def _resolve_status(root, selector, endpoint):
    from .local_sessions import resolve
    key = (str(Path(root).absolute()), selector, endpoint)
    cached = _STATUS_ROWS.get(key)
    if cached:
        try:
            if _status_identity(cached[0]) == cached[1]:
                return cached[0]
        except (OSError, ValueError, KeyError, TypeError):
            pass
        _STATUS_ROWS.pop(key, None)
    row = resolve(root, selector, endpoint=endpoint)
    try:
        identity = _status_identity(row)
    except (OSError, ValueError, KeyError, TypeError):
        return row
    if len(_STATUS_ROWS) >= 128:
        _STATUS_ROWS.pop(next(iter(_STATUS_ROWS)))
    _STATUS_ROWS[key] = (row, identity)
    return row
