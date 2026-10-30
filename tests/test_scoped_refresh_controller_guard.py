import tempfile
import unittest
from pathlib import Path

from codex_wake.controller_auth import AuthError
from codex_wake.scoped_refresh import poll_one


class ScopedRefreshControllerGuardTests(unittest.TestCase):
    def test_revoked_policy_cannot_read_or_reload_original_native_thread(self):
        with tempfile.TemporaryDirectory() as directory:
            def guard(): raise AuthError()
            def request(*unused): self.fail('revoked refresh reached native endpoint')
            for state in ('queued','reloading','verifying','uncertain'):
                with self.subTest(state=state), self.assertRaises(AuthError):
                    poll_one(Path(directory)/'receipt.json',dict(thread_id='original',state=state),
                        request=request,guard=guard)

    def test_resource_readback_uses_same_original_guarded_native_transport(self):
        with tempfile.TemporaryDirectory() as directory:
            calls=[]
            def request(method,params):
                calls.append(method)
                if method=='thread/goal/get':return dict(goal=None)
                self.assertEqual(method,'thread/read')
                return dict(thread=dict(id='original',cwd=directory))
            receipt=dict(thread_id='original',state='verifying',goal_before=None,
                profile=dict(cwd=directory),resources=[])
            poll_one(Path(directory)/'receipt.json',receipt,request=request,guard=lambda:None)
            self.assertEqual(receipt['state'],'completed')
            self.assertEqual(calls,['thread/goal/get','thread/read'])
