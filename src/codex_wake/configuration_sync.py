"""Explicit, directional configuration synchronization over registered stores.

Only hashes, identities and redacted outcomes are retained in Wake metadata.
Configuration remains owned by the selected homes and the existing TOML editor.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import tomllib

from .managed_inventory import InventoryError
from .profile_stores import CATEGORIES, EXCLUDED, _save

PROTECTED = {'cli_auth_credentials_store', 'forced_login_method', 'forced_chatgpt_workspace_id'}


ASSET_RUNTIME = {'.venv', 'node_modules', '__pycache__', '.git', '.hg', '.svn', '.pytest_cache', '.ruff_cache', '.env'}

def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def _fail(code, message):
    raise InventoryError(code, message)


def _metadata(owner):
    from .controller_accounts import _private_directory
    directory = owner.path.parent / ('.' + owner.path.name + '.configuration-sync')
    directory.mkdir(mode=0o700, exist_ok=True)
    _private_directory(directory)
    return directory


def _load(path):
    from .a2a_bus import private_path
    if path.exists():
        private_path(path)
        if path.stat().st_size > 16 * 1024 * 1024:
            _fail('configuration_unavailable', 'sync metadata exceeds bound')
        return json.loads(path.read_text())
    return {}


def _leaf_values(value, prefix=()):
    for key, item in value.items():
        if isinstance(item, dict) and item:
            yield from _leaf_values(item, prefix + (key,))
        else:
            yield prefix + (key,), item


def _category(path):
    if path[0] == 'mcp_servers':
        return 'mcp'
    if path[0] == 'hooks':
        return 'hooks'
    return 'settings'


def _safe_asset(home, path, allow_links=False):
    relative = path.relative_to(home)
    try:
        resolved = path.resolve()
    except RuntimeError:
        _fail('unsupported_target', 'configuration asset link cycle')
    if resolved == home:
        _fail('unsupported_target', 'configuration asset cannot select the entire store')
    within_home = resolved.is_relative_to(home)
    protected_names = {'auth.json', '.credentials.json', 'credentials.json', 'tokens.json',
                       '.env', '.ssh', '.gnupg', 'id_rsa', 'id_ed25519', 'keyring'}
    parts = (*relative.parts, *resolved.parts)
    if (relative.parts[0] in EXCLUDED
            or within_home and resolved.relative_to(home).parts[0] in EXCLUDED
            or any(part in protected_names or 'credential' in part.lower() for part in parts)):
        _fail('unsupported_target', 'configuration asset crosses its authentication or runtime boundary')
    # Explicitly configured skills/rules/hooks may live outside CODEX_HOME.
    # Only the source can follow these links; destinations are private copies.
    linked_configuration = allow_links and relative.parts[0] in {'skills', 'rules', 'hooks'} and resolved != path
    if not within_home and not linked_configuration:
        _fail('unsupported_target', 'external configuration reference requires explicit asset selection')
    if not allow_links and resolved != path:
        _fail('unsupported_target', 'configuration destination requires private direct local assets')
    return resolved


def _read_file(home, path, allow_links=False):
    resolved = _safe_asset(home, path, allow_links)
    if not resolved.is_file() or resolved.stat().st_size > 4 * 1024 * 1024:
        _fail('unsupported_target', 'configuration asset must be a bounded regular local file')
    return resolved.read_bytes()


def _walk_files(home, path, allow_links=False, seen=frozenset(), omissions=None):
    if path.name in ASSET_RUNTIME:
        if omissions is not None:
            omissions.append(dict(entry=str(path.relative_to(home)), reason='runtime_dependency_not_copied'))
        return
    resolved = _safe_asset(home, path, allow_links)
    if resolved.is_dir():
        if resolved in seen:
            _fail('unsupported_target', 'configuration asset link cycle')
        for child in resolved.iterdir():
            yield from _walk_files(home, path / child.name, allow_links, seen | {resolved}, omissions)
    elif path.exists() or path.is_symlink():
        yield path


def _references(value, home):
    if isinstance(value, str):
        for matched in re.findall(re.escape(str(home)) + r"/[^\s\"'`;|&<>]+", value):
            path = Path(matched)
            relative = path.relative_to(home)
            if '..' in relative.parts or relative.parts[0] in EXCLUDED or any('credential' in part.lower() or part.lower() == 'auth.json' for part in relative.parts):
                _fail('unsupported_target', 'configuration references authentication or runtime state')
            if path.exists() or path.is_symlink():
                yield relative
    elif isinstance(value, (list, dict)):
        for item in (value.values() if isinstance(value, dict) else value):
            yield from _references(item, home)


def seed_assets(home):
    """Return configuration-referenced local assets for the seed owner."""
    entries = _inventory(dict(home=str(home)), list(CATEGORIES), allow_links=True)
    return sorted({json.loads(key)[1] for key in entries if json.loads(key)[0] == 'asset'})


def _inventory(store, categories, *, allow_links=False, omissions=None):
    home = Path(store['home'])
    entries = {}
    config = home / 'config.toml'
    if config.exists() or config.is_symlink():
        data = tomllib.loads(_read_file(home, config, allow_links).decode())
        for path, value in _leaf_values(data):
            category = _category(path)
            if category in categories and path[0] not in PROTECTED:
                key = json.dumps(['toml', *path])
                entries[key] = (category, value)
    references = []
    for key, (category, value) in list(entries.items()):
        references.extend((category, relative) for relative in _references(value, home))
    hooks_json = home / 'hooks.json'
    if 'hooks' in categories and hooks_json.exists():
        data = json.loads(_read_file(home, hooks_json, allow_links))
        if not isinstance(data, dict):
            _fail('unsupported_target', 'hooks JSON requires an object')
        for path, value in _leaf_values(data):
            entries[json.dumps(['json', *path])] = ('hooks', value)
            references.extend(('hooks', relative) for relative in _references(value, home))
    for category in categories:
        for relative in CATEGORIES[category]:
            if relative in ('config.toml', 'hooks.json'):
                continue
            path = home / relative
            for item in _walk_files(home, path, allow_links, omissions=omissions):
                key = json.dumps(['file', str(item.relative_to(home))])
                entries[key] = (category, _read_file(home, item, allow_links))
    for category, relative in references:
        path = home / relative
        for item in _walk_files(home, path, allow_links, omissions=omissions):
            entries[json.dumps(['asset', str(item.relative_to(home)), category])] = (category, _read_file(home, item, allow_links))
    return entries


def _normalized(value, home):
    if isinstance(value, bytes):
        try:
            value = value.decode()
        except UnicodeDecodeError:
            return {'binary_sha256': hashlib.sha256(value).hexdigest()}
    if isinstance(value, str):
        return value.replace(str(home), '${CODEX_HOME}')
    if isinstance(value, list):
        return [_normalized(item, home) for item in value]
    if isinstance(value, dict):
        return {key: _normalized(item, home) for key, item in value.items()}
    return value


def _hashes(entries, home):
    result = {}
    aliases = _asset_aliases(entries, home)
    for key, (_, value) in entries.items():
        path = json.loads(key)
        executable = bool((Path(home) / path[1]).stat().st_mode & 0o111) if path[0] in ('file', 'asset') else None
        result[key] = _digest([_normalized(_remap(value, home, home, aliases), home), executable])
    return result


def _input_fingerprint(store, entries, *, allow_links=False):
    home = Path(store["home"])
    config = home / "config.toml"
    raw = hashlib.sha256(_read_file(home, config, allow_links)).hexdigest() if config.exists() else None
    hooks = home / 'hooks.json'
    hooks_raw = hashlib.sha256(_read_file(home, hooks, allow_links)).hexdigest() if hooks.exists() else None
    return _digest([store, raw, hooks_raw, _hashes(entries, home)])


def _pair(source, destination):
    return _digest([source['store_id'], source['home_generation'], destination['store_id'], destination['home_generation']])


def capture_seed(owner, source, destination):
    """Record the actual seed, before users can edit either side."""
    categories = list(CATEGORIES)
    src = _inventory(source, categories, allow_links=True)
    dst = _inventory(destination, categories)
    state = dict(source=_hashes(src, source['home']), destination=_hashes(dst, destination['home']))
    _save(_metadata(owner) / (_pair(source, destination) + '.json'), json.dumps(state))
    reverse = dict(source=state['destination'], destination=state['source'])
    _save(_metadata(owner) / (_pair(destination, source) + '.json'), json.dumps(reverse))


def _asset_aliases(entries, home):
    """Map only materialized asset paths from canonical to logical locations."""
    home = Path(home)
    aliases = {}
    for key in sorted(entries):
        entry = json.loads(key)
        if entry[0] not in ('file', 'asset'):
            continue
        path = home / entry[1]
        while path != home:
            resolved = path.resolve()
            if resolved != path:
                aliases.setdefault(str(resolved), str(path))
            path = path.parent
    return aliases


def _remap(value, source, destination, aliases=None):
    if isinstance(value, bytes):
        try:
            return _remap(value.decode(), source, destination, aliases).encode()
        except UnicodeDecodeError:
            return value
    if isinstance(value, str):
        if aliases:
            # One simultaneous substitution keeps a logical destination from
            # becoming another canonical source alias during the same rewrite.
            pattern = '|'.join(re.escape(path) for path in sorted(aliases, key=len, reverse=True))
            value = re.sub('(?:' + pattern + r')(?![A-Za-z0-9_./-])',
                           lambda match: aliases[match.group()], value)
        return value.replace(str(source), str(destination))
    if isinstance(value, list):
        return [_remap(item, source, destination, aliases) for item in value]
    if isinstance(value, dict):
        return {key: _remap(item, source, destination, aliases) for key, item in value.items()}
    return value


def _edit_toml(text, path, value, delete=False):
    from .controller_accounts import _set_registry_value
    # The existing registry editor also handles root keys through a temporary
    # table. Validate the complete semantic diff before publishing the result.
    before = tomllib.loads(text)
    expected = json.loads(json.dumps(before))
    cursor = expected
    for part in path[:-1]:
        cursor = cursor.setdefault(part, {})
    if delete:
        cursor.pop(path[-1], None)
    else:
        cursor[path[-1]] = value
    table = '.'.join(json.dumps(part) for part in path[:-1])
    if not table:
        marker = '__wake_sync_root__'
        wrapped = '[' + marker + ']\n' + text
        changed = _set_registry_value(wrapped, marker, path[-1], value if not delete else '__wake_delete__')
        changed = changed.removeprefix('[' + marker + ']\n')
    else:
        # Conventional unquoted headings remain supported by the existing editor.
        conventional = '.'.join(path[:-1])
        table = conventional if '[' + conventional + ']' in text else table
        changed = _set_registry_value(text, table, path[-1], value if not delete else '__wake_delete__')
    if delete:
        changed = re.sub(r'(?m)^' + re.escape(json.dumps(path[-1])) + r' = "__wake_delete__"\n', '', changed)
    if tomllib.loads(changed) != expected:
        _fail('unsupported_target', 'configuration layout requires native editing; no changes applied')
    return changed


def execute(owner, operation, arguments, *, reload_executor=None):
    """Preview/apply selected entries; reload_executor is a supported scoped owner."""
    from .controller_accounts import _registry_lock
    allowed = {'source', 'destinations', 'categories', 'operation_id', 'expected_snapshot', 'propagate_deletions', 'reload'}
    if operation not in ('configuration.sync.preview', 'configuration.sync.apply'):
        _fail('unsupported_operation', 'unsupported configuration sync operation')
    if not isinstance(arguments, dict) or set(arguments) - allowed:
        _fail('invalid_argument', 'unsupported sync arguments')
    destinations, categories = arguments.get('destinations'), arguments.get('categories')
    operation_id = arguments.get('operation_id')
    if (not isinstance(arguments.get('source'), str) or not isinstance(destinations, list) or not 1 <= len(destinations) <= 64
            or any(not isinstance(item, str) for item in destinations) or len(set(destinations)) != len(destinations)
            or not isinstance(categories, list) or not categories or any(not isinstance(item, str) or item not in CATEGORIES for item in categories)
            or len(set(categories)) != len(categories) or not isinstance(operation_id, str)
            or re.fullmatch(r'[A-Za-z0-9_-]{1,128}', operation_id) is None
            or any(key in arguments and type(arguments[key]) is not bool for key in ('reload', 'propagate_deletions'))):
        _fail('invalid_argument', 'explicit source, destinations, categories and bounded operation identity required')
    request = {key: value for key, value in arguments.items() if key != 'expected_snapshot'}
    with _registry_lock(owner.path):
        directory = _metadata(owner)
        receipt_path = directory / ('operation-' + _digest(operation_id) + '.json')
        previous = _load(receipt_path)
        if previous:
            if previous['request'] != _digest(request) or (operation.endswith('apply') and previous['snapshot'] != arguments.get('expected_snapshot')):
                _fail('conflict', 'operation identity already belongs to different inputs')
            if previous.get('state') != 'complete':
                _fail('outcome_unknown', 'prior sync may have effects; reconcile selected configuration and reload before a new submission')
            return previous['result']
        source = owner.execute('stores.resolve', {'selector': arguments['source']})['store']
        src = _inventory(source, categories, allow_links=True)
        source_hashes = _hashes(src, source['home'])
        source_aliases = _asset_aliases(src, source['home'])
        plans, snapshot_data = [], []
        fingerprints = [(source, _input_fingerprint(source, src, allow_links=True))]
        for selector in destinations:
            destination = owner.execute('stores.resolve', {'selector': selector})['store']
            if source['store_id'] == destination['store_id'] or source['home'] == destination['home']:
                _fail('invalid_argument', 'source and destination must be distinct stores')
            dst = _inventory(destination, categories)
            destination_hashes = _hashes(dst, destination['home'])
            baseline_path = directory / (_pair(source, destination) + '.json')
            baseline = _load(baseline_path)
            if not baseline and source.get('seed_store_id') and source.get('seed_store_id') == destination.get('seed_store_id'):
                seed = next((store for store in owner.execute('stores.list', {})['stores'] if store['store_id'] == source['seed_store_id']), None)
                if seed:
                    left = _load(directory / (_pair(seed, source) + '.json'))
                    right = _load(directory / (_pair(seed, destination) + '.json'))
                    if left and right and left['source'] == right['source']:
                        baseline = dict(source=left['destination'], destination=right['destination'])
            baseline = baseline or dict(source={}, destination={})
            decisions = []
            for key in sorted(set(src) | set(dst) | set(baseline['source']) | set(baseline['destination'])):
                path = json.loads(key)
                category = _category(path[1:]) if path[0] == 'toml' else ('hooks' if path[0] == 'json' else (path[2] if path[0] == 'asset' else next((name for name, paths in CATEGORIES.items() if any(path[1] == p or path[1].startswith(p + '/') for p in paths)), None)))
                if category not in categories:
                    continue
                s, d = source_hashes.get(key), destination_hashes.get(key)
                bs, bd = baseline['source'].get(key), baseline['destination'].get(key)
                if s == d:
                    status = 'unchanged'
                elif s == bs:
                    status = 'preserved'
                elif s is None and not arguments.get('propagate_deletions', False):
                    status = 'deletion_preserved'
                elif d != bd:
                    status = 'conflict'
                else:
                    status = 'delete' if s is None else 'update'
                decisions.append(dict(entry=path, category=category, status=status))
            fingerprints.append((destination, _input_fingerprint(destination, dst)))
            snapshot_data.append([_input_fingerprint(source, src, allow_links=True), _input_fingerprint(destination, dst), baseline])
            plans.append((destination, dst, baseline_path, baseline, decisions))
        snapshot = _digest([request, snapshot_data])
        result = dict(owner='codex-wake', operation_id=operation_id, snapshot=snapshot, activation='next_launch',
                      destinations=[dict(selector=destination['selector'], store_id=destination['store_id'], entries=decisions)
                                    for destination, _, _, _, decisions in plans])
        if operation.endswith('preview'):
            return result
        if arguments.get('expected_snapshot') != snapshot:
            _fail('stale_target', 'sync inputs changed; preview the selected stores again')
        # Build and validate all selected configuration edits before any write.
        writes = []
        modes = {}
        baselines = []
        for destination, dst, baseline_path, baseline, decisions in plans:
            home = Path(destination['home'])
            text = (home / 'config.toml').read_text() if (home / 'config.toml').exists() else ''
            changed_config = False
            json_path = home / 'hooks.json'
            json_data = json.loads(json_path.read_text()) if json_path.exists() else {}
            changed_json = False
            for decision in decisions:
                key = json.dumps(decision['entry'])
                status = decision['status']
                if status in ('update', 'delete'):
                    path = decision['entry']
                    value = _remap(src[key][1], source['home'], destination['home'], source_aliases) if key in src else None
                    if path[0] == 'toml':
                        text = _edit_toml(text, path[1:], value, status == 'delete')
                        changed_config = True
                    elif path[0] == 'json':
                        cursor = json_data
                        for part in path[1:-1]:
                            cursor = cursor.setdefault(part, {})
                        if status == 'delete':
                            cursor.pop(path[-1], None)
                        else:
                            cursor[path[-1]] = value
                        changed_json = True
                    else:
                        writes.append((home / path[1], value))
                        if value is not None:
                            modes[home / path[1]] = 0o700 if (Path(source['home']) / path[1]).stat().st_mode & 0o111 else 0o600
                    if status == 'delete':
                        baseline['source'].pop(key, None)
                        baseline['destination'].pop(key, None)
                    else:
                        baseline['source'][key] = source_hashes[key]
                        baseline['destination'][key] = source_hashes[key]
                elif status == 'unchanged':
                    if key in source_hashes:
                        baseline['source'][key] = baseline['destination'][key] = source_hashes[key]
            if changed_json:
                writes.append((json_path, json.dumps(json_data, indent=2).encode()))
            if changed_config:
                writes.append((home / 'config.toml', text.encode()))
            baselines.append((baseline_path, baseline))
        for store, fingerprint in fingerprints:
            current = owner.execute('stores.resolve', {'selector': store['selector']})['store']
            if _input_fingerprint(current, _inventory(current, categories, allow_links=current['store_id'] == source['store_id']), allow_links=current['store_id'] == source['store_id']) != fingerprint:
                _fail('stale_target', 'selected configuration changed while preparing sync')
        for path, _value in writes:
            home = next(Path(destination['home']) for destination, *_rest in plans if path.is_relative_to(Path(destination['home'])))
            _safe_asset(home, path)
        _save(receipt_path, json.dumps(dict(request=_digest(request), snapshot=snapshot, state='applying')))
        for path, value in writes:
            if value is None:
                path.unlink(missing_ok=True)
            else:
                path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                if isinstance(value, bytes):
                    import tempfile
                    descriptor, temporary = tempfile.mkstemp(prefix='.sync-', dir=path.parent)
                    try:
                        with os.fdopen(descriptor, 'wb') as output:
                            output.write(value)
                            output.flush()
                            os.fsync(output.fileno())
                        os.chmod(temporary, modes.get(path, 0o600))
                        os.replace(temporary, path)
                    finally:
                        if os.path.exists(temporary):
                            os.unlink(temporary)
        for path, baseline in baselines:
            _save(path, json.dumps(baseline))
        if arguments.get('reload'):
            for item, (destination, *_rest) in zip(result['destinations'], plans):
                if destination['kind'] != 'profile' or reload_executor is None:
                    item['reload'] = 'unsupported; use next launch or supported selected-profile reload'
                else:
                    item['reload'] = reload_executor(destination) or 'requested_selected_profile'
        _save(receipt_path, json.dumps(dict(request=_digest(request), snapshot=snapshot, result=result, state='complete')))
        return result
