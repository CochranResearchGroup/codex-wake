import base64
import hashlib
import unittest

import tests.test_controller_history as history_fixture
THREAD = history_fixture.THREAD


class HistoryAuthorizationTests(unittest.TestCase):
    setUp = history_fixture.ControllerHistoryTests.setUp
    def grant(self, authority, scopes, targets, subject='reader'):
        client = authority.register({'redirect_uris': ['http://localhost/callback']})
        verifier = 'x' * 43
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
        code = authority.authorize(subject=subject, principal_kind='service', client_id=client['client_id'],
            redirect_uri=client['redirect_uris'][0], resource=authority.resource, scopes=scopes,
            targets=targets, code_challenge=challenge)
        return authority.token(dict(grant_type='authorization_code', client_id=client['client_id'],
            code=code, redirect_uri=client['redirect_uris'][0], code_verifier=verifier, resource=authority.resource))['access_token']

    def test_exact_current_account_grant_is_admitted_before_native_history_access(self):
        from codex_wake.controller_auth import OAuthAuthority, AuthError
        from codex_wake.controller_history_authorization import HistoryAuthorization
        from codex_wake.controller_accounts import ControllerAccounts
        authority = OAuthAuthority(self.root / 'auth.sqlite', issuer='https://wake.test', resource='https://wake.test/mcp')
        account = ControllerAccounts(self.path, host='local', environment='test').execute('accounts.resolve', {'selector': 'alice'})['account']['target']
        token = self.grant(authority, ['history.observe'], [account])
        service = HistoryAuthorization(authority, self.root, host='local', environment='test')
        result = service.execute(token, 'history.search', {})
        self.assertEqual([row['owner'] for row in result['result']['sessions']], ['codex-alice'])
        # A disallowed owner's unusable database cannot change this to a schema error.
        (self.root / 'homes' / 'codex-bob' / 'state_5.sqlite').write_bytes(b'invalid')
        with self.assertRaises(AuthError) as error:
            service.execute(token, 'history.read', {'owner': 'bob', 'thread_id': THREAD})
        self.assertEqual(error.exception.code, 'insufficient_scope')
        weak = self.grant(authority, ['observe'], [account])
        with self.assertRaises(AuthError):
            service.execute(weak, 'history.search', {})
        authority.revoke_grant(authority.authenticate(token).grant_id)
        with self.assertRaises(AuthError):
            service.execute(token, 'history.search', {})

    def test_resume_requires_independent_host_delegation_and_rechecks_oauth_before_effect(self):
        import shutil
        import sqlite3
        from codex_wake.a2a_identity import RuntimeIdentity
        from codex_wake.controller_accounts import ControllerAccounts
        from codex_wake.controller_auth import OAuthAuthority, AuthError
        from codex_wake.controller_history_authorization import HistoryAuthorization
        from codex_wake.session_permissions import PermissionStore, Principal
        from tests.test_agent_resume_protocol import ResumeProtocolTests
        fixture = ResumeProtocolTests(methodName='test_mcp_real_protocol_launch_and_reconstructed_owner_exact_identity')
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        fixture.metadata['codexHome'] = str(self.root / 'homes' / 'codex-alice')
        fixture.namespace = RuntimeIdentity.from_metadata(fixture.thread, fixture.metadata).namespace
        agent = fixture.inv.enroll(fixture.sample(True), operator=True)['agent']
        fixture.config['profiles']['saved']['codex_home'] = fixture.metadata['codexHome']
        fixture.config['recovery_callers'] = {'reader': [agent['managed_agent_id']]}
        fixture.save_profiles()
        with sqlite3.connect(self.root / 'homes' / 'codex-alice' / 'state_5.sqlite') as db:
            db.execute('update threads set cwd=?', (str(fixture.base),))
        shutil.copytree(fixture.root, self.root, dirs_exist_ok=True)
        self.path.write_text(self.path.read_text().replace('readable_accounts=["alice","bob"]',
            'readable_accounts=["alice","bob"]\nresume_enabled=true') + f'''\n[history.bindings."{THREAD}"]
account="codex-alice"
managed_agent_id="{agent['managed_agent_id']}"
profile="saved"
profiles="{fixture.profiles}"
''')
        authority = OAuthAuthority(self.root / 'auth.sqlite', issuer='https://wake.test', resource='https://wake.test/mcp')
        target = ControllerAccounts(self.path, host='local', environment='test').execute('accounts.resolve', {'selector': 'alice'})['account']['target']
        token = self.grant(authority, ['history.observe', 'history.resume'], [target])
        service = HistoryAuthorization(authority, self.root, host='local', environment='test',
            runtime=fixture.runtime, now=lambda: fixture.inv.now())
        session = service.execute(token, 'history.search', {'owners': ['alice']})['result']['sessions'][0]
        arguments = dict(owner='alice', thread_id=THREAD, expected_target=session['target'],
                         intent='remote-owned', expires_at='2027-01-16T09:00:00+00:00')
        with self.assertRaises(AuthError):
            service.execute(token, 'history.resume', arguments)
        self.assertFalse(fixture.commands)
        store = PermissionStore(self.root)
        policy = {'version': 1, 'global': {'actions': {'resume.recover': 'allow'}},
                  'delegations': {'reader': {'actions': ['resume.recover'], 'sessions': [THREAD]}}}
        store.configure(policy, Principal('operator', 'operator'), expected_revision=store._read()['revision'])
        success = service.execute(token, 'history.resume', arguments)
        self.assertEqual(success['result']['resume']['status'], 'resumed')
        self.assertEqual(success['actor']['subject'], 'reader')
        fixture.current = False
        original_terminal = fixture.runtime.terminal
        grant_id = authority.authenticate(token).grant_id
        def revoked_terminal(args, *command):
            if command[0] == 'new-window':
                authority.revoke_grant(grant_id)
            return original_terminal(args, *command)
        fixture.runtime.terminal = revoked_terminal
        with self.assertRaises(AuthError):
            service.execute(token, 'history.resume', dict(arguments, intent='revoked-before-effect'))
        self.assertEqual(len([command for command in fixture.commands if command[0] == 'new-window']), 1)
