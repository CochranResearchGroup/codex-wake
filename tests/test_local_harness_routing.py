"""Shared public routes preserve explicit harness and retained operation custody."""
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import Mock,patch

from codex_wake.cli import build_parser
from codex_wake.local_control_service import LocalOperations


class LocalHarnessRoutingTests(unittest.TestCase):
    def test_shared_cli_and_machine_contract_select_grok_explicitly(self):
        args=build_parser().parse_args(['control','resolve','grok:session-one','--harness','grok','--profile','owned'])
        self.assertEqual((args.harness,args.profile),('grok','owned'))
        for verb in ('list','resolve','create','prompt','health','slash.list','slash.run'):
            schema=LocalOperations(Path('/tmp/unused-routing-schema')).definitions['local.'+verb][2]
            self.assertEqual(schema['properties']['harness']['enum'],['codex','grok'])
            self.assertIn('profile',schema['properties'])
        from codex_wake.mcp_server import SPECS
        for tool in ('wake_local_create','wake_local_prompt','wake_local_health','wake_control_slash_run'):
            self.assertEqual(SPECS[tool][3]['harness']['enum'],['codex','grok'])
            self.assertIn('profile',SPECS[tool][3])

    def test_public_resolve_uses_explicit_grok_owner_and_preserves_target_pin(self):
        grok=Mock();grok.resolve.return_value={'thread_id':'session-one','target':{'runtime':'grok'}}
        module=types.SimpleNamespace(LocalGrokControl=Mock(return_value=grok))
        with tempfile.TemporaryDirectory() as directory,patch.dict('sys.modules',{'codex_wake.local_grok_control':module}):
            value=LocalOperations(Path(directory)).execute('local.resolve',dict(selector='grok:session-one',harness='grok',profile='owned',expected_target={'runtime':'grok'}))
        self.assertEqual(value['target']['runtime'],'grok')
        grok.resolve.assert_called_once_with('grok:session-one',{'runtime':'grok'},profile='owned')

    def test_retained_grok_result_routes_from_journal_without_fresh_profile(self):
        grok=Mock();grok.result.return_value={'status':'completed','result':{'operation':{'operation_id':'opaque-id'}}}
        module=types.SimpleNamespace(LocalGrokControl=Mock(return_value=grok))
        with tempfile.TemporaryDirectory() as directory,patch.dict('sys.modules',{'codex_wake.local_grok_control':module}),patch('codex_wake.controller_runtime.ControllerRuntime._load',return_value={'operation':'grok.prompt','target':{'runtime':'grok'}}):
            value=LocalOperations(Path(directory)).execute('local.result',dict(operation_id='opaque-id'))
        self.assertEqual(value['result']['operation']['operation_id'],'opaque-id')
        grok.result.assert_called_once_with('opaque-id',0)
