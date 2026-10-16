"""Dedicated user-service containment; never adopts an existing unit by name.

The service manager owns the deadline independently of the supervising agent.
Identity is the InvocationID, not a PID or reusable unit name. Cgroup paths are
read from systemd and remain beneath the unified cgroup mount.
"""
from __future__ import annotations
import math
import os
from pathlib import Path
import re
import subprocess


class SystemdExecution:
    def __init__(self, runner=subprocess.run):
        self.runner = runner

    def _run(self, argv):
        return self.runner(argv, capture_output=True, text=True, timeout=15, check=False)

    def _show(self, unit):
        result = self._run(['systemctl', '--user', 'show', unit, '--no-pager'])
        if result.returncode:
            raise RuntimeError('systemd readback failed: ' + result.stderr[:500])
        return dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)

    @staticmethod
    def _unit(unit):
        if not isinstance(unit, str) or not re.fullmatch(r'codex-wake-objective-[A-Za-z0-9_-]+\.service', unit):
            raise ValueError('a dedicated codex-wake-objective-*.service unit is required')

    def launch(self, unit, argv, *, cwd, environment, limits, runtime_seconds):
        self._unit(unit)
        if not isinstance(argv, (list, tuple)) or not argv or any(not isinstance(a, str) or '\0' in a for a in argv):
            raise ValueError('argv must be a nonempty string array')
        if not os.path.isabs(argv[0]):
            raise ValueError('executor program must be absolute')
        directory = Path(cwd)
        if not directory.is_absolute() or not directory.is_dir() or directory.is_symlink() or directory.stat().st_uid != os.getuid():
            raise ValueError('cwd must be an existing owned absolute directory')
        if not isinstance(environment, dict) or any(not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', k) or not isinstance(v, str) or '\0' in v for k, v in environment.items()):
            raise ValueError('invalid environment')
        required = {'memory_max_bytes', 'memory_swap_max_bytes', 'cpu_quota_percent', 'tasks_max', 'stop_grace_seconds'}
        if set(limits) != required:
            raise ValueError('all resource limits must be explicit')
        for key in required | {'runtime_seconds'}:
            value = runtime_seconds if key == 'runtime_seconds' else limits[key]
            integer = key in {'memory_max_bytes', 'memory_swap_max_bytes', 'tasks_max'}
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or (integer and not isinstance(value, int)) or value < 0 or (value == 0 and key != 'memory_swap_max_bytes'):
                raise ValueError('invalid resource limit: ' + key)
        before = self._show(unit)
        if before.get('LoadState') != 'not-found':
            raise RuntimeError('unit already exists; reconcile its recorded identity before retrying')
        properties = {'Type': 'exec', 'RuntimeMaxSec': runtime_seconds, 'KillMode': 'control-group',
                      'Restart': 'no', 'SendSIGKILL': 'yes', 'TimeoutStopSec': limits['stop_grace_seconds'],
                      'MemoryMax': limits['memory_max_bytes'], 'MemorySwapMax': limits['memory_swap_max_bytes'],
                      'CPUQuota': str(limits['cpu_quota_percent']) + '%', 'TasksMax': limits['tasks_max']}
        command = ['systemd-run', '--user', '--quiet', '--expand-environment=no', '--unit=' + unit, '--working-directory=' + str(directory)]
        command += ['--property=' + k + '=' + str(v) for k, v in properties.items()]
        command += ['--setenv=' + k + '=' + v for k, v in sorted(environment.items())]
        command += ['--', *argv]
        try:
            result = self._run(command)
        except (subprocess.TimeoutExpired, OSError) as exc:
            # An ambiguous transport outcome is deliberately not retried. Expose
            # observed identity for operator reconciliation without adopting it.
            raise RuntimeError('ambiguous launch; inspect unit ' + unit + ' before retrying') from exc
        if result.returncode:
            raise RuntimeError('launch failed; reconcile unit ' + unit + ': ' + result.stderr[:500])
        row = self._show(unit)
        if not row.get('InvocationID') or not row.get('ControlGroup'):
            raise RuntimeError('launch identity unavailable; reconcile unit ' + unit)
        return {'unit': unit, 'invocation_id': row['InvocationID'], 'control_group': row['ControlGroup'], 'main_pid': int(row.get('MainPID', 0))}

    def inspect(self, identity):
        self._unit(identity['unit'])
        row = self._show(identity['unit'])
        retired = row.get('LoadState') == 'not-found'
        if not identity.get('invocation_id'):
            raise RuntimeError('executor identity required')
        if not retired and row.get('InvocationID') != identity.get('invocation_id'):
            raise RuntimeError('executor identity changed or unavailable')
        observed_group = row.get('ControlGroup')
        if observed_group and observed_group != identity.get('control_group'):
            raise RuntimeError('executor control group changed')
        relative = Path(identity['control_group'])
        if not relative.is_absolute() or '..' in relative.parts or relative == Path('/'):
            raise RuntimeError('unsafe control group')
        root = Path('/sys/fs/cgroup') / str(relative).lstrip('/')
        members = []
        kernel = {}
        if retired and root.exists():
            raise RuntimeError('retired executor control group unexpectedly exists')
        if root.is_dir():
            for processes in root.rglob('cgroup.procs'):
                try:
                    members.extend(int(pid) for pid in processes.read_text().split())
                except FileNotFoundError:
                    pass  # subgroup exited during observation
            events = dict(line.split() for line in (root / 'cgroup.events').read_text().splitlines())
            populated = events.get('populated') == '1'
            for name in ('memory.max', 'memory.swap.max', 'cpu.max', 'pids.max'):
                kernel[name] = (root / name).read_text().strip()
        else:
            if row.get('ActiveState') in {'active', 'activating', 'deactivating'}:
                raise RuntimeError('active executor cgroup unavailable')
            populated = False
        return {'state': 'inactive' if retired else row.get('ActiveState', 'unknown'), 'substate': row.get('SubState', 'unknown'),
                'populated': populated, 'members': sorted(set(members)),
                'identity_retired': retired, 'kernel_limits': kernel,
                'configured_limits': {key: row.get(key) for key in ('MemoryMax', 'MemorySwapMax', 'CPUQuotaPerSecUSec', 'TasksMax')}}

    def stop(self, identity):
        before = self.inspect(identity)  # identity must match immediately before effects
        if before['identity_retired'] or (before['state'] in {'inactive', 'failed'}
                and not before['populated'] and not before['members']):
            return before
        result = self._run(['systemctl', '--user', 'stop', identity['unit']])
        if result.returncode:
            raise RuntimeError('stop failed: ' + result.stderr[:500])
        after = self.inspect(identity)
        if after['populated'] or after['members']:
            raise RuntimeError('executor remains populated after stop')
        return after
