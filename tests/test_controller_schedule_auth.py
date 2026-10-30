import base64
import hashlib
import tempfile
import unittest
from pathlib import Path

from codex_wake.controller_auth import OAuthAuthority, AuthError
from codex_wake.controller_runtime import identity


class ScheduledAuthorityTests(unittest.TestCase):
    def test_original_policy_authority_survives_rotation_but_never_extends_expiry_or_revocation(self):
        with tempfile.TemporaryDirectory() as directory:
            clock=[100]
            auth=OAuthAuthority(Path(directory)/'auth.sqlite',issuer='https://wake.test',resource='https://wake.test/controller',now=lambda:clock[0])
            client=auth.register(dict(redirect_uris=['http://127.0.0.1:45000/callback']))
            verifier='s'*43
            challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
            code=auth.authorize(subject='service',principal_kind='service',client_id=client['client_id'],redirect_uri=client['redirect_uris'][0],
                resource=auth.resource,scopes=['observe','recovery'],targets=[dict(host='fixture',environment='linux')],code_challenge=challenge)
            token=auth.token(dict(grant_type='authorization_code',client_id=client['client_id'],redirect_uri=client['redirect_uris'][0],code=code,code_verifier=verifier,resource=auth.resource))
            actor=auth.authenticate(token['access_token']);principal=identity(actor)
            snapshot=dict(scopes=sorted(actor.scopes),targets=actor.targets,expires_at=actor.expires_at,principal_kind=actor.principal_kind)
            self.assertEqual(auth.revalidate_original(principal,snapshot),actor)
            clock[0]=101
            auth.token(dict(grant_type='refresh_token',refresh_token=token['refresh_token'],client_id=client['client_id'],resource=auth.resource))
            self.assertEqual(auth.revalidate_original(principal,snapshot).expires_at,700)
            with self.assertRaises(AuthError):auth.revalidate_original(dict(principal,subject='another'),snapshot)
            with self.assertRaises(AuthError):auth.revalidate_original(principal,dict(snapshot,scopes=['observe','recovery','control']))
            clock[0]=700
            with self.assertRaises(AuthError):auth.revalidate_original(principal,snapshot)
            clock[0]=102
            auth.revoke_grant(actor.grant_id)
            with self.assertRaises(AuthError):auth.revalidate_original(principal,snapshot)

    def test_corrupt_owner_database_publishes_held_status_on_repeated_scheduled_checks(self):
        import sqlite3
        import time
        from codex_wake.controller_auth import Actor
        from codex_wake.controller_recovery import ControllerRecovery
        from codex_wake.controller_schedule import maintain
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            owner=ControllerRecovery(root)
            target=dict(host='fixture',environment='linux',runtime='codex',namespace='one',build_sha256='a'*64,
                conversation_id='thread',home='/fixture/home',provider='fixture',backend_id='daemon',channel='tui',
                connection_generation='one',process_pid='123',process_start_ticks='456',process_boot_id='boot')
            actor=Actor('service','service','client','grant','https://wake.test','https://wake.test/controller',
                frozenset({'observe','recovery'}),[target],time.time()+60)
            database=root/'controller-operations'/'operations.sqlite'
            original=database.read_bytes()
            try:
                for unused in range(2):
                    database.write_bytes(b'corrupt SQLite owner store')
                    try:
                        maintain(None,root)
                    except sqlite3.DatabaseError:
                        pass  # Inspect the public status even when the scheduler failed.
                    database.write_bytes(original)
                    result=owner.execute(actor,'recovery.list',dict(expected_target=target),authorize=lambda:actor)
                    self.assertEqual(result['result']['scheduler']['status'],'held')
                    self.assertEqual(result['result']['scheduler']['reason'],'scheduler_owner_unavailable')
                    self.assertEqual(result['result']['policies'],[])
            finally:
                database.write_bytes(original)

    def test_existing_controller_server_drives_enabled_policy_without_a_client_tick(self):
        import threading
        import time
        from unittest.mock import patch
        from codex_wake.controller_http import ControllerHTTPServer
        from codex_wake.controller_operations import ControllerOperations
        from codex_wake.controller_recovery import ControllerRecovery
        from codex_wake.managed_inventory import ManagedInventory
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            target=dict(host='fixture',environment='linux',runtime='codex',namespace='one',build_sha256='a'*64,
                conversation_id='thread',home='/fixture/home',provider='fixture',backend_id='daemon',channel='tui',
                connection_generation='one',process_pid='123',process_start_ticks='456',process_boot_id='boot')
            auth=OAuthAuthority(root/'auth.sqlite',issuer='https://wake.test',resource='https://wake.test/controller')
            client=auth.register(dict(redirect_uris=['http://127.0.0.1:45000/callback']))
            verifier='s'*43;challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
            code=auth.authorize(subject='service',principal_kind='service',client_id=client['client_id'],redirect_uri=client['redirect_uris'][0],
                resource=auth.resource,scopes=['observe','recovery'],targets=[target],code_challenge=challenge)
            token=auth.token(dict(grant_type='authorization_code',client_id=client['client_id'],redirect_uri=client['redirect_uris'][0],code=code,code_verifier=verifier,resource=auth.resource))
            actor=auth.authenticate(token['access_token'])
            def notice(actor,source,target,guard):
                guard();return dict(operation_id='notice-'+source,phase='terminal',delivery=dict(status='recorded'))
            owner=ControllerRecovery(root,notice=notice)
            def args(name,**extra):return dict(policy_id='policy',expected_target=target,
                _request=dict(operation_id=name,idempotency_key=name,correlation_id=name,binding='fixture',target=target),**extra)
            policy=dict(interval_seconds=1,probe_timeout=.05,unknown_threshold=32,cooldown_seconds=1,max_attempts=1,
                evidence='suspected_unresponsive',actions=[dict(kind='notify_operator')])
            owner.execute(actor,'recovery.configure',args('configure',policy=policy),authorize=lambda:actor)
            owner.execute(actor,'recovery.enable',args('enable'),authorize=lambda:actor)
            def read():return owner.execute(actor,'recovery.show',dict(policy_id='policy',expected_target=target),authorize=lambda:actor)['result']['policy']
            def probe(unused,operation,arguments):
                return dict(target=arguments['expected_target'],observation=dict(status='unknown',responsive=False,evidence='none',observed_at=time.time()),grants_recovery=False,application_effects=False)
            server=ControllerHTTPServer(('127.0.0.1',0),auth,ControllerOperations(ManagedInventory(root),host='fixture',environment='linux'))
            worker=threading.Thread(target=server.serve_forever,kwargs=dict(poll_interval=.05),daemon=True)
            try:
                with patch('codex_wake.controller_health.ControllerHealth.execute',probe):
                    worker.start();deadline=time.monotonic()+4
                    while time.monotonic()<deadline and read()['checks']==0:time.sleep(.05)
                    self.assertGreater(read()['checks'],0,'enabled controller never scheduled its due observation')
                    auth.revoke_grant(actor.grant_id)
                    deadline=time.monotonic()+3
                    while time.monotonic()<deadline and read().get('scheduler_status')!='authority_unavailable':time.sleep(.05)
                    self.assertEqual(read()['scheduler_status'],'authority_unavailable')
                    held=read()['checks'];time.sleep(.2);self.assertEqual(read()['checks'],held)
            finally:
                server.shutdown();server.server_close();worker.join(timeout=2)
