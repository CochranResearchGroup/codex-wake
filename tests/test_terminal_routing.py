"""Opt-in routing at its public owner seam with disposable native tmux."""
import subprocess
import tempfile
import unittest
from pathlib import Path
from codex_wake.controller_tabs import ControllerTabs
from codex_wake.terminal_routing import TerminalRouting


class RoutingTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='wake-routing-')
        self.root=Path(self.temp.name)
        self.tabs=ControllerTabs(self.root,workspaces={},host='test',environment='fixture')
        for name in ('source','destination','other'):
            self.tabs.execute('tabs.session.create',dict(name=name,start=True))
        self.sock=str(self.root/'terminal-sessions/tmux.sock')
        self.now=100.
        self.owner=TerminalRouting(self.root,tabs=self.tabs,clock=lambda:self.now)
    def tearDown(self):
        subprocess.run(['tmux','-S',self.sock,'kill-server'],capture_output=True)
        self.temp.cleanup()
    def tmux(self,*args):
        return subprocess.check_output(['tmux','-S',self.sock,*args],text=True).strip()
    def execute(self,verb,**args):
        return self.owner.execute('tabs.route.'+verb,args)
    def save(self,name='rule',destination='destination',**args):
        return self.execute('save',name=name,destination=destination,selection={'field':'harness','unknown':True},stability_seconds=5,**args)['rule']
    def test_enable_excludes_existing_births_but_routes_future_tabs_after_stability(self):
        rule=self.save()
        self.execute('enable',rule_id=rule['id'])
        self.assertEqual(self.execute('tick')['outcomes'],[])
        window=self.tmux('new-window','-d','-t','source','-P','-F','#{window_id}')
        self.assertEqual(self.execute('tick')['outcomes'][0]['status'],'stabilizing')
        self.now+=6
        self.owner=TerminalRouting(self.root,tabs=self.tabs,clock=lambda:self.now)
        outcomes=self.execute('tick')['outcomes']
        self.assertEqual(outcomes[0]['status'],'moved')
        self.assertEqual(self.tmux('display-message','-p','-t',window,'#{session_name}'),'destination')
        self.assertEqual(len(self.tmux('list-windows','-t','source').splitlines()),1)
    def test_priority_conflict_pins_and_holds_survive_restart_and_resume_is_not_unpin(self):
        first=self.save(priority=1)
        second=self.save('conflict','other',priority=1)
        self.execute('enable',rule_id=first['id'],include_existing=True)
        self.execute('enable',rule_id=second['id'],include_existing=True)
        result=self.execute('tick')['outcomes']
        self.assertTrue(result)
        self.assertTrue(all(r['reason']=='priority_conflict' for r in result))
        self.execute('pause',rule_id=second['id'])
        resources=self.tabs.execute('tabs.list',{})['resources']
        from codex_wake.tab_views import TabViews
        selection={'tabs':[TabViews.identity(resources[0])]}
        self.execute('pin',selection=selection)
        self.execute('hold',selection=selection,reason='operator choice')
        self.execute('resume',selection=selection)
        self.owner=TerminalRouting(self.root,tabs=self.tabs,clock=lambda:self.now)
        self.assertIn('pinned',[r.get('reason') for r in self.execute('tick')['outcomes']])
        self.execute('unpin',selection=selection)
        self.assertNotIn('pinned',[r.get('reason') for r in self.execute('tick')['outcomes']])

    def test_external_move_is_held_until_explicit_resume(self):
        rule=self.save()
        self.execute('enable',rule_id=rule['id'],include_existing=True)
        window=self.tmux('list-windows','-t','source','-F','#{window_id}')
        self.execute('tick')
        self.tmux('move-window','-d','-s',window,'-t','other:')
        self.now+=6
        self.owner=TerminalRouting(self.root,tabs=self.tabs,clock=lambda:self.now)
        result=self.execute('tick')['outcomes']
        self.assertIn('external_manual_move',[r.get('reason') for r in result])
        self.assertEqual(self.tmux('display-message','-p','-t',window,'#{session_name}'),'other')

    def test_invalid_controls_and_rule_values_never_enable_or_select_all(self):
        from codex_wake.managed_inventory import InventoryError
        for verb in ('pin','hold','resume','unpin'):
            with self.assertRaises(InventoryError):self.execute(verb)
        for field,value in [('priority',True),('stability_seconds',float('nan')),('stability_seconds',-1)]:
            arguments=dict(name='bad',destination='destination',selection={'field':'harness','unknown':True})
            arguments[field]=value
            with self.assertRaises(InventoryError):self.execute('save',**arguments)

    def test_interrupted_move_reconciles_original_plan_before_rerouting_and_does_not_create_manual_hold(self):
        from codex_wake.terminal_sessions import TerminalSessions
        source=TerminalSessions(self.root,tabs=self.tabs).resolve('source')
        rule=self.save()
        self.execute('enable',rule_id=rule['id'],include_existing=True)
        self.execute('tick');self.now+=6
        sent=[]
        from unittest.mock import patch
        from codex_wake.tab_organization import TmuxTransport
        system_command=TmuxTransport.command
        def lose_reply_any(instance,deadline,*args):
            result=system_command(instance,deadline,*args)
            if args[0]=='move-window':
                sent.append(args)
                raise KeyboardInterrupt('lost move acknowledgement')
            return result
        with patch.object(TmuxTransport,'command',lose_reply_any):
            with self.assertRaises(KeyboardInterrupt):self.execute('tick')
        self.owner=TerminalRouting(self.root,tabs=self.tabs,clock=lambda:self.now)
        result=self.execute('tick')
        self.assertEqual(result['pending'],[])
        self.assertEqual(len(sent),1)
        self.assertNotIn('external_manual_move',[r.get('reason') for r in result['outcomes']])

    def test_rule_updates_pause_continuous_mode_and_keep_stable_destination_identity(self):
        rule=self.save()
        self.execute('enable',rule_id=rule['id'],include_existing=True)
        saved=self.execute('save',rule_id=rule['id'],name='renamed',destination='other',selection=rule['selection'],priority=3)['rule']
        self.assertEqual(saved['id'],rule['id'])
        self.assertFalse(saved['enabled'])
        self.assertGreater(saved['revision'],rule['revision'])
        self.assertEqual(self.execute('show',name='renamed')['rule'],saved)
        self.assertEqual(len(self.execute('list')['rules']),1)
        self.execute('delete',rule_id=rule['id'])
        self.assertEqual(self.execute('list')['rules'],[])

    def test_stale_monitor_rows_cannot_accumulate_stability_and_backward_clock_restarts_delay(self):
        rule=self.save()
        self.execute('enable',rule_id=rule['id'],include_existing=True)
        resources=self.tabs.execute('tabs.list',{})['resources']
        self.owner.tick({'resources':resources})
        self.now+=6
        stale=[dict(r,monitor_unavailable=True) for r in resources]
        self.assertEqual(self.owner.tick({'resources':stale})['outcomes'],[])
        self.now=50
        result=self.owner.tick({'resources':resources})
        self.assertTrue(all(r['status']=='stabilizing' for r in result['outcomes']))

    def test_lowest_priority_wins_and_renamed_destination_keeps_identity(self):
        first=self.save(priority=1)
        later=self.save('later','other',priority=20)
        self.execute('enable',rule_id=first['id'],include_existing=True)
        self.execute('enable',rule_id=later['id'],include_existing=True)
        window=self.tmux('list-windows','-t','source','-F','#{window_id}')
        self.tabs.execute('tabs.session.update',dict(session='destination',changes={'name':'renamed'}))
        self.execute('tick');self.now+=6
        self.execute('tick')
        self.assertEqual(self.tmux('display-message','-p','-t',window,'#{session_name}'),'renamed')
        self.assertEqual(self.execute('show',rule_id=first['id'])['rule']['destination'],first['destination'])

    def test_deleted_destination_disables_rule_and_never_rebinds_reused_name(self):
        rule=self.save()
        self.execute('enable',rule_id=rule['id'],include_existing=True)
        self.tmux('kill-session','-t','destination')
        self.tabs.execute('tabs.session.delete',dict(session='destination'))
        self.tabs.execute('tabs.session.create',dict(name='destination',start=True))
        self.execute('tick')
        saved=self.execute('show',rule_id=rule['id'])['rule']
        self.assertFalse(saved['enabled'])
        self.assertEqual(saved['disabled_reason'],'destination_deleted')
    def test_service_owned_monitor_routes_private_sessions_with_existing_daemon(self):
        import json
        import time
        from codex_wake.tab_monitor import TabMonitor
        from codex_wake.terminal_sessions import TerminalSessions
        sessions=TerminalSessions(self.root,tabs=self.tabs).inventory()
        config=self.root/'controller-tabs.json'
        config.write_text(json.dumps(dict(schema_version=1,workspaces={s['name']:dict(kind='tmux',socket_path=self.sock,session_id=s['native_session_id']) for s in sessions})))
        config.chmod(0o600)
        window=self.tmux('list-windows','-t','source','-F','#{window_id}')
        rule=self.execute('save',name='monitor',destination='destination',selection={'field':'harness','unknown':True},stability_seconds=0)['rule']
        self.execute('enable',rule_id=rule['id'],include_existing=True)
        monitor=TabMonitor(self.root)
        try:
            started=monitor.execute('tabs.monitor.start',dict(interval=.2,probe_timeout=.5,cycle_timeout=4,stale_after=10))
            self.assertIn('tab-routing-v1',started['monitor']['capabilities'])
            deadline=time.monotonic()+8
            while True:
                status=monitor.execute('tabs.monitor.status',{})
                routing=status['monitor'].get('last_routing')
                # A partial cycle may hold one tab before another cycle moves it.
                if routing and self.tmux('display-message','-p','-t',window,'#{session_name}')=='destination':
                    break
                self.assertLess(time.monotonic(),deadline,status)
            self.assertEqual(self.tmux('display-message','-p','-t',window,'#{session_name}'),'destination')
            self.assertEqual(monitor.execute('tabs.monitor.start',{})['monitor']['process'],started['monitor']['process'])
        finally:
            monitor.execute('tabs.monitor.stop',{'timeout':2})
    def test_public_controller_rules_use_management_target_fences_and_reject_implicit_all_tabs(self):
        from codex_wake.terminal_sessions import TerminalSessions
        from codex_wake.managed_inventory import InventoryError
        target=TerminalSessions(self.root,tabs=self.tabs).target()
        result=self.tabs.execute('tabs.route.save',dict(name='public',destination='destination',selection={'field':'harness','unknown':True},expected_target=target))
        self.assertFalse(result['rule']['enabled'])
        with self.assertRaises(InventoryError) as stale:
            self.tabs.execute('tabs.route.pause',dict(rule_id=result['rule']['id'],expected_target=target))
        self.assertEqual(stale.exception.code,'stale_target')
        with self.assertRaises(InventoryError):self.tabs.execute('tabs.route.pin',{})
        plan=self.tabs.execute('tabs.relocate.preview',dict(session='source',destination='destination'))
        receipt=self.tabs.execute('tabs.relocate.apply',{'plan_id':plan['plan_id']})
        held=self.tabs.execute('tabs.route.status',{})['holds']
        self.assertIn(receipt['receipt_id'],[h['receipt_id'] for h in held])

    def test_expired_monitor_tick_cannot_begin_a_native_move(self):
        import time
        rule=self.execute('save',name='bounded',destination='destination',selection={'field':'harness','unknown':True},stability_seconds=0)['rule']
        self.execute('enable',rule_id=rule['id'],include_existing=True)
        before=self.tmux('list-windows','-t','source','-F','#{window_id}:#{pane_pid}')
        result=self.owner.tick({'resources':self.tabs.execute('tabs.list',{})['resources']},deadline=time.monotonic()-1)
        self.assertEqual(result['reason'],'cycle_deadline')
        self.assertEqual(before,self.tmux('list-windows','-t','source','-F','#{window_id}:#{pane_pid}'))

    def test_existing_nonmatch_does_not_become_eligible_without_include_existing(self):
        from copy import deepcopy
        rule=self.execute('save',name='later-health',destination='destination',selection={'field':'health','eq':'responsive'},stability_seconds=5)['rule']
        enabled=self.execute('enable',rule_id=rule['id'])
        self.assertEqual(enabled['existing_matches'],[])
        resource=next(r for r in self.tabs.execute('tabs.list',{})['resources'] if r['target']['workspace']==next(k for k,v in self.tabs.workspaces.items() if v.get('label')=='source'))
        observed=deepcopy(resource)
        observed['traits']['traits']['health']={'value':'responsive','status':'observed','freshness':'fresh'}
        # Host-supplied monitor observations change; native tab/process birth does not.
        self.assertEqual(self.owner.tick({'resources':[observed]})['outcomes'],[])
        self.now+=6
        self.assertEqual(self.owner.tick({'resources':[observed]})['outcomes'],[])
        self.assertEqual(self.tmux('display-message','-p','-t',resource['window']['window_id'],'#{session_name}'),'source')
        self.execute('enable',rule_id=rule['id'],include_existing=True)
        self.assertEqual(self.owner.tick({'resources':[observed]})['outcomes'][0]['status'],'stabilizing')
        self.now+=6
        self.assertEqual(self.owner.tick({'resources':[observed]})['outcomes'][0]['status'],'moved')
