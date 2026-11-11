"""Governor public command discovery and authority boundaries."""
import contextlib
import io
import tempfile
import unittest
from pathlib import Path


class GovernorCommandTests(unittest.TestCase):
    def test_current_session_controls_have_one_cli_and_machine_contract(self):
        from codex_wake.cli import build_parser
        from codex_wake.local_control_service import LocalOperations, contract
        from codex_wake.mcp_server import SPECS
        parser = build_parser()
        operations = LocalOperations(Path('/tmp/unused-governor-schema')).definitions
        for verb in ('status', 'activate', 'extend', 'reset', 'disable', 'resume', 'advisory'):
            arguments = ['governor', verb, '--json']
            if verb == 'activate':
                arguments += ['--token-limit', '100000', '--time-limit-seconds', '1800']
            args = parser.parse_args(arguments)
            self.assertEqual(args.governor_verb, verb)
            operation = 'local.governor.' + verb
            self.assertIn(operation, operations)
            self.assertEqual(contract()['operations'][operation]['cli'], ['governor', verb])
            self.assertIn('wake_governor_' + verb, SPECS)
            from codex_wake.controller_http import TOOLS
            from codex_wake.controller_client import MCP_TOOLS
            self.assertEqual(TOOLS['wake_governor_' + verb][0], 'governor.' + verb)
            self.assertEqual(MCP_TOOLS['governor.' + verb], 'wake_governor_' + verb)
            self.assertNotIn('operator_authorized', operations[operation][2]['properties'])

    def test_machine_arguments_cannot_assert_operator_authority(self):
        from codex_wake.local_control_service import LocalOperations
        from codex_wake.managed_inventory import InventoryError
        operations = LocalOperations(Path('/tmp/unused-governor-schema'))
        with self.assertRaises(InventoryError):
            operations.execute('local.governor.disable', {'operator_authorized': True})

    def test_missing_current_session_is_an_actionable_cli_failure(self):
        from codex_wake.cli import run
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()) as out:
            import os
            from unittest.mock import patch
            with patch.dict(os.environ, {}, clear=True):
                result = run(['--wake-root', directory, 'governor', 'status', '--json'])
            self.assertEqual(result, 2)
            self.assertIn('selector', out.getvalue().lower())

    def test_native_model_cannot_call_governor_without_current_caller_identity(self):
        from codex_wake.mcp_server import CommandRunner
        with tempfile.TemporaryDirectory() as directory:
            result, failed = CommandRunner(wake_root=Path(directory)).call('wake_governor_disable', {})
        self.assertTrue(failed)
        self.assertIn('error', result)

    def test_public_operator_forms_cannot_accept_shell_commands_or_authority_flags(self):
        from codex_wake.local_control_service import LocalOperations
        from codex_wake.managed_inventory import InventoryError
        owner = LocalOperations(Path('/tmp/unused-governor-schema'))
        for verb in ('extend', 'reset', 'disable'):
            with self.subTest(verb=verb), self.assertRaises(InventoryError):
                owner.execute('local.governor.' + verb, {'command': 'anything', 'principal': 'operator'})
