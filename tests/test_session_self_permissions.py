"""Native self access without UUID enrollment, preserving effect authority (#310)."""
import hashlib
import os
import subprocess
import sys
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from codex_wake.mcp_server import CommandRunner
from codex_wake.records import WakeError

THREAD = '00000000-0000-7000-8000-000000000310'
PEER = '00000000-0000-7000-8000-000000000311'


def native_context(thread=THREAD):
    return {'threadId': thread, 'sessionId': thread, 'callId': 'call-310',
            'x-codex-turn-metadata': {'thread_id': thread, 'session_id': thread,
                                    'turn_id': 'turn-310'}}


class SessionSelfPermissionsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.policy = self.root / 'profiles.json'
        self.config = {'version': 1, 'callers': {}, 'profiles': {
            'self-refresh': {'refresh_mode': 'shared_mcp_idle',
                'scope_approval': 'operator approved shared reload after idle',
                'cwd': self.temp.name, 'app_server': 'unix:///missing.sock',
                'codex_path': '/bin/true', 'timeout': 1,
                'resources': {'wake': {'kind': 'skill', 'path': '/missing',
                                       'description': 'Wake', 'sha256': 'a' * 64}}}}}
        self.runner = CommandRunner(lifecycle_profiles=self.policy,
                                    lifecycle_root=self.root / 'state')

    def write_policy(self):
        self.policy.write_text(json.dumps(self.config))
        self.policy.chmod(0o600)

    def configure(self, *, context=None, target=THREAD, caller=THREAD):
        self.write_policy()
        return self.runner.call('wake_sessions_configuration',
            {'profile': 'self-refresh', 'thread_id': target, 'caller_thread_id': caller},
            native_context=context)

    def test_new_native_caller_can_inspect_its_approved_refresh_profile(self):
        value, failed = self.configure(context=native_context())
        self.assertFalse(failed, value)
        self.assertEqual(value['thread_id'], THREAD)
        self.assertEqual(value['refresh_scope'], 'shared_server_mcp')
        self.assertEqual(json.loads(self.policy.read_text())['callers'], {})
        self.assertFalse((self.root / 'state' / 'objective-ledgers').exists())

    def test_single_client_profile_has_the_same_self_default(self):
        self.config['profiles']['self-refresh']['refresh_mode'] = 'client_idle'
        value, failed = self.configure(context=native_context())
        self.assertFalse(failed, value)
        self.assertEqual(value['refresh_scope'], 'single_client')

    def test_claim_alone_does_not_get_the_default(self):
        value, failed = self.configure()
        self.assertTrue(failed, value)

    def test_other_session_or_conflicting_native_identity_is_denied(self):
        for caller, target, context in [
            (THREAD, PEER, native_context()),
            (PEER, PEER, native_context()),
            (THREAD, THREAD, native_context(PEER)),
            (THREAD, THREAD, {}),
        ]:
            with self.subTest(caller=caller, target=target, context=context):
                value, failed = self.configure(context=context, target=target, caller=caller)
                self.assertTrue(failed, value)
        context = native_context()
        context['x-codex-turn-metadata']['session_id'] = PEER
        self.assertTrue(self.configure(context=context)[1])

    def test_explicit_denials_and_default_off_override_self_access(self):
        for caller_entries, defaults in [
            ({THREAD: []}, {}), ({THREAD: ['different-profile']}, {}),
            ({}, {'self_access': False}),
        ]:
            self.config['callers'] = caller_entries
            self.config['session_permissions'] = defaults
            value, failed = self.configure(context=native_context())
            self.assertTrue(failed, value)

    def test_explicit_grant_overrides_default_off(self):
        self.config['callers'] = {THREAD: ['self-refresh']}
        self.config['session_permissions'] = {'self_access': False}
        value, failed = self.configure(context=native_context())
        self.assertFalse(failed, value)

    def test_malformed_default_or_caller_policy_fails_closed(self):
        for defaults in [None, [], {'self_access': 'true'}, {'unknown': True}]:
            self.config['session_permissions'] = defaults
            self.assertTrue(self.configure(context=native_context())[1])
        self.config.pop('session_permissions')
        for callers in [None, [], {THREAD: 'self-refresh'}, {THREAD: None}]:
            self.config['callers'] = callers
            self.assertTrue(self.configure(context=native_context())[1])

    def test_default_never_supplies_effect_scope_approval(self):
        self.config['profiles']['self-refresh']['scope_approval'] = ''
        self.assertTrue(self.configure(context=native_context())[1])

    def test_private_native_refresh_queues_without_mutating_host_grants(self):
        self.write_policy()
        checkpoint = self.root / 'checkpoint.json'
        checkpoint.write_text(json.dumps(dict(source_thread_id=THREAD,
            objective='Refresh current resources', authority='user requested refresh',
            next_packet='verify refresh result', pending_obligations=[])))
        arguments = dict(profile='self-refresh', thread_id=THREAD, caller_thread_id=THREAD,
            intent='own-refresh-310', checkpoint='checkpoint.json',
            checkpoint_sha256=hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
            resources=['wake'], expires_at='2030-01-01T00:00:00Z')
        from codex_wake.session_permissions import native_request
        packet = dict(verb='refresh', arguments=arguments, profiles=str(self.policy),
            root=str(self.root / 'state'), binding=dict(thread_id=THREAD, turn_id='turn-310', call_id='call-310'))
        with patch('codex_wake.goal_supervision._heartbeat', return_value={'fresh': True}), \
             patch('codex_wake.lifecycle_budget.trusted_upper', return_value=time.time()):
            previous_umask = os.umask(0o022)
            try:
                value, failed = native_request(packet)
            finally:
                os.umask(previous_umask)
            self.assertEqual((self.root / "state").stat().st_mode & 0o777, 0o700)
            self.assertFalse(failed, value)
            self.assertEqual(value['state'], 'queued')
            self.assertNotIn('native_self_access', value)
            first = value['fingerprint']
            again, failed = native_request(packet)
            self.assertFalse(failed, again)
            self.assertEqual(again['fingerprint'], first)
        receipts = list((self.root / 'state' / 'shared-refresh').glob('*.json'))
        self.assertEqual(len(receipts), 1)
        saved = json.loads(receipts[0].read_text())
        self.assertTrue(saved['native_self_access'])
        self.config['callers'][THREAD] = []
        self.write_policy()
        from codex_wake.shared_refresh import poll
        with patch('codex_wake.shared_refresh._request') as request:
            poll(self.root / 'state')
            request.assert_not_called()
        revoked = json.loads(receipts[0].read_text())
        self.assertEqual(revoked['state'], 'blocked')
        self.assertEqual(json.loads(self.policy.read_text())['callers'], {THREAD: []})
        self.assertFalse((self.root / 'state' / 'objective-ledgers').exists())

    @unittest.skipIf(os.name == 'nt', 'owned flock/FIFO regression is POSIX-only')
    def test_native_refresh_obeys_timeout_when_emergency_lock_is_held(self):
        import fcntl
        self.write_policy()
        checkpoint = self.root / 'checkpoint.json'
        checkpoint.write_text(json.dumps(dict(source_thread_id=THREAD,
            objective='Refresh', authority='user', next_packet='verify', pending_obligations=[])))
        (self.root / 'state').mkdir(mode=0o700)
        lockdir = self.root / 'state' / 'emergency-control'
        lockdir.mkdir(parents=True, mode=0o700)
        lockfile = lockdir / 'effects.lock'
        lockfile.touch(mode=0o600)
        with lockfile.open('r+') as held:
            fcntl.flock(held, fcntl.LOCK_EX)
            self._assert_bounded_refresh(checkpoint)

    @unittest.skipIf(os.name == 'nt', 'owned FIFO regression is POSIX-only')
    def test_native_refresh_obeys_timeout_for_blocking_checkpoint(self):
        self.write_policy()
        checkpoint = self.root / 'checkpoint.json'
        os.mkfifo(checkpoint, 0o600)
        self._assert_bounded_refresh(checkpoint)

    def _assert_bounded_refresh(self, checkpoint):
        script = """
import json,sys,time
from pathlib import Path
from codex_wake.mcp_server import CommandRunner
from test_session_self_permissions import THREAD,native_context
root=Path(sys.argv[1]);start=time.monotonic()
value,failed=CommandRunner(lifecycle_profiles=root/'profiles.json',lifecycle_root=root/'state',call_timeout=.15).call(
 'wake_sessions_refresh',dict(profile='self-refresh',thread_id=THREAD,caller_thread_id=THREAD,
 intent='bounded-310',checkpoint='checkpoint.json',checkpoint_sha256='a'*64,resources=['wake'],
 expires_at='2030-01-01T00:00:00Z'),native_context=native_context())
assert failed and value['error']['code']=='effect_uncertain',value
assert time.monotonic()-start<1.5
print('bounded')
"""
        # The regular checkpoint must reach the held lock; a FIFO must block on read.
        if checkpoint.is_file():
            digest = hashlib.sha256(checkpoint.read_bytes()).hexdigest()
            script = script.replace("checkpoint_sha256='a'*64", 'checkpoint_sha256=' + repr(digest))
        env = dict(os.environ, PYTHONPATH=os.pathsep.join([
            str(Path(__file__).resolve().parents[1] / 'src'), str(Path(__file__).resolve().parent)]))
        try:
            result = subprocess.run([sys.executable, '-c', script, str(self.root)],
                env=env, text=True, capture_output=True, timeout=2)
        except subprocess.TimeoutExpired:
            self.fail('native refresh bypassed the MCP timeout')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), 'bounded')
