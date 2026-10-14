"""MCP dispatch uses the real CLI with injected inventory at its provider seam."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

from codex_wake.mcp_server import CommandRunner, SPECS


class TabTargetMCPTests(unittest.TestCase):
    def test_mcp_accepts_human_descriptor_and_returns_canonical_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            entry=Path(tmp)/'cli'
            entry.write_text(f'#!{sys.executable}\n'+'''
from unittest.mock import patch
from codex_wake.cli import main
from tests.test_sessions import pane,snapshot
s=snapshot(panes=[pane('18','policies')])
with patch('codex_wake.tab_targets.observe',return_value=s):
    raise SystemExit(main())
''')
            entry.chmod(0o700)
            runner=CommandRunner(cli=str(entry))
            for descriptor in ('tab 18','18:policies','poicys'):
                value,failed=runner.call('wake_sessions_target',dict(selector=descriptor,
                    caller_thread_id='00000000-0000-7000-8000-000000000011'))
                self.assertFalse(failed,value)
                self.assertEqual(value['status'],'resolved')
                self.assertEqual(value['session']['thread_id'],'full-thread-id')
            self.assertNotIn('profiles',SPECS['wake_sessions_target'][3])
            value,failed=runner.call('wake_sessions_target',dict(selector='18',profiles='/override',
                    caller_thread_id='00000000-0000-7000-8000-000000000011'))
            self.assertTrue(failed)
            self.assertEqual(value['error']['code'],'invalid_argument')
