"""Bulk relocation at the public owner seam in disposable private tmux."""
import subprocess
import tempfile
import unittest
from pathlib import Path
from codex_wake.controller_tabs import ControllerTabs
from codex_wake.terminal_relocation import TerminalRelocation


class RelocationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='wake-relocate-')
        self.root=Path(self.temp.name)
        self.tabs=ControllerTabs(self.root,workspaces={},host='test',environment='fixture')
        self.source=self.tabs.execute('tabs.session.create',dict(name='source',start=True))['session']
        self.destination=self.tabs.execute('tabs.session.create',dict(name='destination',start=True))['session']
        self.sock=str(self.root/'terminal-sessions/tmux.sock')
        self.owner=TerminalRelocation(self.root,tabs=self.tabs)
    def tearDown(self):
        subprocess.run(['tmux','-S',self.sock,'kill-server'],capture_output=True)
        self.temp.cleanup()
    def tmux(self,*args):
        return subprocess.check_output(['tmux','-S',self.sock,*args],text=True).strip()
    def execute(self,verb,**args):
        return self.owner.execute('tabs.relocate.'+verb,args)
    def preview(self):
        return self.execute('preview',session='source',destination='destination')
    def test_last_tab_moves_all_panes_without_process_restart_and_retains_empty_source(self):
        self.tmux('split-window','-d','-t','source')
        before=self.tmux('list-panes','-s','-t','source','-F','#{pane_id}:#{pane_pid}')
        plan=self.preview()
        receipt=self.execute('apply',plan_id=plan['plan_id'])
        self.assertEqual(receipt['status'],'completed')
        self.assertEqual(receipt['outcomes'][0]['status'],'moved')
        self.assertIn(before,self.tmux('list-panes','-s','-t','destination','-F','#{pane_id}:#{pane_pid}'))
        self.assertEqual(self.tabs.execute('tabs.session.show',dict(session='source'))['session']['state'],'empty')
        self.assertEqual(self.execute('apply',plan_id=plan['plan_id'])['receipt_id'],receipt['receipt_id'])
    def test_empty_destination_and_undo_restore_last_tab_with_durable_routing_hold(self):
        self.tmux('kill-session','-t','destination')
        plan=self.preview()
        receipt=self.execute('apply',plan_id=plan['plan_id'])
        self.assertEqual(receipt['outcomes'][0]['status'],'moved')
        self.assertEqual(self.tmux('list-windows','-t','destination','-F','#{window_id}').count('\n'),0)
        undone=self.execute('undo',receipt_id=receipt['receipt_id'])
        self.assertEqual(undone['outcomes'][0]['status'],'undone')
        from codex_wake.terminal_tab_holds import TabHolds
        identity=receipt['outcomes'][0]['birth']['identity']
        self.assertEqual(TabHolds(self.root).get(identity)['receipt_id'],receipt['receipt_id'])
        self.assertTrue(TabHolds(self.root).resume(identity)['resumed'])
    def test_lost_reply_restart_reconciles_without_dispatching_again(self):
        plan=self.preview()
        transport=self.tabs.workspaces[self.source['workspace']]['transport']
        original=transport.command
        sent=[]
        def lose_reply(deadline,*args):
            result=original(deadline,*args)
            if args[0]=='move-window':
                sent.append(args)
                raise KeyboardInterrupt('owner died after native move')
            return result
        transport.command=lose_reply
        with self.assertRaises(KeyboardInterrupt):self.execute('apply',plan_id=plan['plan_id'])
        self.owner=TerminalRelocation(self.root,tabs=self.tabs)
        receipt=self.execute('status',plan_id=plan['plan_id'])
        self.assertEqual(receipt['outcomes'][0]['status'],'moved')
        self.execute('apply',plan_id=plan['plan_id'])
        self.assertEqual(len(sent),1)

    def test_undo_preserves_subsequent_manual_move_and_batch_retains_partial_success(self):
        self.tmux('new-window','-d','-t','source')
        third=self.tabs.execute('tabs.session.create',dict(name='third',start=True))['session']
        plan=self.preview()
        second=plan['outcomes'][1]['birth']['window_id']
        self.tmux('move-window','-d','-s',second,'-t','third:')
        receipt=self.execute('apply',plan_id=plan['plan_id'])
        self.assertEqual([e['status'] for e in receipt['outcomes']],['moved','held'])
        self.assertEqual(receipt['status'],'partial')
        first=receipt['outcomes'][0]['birth']['window_id']
        self.tmux('move-window','-d','-s',first,'-t','third:')
        undone=self.execute('undo',receipt_id=receipt['receipt_id'])
        self.assertEqual(undone['outcomes'][0]['status'],'skipped')
        self.assertIn(first,self.tmux('list-windows','-t','third','-F','#{window_id}'))

    def test_linked_selection_rejected_before_any_mutation(self):
        self.tmux('link-window','-d','-s','source:0','-t','destination:')
        with self.assertRaisesRegex(ValueError,'Linked windows'):self.preview()
    def test_preview_status_is_read_only_and_selection_freezes_saved_group_members(self):
        self.tmux('new-window','-d','-t','source')
        resources=self.tabs.execute('tabs.list',{})['resources']
        from codex_wake.tab_views import TabViews
        member=next(r for r in resources if r['target']['workspace']==self.source['workspace'])
        views=TabViews(self.root)
        views.execute('tabs.group-save',dict(name='chosen',members=[TabViews.identity(member)['id']]),resources=resources)
        plan=self.execute('preview',session='source',destination='destination',selection={'group':'chosen'})
        views.execute('tabs.group-save',dict(name='chosen',members=[]),resources=resources)
        self.assertEqual(self.execute('status',plan_id=plan['plan_id'])['status'],'preview')
        focus=self.tmux('display-message','-p','-t','destination','#{window_id}')
        receipt=self.execute('apply',plan_id=plan['plan_id'])
        self.assertEqual(len(receipt['outcomes']),1)
        self.assertEqual(receipt['outcomes'][0]['status'],'moved')
        self.assertEqual(self.tmux('display-message','-p','-t','destination','#{window_id}'),focus)

    def test_changed_whole_window_is_held_before_dispatch(self):
        plan=self.preview()
        self.tmux('split-window','-d','-t','source')
        receipt=self.execute('apply',plan_id=plan['plan_id'])
        self.assertEqual(receipt['outcomes'][0]['status'],'held')
        self.assertEqual(self.tmux('list-windows','-t','source','-F','#{window_id}'),plan['outcomes'][0]['birth']['window_id'])
    def test_host_automatic_relocation_does_not_hold_but_undo_always_holds(self):
        from codex_wake.terminal_tab_holds import TabHolds
        self.owner=TerminalRelocation(self.root,tabs=self.tabs,automatic=True)
        plan=self.preview()
        moved=self.execute('apply',plan_id=plan['plan_id'])
        identity=moved['outcomes'][0]['birth']['identity']
        self.assertIsNone(TabHolds(self.root).get(identity))
        self.execute('undo',receipt_id=moved['receipt_id'])
        self.assertIsNotNone(TabHolds(self.root).get(identity))

    def test_undo_multiple_tabs_after_recreating_the_emptied_original_session(self):
        self.tmux('new-window','-d','-t','source','sleep 60')
        self.tmux('kill-session','-t','destination')
        before=sorted(self.tmux('list-panes','-s','-t','source','-F','#{pane_id}:#{pane_pid}').splitlines())
        receipt=self.execute('apply',plan_id=self.preview()['plan_id'])
        self.assertEqual([r['status'] for r in receipt['outcomes']],['moved','moved'])
        undone=self.execute('undo',receipt_id=receipt['receipt_id'])
        self.assertEqual([r['status'] for r in undone['outcomes']],['undone','undone'])
        self.assertEqual(sorted(self.tmux('list-panes','-s','-t','source','-F','#{pane_id}:#{pane_pid}').splitlines()),before)

    def test_materializing_a_destination_never_runs_its_saved_launch_command(self):
        marker=self.root/'unwanted-agent-launch'
        self.tabs.execute('tabs.session.update',dict(session='destination',changes={'defaults':{'argv':['/bin/sh','-c','touch '+str(marker)+'; sleep 60']}}))
        self.tmux('kill-session','-t','destination')
        receipt=self.execute('apply',plan_id=self.preview()['plan_id'])
        self.assertEqual(receipt['outcomes'][0]['status'],'moved')
        self.assertFalse(marker.exists(),'Relocation launched a saved command instead of an inert owned container.')
