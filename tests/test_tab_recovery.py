"""Public workspace snapshot-to-restore contract with explicit native adapters."""
import tempfile
import unittest


class TabRecoveryTests(unittest.TestCase):
    def test_public_capture_preview_restore_retains_two_exact_conversations(self):
        from codex_wake.tab_recovery import TabRecovery
        class Runtime:
            def __init__(self):
                self.live=[dict(window_id='@1',index=1,name='one',logical_id=None,panes=[dict(pane_id='%1')]),
                           dict(window_id='@2',index=2,name='two',logical_id=None,panes=[dict(pane_id='%2')]),
                           dict(window_id='@3',index=3,name='notes',logical_id=None,panes=[dict(pane_id='%3')])]
                self.attached={'thread-one':'@1','thread-two':'@2'};self.calls=[]
            def context(self,workspace):return dict(workspace=workspace,identity='server-generation',windows=self.live)
            def capture(self,context):
                records={}
                for i,thread in enumerate(('thread-one','thread-two'),1):
                    records['@'+str(i)]=dict(kind='codex',identity=dict(runtime='codex',namespace='private-account',conversation_id=thread,root='/same-directory'),
                        profile=dict(cwd='/same-directory',app_server='unix:///native',codex_path='/qualified/codex',codex_home='/private/account',timeout=1),
                        native=dict(account='alice',home='/private/account',home_generation='stable',build_sha256='qualified'))
                records['@3']=dict(kind='noncoding')
                return records
            def mark(self,context,window,logical_id):
                next(v for v in self.live if v['window_id']==window)['logical_id']=logical_id
            def identity(self,record,context):return record['identity']
            def binding(self,record,context):return dict(state='ready' if record['identity']['conversation_id'] in self.attached else 'absent',window_id=self.attached.get(record['identity']['conversation_id']))
            def launch(self,record,context,guard):
                guard();wid='@'+str(10+len(self.calls));self.calls.append(record['identity']['conversation_id'])
                self.live.append(dict(window_id=wid,index=record['index'],name=record['name'],logical_id=None,panes=[dict(pane_id='%'+wid[1:])]))
                self.attached[record['identity']['conversation_id']]=wid
                return dict(window_id=wid,pane_id='%'+wid[1:])
        runtime=Runtime()
        with tempfile.TemporaryDirectory() as directory:
            owner=TabRecovery(directory,runtime=runtime)
            capture=owner.execute('tabs.recovery.capture',dict(workspace='saved',capture_id='nightly'))
            self.assertEqual(capture['status'],'captured')
            # Simulated process/server restart: both old IDs are deliberately reused
            # by unrelated shells. They must not be treated as conversation proof.
            runtime.live=[dict(window_id='@1',index=0,name='unrelated',logical_id=None,panes=[dict(pane_id='%1')])]
            runtime.attached={}
            restarted=TabRecovery(directory,runtime=runtime)
            preview=restarted.execute('tabs.recovery.preview',dict(capture_id='nightly',workspace='restored',restore_layout=True))
            self.assertEqual([r['status'] for r in preview['rows']],['restoreable','restoreable','preserved'])
            args=dict(capture_id='nightly',workspace='restored',restore_layout=True,intent='restore-once',expected_target=preview['target'])
            applied=restarted.execute('tabs.recovery.apply',args)
            self.assertEqual(applied['status'],'completed')
            self.assertEqual(runtime.calls,['thread-one','thread-two'])
            self.assertEqual(runtime.live[0]['name'],'unrelated')
            repeated=restarted.execute('tabs.recovery.apply',args)
            self.assertTrue(repeated['replayed'])
            self.assertEqual(runtime.calls,['thread-one','thread-two'])

    def test_uncertain_launch_fences_new_intents_and_never_replays(self):
        from codex_wake.tab_recovery import TabRecovery
        from codex_wake.managed_inventory import InventoryError
        class Runtime:
            calls=0
            captured=True
            def context(self,workspace):return dict(workspace=workspace,identity='server',windows=[dict(window_id='@1',index=1,name='saved',panes=[dict(pane_id='%1')])] if self.captured else [])
            def capture(self,context):return {'@1':dict(kind='codex',identity=dict(runtime='codex',namespace='a',conversation_id='exact',root='/tmp'),profile=dict(timeout=.1))}
            def mark(self,*args):pass
            def identity(self,record,context):return record['identity']
            def binding(self,*args):return dict(state='absent')
            def launch(self,record,context,guard):self.calls+=1;raise TimeoutError('effect unknown')
        runtime=Runtime()
        with tempfile.TemporaryDirectory() as directory:
            owner=TabRecovery(directory,runtime=runtime)
            owner.execute('tabs.recovery.capture',dict(workspace='original',capture_id='saved'))
            runtime.captured=False
            preview=owner.execute('tabs.recovery.preview',dict(workspace='new',capture_id='saved',restore_layout=True))
            args=dict(workspace='new',capture_id='saved',restore_layout=True,intent='original',expected_target=preview['target'])
            first=owner.execute('tabs.recovery.apply',args)
            self.assertEqual(first['rows'][0]['status'],'uncertain')
            self.assertEqual(owner.execute('tabs.recovery.apply',args)['rows'][0]['status'],'uncertain')
            self.assertEqual(runtime.calls,1)
            with self.assertRaises(InventoryError) as error:
                owner.execute('tabs.recovery.apply',dict(args,intent='different'))
            self.assertEqual(error.exception.code,'recovery_original_intent_required')
            self.assertEqual(runtime.calls,1)
