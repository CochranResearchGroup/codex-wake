"""Durable native release runs over host-registered recipes and isolated worktrees."""
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time
import uuid

from codex_profiles.upgrades import _atomic
from .managed_inventory import InventoryError

VERBS = {'prepare', 'status', 'build', 'resume', 'qualify', 'cleanup', 'run'}


def digest(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(chunk)
    return value.hexdigest()


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def toolchain_version(worktree):
    tree = Path(worktree)
    cwd = tree / 'codex-rs' if (tree / 'codex-rs/rust-toolchain.toml').exists() else tree
    return subprocess.run(['rustc', '--version'], cwd=cwd, capture_output=True, text=True, check=True).stdout.strip()


class ReleaseDriver:
    def __init__(self, root, recipes):
        self.root = Path(root).absolute()
        self.recipes = recipes

    @contextmanager
    def locked(self):
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        if self.root.is_symlink() or self.root.stat().st_uid != os.getuid() or self.root.stat().st_mode & 0o077:
            raise ValueError('release storage must be private and owned')
        with (self.root / '.lock').open('a') as stream:
            fcntl.flock(stream, fcntl.LOCK_EX)
            yield

    def load(self, run_id):
        if not isinstance(run_id, str) or not re.fullmatch(r'[a-f0-9]{32}', run_id):
            raise ValueError('valid run_id required')
        path = self.root / run_id / 'manifest.json'
        value = json.loads(path.read_text())
        if value['run_id'] != run_id:
            raise ValueError('run identity mismatch')
        return value

    def save(self, run):
        _atomic(Path(run['manifest']), run)

    def event(self, run, kind, **details):
        event = dict(sequence=len(run['events']) + 1, at=time.time(), kind=kind, **details)
        run['events'].append(event)
        self.save(run)

    def snapshot(self, run):
        tree = Path(run['worktree'])
        git = ['git', '-C', str(tree)]
        revision = subprocess.check_output([*git, 'rev-parse', 'HEAD'], text=True).strip()
        changes = subprocess.check_output([*git, 'diff', '--binary', 'HEAD'])
        untracked = subprocess.check_output([*git, 'ls-files', '--others', '--exclude-standard', '-z']).split(b'\0')
        extra = {os.fsdecode(p): digest(tree / os.fsdecode(p)) for p in untracked if p}
        lock = tree / 'Cargo.lock'
        if not lock.exists():
            lock = tree / 'codex-rs/Cargo.lock'
        return dict(revision=revision, diff=hashlib.sha256(changes).hexdigest(), untracked=extra,
                    lockfile=digest(lock) if lock.exists() else None)

    def prepare(self, arguments):
        name = arguments.get('recipe')
        if name not in self.recipes:
            raise ValueError('recipe is not host registered')
        recipe_path = Path(self.recipes[name])
        recipe = json.loads(recipe_path.read_text())
        source = Path(recipe['source_repository']).resolve(strict=True)
        pins = {}
        for key in ('upstream', 'mod_revision'):
            ref = arguments.get(key)
            if not isinstance(ref, str) or not re.fullmatch(r'[a-fA-F0-9]{40}', ref):
                raise ValueError(key + ' must be a full commit SHA')
            pins[key] = subprocess.check_output(['git', '-C', str(source), 'rev-parse', '--verify', ref + '^{commit}'], text=True).strip()
        run_id = uuid.uuid4().hex
        directory = self.root / run_id
        directory.mkdir(mode=0o700)
        tree = directory / 'source'
        subprocess.run(['git', '-C', str(source), 'worktree', 'add', '--detach', str(tree), pins['mod_revision']],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        with (directory / 'integration.log').open('wb') as log:
            merged = subprocess.run(['git', '-C', str(tree), '-c', 'user.name=Release Driver',
                '-c', 'user.email=release-driver@example.invalid', 'merge', '--no-edit', pins['upstream']],
                stdout=log, stderr=subprocess.STDOUT)
        toolchain = toolchain_version(tree)
        run = dict(schema_version=1, run_id=run_id, recipe_name=name, recipe=recipe,
                   recipe_sha256=digest(recipe_path), source=dict(repository=str(source), **pins),
                   worktree=str(tree), manifest=str(directory / 'manifest.json'),
                   status='prepared' if merged.returncode == 0 else 'conflicted',
                   created_at=time.time(), toolchain=toolchain, build_environment={key: os.environ.get(key) for key in
                       ('RUSTFLAGS','RUSTDOCFLAGS','CARGO_ENCODED_RUSTFLAGS','CC','CXX','AR','V8_FROM_PREBUILT','V8_BASE_URL')}, stages={}, events=[])
        self.save(run)
        if merged.returncode == 0:
            run['source_snapshot'] = self.snapshot(run)
        self.event(run, 'prepared', status=run['status'])
        return run

    def execute(self, operation, arguments):
        allowed = {'recipe', 'upstream', 'mod_revision', 'run_id', 'jobs', 'output', 'max_items', 'confirm', 'expected_cache'}
        if not isinstance(arguments, dict) or set(arguments) - allowed:
            raise ValueError('unsupported release arguments')
        with self.locked():
            if operation == 'prepare':
                result = self.prepare(arguments)
            else:
                run = self.load(arguments.get('run_id'))
                if operation == 'status':
                    if run.get('stages'):
                        from .release_build import reconcile
                        reconcile(self, run)
                    if run.get('qualification'):
                        from .release_qualification import reconcile as reconcile_qualification
                        reconcile_qualification(self, run)
                    result = run
                elif operation in ('resume', 'qualify', 'cleanup', 'run'):
                    from importlib import import_module
                    module = import_module('.release_' + {'qualify':'qualification'}.get(operation, operation), __package__)
                    result = module.execute(self, operation, run, arguments)
                else:
                    from .release_build import execute
                    result = execute(self, operation, run, arguments)
            return self.present(result, arguments)

    def present(self, run, arguments):
        mode = arguments.get('output', 'compact')
        if mode not in ('compact', 'json', 'progress', 'diagnostics'):
            raise ValueError('invalid release output mode')
        bound = arguments.get('max_items', 8)
        if type(bound) != int or not 1 <= bound <= 40:
            raise ValueError('max_items must be 1..40')
        # Source/recipe metadata are needed for repeatable orchestration. Raw logs
        # are never copied into these public views.
        result = dict(run)
        result['events'] = run.get('events', [])[-bound:] if mode == 'progress' else []
        if mode != 'json':
            result['stages'] = {name: {k: v for k, v in stage.items() if k != 'attempts'}
                                for name, stage in run.get('stages', {}).items()}
        if mode == 'diagnostics':
            diagnostics = []
            for name, stage in run.get('stages', {}).items():
                receipt = stage.get('receipt') or {}
                if isinstance(receipt, dict):
                    for item in receipt.get('diagnostics', []):
                        diagnostics.append(dict(stage=name, diagnostic=item))
            result['diagnostics'] = diagnostics[:bound]
        return result
