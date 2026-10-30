"""Wake account/configuration owner, reusing the absorbed Profiles implementation.

This owner selects existing homes and explains configuration. It never opens
credential files, changes the selected account, or launches provider work.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import re
import tomllib

from codex_profiles.config import load_settings
from .managed_inventory import InventoryError

_NAME = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\Z')
_PRIVATE = {'auth.json', 'sessions', 'history.jsonl', 'memories', 'cache', 'log'}


def _safe_name(value):
    if not isinstance(value, str) or not _NAME.fullmatch(value):
        raise InventoryError('invalid_argument', 'account names must be bounded identifiers')
    return value


def _redact(value, key=''):
    if any(word in key.lower() for word in ('token', 'secret', 'password', 'api_key', 'credential', 'authorization')) or 'env' in key.lower().split('.'):
        return '[redacted]'
    if isinstance(value, dict):
        return {k: _redact(v, k) for k, v in value.items()}
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


class ControllerAccounts:
    def __init__(self, config_path, *, host, environment):
        self.path = Path(config_path)
        self.host, self.environment = host, environment

    def execute(self, operation, arguments):
        if operation not in ('accounts.list', 'accounts.resolve', 'configuration.explain'):
            raise InventoryError('unsupported_operation', 'unsupported account operation')
        allowed = set() if operation == 'accounts.list' else {'selector', 'expected_target'}
        if not isinstance(arguments, dict) or set(arguments) - allowed:
            raise InventoryError('invalid_argument', 'unsupported account arguments')
        if not self.path.is_file():
            raise InventoryError('configuration_unavailable', 'host account configuration is unavailable')
        try:
            raw = self.path.read_bytes()
            data = tomllib.loads(raw.decode())
            settings = load_settings(self.path)
            # Profiles defaults are useful for legacy commands, but controller
            # inventory must never silently discover the operator home.
            if not data.get('profiles', {}).get('state_root'):
                raise ValueError('explicit state_root required')
            configured = list(settings.known_profiles) + list(settings.aliases.values())
            if settings.default_profile:
                configured.append(settings.default_profile)
            discovered = list(settings.state_root.glob(settings.account_prefix + '*'))
            if len(discovered) > 256:
                raise ValueError('account discovery exceeds bounded capacity')
            configured += [path.name for path in discovered if path.is_dir()]
            names = sorted({_safe_name(settings.resolve_profile_name(_safe_name(name))) for name in configured})
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
            if operation == 'accounts.list':
                return dict(owner='codex-wake', accounts=accounts)
            selector = _safe_name(arguments.get('selector'))
            name = _safe_name(settings.resolve_profile_name(selector))
            matches = [account for account in accounts if account['id'] == name]
            if not matches:
                raise InventoryError('target_not_found', 'account is not configured')
            account = matches[0]
            if arguments.get('expected_target') is not None and arguments['expected_target'] != account['target']:
                raise InventoryError('stale_target', 'account or configuration generation changed')
            if operation == 'accounts.resolve':
                return dict(owner='codex-wake', account=account, grants_operations=False)
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
