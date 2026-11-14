"""Private bearer boundary: credentials never enter public readiness results."""
import json
import os
from pathlib import Path
import tempfile
import unittest

from codex_wake.grok_provider_auth import GrokSession


class GrokSessionTest(unittest.TestCase):
    def test_native_session_status_is_sanitized_and_bearer_requires_qualified_time(self):
        with tempfile.TemporaryDirectory() as directory:
            auth = Path(directory) / 'auth.json'
            auth.write_text(json.dumps({'https://accounts.x.ai/sign-in': {
                'key': 'private-session-secret', 'auth_mode': 'web_login',
                'user_id': 'account-one', 'expires_at': '2030-01-01T00:00:00Z'}}))
            os.chmod(auth, 0o600)
            session = GrokSession(auth)
            status = session.status()
            self.assertEqual(status['authentication'], 'present')
            self.assertEqual(status['inference'], 'unverified')
            self.assertNotIn('private-session-secret', json.dumps(status))
            with self.assertRaisesRegex(ValueError, 'qualified_time_required'):
                session.bearer(None)
            self.assertEqual(session.bearer(1800000000), 'private-session-secret')

    def test_private_bearer_holds_expired_and_ambiguous_sessions(self):
        with tempfile.TemporaryDirectory() as directory:
            auth = Path(directory) / 'auth.json'
            value = {'key': 'private-secret', 'auth_mode': 'oidc',
                     'expires_at': '2020-01-01T00:00:00Z'}
            auth.write_text(json.dumps({'https://auth.x.ai': value}))
            os.chmod(auth, 0o600)
            session = GrokSession(auth)
            with self.assertRaisesRegex(ValueError, 'native_refresh_required'):
                session.bearer(1800000000)
            auth.write_text(json.dumps({'https://auth.x.ai': value, 'other': value}))
            with self.assertRaisesRegex(ValueError, 'missing_or_ambiguous'):
                session.bearer(1800000000)
