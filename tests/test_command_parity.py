"""Cross-adapter discovery contracts, complementing behavioral owner regressions."""
import unittest


class CommandParityTests(unittest.TestCase):
    def test_published_schemas_and_help_share_migrated_definitions(self):
        from codex_wake.command_contract import public_tools
        from codex_wake.controller_http import TOOLS
        from codex_wake.controller_client import MCP_TOOLS
        from codex_wake.mcp_server import SPECS
        for name, (operation, schema) in public_tools().items():
            with self.subTest(operation=operation):
                self.assertEqual(MCP_TOOLS[operation], name)
                self.assertEqual(TOOLS[name], (operation, schema))
                self.assertIn(name, SPECS)
                native = SPECS[name]
                for key, value in schema['properties'].items():
                    self.assertEqual(native[3][key], value)
                self.assertEqual(set(native[4]) - {'caller_thread_id'}, set(schema['required']))

    def test_coverage_report_declares_local_login_and_deferred_commands(self):
        from codex_wake.command_contract import coverage_report
        from codex_wake.cli import build_parser
        report = coverage_report(build_parser())
        self.assertIn('accounts.login', report['local_only'])
        self.assertIn('after', report['deferred_commands'])
        self.assertIn('accounts.status', report['migrated_operations'])
