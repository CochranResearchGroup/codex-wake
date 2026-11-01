"""Disposable-only migration qualification; production activation stays separate.

Native credential files are never opened/copied. Account directory renames keep
native history and credential inodes with their owner; original shared state is
retained. This module owns filesystem before/after provenance, not operation
admission, retries, authority, accounting, or provider/runtime activation.
"""
from __future__ import annotations

from dataclasses import replace
import hashlib
import json
import os
import re
from pathlib import Path
import stat
import shutil
import tomllib
from uuid import UUID

from codex_profiles.config import load_settings
from codex_profiles.history import discover, select_session
from codex_profiles.layout import plan_migration, apply_migration
from .controller_accounts import ControllerAccounts, account_inventory
from .managed_inventory import InventoryError
from .goal_supervision import _lock, _save


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def _secret_name(path):
    return any(word in path.name.lower() for word in ('auth', 'credential', 'token', 'password', 'keyring', 'secret'))


def _links(path):
    cursor, chain = path.absolute(), []
    for _ in range(32):
        prefix = Path(cursor.anchor)
        found = None
        for index, part in enumerate(cursor.parts[1:], 1):
            prefix /= part
            if prefix.is_symlink():
                raw = os.readlink(prefix)
                chain.append(dict(path=str(prefix), target=raw))
                destination = Path(raw) if Path(raw).is_absolute() else prefix.parent / raw
                found = destination.joinpath(*cursor.parts[index + 1:])
                break
        if found is None:
            return dict(path=str(path), chain=chain, resolved=str(cursor.resolve()), exists=cursor.exists())
        cursor = found
    raise InventoryError('unsupported_target', 'symlink cycle or unbounded indirection')


def _tree(root, fixture, *, limit=4096):
    entries, links = {}, []
    pending = [root]
    while pending:
        path = pending.pop()
        if not path.exists() and not path.is_symlink():
            entries[str(path)] = dict(kind='absent')
            continue
        info = path.lstat()
        row = dict(mode=stat.S_IMODE(info.st_mode), device=info.st_dev, inode=info.st_ino,
                   size=info.st_size, mtime_ns=info.st_mtime_ns, ctime_ns=info.st_ctime_ns)
        if stat.S_ISLNK(info.st_mode):
            row.update(kind='link', target=os.readlink(path))
            try:
                link = _links(path)
                link['scope'] = 'internal' if Path(link['resolved']).is_relative_to(fixture) else 'external_dependency'
            except (InventoryError, OSError, RuntimeError):
                link = dict(path=str(path), chain=[dict(path=str(path), target=os.readlink(path))],
                            resolved=None, exists=False, scope='unknown')
            links.append(link)
        elif stat.S_ISDIR(info.st_mode):
            row['kind'] = 'directory'
            pending.extend(sorted(path.iterdir(), reverse=True))
        elif stat.S_ISREG(info.st_mode):
            row['kind'] = 'file'
            # Inventory generations, not arbitrary contents. Native credential
            # stores may use unrecognized names; only their own owner opens them.
            row['contents'] = 'native_owner_not_opened' if _secret_name(path) else 'metadata_only'
        else:
            raise InventoryError('unsupported_target', 'fixture contains unsupported special file')
        entries[str(path)] = row
        if len(entries) > limit:
            raise InventoryError('unsupported_target', 'fixture inventory exceeds bounded capacity')
    return entries, links


def probe_writers(roots):
    """Bounded same-user runtime-home and write-FD census; uncertainty never means idle."""
    writers, unknown = [], False
    try:
        processes = []
        for path in Path('/proc').iterdir():
            if not path.name.isdigit():
                continue
            try:
                if path.stat().st_uid == os.getuid():
                    processes.append(path)
            except FileNotFoundError:
                continue
            except OSError:
                unknown = True
        if len(processes) > 4096:
            return dict(status='unknown', writers=[], reason='process census exceeds bounded capacity')
        for process in processes:
            try:
                # An idle TUI can reopen its database later. Open descriptors
                # alone do not prove an account home is safe to detach.
                environment = {}
                for item in (process / 'environ').read_bytes().split(b'\0'):
                    key, separator, value = item.partition(b'=')
                    if separator and key in (b'CODEX_HOME', b'HOME'):
                        environment[key] = os.fsdecode(value)
                configured_home = environment.get(b'CODEX_HOME')
                if not configured_home and Path(os.readlink(process / 'exe')).name == 'codex':
                    default_home = environment.get(b'HOME')
                    if default_home:
                        configured_home = str(Path(default_home) / '.codex')
                if configured_home:
                    dependency = Path(configured_home)
                    if not dependency.is_absolute():
                        dependency = (process / 'cwd').resolve() / dependency
                    dependency = Path(_links(dependency)["resolved"])
                    if any(dependency == root or dependency.is_relative_to(root) for root in roots):
                        writers.append(dict(pid=int(process.name), path=str(dependency), evidence='configured_account_home'))
                descriptors = list((process / 'fd').iterdir())
                if len(descriptors) > 4096:
                    unknown = True
                    continue
                for descriptor in descriptors:
                    try:
                        name = os.readlink(descriptor)
                        clean = name.removesuffix(' (deleted)')
                        if not Path(clean).is_absolute() or not any(Path(clean).is_relative_to(root) for root in roots):
                            continue
                        values = dict(line.split(':', 1) for line in (process / 'fdinfo' / descriptor.name).read_text().splitlines() if ':' in line)
                        flags = int(values['flags'].strip(), 8)
                        if flags & os.O_ACCMODE in (os.O_WRONLY, os.O_RDWR):
                            writers.append(dict(pid=int(process.name), fd=descriptor.name, path=clean, evidence='open_write_descriptor'))
                    except FileNotFoundError:
                        continue
                    except (OSError, ValueError, KeyError):
                        unknown = True
            except FileNotFoundError:
                continue
            except (OSError, InventoryError, RuntimeError):
                unknown = True
        return dict(status='unknown' if unknown else 'complete', writers=writers)
    except (OSError, AttributeError):
        return dict(status='unknown', writers=writers, reason='host writer census is unavailable')


def _history_is_quiescent(accounts):
    # SQLite read-only WAL connections can create shared-memory sidecars. A
    # migration preview must not do that; WAL qualification belongs to its
    # quiescent native owner, never an implicit checkpoint or mode conversion.
    for account in accounts:
        database = Path(account['home']) / 'state_5.sqlite'
        if not database.is_file():
            continue
        if database.with_name(database.name + '-wal').exists() or database.with_name(database.name + '-shm').exists():
            return False
        with database.open('rb') as source:
            header = source.read(20)
        if len(header) >= 20 and (header[18] == 2 or header[19] == 2):
            return False
    return True


class ControllerMigration:
    def __init__(self, config_path, *, root, host, environment, writer_probe=None):
        self.path, self.root = Path(config_path), Path(root)
        self.host, self.environment = host, environment
        self.writer_probe = writer_probe or probe_writers

    def _configuration(self):
        data = tomllib.loads(self.path.read_text())
        policy = data['migration']
        if policy.get('strategy', 'relocate') not in ('relocate', 'isolate_in_place'):
            raise InventoryError('unsupported_target', 'unknown migration strategy')
        if policy.get('strategy', 'relocate') != 'isolate_in_place' and 'enabled' in data.get('accounts', {}):
            raise InventoryError('unsupported_target', 'selective admission requires in-place isolation')
        fixture = Path(policy.get('scope_root', policy.get('fixture_root', '')))
        if not fixture.is_absolute() or fixture != fixture.resolve() or not fixture.is_dir():
            raise InventoryError('unauthorized_target', 'canonical disposable fixture root required')
        marker_path = fixture / '.codex-wake-migration-fixture.json'
        marker = None
        if marker_path.is_file():
            try:
                candidate_marker = json.loads(marker_path.read_text())
                if (candidate_marker.get('schema_version') == 1 and candidate_marker.get('purpose') == 'codex-wake-migration-fixture'
                        and str(UUID(candidate_marker['fixture_id'])) == candidate_marker['fixture_id']):
                    marker = candidate_marker
            except (OSError, ValueError, KeyError, TypeError):
                pass
        settings = load_settings(self.path)
        paths = {key: Path(policy[key]) for key in ('candidate_root', 'pointer', 'legacy_config')}
        paths.update(source_root=settings.source_root, state_root=settings.state_root)
        for key, path in paths.items():
            if (not path.is_absolute() or not path.is_relative_to(fixture) or path == fixture
                    or not path.parent.resolve().is_relative_to(fixture)
                    or (not path.is_symlink() and not path.resolve().is_relative_to(fixture))):
                raise InventoryError('unauthorized_target', 'migration path is outside the designated fixture')
        return data, settings, fixture, marker, paths

    def scope_target(self):
        data, unused_settings, unused_fixture, marker, unused_paths = self._configuration()
        name = data['migration'].get('scope_id', 'legacy')
        if not isinstance(name, str) or not 1 <= len(name) <= 128 or any(ord(char) < 32 for char in name):
            raise InventoryError('configuration_unavailable', 'stable migration scope identity required')
        target = dict(host=self.host, environment=self.environment, migration_id=name)
        if marker is not None:
            target['fixture_id'] = marker['fixture_id']
        return target

    def execute(self, operation, arguments, *, authorize=None):
        allowed = {'migration.preview': set(), 'migration.apply': {'expected_target'},
                   'migration.rollback': {'expected_target', 'receipt_id'}}
        if operation not in allowed:
            raise InventoryError('unsupported_operation', 'migration operation is unsupported')
        if not isinstance(arguments, dict) or set(arguments) - allowed[operation]:
            raise InventoryError('invalid_argument', 'unsupported migration arguments; no caller paths accepted')
        if authorize is not None:
            authorize()
        try:
            if operation == 'migration.preview':
                return self._preview()
            data, settings, fixture, marker, paths = self._configuration()
            isolation = data['migration'].get('strategy') == 'isolate_in_place'
            if marker is None and not (isolation and data['migration'].get('live_activation') is True):
                raise InventoryError('production_not_authorized', 'explicit host live activation or disposable designation required')
            if marker is None:
                info = self.path.lstat()
                if self.path.is_symlink() or info.st_uid != os.getuid() or info.st_mode & 0o022:
                    raise InventoryError('unauthorized_target', 'live migration policy must be owned and private from other writers')
            if not isolation and self.root.resolve().is_relative_to(fixture):
                raise InventoryError('unsupported_target', 'migration provenance must remain outside the disposable target')
            directory = self.root / 'controller-migration'
            directory.mkdir(mode=0o700, parents=True, exist_ok=True)
            with _lock(directory, marker['fixture_id'] if marker else _digest(self.scope_target())):
                preview = self._preview()
                if arguments.get('expected_target') != preview['target']:
                    raise InventoryError('stale_target', 'migration plan or target changed')
                if preview['holds']:
                    raise InventoryError('migration_held', 'migration evidence has explicit holds: ' + ','.join(preview['holds']))
                if isolation:
                    if operation == 'migration.apply':
                        return self._isolate_apply(directory, preview, settings, paths, fixture, authorize)
                    return self._isolate_rollback(directory, arguments.get('receipt_id'), preview, settings, paths, fixture, authorize)
                if operation == 'migration.apply':
                    return self._apply(directory, preview, settings, paths, fixture, authorize)
                return self._rollback(directory, arguments.get('receipt_id'), preview, paths, fixture, authorize)
        except InventoryError:
            raise
        except (OSError, ValueError, TypeError, KeyError, RuntimeError):
            raise InventoryError('migration_unavailable', 'migration policy/evidence is unavailable; reconcile any existing receipt before retry') from None

    def _authorize(self, authorize, policy_sha):
        if authorize is not None:
            authorize()
        if hashlib.sha256(self.path.read_bytes()).hexdigest() != policy_sha:
            raise InventoryError('stale_target', 'host migration policy changed before the next effect')
        unused_data, unused_settings, unused_fixture, unused_marker, paths = self._configuration()
        census = self.writer_probe(tuple(paths.values()))
        if census.get('status') != 'complete' or census.get('writers'):
            raise InventoryError('migration_held', 'writer changed or census is unknown before the next effect')
        if authorize is not None:
            authorize()

    def _candidate_configuration(self, candidate):
        original = self.path.read_text()
        before = tomllib.loads(original)
        def credential_field(value, trail=()):
            if isinstance(value, dict):
                return any(credential_field(child, (*trail, key)) for key, child in value.items())
            if isinstance(value, list):
                return any(credential_field(child, trail) for child in value)
            if trail and trail[-1] in ('mcp_oauth_credentials_store', 'cli_auth_credentials_store') and value in ('auto', 'file', 'keyring'):
                return False
            names = {key.lower().replace('-', '_') for key in trail}
            secrets = {'env', 'auth', 'credentials', 'password', 'passwd', 'secret', 'client_secret',
                       'token', 'access_token', 'refresh_token', 'id_token', 'api_key', 'authorization', 'bearer_token'}
            return bool(names & secrets) or any(name.endswith(('_api_key', '_password', '_secret', '_access_token', '_refresh_token')) for name in names)
        if credential_field(before):
            raise InventoryError('unsupported_target', 'embedded credential settings require the native credential owner; registry is not copied')
        lines, section, replaced = [], '', 0
        for line in original.splitlines(keepends=True):
            text = line.strip()
            if text.startswith('[') and text.endswith(']'):
                section = text
            if section == '[profiles]' and text.split('=', 1)[0].strip() == 'state_root' and '=' in text:
                line = 'state_root=' + json.dumps(str(candidate / 'accounts')) + '\n'
                replaced += 1
            lines.append(line)
        result = ''.join(lines)
        expected = dict(before, profiles=dict(before['profiles'], state_root=str(candidate / 'accounts')))
        if replaced != 1 or tomllib.loads(result) != expected:
            raise InventoryError('unsupported_target', 'registry requires explicit migration qualification; no lossy rewrite permitted')
        return result

    def _apply(self, directory, preview, settings, paths, fixture, authorize):
        candidate, pointer = paths['candidate_root'], paths['pointer']
        if candidate.exists() or candidate.is_symlink():
            raise InventoryError('target_changed', 'candidate already exists; no replacement or retry permitted')
        if not pointer.is_symlink() or pointer.resolve() != paths['legacy_config']:
            raise InventoryError('unsupported_target', 'exact legacy configuration pointer is required')
        if not preview['accounts']:
            raise InventoryError('migration_held', 'no qualified owning accounts')
        receipt_id = preview['target']['migration_revision']
        receipt_path = directory / (receipt_id + '.json')
        if receipt_path.exists():
            raise InventoryError('uncertain_effect', 'original migration receipt already exists; no replay permitted')
        source_before, unused = _tree(paths['source_root'], fixture)
        before_pointer = os.readlink(pointer)
        receipt = dict(schema_version=1, receipt_id=receipt_id, state='preparing',
            scope=self.scope_target(), policy_sha=hashlib.sha256(self.path.read_bytes()).hexdigest(), candidate=str(candidate), pointer=str(pointer), old_pointer=before_pointer,
            homes=[dict(old=str(settings.account_root(name)), new=str(candidate / 'accounts' / name)) for name in preview['accounts']],
            original_shared=source_before, original_homes={str(settings.account_root(name)): _tree(settings.account_root(name), fixture)[0]
                for name in preview['accounts']}, moved=[], compatibility_links=[], effects_attempted=True)
        _save(receipt_path, receipt)
        try:
            self._authorize(authorize, receipt['policy_sha'])
            if self._preview()['target'] != preview['target']:
                raise InventoryError('stale_target', 'migration source changed before the first effect')
            candidate.mkdir(mode=0o700)
            candidate_settings = replace(settings, state_root=candidate / 'accounts')
            apply_migration(candidate_settings, plan_migration(candidate_settings))
            if preview.get('selected_account') is not None:
                self._authorize(authorize, receipt['policy_sha'])
                candidate_settings.current_profile_path.write_text(preview['selected_account'] + '\n')
                candidate_settings.current_profile_path.chmod(0o600)
            for home in receipt['homes']:
                self._authorize(authorize, receipt['policy_sha'])
                old, new = Path(home['old']), Path(home['new'])
                if (old.is_symlink() or not old.is_dir() or new.exists()
                        or _tree(old, fixture)[0] != receipt['original_homes'][str(old)]):
                    raise InventoryError('target_changed', 'owning account changed before relocation')
                if old.stat().st_dev != candidate.stat().st_dev:
                    raise InventoryError('unsupported_target', 'account relocation must remain on one filesystem')
                os.rename(old, new)
                receipt['moved'].append(home['old'])
                _save(receipt_path, receipt)
                self._authorize(authorize, receipt['policy_sha'])
                old.symlink_to(new, target_is_directory=True)
                receipt['compatibility_links'].append(home['old'])
                _save(receipt_path, receipt)
            self._authorize(authorize, receipt['policy_sha'])
            config = candidate / 'controller-accounts.toml'
            config.write_text(self._candidate_configuration(candidate))
            config.chmod(0o600)
            # Qualify the candidate through the reused account/history owners.
            selected = ControllerAccounts(config, host=self.host, environment=self.environment).execute('accounts.list', {})['accounts']
            if not _history_is_quiescent(selected):
                raise InventoryError('migration_held', 'candidate WAL history requires its quiescent native owner')
            native = discover(load_settings(config), [row['id'] for row in selected])
            if native['holds']:
                raise InventoryError('migration_held', 'candidate native ownership is unqualified')
            for row in native['sessions']:
                select_session(load_settings(config), row['thread_id'], row['profile'])
            if _tree(paths['source_root'], fixture)[0] != source_before:
                raise InventoryError('target_changed', 'original shared store changed during migration')
            self._authorize(authorize, receipt['policy_sha'])
            if not pointer.is_symlink() or os.readlink(pointer) != before_pointer:
                raise InventoryError('target_changed', 'legacy pointer changed before cutover')
            temporary = pointer.with_name(pointer.name + '.migration-' + receipt_id[:12])
            temporary.symlink_to(config)
            os.replace(temporary, pointer)
            after = self._preview()
            receipt.update(state='applied', target=after['target'], candidate_after=_tree(candidate, fixture)[0],
                           pointer_after=os.readlink(pointer), after_accounts=after['accounts'])
            _save(receipt_path, receipt)
            return dict(status='applied', receipt_id=receipt_id, target=after['target'],
                accounts=after['accounts'], native_history_qualified=not native['holds'],
                credential_copy=False, credential_files='same_native_inodes', original_shared_store='preserved',
                production_activation=False, production_gate='issue380')
        except BaseException as error:
            receipt['state'] = 'uncertain'
            _save(receipt_path, receipt)
            if isinstance(error, Exception):
                raise InventoryError('uncertain_effect', 'migration receipt ' + receipt_id + ' requires reconciliation; no automatic replay') from None
            raise

    def _rollback(self, directory, receipt_id, preview, paths, fixture, authorize):
        if not isinstance(receipt_id, str) or len(receipt_id) != 64 or any(char not in '0123456789abcdef' for char in receipt_id):
            raise InventoryError('invalid_argument', 'exact migration receipt identity required')
        receipt_path = directory / (receipt_id + '.json')
        if receipt_path.is_symlink():
            raise InventoryError('unsupported_target', 'migration receipt must remain private and real')
        receipt = json.loads(receipt_path.read_text())
        candidate, pointer = paths['candidate_root'], paths['pointer']
        if receipt.get('state') != 'applied' or receipt.get('scope') != self.scope_target():
            raise InventoryError('uncertain_effect', 'only an attributable completed migration may roll back')
        if (receipt.get('policy_sha') != hashlib.sha256(self.path.read_bytes()).hexdigest()
                or receipt.get('candidate') != str(candidate) or receipt.get('pointer') != str(pointer)
                or _tree(candidate, fixture)[0] != receipt.get('candidate_after')
                or _tree(paths['source_root'], fixture)[0] != receipt.get('original_shared')
                or not pointer.is_symlink() or os.readlink(pointer) != receipt.get('pointer_after')):
            raise InventoryError('target_changed', 'rollback target changed; original and candidate are retained')
        for home in receipt['homes']:
            old, new = Path(home['old']), Path(home['new'])
            if not old.is_symlink() or os.readlink(old) != str(new) or not new.is_dir():
                raise InventoryError('target_changed', 'owning account compatibility binding changed')
        self._authorize(authorize, receipt['policy_sha'])
        receipt['state'] = 'rolling_back'
        _save(receipt_path, receipt)
        try:
            for home in receipt['homes']:
                self._authorize(authorize, receipt['policy_sha'])
                old, new = Path(home['old']), Path(home['new'])
                old.unlink()
                os.rename(new, old)
            self._authorize(authorize, receipt['policy_sha'])
            temporary = pointer.with_name(pointer.name + '.rollback-' + receipt_id[:12])
            temporary.symlink_to(receipt['old_pointer'])
            os.replace(temporary, pointer)
            self._authorize(authorize, receipt['policy_sha'])
            shutil.rmtree(candidate)
            receipt['state'] = 'rolled_back'
            _save(receipt_path, receipt)
            return dict(status='rolled_back', receipt_id=receipt_id, target=self._preview()['target'],
                        credential_copy=False, original_shared_store='preserved', production_activation=False)
        except BaseException as error:
            receipt['state'] = 'uncertain'
            _save(receipt_path, receipt)
            if isinstance(error, Exception):
                raise InventoryError('uncertain_effect', 'migration receipt ' + receipt_id + ' requires reconciliation; no automatic replay') from None
            raise

    def _preview(self):
        data, settings, fixture, marker, paths = self._configuration()
        if data['migration'].get('strategy') == 'isolate_in_place':
            return self._isolate_preview(data, settings, fixture, marker, paths)
        entries, links = {}, []
        for path in paths.values():
            found, discovered = _tree(path, fixture)
            entries.update(found)
            links.extend(discovered)
        holds = []
        if any(path != path.resolve() for key, path in paths.items() if key != 'pointer'):
            holds.append('indirect_root_requires_qualification')
        if any(link['scope'] != 'internal' or not link['exists'] for link in links):
            holds.append('indirect_dependency_unqualified')
        if (paths['source_root'].is_relative_to(paths['state_root']) or paths['state_root'].is_relative_to(paths['source_root'])
                or any(paths['candidate_root'].is_relative_to(paths[k]) or paths[k].is_relative_to(paths['candidate_root']) for k in ('source_root', 'state_root'))):
            holds.append('migration_roots_overlap')
        writers = self.writer_probe(tuple(paths.values()))
        if writers.get('status') != 'complete':
            holds.append('writer_census_unknown')
        if writers.get('writers'):
            holds.append('competing_writer')
        if set(settings.shared_links) - {'config.toml', 'skills', 'rules'}:
            holds.append('shared_mutable_policy')
        effective_path = self.path
        candidate_config = paths['candidate_root'] / 'controller-accounts.toml'
        active = paths['pointer'].is_symlink() and paths['pointer'].resolve() == candidate_config
        if active and candidate_config.is_file():
            effective_path = candidate_config
            settings = load_settings(candidate_config)
        accounts, history = [], dict(sessions=[], holds=[])
        if not any(reason in holds for reason in ('indirect_root_requires_qualification', 'indirect_dependency_unqualified', 'migration_roots_overlap')):
            try:
                accounts = ControllerAccounts(effective_path, host=self.host, environment=self.environment).execute('accounts.list', {})['accounts']
                if not _history_is_quiescent(accounts):
                    holds.append('native_wal_history_requires_quiescent_owner')
                else:
                    history = discover(settings, [row['id'] for row in accounts])
                if history['holds']:
                    holds.append('native_history_unqualified')
                for row in history['sessions']:
                    select_session(settings, row['thread_id'], row['profile'])
            except (InventoryError, ValueError, OSError):
                holds.append('account_or_history_ownership_unqualified')
        try:
            self._candidate_configuration(paths['candidate_root'])
        except InventoryError:
            holds.append('registry_rewrite_unqualified')
        shared_name = Path(settings.shared_dir_name)
        safe_shared = not shared_name.is_absolute() and '..' not in shared_name.parts and bool(shared_name.parts)
        if not safe_shared:
            holds.append('shared_root_requires_qualification')
        if any(Path(row['home']).name != row['id'] for row in accounts):
            holds.append('noncanonical_account_alias_unqualified')
        selected_account = settings.current_profile_resolved() if safe_shared else None
        if selected_account is not None and selected_account not in {row['id'] for row in accounts}:
            holds.append('selected_account_unqualified')
        candidate = replace(settings, state_root=paths['candidate_root'] / 'accounts')
        plan = [dict(kind=action.kind, source=str(action.source) if action.source else None,
                     destination=str(action.destination), status=action.status) for action in plan_migration(candidate)]
        if selected_account is not None:
            plan.append(dict(kind='selection', source=str(settings.current_profile_path),
                destination=str(candidate.current_profile_path), status='plan', account=selected_account))
        target = dict(self.scope_target(),
                      migration_revision=_digest(dict(configuration=hashlib.sha256(self.path.read_bytes()).hexdigest(), entries=entries, links=links, writers=writers)))
        return dict(status='held' if holds else 'ready', target=target, links=links, writers=writers,
                    holds=sorted(set(holds)), plan=plan, accounts=[row['id'] for row in accounts],
                    history=dict(qualified_sessions=len(history['sessions']), unassigned_policy='preserve_original_store'),
                    selected_account=selected_account,
                    phase='applied' if active else 'legacy',
                    production_effect_status='not_authorized', production_gate='issue380',
                    disposable_effect_status='authorized' if marker is not None else 'not_authorized',
                    production_activation=False, credential_copy=False, original_shared_store='preserved')

    def _isolate_preview(self, data, settings, scope, marker, paths):
        """Plan only affected aliases, never traverse or assign legacy histories."""
        holds, entries, links, plan = [], {}, [], []
        names, inactive = account_inventory(settings, data)
        if not names:
            raise InventoryError('unsupported_target', 'explicit owning accounts required')
        homes = [settings.account_root(name) for name in names]
        for home in homes:
            if (
                home.is_symlink()
                or home != home.resolve()
                or not home.is_dir()
                or home.stat().st_uid != os.getuid()
            ):
                holds.append("account_home_unqualified")
        if any(
            paths["candidate_root"].is_relative_to(root)
            or root.is_relative_to(paths["candidate_root"])
            or self.root.resolve().is_relative_to(root)
            for root in (settings.state_root, settings.source_root)
        ):
            holds.append("isolation_provenance_or_candidate_overlaps_runtime")
        if set(settings.shared_links) - {"config.toml", "skills", "rules"}:
            holds.append("shared_mutable_policy")
        directories = {"sessions", "memories", "cache", "log"}
        mutable = directories | {"history.jsonl"}
        credentials = {}
        affected = set()
        for home in homes:
            auth = home / "auth.json"
            credentials[str(auth)] = _tree(auth, scope)[0]
            if auth.is_symlink():
                holds.append("credential_owner_required")
            candidates = {home / name for name in mutable} | set(home.glob("*.sqlite*"))
            affected.update(str(path) for path in candidates)
            for path in sorted(candidates):
                found, discovered = (
                    _tree(path, scope)
                    if path.is_symlink() or not path.exists() or path.is_file()
                    else (
                        {
                            str(path): dict(
                                kind="private_directory",
                                device=path.stat().st_dev,
                                inode=path.stat().st_ino,
                            )
                        },
                        [],
                    )
                )
                entries.update(found)
                links.extend(discovered)
                if not path.is_symlink():
                    continue
                link = discovered[0]
                if (
                    not link.get("exists")
                    or link.get("scope") != "internal"
                    or not Path(link["resolved"]).is_relative_to(
                        settings.shared_root.resolve()
                    )
                ):
                    holds.append("legacy_runtime_link_unqualified")
                    continue
                plan.append(
                    dict(
                        kind="isolate_runtime_link",
                        path=str(path),
                        target=os.readlink(path),
                        inode=path.lstat().st_ino,
                        replacement="directory"
                        if path.name in directories
                        else "file"
                        if path.name == "history.jsonl"
                        else "absent",
                    )
                )
        protected = data["migration"].get(
            "protected_roots", [str(settings.source_root)]
        )
        if (
            not isinstance(protected, list)
            or len(protected) > 256
            or any(not isinstance(p, str) for p in protected)
        ):
            raise InventoryError(
                "unsupported_target", "bounded protected runtime roots required"
            )
        protected_bindings = []
        for value in protected:
            root = Path(value)
            if (
                not root.is_absolute()
                or not root.is_relative_to(scope)
                or root.is_symlink()
            ):
                holds.append("protected_runtime_root_unqualified")
                continue
            candidates = {root / name for name in mutable} | set(root.glob("*.sqlite*"))
            for path in sorted(candidates):
                if not path.exists() and not path.is_symlink():
                    continue
                try:
                    link = _links(path)
                    protected_bindings.append(link)
                    if any(step["path"] in affected for step in link["chain"]) or any(
                        Path(link["resolved"]).is_relative_to(Path(path))
                        for path in affected
                    ):
                        holds.append("protected_runtime_depends_on_account_alias")
                except (InventoryError, OSError, RuntimeError):
                    holds.append("protected_runtime_dependency_unknown")
        writers = self.writer_probe(tuple(homes))
        if writers.get("status") != "complete":
            holds.append("writer_census_unknown")
        if writers.get("writers"):
            holds.append("competing_writer")
        policy_sha = hashlib.sha256(self.path.read_bytes()).hexdigest()
        target = dict(
            self.scope_target(),
            migration_revision=_digest(
                dict(
                    configuration=policy_sha,
                    entries=entries,
                    credentials=credentials,
                    protected=protected_bindings,
                    writers=writers,
                )
            ),
        )
        return dict(
            status="held" if holds else "ready",
            strategy="isolate_in_place",
            target=target,
            holds=sorted(set(holds)),
            accounts=names,
            inactive_accounts=inactive,
            homes=[str(p) for p in homes],
            plan=plan,
            credentials=credentials,
            links=links,
            protected_bindings=protected_bindings,
            writers=writers,
            history=dict(
                qualified_sessions=0, unassigned_policy="preserve_original_store"
            ),
            phase="legacy" if plan else "isolated",
            credential_copy=False,
            original_shared_store="preserved",
            production_activation=False,
            production_effect_status="authorized"
            if data["migration"].get("live_activation") is True
            else "not_authorized",
            disposable_effect_status="authorized" if marker else "not_authorized",
            production_gate="issue380",
        )

    def _isolate_guard(self, authorize, policy_sha, credentials):
        if authorize is not None:
            authorize()
        if hashlib.sha256(self.path.read_bytes()).hexdigest() != policy_sha:
            raise InventoryError("stale_target", "isolation policy changed")
        data, settings, scope, marker, paths = self._configuration()
        current = self._isolate_preview(data, settings, scope, marker, paths)
        if current["holds"]:
            raise InventoryError(
                "migration_held",
                "isolation dependency or writer changed: " + ",".join(current["holds"]),
            )
        if current["credentials"] != credentials:
            raise InventoryError(
                "stale_target", "native credential owner changed during isolation"
            )
        return current

    def _isolate_apply(self, directory, preview, settings, paths, scope, authorize):
        candidate = paths["candidate_root"]
        if candidate.exists() or candidate.is_symlink():
            raise InventoryError(
                "target_changed", "isolation backup already exists; no replay permitted"
            )
        receipt_id = preview["target"]["migration_revision"]
        receipt_path = directory / (receipt_id + ".json")
        if receipt_path.exists():
            raise InventoryError(
                "uncertain_effect",
                "original isolation receipt already exists; no replay permitted",
            )
        receipt = dict(
            schema_version=1,
            strategy="isolate_in_place",
            state="preparing",
            scope=self.scope_target(),
            receipt_id=receipt_id,
            candidate=str(candidate),
            credentials=preview["credentials"],
            policy_sha=hashlib.sha256(self.path.read_bytes()).hexdigest(),
            moves=[],
            effects_attempted=True,
        )
        _save(receipt_path, receipt)
        try:
            current = self._isolate_guard(
                authorize, receipt["policy_sha"], receipt["credentials"]
            )
            if current["target"] != preview["target"]:
                raise InventoryError(
                    "stale_target", "isolation plan changed before first effect"
                )
            candidate.mkdir(mode=0o700)
            for number, action in enumerate(preview["plan"]):
                self._isolate_guard(
                    authorize, receipt["policy_sha"], receipt["credentials"]
                )
                path = Path(action["path"])
                backup = candidate / str(number)
                if (
                    not path.is_symlink()
                    or os.readlink(path) != action["target"]
                    or path.lstat().st_ino != action["inode"]
                ):
                    raise InventoryError(
                        "stale_target", "legacy alias changed before isolation"
                    )
                row = dict(action, backup=str(backup), state="intent")
                receipt["moves"].append(row)
                _save(receipt_path, receipt)
                os.rename(path, backup)
                if action["replacement"] == "directory":
                    path.mkdir(mode=0o700)
                elif action["replacement"] == "file":
                    with path.open("x"):
                        pass
                    path.chmod(0o600)
                row.update(state="isolated", after=_tree(path, scope)[0])
                _save(receipt_path, receipt)
            self._isolate_guard(
                authorize, receipt["policy_sha"], receipt["credentials"]
            )
            ControllerAccounts(
                self.path, host=self.host, environment=self.environment
            ).execute("accounts.list", {})
            receipt.update(state="applied")
            _save(receipt_path, receipt)
            return dict(
                status="applied",
                strategy="isolate_in_place",
                receipt_id=receipt_id,
                target=self._preview()["target"],
                credential_copy=False,
                credential_files="same_native_inodes",
                original_shared_store="preserved",
                production_activation=False,
            )
        except BaseException:
            receipt["state"] = "uncertain"
            _save(receipt_path, receipt)
            raise

    def _isolate_rollback(
        self, directory, receipt_id, preview, settings, paths, scope, authorize
    ):
        if (
            not isinstance(receipt_id, str)
            or re.fullmatch("[a-f0-9]{64}", receipt_id) is None
        ):
            raise InventoryError("invalid_argument", "exact isolation receipt required")
        receipt_path = directory / (receipt_id + ".json")
        if receipt_path.is_symlink():
            raise InventoryError(
                "unsupported_target", "private isolation receipt required"
            )
        receipt = json.loads(receipt_path.read_text())
        if (
            receipt.get("strategy") != "isolate_in_place"
            or receipt.get("state") != "applied"
            or receipt.get("scope") != self.scope_target()
            or receipt.get("candidate") != str(paths["candidate_root"])
        ):
            raise InventoryError(
                "uncertain_effect", "completed attributable isolation required"
            )
        self._isolate_guard(authorize, receipt["policy_sha"], receipt["credentials"])

        def check_replacement(row):
            path, backup = Path(row["path"]), Path(row["backup"])
            if (
                not backup.is_symlink()
                or os.readlink(backup) != row["target"]
                or backup.lstat().st_ino != row["inode"]
                or _tree(path, scope)[0] != row["after"]
            ):
                raise InventoryError(
                    "target_changed",
                    "private state changed; retain it rather than roll it back",
                )

        for row in receipt["moves"]:
            check_replacement(row)
        receipt["state"] = "rolling_back"
        _save(receipt_path, receipt)
        try:
            for row in reversed(receipt["moves"]):
                self._isolate_guard(
                    authorize, receipt["policy_sha"], receipt["credentials"]
                )
                check_replacement(row)
                path = Path(row["path"])
                if path.exists():
                    if path.is_dir():
                        path.rmdir()
                    else:
                        path.unlink()
                os.rename(row["backup"], path)
                row["state"] = "restored"
                _save(receipt_path, receipt)
            receipt["state"] = "rolled_back"
            _save(receipt_path, receipt)
            return dict(
                status="rolled_back",
                strategy="isolate_in_place",
                receipt_id=receipt_id,
                target=self._preview()["target"],
                credential_copy=False,
                original_shared_store="preserved",
                production_activation=False,
            )
        except BaseException:
            receipt["state"] = "uncertain"
            _save(receipt_path, receipt)
            raise
