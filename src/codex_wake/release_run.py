"""Bounded detached orchestration of existing durable release stages."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import threading
import uuid

from .process import process_identity

ACTIVE = {'running', 'submitting', 'unknown'}
TERMINAL = {'failed', 'unknown', 'conflicted'}


def worker_alive(worker):
    pid = worker.get('pid')
    if type(pid) is not int or worker.get('identity') != process_identity(pid):
        return False
    try:
        return Path('/proc', str(pid), 'stat').read_text().rsplit(') ', 1)[1].split()[0] != 'Z'
    except OSError:
        return False


def reconcile(driver, run):
    """Observe one exact worker; disappearance never licenses another attempt."""
    worker = run.get('orchestration')
    if worker and worker['status'] in ACTIVE and not worker_alive(worker):
        worker.update(status='unknown', reason='recorded orchestration worker is no longer observable')
        driver.event(run, 'orchestration_unknown')
    return run


def execute(driver, operation, run, arguments):
    if operation != 'run':
        raise ValueError('unsupported release workflow operation')
    reconcile(driver, run)
    existing = run.get('orchestration')
    if existing and existing['status'] in ACTIVE:
        return run
    if run['status'] in TERMINAL:
        return run
    if run['status'] == 'qualified':
        from .release_qualification import execute as qualify
        return qualify(driver, 'qualify', run, arguments)
    timeout = run['recipe'].get('workflow_timeout_seconds', 7200)
    interval = run['recipe'].get('workflow_poll_seconds', .5)
    if type(timeout) is not int or not 1 <= timeout <= 21600:
        raise ValueError('workflow timeout must be 1..21600 seconds')
    if type(interval) not in (int, float) or not .05 <= interval <= 10:
        raise ValueError('workflow polling interval must be .05..10 seconds')
    directory = Path(run['manifest']).parent
    nonce = uuid.uuid4().hex
    worker = dict(status='submitting', nonce=nonce, started_at=time.time(),
                  deadline=time.time()+timeout, log=str(directory / ('workflow-'+nonce+'.log')),
                  arguments={key:arguments[key] for key in ('jobs','max_items') if key in arguments})
    if existing:
        run.setdefault('orchestration_attempts', []).append(existing)
    run['orchestration'] = worker
    driver.event(run, 'orchestration_submitting', nonce=nonce)
    # Use the exact current Python and import root for both installed and editable
    # layouts. No shell or inherited terminal controls the detached worker.
    environment = dict(os.environ)
    environment['PYTHONPATH'] = str(Path(__file__).resolve().parent.parent)
    descriptor = os.open(worker['log'], os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, 'w') as log:
        try:
            child = subprocess.Popen([sys.executable, '-m', 'codex_wake.release_run',
                '--root', str(driver.root), '--run-id', run['run_id'], '--nonce', nonce],
                cwd=directory, env=environment, stdin=subprocess.DEVNULL,
                stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        except OSError as error:
            worker.update(status='failed', reason=str(error))
            driver.event(run, 'orchestration_start_failed')
            return run
    threading.Thread(target=child.wait, daemon=True, name='release-worker-reaper').start()
    worker.update(status='running', pid=child.pid, identity=process_identity(child.pid))
    driver.save(run)
    return run


def drive(root, run_id, nonce):
    from .release_driver import ReleaseDriver
    from .release_build import advance
    from .release_qualification import execute as qualify
    driver = ReleaseDriver(root, {})
    while True:
        interval = .5
        with driver.locked():
            run = driver.load(run_id)
            worker = run.get('orchestration', {})
            if worker.get('nonce') != nonce:
                return 2
            if worker.get('identity') != process_identity(os.getpid()):
                return 2
            try:
                if time.time() >= worker['deadline']:
                    worker.update(status='held', reason='workflow deadline reached', finished_at=time.time())
                    driver.event(run, 'orchestration_deadline')
                    return 2
                if run['status'] in TERMINAL:
                    worker.update(status='held', reason=run['status'], finished_at=time.time())
                    driver.event(run, 'orchestration_held', status=run['status'])
                    return 2
                arguments = worker.get('arguments', {})
                if run['status'] in ('built', 'qualifying', 'qualified'):
                    qualify(driver, 'qualify', run, arguments)
                else:
                    advance(driver, run, arguments)
                if run['status'] == 'qualified':
                    worker.update(status='completed', finished_at=time.time())
                    driver.event(run, 'orchestration_completed')
                    return 0
                if run['status'] in TERMINAL:
                    worker.update(status='held', reason=run['status'], finished_at=time.time())
                    driver.event(run, 'orchestration_held', status=run['status'])
                    return 2
                interval = run['recipe'].get('workflow_poll_seconds', .5)
            except Exception as error:
                worker.update(status='held', reason=str(error), finished_at=time.time())
                run['status'] = 'failed'
                driver.event(run, 'orchestration_failed', reason=str(error))
                return 2
        time.sleep(interval)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--nonce', required=True)
    args = parser.parse_args()
    return drive(args.root, args.run_id, args.nonce)


if __name__ == '__main__':
    raise SystemExit(main())
