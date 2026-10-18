"""Lifecycle launch scope is configured by the host, never a tool caller."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

from mcp import Client, StdioServerParameters


class LifecycleMCPTests(unittest.IsolatedAsyncioTestCase):
    async def test_spawn_discovery_and_caller_cannot_override_host_launch_scope(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            marker = root / 'called.json'
            cli = root / 'cli'
            cli.write_text(f'#!{sys.executable}\nimport json,sys,pathlib,os\n'
                f'pathlib.Path({str(marker)!r}).write_text(json.dumps(sys.argv[1:]))\n'
                'print(json.dumps({"argv":sys.argv[1:]}))\n')
            cli.chmod(0o700)
            args = ['-m', 'codex_wake.mcp_server', '--cli', str(cli),
                    '--lifecycle-profiles', str(root / 'host-profiles.json'), '--wake-root', str(root / 'journal')]
            parameters = StdioServerParameters(command=sys.executable, args=args,
                env=dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1] / 'src')))
            async with Client(parameters, mode='legacy') as client:
                tools = {t.name: t for t in (await client.list_tools()).tools}
                configuration_help = tools['wake_sessions_configuration'].description
                spawn_help = tools['wake_sessions_spawn'].description
                self.assertIn('resource limits', configuration_help)
                self.assertIn('strict_execution', configuration_help)
                self.assertIn('operator bootstrap', spawn_help)
                self.assertIn('sampled', spawn_help)
                self.assertIn('existing TUI', spawn_help)
                schema = tools['wake_sessions_spawn'].input_schema
                self.assertNotIn('profiles', schema['properties'])
                self.assertNotIn('wake_root', schema['properties'])
                body = dict(profile='worker', intent='worker157', name='worker', task='Report42',
                            expires_at='2030-01-01T00:00:00Z',
                            caller_thread_id='00000000-0000-7000-8000-000000000011')
                invalid = await client.call_tool('wake_sessions_spawn', dict(body, profiles='/caller/override'))
                self.assertTrue(invalid.is_error)
                self.assertFalse(marker.exists())
                result = await client.call_tool('wake_sessions_spawn', body)
                self.assertFalse(result.is_error)
                command = json.loads(result.content[0].text)['argv']
                self.assertEqual(command[:4], ['--wake-root', str(root / 'journal'), 'sessions', 'spawn'])
                self.assertIn(str(root / 'host-profiles.json'), command)
                self.assertNotIn('--app-server', command)

    async def test_refresh_uses_host_scope_and_only_named_resource_checks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            marker = root / 'called.json'
            cli = root / 'cli'
            cli.write_text(f'#!{sys.executable}\nimport json,sys,pathlib\n'
                f'pathlib.Path({str(marker)!r}).write_text(json.dumps(sys.argv[1:]))\n'
                'print(json.dumps({"argv":sys.argv[1:]}))\n')
            cli.chmod(0o700)
            args = ['-m','codex_wake.mcp_server','--cli',str(cli),
                '--lifecycle-profiles',str(root/'host.json'),'--lifecycle-root',str(root/'journal'),
                '--wake-root',str(root/'legacy')]
            parameters = StdioServerParameters(command=sys.executable,args=args,
                env=dict(os.environ,PYTHONPATH=str(Path(__file__).resolve().parents[1]/'src')))
            async with Client(parameters,mode='legacy') as client:
                tools = {t.name:t for t in (await client.list_tools()).tools}
                schema = tools['wake_sessions_refresh'].input_schema
                self.assertNotIn('app_server',schema['properties'])
                self.assertNotIn('tool',schema['properties'])
                body = dict(profile='worker',intent='refresh158',thread_id='00000000-0000-7000-8000-000000000158',
                    checkpoint='checkpoint.json',checkpoint_sha256='a'*64,resources=['skill','mcp'],
                    expires_at='2030-01-01T00:00:00Z',caller_thread_id='00000000-0000-7000-8000-000000000158')
                invalid=await client.call_tool('wake_sessions_refresh',dict(body,tool='arbitrary'))
                self.assertTrue(invalid.is_error)
                self.assertFalse(marker.exists())
                result=await client.call_tool('wake_sessions_refresh',body)
                self.assertFalse(result.is_error)
                command=json.loads(result.content[0].text)['argv']
                self.assertEqual(command[:4],['--wake-root',str(root/'journal'),'sessions','refresh'])
                self.assertIn(str(root/'host.json'),command)
                self.assertNotIn('--app-server',command)
                self.assertEqual(command.count('--resource'),2)
                self.assertIn('--caller-thread-id',command)

                legacy=await client.call_tool('wake_sessions_target',dict(selector='tab 18',caller_thread_id=body['caller_thread_id']))
                self.assertFalse(legacy.is_error)
                legacy_command=json.loads(legacy.content[0].text)['argv']
                self.assertEqual(legacy_command[:2],['--wake-root',str(root/'legacy')])

    async def test_handoff_exposes_checkpoint_and_mode_without_peer_budget_or_probe_overrides(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);marker=root/'called.json';cli=root/'cli'
            cli.write_text(f'#!{sys.executable}\nimport json,sys,pathlib\n'
                f'pathlib.Path({str(marker)!r}).write_text(json.dumps(sys.argv[1:]))\n'
                'print(json.dumps({"argv":sys.argv[1:]}))\n')
            cli.chmod(0o700)
            parameters=StdioServerParameters(command=sys.executable,args=['-m','codex_wake.mcp_server',
                '--cli',str(cli),'--lifecycle-profiles',str(root/'host.json'),'--wake-root',str(root/'journal')],
                env=dict(os.environ,PYTHONPATH=str(Path(__file__).resolve().parents[1]/'src')))
            async with Client(parameters,mode='legacy') as client:
                tools={t.name:t for t in (await client.list_tools()).tools}
                self.assertIn('wake_sessions_handoff',tools)
                body=dict(profile='worker',intent='handoff159',thread_id='00000000-0000-7000-8000-000000000159',
                    checkpoint='checkpoint.json',checkpoint_sha256='a'*64,mode='new-tab',
                    expires_at='2030-01-01T00:00:00Z',caller_thread_id='00000000-0000-7000-8000-000000000159')
                for forbidden in ('profiles','token_cap','script','app_server'):
                    result=await client.call_tool('wake_sessions_handoff',dict(body,**{forbidden:'override'}))
                    self.assertTrue(result.is_error)
                    self.assertFalse(marker.exists())
                result=await client.call_tool('wake_sessions_handoff',body)
                self.assertFalse(result.is_error)
                command=json.loads(result.content[0].text)['argv']
                self.assertEqual(command[:4],['--wake-root',str(root/'journal'),'sessions','handoff'])
                self.assertIn(str(root/'host.json'),command)
                self.assertNotIn('--app-server',command)
                self.assertEqual(command[command.index('--mode')+1],'new-tab')
                self.assertIn('--caller-thread-id',command)
