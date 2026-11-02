"""New target pins must be grantable; stale observation authority must fail closed."""
import base64
from dataclasses import replace
import hashlib
from pathlib import Path
import tempfile
import time
import unittest

from codex_wake.controller_auth import AuthError, OAuthAuthority
from codex_wake.daemon_commands import execute, local_operator


class ProductAuthorizationTests(unittest.TestCase):
    def test_oauth_can_issue_exact_registry_and_native_generation_grants(self):
        with tempfile.TemporaryDirectory() as tmp:
            authority = OAuthAuthority(Path(tmp) / 'auth.sqlite', issuer='http://localhost:1234', resource='http://localhost:1234/controller')
            client = authority.register({'redirect_uris': ['http://localhost:1234/callback']})
            verifier = 'x' * 43
            challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
            base = dict(host='test', environment='linux')
            registry = dict(base, registry='/tmp/test/controller-accounts.toml', registry_revision='absent')
            daemon = dict(base, account='codex-alice', home='/tmp/alice', home_generation='1:2', build_sha256='a'*64,
                          process=dict(pid=123, start_ticks='456', boot_id='00000000-0000-4000-8000-000000000000'), socket_generation='1:3')
            for target in (registry, daemon, dict(daemon, process=None, socket_generation=None)):
                code = authority.authorize(subject='test', principal_kind='owner', client_id=client['client_id'],
                    redirect_uri=client['redirect_uris'][0], resource=authority.resource, scopes=['admin','control','observe'],
                    targets=[target], code_challenge=challenge)
                tokens = authority.token(dict(grant_type='authorization_code', client_id=client['client_id'],
                    redirect_uri=client['redirect_uris'][0], resource=authority.resource, code=code, code_verifier=verifier))
                self.assertEqual(authority.authenticate(tokens['access_token']).targets, [target])
            with self.assertRaises(AuthError):
                authority.authorize(subject='test', principal_kind='owner', client_id=client['client_id'],
                    redirect_uri=client['redirect_uris'][0], resource=authority.resource, scopes=['control'],
                    targets=[dict(daemon, process={'command': 'arbitrary'})], code_challenge=challenge)

    def test_revoked_or_expired_daemon_observation_never_opens_native_state(self):
        target = dict(host='test', environment='linux', account='alice', home='/tmp/alice', home_generation='1:2')
        actor = local_operator(target)
        class Unreachable:
            def execute(self, *unused):
                raise AssertionError('unauthorized native state opened')
        def revoked():
            raise AuthError()
        for selected, authorize in ((actor, revoked), (replace(actor, expires_at=time.time()-1), lambda: actor)):
            with self.assertRaises(AuthError):
                execute('/tmp/unused', 'daemons.status', {'account':'alice'}, actor=selected, authorize=authorize, owner=Unreachable())

    def test_actual_http_and_oauth_mcp_create_accounts_through_one_registry(self):
        import json
        import threading
        from urllib.request import Request, urlopen
        from codex_wake.controller_accounts import ControllerAccounts
        from codex_wake.controller_http import ControllerHTTPServer
        from codex_wake.controller_operations import ControllerOperations
        from codex_wake.managed_inventory import ManagedInventory
        from codex_wake.account_management import registry_target
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            authority = OAuthAuthority(root/'auth.sqlite', issuer='http://localhost:1234', resource='http://localhost:1234/controller')
            accounts = ControllerAccounts(root/'controller-accounts.toml',host='test',environment='linux')
            operations = ControllerOperations(ManagedInventory(root),host='test',environment='linux')
            server = ControllerHTTPServer(('127.0.0.1',0),authority,operations)
            worker = threading.Thread(target=server.serve_forever,daemon=True);worker.start()
            client = authority.register({'redirect_uris':['http://localhost:1234/callback']})
            verifier = 'x'*43
            challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
            def token(target):
                code = authority.authorize(subject='owner',principal_kind='owner',client_id=client['client_id'],
                    redirect_uri=client['redirect_uris'][0],resource=authority.resource,scopes=['admin'],targets=[target],code_challenge=challenge)
                return authority.token(dict(grant_type='authorization_code',code=code,code_verifier=verifier,resource=authority.resource,
                    client_id=client['client_id'],redirect_uri=client['redirect_uris'][0]))['access_token']
            def post(path,body,bearer):
                with urlopen(Request('http://127.0.0.1:'+str(server.server_port)+path,data=json.dumps(body).encode(),
                    headers={'Authorization':'Bearer '+bearer,'Content-Type':'application/json'}),timeout=5) as response:
                    return json.load(response)
            def arguments(key,target,**values):
                return dict(values,_request=dict(operation_id=key,idempotency_key=key,correlation_id=key,binding='test',target=target))
            try:
                target=registry_target(accounts)
                init=post('/operations',dict(operation='accounts.init',arguments=arguments('init',target)),token(target))
                self.assertEqual(init['result']['operation']['execution'],'completed')
                target=registry_target(accounts);bearer=token(target);create=arguments('create-alice',target,selector='alice',alias='work')
                body=dict(jsonrpc='2.0',id=1,method='tools/call',params=dict(name='wake_controller_account_create',arguments=create))
                first=post('/mcp',body,bearer)['result']['structuredContent']['result']['operation']
                self.assertEqual(first['execution'],'completed')
                repeat=post('/operations',dict(operation='accounts.create',arguments=create),bearer)['result']['operation']
                self.assertEqual(repeat,first)
                self.assertEqual(accounts.execute('accounts.resolve',{'selector':'work'})['account']['id'],'codex-alice')
            finally:
                server.shutdown();server.server_close();worker.join(timeout=5)
