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

    def test_native_expiry_still_renders_after_publisher_is_gone(self):
        from codex_wake.tab_format_expiry import expiring_options
        options={'window-status-format':' #I CX running #W ',
                 'window-status-current-format':'#[bold,underscore] #I CX running #W ',
                 'window-status-style':'fg=white,bg=blue',
                 'window-status-current-style':'fg=white,bg=blue,bold,underscore'}
        self.tmux('set-option','-t','$0','@wake-format-clock','%s')
        expired=expiring_options(options,observed_at=time.time()-21)
        for name,value in expired.items():self.tmux('set-option','-w','-t','@0',name,value)
        rendered=self.tmux('display-message','-p','-t','@0','#{E:window-status-format}')
        self.assertIn('STALE',rendered);self.assertIn('colour238',rendered)
        self.assertIn('kept name',rendered)
        self.assertNotIn('#(',expired['window-status-format'])

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
