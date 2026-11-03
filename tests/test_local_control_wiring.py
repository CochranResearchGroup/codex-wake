"""Public command routing must survive nested native command arguments."""
import unittest
from codex_wake.cli import build_parser
from codex_wake.mcp_server import SPECS


class LocalControlWiringTests(unittest.TestCase):
    def test_slash_action_keeps_outer_control_route(self):
        args=build_parser().parse_args(['control','slash','run','thread:one','/rename','--arguments','new name','--idempotency-key','rename-one'])
        self.assertEqual(args.command,'control')
        self.assertEqual(args.control_verb,'slash')
        self.assertEqual(args.slash_command,'/rename')
        self.assertEqual(args.arguments,'new name')

    def test_local_native_tools_are_discoverable_without_manual_policy(self):
        for name in ['wake_local_prompt','wake_local_output','wake_local_health','wake_self_limits_show','wake_self_limits_set','wake_control_slash_run']:
            self.assertIn(name,SPECS)
