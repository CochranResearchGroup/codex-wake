"""Independent, RPC-free guard for one dedicated native executor.

The guard is the systemd unit's main process. Exiting fences the assignment and
lets KillMode=control-group stop every descendant, including blocked tools.
"""
from __future__ import annotations

from contextlib import contextmanager
import fcntl
import json
import os
import tempfile
from pathlib import Path
import time

from .objective_ledger import ObjectiveLedger, _private
from .records import parse_timestamp
from .lifecycle_budget import objective_identity
from .process import boot_id_value, process_exists, process_identity


class _NonblockingLedger(ObjectiveLedger):
    @contextmanager
    def _transaction(self, *, write=True):
        _private(self.directory, directory=True)
        descriptor = os.open(self.lock_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        with os.fdopen(descriptor, 'a+') as lock:
            _private(self.lock_path)
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            _private(self.path)
            descriptor = os.open(self.path, os.O_RDONLY | os.O_NOFOLLOW)
            with os.fdopen(descriptor) as source:
                state = json.load(source)
            yield state
            if write:
                descriptor, temporary = tempfile.mkstemp(dir=self.directory)
                try:
                    with os.fdopen(descriptor, 'w') as target:
                        json.dump(state, target, sort_keys=True)
                        target.flush()
                        os.fsync(target.fileno())
                    os.replace(temporary, self.path)
                finally:
                    if os.path.exists(temporary):
                        os.unlink(temporary)


class Guard:
    """Check one immutable admission against suspend-aware elapsed time."""

    def __init__(self, configuration):
        self.config = configuration
        strict = configuration['configuration']['strict_execution']
        self.limits = strict.get('limits', strict)
        self.seen_usage = set()

    def check(self, *, boottime=None):
        if boot_id_value() != self.config['boot_id']:
            return 'boot_identity_changed'
        elapsed = (time.clock_gettime(time.CLOCK_BOOTTIME) if boottime is None else boottime) - self.config['started_boottime']
        if elapsed < 0:
            return 'elapsed_time_invalid'
        upper = self.config['started_upper'] + elapsed
        if upper >= self.config['deadline'] - self.limits['stop_grace_seconds'] - self.limits['checkpoint_grace_seconds']:
            return 'deadline_reached'
        try:
            controller = json.loads((Path(self.config['wake_root']) / 'lifecycle/supervision.json').read_text())
            pid = controller['pid']
            if (controller.get('active') is not True or not process_exists(pid)
                    or process_identity(pid) != controller['identity']
                    or Path('/proc', str(pid), 'stat').read_text().rsplit(')', 1)[1].split()[0] == 'Z'
                    or not 0 <= upper - controller['observed_at'] <= self.limits['accounting_max_age_seconds']):
                return 'controller_unavailable'
        except (OSError, ValueError, KeyError, TypeError, IndexError):
            return 'controller_unavailable'
        return self.accounting(upper, elapsed)

    def accounting(self, upper, elapsed):
        """Charge only native rollouts bound to this exact host-owned objective."""
        try:
            ledger = _NonblockingLedger(self.config['wake_root'], self.config['objective_id'])
            view = ledger.inspect(now=upper)
            if view['revision'] != self.config['configuration']['revision']:
                return 'configuration_changed'
            owned = {}
            for path in (Path(self.config['wake_root']) / 'lifecycle').glob('*.json'):
                if path.name == 'supervision.json' or path.name.startswith('owner-'):
                    continue
                receipt = json.loads(path.read_text())
                intent = receipt.get('intent', {})
                if intent.get('operation') != 'spawn' or not receipt.get('thread_id'):
                    continue
                launch = intent.get('launch', {})
                if ((intent.get('configuration') or {}).get('revision') != self.config['configuration']['revision']
                        or objective_identity(intent.get('continuation', {})) != self.config['objective_id']
                        or launch.get('app_server') != self.config['endpoint']
                        or Path(launch.get('codex_home', '')).resolve() != Path(self.config['codex_home']).resolve()):
                    continue
                actor = receipt.get('budget_actor')
                if actor not in view['actors']:
                    return 'actor_binding_unknown'
                thread = receipt['thread_id']
                if thread in owned and owned[thread] != actor:
                    return 'actor_binding_changed'
                owned[thread] = actor
            snapshots = {}
            home = Path(self.config['codex_home']) / 'sessions'
            paths = list(home.rglob('*.jsonl')) if home.exists() else []
            if len(paths) > 512:
                return 'accounting_capacity_exceeded'
            for path in paths:
                if path.is_symlink() or path.stat().st_size > 32 * 1024 * 1024:
                    return 'accounting_capacity_exceeded'
                path.resolve().relative_to(home.resolve())
                data = path.read_text()
                complete = data[:data.rfind('\n') + 1] if not data.endswith('\n') else data
                rows = [json.loads(line) for line in complete.splitlines()]
                identities = {row.get('payload', {}).get('id') for row in rows if row.get('type') == 'session_meta'}
                if not rows and elapsed < self.limits['accounting_max_age_seconds']:
                    continue
                if len(identities) != 1:
                    return 'rollout_identity_unknown'
                thread = next(iter(identities))
                if thread not in owned:
                    if elapsed >= self.limits['accounting_max_age_seconds']:
                        return 'unattributed_native_work'
                    continue
                actor = owned[thread]
                if actor in snapshots:
                    return 'rollout_binding_ambiguous'
                usage, observed = None, None
                for row in rows:
                    payload = row.get('payload', {})
                    if row.get('type') == 'event_msg' and payload.get('type') == 'token_count':
                        info = payload.get('info') or {}
                        value = (info.get('total_token_usage') or {}).get('total_tokens')
                        if type(value) is not int or value < 0 or (usage is not None and value < usage):
                            return 'accounting_invalid'
                        stamp = parse_timestamp(row['timestamp']).timestamp()
                        if observed is not None and stamp < observed:
                            return 'accounting_invalid'
                        usage, observed = value, stamp
                snapshots[actor] = usage, observed
            for actor_id in owned.values():
                actor = view['actors'][actor_id]
                usage, observed = snapshots.get(actor_id, (None, None))
                if not actor['settled'] and upper >= actor['session_deadline'] - self.limits['stop_grace_seconds'] - self.limits['checkpoint_grace_seconds']:
                    return 'session_deadline_reached'
                if actor['settled']:
                    if usage is not None and usage != actor['used']:
                        return 'settled_actor_usage_changed'
                    continue
                if usage is None:
                    if actor_id in self.seen_usage or actor['used'] > 0 or elapsed >= self.limits['accounting_max_age_seconds']:
                        return 'accounting_missing'
                    continue
                if not 0 <= upper - observed <= self.limits['accounting_max_age_seconds']:
                    return 'accounting_stale'
                self.seen_usage.add(actor_id)
                view = ledger.record(actor_id, usage, settled=actor['settled'], now=upper)
                actor = view['actors'][actor_id]
                if not actor['known']:
                    return 'accounting_decreased'
                if usage >= actor['reservation']:
                    return 'session_tokens_exhausted'
                if upper >= actor['session_deadline'] - self.limits['stop_grace_seconds'] - self.limits['checkpoint_grace_seconds']:
                    return 'session_deadline_reached'
            if not view['accounting_known']:
                return 'objective_accounting_unknown'
            if view['tokens_used'] >= view['objective_token_limit']:
                return 'objective_tokens_exhausted'
            if not owned and elapsed >= self.limits['accounting_max_age_seconds']:
                return 'accounting_missing'
            return None
        except (OSError, ValueError, KeyError, TypeError):
            return 'accounting_unavailable'


def _status(config, state, reason=None, child_pid=None):
    destination = Path(config['status_path'])
    destination.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(dir=destination.parent)
    try:
        with os.fdopen(descriptor, 'w') as stream:
            json.dump(dict(state=state, reason=reason, generation=config['generation'],
                pid=os.getpid(), identity=process_identity(os.getpid()), child_pid=child_pid,
                endpoint=config['endpoint'], objective_id=config['objective_id'],
                observed_boottime=time.clock_gettime(time.CLOCK_BOOTTIME)), stream, sort_keys=True)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def run(config):
    """Run as a service main; a stop fence precedes exit and group termination."""
    import subprocess
    guard = Guard(config)
    child = None
    reason = guard.check()
    try:
        if reason is None:
            environment = dict(os.environ, CODEX_HOME=config['codex_home'])
            for key in ('CODEX_THREAD_ID', 'TMUX', 'TMUX_PANE', 'CODEX_WAKE_A2A_CAPABILITY',
                    'CODEX_WAKE_A2A_BUS_ROOT', 'CODEX_WAKE_SENDER_RECEIPT_AUTHORITY'):
                environment.pop(key, None)
            child = subprocess.Popen(config['argv'], cwd=config['cwd'], env=environment,
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            _status(config, 'running', child_pid=child.pid)
            while reason is None:
                if child.poll() is not None:
                    reason = 'executor_exited'
                    break
                time.sleep(guard.limits['poll_seconds'])
                reason = guard.check()
    except Exception:
        reason = 'guard_observation_failed'
    finally:
        _status(config, 'stopped', reason, child_pid=child.pid if child else None)
        if child is not None and child.poll() is None:
            # Never wait for tools to cooperate. Exiting this service main makes
            # systemd apply the configured control-group stop and bounded grace.
            child.terminate()
    return 5


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('configuration', type=Path)
    args = parser.parse_args(argv)
    configuration = json.loads(args.configuration.read_text())
    return run(configuration)


if __name__ == '__main__':
    raise SystemExit(main())
