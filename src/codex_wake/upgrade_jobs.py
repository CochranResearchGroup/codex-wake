"""Durable opt-in upgrade jobs. Recipes and executors are trusted host inputs.

The store lock fences control changes and promotion. Work runs in owned process
sessions outside the lock; every result is checked against the current generation.
"""
from __future__ import annotations

from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import uuid

from codex_profiles.upgrades import _atomic
from .managed_inventory import InventoryError

DEFAULT_LIMITS = dict(repair_attempts=3, total_seconds=7200, compiler_jobs=2,
                      temporary_bytes=24 * 1024**3)
TERMINAL = frozenset(('succeeded', 'failed', 'held', 'disabled', 'superseded'))
READS = frozenset(('status', 'list', 'show'))


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def process_identity(pid):
    try:
        value = Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()
        return {'pid': pid, 'start': value[19], 'boot': Path('/proc/sys/kernel/random/boot_id').read_text().strip()}
    except (OSError, IndexError):
        return None


class UpgradeJobs:
    def __init__(self, root, *, now=None, executor=None):
        self.root = Path(root)
        self.store = self.root / 'upgrade-jobs'
        self.now = now or time.time
        self.executor = executor

    def config(self):
        value = json.loads((self.root / 'upgrade-bot.json').read_text())
        if value.get('schema_version') != 1 or not isinstance(value.get('target'), dict) or not value['target']:
            raise InventoryError('invalid_configuration', 'versioned fixed upgrade target required')
        limits = dict(DEFAULT_LIMITS, **value.get('limits', {}))
        if set(limits) != set(DEFAULT_LIMITS) or any(type(v) is not int or v <= 0 for v in limits.values()):
            raise InventoryError('invalid_configuration', 'positive integer upgrade limits required')
        value['limits'] = limits
        value['recipes'] = dict(value.get('recipes', {}))
        catalog_path = self.store / 'generated-recipes.json'
        discovery = value.get('discovery', {})
        if discovery.get('recipe_template') and catalog_path.exists():
            template_sha = hashlib.sha256(Path(discovery['recipe_template']).read_bytes()).hexdigest()
            if template_sha != discovery.get('recipe_template_sha256'):
                raise InventoryError('stale_template', 'host recipe template pin changed')
            catalog = json.loads(catalog_path.read_text())
            if catalog.get('schema_version') != 1:
                raise InventoryError('unsupported_schema', 'generated recipe catalog schema unsupported')
            for name, row in catalog.get('recipes', {}).items():
                if row.get('template_sha256') != template_sha:
                    continue
                path = Path(row['path'])
                if hashlib.sha256(path.read_bytes()).hexdigest() != row['sha256']:
                    raise InventoryError('stale_recipe', 'generated recipe pin changed')
                value['recipes'][name] = str(path)
        return value

    def register_generated_recipe(self, name, path, expected_sha256):
        # Host-internal only: discovery can fill release/source identity, never
        # invent executable recipe instructions downloaded from the network.
        from codex_profiles.upgrades import official_source_url
        with self.locked():
            config = self.config()
            declaration = config.get('discovery', {})
            template_path = Path(declaration['recipe_template'])
            template = json.loads(template_path.read_text())
            template_sha = hashlib.sha256(template_path.read_bytes()).hexdigest()
            if template_sha != declaration.get('recipe_template_sha256'):
                raise InventoryError('stale_template', 'host recipe template pin required')
            path = Path(path).resolve(strict=True)
            if hashlib.sha256(path.read_bytes()).hexdigest() != expected_sha256:
                raise InventoryError('stale_recipe', 'generated recipe pin mismatch')
            recipe = json.loads(path.read_text())
            mutable = {'id','upstream_version','revision','source'}
            if {k:v for k,v in template.items() if k not in mutable} != {k:v for k,v in recipe.items() if k not in mutable}:
                raise InventoryError('unauthorized_target', 'generated recipe changed host execution policy')
            source = recipe.get('source', {})
            if not official_source_url(source.get('official_url')) or not isinstance(source.get('sha256'), str) or len(source['sha256']) != 64:
                raise InventoryError('invalid_source', 'pinned official source archive required')
            catalog_path = self.store / 'generated-recipes.json'
            catalog = json.loads(catalog_path.read_text()) if catalog_path.exists() else dict(schema_version=1,recipes={})
            previous = catalog['recipes'].get(name)
            row = dict(path=str(path), sha256=expected_sha256, template_sha256=template_sha, upstream_version=recipe.get('upstream_version'))
            if previous and previous != row:
                raise InventoryError('stale_recipe', 'generated recipe name already bound to other bytes')
            catalog['recipes'][name] = row
            _atomic(catalog_path, catalog)
            return row

    @contextmanager
    def locked(self):
        self.store.mkdir(parents=True, exist_ok=True, mode=0o700)
        with (self.store / '.lock').open('a') as stream:
            fcntl.flock(stream, fcntl.LOCK_EX)
            yield

    def load(self):
        path = self.store / 'state.json'
        if not path.exists():
            return dict(schema_version=1, enabled=False, generation=0, jobs={}, events=[])
        value = json.loads(path.read_text())
        if value.get('schema_version') != 1:
            raise InventoryError('unsupported_schema', 'upgrade state schema unsupported')
        return value

    def save(self, state):
        _atomic(self.store / 'state.json', state)

    def event(self, state, kind, job=None, **details):
        state['events'].append(dict(id=len(state['events']) + 1, kind=kind,
            job_id=job['id'] if job else None, at=self.now(), **details))

    def guard(self, actor, target, arguments, authorize, *, write=False):
        current = authorize() if authorize else actor
        if current.subject != actor.subject or ('admin' if write else 'observe') not in current.scopes:
            raise InventoryError('unauthorized_target', 'current upgrade grant required')
        if arguments.get('expected_target') != target or not any(
                all(target.get(k) == v for k, v in scope.items()) for scope in current.targets):
            raise InventoryError('unauthorized_target', 'exact host-configured upgrade scope required')

    def execute(self, actor, operation, arguments, *, authorize=None):
        verb = operation.removeprefix('upgrades.')
        allowed = dict(status=set(), list=set(), show={'job_id'}, enable=set(), disable=set(),
                       start={'recipe', 'expected_recipe_sha256', 'upstream_version'}, advance={'job_id'}, cancel={'job_id'})
        if not operation.startswith('upgrades.') or verb not in allowed or not isinstance(arguments, dict):
            raise InventoryError('invalid_argument', 'exact upgrade job arguments required')
        optional = {'expected_recipe_sha256', 'upstream_version'} if verb == 'start' else set()
        required = (allowed[verb] - optional) | {'expected_target'}
        if set(arguments) - (allowed[verb] | {'expected_target'}) or required - set(arguments):
            raise InventoryError('invalid_argument', 'exact upgrade job arguments required')
        config = self.config()
        self.guard(actor, config['target'], arguments, authorize, write=verb not in READS)
        if verb == 'advance':
            result = self.advance(actor, arguments, authorize)
        else:
            with self.locked():
                state = self.load()
                self.guard(actor, config['target'], arguments, authorize, write=verb not in READS)
                if verb == 'status':
                    result = dict(enabled=state['enabled'], generation=state['generation'],
                        limits=config['limits'], target=config['target'], events=state['events'],
                        notice_delivery=self.notice_summary())
                elif verb == 'list':
                    result = dict(jobs=list(state['jobs'].values()))
                elif verb in ('show', 'cancel'):
                    job = self.job(state, arguments['job_id'])
                    if verb == 'cancel' and job['state'] not in TERMINAL:
                        self.stop(job)
                        job.update(state='disabled', reason='cancelled_by_operator')
                        self.event(state, 'cancelled', job)
                    result = dict(job=job)
                elif verb in ('enable', 'disable'):
                    state['enabled'] = verb == 'enable'
                    state['generation'] += 1
                    if verb == 'disable':
                        for job in state['jobs'].values():
                            if job['state'] not in TERMINAL:
                                self.stop(job)
                                job.update(state='disabled', reason='disabled_by_operator')
                    self.event(state, verb)
                    result = dict(enabled=state['enabled'], generation=state['generation'])
                else:
                    if not state['enabled']:
                        raise InventoryError('upgrade_disabled', 'explicit upgrade enable required')
                    name = arguments['recipe']
                    if not isinstance(name, str) or name not in config.get('recipes', {}):
                        raise InventoryError('unauthorized_target', 'host-approved upgrade recipe required')
                    recipe_path = Path(config['recipes'][name]).resolve(strict=True)
                    recipe = json.loads(recipe_path.read_text())
                    if arguments.get('expected_recipe_sha256', hashlib.sha256(recipe_path.read_bytes()).hexdigest()) != hashlib.sha256(recipe_path.read_bytes()).hexdigest() or arguments.get('upstream_version', recipe.get('upstream_version')) != recipe.get('upstream_version'):
                        raise InventoryError('stale_recipe', 'resolved release recipe changed before job admission')
                    key = digest(dict(recipe=recipe, target=config['target']))
                    existing = next((j for j in state['jobs'].values() if j['key'] == key), None)
                    if existing:
                        result = dict(job=existing)
                    else:
                        if any(j['state'] not in TERMINAL for j in state['jobs'].values()):
                            raise InventoryError('upgrade_busy', 'one upgrade candidate at a time')
                        job = dict(id=uuid.uuid4().hex, key=key, recipe=name,
                            recipe_path=str(recipe_path), recipe_sha256=hashlib.sha256(recipe_path.read_bytes()).hexdigest(),
                            version=recipe.get('upstream_version'), target=config['target'], state='queued',
                            created_at=self.now(), deadline=self.now()+config['limits']['total_seconds'],
                            last_seen=self.now(), repair_attempts=0, limits=config['limits'], generation=state['generation'],
                            stage_id=recipe.get('id'), worker=None, results={})
                        state['jobs'][job['id']] = job
                        self.event(state, 'queued', job)
                        result = dict(job=job)
                self.save(state)
        if verb not in READS:
            self.notify(actor, authorize)
        return dict(schema_version=1, operation=operation, status='completed', result=result)

    def notice_summary(self):
        from .upgrade_notices import UpgradeNotices
        value=UpgradeNotices(self.root).summary()
        drain_status=self.store/'notice-drain-status.json'
        if drain_status.exists():value['last_drain']=json.loads(drain_status.read_text())
        return value

    def notify(self, actor, authorize):
        from .upgrade_notices import UpgradeNotices
        try:
            UpgradeNotices(self.root).drain(actor, authorize=authorize or (lambda: actor))
            _atomic(self.store/'notice-drain-status.json',dict(status='completed',at=self.now()))
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
            # Notice delivery is independently observable, never grounds for
            # changing an already committed upgrade outcome or replaying work.
            _atomic(self.store/'notice-drain-status.json', dict(status='failed',
                reason=getattr(error,'code',type(error).__name__),at=self.now()))

    def job(self, state, identifier):
        if not isinstance(identifier, str) or identifier not in state['jobs']:
            raise InventoryError('unknown_job', 'unknown upgrade job')
        return state['jobs'][identifier]

    def stop(self, job):
        worker = job.get('worker')
        if worker and process_identity(worker['pid']) == worker:
            try:
                os.killpg(worker['pid'], signal.SIGTERM)
            except ProcessLookupError:
                pass
        job['worker'] = None

    def budget_reason(self, job):
        now = self.now()
        if now < job['last_seen']:
            return 'clock_uncertain'
        job['last_seen'] = now
        if now >= job['deadline']:
            return 'deadline_exhausted'
        workspace = self.store / job['id']
        size = sum(p.lstat().st_size for p in workspace.rglob('*') if p.is_file() and not p.is_symlink()) if workspace.exists() else 0
        if size > job['limits']['temporary_bytes']:
            return 'temporary_storage_exhausted'
        return None

    def advance(self, actor, arguments, authorize):
        with self.locked():
            state = self.load()
            job = self.job(state, arguments['job_id'])
            self.guard(actor, job['target'], arguments, authorize, write=True)
            if job['state'] in TERMINAL:
                return dict(job=job)
            reason = self.budget_reason(job)
            if not state['enabled'] or reason:
                job.update(state='held', reason=reason or 'upgrade_disabled')
                self.event(state, 'held', job, reason=job['reason'])
                self.save(state)
                return dict(job=job)
            if job.get('active_phase') and not job['worker']:
                job.update(state='held', reason='worker_intent_pending_reconciliation')
                self.event(state, 'held', job, reason=job['reason'])
                self.save(state)
                return dict(job=job)
            if job['worker']:
                if process_identity(job['worker']['pid']) == job['worker']:
                    raise InventoryError('upgrade_busy', 'owned upgrade worker remains active')
                job.update(state='held', reason='worker_lost_reconcile_required')
                self.event(state, 'held', job, reason=job['reason'])
                self.save(state)
                return dict(job=job)
            config = self.config()
            if str(Path(config['recipes'].get(job['recipe'], '')).resolve()) != job['recipe_path'] or hashlib.sha256(Path(job['recipe_path']).read_bytes()).hexdigest() != job['recipe_sha256']:
                raise InventoryError('stale_recipe', 'pinned upgrade recipe changed')
            phase = 'qualify' if job['state'] == 'qualifying' else 'stage'
            job['active_phase'] = phase
            job['state'] = 'qualifying' if phase == 'qualify' else 'building'
            self.event(state, job['state'], job)
            self.save(state)
            frozen = json.loads(json.dumps(job))
        self.notify(actor, authorize)
        try:
            def guard():
                with self.locked():
                    current_state=self.load();current=self.job(current_state,frozen['id'])
                    self.guard(actor,current['target'],arguments,authorize,write=True)
                    reason=self.budget_reason(current)
                    self.save(current_state)
                    if not current_state['enabled'] or current['state'] in TERMINAL or current_state['generation'] != frozen['generation'] or reason:
                        raise ValueError(reason or 'upgrade_policy_changed')
            def checkpoint(delta):
                guard()
                with self.locked():
                    current_state=self.load();current=self.job(current_state,frozen['id'])
                    value=delta['repair_attempts']
                    if type(value) is not int or value<current['repair_attempts'] or value>current['limits']['repair_attempts']:
                        raise ValueError('invalid_repair_budget_checkpoint')
                    current['repair_attempts']=value
                    self.save(current_state)
            if self.executor:
                result=self.executor(frozen)
            elif frozen['active_phase']=='qualify':
                from .upgrade_qualification import UpgradeQualification
                if not config.get('qualification'):
                    result=dict(status='held',reason='disposable_qualification_not_configured')
                else:
                    result=UpgradeQualification(self.root).run(frozen,config['qualification'],guard=guard)
            else:
                from .upgrade_pipeline import prepare_reviewed_recipe
                repair=prepare_reviewed_recipe(self.root,frozen,config,guard=guard,checkpoint=checkpoint)
                if repair is not None:
                    with self.locked():
                        current_state=self.load();current=self.job(current_state,frozen['id'])
                        current['results']['repair']=repair
                        self.save(current_state)
                    if repair.get('status')!='reviewed':
                        result=dict(status='held',reason=repair.get('reason','semantic_repair_held'))
                    else:
                        frozen['prepared_recipe']=repair['prepared_recipe']
                        result=self.run_stage(frozen)
                else:
                    result=self.run_stage(frozen)
            if not isinstance(result, dict):
                raise ValueError('upgrade executor returned no structured outcome')
        except Exception as error:
            result = dict(status='failed', reason=str(error))
        with self.locked():
            state = self.load();job = self.job(state, frozen['id'])
            self.guard(actor, job['target'], arguments, authorize, write=True)
            if job['state'] in TERMINAL:
                return dict(job=job)
            reason = self.budget_reason(job)
            job['worker'] = None
            job['active_phase'] = None
            job['results']['qualification' if frozen['active_phase']=='qualify' else 'stage'] = result
            if not state['enabled'] or state['generation'] != frozen['generation'] or reason:
                job.update(state='held', reason=reason or 'policy_changed')
            elif result.get('status') == 'qualified':
                job.update(state='promoting', reason='awaiting_qualified_selection')
            elif result.get('status') == 'staged':
                job.update(state='qualifying', reason='awaiting_disposable_qualification')
            else:
                job.update(state='held', reason=result.get('reason', 'stage_failed'))
            self.event(state, job['state'], job, reason=job['reason'])
            self.save(state)
            return dict(job=job)

    def run_stage(self, job):
        directory = self.store / job['id'];directory.mkdir(mode=0o700, exist_ok=True)
        recipe_bytes = Path(job.get('prepared_recipe',job['recipe_path'])).read_bytes()
        if not job.get('prepared_recipe') and hashlib.sha256(recipe_bytes).hexdigest() != job['recipe_sha256']:
            raise InventoryError('stale_recipe', 'pinned upgrade recipe changed')
        frozen_recipe = directory / 'recipe.json'
        _atomic(frozen_recipe, json.loads(recipe_bytes))
        # Child inherits no Codex credentials; build recipes are host-owned.
        with tempfile.TemporaryDirectory(prefix='worker-home-', dir=directory) as home:
            env = {k:v for k,v in os.environ.items() if k in ('PATH','LANG','LC_ALL','PYTHONPATH')}
            env.update(CODEX_UPGRADE_TEMP_ROOT=str(directory), CODEX_UPGRADE_OWNED_GROUP='1', HOME=home, CODEX_HOME=home+'/.codex', XDG_CONFIG_HOME=home+'/.config',
                XDG_DATA_HOME=home+'/.local/share', CARGO_BUILD_JOBS=str(job['limits']['compiler_jobs']))
            Path(env['CODEX_HOME']).mkdir(mode=0o700)
            output = directory / 'stage-result.json'
            with (directory / 'worker.log').open('ab') as log:
                process = subprocess.Popen([sys.executable, '-m', 'codex_wake.upgrade_stage_worker',
                    str(directory / 'build-store'), str(frozen_recipe), str(output)],
                    env=env, stdout=log, stderr=log, start_new_session=True)
                identity = process_identity(process.pid)
                with self.locked():
                    state=self.load();current=self.job(state,job['id'])
                    if current['state'] in TERMINAL or not state['enabled'] or current['generation'] != state['generation']:
                        process.terminate()
                    else:
                        current['worker']=identity
                    self.save(state)
                try:
                    while process.poll() is None:
                        with self.locked():
                            state=self.load();current=self.job(state,job['id'])
                            reason=self.budget_reason(current)
                            stopped=current['state'] in TERMINAL or not state['enabled'] or reason
                            if stopped:
                                self.stop(current)
                                if reason:current.update(state='held',reason=reason)
                            self.save(state)
                        if stopped:
                            try:process.wait(timeout=2)
                            except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL)
                            break
                        time.sleep(.1)
                    process.wait()
                finally:
                    try:os.killpg(process.pid,signal.SIGKILL)
                    except ProcessLookupError:pass
                if output.is_file():return json.loads(output.read_text())
                return dict(status='failed',reason='stage_worker_exit_'+str(process.returncode))
