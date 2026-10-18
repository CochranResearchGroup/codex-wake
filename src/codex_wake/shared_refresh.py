"""Explicitly approved shared-server MCP reload, without replacing conversations."""
from pathlib import Path
from uuid import UUID

from .records import WakeError

MODE = 'shared_mcp_idle'
_stopping = False


def configuration(config, profile_name, thread_id, caller_thread_id):
    from . import __version__
    try:
        profile = config['profiles'][profile_name]
        if (config['version'] != 1 or profile['refresh_mode'] != MODE
                or not profile['scope_approval'] or str(UUID(thread_id)) != thread_id
                or caller_thread_id != thread_id
                or profile_name not in config['callers'][caller_thread_id]
                or not isinstance(profile['resources'], dict) or not profile['resources']):
            raise ValueError
    except (KeyError, TypeError, ValueError, AttributeError):
        raise WakeError('shared refresh requires exact host caller and explicit scope approval') from None
    return dict(version=__version__, profile=profile_name, thread_id=thread_id,
                refresh_scope='shared_server_mcp', idle_required=True,
                resources=sorted(profile['resources']), operations=['configuration', 'refresh'])


def _directory(root):
    from .goal_supervision import _private
    root = Path(root).absolute()
    if root != root.resolve():
        raise WakeError('shared refresh root must be canonical')
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    _private(root, True)
    directory = root/'shared-refresh'
    directory.mkdir(exist_ok=True, mode=0o700)
    _private(directory, True)
    return directory


def _public(receipt):
    return {key: value for key, value in receipt.items()
            if key not in ('profile', 'policy_path', 'checkpoint_path', 'goals_before', 'last_busy_thread')}


def _validate_profile(profile):
    import math
    try:
        if (set(profile) != {'refresh_mode', 'scope_approval', 'cwd', 'app_server',
                            'codex_path', 'timeout', 'resources'}
                or profile['refresh_mode'] != MODE or not isinstance(profile['scope_approval'], str)
                or not profile['scope_approval'].strip()
                or not Path(profile['cwd']).is_absolute() or not Path(profile['cwd']).is_dir()
                or not Path(profile['codex_path']).is_absolute() or not Path(profile['codex_path']).is_file()
                or not profile['app_server'].startswith('unix:///')
                or type(profile['timeout']) not in (int, float)
                or not math.isfinite(profile['timeout']) or not 0 < profile['timeout'] <= 5):
            raise ValueError
        for check in profile['resources'].values():
            fields = ({'kind', 'path', 'description', 'sha256'} if check['kind'] == 'skill' else
                      {'kind', 'server', 'tool', 'arguments', 'read_only', 'expected_content'})
            if set(check) != fields or check['kind'] not in ('skill', 'mcp'):
                raise ValueError
            if check['kind'] == 'mcp' and check['read_only'] is not True:
                raise ValueError
    except (KeyError, TypeError, ValueError, AttributeError):
        raise WakeError('shared refresh profile or read-only resource proof is invalid') from None


def command(args, root, config, profile, checkpoint, content):
    import hashlib
    import json
    import time
    from .goal_supervision import _heartbeat, _lock, _private, _save
    from .lifecycle_budget import trusted_upper
    from .process import boot_id_value
    from .records import parse_timestamp
    from .sessions_cli import emit
    configuration(config, args.profile, args.thread_id, args.caller_thread_id)
    _validate_profile(profile)
    policy = Path(args.profiles).absolute()
    _private(policy)
    if policy != policy.resolve():
        raise WakeError('shared refresh policy must be canonical')
    if args.rollback:
        raise WakeError('shared MCP refresh never replaces a client; rollback is unavailable')
    body = json.loads(content)
    if (body.get('source_thread_id') != args.thread_id or body.get('pending_obligations') != []
            or any(not body.get(key) for key in ('objective', 'authority', 'next_packet'))):
        raise WakeError('source checkpoint must preserve work and account for obligations')
    if not args.intent or len(args.intent) > 200 or len(set(args.resource)) != len(args.resource):
        raise WakeError('shared refresh requires a bounded stable intent and unique resources')
    if not args.resource or any(name not in profile['resources'] for name in args.resource):
        raise WakeError('requested resources require host-approved proof checks')
    directory = _directory(root)
    intent = dict(thread_id=args.thread_id, profile_name=args.profile, profile=profile,
                  policy_path=str(policy), checkpoint_path=str(checkpoint),
                  checkpoint_sha256=args.checkpoint_sha256, resources=args.resource,
                  expires_at=args.expires_at)
    fingerprint = hashlib.sha256(json.dumps(intent, sort_keys=True).encode()).hexdigest()
    name = hashlib.sha256(args.intent.encode()).hexdigest()
    path = directory/(name+'.json')
    with _lock(directory, name):
        if path.exists():
            _private(path)
            receipt = json.loads(path.read_text())
            if receipt['fingerprint'] != fingerprint:
                raise WakeError('intent already binds a different shared refresh')
        else:
            if not _heartbeat(directory).get('fresh'):
                raise WakeError('independent sessions refresh-watch controller required')
            upper = trusted_upper()
            deadline = parse_timestamp(args.expires_at).timestamp()
            if deadline <= upper:
                raise WakeError('shared refresh expiry reached')
            receipt = dict(intent, fingerprint=fingerprint, intent_key=args.intent,
                           refresh_scope='shared_server_mcp', state='queued', reason='waiting_for_idle',
                           started_upper=upper, started_boottime=time.clock_gettime(time.CLOCK_BOOTTIME),
                           boot_id=boot_id_value(), deadline=deadline)
            _save(path, receipt)
        emit(_public(receipt), args.as_json)
        return 0 if receipt['state'] in ('queued', 'verifying', 'completed') else 5


def _remaining(receipt):
    import time
    from .process import boot_id_value
    if boot_id_value() != receipt['boot_id']:
        raise WakeError('boot identity changed')
    elapsed = time.clock_gettime(time.CLOCK_BOOTTIME)-receipt['started_boottime']
    if elapsed < 0:
        raise WakeError('elapsed time invalid')
    return receipt['deadline']-receipt['started_upper']-elapsed


def _request(receipt, method, params):
    if _stopping:
        raise WakeError('refresh controller is stopping')
    from .native_protocol import native_request
    remaining = _remaining(receipt)
    if remaining <= 0:
        raise TimeoutError('shared refresh expiry reached')
    profile = receipt['profile']
    return native_request(profile['app_server'], profile['codex_path'], method, params,
                          min(profile['timeout'], remaining))


def _continuity(before, after):
    if before is None or after is None:
        return before == after
    counters = {'tokensUsed', 'timeUsedSeconds', 'updatedAt'}
    return ({key: value for key, value in before.items() if key not in counters}
            == {key: value for key, value in after.items() if key not in counters}
            and all(type(before.get(key)) in (int, float) and type(after.get(key)) in (int, float)
                    and after[key] >= before[key] for key in counters))


def _source_workspace(receipt, value):
    try:
        cwd = value.get('cwd')
        return (value.get('id') == receipt['thread_id'] and isinstance(cwd, str)
                and Path(cwd).is_absolute()
                and Path(cwd).resolve(strict=True) == Path(receipt['profile']['cwd']).resolve(strict=True))
    except (OSError, ValueError, TypeError):
        return False


def _resources(receipt):
    import hashlib
    profile = receipt['profile']
    source = _request(receipt, 'thread/read', dict(threadId=receipt['thread_id'], includeTurns=False))['thread']
    if not _source_workspace(receipt, source):
        return None
    checks = {}
    catalog = None
    for name in receipt['resources']:
        check = profile['resources'][name]
        if check['kind'] == 'skill':
            if catalog is None:
                catalog = _request(receipt, 'skills/list', dict(cwds=[profile['cwd']], forceReload=True))['data']
            selected = [skill for row in catalog if row['cwd'] == profile['cwd'] and not row['errors']
                        for skill in row['skills'] if skill['path'] == check['path'] and skill['enabled']]
            ready = (len(selected) == 1 and selected[0]['description'] == check['description']
                     and hashlib.sha256(Path(check['path']).read_bytes()).hexdigest() == check['sha256'])
        else:
            result = _request(receipt, 'mcpServer/tool/call', dict(threadId=receipt['thread_id'],
                server=check['server'], tool=check['tool'], arguments=check['arguments']))
            ready = result.get('isError') is not True and result['content'] == check['expected_content']
        checks[name] = dict(state='ready' if ready else 'stale', kind=check['kind'])
    return checks


def _poll_one(path, receipt):
    import hashlib
    import json
    from .goal_supervision import _private, _save
    from .wake_control import paused
    if paused(path.parent.parent):
        receipt['reason'] = 'emergency_paused'
        return
    if _remaining(receipt) <= 0:
        receipt.update(state='expired', reason='expiry_reached')
        return
    policy = Path(receipt['policy_path'])
    _private(policy)
    config = json.loads(policy.read_text())
    configuration(config, receipt['profile_name'], receipt['thread_id'], receipt['thread_id'])
    if config['profiles'][receipt['profile_name']] != receipt['profile']:
        receipt.update(state='blocked', reason='host_refresh_policy_changed')
        return
    if hashlib.sha256(Path(receipt['checkpoint_path']).read_bytes()).hexdigest() != receipt['checkpoint_sha256']:
        receipt.update(state='blocked', reason='source_checkpoint_changed')
        return
    if receipt['state'] == 'queued':
        loaded = []
        cursor = None
        for page in range(4):
            params = dict(limit=100)
            if cursor:params['cursor'] = cursor
            result = _request(receipt, 'thread/loaded/list', params)
            loaded.extend(result['data']);cursor = result.get('nextCursor')
            if not cursor:break
        if cursor or len(loaded) > 256 or len(loaded) != len(set(loaded)):
            raise WakeError('loaded conversation inventory is incomplete')
        if receipt['thread_id'] not in loaded:
            raise WakeError('source conversation is not loaded')
        busy = 0
        order = list(dict.fromkeys([receipt['thread_id'], receipt.get('last_busy_thread'), *loaded]))
        for thread in (thread for thread in order if thread in loaded):
            value = _request(receipt, 'thread/read', dict(threadId=thread, includeTurns=False))['thread']
            if thread == receipt['thread_id'] and not _source_workspace(receipt, value):
                receipt.update(state='blocked', reason='source_workspace_mismatch')
                return
            if value['id'] != thread or value['status']['type'] not in ('idle', 'active'):
                raise WakeError('conversation state is unknown')
            if value['status']['type'] != 'idle' or value['status'].get('activeFlags'):
                busy = 1
                receipt['last_busy_thread'] = thread
                break
        receipt.update(loaded_count=len(loaded), busy_count=busy)
        if busy:
            receipt['reason'] = 'waiting_for_idle'
            return
        goals = {thread: _request(receipt, 'thread/goal/get', dict(threadId=thread))['goal'] for thread in loaded}
        # Recheck after goal observations; the native API supplies no atomic idle CAS.
        current_loaded = []
        cursor = None
        for page in range(4):
            params = dict(limit=100)
            if cursor:params['cursor'] = cursor
            current = _request(receipt, 'thread/loaded/list', params)
            current_loaded.extend(current['data']);cursor = current.get('nextCursor')
            if not cursor:break
        if cursor or set(current_loaded) != set(loaded) or len(current_loaded) != len(loaded):
            receipt['reason'] = 'inventory_changed_during_preflight'
            return
        for thread in loaded:
            value = _request(receipt, 'thread/read', dict(threadId=thread, includeTurns=False))['thread']
            if thread == receipt['thread_id'] and not _source_workspace(receipt, value):
                receipt.update(state='blocked', reason='source_workspace_mismatch')
                return
            if value['id'] != thread or value['status']['type'] != 'idle' or value['status'].get('activeFlags'):
                receipt.update(reason='waiting_for_idle', last_busy_thread=thread, busy_count=1)
                return
        receipt.update(goals_before=goals, goal_before=goals[receipt['thread_id']], state='reloading',
                       reason=None, reload_attempted=True)
        _save(path, receipt)  # Intent precedes the single external effect; never blindly replay it.
        try:
            from .wake_control import delivery_guard
            with delivery_guard(path.parent.parent):
                _request(receipt, 'config/mcpServer/reload', None)
            receipt.update(state='verifying', reload_acknowledged=True)
        except Exception as exc:
            receipt.update(state='uncertain', reason='reload_outcome_uncertain', observation_error=type(exc).__name__)
            return
        _save(path, receipt)
    if receipt['state'] in ('reloading', 'verifying', 'uncertain'):
        after = {thread: _request(receipt, 'thread/goal/get', dict(threadId=thread))['goal']
                 for thread in receipt['goals_before']}
        if not all(_continuity(before, after[thread]) for thread, before in receipt['goals_before'].items()):
            receipt.update(state='blocked', reason='goal_continuity_unverified')
            return
        receipt.update(goal_after=after[receipt['thread_id']], goal_continuity_verified=True)
        checks = _resources(receipt)
        if checks is None:
            receipt.update(state='blocked', reason='source_workspace_mismatch')
            return
        receipt['resource_status'] = checks
        if all(value['state'] == 'ready' for value in receipt['resource_status'].values()):
            receipt.update(state='completed', reason=None)
        elif receipt['state'] != 'uncertain':
            receipt.update(state='verifying', reason='requested_resources_not_ready')


def poll(root):
    import json
    from .goal_supervision import _lock, _private, _save
    directory = _directory(root)
    for path in directory.glob('*.json'):
        if path.name == 'controller.json':continue
        with _lock(directory, path.stem):
            _private(path)
            receipt = json.loads(path.read_text())
            if receipt['state'] not in ('queued', 'reloading', 'verifying', 'uncertain'):continue
            try:
                _poll_one(path, receipt)
            except TimeoutError:
                receipt.update(state='expired', reason='expiry_reached')
            except Exception as exc:
                receipt.update(reason='observation_unavailable', observation_error=type(exc).__name__)
                try:
                    if _remaining(receipt) <= 0:receipt.update(state='expired', reason='expiry_reached')
                except WakeError as guard:
                    receipt.update(state='blocked', reason=str(guard))
            _save(path, receipt)


def watch(root, interval=1):
    global _stopping
    _stopping = False
    import fcntl
    import math
    import os
    import signal
    import time
    from uuid import uuid4
    from .goal_supervision import _save
    from .process import boot_id_value, process_identity
    if type(interval) not in (int, float) or not math.isfinite(interval) or not .05 <= interval <= 5:
        raise WakeError('refresh interval must be between 0.05 and 5 seconds')
    directory = _directory(root)
    descriptor = os.open(directory/'watch.lock', os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX|fcntl.LOCK_NB)
        running = True
        def finish(signum, frame):
            global _stopping
            nonlocal running
            _stopping = True
            running = False
        prior = {sig: signal.signal(sig, finish) for sig in (signal.SIGTERM, signal.SIGINT)}
        heartbeat = dict(generation=uuid4().hex, pid=os.getpid(), identity=process_identity(os.getpid()),
                         boot_id=boot_id_value(), interval=interval)
        try:
            while running:
                _save(directory/'controller.json', dict(heartbeat, active=True,
                    observed_boottime=time.clock_gettime(time.CLOCK_BOOTTIME)))
                poll(root)
                time.sleep(interval)
        finally:
            _save(directory/'controller.json', dict(heartbeat, active=False,
                observed_boottime=time.clock_gettime(time.CLOCK_BOOTTIME)))
            for sig, handler in prior.items():signal.signal(sig, handler)
