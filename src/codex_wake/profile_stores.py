"""Stock stores and independent profile snapshots owned by the account registry."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import re
import tempfile
import tomllib
import uuid

from .managed_inventory import InventoryError

CATEGORIES = {'settings': ('config.toml',), 'hooks': ('hooks.json', 'hooks'),
              'skills': ('skills',), 'rules': ('rules',), 'mcp': ()}
EXCLUDED = {'auth.json', '.credentials.json', 'sessions', 'archived_sessions', 'history.jsonl',
            'memories', 'cache', 'log', 'logs', 'tmp', 'shell_snapshots', 'state_5.sqlite'}


def _generation(home):
    info = home.stat()
    return f'{info.st_dev}:{info.st_ino}'


def _save(path, text):
    descriptor, temporary = tempfile.mkstemp(prefix='.stores-', dir=path.parent)
    try:
        with os.fdopen(descriptor, 'w') as output:
            output.write(text)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _record(path, selector, record):
    from .controller_accounts import _set_registry_value
    text = path.read_text()
    for key, value in record.items():
        text = _set_registry_value(text, 'stores.' + json.dumps(selector), key, value)
    tomllib.loads(text)
    _save(path, text)


def _resolve(owner, selector):
    from .controller_accounts import _safe_name
    _safe_name(selector)
    data = tomllib.loads(owner.path.read_text())
    stores = data.get('stores', {})
    record = stores.get(selector)
    if record is None:
        account = owner.execute('accounts.resolve', {'selector': selector})['account']
        record = stores.get(account['id'])
        if record is None:
            record = dict(store_id='legacy:' + account['target']['home_generation'], kind='profile',
                          home=account['home'], independent=False,
                          home_generation=account['target']['home_generation'])
    home = Path(record['home'])
    if not home.is_dir() or home.is_symlink() or str(home.resolve()) != str(home) or _generation(home) != record['home_generation']:
        raise InventoryError('stale_target', 'store home changed; register the selected replacement explicitly')
    return dict(record, selector=selector, account_provenance='unknown; current login does not identify stored history')


def execute(owner, operation, arguments):
    from .controller_accounts import _safe_name, _registry_lock
    if not isinstance(arguments, dict):
        raise InventoryError('invalid_argument', 'store arguments must be an object')
    allowed = {'stores.register': {'selector', 'home'}, 'stores.resolve': {'selector'}, 'stores.list': set()}
    if operation not in allowed or set(arguments) - allowed[operation]:
        raise InventoryError('invalid_argument', 'unsupported store arguments')
    if operation == 'stores.resolve':
        return dict(owner='codex-wake', store=_resolve(owner, arguments.get('selector')))
    if operation == 'stores.list':
        data = tomllib.loads(owner.path.read_text())
        return dict(owner='codex-wake', stores=[_resolve(owner, name) for name in data.get('stores', {})])
    selector = _safe_name(arguments.get('selector'))
    if selector != 'stock':
        raise InventoryError('invalid_argument', 'register the stock store as stock; create profiles through accounts.create')
    value = arguments.get('home')
    if not isinstance(value, str):
        raise InventoryError('invalid_argument', 'stock registration requires an absolute home')
    home = Path(value)
    if (not home.is_absolute() or home != home.resolve() or not home.is_dir()
            or home.stat().st_uid != os.getuid() or home.stat().st_mode & 0o022):
        raise InventoryError('unauthorized_target', 'stock registration requires a canonical user-owned home without group or world writes; stock permissions are never changed')
    with _registry_lock(owner.path):
        data = tomllib.loads(owner.path.read_text())
        existing = data.get('stores', {}).get(selector)
        if existing:
            if existing['home'] != str(home) or existing['home_generation'] != _generation(home):
                raise InventoryError('conflict', 'registered stock home differs; existing identity is preserved')
        else:
            _record(owner.path, selector, dict(store_id=str(uuid.uuid4()), kind='stock', home=str(home),
                                             independent=False, home_generation=_generation(home)))
    return dict(owner='codex-wake', store=_resolve(owner, selector), stock_modified=False)


def _dependencies(value, home, entry=()):
    if isinstance(value, dict):
        for key, child in value.items():
            yield from _dependencies(child, home, entry + (key,))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _dependencies(child, home, entry + (str(index),))
    elif isinstance(value, str):
        paths = re.findall(r"(?<![A-Za-z0-9:])/(?:[^\s\"'`;|&<>]+)", value)
        for reference in paths:
            path = Path(reference)
            if not path.is_relative_to(home):
                yield dict(entry=list(entry), scope='external', value='[redacted]')
                break
            if not path.exists():
                yield dict(entry=list(entry), scope='unavailable_home_local', value='[redacted]')
                break


def inventory(home):
    from .configuration_sync import _inventory
    recognized = {item for values in CATEGORIES.values() for item in values}
    omissions = []
    entries = _inventory(dict(home=str(home)), list(CATEGORIES), allow_links=True, omissions=omissions)
    categories = {name: [item for item in values if (home / item).exists()] for name, values in CATEGORIES.items()}
    for name in ('mcp', 'hooks'):
        if any(category == name and json.loads(key)[0] == 'toml' for key, (category, _value) in entries.items()):
            categories[name].append('config.toml:' + ('mcp_servers' if name == 'mcp' else 'hooks'))
    config = home / "config.toml"
    data = tomllib.loads(config.read_text()) if config.exists() else {}
    return dict(unsupported_entries=omissions, dependencies=list(_dependencies(data, home)), categories=categories,
                entries={name: [json.loads(key) for key, (category, _value) in entries.items() if category == name] for name in CATEGORIES},
                external_dependencies='references outside the selected home are preserved; assets and credentials there are not copied',
                unknown=sorted(item.name for item in home.iterdir() if item.name not in recognized | EXCLUDED
                               and not item.name.endswith(('.sqlite', '.sqlite-wal', '.sqlite-shm'))),
                mcp_auth='operator keyring when supported; file credentials remain local and are not copied')


def _copy_asset(source, destination, source_home, destination_home, seen=frozenset()):
    from .configuration_sync import _safe_asset, _read_file, ASSET_RUNTIME
    if source.name in ASSET_RUNTIME:
        return
    resolved = _safe_asset(source_home, source, allow_links=True)
    if resolved in seen:
        raise InventoryError('unsupported_target', 'configuration asset link cycle')
    if source.is_dir():
        destination.mkdir(mode=0o700)
        for child in source.iterdir():
            _copy_asset(child, destination / child.name, source_home, destination_home, seen | {resolved})
    elif source.is_file():
        raw = _read_file(source_home, source, allow_links=True)
        try:
            raw = raw.decode().replace(str(source_home), str(destination_home)).encode()
        except UnicodeDecodeError:
            pass
        destination.write_bytes(raw)
        destination.chmod(0o700 if source.stat().st_mode & 0o111 else 0o600)
    else:
        raise InventoryError('unsupported_target', 'seed contains a non-file asset')


def create(owner, arguments):
    """Seed only configuration into a private new home; preserve legacy creation."""
    from .controller_accounts import _registry_lock, _safe_name, _set_registry_value, _private_directory
    from codex_profiles.config import load_settings
    if set(arguments) - {'selector', 'alias', 'mode', 'source'}:
        raise InventoryError('invalid_argument', 'unsupported independent profile arguments')
    selector = _safe_name(arguments.get('selector'))
    source = _resolve(owner, arguments.get('source', 'stock'))
    source_home = Path(source['home'])
    with _registry_lock(owner.path):
        settings = load_settings(owner.path)
        _private_directory(settings.state_root)
        name = _safe_name(settings.normalize_profile_name(selector))
        home = settings.state_root / name
        data = tomllib.loads(owner.path.read_text())
        if home.exists() or home.is_symlink():
            record = data.get('stores', {}).get(name)
            if record and record.get('independent') and record.get('seed_store_id') == source['store_id']:
                return dict(owner.execute('accounts.resolve', {'selector': name}), created=False, store=_resolve(owner, name))
            raise InventoryError('conflict', 'existing profile is preserved; use explicit adoption')
        if 'enabled' in data.get('accounts', {}):
            raise InventoryError('unsupported_target', 'selected account admission requires the existing host workflow')
        from .configuration_sync import _input_fingerprint, _inventory
        seed_fingerprint = _input_fingerprint(source, _inventory(source, list(CATEGORIES), allow_links=True), allow_links=True)
        assets = inventory(source_home)
        stage = Path(tempfile.mkdtemp(prefix='.profile-seed-', dir=settings.state_root))
        try:
            for values in CATEGORIES.values():
                for relative in values:
                    item = source_home / relative
                    if item.exists() or item.is_symlink():
                        _copy_asset(item, stage / relative, source_home, home)
            from .configuration_sync import seed_assets
            for relative in seed_assets(source_home):
                if not (stage / relative).exists():
                    (stage / relative).parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                    _copy_asset(source_home / relative, stage / relative, source_home, home)
            config = stage / 'config.toml'
            if config.exists():
                text = config.read_text()
                # Codex account credentials must not inherit operator keyring identity.
                text = re.sub(r'(?m)^cli_auth_credentials_store\s*=.*\n?', '', text)
                text = 'cli_auth_credentials_store = "file"\n' + text
                tomllib.loads(text)
                config.write_text(text)
            raw = owner.path.read_text()
            updated = _set_registry_value(raw, 'profiles', 'known_profiles', list(settings.known_profiles) + [name])
            if arguments.get('alias'):
                alias = _safe_name(arguments['alias'])
                if alias in settings.aliases:
                    raise InventoryError('conflict', 'alias already exists')
                updated = _set_registry_value(updated, 'profiles.aliases', alias, name)
            # Revalidate the selected source before publishing the snapshot.
            current_source = _resolve(owner, arguments.get('source', 'stock'))
            if _input_fingerprint(current_source, _inventory(current_source, list(CATEGORIES), allow_links=True), allow_links=True) != seed_fingerprint:
                raise InventoryError('stale_target', 'seed configuration changed; retry from a fresh source snapshot')
            tomllib.loads(updated)
            record = dict(store_id=str(uuid.uuid4()), kind='profile', home=str(home), independent=True,
                          home_generation=_generation(stage), seed_store_id=source['store_id'])
            for key, value in record.items():
                updated = _set_registry_value(updated, 'stores.' + json.dumps(name), key, value)
            tomllib.loads(updated)
            from .configuration_sync import capture_seed
            stage.rename(home)
            try:
                capture_seed(owner, source, record)
                _save(owner.path, updated)
            except Exception:
                # Registry publication is the authority boundary. Preserve an
                # uncertain published home; remove only a definitely unclaimed one.
                published = tomllib.loads(owner.path.read_text()).get('stores', {}).get(name)
                if published != record and home.exists():
                    shutil.rmtree(home)
                raise
        finally:
            if stage.exists():
                shutil.rmtree(stage)
    return dict(owner.execute('accounts.resolve', {'selector': name}), created=True, store=_resolve(owner, name),
                inventory=assets, authentication='profile-local; not copied', activation='next_launch')
