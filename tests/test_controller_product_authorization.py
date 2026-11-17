"""New target pins must be grantable; stale observation authority must fail closed."""
import base64
from dataclasses import replace
import hashlib
from pathlib import Path
import tempfile
import unittest

from codex_wake.controller_auth import Actor, AuthError, OAuthAuthority
from unittest.mock import patch

UTC=1800000000
from codex_wake.daemon_commands import execute


class ProductAuthorizationTests(unittest.TestCase):
    def setUp(self):
        clock=patch('codex_wake.measurements.utc_bounds',return_value=(UTC,UTC+1))
        clock.start();self.addCleanup(clock.stop)

    def test_remote_actor_clock_loss_and_ambiguous_expiry_refuse_before_private_io(self):
        from codex_wake.measurements import TimeUnavailable
        from codex_wake.profile_operations import execute as profile_execute
        target=dict(host='fixture',environment='test',account='alice',home='/fixture/alice',home_generation='1:2')
        actor=Actor('operator','owner','client','grant','https://fixture','wake:controller',frozenset({'observe','account.observe'}),[target],200)
        class Owner:
            calls=[]
            def execute(self,operation,arguments):
                self.calls.append(operation)
                return {'stores':[]} if operation=='stores.list' else {'daemon':{'target':target}}
        for route in ('profile','daemon'):
            owner=Owner();owner.calls=[]
            def call():
                if route=='profile':return profile_execute('/unused','stores.list',{},accounts=owner,actor=actor,authorize=lambda:actor)
                return execute('/unused','daemons.status',{},owner=owner,actor=actor,authorize=lambda:actor)
            with self.subTest(route=route), patch('codex_wake.measurements.utc_bounds',return_value=(198,199)):
                self.assertEqual(call()['status'],'completed')
            for bounds,code in (((199,200),'insufficient_scope'),(TimeUnavailable('private-clock'),'qualified_time_unavailable')):
                owner.calls=[]
                with self.subTest(route=route,code=code), patch('codex_wake.measurements.utc_bounds',return_value=bounds if isinstance(bounds,tuple) else None,side_effect=bounds if isinstance(bounds,Exception) else None):
                    with self.assertRaises(AuthError) as held:call()
                    self.assertEqual(held.exception.code,code)
                    self.assertEqual(owner.calls,[])
                    self.assertNotIn('private-clock',str(held.exception))

    def test_local_status_and_stop_remain_separate_from_explicit_actor_read_guard(self):
        from codex_wake.measurements import TimeUnavailable
        from codex_wake.controller_runtime import ControllerRuntime
        target=dict(host='fixture',environment='test',account='alice',home='/fixture/alice',home_generation='1:2',build_sha256='a'*64,process=None,socket_generation=None)
        actor=Actor('operator','owner','local-fixture','local-fixture','local://fixture','wake:controller',frozenset({'control','observe'}),[target],UTC+120)
        class Owner:
            calls=[]
            def execute(self,operation,arguments):
                self.calls.append(operation)
                return {'daemon':{'target':target}}
        with tempfile.TemporaryDirectory() as directory:
            runtime=ControllerRuntime(directory,now=lambda:UTC)
            owner=Owner()
            request=dict(operation_id='stop',idempotency_key='stop',correlation_id='stop',binding='local-cli',target=target)
            with patch('codex_wake.measurements.utc_bounds',side_effect=TimeUnavailable('missing')), patch('codex_wake.daemon_commands.local_operator',return_value=actor), patch('codex_wake.controller_runtime.ControllerRuntime',return_value=runtime):
                self.assertEqual(execute(directory,'daemons.status',{},owner=owner)['status'],'completed')
                result=execute(directory,'daemons.stop',dict(expected_target=target,confirm=True,_request=request),owner=owner)
            self.assertEqual(result['status'],'completed')
            self.assertIn('daemons.stop',owner.calls)

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
        actor = Actor('fixture','owner','client','grant','local://fixture','wake:controller',frozenset({'observe'}),[target],UTC+120)
        class Unreachable:
            def execute(self, *unused):
                raise AssertionError('unauthorized native state opened')
        def revoked():
            raise AuthError()
        for selected, authorize in ((actor, revoked), (replace(actor, expires_at=UTC-1), lambda: actor)):
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
