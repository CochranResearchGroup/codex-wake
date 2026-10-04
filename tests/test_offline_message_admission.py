"""CLI admission must not require a recipient's thread to be loaded."""
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from codex_wake.a2a_bus import BusStore
from codex_wake.a2a_identity import RuntimeIdentity
from codex_wake.cli import main


class OfflineAdmissionTests(unittest.TestCase):
    def send_offline(self, *, enrolled=True, reported_id='recipient', cross_root=False):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo = root / 'repo'; repo.mkdir()
            body = repo / 'request.txt'; body.write_text('Offline request')
            threads = {name: dict(id=name, cwd=str(repo), modelProvider='fixture')
                       for name in ('sender', 'recipient')}
            recipient_repo = repo
            if cross_root:
                recipient_repo = root / 'other-repo'; recipient_repo.mkdir()
                threads['recipient']['cwd'] = str(recipient_repo)

            class Reader:
                server_metadata = dict(codexHome=str(root / 'codex'))
                def __enter__(self): return self
                def __exit__(self, *args): pass
                def read_thread(self, identifier):
                    thread = dict(threads[identifier])
                    if identifier == 'recipient': thread['id'] = reported_id
                    return thread
                def loaded_threads(self): return [threads['sender']]

            reader = Reader()
            bus, operator = BusStore.configure(root / 'bus')
            bus.enroll(repo, operator, notify=True)
            if cross_root: bus.enroll(recipient_repo, operator, notify=True)
            capabilities = {}
            for name in threads:
                if name == 'recipient' and not enrolled: continue
                identity = RuntimeIdentity.from_metadata(threads[name], reader.server_metadata)
                capabilities[name], _ = bus.issue_actor(identity, Path(identity.cwd), operator)
            from codex_wake.a2a_mailbox import Mailbox
            Mailbox.migrate(bus, operator)

            with patch.dict('os.environ', {'CODEX_THREAD_ID': 'sender'}), \
                    patch('codex_wake.a2a_cli.Path.cwd', return_value=repo), \
                    patch('codex_wake.a2a_cli.SharedAppServerReader', return_value=reader), \
                    patch('codex_wake.sessions.SharedAppServerReader', return_value=reader), \
                    patch('codex_wake.sessions.tmux_inventory', return_value=[]), \
                    patch('sys.stdout', new_callable=io.StringIO) as output:
                code = main(['messages', 'send', '--to', 'thread:recipient',
                             '--app-server', 'unix:///fixture/socket',
                             '--bus-root', str(bus.root), '--capability', str(capabilities['sender']),
                             '--body-file', str(body), '--idempotency-key', 'offline-request',
                             '--ttl', '120s', '--delivery', 'notify', '--json'])
            response = json.loads(output.getvalue())
            return code, response

    def test_enrolled_offline_recipient_accepts_notify_request_without_resume(self):
        code, response = self.send_offline()
        self.assertEqual(code, 0, response)
        self.assertEqual(response['message']['recipient']['thread_id'], 'recipient')
        self.assertEqual(response['message']['state']['notification'], 'pending')
        self.assertEqual(response['message']['state']['recipient'], 'unread')

    def test_unenrolled_offline_recipient_is_denied(self):
        code, response = self.send_offline(enrolled=False)
        self.assertNotEqual(code, 0)
        self.assertEqual(response['error']['code'], 'authorization_denied')

    def test_different_returned_thread_cannot_retarget_send(self):
        code, response = self.send_offline(reported_id='other')
        self.assertNotEqual(code, 0)
        self.assertEqual(response['error']['code'], 'identity_unavailable')

    def test_offline_resolution_does_not_bypass_cross_root_policy(self):
        code, response = self.send_offline(cross_root=True)
        self.assertNotEqual(code, 0)
        self.assertEqual(response['error']['code'], 'cross_root_denied')
