"""Monitor mutation replies fit the existing retained-operation size boundary."""
import contextlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import unittest


@unittest.skipUnless(shutil.which('tmux'),'tmux unavailable')
class MonitorControlTests(unittest.TestCase):
    def test_large_inventory_does_not_make_control_effects_uncertain(self):
        from codex_wake.cli import run
        from codex_wake.tab_monitor import TabMonitor
        from codex_wake.tab_observer import TabObserver
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);tmux=['tmux','-S',str(root/'tmux.sock')]
            subprocess.run([*tmux,'new-session','-d','-s','fixture','sleep 60'],check=True)
            for _ in range(99):
                subprocess.run([*tmux,'new-window','-d','-t','fixture','sleep 60'],check=True)
            path=root/'controller-tabs.json'
            path.write_text(json.dumps(dict(schema_version=1,workspaces=dict(fixture=dict(
                kind='tmux',socket_path=str(root/'tmux.sock'),session_id='$0')))));path.chmod(0o600)
            monitor=TabMonitor(root)
            observer=TabObserver(root)
            try:
                snapshot=observer.tick(deadline=time.monotonic()+10)
                self.assertEqual(len(snapshot['resources']),100)
                snapshot['origin']='manual'
                cached=root/'tab-monitor'/'snapshot.json'
                cached.write_text(json.dumps(snapshot));cached.chmod(0o600)
                full=monitor.execute('tabs.monitor.status',{})
                self.__class__.full_status_bytes=len(json.dumps(full).encode())
                self.__class__.control_result_bytes={}
                self.assertGreater(self.full_status_bytes,262144)
                self.assertEqual(len(full['snapshot']['resources']),100)
                def cli(action,request):
                    snapshot['observed_at']=time.time()
                    cached.write_text(json.dumps(snapshot));cached.chmod(0o600)
                    self.assertGreater(len(json.dumps(monitor.execute('tabs.monitor.status',{})).encode()),262144)
                    output=io.StringIO()
                    flags=['--interval','300','--stale-after','600'] if action=='monitor-start' else []
                    with contextlib.redirect_stdout(output):
                        code=run(['--wake-root',directory,'tabs',action,'--json','--request-id',request,*flags])
                    self.assertEqual(code,0,output.getvalue())
                    value=json.loads(output.getvalue())
                    operation=value['result']['operation']
                    self.assertEqual(operation['phase'],'terminal')
                    self.assertEqual(operation['execution'],'completed')
                    self.__class__.control_result_bytes[request]=len(json.dumps(operation['result']).encode())
                    self.assertLess(self.control_result_bytes[request],262144)
                    self.assertNotIn('snapshot',operation['result'])
                    self.assertIn('settings',operation['result']['monitor'])
                    return operation['result']
                stopped=cli('monitor-stop','large-already-stop')
                self.assertTrue(stopped['already_stopped'])
                self.assertEqual(len(monitor.execute('tabs.monitor.status',{})['snapshot']['resources']),100)
                # Stop observer and choose an empty disposable configuration before
                # testing service ownership, so these controls do no formatting work.
                observer.close()
                path.write_text(json.dumps(dict(schema_version=1,workspaces={})));path.chmod(0o600)
                started=cli('monitor-start','bounded-start')
                pid=started['monitor']['process']['pid']
                self.assertFalse(started['already_running'])
                duplicate=cli('monitor-start','bounded-start-again')
                self.assertTrue(duplicate['already_running'])
                self.assertEqual(duplicate['monitor']['process']['pid'],pid)
                stopped=cli('monitor-stop','bounded-stop')
                self.assertTrue(stopped['stop_requested'])
                self.assertEqual(stopped['monitor']['status'],'stopped')
                self.assertEqual(stopped['monitor']['process']['pid'],pid)
                self.assertTrue(cli('monitor-stop','bounded-stop-again')['already_stopped'])
                human=io.StringIO()
                with contextlib.redirect_stdout(human):
                    code=run(['--wake-root',directory,'tabs','monitor-stop','--request-id','bounded-stop-again'])
                self.assertEqual(code,0)
                self.assertIn('Tab monitor: stopped',human.getvalue())
                self.assertIn('tabs monitor-status --json',human.getvalue())
                self.assertNotIn('Tabs: 0',human.getvalue())
            finally:
                observer.close()
                monitor.execute('tabs.monitor.stop',{'timeout':5})
                subprocess.run([*tmux,'kill-server'],capture_output=True)
