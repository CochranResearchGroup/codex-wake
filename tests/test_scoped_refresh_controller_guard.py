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
