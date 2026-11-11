"""Finite native formatting batches keep explicit/inherited custody and errors."""
import shutil
import subprocess
import time
import unittest
from unittest.mock import patch

import test_tab_formatting as fixture


@unittest.skipUnless(shutil.which('tmux'),'tmux unavailable')
class NativeFormattingBatchTests(unittest.TestCase):
    setUp=fixture.FormattingTests.setUp
    tmux=fixture.FormattingTests.tmux
    call=fixture.FormattingTests.call

    def test_cross_window_write_readback_preserves_literals_and_inheritance(self):
        self.tmux('new-window','-d','-t','fixture:','exec sleep 90')
        self.tmux('set-option','-g','window-status-style','fg=green,bg=black')
        deadline=time.monotonic()+5
        before=self.transport.formatting_batch([dict(action='read',window=wid) for wid in ('@0','@1')],deadline)
        self.assertFalse(before[0]['window-status-style']['explicit'])
        self.assertEqual(before[0]['window-status-style']['effective'],'fg=green,bg=black')
        value='literal comma, braces {} ; #W\nsecond line'
        requests=[dict(action='write',window='@0',values={'window-status-format':value,'window-status-style':'fg=blue'}),
                  dict(action='write',window='@1',values={'window-status-format':';','window-status-style':None})]
        commands=[];original=subprocess.run
        def counted(*args,**kwargs):commands.append(args[0]);return original(*args,**kwargs)
        with patch('subprocess.run',side_effect=counted):
            after=self.transport.formatting_batch(requests,deadline)
        self.assertEqual(len(commands),1)
        self.assertEqual(after[0]['window-status-format']['value'],value)
        self.assertEqual(after[0]['window-status-style']['parent'],'fg=green,bg=black')
        self.assertEqual(after[1]['window-status-format']['value'],';')
        self.assertFalse(after[1]['window-status-style']['explicit'])
        self.assertEqual(after[1]['window-status-style']['effective'],'fg=green,bg=black')

    def test_combined_read_keeps_manual_session_custody_before_window_effects(self):
        self.assertEqual(self.call('enable')['status'],'applied')
        before=self.tmux('show-options','-w','-t','@0')
        self.tmux('set-option','-t','$0','status-interval','1')
        self.call('configure',preset='graphite')
        commands=[];original=subprocess.run
        def counted(*args,**kwargs):commands.append(args[0]);return original(*args,**kwargs)
        with patch('subprocess.run',side_effect=counted):result=self.call('enable')
        self.assertEqual(result['status'],'partial')
        self.assertEqual(result['failures'],[dict(code='manual_override')])
        self.assertFalse(any('set-option' in command for command in commands))
        self.assertEqual(self.tmux('show-options','-w','-t','@0'),before)
        self.assertEqual(self.tmux('show-options','-v','-t','$0','status-interval').strip(),'1')

    def test_invalid_later_member_is_rejected_before_first_write(self):
        from codex_wake.managed_inventory import InventoryError
        original=self.tmux('show-options','-w','-t','@0')
        with self.assertRaises(InventoryError):
            self.transport.formatting_batch([dict(action='write',window='@0',values={'window-status-format':'changed'}),
                dict(action='write',window='@0',values={'pane-border-style':'fg=red'})],time.monotonic()+5)
        self.assertEqual(self.tmux('show-options','-w','-t','@0'),original)

    def test_disappeared_window_is_error_and_live_readback_remains_exact(self):
        self.tmux('new-window','-d','-t','fixture:','exec sleep 90')
        self.tmux('kill-window','-t','@1')
        results=self.transport.formatting_batch([dict(action='read',window='@1'),dict(action='read',window='@0')],time.monotonic()+5)
        self.assertEqual(results[0],dict(error=dict(code='stale_target')))
        self.assertIn('window-status-format',results[1])

    def test_failed_write_cohort_is_not_replayed(self):
        requests=[dict(action='write',window='@0',values={'window-status-format':'first native effect'}),
                  dict(action='write',window='@99999',values={'window-status-format':'missing target'})]
        commands=[];original=subprocess.run
        def counted(*args,**kwargs):commands.append(args[0]);return original(*args,**kwargs)
        with patch('subprocess.run',side_effect=counted):
            result=self.transport.formatting_batch(requests,time.monotonic()+5)
        self.assertEqual(sum('set-option' in command for command in commands),1)
        self.assertEqual(result[0]['window-status-format']['value'],'first native effect')
        self.assertEqual(result[1],dict(error=dict(code='stale_target')))
        self.assertEqual(self.tmux('show-options','-w','-v','-t','@0','window-status-format').strip(),'first native effect')

    def test_unselected_pane_replacement_loses_old_claims_before_next_write(self):
        from codex_wake.tab_format_monitor import refresh_formatting
        self.tmux('new-window','-d','-t','fixture:','exec sleep 90')
        wall=time.time();observed=dict(self.tabs.execute('tabs.list',{}),origin='daemon',projection_revision='first')
        def trait(value):return dict(value=value,status='observed',observed_at=wall,source_available=True)
        for resource in observed['resources']:
            resource.update(projection_revision=resource['window']['window_id']+'-first',evidence_revision='initial')
            resource['traits']=dict(panes=[dict(pane_id=resource['window']['panes'][0]['pane_id'],traits=dict(
                harness=trait('codex'),build=trait('stock'),activity=trait('running')))])
        self.assertEqual(refresh_formatting(self.root,observed,tabs=self.tabs)['status'],'completed')
        self.tmux('respawn-pane','-k','-t','%1','exec sleep 90')
        observed['projection_revision']='second'
        observed['resources'][0]['projection_revision']='@0-second'
        observed['resources'][0]['traits']['panes'][0]['traits']['activity']=trait('idle')
        self.assertEqual(refresh_formatting(self.root,observed,tabs=self.tabs)['status'],'completed')
        shown=self.tmux('display-message','-p','-t','@1','#{E:window-status-format}')
        self.assertNotIn('RUN',shown)
        self.assertNotIn('CX',shown)
        self.assertEqual(self.call('rollback')['status'],'rolled_back')

    def test_selective_read_only_inspection_keeps_complete_roster_and_default_fences(self):
        from codex_wake.tab_lifecycle import TabLifecycle
        self.tmux('new-window','-d','-t','fixture:','exec sleep 90')
        owner=TabLifecycle(self.root,workspaces=self.tabs.workspaces,host=self.tabs.host,environment=self.tabs.environment)
        selected=owner.inspect('work',window_ids={'@0'})['snapshot']
        self.assertEqual({window['window_id'] for window in selected['windows']},{'@0','@1'})
        self.assertIn('process_generation',selected['windows'][0]['panes'][0])
        self.assertNotIn('process_generation',selected['windows'][1]['panes'][0])
        full=owner.inspect('work')['snapshot']
        self.assertTrue(all('process_generation' in pane for window in full['windows'] for pane in window['panes']))

    def test_failed_source_loss_projection_does_not_extend_old_dynamic_lease(self):
        from types import SimpleNamespace
        from codex_wake.tab_format_monitor import refresh_formatting
        wall=time.time();observed=dict(self.tabs.execute('tabs.list',{}),origin='daemon',projection_revision='first')
        resource=observed['resources'][0]
        def trait(value):return dict(value=value,status='observed',observed_at=wall,source_available=True)
        resource.update(projection_revision='running',evidence_revision='first')
        resource['traits']=dict(panes=[dict(pane_id=resource['window']['panes'][0]['pane_id'],traits=dict(
            harness=trait('codex'),build=trait('stock'),activity=trait('running')))])
        self.assertEqual(refresh_formatting(self.root,observed,tabs=self.tabs)['status'],'completed')
        lease=self.tmux('show-options','-v','-t','$0','@wake-format-clock')
        observed['projection_revision']='lost';resource['projection_revision']='lost'
        resource['traits']['panes'][0]['traits']['activity']['source_available']=False
        original=subprocess.run
        def refused(*args,**kwargs):
            if 'set-option' in args[0] and '-w' in args[0]:raise OSError('fixture native write refused')
            return original(*args,**kwargs)
        clock=SimpleNamespace(time=lambda:wall+6,monotonic=time.monotonic,sleep=time.sleep)
        with patch('subprocess.run',side_effect=refused),patch('codex_wake.tab_formatting.time',clock):
            report=refresh_formatting(self.root,observed,tabs=self.tabs)
        self.assertEqual(report['status'],'partial')
        self.assertEqual(self.tmux('show-options','-v','-t','$0','@wake-format-clock'),lease)
