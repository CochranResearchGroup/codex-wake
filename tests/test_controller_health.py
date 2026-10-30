import hashlib
import json
import os
from pathlib import Path
import tempfile
import time
import unittest


class HealthTests(unittest.TestCase):
    def fixture(self,directory,request):
        from codex_wake.controller_health import ControllerHealth
        from codex_wake.process import process_identity
        root=Path(directory);binding=dict(host='fixture',environment='linux',runtime='codex',namespace='fixture-account',conversation_id='11111111-1111-4111-8111-111111111111',home=str(root),provider='fixture',backend_id='backend',channel='native_tui',process=dict(pid=os.getpid(),start_ticks=process_identity(os.getpid())['start_time_ticks'],boot_id=process_identity(os.getpid())['boot_id']),connection_generation='connection-one')
        executable=Path('/proc/self/exe').resolve();binding['build_sha256']=hashlib.sha256(executable.read_bytes()).hexdigest()
        config=dict(version=1,bindings=[dict(target=binding,codex_cmd=[str(executable)],endpoint='unix:///synthetic/daemon.sock')])
        path=root/'controller-health.json';path.write_text(json.dumps(config));path.chmod(0o600)
        return ControllerHealth(root,request=request),binding

    def test_metadata_or_background_reply_cannot_qualify_positive_health(self):
        def background(*args):return dict(state='responsive',evidence='daemon_metadata',challenge=args[3]['challenge'])
        with tempfile.TemporaryDirectory() as directory:
            service,target=self.fixture(directory,background)
            result=service.execute('health.observe',dict(expected_target=target,timeout=.2))
            self.assertEqual(result['observation']['status'],'unknown')
            self.assertFalse(result['observation']['responsive'])
            self.assertFalse(result['grants_recovery'])

    def test_wrong_target_expiry_and_unsupported_remain_nonpositive(self):
        def unsupported(*args):
            from codex_wake.native_protocol import NativeCapabilityUnavailable
            raise NativeCapabilityUnavailable('unknown method')
        with tempfile.TemporaryDirectory() as directory:
            service,target=self.fixture(directory,unsupported)
            self.assertEqual(service.execute('health.observe',dict(expected_target=target,timeout=.2))['observation']['status'],'unsupported')
            changed=dict(target,connection_generation='replacement')
            self.assertEqual(service.execute('health.observe',dict(expected_target=changed,timeout=.2))['observation']['status'],'unknown')
    def test_expired_and_wrong_challenge_cannot_become_positive(self):
        def expired(*args):
            time.sleep(.08)
            return dict(state='responsive',evidence='tui_main_loop_ack',challenge=args[3]['challenge'])
        with tempfile.TemporaryDirectory() as directory:
            service,target=self.fixture(directory,expired)
            result=service.execute('health.observe',dict(expected_target=target,timeout=.05))
            self.assertFalse(result['observation']['responsive'])
            self.assertEqual(result['observation']['reason'],'challenge_deadline')
            changed=dict(target,process=dict(target['process'],start_ticks='0'))
            # Pinned binding matching alone never validates a reused process identity.
            path=Path(directory)/'controller-health.json'
            body=json.loads(path.read_text());body['bindings'][0]['target']=changed;path.write_text(json.dumps(body))
            self.assertEqual(service.execute('health.observe',dict(expected_target=changed))['observation']['reason'],'stale_process_generation')

    def test_existing_endpoint_only_never_discovers_or_starts_server(self):
        calls=[]
        with tempfile.TemporaryDirectory() as directory:
            service,target=self.fixture(directory,lambda *args:calls.append(args))
            path=Path(directory)/'controller-health.json';body=json.loads(path.read_text());body['bindings'][0]['endpoint']='unix://';path.write_text(json.dumps(body))
            result=service.execute('health.observe',dict(expected_target=target))
            self.assertEqual(result['observation']['status'],'unsupported')
            self.assertEqual(calls,[])
