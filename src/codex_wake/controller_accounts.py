"""Wake account/configuration owner, reusing the absorbed Profiles implementation.

This owner creates private homes, selects them and explains configuration. It never opens
credential files, changes the selected account, or launches provider work.
"""
from __future__ import annotations

import hashlib
import fcntl
from contextlib import contextmanager
import copy
import json
import os
from pathlib import Path
import re
import stat
import tempfile
import tomllib

from codex_profiles.config import load_settings
from .managed_inventory import InventoryError

_NAME = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\Z')
_PRIVATE = {'auth.json', 'sessions', 'history.jsonl', 'memories', 'cache', 'log'}


def launch_overrides(view):
    """Materialize explained scoped settings without changing the native home."""
    result = []
    for key, source in view['provenance'].items():
        if source.startswith('native:'):
            continue
        value = view['effective'][key]
        if value == '[redacted]':
            raise InventoryError('unsupported_target', 'secret configuration overrides require the native credential owner')
        native_key = '.'.join(json.dumps(segment) for segment in key.split('.'))
        result += ['-c', native_key + '=' + json.dumps(value, separators=(',', ':'))]
    return result


def _safe_name(value):
    if not isinstance(value, str) or not _NAME.fullmatch(value):
        raise InventoryError('invalid_argument', 'account names must be bounded identifiers')
    return value


def account_inventory(settings, data):
    """Apply explicit host admission without touching inactive legacy homes."""
    configured = list(settings.known_profiles) + list(settings.aliases.values())
    if settings.default_profile:
        configured.append(settings.default_profile)
    discovered = list(settings.state_root.glob(settings.account_prefix + "*"))
    if len(discovered) > 256 or len(configured) > 256:
        raise InventoryError(
            "unsupported_target", "account discovery exceeds bounded capacity"
        )
    configured += [path.name for path in discovered if path.is_dir()]
    names = sorted(
        {
            _safe_name(settings.resolve_profile_name(_safe_name(name)))
            for name in configured
        }
    )
    policy = data.get("accounts", {})
    if not isinstance(policy, dict):
        raise InventoryError(
            "configuration_unavailable", "account admission must be a host table"
        )
    if "enabled" not in policy:
        return names, []
    enabled = policy["enabled"]
    if not isinstance(enabled, list) or not 1 <= len(enabled) <= 256:
        raise InventoryError(
            "configuration_unavailable",
            "enabled accounts require a nonempty bounded host list",
        )
    admitted = sorted(
        {
            _safe_name(settings.resolve_profile_name(_safe_name(name)))
            for name in enabled
        }
    )
    if set(admitted) - set(names):
        raise InventoryError(
            "configuration_unavailable", "enabled account is not configured"
        )
    return admitted, sorted(set(names) - set(admitted))

def _redact(value, key=''):
    # Storage policy is public configuration, not a credential value.
    if key == 'cli_auth_credentials_store' and isinstance(value, str) and value in ('file', 'keyring', 'auto', 'ephemeral'):
        return value
    if any(word in key.lower() for word in ('token', 'secret', 'password', 'api_key', 'credential', 'authorization')) or 'env' in key.lower().split('.'):
        return '[redacted]'
    if isinstance(value, dict):
        return {k: _redact(v, k) for k, v in value.items()}
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


def _private_directory(path):
    if (not path.is_absolute() or path != path.resolve() or not path.is_dir()
            or path.stat().st_uid != os.getuid() or path.stat().st_mode & 0o077):
        raise InventoryError('unauthorized_target', 'account management requires real private user-owned directories')


@contextmanager
def _registry_lock(path):
    _private_directory(path.parent)
    descriptor = os.open(path.parent / '.accounts.lock',
                         os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise InventoryError('unauthorized_target', 'account registry lock is not private')
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise InventoryError('operation_in_progress', 'another account registry mutation is in progress') from None
        yield
    finally:
        os.close(descriptor)


def _set_registry_value(text, table, key, value):
    """Change one conventional TOML assignment, retaining unrelated source text.

    Ambiguous/inline-table layouts are rejected by the caller's semantic diff
    before any filesystem changes rather than rewritten by a second serializer.
    """
    lines = text.splitlines(keepends=True)
    header = '[' + table + ']'
    headings = [index for index, line in enumerate(lines) if line.lstrip().startswith('[')]
    starts = [index for index in headings if lines[index].strip().split('#', 1)[0].strip() == header]
    assignment = json.dumps(key) + ' = ' + json.dumps(value) + '\n'
    if not starts:
        return text.rstrip() + '\n\n' + header + '\n' + assignment
    if len(starts) != 1:
        raise InventoryError('unsupported_target', 'ambiguous account registry table')
    start = starts[0]
    end = next((index for index in headings if index > start), len(lines))
    for index in range(start + 1, end):
        matched = re.match(r'\s*(?:' + re.escape(key) + '|' + re.escape(json.dumps(key)) + r')\s*=\s*(.*)', lines[index])
        if not matched:
            continue
        for stop in range(index + 1, end + 1):
            try:
                tomllib.loads('value = ' + matched[1] + '\n' + ''.join(lines[index + 1:stop]))
            except ValueError:
                continue
            return ''.join(lines[:index]) + assignment + ''.join(lines[stop:])
        raise InventoryError('unsupported_target', 'account registry assignment cannot be safely edited')
    return ''.join(lines[:end]).rstrip() + '\n' + assignment + ''.join(lines[end:])


class ControllerAccounts:
    def __init__(self, config_path, *, host, environment):
        self.path = Path(config_path)
        self.host, self.environment = host, environment

    def execute(self, operation, arguments):
        if operation.startswith('stores.'):
            from .profile_stores import execute
            return execute(self, operation, arguments)
        if operation == 'accounts.create' and isinstance(arguments, dict) and arguments.get('mode') == 'independent':
            from .profile_stores import create
            return create(self, arguments)
        if operation in ('accounts.init', 'accounts.create'):
            try:
                return self._manage(operation, arguments)
            except InventoryError:
                raise
            except (OSError, ValueError, TypeError, KeyError, AttributeError):
                raise InventoryError('configuration_unavailable', 'account registry mutation could not be qualified') from None
        if operation not in ('accounts.list', 'accounts.resolve', 'configuration.explain'):
            raise InventoryError('unsupported_operation', 'unsupported account operation')
        allowed = set() if operation == 'accounts.list' else {'selector', 'expected_target'}
        if not isinstance(arguments, dict) or set(arguments) - allowed:
            raise InventoryError('invalid_argument', 'unsupported account arguments')
        from .controller_registry import resolve_registry
        path = resolve_registry(self.path, host=self.host, environment=self.environment)
        if not path.is_file():
            raise InventoryError('configuration_unavailable', 'host account configuration is unavailable')
        try:
            raw = path.read_bytes()
            data = tomllib.loads(raw.decode())
            settings = load_settings(path)
            # Profiles defaults are useful for legacy commands, but controller
            # inventory must never silently discover the operator home.
            if not data.get('profiles', {}).get('state_root'):
                raise ValueError('explicit state_root required')
            names, inactive = account_inventory(settings, data)
            if settings.selection_mode != 'launcher' or set(settings.shared_links) - {'config.toml', 'skills', 'rules'}:
                raise InventoryError('unsupported_target', 'concurrent accounts require private launcher mode')
            accounts = []
            for name in names:
                home = settings.account_root(name).absolute()
                if not home.is_dir() or home != home.resolve():
                    raise InventoryError('stale_target', 'configured account home is absent or replaced')
                mutable = [home / item for item in _PRIVATE] + list(home.glob('*.sqlite*'))
                if any(item.is_symlink() for item in mutable):
                    raise InventoryError('unsupported_target', 'account mutable state must remain private')
                for previous in accounts:
                    peer = Path(previous['home'])
                    if home.samefile(peer):
                        raise InventoryError('unsupported_target', 'accounts share a runtime home')
                    for item in mutable:
                        other = peer / item.name
                        if item.exists() and other.exists() and item.samefile(other):
                            raise InventoryError('unsupported_target', 'accounts share mutable runtime state')
                info = home.stat()
                if hasattr(os, 'getuid') and info.st_uid != os.getuid():
                    raise InventoryError('unauthorized_target', 'account home belongs to a different user')
                native_config = home / 'config.toml'
                native_bytes = native_config.read_bytes() if native_config.exists() else b''
                revision = hashlib.sha256(raw + b'\0' + native_bytes).hexdigest()
                target = dict(host=self.host, environment=self.environment, provider='codex', account=name,
                              home=str(home), home_generation=f'{info.st_dev}:{info.st_ino}', configuration_revision=revision)
                accounts.append(dict(id=name, home=str(home), target=target,
                                     aliases=sorted(k for k, v in settings.aliases.items()
                                                    if settings.resolve_profile_name(v) == name)))
            if 'stock' in data.get('stores', {}):
                from .profile_stores import execute as store_execute
                store = store_execute(self, 'stores.resolve', {'selector': 'stock'})['store']
                home = Path(store['home'])
                native_path = home / 'config.toml'
                native_bytes = native_path.read_bytes() if native_path.exists() else b''
                target = dict(host=self.host, environment=self.environment, provider='codex', account='stock',
                              home=str(home), home_generation=store['home_generation'],
                              configuration_revision=hashlib.sha256(raw + b'\0' + native_bytes).hexdigest())
                accounts.append(dict(id='stock', home=str(home), target=target, aliases=[],
                                     store_id=store['store_id'], kind='stock', independent=False,
                                     account_provenance='unknown'))
            for account in accounts:
                stored = data.get('stores', {}).get(account['id'])
                if stored:
                    account.update(store_id=stored['store_id'], kind=stored['kind'],
                                   independent=stored['independent'])
            if operation == 'accounts.list':
                result = dict(owner='codex-wake', accounts=accounts)
                if 'enabled' in data.get('accounts', {}):
                    result['inactive_accounts'] = inactive
                return result
            selector = _safe_name(arguments.get('selector'))
            name = 'stock' if selector == 'stock' and 'stock' in data.get('stores', {}) else _safe_name(settings.resolve_profile_name(selector))
            matches = [account for account in accounts if account['id'] == name]
            if not matches:
                raise InventoryError('target_not_found', 'account is not enabled for private operation')
            account = matches[0]
            if arguments.get('expected_target') is not None and arguments['expected_target'] != account['target']:
                raise InventoryError('stale_target', 'account or configuration generation changed')
            if operation == 'accounts.resolve':
                return dict(owner='codex-wake', account=account, grants_operations=False)
            if name == 'stock':
                from .profile_stores import inventory
                view = dict(profile='stock', inventory=inventory(Path(account['home'])),
                            mcp=dict(codex_account_auth='stock shared-home login; independent of Wake profiles'))
            else:
                view = settings.configuration_view(name)
            native_path = Path(account['home']) / 'config.toml'
            native = tomllib.loads(native_path.read_text()) if native_path.exists() else {}
            effective, provenance = {}, {}
            def overlay(values, source, prefix=''):
                if not isinstance(values, dict):
                    raise ValueError('configuration scope must be a table')
                for key, value in values.items():
                    path = prefix + key
                    if isinstance(value, dict):
                        overlay(value, source, path + '.')
                    else:
                        effective[path] = _redact(value, path)
                        provenance[path] = source
            overlay(native, 'native:' + str(native_path.resolve()))
            config = data.get('configuration', {})
            for values, source in ((config.get('base', {}), 'base'),
                (config.get('host', {}).get(self.host, {}), 'host:' + self.host),
                (config.get('provider', {}).get('codex', {}), 'provider:codex'),
                (config.get('account', {}).get(name, {}), 'account:' + name)):
                overlay(values, source)
            return dict(owner='codex-wake', account=account, effective=effective,
                        provenance=provenance, configuration=view,
                        applies_to='subsequent_explicit_launches', activation='not_performed')
        except InventoryError:
            raise
        except (OSError, ValueError, TypeError, KeyError, AttributeError):
            raise InventoryError('configuration_unavailable', 'host account configuration cannot be qualified') from None

    def prepare_login(self, selector, expected_target):
        """Persist this account's native credential mode without changing shared assets."""
        path = self.path.absolute()
        if path.is_symlink() or path != path.resolve():
            raise InventoryError('stale_target', 'login requires the fixed real account registry')
        with _registry_lock(path):
            account = self.execute('accounts.resolve', dict(selector=selector, expected_target=expected_target))['account']
            raw = path.read_text()
            info = path.stat()
            if info.st_uid != os.getuid() or info.st_mode & 0o077:
                raise InventoryError('unauthorized_target', 'account registry must be private and user-owned')
            data = tomllib.loads(raw)
            expected = copy.deepcopy(data)
            policy = expected
            for key in ('configuration', 'account', account['id']):
                policy = policy.setdefault(key, {})
                if not isinstance(policy, dict):
                    raise InventoryError('configuration_unavailable', 'account configuration scopes must be tables')
            if policy.get('cli_auth_credentials_store') == 'file':
                return account
            policy['cli_auth_credentials_store'] = 'file'
            bare = 'configuration.account.' + account['id']
            table = bare if re.fullmatch(r'[A-Za-z0-9_-]+', account['id']) and ('[' + bare + ']') in raw else 'configuration.account.' + json.dumps(account['id'])
            updated = _set_registry_value(raw, table, 'cli_auth_credentials_store', 'file')
            if tomllib.loads(updated) != expected:
                raise InventoryError('unsupported_target', 'login configuration cannot be edited without changing unrelated values')
            descriptor, temporary = tempfile.mkstemp(prefix='.accounts-auth-', dir=path.parent)
            try:
                with os.fdopen(descriptor, 'w') as output:
                    output.write(updated)
                    output.flush()
                    os.fsync(output.fileno())
                if path.read_text() != raw or path.stat().st_ino != info.st_ino:
                    raise InventoryError('stale_target', 'account registry changed before login configuration')
                os.replace(temporary, path)
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)
            return self.execute('accounts.resolve', {'selector': selector})['account']

    def _manage(self, operation, arguments):
        allowed = set() if operation == 'accounts.init' else {'selector', 'alias'}
        if not isinstance(arguments, dict) or set(arguments) - allowed:
            raise InventoryError('invalid_argument', 'unsupported account management arguments')
        path = self.path.absolute()
        # Management never follows a migration pointer or an alternate registry.
        if path.is_symlink() or path != path.resolve():
            raise InventoryError('stale_target', 'account management requires the fixed real registry')
        if operation == 'accounts.init' and not path.parent.exists():
            path.parent.mkdir(mode=0o700, parents=True)
        with _registry_lock(path):
            if operation == 'accounts.init':
                return self._initialize(path)
            return self._create(path, arguments)

    def _initialize(self, path):
        state = path.parent / 'accounts'
        shared = state / 'shared'
        if path.exists():
            data = tomllib.loads(path.read_text())
            if (data.get('accounts', {}).get('managed_by') != 'codex-wake'
                    or data.get('profiles', {}).get('state_root') != str(state)
                    or data['profiles'].get('source_root') != str(shared)):
                raise InventoryError('conflict', 'existing account registry is preserved; initialization will not overwrite it')
            _private_directory(state)
            _private_directory(shared)
            return dict(owner='codex-wake', registry=str(path), state_root=str(state), created=False)
        if state.exists() or state.is_symlink():
            raise InventoryError('conflict', 'existing account storage is preserved; choose a new isolated Wake root')
        state.mkdir(mode=0o700)
        shared.mkdir(mode=0o700)
        for relative in ('skills', 'rules'):
            (shared / relative).mkdir(mode=0o700)
        (shared / 'config.toml').touch(mode=0o600)
        content = ('[profiles]\nstate_root = ' + json.dumps(str(state))
                   + '\nsource_root = ' + json.dumps(str(shared))
                   + '\nselection_mode = "launcher"\nknown_profiles = []\ncheck_upstream_releases = false\n'
                   + '\n[accounts]\nmanaged_by = "codex-wake"\n')
        with path.open('x') as output:
            os.chmod(path, 0o600)
            output.write(content)
            output.flush()
            os.fsync(output.fileno())
        return dict(owner='codex-wake', registry=str(path), state_root=str(state), created=True)

    def _create(self, path, arguments):
        selector = _safe_name(arguments.get('selector'))
        alias = arguments.get('alias')
        if alias is not None:
            _safe_name(alias)
        if not path.is_file():
            raise InventoryError('configuration_unavailable', 'initialize the account registry first')
        info = path.stat()
        if info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise InventoryError('unauthorized_target', 'account registry must be private and user-owned')
        raw = path.read_text()
        data = tomllib.loads(raw)
        if 'migration' in data:
            raise InventoryError('unsupported_target', 'account creation in a migration registry requires its migration owner')
        settings = load_settings(path)
        if not data.get('profiles', {}).get('state_root') or settings.selection_mode != 'launcher':
            raise InventoryError('unsupported_target', 'account creation requires an explicit private launcher state root')
        if set(settings.shared_links) - {'config.toml', 'skills', 'rules'}:
            raise InventoryError('unsupported_target', 'private runtime state cannot be shared')
        _private_directory(settings.state_root)
        _private_directory(settings.shared_root)
        name = _safe_name(settings.normalize_profile_name(selector))
        if selector in settings.aliases and settings.resolve_profile_name(selector) != name:
            raise InventoryError('conflict', 'account name is already an alias')
        home = settings.state_root / name
        if alias is not None:
            if alias in settings.aliases and settings.resolve_profile_name(alias) != name:
                raise InventoryError('conflict', 'alias belongs to another account')
            names, inactive = account_inventory(settings, data)
            if settings.normalize_profile_name(alias) in set(names + inactive) - {name}:
                raise InventoryError('conflict', 'alias shadows an existing account')
        known = list(settings.known_profiles)
        configured = {settings.normalize_profile_name(value) for value in known}
        if home.exists() or home.is_symlink():
            if name not in configured or home.is_symlink():
                raise InventoryError('conflict', 'existing account directory is never adopted or overwritten')
            _private_directory(home)
            if alias is not None and settings.aliases.get(alias) != name:
                raise InventoryError('conflict', 'existing account creation arguments differ')
            return dict(self.execute('accounts.resolve', {'selector': name}), created=False, authentication='not_checked')
        if len(known) >= 256:
            raise InventoryError('unsupported_target', 'account registry exceeds bounded capacity')
        if 'enabled' in data.get('accounts', {}):
            raise InventoryError('unsupported_target', 'account creation under restricted admission requires the host policy workflow; no admission changed')
        # Qualify existing homes before effects: a rejected peer must not leave
        # an apparently failed creation published into the registry.
        self.execute('accounts.list', {})
        expected = copy.deepcopy(data)
        expected['profiles']['known_profiles'] = known + [name]
        updated = _set_registry_value(raw, 'profiles', 'known_profiles', known + [name])
        if alias is not None:
            expected['profiles'].setdefault('aliases', {})[alias] = name
            updated = _set_registry_value(updated, 'profiles.aliases', alias, name)
        if tomllib.loads(updated) != expected:
            raise InventoryError('unsupported_target', 'registry layout cannot be edited without changing unrelated configuration')
        # Shared assets are selected explicitly; no auth or historical files are copied.
        for relative in settings.shared_links:
            source = settings.shared_root / relative
            if not source.exists() or source.is_symlink() or source.resolve() != source:
                raise InventoryError('unsupported_target', 'shared configuration asset is unavailable or indirect')
        home.mkdir(mode=0o700)
        for relative in settings.shared_links:
            (home / relative).symlink_to(settings.shared_root / relative)
        descriptor, temporary = tempfile.mkstemp(prefix='.accounts-', dir=path.parent)
        try:
            with os.fdopen(descriptor, 'w') as output:
                output.write(updated)
                output.flush()
                os.fsync(output.fileno())
            if path.read_text() != raw or path.stat().st_ino != info.st_ino:
                raise InventoryError('stale_target', 'registry changed during account creation; new private home retained')
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        return dict(self.execute('accounts.resolve', {'selector': name}), created=True, authentication='not_configured')
