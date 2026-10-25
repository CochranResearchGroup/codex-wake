"""Inspect or start the one configured watcher without changing its mask or grants."""
from pathlib import Path
import shlex
import subprocess

from .session_permissions import PermissionStore, Principal, PermissionDenied

SERVICE = 'codex-wake-goal-limits.service'


def watcher_status(root, *, runner=subprocess.run):
    root = Path(root).absolute()
    if root != root.resolve():
        raise ValueError('canonical supervision root required')
    result = runner(['systemctl', '--user', 'show', SERVICE, '--no-pager',
        '--property=LoadState,UnitFileState,ActiveState,SubState,MainPID,ExecStart'],
        capture_output=True, text=True, timeout=10, check=False)
    values = dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)
    command = values.get('ExecStart', '')
    argv = []
    try:
        argv = shlex.split(command.split('argv[]=', 1)[1].split(' ;', 1)[0])
        index = argv.index('--wake-root')
        scope = (argv[index+1] == str(root) and 'goal-limits' in argv
                 and argv[argv.index('goal-limits')+1] == 'watch')
    except (ValueError, IndexError):
        scope = False
    masked = values.get('UnitFileState', '').startswith('masked') or values.get('LoadState') == 'masked'
    if masked:
        reason = 'watcher_masked'
        action = ('The operator must reconcile why this service was masked before explicitly unmasking it. '
                  'Then run goal-limits start-watcher and verify the exact enrollment first-poll acknowledgement.')
    elif result.returncode or values.get('LoadState') != 'loaded':
        reason = 'watcher_not_installed'
        action = 'Install the configured codex-wake-goal-limits.service for this existing private root; do not create a competing watcher.'
    elif not scope:
        reason = 'watcher_scope_mismatch'
        action = 'Reconcile the configured service root with the selected host root. No alternate root or service will be started.'
    elif values.get('ActiveState') == 'active':
        reason = 'watcher_running'
        action = 'Inspect goal-limits show for fresh accounting and an acknowledgement of this enrollment revision.'
    else:
        reason = 'watcher_not_running'
        action = 'Run goal-limits start-watcher with your existing authenticated operator or common-policy authority.'
    return dict(service=SERVICE, reason=reason, active_state=values.get('ActiveState', 'unknown'),
        unit_file_state=values.get('UnitFileState', 'unknown'), configured_root_verified=scope,
        start_attempted=False, enforcement_verified=False, next_action=action)


def start_watcher(root, *, principal, task_id=None, operation_id=None, runner=subprocess.run):
    if not isinstance(principal, Principal):
        raise PermissionDenied('permission_identity_unverified')
    store = PermissionStore(root)
    if not store.active() and principal.role != 'operator':
        raise PermissionDenied('watcher_start_requires_operator_or_common_policy')
    from .permission_enforcement import authorize
    authorize(root, 'enforcement.watcher_start', principal, task_id=task_id, operation_id=operation_id)
    before = watcher_status(root, runner=runner)
    if before['reason'] != 'watcher_not_running':
        return before
    # A maintenance handover must keep its exact original interval and controller.
    from .goal_supervision import _directory, _lock
    from .goal_maintenance import admission_guard
    directory = _directory(root)
    with _lock(directory, 'maintenance'):
        admission_guard(directory)
        current = watcher_status(root, runner=runner)
        if current['reason'] != 'watcher_not_running':
            return current
        started = runner(['systemctl', '--user', 'start', SERVICE], capture_output=True,
                         text=True, timeout=10, check=False)
    result = watcher_status(root, runner=runner)
    result['start_attempted'] = True
    if started.returncode:
        result.update(reason='watcher_start_failed', next_action='Inspect the configured service journal, then reconcile its exact failed start; no restart or unmask was attempted.')
    return result
