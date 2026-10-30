import tempfile
import unittest
from pathlib import Path

from codex_wake.managed_inventory import ManagedInventory, Observation


class ControllerOperationTests(unittest.TestCase):
    def test_inventory_reports_scoped_identity_without_inventing_health(self):
        from codex_wake.controller_operations import ControllerOperations
        with tempfile.TemporaryDirectory() as directory:
            store = ManagedInventory(Path(directory) / 'wake', now=lambda: 100)
            enrolled = store.enroll(Observation(
                'codex', 'account:alice', 'conversation-one', '/fixture', 'ready', 100,
                'native_metadata', {'pid': 123, 'start_ticks': 42, 'boot_id': 'boot-one'},
                [{'pane_id': '%1', 'window_name': 'work'}], {}, profile='alice'), operator=True)
            service = ControllerOperations(store, host='host-one', environment='wsl:test')
            result = service.execute('inventory.list', {'query': 'conversation-one'})
            self.assertEqual(result['schema_version'], 1)
            row = result['result']['resources'][0]
            self.assertEqual(row['id'], enrolled['agent']['managed_agent_id'])
            self.assertEqual(row['target']['namespace'], 'account:alice')
            self.assertEqual(row['target']['host'], 'host-one')
            self.assertEqual(row['state']['responsiveness']['value'], 'unsupported')
            self.assertEqual(row['state']['activity']['value'], 'unknown')
            self.assertFalse(row['grants_operations'])

    def test_pinned_target_refuses_process_replacement_instead_of_retargeting(self):
        from codex_wake.controller_operations import ControllerOperations
        from codex_wake.managed_inventory import InventoryError
        with tempfile.TemporaryDirectory() as directory:
            store = ManagedInventory(Path(directory) / 'wake', now=lambda: 100)
            sample = Observation('codex', 'account:alice', 'one', '/fixture', 'ready', 100,
                'native_metadata', {'pid': 123, 'start_ticks': 42, 'boot_id': 'boot-one'}, [], {})
            identifier = store.enroll(sample, operator=True)['agent']['managed_agent_id']
            service = ControllerOperations(store, host='host-one', environment='wsl:test')
            original = service.execute('inventory.resolve', {'selector': 'one'})['result']['resource']
            from dataclasses import replace
            store.reconcile(identifier, replace(sample, process={'pid': 123, 'start_ticks': 99, 'boot_id': 'boot-one'}))
            with self.assertRaises(InventoryError) as error:
                service.execute('inventory.resolve', {'selector': identifier, 'expected_target': original['target']})
            self.assertEqual(error.exception.code, 'stale_target')

    def test_cli_and_mcp_use_same_read_only_operation_contract(self):
        import contextlib
        import io
        import json
        from codex_wake.cli import main
        from codex_wake.mcp_server import CommandRunner
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'wake'
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = main(['--wake-root', str(root), 'controller', 'list', '--json'])
            self.assertEqual(code, 0)
            cli = json.loads(output.getvalue())
            mcp, failed = CommandRunner(wake_root=root).call('wake_controller_list', {})
            self.assertFalse(failed)
            self.assertEqual(cli, mcp)
            self.assertEqual(cli['result']['resources'], [])

    def test_ambiguous_native_ids_and_stale_observations_are_not_resolved(self):
        from codex_wake.controller_operations import ControllerOperations
        from codex_wake.managed_inventory import InventoryError
        with tempfile.TemporaryDirectory() as directory:
            clock = [100]
            store = ManagedInventory(Path(directory) / 'wake', now=lambda: clock[0])
            ids = []
            for account in ('alice', 'bob'):
                sample = Observation('codex', 'account:' + account, 'shared-native-id', '/fixture', 'ready', 100,
                    'native_metadata', {'pid': 123, 'start_ticks': 42, 'boot_id': 'boot-one'}, [], {})
                ids.append(store.enroll(sample, operator=True)['agent']['managed_agent_id'])
            service = ControllerOperations(store, host='host-one', environment='wsl:test')
            with self.assertRaises(InventoryError) as error:
                service.execute('inventory.resolve', {'selector': 'shared-native-id'})
            self.assertEqual(error.exception.code, 'ambiguous_target')
            clock[0] = 131
            row = service.execute('inventory.list', {})['result']['resources'][0]
            self.assertEqual(row['observation']['freshness'], 'stale')
            with self.assertRaises(InventoryError) as error:
                service.execute('inventory.resolve', {'selector': ids[0]})
            self.assertEqual(error.exception.code, 'stale_target')
