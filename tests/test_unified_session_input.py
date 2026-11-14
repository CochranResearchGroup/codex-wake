"""Explicit busy-input policies retain original native effects across retries."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

class SessionInputTests(unittest.TestCase):
    def test_queue_retains_native_acceptance_without_claiming_completion_or_replaying(self):
        from codex_wake.unified_session_input import SessionInputs
        with tempfile.TemporaryDirectory() as d:
            target=dict(host='h',environment='e',uid=os.getuid(),home=d,conversation_id='thread',process={'pid':os.getpid()})
            row=dict(thread_id='thread',target=target,endpoint='unix:///private.sock',codex_cmd=['codex'])
            calls=[]
            def request(row,method,args):
                calls.append(method)
                if method=='thread/read':return {'thread':{'id':'thread','status':{'type':'active'},'turns':[{'id':'active','status':'inProgress','items':[]}]}}
                if method=='thread/queue/add':return {'queuedSubmission':{'id':'queued','clientUserMessageId':args['clientUserMessageId'],'input':args['input']}}
                raise AssertionError(method)
            with patch('codex_wake.unified_session_input.resolve',return_value=row):
                owner=SessionInputs(Path(d),request=request)
                first=owner.submit('thread:thread','Next task','queue','key')
                second=owner.submit('thread:thread','Next task','queue','key')
                self.assertEqual(first['result']['operation']['operation_id'],second['result']['operation']['operation_id'])
                self.assertEqual(first['result']['operation']['execution'],'queued')
                self.assertEqual(calls.count('thread/queue/add'),1)
                self.assertNotIn('turn/start',calls)
    def test_reject_busy_does_not_mutate_the_native_session(self):
        from codex_wake.unified_session_input import SessionInputs
        from codex_wake.managed_inventory import InventoryError
        with tempfile.TemporaryDirectory() as d:
            row=dict(thread_id='t',target=dict(host='h',environment='e',uid=os.getuid(),home=d),endpoint='unix:///owned',codex_cmd=['codex'])
            calls=[]
            def request(row,method,args):calls.append(method);return {'thread':{'id':'t','status':{'type':'active'},'turns':[]}}
            with patch('codex_wake.unified_session_input.resolve',return_value=row):
                with self.assertRaisesRegex(InventoryError,'busy'):SessionInputs(Path(d),request=request).submit('thread:t','hello','reject','key')
                self.assertEqual(calls,['thread/read'])
