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

    def test_registration_pins_account_identity_across_native_rotation(self):
        from codex_wake.grok_provider_auth import GrokAccounts
        with tempfile.TemporaryDirectory() as directory:
            auth = Path(directory) / 'auth.json'
            value = {'key': 'first-secret', 'auth_mode': 'oidc', 'user_id': 'one',
                     'expires_at': '2030-01-01T00:00:00Z'}
            auth.write_text(json.dumps({'https://auth.x.ai': value}))
            os.chmod(auth, 0o600)
            accounts = GrokAccounts(Path(directory) / 'wake')
            accounts.register('personal', 'Personal Grok', auth)
            self.assertEqual(accounts.status('personal')['authentication'], 'present')
            value.update(key='rotated-secret', user_id='two')
            auth.write_text(json.dumps({'https://auth.x.ai': value}))
            self.assertEqual(accounts.status('personal')['authentication'], 'account_changed')
            with self.assertRaisesRegex(ValueError, 'account_changed'):
                accounts.bearer('personal', 1800000000)

    def test_login_never_relays_native_errors_or_treats_exit_zero_as_sign_in(self):
        from codex_wake.grok_provider_auth import login
        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / 'grok'
            executable.write_text('#!/bin/sh\necho private-provider-secret >&2\nexit 0\n')
            executable.chmod(0o700)
            events = []
            result = login(executable, Path(directory) / 'auth.json', emit=events.append)
            self.assertEqual(result['authentication'], 'logged_out')
            self.assertNotIn('private-provider-secret', json.dumps(events + [result]))
