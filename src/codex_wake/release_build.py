"""Native package stage execution through durable Cargo Signal MCP jobs.

Host recipe fields: build_steps [{name, argv, cwd='.', inputs=[], outputs=[]}],
package_directory, required_artifacts, target_directory, preflight
{executables, files, python_modules, argv_checks}, minimum_disk_bytes,
max_jobs, memory_per_job_bytes, retained_package {path, files, binding}.
Paths are relative to the isolated worktree unless explicitly host registered.
retained_package binding must equal adoption_binding(driver,run).
"""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

from .release_driver import digest, fingerprint
from .release_signal import SignalClient

NATIVE_ARTIFACTS = ['bin/codex', 'bin/codex-code-mode-host', 'bin/codex-exec-server',
                    'codex-resources/bwrap', 'codex-path/rg', 'codex-package.json']


def safe_path(root, relative):
    root = Path(root).resolve()
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError('release path escapes owned directory')
    return path


def stage_definitions(run):
    steps = run['recipe'].get('build_steps', [])
    if not steps:
        raise ValueError('host recipe must declare maintained packaging commands')
    names = set()
    for step in steps:
        if not isinstance(step.get('name'), str) or not step['name'] or step['name'] in names:
            raise ValueError('unique build step names required')
        names.add(step['name'])
        argv = step.get('argv')
        if not isinstance(argv, list) or not argv or any(not isinstance(v, str) or '\0' in v for v in argv):
            raise ValueError('build commands must be explicit argv arrays')
        safe_path(run['worktree'], step.get('cwd', '.'))
    return steps


def adoption_binding(driver, run):
    return dict(source_revision=driver.snapshot(run)['revision'],
                target=run['recipe'].get('target'), profile=run['recipe'].get('profile'),
                features=run['recipe'].get('features', []))


def stage_fingerprint(driver, run, step):
    inputs = step.get('inputs', [])
    source = ({name: digest(safe_path(run['worktree'], name)) for name in inputs}
              if inputs else driver.snapshot(run))
    return fingerprint(dict(source=source, definition=step, toolchain=run['toolchain'],
                            target=run['recipe'].get('target'), profile=run['recipe'].get('profile'),
                            features=run['recipe'].get('features', []), environment=run.get('build_environment'), resources=run.get('resources')))


def output_inventory(run, step):
    return {name: digest(safe_path(run['worktree'], name)) for name in step.get('outputs', [])}


def verify_outputs(run, step, expected):
    try:
        return output_inventory(run, step) == expected
    except OSError:
        return False


def package_inventory(run, directory=None):
    recipe = run['recipe']
    package = Path(directory) if directory else safe_path(run['worktree'], recipe['package_directory'])
    package = package.resolve(strict=True)
    files = {}
    for relative in recipe.get('required_artifacts', NATIVE_ARTIFACTS):
        path = safe_path(package, relative)
        if not path.is_file() or path.is_symlink():
            raise ValueError('complete package missing regular artifact: ' + relative)
        if relative != 'codex-package.json' and not os.access(path, os.X_OK):
            raise ValueError('package artifact is not executable: ' + relative)
    for path in sorted(package.rglob('*')):
        if path.is_symlink():
            raise ValueError('package symlinks require materialization before qualification')
        if path.is_file():
            files[str(path.relative_to(package))] = digest(path)
    return dict(path=str(package), files=files, inventory_sha256=fingerprint(files))


def resource_limits(run, arguments):
    recipe = run['recipe']
    available = 0
    for line in Path('/proc/meminfo').read_text().splitlines():
        if line.startswith('MemAvailable:'):
            available = int(line.split()[1]) * 1024
    per_job = recipe.get('memory_per_job_bytes', 3 * 1024 ** 3)
    cpu = max(1, os.cpu_count() or 1)
    selected = max(1, min(cpu, recipe.get('max_jobs', 4), max(1, available // per_job)))
    competing = []
    for comm in Path('/proc').glob('[0-9]*/comm'):
        try:
            if comm.read_text().strip() in ('cargo', 'rustc'):
                competing.append(int(comm.parent.name))
        except (OSError, ValueError):
            continue
    if competing:
        selected = 1
    override = arguments.get('jobs')
    if override is not None:
        if type(override) != int or not 1 <= override <= cpu:
            raise ValueError('jobs override must be within available CPU count')
        selected = override
    free = shutil.disk_usage(run['worktree']).free
    if free < recipe.get('minimum_disk_bytes', 1024 ** 3):
        raise ValueError('insufficient disk space for declared build')
    return dict(jobs=selected, available_memory_bytes=available, free_disk_bytes=free,
                competing_build_pids=competing)


def preflight(run):
    requirements = run['recipe'].get('preflight', {})
    for executable in requirements.get('executables', []):
        if not shutil.which(executable):
            raise ValueError('required executable unavailable: ' + executable)
    for step in stage_definitions(run):
        if not shutil.which(step['argv'][0]):
            raise ValueError('build executable unavailable: ' + step['argv'][0])
    for relative in requirements.get('files', []):
        if not safe_path(run['worktree'], relative).is_file():
            raise ValueError('required helper asset unavailable: ' + relative)
    for module in requirements.get('python_modules', []):
        if importlib.util.find_spec(module) is None:
            raise ValueError('declared Python dependency unavailable: ' + module)
    for argv in requirements.get('argv_checks', []):
        if not isinstance(argv, list) or not argv or any(not isinstance(x, str) for x in argv):
            raise ValueError('preflight checks require explicit argv')
        result = subprocess.run(argv, cwd=run['worktree'], capture_output=True, timeout=30)
        if result.returncode:
            raise ValueError('fixture argument/dependency preflight failed')


def cache_claim(driver, run):
    cache = Path(run['recipe'].get('target_directory', str(Path(run['worktree']) / 'target')))
    if not cache.is_absolute():
        cache = safe_path(run['worktree'], str(cache))
    cache = cache.resolve()
    root = driver.root / 'cache-claims'
    root.mkdir(mode=0o700, exist_ok=True)
    path = root / (fingerprint(str(cache)) + '.json')
    if path.exists():
        other = json.loads(path.read_text())
        if other['run_id'] != run['run_id']:
            raise ValueError('shared build cache has an unresolved writer: ' + other['run_id'])
    else:
        with path.open('x') as stream:
            json.dump(dict(run_id=run['run_id'], cache=str(cache)), stream)
        path.chmod(0o600)
    run['cache_claim'] = str(path)
    run['target_directory'] = str(cache)
    return path


def release_cache_claim(run):
    path = Path(run['cache_claim']) if run.get('cache_claim') else None
    if path and path.exists() and json.loads(path.read_text()).get('run_id') == run['run_id']:
        path.unlink()


def reconcile(driver, run):
    for name, stage in run['stages'].items():
        if stage.get('status') not in ('running', 'submitting', 'unknown'):
            continue
        if not stage.get('job_dir'):
            stage['status'] = 'unknown'
            run['status'] = 'unknown'
            driver.save(run)
            return run
        with SignalClient(run['recipe'].get('cargo_signal', 'cargo-signal')) as client:
            receipt = client.call('get_command_status', dict(job_dir=stage['job_dir'], brief=False))
        stage['receipt'] = receipt
        if receipt['status'] == 'running':
            run['status'] = 'building'
            driver.save(run)
            return run
        if receipt['status'] == 'unknown':
            stage['status'] = run['status'] = 'unknown'
            driver.save(run)
            return run
        attempt = stage['attempts'][-1]
        attempt.update(finished_at=time.time(), receipt=receipt)
        definitions = {step['name']: step for step in stage_definitions(run)}
        step = definitions[name]
        unchanged = stage_fingerprint(driver, run, step) == stage['input_fingerprint']
        if receipt.get('exit_code') == 0 and receipt['status'] == 'passed' and unchanged:
            try:
                stage['outputs'] = output_inventory(run, step)
                stage['status'] = 'passed'
            except OSError:
                stage['status'] = 'failed'
                stage['failure'] = 'declared output unavailable'
        else:
            stage['status'] = 'failed'
            stage['failure'] = 'command failed or build inputs changed during execution'
        attempt['status'] = stage['status']
        driver.event(run, 'stage_finished', stage=name, status=stage['status'])
        if stage['status'] != 'passed':
            run['status'] = 'failed'
            release_cache_claim(run)
            driver.save(run)
            return run
    return run


def adopt(driver, run):
    if run.get('retained_invalidated'):
        return False
    retained = run['recipe'].get('retained_package')
    if not retained:
        return False
    binding = retained.get('binding', {})
    expected = adoption_binding(driver, run)
    if any(binding.get(key) != value for key, value in expected.items()):
        raise ValueError('retained artifact source/build binding mismatch')
    snapshot = driver.snapshot(run)
    if snapshot['diff'] != __import__('hashlib').sha256(b'').hexdigest() or snapshot['untracked']:
        raise ValueError('retained package requires unchanged pinned source')
    compiler = binding.get('toolchain')
    if compiler and compiler != 'unknown' and compiler != run['toolchain']:
        raise ValueError('retained artifact compiler binding mismatch')
    package = package_inventory(run, retained['path'])
    if package['files'] != retained.get('files'):
        raise ValueError('retained complete package inventory mismatch')
    run['package'] = dict(package, reused=True, origin='verified_retained_package',
                          binding=binding, provenance_gaps=[] if compiler and compiler != 'unknown' else
                          ['historical compiler toolchain not recorded'])
    run['status'] = 'built'
    driver.event(run, 'package_reused', inventory_sha256=package['inventory_sha256'])
    return True


def advance(driver, run, arguments):
    if run['status'] == 'conflicted':
        raise ValueError('resolve isolated integration conflicts before building')
    if run['status'] in ('built', 'qualified'):
        if package_inventory(run, run['package']['path'])['files'] != run['package']['files']:
            raise ValueError('completed package bytes changed')
        return run
    reconcile(driver, run)
    if run['status'] in ('unknown', 'failed') or any(s.get('status') == 'running' for s in run['stages'].values()):
        return run
    if adopt(driver, run):
        return run
    steps = stage_definitions(run)
    preflight(run)
    if not run.get('resources'):
        run['resources'] = resource_limits(run, arguments)
    for step in steps:
        name = step['name']
        existing = run['stages'].get(name)
        if existing and existing['status'] == 'passed':
            continue
        claim = cache_claim(driver, run)
        stage = dict(status='submitting', input_fingerprint=stage_fingerprint(driver, run, step),
                     attempts=[*(existing or {}).get('attempts', []), dict(started_at=time.time(), status='submitting')])
        run['stages'][name] = stage
        run['status'] = 'building'
        driver.event(run, 'stage_submitting', stage=name)
        cwd = safe_path(run['worktree'], step.get('cwd', '.'))
        frozen_environment = run.get('build_environment', {})
        clear = [arg for key, value in frozen_environment.items() if value is None for arg in ('-u', key)]
        values = [key + '=' + value for key, value in frozen_environment.items() if value is not None]
        argv = ['/usr/bin/env', *clear, *values, 'CARGO_BUILD_JOBS=' + str(run['resources']['jobs']),
                'CARGO_TARGET_DIR=' + run['target_directory'], *step['argv']]
        stage['argv'] = argv
        try:
            with SignalClient(run['recipe'].get('cargo_signal', 'cargo-signal')) as client:
                receipt = client.call('start_command', dict(argv=argv, cwd=str(cwd),
                    artifact_root=str(Path(run['manifest']).parent / 'jobs'), max_items=arguments.get('max_items', 8),
                    timeout_seconds=run['recipe'].get('timeout_seconds', 7200)))
        except (OSError, ValueError) as error:
            stage['status'] = run['status'] = 'unknown'
            stage['failure'] = str(error)
            driver.save(run)
            return run
        stage.update(status='running', job_dir=receipt['job_dir'])
        stage['attempts'][-1].update(status='running', job_dir=receipt['job_dir'], argv=argv)
        driver.save(run)
        return run
    try:
        run['package'] = dict(package_inventory(run), reused=False, origin='executed_build')
        run['status'] = 'built'
        driver.event(run, 'package_built', inventory_sha256=run['package']['inventory_sha256'])
    except (OSError, ValueError) as error:
        run['status'] = 'failed'
        run['failure'] = str(error)
        driver.event(run, 'package_failed', reason=str(error))
    finally:
        release_cache_claim(run)
    return run


def execute(driver, operation, run, arguments):
    if operation == 'status':
        return reconcile(driver, run)
    if operation != 'build':
        raise ValueError('release operation not implemented: ' + operation)
    return advance(driver, run, arguments)
