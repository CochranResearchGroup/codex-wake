"""Native own-session voluntary limits; no model-issued grants or renewals.

The host supplies its existing policy/root and private native caller metadata.
A shared controller is started only when no configured service owns this root;
its existing singleton lock arbitrates concurrent first enrollments.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import time
from uuid import uuid4

from . import goal_supervision as supervision
from .session_permissions import Principal, PermissionStore, PermissionDenied

_CHILDREN = {}


def ensure_watcher(root, thread):
    """Arrange enforcement without changing service configuration or grants."""
    directory = supervision._directory(root)
    if supervision._heartbeat(directory).get('fresh'):
        return dict(reason='watcher_running', start_attempted=False)
    store = PermissionStore(root)
    if store.active():
        from .permission_enforcement import authorize
        authorize(root, 'enforcement.self_watch', Principal(thread))
        inherited = store.evaluate('enforcement.watcher_start', Principal(thread))
        if inherited['permission'] != 'allow' and inherited['rule'] != 'profile:permissive':
            raise PermissionDenied('permission_' + inherited['permission'], inherited)
    from .goal_watcher import watcher_status, SERVICE
    try:
        service = watcher_status(root)
    except (OSError, subprocess.SubprocessError):
        service = dict(reason='watcher_not_installed')
    if service['reason'] != 'watcher_not_installed':
        # Never bypass a service mask, scope mismatch or configured controller.
        if service['reason'] == 'watcher_not_running':
            from .goal_maintenance import admission_guard
            with supervision._lock(directory, 'maintenance'):
                admission_guard(directory)
                current = watcher_status(root)
                if current['reason'] != 'watcher_not_running':
                    return current
                started = subprocess.run(['systemctl', '--user', 'start', SERVICE],
                    capture_output=True, text=True, timeout=10, check=False)
            result = watcher_status(root)
            result['start_attempted'] = True
            if started.returncode:
                result.update(reason='watcher_start_failed',
                    next_action='Inspect the configured service journal; no restart or unmask was attempted.')
            return result
        return service
    with supervision._lock(directory, 'self-watcher-start'):
        if supervision._heartbeat(directory).get('fresh'):
            return dict(reason='watcher_running', start_attempted=False)
        environment = dict(os.environ)
        source = str(Path(__file__).resolve().parent.parent)
        environment['PYTHONPATH'] = source + os.pathsep + environment.get('PYTHONPATH', '')
        with (directory / 'self-watcher.log').open('a') as log:
            child = subprocess.Popen([sys.executable, '-m', 'codex_wake.self_limits',
                'watch', str(Path(root).absolute())], stdin=subprocess.DEVNULL,
                stdout=log, stderr=log, env=environment, start_new_session=True,
                close_fds=True)
        _CHILDREN[child.pid] = child
        end = time.monotonic() + 3
        while time.monotonic() < end:
            if supervision._heartbeat(directory).get('fresh'):
                return dict(reason='watcher_running', start_attempted=True, pid=child.pid)
            if child.poll() is not None:
                break
            time.sleep(.05)
        return dict(reason='watcher_start_unverified', start_attempted=True,
            pid=child.pid, next_action='Inspect private goal-supervision/self-watcher.log and controller readiness; do not assume enforcement.')


def execute(root, policy, verb, arguments, *, native_context, activation_baseline=False,replace_advisory=False):
    """Private native hook. The caller cannot choose a thread, scope or policy."""
    if not isinstance(arguments, dict):
        raise ValueError('self limit arguments must be an object')
    thread = (native_context or {}).get('threadId')
    supervision.verified_native_caller(native_context, thread)
    allowed = {'token_limit', 'time_limit_seconds'} if verb == 'set' else set()
    if verb not in ('show', 'set') or set(arguments) - allowed:
        raise ValueError('self limits support show and set/tighten only')
    grant = supervision._grant(policy, thread, root=root)
    if verb == 'show':
        result = supervision.show(root, policy, thread, native_context=native_context)
        if result.get('reason') == 'not_enrolled':
            from .goal_usage import observe_session_usage
            usage = observe_session_usage(grant['codex_home'], thread)
            result.update(accounting=usage, used_tokens=usage.get('used_tokens'),
                lifetime_used_tokens=usage.get('used_tokens'))
        return result
    tokens, seconds = arguments.get('token_limit'), arguments.get('time_limit_seconds')
    for value, cap in ((tokens, grant['max_tokens']), (seconds, grant['max_seconds'])):
        if type(value) is not int or not 0 < value <= cap:
            raise ValueError('positive limits within inherited host ceilings required')
    # A voluntary session allowance observes existing native goals; creating or
    # activating a goal can start autonomous work and is never setup authority.
    # Enrollment owns lifetime accounting and rejects increases, scope changes,
    # successor renewal and stop clearing under its maintenance/allocation locks.
    prepared = supervision.enroll(root, policy, thread, tokens, seconds,
        native_context=native_context, session_scope=True, prepare_only=True, activation_baseline=activation_baseline,requires_native_guard=activation_baseline,replace_advisory=replace_advisory)
    if prepared.get('state') != 'prepared':
        return prepared
    try:
        setup = ensure_watcher(root, thread)
    except PermissionDenied as error:
        setup = dict(reason=str(error), start_attempted=False,
            permission=error.decision, next_action='Respect the inherited watcher restriction; inspect host policy.')
    if setup.get('reason') != 'watcher_running':
        from .goal_readiness import engagement
        return dict(prepared,state='held',reason=setup.get('reason'),watcher_setup=setup,
            engagement=engagement(prepared,supervision._heartbeat(supervision._directory(root))))
    path=Path(root)/'goal-supervision'/(supervision._name(thread)+'.json')
    if activation_baseline and (not path.exists() or replace_advisory):
        from .goal_native_guard import preflight
        readiness=preflight(root,grant,thread)
        if not readiness['ready']:
            from .goal_readiness import engagement
            return dict(prepared,state='held',reason=readiness['reason'],admitted=False,
                deadline=None,time_origin=None,started_upper=None,used_tokens=None,enrollment_revision=0,generation=None,
                activation_preflight=readiness,controller=supervision._heartbeat(supervision._directory(root)),
                engagement=engagement(dict(prepared,state='held',reason=readiness['reason']),
                    supervision._heartbeat(supervision._directory(root))))
    result = supervision.enroll(root, policy, thread, tokens, seconds,
        native_context=native_context, session_scope=True, activation_baseline=activation_baseline,requires_native_guard=activation_baseline,replace_advisory=replace_advisory)
    end = time.monotonic() + 3
    while True:
        result = supervision.show(root, policy, thread, native_context=native_context)
        status = result.get('engagement', {}).get('status')
        if setup.get('reason') != 'watcher_running' or status == 'engaged' or result.get('state') in ('stopped', 'stop_unverified') or time.monotonic() >= end:
            break
        time.sleep(.05)
    return dict(result, watcher_setup=setup)


def local_execute(root, policy, verb, arguments, *, thread_id, activation_baseline=False,replace_advisory=False):
    """Same-UID human CLI adapter; exact owned native endpoint/history qualifies target.

    This is host authority, like the existing local CLI, not native model caller
    attestation. Remote adapters must use execute with private native metadata.
    """
    grant = supervision._grant(policy, thread_id, root=root)
    native = supervision._request(grant, 'thread/read',
        dict(threadId=thread_id, includeTurns=False))['thread']
    if native.get('id') != thread_id:
        raise ValueError('native target identity changed')
    path = Path(native['path'])
    home = Path(grant['codex_home']).resolve()
    if path != path.resolve() or not path.is_relative_to(home / 'sessions'):
        raise ValueError('owned native session history required')
    supervision._private(path)
    with path.open() as stream:
        row = json.loads(stream.readline(65537))
    metadata = row.get('payload', {})
    if row.get('type') != 'session_meta' or metadata.get('id') != thread_id:
        raise ValueError('native session history identity changed')
    session = metadata.get('session_id', thread_id)
    _, active = supervision._native(grant, thread_id)
    context = dict(threadId=thread_id, sessionId=session, callId='local-'+uuid4().hex,
        **{'x-codex-turn-metadata':dict(thread_id=thread_id, session_id=session,
            turn_id=active[0] if active else 'local-operator')})
    return execute(root, policy, verb, arguments, native_context=context, activation_baseline=activation_baseline,replace_advisory=replace_advisory)


def tool_specs():
    integer = dict(type='integer', minimum=1)
    return {
        'wake_self_limits_show': ('self-limits', 'show',
            'Inspect your own session usage and actual enforcement readiness.', {}, [], True),
        'wake_self_limits_set': ('self-limits', 'set',
            'Set or tighten voluntary own-session token and elapsed-time limits. Starts enforcement; preserves inherited ceilings and lifetime usage.',
            dict(token_limit=integer, time_limit_seconds=integer),
            ['token_limit', 'time_limit_seconds'], False),
    }


def register(subparsers):
    parser = subparsers.add_parser('self-limits', help='inspect or tighten native own-session resource limits')
    commands = parser.add_subparsers(dest='self_limits_command', required=True)
    commands.add_parser('show')
    setup = commands.add_parser('set')
    setup.add_argument('--token-limit', type=int, required=True)
    setup.add_argument('--time-limit-seconds', type=int, required=True)
    return parser


if __name__ == '__main__':
    if len(sys.argv) != 3 or sys.argv[1] != 'watch':
        raise SystemExit('private self-limit watcher requires an exact root')
    supervision.watch(Path(sys.argv[2]), interval=1)
