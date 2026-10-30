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

    def test_cooldown_and_attempt_ceiling_are_cumulative_across_reenable(self):
        with tempfile.TemporaryDirectory() as directory:
            owner,actor,target,args,policy,clock,probes,notices,status=self.fixture(Path(directory))
            owner.execute(actor,'recovery.configure',args('configure',policy=policy),authorize=lambda:actor)
            owner.execute(actor,'recovery.enable',args('enable'),authorize=lambda:actor)
            for index in range(5):
                clock[0]+=10
                owner.execute(actor,'recovery.tick',args('tick-'+str(index)),authorize=lambda:actor)
            state=owner.execute(actor,'recovery.show',dict(policy_id='policy',expected_target=target),authorize=lambda:actor)['result']['policy']
            self.assertEqual(state['attempts'],2)
            owner.execute(actor,'recovery.disable',args('off'),authorize=lambda:actor)
            owner.execute(actor,'recovery.enable',args('on-again'),authorize=lambda:actor)
            clock[0]+=30
            exhausted=owner.execute(actor,'recovery.tick',args('exhausted'),authorize=lambda:actor)
            self.assertEqual(exhausted['result']['operation']['result']['outcome'],'attempt_ceiling')
            after=owner.execute(actor,'recovery.show',dict(policy_id='policy',expected_target=target),authorize=lambda:actor)['result']['policy']
            self.assertEqual(after['attempts'],2)
            self.assertEqual(after['checks'],6)
            self.assertEqual(after['action_status'],'exhausted')

    def test_deactivation_prevents_later_actions_and_reconciles_only_original_effect(self):
        with tempfile.TemporaryDirectory() as directory:
            owner,actor,target,args,policy,clock,probes,notices,status=self.fixture(Path(directory))
            policy['actions']=[dict(kind='notify_operator'),dict(kind='notify_operator')]
            owner.execute(actor,'recovery.configure',args('configure',policy=policy),authorize=lambda:actor)
            owner.execute(actor,'recovery.enable',args('enable'),authorize=lambda:actor)
            calls=[]
            def action(actor,record,declaration,operation_id,index,guard):
                calls.append(index)
                owner.execute(actor,'recovery.disable',args('off-during-effect'),authorize=lambda:actor)
                return dict(kind='notify_operator',status='completed')
            owner.action=action
            for index in range(2):
                clock[0]+=10
                owner.execute(actor,'recovery.tick',args('tick-'+str(index)),authorize=lambda:actor)
            self.assertEqual(calls,[0])
            retained=owner.execute(actor,'recovery.reconcile',dict(policy_id='policy',expected_target=target),authorize=lambda:actor)['result']['policy']
            self.assertEqual(retained['mode'],'off')
            self.assertEqual(retained['attempts'],1)
            self.assertIsNone(retained['in_flight'])
            self.assertEqual(calls,[0])

    def test_exact_thread_refresh_reuses_existing_owner_without_shared_restart(self):
        import hashlib,json,os,sys
        from codex_wake.process import process_identity
        from codex_wake.controller_notices import flat_target
        from codex_wake.controller_recovery import ControllerRecovery,raw_target
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);owner,actor,target,args,policy,clock,probes,notices,status=self.fixture(root)
            birth=process_identity(os.getpid())
            target.update(process_pid=str(os.getpid()),process_start_ticks=str(birth['start_time_ticks']),process_boot_id=birth['boot_id'],build_sha256=hashlib.sha256(Path(sys.executable).resolve().read_bytes()).hexdigest())
            profile=dict(refresh_mode='thread_mcp_idle',scope_approval='explicit fixture owner approval',cwd=str(root),app_server='unix:///fixture.sock',codex_path=str(Path(sys.executable).resolve()),timeout=1,resources=dict(catalog=dict(kind='mcp_catalog',server='fixture',version='1',tools={'ping':[]})))
            binding=root/'controller-health.json';binding.write_text(json.dumps(dict(version=1,bindings=[dict(target=raw_target(target),endpoint='unix:///fixture.sock',codex_cmd=[profile['codex_path']])])));binding.chmod(0o600)
            registry=root/'controller-recovery.json';registry.write_text(json.dumps(dict(version=1,profiles=dict(selected=dict(target=target,refresh=profile)))));registry.chmod(0o600)
            calls=[]
            def request(endpoint,command,method,params,timeout):
                calls.append((method,params))
                if method=='thread/read':return dict(thread=dict(id='thread',cwd=str(root),modelProvider='fixture',status=dict(type='idle')))
                if method=='thread/goal/get':return {'goal':None}
                if method=='thread/mcpServer/reload':return dict(threadId='thread',queued=not params.get('dryRun',False))
                if method=='mcpServerStatus/list':return dict(data=[dict(name='fixture',serverInfo=dict(version='1'),tools=dict(ping=dict(inputSchema=dict(properties={}))))])
                raise AssertionError(method)
            owner=ControllerRecovery(root,now=lambda:clock[0],probe=owner.probe,notice=owner.notice,request=request)
            policy['actions']=[dict(kind='thread_mcp_refresh',profile='selected')]
            owner.execute(actor,'recovery.configure',args('configure',policy=policy),authorize=lambda:actor)
            owner.execute(actor,'recovery.enable',args('enable'),authorize=lambda:actor)
            for index in range(2):
                clock[0]+=10
                result=owner.execute(actor,'recovery.tick',args('tick-'+str(index)),authorize=lambda:actor)
            self.assertEqual(result['result']['operation']['result']['outcome'],'completed')
            mutations=[(method,params) for method,params in calls if method=='thread/mcpServer/reload' and not params.get('dryRun')]
            self.assertEqual(mutations,[('thread/mcpServer/reload',dict(threadId='thread'))])
            self.assertNotIn('config/mcpServer/reload',{method for method,params in calls})
            self.assertTrue(all(params.get('threadId')=='thread' for method,params in calls))

    def test_unsupported_actions_stale_targets_and_observer_cannot_enable(self):
        with tempfile.TemporaryDirectory() as directory:
            owner,actor,target,args,policy,clock,probes,notices,status=self.fixture(Path(directory))
            invalid=dict(policy,actions=[dict(kind='shared_native_restart')])
            from codex_wake.managed_inventory import InventoryError
            with self.assertRaises(InventoryError):
                owner.execute(actor,'recovery.configure',args('invalid',policy=invalid),authorize=lambda:actor)
            owner.execute(actor,'recovery.configure',args('configure',policy=policy),authorize=lambda:actor)
            observer=Actor(actor.subject,actor.principal_kind,actor.client_id,actor.grant_id,actor.issuer,actor.resource,frozenset({'observe'}),actor.targets,actor.expires_at)
            with self.assertRaises(AuthError):owner.execute(observer,'recovery.enable',args('enable'),authorize=lambda:observer)
            replaced=dict(target,connection_generation='replacement')
            replacement_actor=Actor(actor.subject,actor.principal_kind,actor.client_id,actor.grant_id,actor.issuer,actor.resource,actor.scopes,[replaced],actor.expires_at)
            with self.assertRaises(InventoryError):owner.execute(replacement_actor,'recovery.show',dict(policy_id='policy',expected_target=replaced),authorize=lambda:replacement_actor)
            self.assertEqual(probes,[])
            self.assertEqual(notices,[])
