"""Preview and explicitly retire one owned inactive Cargo cache.

The controller performs all gates before renaming the pinned directory and using
Python's fd-based rmtree. A failed gate never invokes the cleaner. Unrelated
protected processes are an observation limit, not a universal cleanup veto.
"""
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import uuid

from .release_driver import fingerprint

ACTIVE = {'running', 'submitting', 'unknown'}


def beneath(path, root):
    return path == root or path.is_relative_to(root)


def tree_identity(path):
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode) or path.is_symlink() or info.st_uid != os.getuid():
        raise ValueError('cache must be an owned regular directory')
    entries = []
    for parent, directories, files in os.walk(path, followlinks=False):
        for name in sorted([*directories, *files]):
            child = Path(parent) / name
            item = child.lstat()
            entries.append([str(child.relative_to(path)), item.st_dev, item.st_ino,
                            item.st_mode, item.st_uid, item.st_size,
                            item.st_mtime_ns, item.st_ctime_ns,
                            os.readlink(child) if child.is_symlink() else None])
    return dict(device=info.st_dev, inode=info.st_ino, owner=info.st_uid,
                mode=info.st_mode, modified=info.st_mtime_ns, changed=info.st_ctime_ns,
                contents=fingerprint(sorted(entries)))


def cache_path(run):
    value = run.get('target_directory', run['recipe'].get('target_directory', 'target'))
    path = Path(value)
    return path if path.is_absolute() else Path(run['worktree']) / path


def protected_paths(driver, run, target):
    """Return scope errors, including data retained by any other release run."""
    reasons = []
    tree = Path(run['worktree']).resolve()
    store = driver.root.resolve()
    if target == tree or beneath(tree, target) or target == store or beneath(store, target):
        reasons.append('cache overlaps source or release storage root')
    # An internal cache has the conventional Cargo target name. Custom cache
    # locations may be outside the worktree; source directories are never caches.
    if target.is_relative_to(tree) and target.name != 'target':
        reasons.append('internal cleanup target must be a Cargo target directory')
    protected = [Path(run['manifest']).resolve(), tree / '.git']
    source = Path(run['source']['repository']).resolve()
    if beneath(target, source) or beneath(source, target):
        reasons.append('cache overlaps the retained source repository')
    for manifest in driver.root.glob('*/manifest.json'):
        state = json.loads(manifest.read_text())
        protected.extend([manifest.resolve(), manifest.parent / 'jobs', manifest.parent / 'qualification', manifest.parent / 'integration.log'])
        recipe = state['recipe']
        worktree = Path(state['worktree']).resolve()
        if state.get('package', {}).get('path'):
            protected.append(Path(state['package']['path']).resolve())
        if recipe.get('package_directory'):
            protected.append((worktree / recipe['package_directory']).resolve())
        if recipe.get('retained_package', {}).get('path'):
            protected.append(Path(recipe['retained_package']['path']).resolve())
        for key in ('rollback_artifacts', 'protected_paths', 'evidence_paths'):
            for value in recipe.get(key, []):
                protected.append((worktree / value).resolve())
        for value in recipe.get('qualification', {}).get('preflight', {}).get('files', []):
            protected.append((worktree / value).resolve())
        for step in recipe.get('build_steps', []):
            protected.extend((worktree / value).resolve() for value in step.get('inputs', []))
        protected.extend((worktree / value).resolve() for value in state.get('source_snapshot', {}).get('untracked', {}))
        if beneath(worktree, target) or beneath(target, worktree):
            tracked = subprocess.check_output(['git', '-C', str(worktree), 'ls-files', '-z'])
            protected.extend((worktree / os.fsdecode(value)).resolve() for value in tracked.split(b'\0') if value)
        for stage in state.get('stages', {}).values():
            if stage.get('status') in ACTIVE and cache_path(state).resolve() == target:
                reasons.append('cache has an active or unresolved release stage')
    if any(beneath(value, target) or beneath(target, value) for value in protected):
        reasons.append('cache overlaps source inputs, package, rollback or evidence')
    claims = driver.root / 'cache-claims'
    for path in claims.glob('*.json'):
        claim = json.loads(path.read_text())
        if Path(claim['cache']).resolve() == target:
            reasons.append('cache has an unresolved writer claim')
    return sorted(set(reasons))


def live_references(target):
    found = []
    visibility = dict(unrelated_protected_processes=0, relevant_unknown_processes=[])
    for process in Path('/proc').glob('[0-9]*'):
        pid = int(process.name)
        if pid == os.getpid():
            continue
        relevant = False
        incomplete = False
        try:
            command = (process / 'comm').read_text().strip()
        except (OSError, UnicodeError):
            command = ''
        def inspect_link(link):
            nonlocal relevant, incomplete
            try:
                value = os.readlink(link).removesuffix(' (deleted)')
                if value.startswith('/') and beneath(Path(value), target):
                    relevant = True
            except FileNotFoundError:
                pass
            except OSError:
                incomplete = True
        inspect_link(process / 'cwd')
        inspect_link(process / 'exe')
        try:
            argv = (process / 'cmdline').read_bytes()[:65536].split(b'\0')
            for raw in argv:
                value = os.fsdecode(raw).split('=', 1)[-1]
                if value.startswith('/') and beneath(Path(value), target):
                    relevant = True
            environment = (process / 'environ').read_bytes().split(b'\0')
            for raw in environment:
                if raw.startswith(b'CARGO_TARGET_DIR='):
                    value = Path(os.fsdecode(raw.split(b'=', 1)[1]))
                    if value.is_absolute() and beneath(value, target):
                        relevant = True
            for descriptor in (process / 'fd').iterdir():
                inspect_link(descriptor)
            with (process / 'maps').open() as stream:
                for line in stream:
                    if str(target) not in line:
                        continue
                    fields = line.split(maxsplit=5)
                    if len(fields) == 6:
                        value = fields[5].strip().removesuffix(' (deleted)')
                        if value.startswith('/') and beneath(Path(value), target):
                            relevant = True
        except FileNotFoundError:
            continue
        except (OSError, UnicodeError):
            incomplete = True
        if relevant:
            found.append(pid)
        elif incomplete and command in ('cargo', 'rustc', 'sccache'):
            visibility['relevant_unknown_processes'].append(pid)
        elif incomplete:
            visibility['unrelated_protected_processes'] += 1
    return sorted(set(found)), visibility


def preflight(driver, run):
    raw = cache_path(run).absolute()
    target = raw.resolve()
    if raw != target:
        raise ValueError('cache aliases and symlinks are not cleanup targets')
    reasons = protected_paths(driver, run, target)
    identity = tree_identity(target) if target.exists() else None
    references, visibility = live_references(target)
    if references:
        reasons.append('cache has live process references: ' + ','.join(map(str, references)))
    if visibility['relevant_unknown_processes']:
        reasons.append('relevant build process visibility is incomplete')
    if not shutil.rmtree.avoids_symlink_attacks:
        reasons.append('fd-safe directory cleanup unavailable')
    pin = fingerprint(dict(path=str(target), identity=identity))
    return dict(status='preview' if identity else 'absent', eligible=not reasons,
                cache=str(target), expected_cache=pin, identity=identity,
                reasons=sorted(set(reasons)), protected_process_visibility=visibility)


def execute(driver, operation, run, arguments):
    if operation != 'cleanup':
        raise ValueError('unsupported cleanup operation')
    confirm = arguments.get('confirm', False)
    if type(confirm) is not bool:
        raise ValueError('cleanup confirmation must be boolean')
    try:
        report = preflight(driver, run)
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        report = dict(status='refused', eligible=False, cache=str(cache_path(run)), reasons=[str(error)])
    if report['eligible'] and confirm:
        if arguments.get('expected_cache') != report['expected_cache']:
            report.update(status='refused', eligible=False)
            report['reasons'].append('cache identity changed or preview pin missing')
        elif report['identity'] is not None:
            target = Path(report['cache'])
            quarantine = target.with_name('.' + target.name + '.cleanup-' + uuid.uuid4().hex)
            # Only the previously validated directory moves; a newly created
            # target at the old path is never followed or removed.
            try:
                target.rename(quarantine)
                moved = tree_identity(quarantine)
                references, visibility = live_references(quarantine)
                if (moved['device'], moved['inode'], moved['contents']) != (
                        report['identity']['device'], report['identity']['inode'], report['identity']['contents']) or references or visibility['relevant_unknown_processes']:
                    raise ValueError('cache changed or acquired a live reference before cleanup')
            except (OSError, ValueError) as error:
                if quarantine.exists() and not target.exists():
                    quarantine.rename(target)
                report.update(status='refused', eligible=False,
                              retained_path=str(quarantine if quarantine.exists() else target))
                report['reasons'].append(str(error))
            else:
                try:
                    shutil.rmtree(quarantine)
                    report['status'] = 'cleaned'
                except OSError as error:
                    report.update(status='failed', eligible=False, retained_path=str(quarantine))
                    report['reasons'].append(str(error))
    elif not report['eligible']:
        report['status'] = 'refused'
    run['cleanup'] = report
    driver.event(run, 'cache_cleanup', status=report['status'], cache=report['cache'])
    return run
