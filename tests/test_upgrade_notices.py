"""Upgrade notice delivery through persisted events and native no-turn protocol."""
import json
from pathlib import Path
import tempfile
import unittest
from codex_wake.controller_auth import Actor

from codex_wake.controller_notices import ControllerNotices
from codex_wake.upgrade_notices import UpgradeNotices


class UpgradeNoticeTests(unittest.TestCase):
    def fixture(self,root):
        from codex_wake.controller_health import _TARGET_FIELDS
        target={key:'fixture' for key in _TARGET_FIELDS if key!='process'}
        target.update(process_pid='123',process_start_ticks='456',process_boot_id='boot',runtime='codex',conversation_id='operator',home='/fixture/home')
        actor=Actor('owner','service','client','grant','issuer','resource',frozenset({'observe','control','admin'}),[target],9999999999)
        store=root/'upgrade-jobs';store.mkdir()
        state=dict(schema_version=1,enabled=False,generation=2,jobs={'job':dict(id='job',version='0.166.0',target={'namespace':'test'})},
            events=[dict(id=1,kind='held',job_id='job',at=100,reason='repair_attempts_exhausted')])
        (store/'state.json').write_text(json.dumps(state))
        (root/'upgrade-bot.json').write_text(json.dumps(dict(schema_version=1,target={'namespace':'test'},recipes={},notice_recipients=[dict(target=target)])))
        notices={};calls=[]
        def request(endpoint,command,method,params,timeout):
            calls.append((method,params))
            if method=='thread/notice/read':
                return dict(notice=notices.get(params['eventId']),modelContextAvailable=True)
            self.assertEqual(method,'thread/notice/append')
            notices[params['eventId']]=dict(eventId=params['eventId'],text=params['text'])
            return dict(eventId=params['eventId'],recorded=True,notificationPublished=True,modelContextAvailable=True)
        owner=ControllerNotices(root,request=request,binding=lambda value:dict(endpoint='unix:///fixture',codex_cmd=['fixture']))
        return target,actor,owner,request,notices,calls

    def test_held_notice_is_delivered_without_enabling_upgrade_or_model_turn(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);target,actor,owner,request,notices,calls=self.fixture(root)
            result=UpgradeNotices(root,owner=owner).drain(actor,authorize=lambda:actor)
            self.assertEqual(result['deliveries'][0]['status'],'recorded',result)
            self.assertIn('0.166.0',next(iter(notices.values()))['text'])
            self.assertIn('repair_attempts_exhausted',next(iter(notices.values()))['text'])
            again=UpgradeNotices(root,owner=owner).drain(actor,authorize=lambda:actor)
            self.assertEqual(len(calls),1)
            self.assertFalse(json.loads((root/'upgrade-jobs/state.json').read_text())['enabled'])
            self.assertEqual(again['deliveries'][0]['status'],'recorded')

    def test_response_loss_reconciles_original_event_without_second_append(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);target,actor,owner,request,notices,calls=self.fixture(root)
            def lost_ack(*args):
                reply=request(*args)
                if args[2]=='thread/notice/append':raise OSError('reply lost')
                return reply
            owner.request=lost_ack
            first=UpgradeNotices(root,owner=owner).drain(actor,authorize=lambda:actor)
            self.assertEqual(first['deliveries'][0]['status'],'uncertain')
            owner.request=request
            second=UpgradeNotices(root,owner=owner).drain(actor,authorize=lambda:actor)
            self.assertEqual(second['deliveries'][0]['status'],'recorded')
            self.assertEqual([method for method,_ in calls],['thread/notice/append','thread/notice/read'])

    def test_missing_recipient_and_pre_effect_refusal_are_visible_and_recoverable(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);target,actor,owner,request,notices,calls=self.fixture(root)
            config=json.loads((root/'upgrade-bot.json').read_text())
            config['notice_recipients']=[];(root/'upgrade-bot.json').write_text(json.dumps(config))
            missing=UpgradeNotices(root,owner=owner).drain(actor,authorize=lambda:actor)
            self.assertEqual(missing['no_recipient_events'],[1])
            self.assertEqual(calls,[])
            config['notice_recipients']=[dict(target=target)];(root/'upgrade-bot.json').write_text(json.dumps(config))
            readonly=Actor(actor.subject,actor.principal_kind,actor.client_id,actor.grant_id,actor.issuer,actor.resource,frozenset({'observe'}),[target],actor.expires_at)
            denied=UpgradeNotices(root,owner=owner).drain(readonly,authorize=lambda:readonly)
            self.assertEqual(denied['deliveries'][0]['status'],'failed')
            self.assertEqual(denied['deliveries'][0]['reason'],'insufficient_scope')
            self.assertEqual(calls,[])
            restored=UpgradeNotices(root,owner=owner).drain(actor,authorize=lambda:actor)
            self.assertEqual(restored['deliveries'][0]['status'],'recorded')
            self.assertEqual(len(calls),1)

    def test_replaced_recipient_generation_gets_new_notice_but_mutated_event_is_held(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);target,actor,owner,request,notices,calls=self.fixture(root)
            first=UpgradeNotices(root,owner=owner).drain(actor,authorize=lambda:actor)
            changed=dict(target,connection_generation='replacement',process_start_ticks='789')
            config=json.loads((root/'upgrade-bot.json').read_text());config['notice_recipients']=[dict(target=changed)]
            (root/'upgrade-bot.json').write_text(json.dumps(config))
            next_actor=Actor(actor.subject,actor.principal_kind,actor.client_id,actor.grant_id,actor.issuer,actor.resource,actor.scopes,[changed],actor.expires_at)
            second=UpgradeNotices(root,owner=owner).drain(next_actor,authorize=lambda:next_actor)
            self.assertEqual(len(second['deliveries']),2)
            self.assertEqual(len({record['event_id'] for record in second['deliveries']}),2)
            self.assertEqual(len(calls),2)
            state=json.loads((root/'upgrade-jobs/state.json').read_text());state['events'][0]['reason']='modified retained event'
            (root/'upgrade-jobs/state.json').write_text(json.dumps(state))
            held=UpgradeNotices(root,owner=owner).drain(next_actor,authorize=lambda:next_actor)
            current=next(r for r in held['deliveries'] if r['target']==changed)
            self.assertEqual(current['status'],'source_changed')
            self.assertEqual(len(calls),2)

    def test_absent_or_unsupported_readback_never_retries_an_uncertain_append(self):
        from codex_wake.native_protocol import NativeCapabilityUnavailable
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);target,actor,owner,request,notices,calls=self.fixture(root)
            def unobserved(endpoint,command,method,params,timeout):
                calls.append((method,params))
                if method=='thread/notice/append':raise OSError('unknown append result')
                return dict(notice=None)
            owner.request=unobserved
            UpgradeNotices(root,owner=owner).drain(actor,authorize=lambda:actor)
            missing=UpgradeNotices(root,owner=owner).drain(actor,authorize=lambda:actor)
            self.assertEqual(missing['deliveries'][0]['status'],'uncertain')
            def unsupported(*args):raise NativeCapabilityUnavailable('missing notice read')
            owner.request=unsupported
            held=UpgradeNotices(root,owner=owner).drain(actor,authorize=lambda:actor)
            self.assertEqual(held['deliveries'][0]['status'],'uncertain')
            self.assertEqual([method for method,_ in calls],['thread/notice/append','thread/notice/read'])
