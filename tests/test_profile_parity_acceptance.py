"""Acceptance script must not substitute source code for an absent installation."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class InstalledParityAcceptanceTests(unittest.TestCase):
    def test_missing_installed_entrypoints_fail_without_source_fallback(self):
        script = Path(__file__).resolve().parents[1] / 'scripts/profile_transport_parity_acceptance.py'
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            receipt = root / 'receipt.json'
            result = subprocess.run([sys.executable, str(script), '--installed-prefix', str(root),
                                     '--receipt', str(receipt)], capture_output=True, text=True,
                                    env=dict(os.environ, PYTHONPATH=str(script.parents[1] / 'src')))
            self.assertNotEqual(result.returncode, 0)
            self.assertTrue(receipt.exists(), result.stderr)
            report = json.loads(receipt.read_text())
            self.assertEqual(report['execution_mode'], 'installed')
            self.assertEqual(report['state'], 'failed')
            self.assertIn('installed acceptance requires', report['error'])
            self.assertFalse(report.get('cli', False))
