"""Tier cadence and failure semantics through public scheduled-check boundary."""
import unittest


class TieredChecksTests(unittest.TestCase):
    def test_health_background_is_per_exact_agent_and_explicit_bypasses_cadence(self):
        from codex_wake.tab_observation_checks import TieredChecks
        now=[0.0]; calls=[]
        checks=TieredChecks(monotonic=lambda:now[0])
        def probe():
            calls.append(now[0])
            return dict(value='responsive',status='observed',source='tui_main_loop_ack',observed_at=now[0])
        checks.run('health',('agent',1),probe)
        now[0]=59
        checks.run('health',('agent',1),probe)
        self.assertEqual(calls,[0])
        checks.run('health',('agent',1),probe,force=True)
        now[0]=60
        checks.run('health',('agent',2),probe)
        self.assertEqual(calls,[0,59,60])
        now[0]=119
        checks.run('health',('agent',1),probe)
        self.assertEqual(calls,[0,59,60,119])

    def test_error_cadence_redacts_and_failed_check_retains_only_attributable_detail(self):
        from codex_wake.tab_observation_checks import TieredChecks
        now=[0.0]; calls=[]
        checks=TieredChecks(monotonic=lambda:now[0])
        def error():
            calls.append(now[0])
            if now[0]>=5:
                return dict(value='unknown',status='unknown',source='none',reason='capture_failed')
            return dict(value='present',status='observed',source='current_visible_screen',
                        observed_at=123,message='Error: private fixture payload',location=dict(pane_id='%1',row=9))
        first=checks.run('errors',('pane',1),error)
        self.assertNotIn('private fixture payload',str(first))
        now[0]=4
        checks.run('errors',('pane',1),error)
        self.assertEqual(calls,[0])
        now[0]=5
        failed=checks.run('errors',('pane',1),error)
        self.assertEqual(failed['value'],'unknown')
        self.assertEqual(failed['last_observation']['value'],'present')
        self.assertEqual(failed['last_observation']['observed_at'],123)
        self.assertNotIn('private fixture payload',str(checks.status()))
        checks.configure(errors=False)
        self.assertEqual(checks.run('errors',('pane',1),error)['reason'],'check_disabled')
        self.assertEqual(calls,[0,5])

    def test_public_inventory_keeps_health_independent_and_explicit_checks_immediate(self):
        import os
        import tempfile
        import time
        from codex_wake.process import process_identity
        from codex_wake.tab_observation import ObservationCache
        birth=process_identity(os.getpid()); now=[0.0]; probes=[]; captures=[]
        def processes(pid,deadline):
            return [dict(process=dict(pid=pid,start_ticks=birth['start_time_ticks'],boot_id=birth['boot_id']),
                         executable='/fixture/codex',argv=['codex'],cwd='/tmp')],True
        def reader(root,**options):
            return dict(holds=[],sessions=[dict(target=dict(provider='codex',account='fixture',conversation_id='thread',
                build_sha256='fixture-build'),runtime_state='active',active_flags=[],cwd='/tmp',attachments=[dict(pane_id='%1',
                client_pid=os.getpid(),client_start_time_ticks=birth['start_time_ticks'])])])
        def health(root,row,**options):
            probes.append(now[0])
            return dict(observation=dict(status='responsive',evidence='tui_main_loop_ack',observed_at=42))
        class Screen:
            def visible_screen(self,pane,deadline):
                captures.append(now[0])
                return 'Error: synthetic private message'
        with tempfile.TemporaryDirectory() as directory:
            cache=ObservationCache(directory,process_probe=processes,session_reader=reader,
                                   health_probe=health,monotonic=lambda:now[0])
            snapshot=dict(server='fixture',session_id='$1',socket_identity=[1,2],windows=[dict(window_id='@1',name='fixture',
                panes=[dict(pane_id='%1',pid=os.getpid(),pane_title='thread',pane_current_path='/tmp')])])
            def observe(**options):
                return cache.observe('fixture',snapshot,transport=Screen(),privacy=lambda pane:'safe',
                                     deadline=time.monotonic()+1,**options)[0]['@1']['traits']
            self.assertEqual(observe()['health']['value'],'responsive')
            now[0]=5
            result=observe(dirty_panes=['%1'])
            self.assertEqual(probes,[0])
            self.assertEqual(captures,[0,5])
            self.assertNotIn('synthetic private message',str(result))
            cache.configure_checks(activity=False,health=True,errors=False)
            result=observe()
            self.assertEqual(result['activity']['value'],'unknown')
            self.assertEqual(result['health']['value'],'responsive')
            self.assertEqual(result['error']['reason'],'check_disabled')
            observe(explicit_checks=True)
            self.assertEqual(probes,[0,5])

    def test_dirty_idle_pane_gets_five_second_error_check_without_health_probe(self):
        import os
        import tempfile
        import time
        from codex_wake.process import process_identity
        from codex_wake.tab_observation import ObservationCache
        birth=process_identity(os.getpid());now=[0.0];captures=[];text=['']
        def processes(pid,deadline):
            return [dict(process=dict(pid=pid,start_ticks=birth['start_time_ticks'],boot_id=birth['boot_id']),
                         executable='/fixture/codex',argv=['codex'],cwd='/tmp')],True
        def reader(root,**options):
            return dict(holds=[],sessions=[dict(target=dict(provider='codex',account='fixture',conversation_id='thread'),
                runtime_state='idle',active_flags=[],cwd='/tmp',attachments=[dict(pane_id='%1',client_pid=os.getpid(),
                client_start_time_ticks=birth['start_time_ticks'])])])
        class Screen:
            def visible_screen(self,pane,deadline):
                captures.append(now[0]);return text[0]
        with tempfile.TemporaryDirectory() as directory:
            cache=ObservationCache(directory,process_probe=processes,session_reader=reader,monotonic=lambda:now[0])
            snapshot=dict(server='fixture',session_id='$1',socket_identity=[1,2],windows=[dict(window_id='@1',name='fixture',
                panes=[dict(pane_id='%1',pid=os.getpid(),pane_title='thread',pane_current_path='/tmp')])])
            def observe():
                return cache.observe('fixture',snapshot,transport=Screen(),privacy=lambda pane:'safe',
                    deadline=time.monotonic()+1)[0]['@1']['traits']['error']
            self.assertEqual(observe()['value'],'absent')
            now[0]=6;text[0]='Error: private fixture text'
            self.assertEqual(observe()['value'],'absent')
            cache.mark_dirty('fixture',['%1'])
            self.assertTrue(cache.has_dirty('fixture'))
            result=observe()
            self.assertEqual(result['value'],'present')
            self.assertEqual(captures,[0,6])
            self.assertNotIn('private fixture text',str(result))
            now[0]=37
            self.assertFalse(cache.has_dirty('fixture'))
