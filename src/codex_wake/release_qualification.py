"""Evidence-bound native qualification using host-declared disposable helpers.

Recipe qualification: environment {kind, uid, shared_kernel}, optional preflight
{executables, files, python_modules}, steps [{name, argv, cwd?, report?, timeout_seconds?}].
Argv placeholders: {package}, {run_dir}, {report}, {run_id}. Each fresh report is
schema_version=1,state=passed,uid,package_inventory_sha256,external_model_calls=0,
owned_processes=[],checks={check: true}. Steps may cover complementary checks.
"""
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import time
import uuid

from .release_build import package_inventory
from .release_driver import digest, fingerprint
from .release_signal import SignalClient

CHECKS = ('history', 'active_multiclient', 'reconnect', 'private_ownership',
          'upgrade', 'rollback', 'failed_start')


def _configuration(run):
    value = run['recipe'].get('qualification')
    if not isinstance(value, dict):
        raise ValueError('host qualification recipe required')
    environment = value.get('environment', {})
    if environment.get('kind') not in ('separate_uid', 'disposable_wsl', 'owned_fixture'):
        raise ValueError('approved disposable qualification environment required')
    if type(environment.get('uid')) is not int or environment['uid'] < 0:
        raise ValueError('qualification environment UID required')
    if environment['kind'] == 'separate_uid' and environment['uid'] == os.getuid():
        raise ValueError('separate UID qualification cannot use working UID')
    steps = value.get('steps')
    if not isinstance(steps, list) or not steps:
        raise ValueError('qualification helper steps required')
    names = set()
    for step in steps:
        name = step.get('name')
        if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', name) or name in names:
            raise ValueError('unique qualification helper names required')
        names.add(name)
        argv = step.get('argv')
        if not isinstance(argv, list) or not argv or any(not isinstance(x, str) or '\0' in x for x in argv):
            raise ValueError('qualification helpers require explicit argv arrays')
        report = step.get('report', 'report.json')
        if not isinstance(report, str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,100}', report) or report in ('.', '..'):
            raise ValueError('qualification report must be a basename')
        timeout = step.get('timeout_seconds', 1800)
        if type(timeout) is not int or not 1 <= timeout <= 7200:
            raise ValueError('qualification timeout must be 1..7200 seconds')
    return value


def _binding(driver, run):
    package = package_inventory(run, run['package']['path'])
    if package['files'] != run['package']['files']:
        raise ValueError('package bytes changed before qualification')
    return fingerprint(dict(source=driver.snapshot(run), package=package,
                            qualification=_configuration(run)))


def _preflight(run, configuration):
    requirements = configuration.get('preflight', {})
    for executable in requirements.get('executables', []):
        if not shutil.which(executable):
            raise ValueError('qualification executable unavailable: ' + executable)
    for step in configuration['steps']:
        if not shutil.which(step['argv'][0]):
            raise ValueError('qualification helper executable unavailable: ' + step['argv'][0])
    for name in requirements.get('files', []):
        path = Path(name)
        if not path.is_absolute():
            path = Path(run['worktree']) / path
        if not path.is_file():
            raise ValueError('qualification helper asset unavailable: ' + name)
    for module in requirements.get('python_modules', []):
        if importlib.util.find_spec(module) is None:
            raise ValueError('qualification Python dependency unavailable: ' + module)


def _fail(driver, run, qualification, reason):
    qualification.update(status='failed', failure=reason)
    run['status'] = 'failed'
    driver.event(run, 'qualification_failed', reason=reason)
    return run


def _read_report(run, qualification, stage):
    path = Path(stage['report'])
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 1024 * 1024:
        raise ValueError('fresh bounded qualification report unavailable')
    report = json.loads(path.read_text())
    if not isinstance(report, dict) or report.get('schema_version') != 1 or report.get('state') != 'passed':
        raise ValueError('qualification report did not pass')
    if type(report.get('uid')) is not int or report['uid'] != qualification['environment']['uid']:
        raise ValueError('qualification report environment UID mismatch')
    if report.get('package_inventory_sha256') != run['package']['inventory_sha256']:
        raise ValueError('qualification report package identity mismatch')
    if type(report.get('external_model_calls')) is not int or report['external_model_calls'] != 0:
        raise ValueError('qualification report must prove zero external model calls')
    if report.get('owned_processes') != []:
        raise ValueError('qualification report must prove empty final owned-process census')
    checks = report.get('checks')
    if not isinstance(checks, dict) or any(value is not True for value in checks.values()):
        raise ValueError('qualification report has failed or unknown checks')
    stage['report_sha256'] = digest(path)
    stage['checks'] = checks
    stage['report_environment'] = dict(uid=report['uid'], external_model_calls=0, owned_processes=[])
    qualification['checks'].update(checks)


def reconcile(driver, run):
    """Observe existing qualification only; this function never submits a job."""
    qualification = run.get('qualification')
    if not qualification:
        return run
    for name, stage in qualification['steps'].items():
        if stage['status'] not in ('running', 'submitting', 'unknown'):
            continue
        if not stage.get('job_dir'):
            stage['status'] = qualification['status'] = run['status'] = 'unknown'
            driver.save(run)
            return run
        with SignalClient(run['recipe'].get('cargo_signal', 'cargo-signal')) as client:
            receipt = client.call('get_command_status', dict(job_dir=stage['job_dir'], brief=False))
        stage['receipt'] = receipt
        if receipt['status'] == 'running':
            run['status'] = 'qualifying'
            driver.save(run)
            return run
        if receipt['status'] == 'unknown':
            stage['status'] = qualification['status'] = run['status'] = 'unknown'
            driver.save(run)
            return run
        attempt = stage['attempts'][-1]
        attempt.update(finished_at=time.time(), receipt=receipt)
        try:
            if receipt['status'] != 'passed' or receipt.get('exit_code') != 0:
                raise ValueError('qualification helper failed')
            if _binding(driver, run) != qualification['input_fingerprint']:
                raise ValueError('source or package inputs changed during qualification')
            _read_report(run, qualification, stage)
        except (OSError, ValueError, KeyError) as error:
            stage['status'] = attempt['status'] = 'failed'
            return _fail(driver, run, qualification, str(error))
        stage['status'] = attempt['status'] = 'passed'
        driver.event(run, 'qualification_step_finished', stage=name, status='passed')
    # Resolve submitted effects before withdrawing their input acceptance.
    # A changed source must never make a live helper disappear from custody.
    try:
        if _binding(driver, run) != qualification['input_fingerprint']:
            raise ValueError('source or package inputs changed during qualification')
        for stage in qualification['steps'].values():
            if stage['status'] == 'passed' and digest(stage['report']) != stage['report_sha256']:
                raise ValueError('retained qualification report changed')
    except (OSError, ValueError, KeyError) as error:
        return _fail(driver, run, qualification, str(error))
    return run


def execute(driver, operation, run, arguments):
    if operation != 'qualify':
        raise ValueError('unsupported qualification operation')
    if 'package' not in run:
        raise ValueError('complete built package required before qualification')
    configuration = _configuration(run)
    _preflight(run, configuration)
    qualification = run.get('qualification')
    if qualification:
        reconcile(driver, run)
        if qualification['status'] in ('failed', 'unknown', 'passed'):
            return run
    else:
        binding = _binding(driver, run)
        if run['status'] != 'built':
            raise ValueError('complete built package required before qualification')
        qualification = run['qualification'] = dict(status='running', input_fingerprint=binding,
            environment=configuration['environment'], checks={}, steps={},
            evidence_scope='fixture_only' if configuration['environment']['kind'] == 'owned_fixture' else 'disposable_runtime',
            working_installation_eligible=False)
        driver.save(run)
    binding = qualification['input_fingerprint']
    if any(stage['status'] in ('running', 'submitting', 'unknown') for stage in qualification['steps'].values()):
        return run
    for step in configuration['steps']:
        name = step['name']
        if qualification['steps'].get(name, {}).get('status') == 'passed':
            continue
        attempt_id = uuid.uuid4().hex
        directory = Path(run['manifest']).parent / 'qualification' / attempt_id
        directory.mkdir(mode=0o700, parents=True)
        report = directory / step.get('report', 'report.json')
        replacements = dict(package=run['package']['path'], run_dir=str(directory),
                            report=str(report), run_id=run['run_id'])
        argv = [arg for arg in step['argv']]
        for index, arg in enumerate(argv):
            for token, value in replacements.items():
                arg = arg.replace('{' + token + '}', value)
            argv[index] = arg
        cwd = Path(step.get('cwd', run['worktree']))
        if not cwd.is_absolute():
            cwd = Path(run['worktree']) / cwd
        if not cwd.is_dir():
            raise ValueError('qualification working directory unavailable')
        stage = dict(status='submitting', report=str(report), attempts=[dict(id=attempt_id,
            started_at=time.time(), argv=argv, cwd=str(cwd), input_fingerprint=binding)])
        qualification['steps'][name] = stage
        run['status'] = 'qualifying'
        driver.event(run, 'qualification_step_submitting', stage=name)
        try:
            with SignalClient(run['recipe'].get('cargo_signal', 'cargo-signal')) as client:
                started = client.call('start_command', dict(argv=argv, cwd=str(cwd), artifact_root=str(directory),
                    max_items=arguments.get('max_items', 8), timeout_seconds=step.get('timeout_seconds', 1800)))
            stage.update(status=started['status'], job_dir=started['job_dir'])
            stage['attempts'][-1]['job_dir'] = started['job_dir']
            driver.save(run)
        except (OSError, ValueError, KeyError) as error:
            stage['status'] = qualification['status'] = run['status'] = 'unknown'
            qualification['failure'] = 'qualification submission unresolved: ' + str(error)
            driver.save(run)
        return run
    missing = [name for name in CHECKS if qualification['checks'].get(name) is not True]
    if missing:
        return _fail(driver, run, qualification, 'qualification checks missing or unknown: ' + ', '.join(missing))
    qualification.update(status='passed', completed_at=time.time())
    run['status'] = 'qualified'
    driver.event(run, 'qualified', evidence_scope=qualification['evidence_scope'])
    return run
