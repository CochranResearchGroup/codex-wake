"""Native clock reader's process contract: no configured authority means hold."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class NativeQueueClockTests(unittest.TestCase):
    def test_missing_stable_time_configuration_holds_without_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [sys.executable, '-m', 'codex_wake.native_queue_clock',
                 '--config', str(Path(directory)/'absent.json')],
                capture_output=True, text=True, timeout=10,
                env=dict(os.environ, PYTHONPATH='src'))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {
            'contract_version': 1, 'state': 'held', 'reason': 'stable_time_unavailable'})
        self.assertEqual(result.stderr, '')
