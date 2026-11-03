"""Human terminal conveniences never relax the existing pinned owner contract."""
import json
import sys
from uuid import uuid4

from .managed_inventory import InventoryError


def interactive():
    return sys.stdin.isatty() and sys.stdout.isatty()


def require_terminal(missing):
    if missing and not interactive():
        raise InventoryError('explicit_target_required', 'noninteractive execution requires ' + ', '.join(missing))


def show_intent(operation, target, key, *, source=None):
    if not isinstance(target, dict) or (source is not None and not isinstance(source, dict)):
        raise InventoryError('invalid_argument', 'exact target pins must be JSON objects')
    selected = {field: target.get(field) for field in ('account', 'home', 'process', 'build_channel', 'build_revision', 'build_sha256', 'executable')}
    print(operation + ' exact target: ' + json.dumps(selected, sort_keys=True), file=sys.stderr)
    if source is not None:
        print('Source target: ' + json.dumps(source, sort_keys=True), file=sys.stderr)
    print('Intent key: ' + key + '; retain this key and the target to reconcile an uncertain result.', file=sys.stderr)


def confirm_intent(message, confirmed=False):
    print(message, file=sys.stderr)
    if confirmed:
        return True
    print('Continue? [y/N] ', end='', file=sys.stderr, flush=True)
    if sys.stdin.readline().strip().casefold() not in ('y', 'yes'):
        raise InventoryError('confirmation_required', 'operation cancelled; no mutation submitted')
    return True


def intent_key():
    return 'interactive-' + uuid4().hex
