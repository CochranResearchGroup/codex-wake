"""Resolve a completed, fixture-qualified cutover for normal Wake entrypoints.

The fixed host registry remains routing/rollback authority. Only its declared
candidate, active pointer and private completed receipt can select a new owner.
This loader never guesses a namespace from an arbitrary symlink or copies auth.
"""
import hashlib
import json
import os
from pathlib import Path
import socket
import tomllib

from .managed_inventory import InventoryError


def resolve_registry(path, *, root=None, host=None, environment=None):
    requested = Path(path)
    if not requested.is_file():
        return requested
    route = Path(root) / 'controller-accounts.toml' if root is not None else requested
    if not route.is_file():
        route = requested
    try:
        raw = route.read_bytes()
        data = tomllib.loads(raw.decode())
    except (OSError, ValueError, UnicodeError):
        return requested
    if 'migration' not in data:
        return requested
    policy = data['migration']
    if route.is_symlink():
        raise InventoryError('stale_target', 'host migration routing registry must remain a real file')
    try:
        candidate = Path(policy['candidate_root']) / 'controller-accounts.toml'
        # An explicitly selected candidate is already a caller-selected registry,
        # not an automatic host pointer lookup. Normal host entrypoints pass root
        # or the fixed host path and must prove the receipt below.
        if root is None and requested == candidate and not candidate.is_symlink() and Path(data['profiles']['state_root']) == candidate.parent / 'accounts':
            return requested
        pointer, legacy = Path(policy['pointer']), Path(policy['legacy_config'])
        if not pointer.is_symlink() or pointer.resolve() == legacy:
            if root is not None and requested != route:
                raise InventoryError('stale_target', 'requested candidate is no longer active')
            return route
        if pointer.resolve() != candidate or candidate.is_symlink() or not candidate.is_file():
            raise InventoryError('stale_target', 'active registry is not the declared migration candidate')
        from .controller_migration import ControllerMigration
        provenance = Path(root) if root is not None else route.parent
        owner = ControllerMigration(route, root=provenance, host=host or socket.gethostname(),
            environment=environment or os.environ.get('WSL_DISTRO_NAME') or os.name)
        unused_data, settings, fixture, marker, paths = owner._configuration()
        if marker is None or paths['candidate_root'] != paths['candidate_root'].resolve():
            raise InventoryError('production_not_authorized', 'unqualified production registry cutover remains gated by issue380')
        directory = provenance / 'controller-migration'
        if directory.is_symlink() or not directory.is_dir() or directory.stat().st_mode & 0o077:
            raise InventoryError('stale_target', 'private migration receipt custody is unavailable')
        matched = []
        files = list(directory.glob('*.json'))
        if len(files) > 256:
            raise InventoryError('unsupported_target', 'migration receipt lookup exceeds bounded capacity')
        for receipt_path in files:
            if receipt_path.is_symlink() or receipt_path.stat().st_mode & 0o077 or receipt_path.stat().st_size > 8 * 1024 * 1024:
                raise InventoryError('stale_target', 'migration receipt custody changed')
            receipt = json.loads(receipt_path.read_text())
            if (receipt.get('schema_version') == 1 and receipt.get('state') == 'applied'
                    and receipt.get('scope') == owner.scope_target()
                    and receipt.get('candidate') == str(paths['candidate_root'])
                    and receipt.get('pointer') == str(pointer)
                    and receipt.get('pointer_after') == os.readlink(pointer)
                    and receipt.get('policy_sha') == hashlib.sha256(raw).hexdigest()):
                matched.append(receipt)
        if len(matched) != 1:
            raise InventoryError('stale_target', 'one completed attributable cutover receipt is required')
        for home in matched[0]['homes']:
            old, new = Path(home['old']), Path(home['new'])
            if (old.parent != settings.state_root or new.parent != paths['candidate_root'] / 'accounts'
                    or old.name != new.name or not old.is_symlink() or os.readlink(old) != str(new)
                    or new != new.resolve() or not new.is_dir()):
                raise InventoryError('stale_target', 'qualified owning account cutover binding changed')
        active = tomllib.loads(candidate.read_text())
        if (Path(active['profiles']['state_root']) != paths['candidate_root'] / 'accounts'
                or Path(active['profiles']['source_root']) != settings.source_root
                or active.get('migration') != policy):
            raise InventoryError('stale_target', 'candidate registry escaped the qualified account/source scope')
        return candidate
    except InventoryError:
        raise
    except (OSError, ValueError, KeyError, TypeError, RuntimeError):
        raise InventoryError('stale_target', 'active migration registry cannot be qualified') from None
