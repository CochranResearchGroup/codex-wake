"""The spoke bridge must hold an original envelope without an owning binding."""
from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


@unittest.skipUnless(os.name == 'posix' and Path('/proc/self').is_dir(), 'requires Linux')
class LinuxNetworkRecipientTests(unittest.TestCase):
    def test_missing_binding_holds_exact_input_without_claiming_effect(self):
        from codex_wake.wake_network_native import main

        request = dict(identifier='3406b6bc-c22a-4abc-b99e-bdd366541555', source='direct', scope='peer:fixture',
                       recipient='8eb45f30-a5db-4d51-b604-0f5b4afa66cf', expires_at_micros=2_000_000_000_000_000,
                       payload='fixture')
        stdin = io.TextIOWrapper(io.BytesIO(json.dumps(request).encode()))
        out = io.StringIO()
        with tempfile.TemporaryDirectory() as directory, patch('sys.stdin', stdin), redirect_stdout(out):
            result = main(['--binding', str(Path(directory)/'missing.json'), 'deliver'])
        self.assertEqual(result, 0)
        self.assertEqual(json.loads(out.getvalue()), dict(id=request['identifier'], recipient=request['recipient'],
            expires_at_micros=request['expires_at_micros'], status='unsent', reason='offline'))
