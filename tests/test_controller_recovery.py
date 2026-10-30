"""Public recovery-policy seam: persistence, original authority and bounded effects."""
import tempfile
import time
import unittest
from pathlib import Path

from codex_wake.controller_auth import Actor, AuthError


class RecoveryTests(unittest.TestCase):
    def fixture(self, root):
        from codex_wake.controller_recovery import ControllerRecovery
        clock=[100.0]
        target=dict(host='fixture',environment='linux',runtime='codex',namespace='one',build_sha256='a'*64,
            conversation_id='thread',home='/fixture/home',provider='fixture',backend_id='daemon',channel='tui',
            connection_generation='one',process_pid='123',process_start_ticks='456',process_boot_id='boot')
        actor=Actor('owner','service','client','grant','issuer','resource',frozenset({'observe','control','recovery'}),[target],1000)
        probes=[];notices=[];status=['unknown']
        def probe(raw,timeout):
            probes.append((raw,timeout));return dict(target=raw,observation=dict(status=status[0],responsive=status[0]=='responsive',evidence='tui_main_loop_ack' if status[0]=='responsive' else 'none',observed_at=clock[0],reason='fixture'),grants_recovery=False,application_effects=False)
        def notice(actor,source_id,target,guard):
            guard();notices.append(source_id);return dict(operation_id='notice-'+source_id,phase='terminal',delivery=dict(status='recorded'))
        owner=ControllerRecovery(root,now=lambda:clock[0],probe=probe,notice=notice)
        def args(name,**extra):
            return dict(policy_id='policy',expected_target=target,_request=dict(operation_id=name,idempotency_key=name,correlation_id=name,binding='operator',target=target),**extra)
        declaration=dict(interval_seconds=10,probe_timeout=1,unknown_threshold=2,cooldown_seconds=30,max_attempts=2,
            evidence='suspected_unresponsive',actions=[dict(kind='notify_operator')])
        return owner,actor,target,args,declaration,clock,probes,notices,status

    def test_default_observation_explicit_activation_and_deactivation_keep_accounting(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);owner,actor,target,args,policy,clock,probes,notices,status=self.fixture(root)
            configured=owner.execute(actor,'recovery.configure',args('configure',policy=policy),authorize=lambda:actor)
            self.assertEqual(configured['result']['operation']['result']['mode'],'observe')
            for index in range(2):
                clock[0]+=10
                owner.execute(actor,'recovery.tick',args('observe-'+str(index)),authorize=lambda:actor)
            state=owner.execute(actor,'recovery.show',dict(policy_id='policy',expected_target=target),authorize=lambda:actor)['result']['policy']
            self.assertEqual(state['health_status'],'suspected_unresponsive')
            self.assertEqual(state['attempts'],0)
            self.assertEqual(notices,[])
            owner.execute(actor,'recovery.enable',args('enable'),authorize=lambda:actor)
            clock[0]+=10
            applied=owner.execute(actor,'recovery.tick',args('automatic'),authorize=lambda:actor)
            self.assertEqual(applied['result']['operation']['result']['outcome'],'completed')
            self.assertEqual(len(probes),3)
            self.assertEqual(len(notices),2) # explicit activation and separate intervention
            before=owner.execute(actor,'recovery.show',dict(policy_id='policy',expected_target=target),authorize=lambda:actor)['result']['policy']
            disabled=owner.execute(actor,'recovery.disable',args('disable'),authorize=lambda:actor)
            self.assertEqual(disabled['result']['operation']['result']['mode'],'off')
            clock[0]+=50
            owner.execute(actor,'recovery.tick',args('after-disable'),authorize=lambda:actor)
            after=owner.execute(actor,'recovery.show',dict(policy_id='policy',expected_target=target),authorize=lambda:actor)['result']['policy']
            self.assertEqual(after['attempts'],before['attempts'])
            self.assertGreater(after['checks'],before['checks'])
            self.assertEqual(after['mode'],'off')
            self.assertEqual(after['next_due'],clock[0]+10)
            self.assertEqual(len(notices),3)
            self.assertFalse((root/'goal-supervision').exists())
            peer=Actor('peer',*tuple(actor.__dict__.values())[1:])
            with self.assertRaises(AuthError):owner.execute(peer,'recovery.show',dict(policy_id='policy',expected_target=target),authorize=lambda:peer)
