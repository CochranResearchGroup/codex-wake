import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from codex_wake.cli import main
from codex_wake.a2a_bus import BusStore
from codex_wake.a2a_identity import RuntimeIdentity
from codex_wake.a2a_mailbox import Mailbox


class MessageCLITests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / 'bus'
        self.repo = Path(self.temporary.name) / 'repo';self.repo.mkdir()
        self.body = self.repo / 'body.txt';self.body.write_text('Fixture body')
        self.bus,self.operator = BusStore.configure(self.root)
        self.bus.enroll(self.repo,self.operator)
        self.identities = [RuntimeIdentity('runtime', thread, str(self.repo)) for thread in ['sender','recipient']]
        self.capabilities=[];self.actors=[]
        for identity in self.identities:
            capability,_=self.bus.issue_actor(identity,self.repo,self.operator)
            self.capabilities.append(capability)
            self.actors.append(self.bus.authenticate(capability,identity,invoking_cwd=self.repo))
        Mailbox.migrate(self.bus,self.operator)

    def invoke(self, arguments, actor=0):
        with patch('codex_wake.messages_cli.invoking_actor',return_value=self.actors[actor]), patch('codex_wake.messages_cli.resolve_identity',return_value=self.identities[1]), patch('sys.stdout',new_callable=io.StringIO) as out:
            code=main(['messages',*arguments,'--bus-root',str(self.root),'--capability',str(self.capabilities[actor]),'--json'])
        return code,[json.loads(line) for line in out.getvalue().splitlines()]

    def send(self,key='cli-intent'):
        code,values=self.invoke(['send','--to','thread:recipient','--body-file',str(self.body),'--idempotency-key',key,'--delivery','inbox'])
        self.assertEqual(code,0)
        return values[0]['message']['message_id']

    def test_full_inbox_read_ack_reply_wait_and_outbox_workflow(self):
        identifier=self.send()
        code,inbox=self.invoke(['inbox'],actor=1)
        self.assertEqual(inbox[0]['messages'][0]['message_id'],identifier)
        self.assertNotIn('Fixture body',json.dumps(inbox))
        code,read=self.invoke(['read',identifier],actor=1)
        self.assertEqual(read[0]['body'],'Fixture body')
        self.assertEqual(read[0]['peer_content_trust'],'untrusted')
        code,claim=self.invoke(['ack',identifier,'--outcome','accepted'],actor=1)
        self.assertTrue(claim[0]['claimed'])
        code,reply=self.invoke(['reply',identifier,'--body-file',str(self.body),'--idempotency-key','reply-intent','--delivery','inbox'],actor=1)
        self.assertEqual(code,0)
        reply_id=reply[0]['message']['message_id']
        code,wait=self.invoke(['wait',identifier,'--for','reply','--timeout','1s'])
        self.assertEqual(code,0);self.assertEqual(wait[0]['replies'][0]['message_id'],reply_id)
        self.assertEqual(self.invoke(['read',reply_id])[1][0]['body'],'Fixture body')
        self.assertEqual(self.invoke(['outbox'])[1][0]['messages'][0]['message_id'],identifier)

    def test_machine_key_required_before_store_or_peer_access(self):
        with patch('codex_wake.messages_cli.resolve_identity') as resolve:
            code,error=self.invoke(['send','--to','thread:recipient','--body-file',str(self.body)])
        self.assertEqual(code,8)
        self.assertEqual(error[0]['error']['code'],'invalid_argument')
        resolve.assert_not_called()

    def test_idempotency_conflict_returns_original_key_and_no_second_message(self):
        identifier=self.send()
        self.body.write_text('Different fixture body')
        code,error=self.invoke(['send','--to','thread:recipient','--body-file',str(self.body),'--idempotency-key','cli-intent','--delivery','inbox'])
        self.assertEqual(code,9)
        self.assertEqual(error[0]['idempotency_key'],'cli-intent')
        self.assertEqual(len(self.invoke(['outbox'])[1][0]['messages']),1)

    def test_operator_body_inspection_does_not_mark_received(self):
        identifier=self.send()
        code,inspected=self.invoke(['read',identifier,'--as-operator','--operator-capability',str(self.operator)])
        self.assertEqual(code,0)
        self.assertEqual(inspected[0]['body'],'Fixture body')
        self.assertIsNone(inspected[0]['message']['received_receipt_id'])

    def test_bounded_wait_timeout_and_watch_are_observation_only(self):
        identifier=self.send()
        with patch('codex_wake.messages_cli.time.monotonic',side_effect=[0,2]):
            code,error=self.invoke(['wait',identifier,'--for','received','--timeout','1s'])
        self.assertEqual(code,10)
        self.assertEqual(error[0]['error']['code'],'observation_timeout')
        with patch('codex_wake.messages_cli.time.monotonic',side_effect=[0,2]):
            code,watch=self.invoke(['watch',identifier,'--duration','1s'])
        self.assertEqual(code,0)
        self.assertEqual([item['event'] for item in watch],['initial','summary'])
        self.assertEqual(self.invoke(['show',identifier])[1][0]['message']['state']['recipient'],'unread')

    def test_cancelled_message_stays_inspectable(self):
        identifier=self.send()
        self.assertEqual(self.invoke(['cancel',identifier])[0],0)
        self.assertEqual(self.invoke(['show',identifier])[1][0]['message']['state']['admission'],'cancelled')
        self.assertEqual(self.invoke(['reconcile',identifier])[1][0]['reconciliation'],'no_uncertain_effect')
