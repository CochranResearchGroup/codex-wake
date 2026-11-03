"""Public discovery seams for the first migrated command slice."""
import subprocess
import sys
import unittest


class CommandContractTests(unittest.TestCase):
    def test_login_help_explains_device_flow_and_channel_default(self):
        result = subprocess.run([sys.executable, '-m', 'codex_wake.entrypoint', 'accounts', 'login', '--help'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('one-time device code', result.stdout)
        self.assertIn('default: modded', result.stdout)
        self.assertIn('Examples:', result.stdout)

    def test_daemon_contract_describes_pinned_mutation_not_implicit_replay(self):
        from codex_wake.command_contract import public_tools
        operation, schema = public_tools()['wake_daemons_restart']
        self.assertEqual(operation, 'daemons.restart')
        self.assertEqual(schema['required'], ['account', 'expected_target', '_request'])
        self.assertFalse(schema['additionalProperties'])
        self.assertIn('replacement is refused', schema['properties']['expected_target']['description'])

    def test_generated_reference_can_be_checked_for_staleness(self):
        from pathlib import Path
        result = subprocess.run([sys.executable, 'scripts/generate_command_reference.py', '--check'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        reference = Path('docs/agents/command-reference.md').read_text()
        self.assertIn('## history import', reference)
        self.assertIn('Local human CLI only', reference)


if __name__ == '__main__':
    unittest.main()
