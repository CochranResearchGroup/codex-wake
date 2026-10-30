"""Read-only controller operation service over the existing managed inventory.

Host/environment are trusted adapter configuration, never selector inputs.
Inventory membership and observation do not grant control authority.
"""
from __future__ import annotations

from .managed_inventory import InventoryError


class ControllerOperations:
    def __init__(self, inventory, *, host, environment, accounts=None, builds=None, hosts=None, history_runtime=None, history_now=None, migration=None, migration_writer_probe=None):
        self.migration, self.migration_writer_probe = migration, migration_writer_probe
        self.history_runtime, self.history_now = history_runtime, history_now
        self.hosts = hosts
        self.builds = builds
        self.accounts = accounts
        self.inventory = inventory
        self.host = host
        self.environment = environment

    def execute(self, operation, arguments, *, actor=None, authorize=None):
        if operation.startswith('migration.'):
            if self.migration is None:
                raise InventoryError('configuration_unavailable', 'host migration owner is unavailable')
            return dict(schema_version=1, operation=operation, status='completed',
                result=self.migration.execute(operation, arguments, authorize=authorize))
        if operation.startswith('hosts.'):
            if self.hosts is None:
                raise InventoryError('configuration_unavailable', 'host routing owner is unavailable')
            return dict(schema_version=1, operation=operation, status='completed',
                        result=self.hosts.execute(operation, arguments, actor=actor, authorize=authorize))
        if operation.startswith('builds.'):
            if self.builds is None:
                raise InventoryError('configuration_unavailable', 'host build owner is unavailable')
            return dict(schema_version=1, operation=operation, status='completed',
                        result=self.builds.execute(operation, arguments))
        if operation in ('accounts.list', 'accounts.resolve', 'configuration.explain'):
            if self.accounts is None:
                raise InventoryError('configuration_unavailable', 'host account owner is unavailable')
            return dict(schema_version=1, operation=operation, status='completed',
                        result=self.accounts.execute(operation, arguments))
        if operation not in ('inventory.list', 'inventory.resolve'):
            raise InventoryError('unsupported_operation', 'operation is unsupported')
        allowed = {'query'} if operation == 'inventory.list' else {'selector', 'expected_target'}
        if not isinstance(arguments, dict) or set(arguments) - allowed:
            raise InventoryError('invalid_argument', 'unsupported operation arguments')
        query = arguments.get('query', '')
        selector = arguments.get('selector')
        if not isinstance(query, str) or len(query) > 1024:
            raise InventoryError('invalid_argument', 'invalid inventory query')
        if operation == 'inventory.resolve' and (not isinstance(selector, str) or not selector or len(selector) > 1024):
            raise InventoryError('invalid_argument', 'selector is required')
        resources = []
        for agent in self.inventory.inspect()['agents']:
            if query and not any(query.casefold() in str(agent.get(key, '')).casefold()
                                 for key in ('managed_agent_id', 'conversation_id', 'namespace', 'profile')):
                continue
            observed = agent['observed_at']
            def state(value):
                return {'value': value, 'observed_at': observed}
            resources.append({
                'id': agent['managed_agent_id'],
                'target': {'host': self.host, 'environment': self.environment,
                           'runtime': agent['runtime'], 'namespace': agent['namespace'],
                           'conversation_id': agent['conversation_id'], 'process': agent['process']},
                'observation': {'observed_at': observed, 'age_seconds': max(0, self.inventory.now() - observed),
                                'freshness': 'stale' if agent['state'] == 'stale' else 'current'},
                'profile': agent['profile'], 'attachments': agent['attachments'],
                'binding_current': agent['binding_current'],
                'state': {'activity': state('unknown'), 'responsiveness': state('unsupported'),
                          'attachment': state('unknown' if agent['state'] == 'stale' else 'attached' if agent['attachments'] else 'unattached'),
                          'control': state('unknown')},
                'grants_operations': False})
        if operation == 'inventory.resolve':
            candidates = [row for row in resources if selector in (
                row['id'], row['target']['conversation_id'], row['profile'])]
            if not candidates:
                raise InventoryError('target_not_found', 'target is absent from managed inventory')
            if len(candidates) != 1:
                raise InventoryError('ambiguous_target', 'selector identifies multiple scoped targets')
            resource = candidates[0]
            expected = arguments.get('expected_target')
            if not resource['binding_current'] or (expected is not None and expected != resource['target']):
                raise InventoryError('stale_target', 'target binding is stale or replaced')
            result = {'resource': resource}
        else:
            result = {'resources': resources}
        return {'schema_version': 1, 'operation': operation, 'status': 'completed',
                'result': result}
