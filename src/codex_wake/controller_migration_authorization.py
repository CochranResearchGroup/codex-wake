"""Stable scoped migration grants over the common durable effect owner."""
import hashlib

from .controller_auth import AuthError
from .managed_inventory import InventoryError


class MigrationAuthorization:
    def __init__(self, authority, migration, *, runtime=None):
        self.authority, self.migration, self.runtime = authority, migration, runtime

    def execute(self, token, operation, arguments):
        if operation not in ('migration.preview', 'migration.apply', 'migration.rollback'):
            raise InventoryError('unsupported_operation', 'unsupported migration operation')
        if not isinstance(arguments, dict):
            raise InventoryError('invalid_argument', 'migration arguments must be an object')
        actor = self.authority.authenticate(token)
        required = 'migration.observe' if operation == 'migration.preview' else 'admin'
        if required not in actor.scopes:
            raise AuthError('insufficient_scope')
        stable = self.migration.scope_target()
        fields = {'host', 'environment', 'migration_id'}
        if operation != 'migration.preview' and 'fixture_id' in stable:
            fields.add('fixture_id')
        expected = arguments.get('expected_target')
        target = stable if operation == 'migration.preview' else expected
        if not isinstance(target, dict) or not fields <= target.keys() or any(target.get(key) != value for key, value in stable.items()):
            raise AuthError('insufficient_scope')
        # Stable scopes intentionally omit migration_revision; an explicitly
        # revision-restricted grant remains narrow rather than being broadened.
        scopes = [scope for scope in actor.targets if fields <= scope.keys()
                  and all(target.get(key) == value for key, value in scope.items()
                          if operation != 'migration.preview' or key != 'migration_revision')]
        if not scopes:
            raise AuthError('insufficient_scope')
        policy_sha = hashlib.sha256(self.migration.path.read_bytes()).hexdigest()
        def authorize():
            current = self.authority.authenticate(token)
            if current != actor:
                raise AuthError()
            # Configuration authority is pinned; own target filesystem effects
            # must not invalidate the reusable grant or final result delivery.
            if (self.migration.scope_target() != stable
                    or hashlib.sha256(self.migration.path.read_bytes()).hexdigest() != policy_sha):
                raise InventoryError('stale_target', 'host migration policy changed')
            return current
        authorize()
        if operation == 'migration.preview':
            value = self.migration.execute(operation, arguments, authorize=authorize)
            if not any(all(value['target'].get(key) == val for key, val in scope.items()) for scope in scopes):
                raise AuthError('insufficient_scope')
            authorize()
            return dict(schema_version=1, operation=operation, status='completed', result=value)
        request = arguments.get('_request')
        if isinstance(request, dict) and request.get('target') != expected:
            raise InventoryError('stale_target', 'durable intent must pin the expected migration target')
        if self.runtime is None:
            raise InventoryError('operation_runtime_required', 'durable admission and uncertain-effect reconciliation are required')
        return self.runtime.execute(actor, operation, arguments, authorize=authorize,
            dispatch=lambda op, payload: self.migration.execute(op, payload, authorize=authorize))
