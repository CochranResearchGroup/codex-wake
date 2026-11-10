"""Automatic formatting and daemon-loss expiry at native/public seams."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import unittest

from codex_wake.controller_tab_adapters import TmuxAttachmentTransport
from codex_wake.controller_tabs import ControllerTabs


@unittest.skipUnless(shutil.which('tmux'),'tmux unavailable')
class FormattingMonitorTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.socket=str(self.root/'tmux.sock')
        self.tmux('new-session','-d','-s','fixture','-n','kept name','exec sleep 90')
        self.addCleanup(lambda:self.tmux('kill-server',check=False))
        self.transport=TmuxAttachmentTransport(self.socket,'$0')
        self.tabs=ControllerTabs(self.root,workspaces={'work':dict(kind='tmux',transport=self.transport)},host='test',environment='local')

    def tmux(self,*args,check=True):
        return subprocess.run(['tmux','-S',self.socket,*args],text=True,capture_output=True,check=check,timeout=5).stdout

    def test_publisher_lease_expires_dynamic_cue_without_dimming_type_or_name(self):
        from codex_wake.tab_format_expiry import expiring_options
        from codex_wake.tab_format_projection import project
        def trait(value):return dict(value=value,status='observed',observed_at=time.time(),source_available=True)
        resource=dict(traits=dict(panes=[dict(traits=dict(harness=trait('codex'),build=trait('stock'),activity=trait('running')))]))
        shown=project(resource,dict(preset='slate',_source_lease=True))
        options=expiring_options(shown['options'],observed_at=time.time(),shared_lease=True,fallback_styles=shown['fallback_styles'])
        self.tmux('set-option','-t','$0','@wake-format-clock',str(int(time.time()+20)))
        for name,value in options.items():self.tmux('set-option','-w','-t','@0',name,value)
        active=self.tmux('display-message','-p','-t','@0','#{E:window-status-format}')
        self.assertIn('*',active)
        self.tmux('set-option','-t','$0','@wake-format-clock',str(int(time.time()-1)))
        expired=self.tmux('display-message','-p','-t','@0','#{E:window-status-format}')
        self.assertNotIn('*',expired)
        self.assertNotIn('STALE',expired)
        self.assertNotIn('dim',expired)
        self.assertIn('CX',expired)
        self.assertIn('kept name',expired)
        self.assertEqual(self.tmux('show-options','-w','-v','-t','@0','window-status-style').strip(),shown['options']['window-status-style'])

    def test_public_monitor_automatically_decorates_then_rollback_holds(self):
        from codex_wake.tab_monitor import TabMonitor
        config=self.root/'controller-tabs.json'
        config.write_text(json.dumps(dict(schema_version=1,workspaces={'work':dict(kind='tmux',socket_path=self.socket,session_id='$0')})));config.chmod(0o600)
        self.tmux('set-option','-t','$0','status-interval','0')
        monitor=TabMonitor(self.root)
        monitor.execute('tabs.monitor.start',dict(interval=.2,probe_timeout=.8,cycle_timeout=2,stale_after=20))
        self.addCleanup(lambda:monitor.execute('tabs.monitor.stop',{}))
        until=time.monotonic()+5
        while not self.tmux('show-options','-w','-v','-t','@0','window-status-format'):
            self.assertLess(time.monotonic(),until,'automatic decoration never appeared');time.sleep(.02)
        self.assertEqual(self.tmux('show-options','-v','-t','$0','status-interval').strip(),'5')
        self.tabs.execute('tabs.format.rollback',dict(workspace='work'))
        deadline=time.monotonic()+5
        while True:
            report=monitor.execute('tabs.monitor.status',{})
            rows=(report['monitor'].get('last_formatting') or {}).get('workspaces',[])
            if any(
                    row.get('workspace')=='work' and row.get('status')=='disabled' for row in rows):
                break
            self.assertLess(time.monotonic(),deadline,
                            ('no completed monitor cycle consumed rollback',report['monitor'].get('last_formatting')))
            time.sleep(.02)
        self.assertEqual(self.tmux('show-options','-w','-v','-t','@0','window-status-format'),'')
        self.assertEqual(self.tmux('show-options','-v','-t','$0','status-interval').strip(),'0')
        self.assertNotIn('@wake-format-clock',self.tmux('show-options','-t','$0'))
        report=monitor.execute('tabs.monitor.status',{})
        self.assertIn('last_formatting',report['monitor'])
        self.assertFalse(report['application_effects'])

    def test_unchanged_projection_skips_window_commands_and_source_loss_clears_cues(self):
        from unittest.mock import patch
        from codex_wake.tab_format_monitor import refresh_formatting
        self.tmux('new-window','-d','-t','fixture:','exec sleep 90')
        observed=self.tabs.execute('tabs.list',{})
        def trait(value):return dict(value=value,status='observed',observed_at=time.time(),source_available=True)
        for resource in observed['resources']:
            resource['traits']=dict(panes=[dict(pane_id=resource['window']['panes'][0]['pane_id'],
                traits=dict(harness=trait('codex'),build=trait('stock'),activity=trait('running')))])
        self.tabs.execute('tabs.format.configure',dict(workspace='work',preset='slate'))
        self.assertEqual(refresh_formatting(self.root,observed,tabs=self.tabs)['status'],'completed')
        original=subprocess.run;commands=[]
        def counted(*args,**kwargs):
            commands.append(args[0]);return original(*args,**kwargs)
        with patch('subprocess.run',side_effect=counted):
            repeated=dict(observed,resources=[dict(resource,monitor_observed_at=time.time()+5) for resource in observed['resources']])
            self.assertEqual(refresh_formatting(self.root,repeated,tabs=self.tabs)['status'],'completed')
        self.assertFalse(any('show-options' in command and '-w' in command for command in commands))
        self.assertFalse(any('set-option' in command and '-w' in command for command in commands))
        lost=dict(observed,resources=[dict(observed['resources'][0],monitor_unavailable=True)],
                  unavailable=[dict(workspace='work',reason='source_lost')])
        refresh_formatting(self.root,lost,tabs=self.tabs)
        for wid in ('@0','@1'):
            rendered=self.tmux('display-message','-p','-t',wid,'#{E:window-status-format}')
            self.assertIn('CX',rendered)
            self.assertNotIn('*',rendered)
            self.assertNotIn('STALE',rendered)
        self.tabs.execute('tabs.format.rollback',dict(workspace='work'))
        self.assertNotIn('@wake-format-clock',self.tmux('show-options','-t','$0'))

    def test_refresh_uses_existing_sample_and_reports_unavailable_without_extending_ttl(self):
        from codex_wake.tab_format_monitor import refresh_formatting
        observed=self.tabs.execute('tabs.list',{})
        result=refresh_formatting(self.root,observed,tabs=self.tabs)
        self.assertEqual(result['status'],'completed')
        first=self.tmux('show-options','-w','-v','-t','@0','window-status-format')
        unavailable=dict(resources=[dict(r,monitor_unavailable=True) for r in observed['resources']],
                         unavailable=[dict(workspace='work',reason='probe_deadline')])
        result=refresh_formatting(self.root,unavailable,tabs=self.tabs)
        self.assertEqual(result['status'],'partial')
        self.assertEqual(result['workspaces'][0]['code'],'probe_deadline')
        self.assertEqual(self.tmux('show-options','-w','-v','-t','@0','window-status-format'),first)

    def test_unchanged_event_tick_defers_native_io_but_policy_change_is_immediate(self):
        from unittest.mock import patch
        from codex_wake.tab_format_monitor import refresh_formatting
        observed=self.tabs.execute('tabs.list',{})
        self.assertEqual(refresh_formatting(self.root,observed,tabs=self.tabs)['status'],'completed')
        commands=[];original=subprocess.run
        def counted(*args,**kwargs):
            commands.append(args[0]);return original(*args,**kwargs)
        repeated=dict(observed,resources=[dict(resource,monitor_observed_at=time.time()+1) for resource in observed['resources']])
        with patch('subprocess.run',side_effect=counted):
            self.assertEqual(refresh_formatting(self.root,repeated,tabs=self.tabs)['status'],'completed')
        self.assertEqual(commands,[])
        def trait(value):return dict(value=value,status='observed',observed_at=time.time(),source_available=True)
        changed=dict(observed,resources=[dict(resource,traits=dict(panes=[dict(
            pane_id=resource['window']['panes'][0]['pane_id'],traits=dict(
                harness=trait('codex'),build=trait('stock'),activity=trait('running')))]))
            for resource in observed['resources']])
        self.assertEqual(refresh_formatting(self.root,changed,tabs=self.tabs)['status'],'completed')
        self.assertIn('RUN',self.tmux('display-message','-p','-t','@0','#{E:window-status-format}'))
        changed['resources'][0]['traits']['panes'][0]['traits']['activity']['source_available']=False
        self.assertEqual(refresh_formatting(self.root,changed,tabs=self.tabs)['status'],'completed')
        self.assertNotIn('RUN',self.tmux('display-message','-p','-t','@0','#{E:window-status-format}'))
        self.tabs.execute('tabs.format.rollback',dict(workspace='work'))
        report=refresh_formatting(self.root,repeated,tabs=self.tabs)
        self.assertTrue(any(row['status']=='disabled' for row in report['workspaces']))

    def test_idle_projection_renews_before_shared_publisher_lease_can_expire(self):
        from types import SimpleNamespace
        from unittest.mock import patch
        from codex_wake.tab_format_monitor import refresh_formatting
        observed=self.tabs.execute('tabs.list',{})
        self.assertEqual(refresh_formatting(self.root,observed,tabs=self.tabs)['status'],'completed')
        now=time.monotonic();wall=time.time();commands=[];original=subprocess.run
        def counted(*args,**kwargs):
            commands.append(args[0]);return original(*args,**kwargs)
        # Substitute only the scheduler clock boundary, leaving native wall-clock
        # lease evaluation and transport deadlines on their real system clocks.
        with patch('codex_wake.tab_format_monitor.time',SimpleNamespace(monotonic=lambda:now+6)),patch('subprocess.run',side_effect=counted):
            result=refresh_formatting(self.root,observed,tabs=self.tabs)
        self.assertEqual(result['status'],'completed')
        self.assertFalse(commands,'Quiet projection need not perform native IO at six seconds.')
        clock=SimpleNamespace(time=lambda:wall+11,monotonic=time.monotonic,sleep=time.sleep)
        with patch('codex_wake.tab_format_monitor.time',SimpleNamespace(monotonic=lambda:now+11)),patch('codex_wake.tab_formatting.time',clock),patch('subprocess.run',side_effect=counted):
            result=refresh_formatting(self.root,observed,tabs=self.tabs)
        self.assertEqual(result['status'],'completed')
        self.assertTrue(commands)
        lease=int(self.tmux('show-options','-v','-t','$0','@wake-format-clock'))
        self.assertGreater(lease,wall+29)
        self.assertLessEqual(lease,wall+31)

    def test_trusted_revision_lease_renewal_avoids_repeated_physical_inventory(self):
        from types import SimpleNamespace
        from unittest.mock import patch
        from codex_wake.tab_format_monitor import refresh_formatting
        observed=dict(self.tabs.execute('tabs.list',{}),origin='daemon',projection_revision='fixture-one')
        for resource in observed['resources']:
            resource['projection_revision']='window-one'
            resource['evidence_revision']='evidence-one'
        self.assertEqual(refresh_formatting(self.root,observed,tabs=self.tabs)['status'],'completed')
        now=time.monotonic();commands=[];original=subprocess.run
        def counted(*args,**kwargs):
            commands.append(args[0]);return original(*args,**kwargs)
        with patch('codex_wake.tab_format_monitor.time',SimpleNamespace(monotonic=lambda:now+11,time=time.time)),patch('subprocess.run',side_effect=counted):
            result=refresh_formatting(self.root,observed,tabs=self.tabs)
        self.assertEqual(result['status'],'completed')
        self.assertFalse(any('list-panes' in command for command in commands),commands)
        self.assertTrue(any('show-options' in command for command in commands))
        self.assertLessEqual(len(commands),2)

    def test_failed_quiet_renewal_retries_on_next_tick_before_twenty_second_expiry(self):
        from types import SimpleNamespace
        from unittest.mock import patch
        from codex_wake.tab_format_monitor import refresh_formatting
        observed=dict(self.tabs.execute('tabs.list',{}),origin='daemon',projection_revision='steady')
        for resource in observed['resources']:resource['projection_revision']='window'
        self.assertEqual(refresh_formatting(self.root,observed,tabs=self.tabs)['status'],'completed')
        mono=time.monotonic();wall=time.time();original=self.transport.formatting
        def unavailable(action,arguments,deadline):
            if action=='read-session':raise OSError('temporary native read failure')
            return original(action,arguments,deadline)
        self.transport.formatting=unavailable
        with patch('codex_wake.tab_format_monitor.time',SimpleNamespace(monotonic=lambda:mono+11,time=time.time)):
            report=refresh_formatting(self.root,observed,tabs=self.tabs)
        self.assertEqual(report['status'],'partial')
        self.transport.formatting=original
        clock=SimpleNamespace(time=lambda:wall+12,monotonic=time.monotonic,sleep=time.sleep)
        with patch('codex_wake.tab_format_monitor.time',SimpleNamespace(monotonic=lambda:mono+12,time=time.time)),patch('codex_wake.tab_formatting.time',clock):
            report=refresh_formatting(self.root,observed,tabs=self.tabs)
        self.assertEqual(report['status'],'completed')
        lease=int(self.tmux('show-options','-v','-t','$0','@wake-format-clock'))
        self.assertGreater(lease,wall+30)
        self.assertLessEqual(lease,wall+32)

    def test_trusted_revision_keeps_native_manual_custody_audit(self):
        from types import SimpleNamespace
        from unittest.mock import patch
        from codex_wake.tab_format_monitor import refresh_formatting
        observed=dict(self.tabs.execute('tabs.list',{}),origin='daemon',projection_revision='fixture-one')
        for resource in observed['resources']:
            resource['projection_revision']='window-one'
            resource['evidence_revision']='evidence-one'
        self.assertEqual(refresh_formatting(self.root,observed,tabs=self.tabs)['status'],'completed')
        self.tmux('set-option','-w','-t','@0','window-status-format','manual style #W')
        mono=time.monotonic();wall=time.time()
        monitor_clock=SimpleNamespace(monotonic=lambda:mono+61,time=lambda:wall+61)
        formatting_clock=SimpleNamespace(monotonic=time.monotonic,time=lambda:wall+61,sleep=time.sleep)
        with patch('codex_wake.tab_format_monitor.time',monitor_clock),patch('codex_wake.tab_formatting.time',formatting_clock):
            result=refresh_formatting(self.root,observed,tabs=self.tabs)
        self.assertEqual(result['status'],'partial')
        self.assertTrue(any(failure['code']=='manual_override' for row in result['workspaces'] for failure in row.get('failures',[])))
        self.assertEqual(self.tmux('show-options','-w','-v','-t','@0','window-status-format').strip(),'manual style #W')

    def test_expired_trusted_revision_cannot_retain_intermittent_error(self):
        from types import SimpleNamespace
        from unittest.mock import patch
        from codex_wake.tab_format_monitor import refresh_formatting
        wall=time.time();mono=time.monotonic()
        observed=dict(self.tabs.execute('tabs.list',{}),origin='daemon',projection_revision='fixture-one',projection_valid_until=wall+20)
        for resource in observed['resources']:
            resource.update(projection_revision='window-one',evidence_revision='evidence-one',projection_valid_until=wall+20)
            resource['traits']=dict(panes=[dict(pane_id=resource['window']['panes'][0]['pane_id'],traits=dict(
                harness=dict(value='codex',status='observed',observed_at=wall),
                build=dict(value='stock',status='observed',observed_at=wall),
                activity=dict(value='idle',status='observed',observed_at=wall,source_available=True),
                error=dict(value='present',status='observed',observed_at=wall,redacted_message='redacted fixture')))])
        self.assertEqual(refresh_formatting(self.root,observed,tabs=self.tabs)['status'],'completed')
        self.assertIn('ERR',self.tmux('show-options','-w','-v','-t','@0','window-status-format'))
        monitor_clock=SimpleNamespace(monotonic=lambda:mono+21,time=lambda:wall+21)
        formatting_clock=SimpleNamespace(monotonic=time.monotonic,time=lambda:wall+21,sleep=time.sleep)
        with patch('codex_wake.tab_format_monitor.time',monitor_clock),patch('codex_wake.tab_formatting.time',formatting_clock):
            result=refresh_formatting(self.root,observed,tabs=self.tabs)
        self.assertEqual(result['status'],'completed')
        self.assertNotIn('ERR',self.tmux('show-options','-w','-v','-t','@0','window-status-format'))
        inspected=self.tabs.execute('tabs.format.inspect',dict(workspace='work'))['record']['windows']['@0']['projection']
        self.assertEqual(inspected['state'],'idle')
        self.assertEqual(inspected['details']['panes'][0]['attention']['error']['value'],'present')

    def test_expired_metadata_frame_loads_resources_before_legacy_key(self):
        import copy
        from codex_wake.tab_format_monitor import refresh_formatting
        observed=self.tabs.execute('tabs.list',{});wall=time.time();loads=[]
        def frame(state):
            metadata=dict(origin='daemon',projection_revision='expired',projection_valid_until=wall-1)
            def load():
                loads.append(state)
                metadata['resources']=copy.deepcopy(observed['resources'])
                for resource in metadata['resources']:
                    resource['traits']=dict(panes=[dict(pane_id=resource['window']['panes'][0]['pane_id'],traits=dict(
                        harness=dict(value='codex',status='observed',observed_at=wall),
                        build=dict(value='stock',status='observed',observed_at=wall),
                        activity=dict(value=state,status='observed',observed_at=wall,source_available=True)))])
            return metadata,load
        first,load=frame('idle')
        self.assertEqual(refresh_formatting(self.root,first,tabs=self.tabs,resources_loader=load)['status'],'completed')
        second,load=frame('running')
        self.assertEqual(refresh_formatting(self.root,second,tabs=self.tabs,resources_loader=load)['status'],'completed')
        self.assertEqual(loads,['idle','running'])
        self.assertIn('RUN',self.tmux('display-message','-p','-t','@0','#{E:window-status-format}'))
