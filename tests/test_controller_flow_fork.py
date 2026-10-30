import unittest
from codex_wake.controller_flow_fork import fork_capability
from codex_wake.managed_inventory import InventoryError


class ForkTests(unittest.TestCase):
    def test_native_fork_requires_precise_checkpoint_variant(self):
        for profile,metadata in (({'modes':['fork'],'methods':['thread/fork']},{'forkCheckpointV1':True}),
                                 ({'modes':['fork'],'methods':['thread/fork@checkpoint_v1']},{})):
            with self.assertRaises(InventoryError) as caught:
                fork_capability(profile,metadata)
            self.assertEqual(caught.exception.code,'unsupported_fork_variant')
        fork_capability({'modes':['fork'],'methods':['thread/fork','thread/fork@checkpoint_v1']},{'forkCheckpointV1':True})

    def fixture(self,root,*,variant=True):
        import hashlib,json,os,time
        from pathlib import Path
        from codex_wake.controller_auth import Actor
        from codex_wake.controller_flow_sessions import ControllerFlowSessions
        from codex_wake.process import process_identity
        birth=process_identity(os.getpid())
        process=dict(pid=os.getpid(),start_ticks=birth['start_time_ticks'],boot_id=birth['boot_id'])
        base=dict(host='host',environment='fixture',provider='codex',account='alice',home=str(root),home_generation='fixture',
            configuration_revision='one',build_channel='modded',build_sha256=hashlib.sha256(Path('/proc/self/exe').read_bytes()).hexdigest(),build_revision='fixture',executable='/fixture/native')
        profile=dict(target=base,endpoint='unix:///fixture/native.sock',process=process,modes=['fork'],native_provider='codex',cwd=str(root),
            methods=['thread/start','turn/start','thread/read','turn/interrupt','thread/fork','thread/fork@checkpoint_v1'])
        path=root/'controller-flow-sessions.json'
        path.write_text(json.dumps(dict(version=1,profiles={'fixture':profile})));path.chmod(0o600)
        source=dict(id='source',cwd=str(root),modelProvider='codex',checkpointId='checkpoint-one',turns=[])
        effects=[]
        def request(endpoint,executable,method,params,timeout):
            if method=='thread/read':return dict(thread=dict(source))
            if method=='thread/fork':
                effects.append(params)
                return dict(thread=dict(id='child-'+str(len(effects)),cwd=str(root),modelProvider='codex'),
                    forkProvenance=dict(sourceThreadId=params['threadId'],checkpointId=params['checkpointId'],sourceSnapshotSha256=params['expectedSnapshotSha256']))
            raise AssertionError(method)
        owner=ControllerFlowSessions(root,resolve_build=lambda target:base,request=request,
            metadata=lambda profile:dict(codexHome=str(root),peer_pid=os.getpid(),forkCheckpointV1=variant))
        target=dict(owner.target('fixture'),conversation_id='source')
        actor=Actor('caller','service','client','grant','local://fixture','wake:controller',frozenset({'observe','control'}),[base],time.time()+600)
        return owner,target,actor,source,effects

    def test_common_checkpoint_distinct_children_stale_refusal_and_no_replay(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as directory:
            owner,target,actor,source,effects=self.fixture(Path(directory))
            checkpoint=owner.execute(actor,'sessions.checkpoint',dict(profile='fixture',expected_target=target),authorize=lambda:actor)['result']['checkpoint']
            def fork(key):
                return owner.execute(actor,'sessions.fork',dict(profile='fixture',expected_target=target,checkpoint=checkpoint,
                    _request=dict(operation_id=key,idempotency_key=key,correlation_id=key,binding='foreach',target=target)),authorize=lambda:actor)
            first=fork('one')
            second=fork('two')
            self.assertNotEqual(first['result']['operation']['result']['target'],second['result']['operation']['result']['target'])
            self.assertEqual(first['result']['operation']['result']['checkpoint'],second['result']['operation']['result']['checkpoint'])
            self.assertEqual(fork('one'),first)
            self.assertEqual(len(effects),2)
            source['checkpointId']='changed'
            denied=fork('three')['result']['operation']
            self.assertEqual(denied['reason'],'stale_checkpoint')
            self.assertEqual(len(effects),2)
            self.assertEqual(effects[0]['checkpointId'],'checkpoint-one')

    def test_unknown_variant_has_no_native_effect(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as directory:
            owner,target,actor,source,effects=self.fixture(Path(directory),variant=False)
            with self.assertRaises(InventoryError) as caught:
                owner.execute(actor,'sessions.checkpoint',dict(profile='fixture',expected_target=target),authorize=lambda:actor)
            self.assertEqual(caught.exception.code,'unsupported_fork_variant')
            self.assertEqual(effects,[])
