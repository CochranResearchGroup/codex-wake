"""Shared MCP must resolve a separate host-owned mailbox actor for each caller."""
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from codex_wake.a2a_bus import BusStore
from codex_wake.a2a_identity import RuntimeIdentity
from codex_wake.cli import main
from codex_wake.mcp_server import CommandRunner


class NativeMailboxBootstrapTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.project = self.root / 'project'; self.project.mkdir()
        self.bus, self.operator = BusStore.configure(self.root / 'bus')
        self.bus.enroll(self.project, self.operator)
        from codex_wake.a2a_mailbox import Mailbox
        Mailbox.migrate(self.bus,self.operator)
        self.ids = ['00000000-0000-7000-8000-000000000011',
                    '00000000-0000-7000-8000-000000000012']
        self.identities = {t: RuntimeIdentity('fixture-runtime', t, str(self.project)) for t in self.ids}
        self.runner = CommandRunner(bus_root=self.bus.root, app_server='fixture://',
                                   mailbox_operator_capability=self.operator)

    def context(self, thread):
        return dict(threadId=thread, sessionId=thread, callId='fixture-call',
                    **{'x-codex-turn-metadata': dict(thread_id=thread,session_id=thread,turn_id='fixture-turn')})

    def execute_cli(self, command, arguments, readonly, body=None, *, cwd=None):
        # Real CLI/store/authentication; only native runtime discovery is injected.
        actor_thread = arguments['caller_thread_id']
        identity = self.identities[actor_thread]
        class Reader:
            server_metadata = {}
            def __init__(s,*a,**k): pass
            def __enter__(s): return s
            def __exit__(s,*a): pass
            def read_thread(s, thread): return {'identity': self.identities[thread]}
        def metadata(thread, server): return thread['identity']
        with patch.dict(os.environ, CODEX_THREAD_ID=actor_thread), \
             patch('pathlib.Path.cwd', return_value=Path(cwd or self.project)), \
             patch('codex_wake.a2a_cli.SharedAppServerReader', Reader), \
             patch.object(RuntimeIdentity, 'from_metadata', side_effect=metadata), \
             patch('codex_wake.messages_cli.resolve_identity', return_value=self.identities[self.ids[1]]), \
             patch('sys.stdin',io.TextIOWrapper(io.BytesIO((body or '').encode()))), \
             patch('sys.stdout',new_callable=io.StringIO) as out:
            # CommandRunner defaults to python -m codex_wake.
            code=main(command[3:])
        return json.loads(out.getvalue()),code != 0

    def call(self, thread, tool='inbox', **arguments):
        from codex_wake.a2a_mailbox import Mailbox
        from functools import partial
        with patch('codex_wake.native_mailbox_bootstrap.resolve_identity',
                   side_effect=lambda t, **k: self.identities[t.removeprefix('thread:')]), \
             patch.object(self.runner,'_execute',side_effect=self.execute_cli), \
             patch('codex_wake.messages_cli.Mailbox',partial(Mailbox,clock=lambda:1_800_000_000.,monotonic=lambda:1_800_000_000.)):
            return self.runner.call('wake_messages_'+tool,
                dict(caller_thread_id=thread,**arguments),self.context(thread))

    def test_two_callers_get_distinct_reused_actors_without_fixed_capability(self):
        for thread in self.ids:
            value,error=self.call(thread)
            self.assertFalse(error,value)
            self.assertTrue(value['success'])
        self.call(self.ids[0])
        with self.bus.connection(read_only=True) as db:
            rows=db.execute('select thread_id,actor_id from actors').fetchall()
        self.assertEqual({r['thread_id'] for r in rows},set(self.ids))
        self.assertEqual(len({r['actor_id'] for r in rows}),2)
        self.assertIsNone(self.runner.capability)

    def test_correlated_question_claim_reply_between_distinct_callers(self):
        sender,recipient=self.ids
        self.assertFalse(self.call(recipient)[1])  # worker registers on first inbox poll
        value,error=self.call(sender,'send',to='thread:'+recipient,body='Fixture question?',
            idempotency_key='question-1',delivery='inbox',kind='request')
        self.assertFalse(error,value)
        message=value['message']['message_id']
        value,error=self.call(recipient,'read',message_id=message)
        self.assertFalse(error,value)
        self.assertEqual(value['body'],'Fixture question?')
        value,error=self.call(recipient,'ack',message_id=message,outcome='accepted')
        self.assertFalse(error,value);self.assertTrue(value['claimed'])
        value,error=self.call(recipient,'reply',message_id=message,body='Fixture answer.',
            idempotency_key='reply-1',delivery='inbox')
        self.assertFalse(error,value)
        reply=value['message']['message_id']
        value,error=self.call(sender,'read',message_id=reply)
        self.assertFalse(error,value);self.assertEqual(value['body'],'Fixture answer.')
        self.assertNotEqual(message,reply)

    def test_first_contact_does_not_require_recipient_to_poll_before_receiving(self):
        sender, recipient = self.ids
        value, error = self.call(sender, 'send', to='thread:' + recipient,
            body='First contact', idempotency_key='first-contact', delivery='inbox')
        self.assertFalse(error, value)
        value, error = self.call(recipient, 'read', message_id=value['message']['message_id'])
        self.assertFalse(error, value)
        self.assertEqual(value['body'], 'First contact')

    def test_first_contact_preserves_recipient_revocation_and_receive_denial(self):
        sender, recipient = self.ids
        self.assertFalse(self.call(recipient)[1])
        with self.bus.connection() as db:
            db.execute('UPDATE actors SET revoked=1 WHERE thread_id=?', (recipient,)); db.commit()
        value, error = self.call(sender, 'send', to='thread:' + recipient,
            body='Refused', idempotency_key='revoked-contact', delivery='inbox')
        self.assertTrue(error, value)
        self.assertEqual(value['error']['code'], 'authorization_denied')
        with self.bus.connection(read_only=True) as db:
            self.assertEqual(db.execute('SELECT revoked FROM actors WHERE thread_id=?', (recipient,)).fetchone()[0], 1)
        self.bus.enroll(self.project, self.operator, receive=False)
        value, error = self.call(sender, 'send', to='thread:' + recipient,
            body='Refused', idempotency_key='receive-disabled', delivery='inbox')
        self.assertTrue(error, value)

    def test_first_contact_preserves_cross_root_denial_before_issuance(self):
        sender, recipient = self.ids
        other = self.root / 'other'; other.mkdir()
        self.bus.enroll(other, self.operator)
        self.identities[recipient] = RuntimeIdentity('fixture-runtime', recipient, str(other))
        value, error = self.call(sender, 'send', to='thread:' + recipient,
            body='Refused', idempotency_key='cross-root-contact', delivery='inbox')
        self.assertTrue(error, value)
        self.assertEqual(value['error']['code'], 'cross_root_denied')
        with self.bus.connection(read_only=True) as db:
            self.assertIsNone(db.execute('SELECT actor_id FROM actors WHERE thread_id=?', (recipient,)).fetchone())

    def test_first_contact_never_enrolls_outside_recipient_root(self):
        sender, recipient = self.ids
        outside = self.root / 'outside'; outside.mkdir()
        self.identities[recipient] = RuntimeIdentity('fixture-runtime', recipient, str(outside))
        value, error = self.call(sender, 'send', to='thread:' + recipient,
            body='Refused', idempotency_key='outside-contact', delivery='inbox')
        self.assertTrue(error, value)
        self.assertEqual(value['error']['code'], 'mailbox_root_not_enrolled')
        with self.bus.connection(read_only=True) as db:
            self.assertIsNone(db.execute('SELECT actor_id FROM actors WHERE thread_id=?', (recipient,)).fetchone())

    def test_missing_or_contradictory_native_context_cannot_issue_actor(self):
        for context in (None,self.context(self.ids[1])):
            value,error=self.runner.call('wake_messages_inbox',
                dict(caller_thread_id=self.ids[0]),context)
            self.assertTrue(error,value)
        self.assertEqual(self.bus.status()['active_actors'],0)

    def test_unenrolled_root_and_revoked_actor_are_not_reauthorized(self):
        outside=self.root/'outside';outside.mkdir()
        thread=self.ids[0]
        self.identities[thread]=RuntimeIdentity('fixture-runtime',thread,str(outside))
        value,error=self.call(thread)
        self.assertTrue(error,value)
        self.assertEqual(value['error']['code'],'mailbox_root_not_enrolled')
        self.assertEqual(self.bus.status()['active_actors'],0)
        self.identities[thread]=RuntimeIdentity('fixture-runtime',thread,str(self.project))
        self.assertFalse(self.call(thread)[1])
        with self.bus.connection() as db:
            db.execute('UPDATE actors SET revoked=1');db.commit()
        value,error=self.call(thread)
        self.assertTrue(error,value)
        with self.bus.connection(read_only=True) as db:
            self.assertEqual(db.execute('select count(*) from actors').fetchone()[0],1)
            self.assertEqual(db.execute('select revoked from actors').fetchone()[0],1)

    def test_current_rotated_capability_is_reused(self):
        thread=self.ids[0];self.assertFalse(self.call(thread)[1])
        with self.bus.connection(read_only=True) as db:
            actor=db.execute('select actor_id from actors').fetchone()[0]
        self.bus.rotate_actor(actor,self.operator)
        self.assertFalse(self.call(thread)[1])
        with self.bus.connection(read_only=True) as db:
            self.assertEqual(db.execute('select generation from actors').fetchone()[0],2)

    def test_bad_operator_does_not_probe_native_runtime(self):
        self.runner.mailbox_operator_capability=self.root/'absent-operator'
        with patch('codex_wake.native_mailbox_bootstrap.resolve_identity') as observe:
            value,error=self.runner.call('wake_messages_inbox',
                dict(caller_thread_id=self.ids[0]),self.context(self.ids[0]))
        self.assertTrue(error,value);observe.assert_not_called()
        self.assertEqual(self.bus.status()['active_actors'],0)

    def test_disabled_enrollment_does_not_issue_actor(self):
        self.bus.enroll(self.project,self.operator,send=False,receive=False)
        value,error=self.call(self.ids[0])
        self.assertTrue(error,value)
        self.assertEqual(self.bus.status()['active_actors'],0)

    def test_concurrent_first_use_issues_one_actor_and_reuses_it(self):
        from concurrent.futures import ThreadPoolExecutor
        from codex_wake.native_mailbox_bootstrap import actor_context
        thread=self.ids[0]
        def resolve():
            return actor_context(self.bus.root,self.operator,thread,self.context(thread),endpoint='fixture://')['capability']
        with patch('codex_wake.native_mailbox_bootstrap.resolve_identity',return_value=self.identities[thread]):
            with ThreadPoolExecutor(max_workers=2) as pool:
                paths=list(pool.map(lambda _:resolve(),range(2)))
        self.assertEqual(paths[0],paths[1])
        self.assertEqual(self.bus.status()['active_actors'],1)
