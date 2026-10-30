import base64
import hashlib
import unittest

import tests.test_controller_migration as fixture_module


class MigrationAuthorizationTests(unittest.TestCase):
    setUp = fixture_module.ControllerMigrationTests.setUp
    owner = fixture_module.ControllerMigrationTests.owner

    def grant(self, authority, scopes, target):
        client = authority.register({'redirect_uris': ['http://localhost/callback']})
        verifier = 'x' * 43
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
        code = authority.authorize(subject='migration-operator', principal_kind='service', client_id=client['client_id'],
            redirect_uri=client['redirect_uris'][0], resource=authority.resource, scopes=scopes,
            targets=[target], code_challenge=challenge)
        return authority.token(dict(grant_type='authorization_code', client_id=client['client_id'],
            code=code, redirect_uri=client['redirect_uris'][0], code_verifier=verifier, resource=authority.resource))['access_token']

    def request(self, target, label, **arguments):
        return dict(arguments, expected_target=target, _request=dict(operation_id=label, idempotency_key=label,
            correlation_id='correlation-' + label, binding='fixture-operator', target=target))

    def test_same_stable_grant_previews_applies_replays_and_rolls_back(self):
        from codex_wake.controller_auth import OAuthAuthority
        from codex_wake.controller_runtime import ControllerRuntime
        from codex_wake.controller_migration_authorization import MigrationAuthorization
        authority = OAuthAuthority(self.root / 'oauth.sqlite', issuer='https://wake.fixture', resource='https://wake.fixture/mcp')
        owner = self.owner()
        # No plan revision in the reusable stable scope grant.
        token = self.grant(authority, ['migration.observe', 'admin'], owner.scope_target())
        service = MigrationAuthorization(authority, owner, runtime=ControllerRuntime(self.root / 'wake'))
        preview = service.execute(token, 'migration.preview', {})
        args = self.request(preview['result']['target'], 'apply')
        applied = service.execute(token, 'migration.apply', args)
        record = applied['result']['operation']
        self.assertEqual(record['execution'], 'completed')
        result = record['result']
        self.assertEqual(result['status'], 'applied')
        replay = service.execute(token, 'migration.apply', args)
        self.assertEqual(replay['result']['operation']['operation_id'], 'apply')
        rollback = service.execute(token, 'migration.rollback', self.request(result['target'], 'rollback', receipt_id=result['receipt_id']))
        self.assertEqual(rollback['result']['operation']['result']['status'], 'rolled_back')
        self.assertEqual(self.pointer.resolve(), self.legacy)

    def test_readonly_and_wrong_scope_grants_cannot_admit_mutation(self):
        from codex_wake.controller_auth import OAuthAuthority, AuthError
        from codex_wake.controller_runtime import ControllerRuntime
        from codex_wake.controller_migration_authorization import MigrationAuthorization
        authority = OAuthAuthority(self.root / 'oauth.sqlite', issuer='https://wake.fixture', resource='https://wake.fixture/mcp')
        owner = self.owner()
        preview = owner.execute('migration.preview', {})
        args = self.request(preview['target'], 'denied')
        for scopes, target in ((['migration.observe'], owner.scope_target()),
                               (['admin'], dict(owner.scope_target(), migration_id='other-scope'))):
            token = self.grant(authority, scopes, target)
            with self.assertRaises(AuthError):
                MigrationAuthorization(authority, owner, runtime=ControllerRuntime(self.root / 'wake')).execute(token, 'migration.apply', args)
        self.assertFalse((self.lab / 'candidate').exists())
        self.assertEqual(self.pointer.resolve(), self.legacy)

    def test_revocation_during_evidence_probe_blocks_the_next_filesystem_step(self):
        from codex_wake.controller_auth import OAuthAuthority, AuthError
        from codex_wake.controller_runtime import ControllerRuntime
        from codex_wake.controller_migration_authorization import MigrationAuthorization
        authority = OAuthAuthority(self.root / 'oauth.sqlite', issuer='https://wake.fixture', resource='https://wake.fixture/mcp')
        owner = self.owner()
        token = self.grant(authority, ['migration.observe', 'admin'], owner.scope_target())
        grant = authority.authenticate(token).grant_id
        def probe(unused):
            if self.home.is_symlink():
                authority.revoke_grant(grant)
            return dict(status='complete', writers=[])
        owner.writer_probe = probe
        service = MigrationAuthorization(authority, owner, runtime=ControllerRuntime(self.root / 'wake'))
        target = service.execute(token, 'migration.preview', {})['result']['target']
        with self.assertRaises(AuthError):
            service.execute(token, 'migration.apply', self.request(target, 'revoked'))
        self.assertEqual(self.pointer.resolve(), self.legacy)
        self.assertFalse((self.lab / 'candidate' / 'controller-accounts.toml').exists())

    def test_lost_qualification_after_partial_effect_is_durable_unknown_and_never_replayed(self):
        from codex_wake.controller_auth import OAuthAuthority
        from codex_wake.controller_runtime import ControllerRuntime
        from codex_wake.controller_migration_authorization import MigrationAuthorization
        authority = OAuthAuthority(self.root / 'oauth.sqlite', issuer='https://wake.fixture', resource='https://wake.fixture/mcp')
        owner = self.owner(writer_probe=lambda unused: dict(status='unknown' if self.home.is_symlink() else 'complete', writers=[]))
        token = self.grant(authority, ['migration.observe', 'admin'], owner.scope_target())
        service = MigrationAuthorization(authority, owner, runtime=ControllerRuntime(self.root / 'wake'))
        target = service.execute(token, 'migration.preview', {})['result']['target']
        args = self.request(target, 'uncertain')
        first = service.execute(token, 'migration.apply', args)['result']['operation']
        self.assertEqual(first['execution'], 'unknown')
        self.assertEqual(first['phase'], 'uncertain')
        self.assertEqual(first['reason'], 'uncertain_effect')
        self.assertEqual(service.execute(token, 'migration.apply', args)['result']['operation']['operation_id'], 'uncertain')
        self.assertEqual(self.pointer.resolve(), self.legacy)
        self.assertTrue(self.home.is_symlink())
        self.assertFalse((self.lab / 'candidate' / 'controller-accounts.toml').exists())
