"""Public goal-limit commands fail closed when host setup is missing."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class GoalLimitsCLITests(unittest.TestCase):
    def test_missing_host_policy_is_a_structured_refusal(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run([sys.executable, '-m', 'codex_wake',
                '--wake-root', str(Path(tmp) / 'journal'), 'goal-limits', 'set',
                '--policy', str(Path(tmp) / 'missing.json'),
                '--caller-thread-id', '00000000-0000-7000-8000-000000000279',
                '--token-limit', '1000000', '--time-limit-seconds', '14400', '--json'],
                env=dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1] / 'src')),
                capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(json.loads(result.stdout)['error']['code'], 'goal_limits_unavailable')
            self.assertNotIn('Traceback', result.stderr)
