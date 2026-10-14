"""Effective lifecycle policy through the public CLI/MCP, without native effects."""
from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest

from codex_wake.cli import run
from codex_wake.mcp_server import CommandRunner


class LifecycleConfigurationTests(unittest.TestCase):
    def test_objective_override_selects_actual_instructions_before_admission(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            writer = root / 'writer.md'
            reviewer = root / 'reviewer.md'
            alternate = root / 'alternate.md'
            writer.write_text('Write an evidence checkpoint.')
            reviewer.write_text('Route the substantive review.')
            alternate.write_text('Review local evidence without GitHub.')
            profiles = root / 'profiles.json'
            profiles.write_text(json.dumps(dict(
                profiles={'worker': {'cwd': tmp}},
                lifecycle_defaults=dict(
                    handoff_writer={'name': 'writer', 'path': str(writer)},
                    preflight_reviewer={'name': 'router', 'path': str(reviewer)},
                    session_token_limit=100, session_time_limit_seconds=60,
                    objective_token_limit=500, objective_time_limit_seconds=300,
                    max_correction_cycles=2),
                continuations={'source': dict(objective='Finish the feature',
                    approval='operator', started_at='2030-01-01T00:00:00Z',
                    configuration={'preflight_reviewer': {'name': 'local-review', 'path': str(alternate)}})})))
            output = StringIO()
            with redirect_stdout(output):
                code = run(['sessions', 'configuration', '--profiles', str(profiles),
                            '--profile', 'worker', '--thread-id', 'source', '--json'])
            self.assertEqual(code, 0)
            effective = json.loads(output.getvalue())
            self.assertEqual(effective['preflight_reviewer']['name'], 'local-review')
            self.assertEqual(effective['preflight_reviewer']['instructions'],
                             'Review local evidence without GitHub.')
            self.assertEqual(effective['handoff_writer']['instructions'], 'Write an evidence checkpoint.')
            self.assertEqual(effective['objective_deadline'], '2030-01-01T00:05:00+00:00')
            self.assertEqual(effective['session_token_limit'], 100)
            self.assertEqual(len(effective['revision']), 64)
            runner = CommandRunner(lifecycle_profiles=profiles, wake_root=root / 'wake')
            value, failed = runner.call('wake_sessions_configuration', dict(profile='worker',
                thread_id='source', caller_thread_id='00000000-0000-7000-8000-000000000159'))
            self.assertTrue(failed)
            self.assertIn('unavailable', value['error']['message'])
            config = json.loads(profiles.read_text())
            caller = '00000000-0000-7000-8000-000000000159'
            config['continuations'][caller] = config['continuations'].pop('source')
            config['callers'] = {caller: ['worker']}
            profiles.write_text(json.dumps(config))
            value, failed = runner.call('wake_sessions_configuration', dict(profile='worker',
                thread_id=caller, caller_thread_id=caller))
            self.assertFalse(failed, value)
            self.assertEqual(value['preflight_reviewer']['instructions'], 'Review local evidence without GitHub.')
            alternate.unlink()
            value, failed = runner.call('wake_sessions_configuration', dict(profile='worker',
                thread_id=caller, caller_thread_id=caller))
            self.assertTrue(failed)
            self.assertEqual(value['error']['code'], 'configuration_unavailable')
            self.assertNotIn('preflight_reviewer', value)
