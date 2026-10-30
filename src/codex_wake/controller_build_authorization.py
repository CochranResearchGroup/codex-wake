"""Build mutation admission; durable effect execution belongs to operation runtime.

The runtime must persist intent before dispatch and reconcile uncertain launches
without replay. This module deliberately refuses effects without that owner.
"""
import hashlib
from pathlib import Path

from .controller_auth import AuthError
from .managed_inventory import InventoryError


class BuildAuthorization:
    OPERATIONS = frozenset(('builds.launch', 'builds.stage', 'builds.select', 'builds.rollback'))
    ACCOUNT_FIELDS = frozenset(('host', 'environment', 'provider', 'account', 'home',
                               'home_generation', 'configuration_revision', 'build_channel',
                               'build_sha256', 'build_revision', 'executable'))

    def __init__(self, authority, builds, *, recipe_targets=None, runtime=None):
        self.authority, self.builds = authority, builds
        self.recipe_targets = dict(recipe_targets or {})
        self.runtime = runtime

    def execute(self, token, operation, arguments):
        actor = self.authority.authenticate(token)
        if operation not in self.OPERATIONS:
            raise InventoryError('unsupported_operation', 'unsupported build mutation')
        required = 'admin' if operation in ('builds.stage', 'builds.select', 'builds.rollback') else 'control'
        if required not in actor.scopes:
            raise AuthError('insufficient_scope')
        if not isinstance(arguments, dict):
            raise InventoryError('invalid_argument', 'object arguments required')
        if operation == 'builds.stage':
            target = self.recipe_targets.get(arguments.get('recipe'))
            fields = {'host', 'environment', 'recipe', 'recipe_sha256'}
        else:
            target = arguments.get('expected_target')
            fields = self.ACCOUNT_FIELDS
        if not isinstance(target, dict) or not fields <= target.keys():
            raise AuthError('insufficient_scope')
        request = arguments.get('_request')
        if request is not None and (not isinstance(request, dict) or request.get('target') != target):
            raise InventoryError('stale_target', 'durable request must name the authorized target')
        if not any(fields <= scope.keys() and all(target.get(k) == v for k, v in scope.items())
                   for scope in actor.targets):
            raise AuthError('insufficient_scope')
        def authorize():
            current = self.authority.authenticate(token)
            if current != actor:
                raise AuthError()
            if operation == 'builds.stage':
                path = self.builds.recipes.get(arguments.get('recipe'))
                try:
                    digest = hashlib.sha256(Path(path).read_bytes()).hexdigest()
                except (OSError, TypeError):
                    raise InventoryError('stale_target', 'host recipe is unavailable') from None
                if digest != target['recipe_sha256']:
                    raise InventoryError('stale_target', 'host recipe changed since authorization')
            return current
        authorize()
        if self.runtime is None:
            raise InventoryError('operation_runtime_required', 'durable mutation intent and uncertain-effect reconciliation required')
        # Runtime owns durable idempotency, cancellation/reconnect, result custody,
        # and a final admission callback immediately before invoking this owner.
        return self.runtime.execute(actor, operation, arguments,
                                    authorize=authorize,
                                    dispatch=self.builds.execute)
