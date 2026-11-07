"""Private configuration adoption under the existing migration custody owner.

Native authentication, histories and runtime control state stay at their original
inodes. Only explicit configuration assets are copied; linked native state needs
its supported native owner and is refused rather than cloned.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import tomllib

from .controller_accounts import account_inventory
from .goal_supervision import _save
from .managed_inventory import InventoryError

ASSETS = {'config.toml', 'skills', 'rules', 'hooks', 'hooks.json', 'AGENTS.md'}


def preview(owner, data, settings, scope, marker, paths):
    from .controller_migration import _tree, _links, _digest, _secret_name
    names, inactive = account_inventory(settings, data)
    holds, entries, plan, sources = [], {}, [], {}
    homes = [settings.account_root(name) for name in names]
    if not homes:
        holds.append('explicit_profile_selection_required')
    candidate = paths['candidate_root']
    for home in homes:
        if home.is_symlink() or home != home.resolve() or not home.is_dir():
            holds.append('profile_home_requires_canonical_private_directory')
            continue
        if home == settings.source_root or home.is_relative_to(settings.source_root) or settings.source_root.is_relative_to(home):
            holds.append('stock_profile_roots_overlap')
        if candidate.is_relative_to(home) or owner.root.resolve().is_relative_to(home):
            holds.append('adoption_custody_overlaps_profile')
        found, links = _tree(home, scope)
        entries.update(found)
        for value, metadata in found.items():
            path = Path(value)
            if metadata['kind'] == 'file' and path.stat().st_nlink > 1:
                holds.append('hardlinked_profile_state_requires_native_owner')
            if metadata['kind'] != 'link':
                continue
            relative = path.relative_to(home)
            if relative.parts[0] not in ASSETS:
                holds.append('linked_native_or_unknown_state_requires_native_owner')
                continue
            try:
                link = _links(path)
                source = Path(link['resolved'])
                if not link['exists'] or not source.is_relative_to(scope) or source.is_relative_to(home):
                    raise ValueError()
                if path.name == 'config.toml':
                    text = source.read_text()
                    # Until reference-aware seeding qualifies a mapping, an
                    # absolute stock dependency cannot claim independence.
                    if str(settings.source_root) in text:
                        holds.append('configuration_home_references_require_asset_mapping')
                    def embedded(value):
                        if isinstance(value, dict):
                            return any(k.lower() in {'env', 'password', 'token', 'api_key', 'secret', 'credentials', 'authorization'} or embedded(v) for k, v in value.items())
                        if isinstance(value, list):
                            return any(embedded(v) for v in value)
                        return False
                    if embedded(tomllib.loads(text)):
                        holds.append('embedded_credentials_require_native_owner')
                snapshot, nested = _tree(source, scope)
                if nested or any(_secret_name(Path(p)) for p in snapshot):
                    holds.append('linked_asset_credentials_or_nested_links_require_repair')
                    continue
                sources[str(path)] = snapshot
                plan.append(dict(path=str(path), source=str(source), target=os.readlink(path)))
            except (OSError, ValueError, RuntimeError, InventoryError):
                holds.append('linked_configuration_source_requires_repair')
    writers = owner.writer_probe(tuple(homes) + tuple(Path(p['source']) for p in plan))
    if writers.get('status') != 'complete':
        holds.append('writer_census_unknown')
    if writers.get('writers'):
        holds.append('competing_writer')
    policy_sha = hashlib.sha256(owner.path.read_bytes()).hexdigest()
    return dict(status='held' if holds else 'ready', strategy='adopt_independent',
                target=dict(owner.scope_target(), migration_revision=_digest(dict(policy=policy_sha, entries=entries, sources=sources, writers=writers))),
                holds=sorted(set(holds)), accounts=names, inactive_accounts=inactive,
                homes=[str(h) for h in homes], plan=plan, sources=sources,
                policy_sha=policy_sha, credential_copy=False,
                original_shared_store='preserved', production_activation=False)


def _guard(owner, authorize, expected):
    if authorize:
        authorize()
    current = owner._preview()
    if current['holds']:
        raise InventoryError('migration_held', 'adoption requires idle selected profiles and linked configuration sources: ' + ','.join(current['holds']))
    if current['target'] != expected:
        raise InventoryError('stale_target', 'adoption inputs changed; preview again before applying')
    return current


def _copy(source, destination):
    if source.is_dir():
        shutil.copytree(source, destination)
        for path in [destination, *destination.rglob('*')]:
            mode = path.stat().st_mode
            path.chmod(0o700 if stat.S_ISDIR(mode) else 0o700 if mode & 0o111 else 0o600)
    else:
        shutil.copyfile(source, destination)
        destination.chmod(0o700 if source.stat().st_mode & 0o111 else 0o600)


def apply(owner, directory, before, authorize):
    from .controller_migration import _tree
    _, _, scope, _, paths = owner._configuration()
    custody = paths['candidate_root']
    identifier = before['target']['migration_revision']
    receipt_path = directory / (identifier + '.json')
    if custody.exists() or custody.is_symlink() or receipt_path.exists():
        raise InventoryError('uncertain_effect', 'adoption custody already exists; reconcile its receipt before retry')
    _guard(owner, authorize, before['target'])
    receipt = dict(schema_version=1, strategy='adopt_independent', receipt_id=identifier,
                   scope=owner.scope_target(), state='preparing', custody=str(custody),
                   policy_sha=before['policy_sha'], sources=before['sources'], moves=[])
    _save(receipt_path, receipt)
    try:
        custody.mkdir(mode=0o700)
        for number, action in enumerate(before['plan']):
            staged = custody / ('private-' + str(number))
            _copy(Path(action['source']), staged)
        # Copying never opens native state; recheck full selected state and all
        # link sources after staging and immediately before each replacement.
        current = _guard(owner, authorize, before['target'])
        for number, action in enumerate(before['plan']):
            current = _guard(owner, authorize, current['target'])
            path = Path(action['path'])
            backup = custody / ('link-' + str(number))
            row = dict(action, backup=str(backup), state='intent')
            receipt['moves'].append(row)
            _save(receipt_path, receipt)
            os.rename(path, backup)
            os.rename(custody / ('private-' + str(number)), path)
            row['state'] = 'adopted'
            _save(receipt_path, receipt)
            current = owner._preview()
        _guard(owner, authorize, current['target'])
        receipt.update(state='applied', after={h: _tree(Path(h), scope)[0] for h in before['homes']})
        _save(receipt_path, receipt)
        return dict(status='applied', strategy='adopt_independent', receipt_id=identifier,
                    target=current['target'], adopted_homes=before['homes'], credential_copy=False,
                    native_state='preserved_in_place', original_shared_store='preserved')
    except BaseException:
        receipt['state'] = 'uncertain'
        _save(receipt_path, receipt)
        raise


def rollback(owner, directory, identifier, before, authorize):
    from .controller_migration import _tree
    if not isinstance(identifier, str) or len(identifier) != 64 or any(c not in '0123456789abcdef' for c in identifier):
        raise InventoryError('invalid_argument', 'exact adoption receipt identity required')
    path = directory / (identifier + '.json')
    if path.is_symlink() or path.stat().st_mode & 0o077 or path.stat().st_uid != os.getuid():
        raise InventoryError('unauthorized_target', 'private owned adoption receipt required')
    receipt = json.loads(path.read_text())
    _, _, scope, _, paths = owner._configuration()
    if (receipt.get('state') != 'applied' or receipt.get('strategy') != 'adopt_independent'
            or receipt.get('scope') != owner.scope_target() or receipt.get('policy_sha') != before['policy_sha']
            or receipt.get('custody') != str(paths['candidate_root'])):
        raise InventoryError('uncertain_effect', 'only the original completed adoption can roll back')
    def check():
        _guard(owner, authorize, before['target'])
        if any(_tree(Path(h), scope)[0] != snapshot for h, snapshot in receipt['after'].items()):
            raise InventoryError('target_changed', 'profile changed since adoption; private work and custody retained')
        for source_path, snapshot in receipt['sources'].items():
            source = next(row['source'] for row in receipt['moves'] if row['path'] == source_path)
            if _tree(Path(source), scope)[0] != snapshot:
                raise InventoryError('target_changed', 'original linked configuration changed; rollback needs reconciliation')
        for row in receipt['moves']:
            backup = Path(row['backup'])
            if not backup.is_symlink() or os.readlink(backup) != row['target']:
                raise InventoryError('target_changed', 'rollback link custody changed; repair required')
    check()
    # Authorize once more before effects, retaining new private state on refusal.
    check()
    receipt['state'] = 'rolling_back'
    _save(path, receipt)
    try:
        expected = before['target']
        for number, row in enumerate(receipt['moves']):
            _guard(owner, authorize, expected)
            original = Path(row['path'])
            os.rename(original, paths['candidate_root'] / ('retained-private-' + str(number)))
            os.rename(row['backup'], original)
            expected = owner._preview()['target']
        receipt['state'] = 'rolled_back'
        _save(path, receipt)
        return dict(status='rolled_back', receipt_id=identifier, target=owner._preview()['target'], credential_copy=False)
    except BaseException:
        receipt['state'] = 'uncertain'
        _save(path, receipt)
        raise
