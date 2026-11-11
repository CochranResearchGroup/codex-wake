"""Explicit deletion at the public owner seam, using private native tmux."""
import subprocess
import tempfile
import unittest
from pathlib import Path
from codex_wake.controller_tabs import ControllerTabs


class SessionDeleteTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='wake-delete-')
        self.root=Path(self.temp.name)
        self.tabs=ControllerTabs(self.root,workspaces={},host='test',environment='fixture')
        self.source=self.tabs.execute('tabs.session.create',dict(name='source',start=True))['session']
        self.peer=self.tabs.execute('tabs.session.create',dict(name='peer',start=True))['session']
        self.sock=str(self.root/'terminal-sessions/tmux.sock')
        self.tmux('set-window-option','-g','automatic-rename','off')
    def tearDown(self):
        subprocess.run(['tmux','-S',self.sock,'kill-server'],capture_output=True)
        self.temp.cleanup()
    def tmux(self,*args):
        return subprocess.check_output(['tmux','-S',self.sock,*args],text=True).strip()
    def delete(self,**args):
        return self.tabs.execute('tabs.session.delete',dict(session=self.source['id'],**args))
    def test_explicit_termination_preserves_peer_process_births_and_tombstone(self):
        self.tmux('new-window','-d','-t','source')
        peer=self.tmux('list-panes','-s','-t','peer','-F','#{pane_id}:#{pane_pid}')
        peer_births=[r['window']['panes'] for r in self.tabs.execute('tabs.list',{})['resources'] if r['target']['workspace']==self.peer['workspace']]
        with self.assertRaisesRegex(ValueError,'explicit drain'):self.delete()
        result=self.delete(terminate=True)
        self.assertEqual(result['status'],'deleted')
        self.assertEqual([o['status'] for o in result['outcomes']],['terminated','terminated'])
        self.assertTrue(result['session']['deleted'])
        self.assertEqual(self.tmux('list-panes','-s','-t','peer','-F','#{pane_id}:#{pane_pid}'),peer)
        self.assertEqual([r['window']['panes'] for r in self.tabs.execute('tabs.list',{})['resources'] if r['target']['workspace']==self.peer['workspace']],peer_births)
        replacement=self.tabs.execute('tabs.session.create',dict(name='source'))['session']
        self.assertNotEqual(replacement['id'],self.source['id'])

    def test_drain_and_deleted_destination_rules_preserve_processes_and_retired_identity(self):
        from codex_wake.terminal_routing import TerminalRouting
        routing=TerminalRouting(self.root,tabs=self.tabs)
        rule=routing.execute('tabs.route.save',dict(name='to-source',destination='source',selection={'tabs':[]}))['rule']
        routing.execute('tabs.route.enable',dict(rule_id=rule['id']))
        before=self.tmux('list-panes','-s','-t','source','-F','#{pane_id}:#{pane_pid}')
        result=self.delete(destination='peer')
        self.assertEqual(result['status'],'deleted')
        self.assertEqual(result['outcomes'][0]['status'],'moved')
        self.assertIn(before,self.tmux('list-panes','-s','-t','peer','-F','#{pane_id}:#{pane_pid}'))
        retired=routing.execute('tabs.route.list',{})['rules'][0]
        self.assertFalse(retired['enabled'])
        self.assertEqual(retired['disabled_reason'],'destination_deleted')
        self.assertEqual(retired['revision'],rule['revision']+2)
        self.tabs.execute('tabs.session.create',dict(name='source'))
        with self.assertRaises(ValueError):routing.execute('tabs.route.enable',dict(rule_id=rule['id']))
        self.assertEqual(self.delete(plan_id=result['plan_id'])['status'],'deleted')

    def test_changing_titles_do_not_prevent_explicit_termination(self):
        from codex_wake.controller_tab_adapters import TmuxAttachmentTransport
        class LiveTitles(TmuxAttachmentTransport):
            sequence = 0
            def snapshot(self, deadline):
                self.sequence += 1
                self.command(deadline, 'select-pane', '-t', '%0', '-T', 'turn '+str(self.sequence))
                return super().snapshot(deadline)
        config=self.tabs.workspaces[self.source['workspace']]
        config['transport']=LiveTitles(self.sock, self.source['snapshot']['session_id'])
        peer=self.tmux('list-panes','-s','-t','peer','-F','#{pane_id}:#{pane_pid}')
        result=self.delete(terminate=True)
        self.assertEqual(result['status'],'deleted',result)
        self.assertEqual(result['outcomes'][0]['status'],'terminated')
        self.assertEqual(self.tmux('list-panes','-s','-t','peer','-F','#{pane_id}:#{pane_pid}'),peer)

    def test_lost_native_close_reply_reconciles_after_restart_without_replay(self):
        from unittest.mock import patch
        real_run=subprocess.run;sent=[]
        def lost_reply(command,*args,**kwargs):
            result=real_run(command,*args,**kwargs)
            if 'kill-window' in command:
                sent.append(command)
                raise KeyboardInterrupt('owner stopped after OS effect')
            return result
        with patch('subprocess.run',side_effect=lost_reply):
            with self.assertRaises(KeyboardInterrupt):self.delete(terminate=True)
        self.tabs=ControllerTabs(self.root,workspaces={},host='test',environment='fixture')
        result=self.delete(terminate=True)
        self.assertEqual(result['status'],'deleted')
        self.assertEqual(result['outcomes'][0]['status'],'terminated')
        self.assertEqual(len(sent),1)

    def test_uncertain_pre_effect_close_retains_definition_and_does_not_replay(self):
        from unittest.mock import patch
        real_run=subprocess.run;sent=[]
        def lost_reply(command,*args,**kwargs):
            if 'kill-window' in command:
                sent.append(command)
                raise subprocess.TimeoutExpired(command,10)
            return real_run(command,*args,**kwargs)
        with patch('subprocess.run',side_effect=lost_reply):result=self.delete(terminate=True)
        self.assertEqual(result['status'],'partial')
        self.assertEqual(result['outcomes'][0]['status'],'uncertain')
        self.assertEqual(self.tabs.execute('tabs.session.show',dict(session='source'))['session']['state'],'running')
        self.tabs=ControllerTabs(self.root,workspaces={},host='test',environment='fixture')
        with patch('subprocess.run',side_effect=lost_reply):again=self.delete(plan_id=result['plan_id'])
        self.assertEqual(again['outcomes'][0]['status'],'uncertain')
        self.assertEqual(len(sent),1)

    def test_crash_after_tombstone_reconciles_rule_cleanup_without_native_replay(self):
        import json
        import os
        from unittest.mock import patch
        from codex_wake.terminal_routing import TerminalRouting
        routing=TerminalRouting(self.root,tabs=self.tabs)
        routing.execute('tabs.route.save',dict(name='retired',destination='source',selection={'tabs':[]}))
        real_replace=os.replace
        def crash_after_commit(source,destination,*args,**kwargs):
            result=real_replace(source,destination,*args,**kwargs)
            if Path(destination)==self.root/'terminal-sessions/registry.json':
                value=json.loads(Path(destination).read_text())
                if value['sessions'][self.source['id']].get('deleted'):
                    raise KeyboardInterrupt('crash after durable tombstone')
            return result
        with patch('os.replace',side_effect=crash_after_commit):
            with self.assertRaises(KeyboardInterrupt):self.delete(terminate=True)
        self.tabs=ControllerTabs(self.root,workspaces={},host='test',environment='fixture')
        result=self.delete(terminate=True)
        self.assertEqual(result['status'],'deleted')
        rules=TerminalRouting(self.root,tabs=self.tabs).execute('tabs.route.list',{})['rules']
        self.assertEqual(rules[0]['disabled_reason'],'destination_deleted')

    def test_name_reentry_keeps_uncertain_frozen_intent_instead_of_replaying(self):
        from unittest.mock import patch
        real_run=subprocess.run;sent=[]
        def timeout(command,*args,**kwargs):
            if 'kill-window' in command:
                sent.append(command);raise subprocess.TimeoutExpired(command,10)
            return real_run(command,*args,**kwargs)
        with patch('subprocess.run',side_effect=timeout):
            first=self.tabs.execute('tabs.session.delete',dict(session='source',terminate=True))
            second=self.tabs.execute('tabs.session.delete',dict(session='source',terminate=True))
        self.assertEqual(first['plan_id'],second['plan_id'])
        self.assertEqual(len(sent),1)

    def test_partial_drain_retains_source_and_enabled_rules_without_uncertain_replay(self):
        from unittest.mock import patch
        from codex_wake.terminal_routing import TerminalRouting
        self.tmux('new-window','-d','-t','source')
        routing=TerminalRouting(self.root,tabs=self.tabs)
        rule=routing.execute('tabs.route.save',dict(name='retain',destination='source',selection={'tabs':[]}))['rule']
        routing.execute('tabs.route.enable',dict(rule_id=rule['id']))
        real_run=subprocess.run;sent=[]
        def timeout_second(command,*args,**kwargs):
            if 'move-window' in command:
                sent.append(command)
                if len(sent)>1:raise subprocess.TimeoutExpired(command,10)
            return real_run(command,*args,**kwargs)
        with patch('subprocess.run',side_effect=timeout_second):first=self.delete(destination='peer')
        self.assertEqual(first['status'],'partial')
        self.assertEqual([e['status'] for e in first['outcomes']],['moved','uncertain'])
        self.assertEqual(self.tabs.execute('tabs.session.show',dict(session='source'))['session']['tab_count'],1)
        self.assertTrue(routing.execute('tabs.route.list',{})['rules'][0]['enabled'])
        self.tabs=ControllerTabs(self.root,workspaces={},host='test',environment='fixture')
        with patch('subprocess.run',side_effect=timeout_second):second=self.delete(plan_id=first['plan_id'])
        self.assertEqual([e['status'] for e in second['outcomes']],['moved','uncertain'])
        self.assertEqual(len(sent),2)

    def test_rejected_drain_destination_does_not_poison_later_explicit_termination(self):
        with self.assertRaises(ValueError):self.delete(destination='missing')
        result=self.delete(terminate=True)
        self.assertEqual(result['status'],'deleted')
        self.assertEqual(result['mode'],'terminate')
