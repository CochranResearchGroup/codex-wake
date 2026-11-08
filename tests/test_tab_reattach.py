"""Public reattachment state machine; injected native evidence is not native acceptance."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import unittest
from codex_wake.controller_tab_adapters import TmuxAttachmentTransport
from codex_wake.managed_inventory import InventoryError


@unittest.skipUnless(shutil.which('tmux'), 'tmux unavailable')
class TabReattachTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.socket = str(self.root / 'tmux.sock')
        self.tmux('new-session', '-d', '-s', 'source', '-n', 'anchor', 'sleep 120')
        self.addCleanup(lambda: subprocess.run(['tmux','-S',self.socket,'kill-server'],capture_output=True))
        self.source_window = self.tmux('new-window','-d','-P','-F','#{window_id}','-t','$0:','-n','source','sleep 120')
        self.tmux('new-session','-d','-s','destination','-n','anchor','sleep 120')
        self.workspaces = {'source':dict(kind='byobu',transport=TmuxAttachmentTransport(self.socket,'$0')),
                           'destination':dict(kind='tmux',transport=TmuxAttachmentTransport(self.socket,'$1'))}
        self.runtime = FixtureRuntime(self)

    def tmux(self,*args):
        return subprocess.check_output(['tmux','-S',self.socket,*args],text=True).strip()

    def owner(self):
        from codex_wake.tab_reattach import TabReattach
        return TabReattach(self.root,workspaces=self.workspaces,host='fixture',environment='fixture',runtime=self.runtime)

    def preview(self, owner, retire_source=True):
        return owner.execute('tabs.reattach-preview',dict(workspace='source',
            expected_target=owner.lifecycle.inspect('source')['target'],window=self.source_window,
            destination='destination',expected_destination=owner.lifecycle.inspect('destination')['target'],force=True,retire_source=retire_source))

    def test_destination_identity_verified_before_retiring_source_and_replay(self):
        owner = self.owner()
        preview = self.preview(owner)
        self.assertEqual(preview['status'],'ready')
        self.assertIn(self.source_window,self.tmux('list-windows','-t','$0','-F','#{window_id}'))
        applied = owner.execute('tabs.reattach-apply',{'plan_id':preview['plan_id']})
        self.assertEqual(applied['status'],'applied')
        self.assertNotIn(self.source_window,self.tmux('list-windows','-t','$0','-F','#{window_id}'))
        self.assertTrue(self.runtime.source_present_during_verification)
        self.assertEqual(applied['identity']['conversation_id'],'same-conversation')
        again = self.owner().execute('tabs.reattach-apply',{'plan_id':preview['plan_id']})
        self.assertTrue(again['replayed'])
        self.assertEqual(self.runtime.launches,1)


    def test_default_retains_source_and_unknown_draft_blocks_retirement(self):
        owner=self.owner()
        ready=self.preview(owner,retire_source=False)
        applied=owner.execute('tabs.reattach-apply',{'plan_id':ready['plan_id']})
        self.assertEqual(applied['status'],'applied')
        self.assertTrue(applied['source_preserved'])
        self.assertFalse(applied['source_retired'])
        self.assertIn(self.source_window,self.tmux('list-windows','-t','$0','-F','#{window_id}'))
        self.runtime.safe=False
        held=self.preview(owner)
        self.assertEqual(held['status'],'held')
        self.assertEqual(held['reason'],'source_input_custody_unknown_or_nonempty')
        self.assertEqual(self.runtime.launches,1)

    def test_new_input_after_preview_prevents_launch(self):
        owner=self.owner()
        ready=self.preview(owner)
        self.runtime.safe=False
        with self.assertRaises(InventoryError) as caught:
            owner.execute('tabs.reattach-apply',{'plan_id':ready['plan_id']})
        self.assertEqual(caught.exception.code,'source_input_custody_unknown_or_nonempty')
        self.assertEqual(self.runtime.launches,0)

    def test_new_input_during_attachment_retains_source_and_never_relaunches(self):
        owner=self.owner()
        ready=self.preview(owner)
        verify=self.runtime.verify
        def changed(plan,handle):
            result=verify(plan,handle)
            self.runtime.safe=False
            return result
        self.runtime.verify=changed
        result=owner.execute('tabs.reattach-apply',{'plan_id':ready['plan_id']})
        self.assertEqual(result['status'],'uncertain')
        self.assertTrue(result['source_preserved'])
        self.assertFalse(result['source_retired'])
        self.assertEqual(result['reason'],'source_input_custody_unknown_or_nonempty')
        again=owner.execute('tabs.reattach-apply',{'plan_id':ready['plan_id']})
        self.assertEqual(again['launch_attempts'],1)
        self.assertEqual(self.runtime.launches,1)

    def test_destination_mismatch_retains_source_and_fences_new_plan(self):
        owner=self.owner()
        preview=self.preview(owner)
        self.runtime.mismatch=True
        unknown=owner.execute('tabs.reattach-apply',{'plan_id':preview['plan_id']})
        self.assertEqual(unknown['status'],'uncertain')
        self.assertTrue(unknown['source_preserved'])
        self.assertIn(self.source_window,self.tmux('list-windows','-t','$0','-F','#{window_id}'))
        owner.execute('tabs.reattach-apply',{'plan_id':preview['plan_id']})
        self.assertEqual(self.runtime.launches,1)
        another=self.preview(owner)
        with self.assertRaises(InventoryError) as caught:
            owner.execute('tabs.reattach-apply',{'plan_id':another['plan_id']})
        self.assertEqual(caught.exception.code,'reattach_original_plan_required')
        self.assertEqual(self.runtime.launches,1)

    def test_lost_launch_response_is_never_retried_and_source_remains(self):
        owner=self.owner()
        preview=self.preview(owner)
        self.runtime.fail_after_launch=True
        result=owner.execute('tabs.reattach-apply',{'plan_id':preview['plan_id']})
        self.assertEqual(result['status'],'uncertain')
        self.assertTrue(result['source_preserved'])
        resumed=self.owner().execute('tabs.reattach-apply',{'plan_id':preview['plan_id']})
        self.assertEqual(resumed['status'],'uncertain')
        self.assertEqual(self.runtime.launches,1)
        self.assertIn(self.source_window,self.tmux('list-windows','-t','$0','-F','#{window_id}'))

    def test_stale_destination_and_unsupported_capability_have_no_launch(self):
        owner=self.owner()
        preview=self.preview(owner)
        self.tmux('new-window','-d','-t','$1:','-n','manual-change','sleep 120')
        with self.assertRaises(InventoryError) as caught:
            owner.execute('tabs.reattach-apply',{'plan_id':preview['plan_id']})
        self.assertEqual(caught.exception.code,'stale_target')
        self.assertEqual(self.runtime.launches,0)
        self.runtime.supports=lambda destination,source:False
        unsupported=self.preview(owner)
        self.assertEqual(unsupported['status'],'unsupported')
        self.assertTrue(unsupported['source_preserved'])
        self.assertEqual(self.runtime.launches,0)


class FixtureRuntime:
    def __init__(self, fixture):
        self.fixture=fixture
        self.launches=0
        self.source_present_during_verification=False
        self.mismatch=False
        self.fail_after_launch=False
        self.safe=True

    def capture(self, workspace, window):
        return dict(identity=dict(runtime='codex',namespace='same-account',conversation_id='same-conversation',root=str(self.fixture.root)),
            profile=dict(codex_home=str(self.fixture.root),codex_path='/synthetic/codex',app_server='unix:///synthetic',timeout=2),
            process=dict(pid=window['panes'][0]['pid']),ui_safety=dict(known_empty=self.safe,private_input=False,queue_empty=True,controller_owned=True,process=dict(pid=window['panes'][0]['pid']),observed_at=time.time()),state='idle',health=dict(responsive=True,evidence='tui_main_loop_ack'))

    def supports(self, destination, source):
        return True

    def launch(self, plan, guard):
        guard()
        self.launches+=1
        wid=self.fixture.tmux('new-window','-d','-P','-F','#{window_id}','-t','$1:','-n',plan['name'],'sleep 120')
        if self.fail_after_launch:raise OSError('synthetic lost launch reply')
        return dict(window_id=wid)

    def verify(self, plan, handle):
        self.source_present_during_verification=plan['window']['window_id'] in self.fixture.tmux('list-windows','-t','$0','-F','#{window_id}')
        identity=dict(plan['source']['identity'])
        if self.mismatch:identity['namespace']='wrong-account'
        return dict(identity=identity,handle=handle,health=dict(responsive=True,evidence='tui_main_loop_ack'))
