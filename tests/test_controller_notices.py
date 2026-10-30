import json
import tempfile
import time
import unittest
from pathlib import Path

from codex_wake.controller_auth import Actor, AuthError
from codex_wake.controller_runtime import ControllerRuntime


class ControllerNoticeTests(unittest.TestCase):
    def test_retained_action_is_visible_without_turn_or_replayed_delivery(self):
        from codex_wake.controller_notices import ControllerNotices
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = dict(host='fixture', environment='linux', runtime='codex',
                namespace='account:one', conversation_id='thread-one', home='/fixture/home',
                provider='fixture', build_sha256='a'*64, backend_id='native', channel='tui',
                connection_generation='one', process_pid='123', process_start_ticks='456', process_boot_id='boot')
            actor = Actor('operator','service','client','grant','issuer','resource',
                frozenset({'observe','recovery'}),[target],time.time()+600)
            runtime = ControllerRuntime(root)
            def meta(name):
                return dict(operation_id=name,idempotency_key=name,correlation_id=name,binding='sender',target=target)
            runtime.execute(actor,'recovery.disable',dict(expected_target=target,_request=meta('source')),
                authorize=lambda:actor,dispatch=lambda *unused:dict(policy_id='policy-one',mode='off',reason='operator requested',outcome='disabled'))
            calls, notices = [], {}
            def request(endpoint,command,method,params,timeout):
                calls.append(method)
                if method=='thread/notice/append':
                    notices[params['eventId']] = dict(eventId=params['eventId'],text=params['text'])
                    return dict(eventId=params['eventId'],recorded=True,modelContextAvailable=True,notificationPublished=True)
                return dict(notice=notices.get(params['eventId']),modelContextAvailable=True)
            owner = ControllerNotices(root,request=request,binding=lambda target:dict(endpoint='unix:///fixture',codex_cmd=['/fixture/codex']))
            args = dict(expected_target=target,source_operation_id='source',_request=meta('notice'))
            first = owner.execute(actor,'notices.publish',args,authorize=lambda:actor)
            self.assertEqual(first['result']['operation']['result']['delivery']['status'],'recorded')
            self.assertEqual(owner.execute(actor,'notices.publish',args,authorize=lambda:actor),first)
            self.assertEqual(calls,['thread/notice/append'])
            text = next(iter(notices.values()))['text']
            for value in ('Codex Wake controller','policy-one','recovery.disable','operator requested','disabled','off'):
                self.assertIn(value,text)
            listed = owner.execute(actor,'notices.list',dict(expected_target=target),authorize=lambda:actor)
            self.assertEqual(listed['result']['notices'][0]['source']['policy_id'],'policy-one')
            self.assertFalse((root/'goal-supervision').exists())
            peer = Actor('peer',*tuple(actor.__dict__.values())[1:])
            self.assertEqual(owner.execute(peer,'notices.list',dict(expected_target=target),authorize=lambda:peer)['result']['notices'],[])
            with self.assertRaises(AuthError):
                owner.execute(peer,'notices.publish',dict(args,_request=meta('peer-notice')),authorize=lambda:peer)
            def lost_ack(*values):
                request(*values)
                raise TimeoutError('fixture lost acknowledgement')
            owner.request = lost_ack
            uncertain_args = dict(args,_request=meta('lost-ack'))
            uncertain = owner.execute(actor,'notices.publish',uncertain_args,authorize=lambda:actor)
            self.assertEqual(uncertain['result']['operation']['phase'],'uncertain')
            self.assertEqual(owner.execute(actor,'notices.publish',uncertain_args,authorize=lambda:actor),uncertain)
            owner.request = request
            reconciled = owner.execute(actor,'notices.reconcile',dict(expected_target=target,operation_id='lost-ack'),authorize=lambda:actor)
            self.assertEqual(reconciled['result']['operation']['acceptance'],'owner_observed')
            self.assertIsNone(reconciled['result']['operation']['result']['delivery']['notification_published'])
            self.assertEqual(calls,['thread/notice/append','thread/notice/append','thread/notice/read'])
            from codex_wake.native_protocol import NativeCapabilityUnavailable
            def unsupported(*unused):
                raise NativeCapabilityUnavailable('stock runtime lacks notices')
            owner.request = unsupported
            refused = owner.execute(actor,'notices.publish',dict(args,_request=meta('stock')),authorize=lambda:actor)
            self.assertEqual(refused['result']['operation']['result']['delivery']['status'],'unsupported')

    def test_notice_cli_and_mcp_share_strict_public_schemas(self):
        from codex_wake.cli import build_parser
        from codex_wake.controller_http import TOOLS, ProtectedOperations
        from codex_wake.mcp_server import SPECS
        args = build_parser().parse_args(['notices','list','--arguments','{"expected_target":{}}'])
        self.assertEqual(args.notice_verb,'list')
        for verb in ('publish','list','reconcile'):
            name = 'wake_controller_notices_' + verb
            self.assertEqual(TOOLS[name][0],'notices.'+verb)
            self.assertEqual(SPECS[name][1],'notices.'+verb)
            self.assertIn('notices.'+verb,ProtectedOperations.READ_POLICIES)
