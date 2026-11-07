"""Reconcile durable workers and selectively resume native release build stages."""
import subprocess

from .release_driver import toolchain_version
from .release_build import (
    adoption_binding, advance, package_inventory, reconcile, release_cache_claim, resource_limits,
    stage_definitions, stage_fingerprint, verify_outputs,
)

ACTIVE = {'running', 'submitting', 'unknown'}


def dependencies(steps):
    """Recipes execute in declared order; prerequisites must already be declared."""
    previous = []
    result = {}
    for step in steps:
        parents = step.get('depends_on', previous[-1:])
        if not isinstance(parents, list) or any(not isinstance(p, str) or p not in previous for p in parents):
            raise ValueError('stage dependencies must name preceding steps without cycles')
        result[step['name']] = set(parents)
        previous.append(step['name'])
    return result


def resolved_source(driver, run):
    if run['status'] != 'conflicted':
        return
    git = ['git', '-C', run['worktree']]
    if subprocess.check_output([*git, 'ls-files', '-u']):
        raise ValueError('resolve isolated integration conflicts before resuming')
    merging = subprocess.run([*git, 'rev-parse', '--verify', 'MERGE_HEAD'], capture_output=True)
    if merging.returncode == 0:
        raise ValueError('commit the resolved isolated integration before resuming')
    ancestry = subprocess.run([*git, 'merge-base', '--is-ancestor', run['source']['upstream'], 'HEAD'])
    if ancestry.returncode:
        raise ValueError('resolved source must retain the pinned upstream integration')
    run['source_snapshot'] = driver.snapshot(run)
    run['status'] = 'prepared'
    driver.event(run, 'integration_resolved')


def invalid_stages(driver, run, steps, graph):
    invalid = set()
    for step in steps:
        name = step['name']
        stage = run['stages'].get(name)
        if not stage:
            continue
        try:
            matches = stage_fingerprint(driver, run, step) == stage.get('input_fingerprint')
        except (OSError, ValueError):
            matches = False
        if (stage.get('status') != 'passed' or not matches
                or not verify_outputs(run, step, stage.get('outputs', {}))):
            invalid.add(name)
    for step in steps:
        if graph[step['name']] & invalid:
            invalid.add(step['name'])
    return invalid


def execute(driver, operation, run, arguments):
    if operation != 'resume':
        raise ValueError('unsupported release resume operation')
    resolved_source(driver, run)
    steps = stage_definitions(run)
    graph = dependencies(steps)
    # Reconciliation never launches work. Even a lost submission response must
    # remain held until a concrete terminal outcome is available.
    try:
        reconcile(driver, run)
    except (OSError, ValueError) as error:
        pending = [stage for stage in run['stages'].values() if stage.get('status') in ACTIVE]
        if not pending:
            raise
        for stage in pending:
            stage['status'] = 'unknown'
            stage['failure'] = 'worker reconciliation unavailable: ' + str(error)
        run['status'] = 'unknown'
        driver.save(run)
    active = [name for name, stage in run['stages'].items() if stage.get('status') in ACTIVE]
    if active:
        summary = run.setdefault('resume_summary', dict(reused=[], invalidated=[], executed=[], unresolved=[]))
        summary['unresolved'] = active
        driver.save(run)
        return run
    # Effective toolchain and explicit job overrides are build inputs. Keep
    # recorded settings fixed while any prior worker remains unresolved.
    toolchain = toolchain_version(run['worktree'])
    run['toolchain'] = toolchain
    if arguments.get('jobs') is not None and arguments['jobs'] != run.get('resources', {}).get('jobs'):
        run['resources'] = resource_limits(run, arguments)
    invalid = invalid_stages(driver, run, steps, graph)
    retained = run.get('package', {})
    if retained.get('reused'):
        binding = retained.get('binding', {})
        changed = (driver.snapshot(run) != run.get('source_snapshot') or
                   any(binding.get(key) != value for key, value in adoption_binding(driver, run).items()) or
                   binding.get('toolchain') not in (None, 'unknown', toolchain))
        if changed:
            run['retained_invalidated'] = True
            invalid.update(step['name'] for step in steps)
    names = [step['name'] for step in steps]
    continuing = run.get('resume_plan_active', False)
    if not continuing or invalid:
        summary = run.get('resume_summary') if continuing else None
        if summary is None:
            summary = dict(reused=[], invalidated=[], executed=[], unresolved=[])
        for name in names:
            stage = run['stages'].get(name)
            if name in invalid:
                if name not in summary['invalidated']:
                    summary['invalidated'].append(name)
                if stage:
                    # Attempt records are historical evidence, not mutable state.
                    stage['status'] = 'invalidated'
                if name in summary['reused']:
                    summary['reused'].remove(name)
            elif stage and stage.get('status') == 'passed' and name not in summary['executed'] and name not in summary['reused']:
                summary['reused'].append(name)
        summary['unresolved'] = []
        run['resume_summary'] = summary
    else:
        summary = run['resume_summary']
        summary['unresolved'] = []
    if invalid:
        # Package/qualification evidence remains in events and receipts, while
        # the current acceptance is withdrawn until the affected stages pass.
        if run.get('package'):
            run.setdefault('prior_packages', []).append(run.pop('package'))
        run.pop('qualification', None)
        run['status'] = 'prepared'
        run.pop('failure', None)
        release_cache_claim(run)
        driver.event(run, 'stages_invalidated', stages=[name for name in names if name in invalid])
    elif run['status'] in ('built', 'qualified'):
        package = run.get('package')
        if not package or package_inventory(run, package['path'])['files'] != package['files']:
            raise ValueError('completed package bytes changed outside declared outputs')
        run['resume_plan_active'] = False
        driver.save(run)
        return run
    elif run['status'] in ('failed', 'unknown'):
        run['status'] = 'prepared'
        run.pop('failure', None)
    before = {name: len(stage.get('attempts', [])) for name, stage in run['stages'].items()}
    run['resume_plan_active'] = True
    result = advance(driver, run, arguments)
    for name in names:
        count = len(result['stages'].get(name, {}).get('attempts', []))
        if count > before.get(name, 0) and name not in summary['executed']:
            summary['executed'].append(name)
    if result['status'] in ('built', 'qualified'):
        result['resume_plan_active'] = False
    driver.save(result)
    return result
