"""Goal-limit tools retain the host's scope across the public stdio seam."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

from mcp import Client, StdioServerParameters


class GoalLimitsMCPTests(unittest.IsolatedAsyncioTestCase):
    async def test_limits_are_discoverable_and_caller_cannot_select_host_scope(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            marker = root / 'called.json'
            cli = root / 'cli'
            cli.write_text(f'#!{sys.executable}\nimport json,sys,pathlib,os\n'
                f'pathlib.Path({str(marker)!r}).write_text(json.dumps(sys.argv[1:]))\n'
                'print(json.dumps({"argv":sys.argv[1:],"caller":os.environ.get("CODEX_THREAD_ID")}))\n')
            cli.chmod(0o700)
            parameters = StdioServerParameters(command=sys.executable,
                args=['-m', 'codex_wake.mcp_server', '--cli', str(cli),
                      '--goal-limits-policy', str(root / 'host.json'),
                      '--wake-root', str(root / 'legacy'), '--goal-limits-root', str(root / 'journal')],
                env=dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1] / 'src')))
            async with Client(parameters, mode='legacy') as client:
                tools = {t.name: t for t in (await client.list_tools()).tools}
                tool = tools['wake_goal_limits_set']
                for phrase in ('resource limits', 'checkpoint', 'pause', 'cached', 'reset'):
                    self.assertIn(phrase, tool.description)
                caller = '00000000-0000-7000-8000-000000000279'
                body = dict(caller_thread_id=caller, token_limit=1000000, time_limit_seconds=14400)
                for key in ('policy', 'wake_root', 'app_server', 'thread_id', 'reset'):
                    denied = await client.call_tool('wake_goal_limits_set', dict(body, **{key: 'override'}))
                    self.assertTrue(denied.is_error)
                    self.assertFalse(marker.exists())
                result = await client.call_tool('wake_goal_limits_set', body)
                self.assertFalse(result.is_error)
                output = json.loads(result.content[0].text)
                command = output['argv']
                self.assertEqual(command[:4], ['--wake-root', str(root / 'journal'), 'goal-limits', 'set'])
                self.assertEqual(command[command.index('--policy') + 1], str(root / 'host.json'))
                self.assertEqual(command[command.index('--caller-thread-id') + 1], caller)
                self.assertEqual(output['caller'], caller)
                legacy = await client.call_tool('wake_sessions_target', {'caller_thread_id': caller, 'selector': 'tab 18'})
                self.assertFalse(legacy.is_error)
                self.assertEqual(json.loads(legacy.content[0].text)['argv'][:4], ['--wake-root', str(root / 'legacy'), 'sessions', 'target'])
                shown = await client.call_tool('wake_goal_limits_show', {'caller_thread_id': caller})
                self.assertFalse(shown.is_error)
                self.assertEqual(json.loads(shown.content[0].text)['argv'][2:4], ['goal-limits', 'show'])

    async def test_fractional_checkpoint_reserve_reaches_host_admission_without_a_grant(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            policy = root / 'host.json'
            policy.write_text(json.dumps(dict(version=1, callers={})))
            policy.chmod(0o600)
            parameters = StdioServerParameters(command=sys.executable,
                args=['-m', 'codex_wake.mcp_server', '--goal-limits-policy', str(policy),
                      '--goal-limits-root', str(root / 'journal')],
                env=dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1] / 'src')))
            async with Client(parameters, mode='legacy') as client:
                result = await client.call_tool('wake_goal_limits_set', dict(
                    caller_thread_id='00000000-0000-7000-8000-000000000279',
                    token_limit=2000000, time_limit_seconds=21600,
                    checkpoint_token_percent=17.5, checkpoint_seconds=900))
                self.assertTrue(result.is_error)
                output = json.loads(result.content[0].text)
                self.assertEqual(output['error']['code'], 'goal_limits_unavailable', output)
                self.assertEqual(output['error']['message'], 'host caller grant unavailable or malformed')
                self.assertEqual(output['state'], 'held')
                self.assertEqual(output['reason'], 'caller_grant_missing')
                self.assertFalse(output['effect_attempted'])
                self.assertEqual(output['operator_interaction'], 'available')
                self.assertIn('host', output['next_action'])
                self.assertIn('caller_identity', output['missing_evidence'])
                self.assertFalse(list((root / 'journal').rglob('*.json')))


if __name__ == '__main__':
    unittest.main()
