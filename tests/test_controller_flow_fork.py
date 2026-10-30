import unittest
from codex_wake.controller_flow_fork import fork_capability
from codex_wake.managed_inventory import InventoryError


class ForkTests(unittest.TestCase):
    def test_existing_native_fork_method_is_sufficient_without_hypothetical_advertisement(self):
        fork_capability({'modes':['fork'],'methods':['thread/fork','thread/read']},{})
        with self.assertRaises(InventoryError):
            fork_capability({'modes':['fork'],'methods':['thread/read']},{})

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
            methods=['thread/start','turn/start','thread/read','turn/interrupt','thread/fork'])
        if not variant: profile['methods'].remove('thread/fork')
        path=root/'controller-flow-sessions.json'
        path.write_text(json.dumps(dict(version=1,profiles={'fixture':profile})));path.chmod(0o600)
        source=dict(id='source',cwd=str(root),modelProvider='codex',ephemeral=False,path=str(root/'rollout.jsonl'),turns=[dict(id='persisted-one',status='completed',items=[dict(id='message-one',type='agentMessage',text='retained answer')])])
        effects=[];children={}
        def request(endpoint,executable,method,params,timeout):
            if method=='thread/read':
                import copy
                return dict(thread=copy.deepcopy(source if params['threadId']=='source' else children[params['threadId']]))
            if method=='thread/fork':
                effects.append(params)
                import copy
                child=copy.deepcopy(source)
                child['id']='child-'+str(len(effects))
                stop=next(i for i,t in enumerate(child['turns']) if t['id']==params['lastTurnId'])
                child['turns']=child['turns'][:stop+1]
                children[child['id']]=child
                return dict(thread=child)
            raise AssertionError(method)
        owner=ControllerFlowSessions(root,resolve_build=lambda target:base,request=request,
            metadata=lambda profile:dict(codexHome=str(root),peer_pid=os.getpid()))
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
            source['turns'][0]['items'][0]['text']='changed'
            denied=fork('three')['result']['operation']
            self.assertEqual(denied['reason'],'stale_checkpoint')
            self.assertEqual(len(effects),2)
            self.assertEqual(effects[0]['lastTurnId'],'persisted-one')

    def test_noncompleted_or_unpersisted_checkpoint_has_no_native_effect(self):
        import tempfile
        from pathlib import Path
        for change in (lambda source: source.update(ephemeral=True),
                       lambda source: source.update(path=None),
                       lambda source: source['turns'][0].update(status='inProgress'),
                       lambda source: source['turns'][0].update(status='failed'),
                       lambda source: source['turns'][0].update(itemsView='summary')):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as directory:
                owner,target,actor,source,effects=self.fixture(Path(directory));change(source)
                with self.assertRaises(InventoryError):
                    owner.execute(actor,'sessions.checkpoint',dict(profile='fixture',expected_target=target),authorize=lambda:actor)
                self.assertEqual(effects,[])

    def test_child_mismatch_never_exposes_promptable_target_or_replays_effect(self):
        import tempfile
        from pathlib import Path
        for damage in ('items','id','extra'):
            with self.subTest(damage=damage), tempfile.TemporaryDirectory() as directory:
                owner,target,actor,source,effects=self.fixture(Path(directory))
                pinned=owner.execute(actor,'sessions.checkpoint',dict(profile='fixture',expected_target=target),authorize=lambda:actor)['result']['checkpoint']
                original=owner.request;calls=[]
                def corrupt(endpoint,executable,method,params,timeout):
                    calls.append(method);value=original(endpoint,executable,method,params,timeout)
                    if method=='thread/read' and params['threadId']!='source':
                        turns=value['thread']['turns']
                        if damage=='items': turns[0]['items'][0]['text']='wrong answer'
                        elif damage=='id': turns[0]['id']='wrong turn'
                        else: turns.append(dict(id='later',status='completed',items=[]))
                    return value
                owner.request=corrupt
                args=dict(profile='fixture',expected_target=target,checkpoint=pinned,
                    _request=dict(operation_id='bad',idempotency_key='bad',correlation_id='bad',binding='fixture',target=target))
                result=owner.execute(actor,'sessions.fork',args,authorize=lambda:actor)
                self.assertEqual(result['result']['operation']['phase'],'uncertain')
                self.assertIsNone(result['result']['operation']['result'])
                self.assertEqual(owner.execute(actor,'sessions.fork',args,authorize=lambda:actor),result)
                self.assertEqual(len(effects),1)
                self.assertNotIn('turn/start',calls)
                self.assertNotIn('thread/revert',calls)

    def test_source_later_turn_is_excluded_from_selected_common_checkpoint(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as directory:
            owner,target,actor,source,effects=self.fixture(Path(directory))
            pinned=owner.execute(actor,'sessions.checkpoint',dict(profile='fixture',expected_target=target),authorize=lambda:actor)['result']['checkpoint']
            source['turns'].append(dict(id='later',status='completed',items=[]))
            result=owner.execute(actor,'sessions.fork',dict(profile='fixture',expected_target=target,checkpoint=pinned,
                _request=dict(operation_id='later',idempotency_key='later',correlation_id='later',binding='fixture',target=target)),authorize=lambda:actor)
            self.assertEqual(result['result']['operation']['result']['provenance']['retainedTurnIds'],['persisted-one'])
            self.assertEqual(effects[0],dict(threadId='source',lastTurnId='persisted-one',cwd=directory,ephemeral=False))

    def test_revocation_after_source_read_blocks_native_fork(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as directory:
            owner,target,actor,source,effects=self.fixture(Path(directory))
            pinned=owner.execute(actor,'sessions.checkpoint',dict(profile='fixture',expected_target=target),authorize=lambda:actor)['result']['checkpoint']
            original=owner.request;revoked=[False]
            def request(endpoint,executable,method,params,timeout):
                value=original(endpoint,executable,method,params,timeout)
                if method=='thread/read':revoked[0]=True
                return value
            def authorize():
                if revoked[0]:raise InventoryError('forbidden','fixture grant revoked')
                return actor
            owner.request=request
            try:
                owner.execute(actor,'sessions.fork',dict(profile='fixture',expected_target=target,checkpoint=pinned,
                    _request=dict(operation_id='revoked',idempotency_key='revoked',correlation_id='revoked',binding='fixture',target=target)),authorize=authorize)
            except InventoryError:
                pass
            self.assertEqual(effects,[])

    def test_unknown_variant_has_no_native_effect(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as directory:
            owner,target,actor,source,effects=self.fixture(Path(directory),variant=False)
            with self.assertRaises(InventoryError) as caught:
                owner.execute(actor,'sessions.checkpoint',dict(profile='fixture',expected_target=target),authorize=lambda:actor)
            self.assertEqual(caught.exception.code,'unsupported_fork_variant')
            self.assertEqual(effects,[])

    def test_advertised_but_unknown_native_method_stays_uncertain_without_fallback(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as directory:
            owner,target,actor,source,effects=self.fixture(Path(directory))
            pinned=owner.execute(actor,'sessions.checkpoint',dict(profile='fixture',expected_target=target),authorize=lambda:actor)['result']['checkpoint']
            original=owner.request
            calls=[]
            def unsupported(endpoint,executable,method,params,timeout):
                if method=='thread/fork':
                    calls.append(method)
                    raise ValueError('native unknown method thread/fork')
                return original(endpoint,executable,method,params,timeout)
            owner.request=unsupported
            args=dict(profile='fixture',expected_target=target,checkpoint=pinned,
                _request=dict(operation_id='unknown',idempotency_key='unknown',correlation_id='unknown',binding='fixture',target=target))
            result=owner.execute(actor,'sessions.fork',args,authorize=lambda:actor)
            self.assertEqual(result['result']['operation']['phase'],'uncertain')
            self.assertIsNone(result['result']['operation']['result'])
            self.assertEqual(owner.execute(actor,'sessions.fork',args,authorize=lambda:actor),result)
            self.assertEqual(calls,['thread/fork'])
            self.assertEqual(effects,[])
