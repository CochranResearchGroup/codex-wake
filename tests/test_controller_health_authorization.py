import json
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from codex_wake.controller_auth import Actor, AuthError


class HealthAuthorizationTests(unittest.TestCase):
    def test_full_process_grant_observes_unknown_and_broad_grant_is_denied(self):
        from codex_wake.controller_http import ProtectedOperations
        from codex_wake.controller_operations import ControllerOperations
        from codex_wake.managed_inventory import ManagedInventory
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / 'controller-health.json'
            path.write_text(json.dumps(dict(version=1,bindings=[])));path.chmod(0o600)
            target = dict(host='host',environment='test',runtime='codex',namespace='native',build_sha256='fixture',
                conversation_id='thread',home='/fixture/home',provider='fixture',backend_id='backend',channel='modded',
                connection_generation='one',process=dict(pid=123,start_ticks='42',boot_id='boot'))
            grant = {key:value for key,value in target.items() if key != 'process'}
            grant.update(process_pid='123',process_start_ticks='42',process_boot_id='boot')
            actor = Actor('reader','service','client','grant','local://test','wake:controller',
                frozenset({'observe'}),[grant],time.time()+600)
            authority = SimpleNamespace(authenticate=lambda unused: actor)
            protected = ProtectedOperations(authority,ControllerOperations(ManagedInventory(root),host='host',environment='test'))
            value = protected.execute('token','health.observe',dict(expected_target=target))
            self.assertEqual(value['result']['observation']['status'],'unknown')
            self.assertFalse(value['result']['grants_recovery'])
            actor = Actor('reader','service','client','grant','local://test','wake:controller',
                frozenset({'observe'}),[{'host':'host'}],time.time()+600)
            with self.assertRaises(AuthError):
                protected.execute('token','health.observe',dict(expected_target=target))
