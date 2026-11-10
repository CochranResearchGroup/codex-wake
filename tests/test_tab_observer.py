"""Retained public observer behavior over disposable native metadata sources."""
import json
import threading
from websockets.sync.server import unix_serve
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import unittest

from codex_wake.tab_monitor import TabMonitor
from codex_wake.tab_observer import TabObserver


@unittest.skipUnless(shutil.which('tmux'), 'tmux unavailable')
class ObserverTests(unittest.TestCase):
    def test_persistent_inventory_source_loss_and_owned_cleanup(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            command = ['tmux', '-S', str(root/'tmux.sock')]
            subprocess.run([*command, 'new-session', '-d', '-s', 'fixture', 'sleep 60'], check=True)
            config = dict(schema_version=1, workspaces=dict(fixture=dict(kind='tmux',
                socket_path=str(root/'tmux.sock'), session_id='$0')))
            path = root/'controller-tabs.json'
            path.write_text(json.dumps(config)); path.chmod(0o600)
            observer = TabObserver(root, settings=dict(health=False, errors=False))
            try:
                until = time.monotonic()+3
                while True:
                    result = observer.tick()
                    if result['resources']:
                        break
                    self.assertLess(time.monotonic(), until)
                row = result['resources'][0]
                self.assertEqual(row['target']['workspace'], 'fixture')
                owner_pid = observer.status()['sources'][0]['owned_pid']
                self.assertIsNotNone(owner_pid)
                second = observer.tick()
                self.assertEqual(second['resources'][0]['window'], row['window'])
                self.assertEqual(observer.status()['sources'][0]['owned_pid'], owner_pid)
                self.assertEqual(observer.status()['costs']['fallback_probes'], 0)
                subprocess.run([*command, 'kill-server'], check=True)
                until = time.monotonic()+2
                while not observer.tick()['unavailable']:
                    self.assertLess(time.monotonic(), until)
                self.assertNotEqual(observer.status()['sources'][0]['state'], 'connected')
            finally:
                observer.close()
                subprocess.run([*command, 'kill-server'], capture_output=True)
            self.assertTrue(observer.status()['closed'])
            self.assertFalse(Path('/proc', str(owner_pid)).exists())

    def test_native_delta_projects_without_inventory_and_source_loss_removes_authority(self):
        from codex_wake.controller_tabs import controller_tabs_from_root
        from codex_wake.tab_observation import ObservationCache
        from codex_wake.process import process_identity
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); home=root/'home'; home.mkdir()
            tmux=['tmux','-S',str(root/'tmux.sock')]
            subprocess.run([*tmux,'new-session','-d','-s','fixture','-c',str(root),'sleep 60'],check=True)
            subprocess.run([*tmux,'select-pane','-t','%0','-T','native-fixture'],check=True)
            path=root/'controller-tabs.json'
            path.write_text(json.dumps(dict(schema_version=1,workspaces=dict(fixture=dict(
                kind='tmux',socket_path=str(root/'tmux.sock'),session_id='$0')))));path.chmod(0o600)
            connections=[]
            def handler(connection):
                connections.append(connection)
                try:
                    for raw in connection:
                        value=json.loads(raw);method=value.get('method')
                        if method=='initialized':continue
                        if method=='initialize':result=dict(codexHome=str(home),userAgent='fixture')
                        elif method=='thread/loaded/list':result=dict(data=['t1'],nextCursor=None)
                        elif method=='thread/read':result=dict(thread=dict(id='t1',name='native-fixture',cwd=str(root),status=dict(type='idle')))
                        else:raise AssertionError(method)
                        connection.send(json.dumps(dict(id=value['id'],result=result)))
                except Exception:pass
            def process_probe(pid,deadline):
                birth=process_identity(pid)
                return ([dict(process=dict(pid=pid,start_ticks=birth['start_time_ticks'],boot_id=birth['boot_id']),
                    executable='/synthetic/codex',argv=[],cwd=str(root))],True)
            native_path=str(root/'native.sock')
            with unix_serve(handler,path=native_path) as server:
                thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
                owner=controller_tabs_from_root(root)
                mono=[0.];wall_offset=[0.]
                owner.observation_cache=ObservationCache(root,process_probe=process_probe,monotonic=lambda:mono[0])
                observer=TabObserver(root,owner=owner,settings=dict(health=False,errors=False),
                    monotonic=lambda:mono[0],clock=lambda:time.time()+wall_offset[0],native_endpoints=['unix://'+native_path])
                try:
                    result=observer.tick()
                    pane=result['resources'][0]['traits']['panes'][0]
                    self.assertEqual(pane['binding']['conversation_id'],'t1')
                    self.assertTrue(pane['traits']['activity']['source_available'])
                    original_projection=result['projection_revision']
                    original_resource=result['resources'][0]['projection_revision']
                    quiet=observer.tick()
                    self.assertEqual(quiet['projection_revision'],original_projection)
                    self.assertEqual(quiet['resources'][0]['projection_revision'],original_resource)
                    mono[0]=6.
                    refreshed=observer.tick()
                    self.assertEqual(refreshed['projection_revision'],original_projection)
                    self.assertNotEqual(refreshed['evidence_revision'],result['evidence_revision'])
                    passes=observer.status()['costs']['inventory_passes']
                    connections[-1].send(json.dumps(dict(method='thread/status/changed',params=dict(threadId='t1',status=dict(type='active',activeFlags=[])))))
                    until=time.monotonic()+2
                    while True:
                        result=observer.tick();activity=result['resources'][0]['traits']['traits']['activity']
                        if activity['value']=='running':break
                        self.assertLess(time.monotonic(),until)
                    self.assertEqual(observer.status()['costs']['inventory_passes'],passes)
                    self.assertTrue(activity['source_available'])
                    self.assertNotEqual(result['projection_revision'],original_projection)
                    running_projection=result['projection_revision']
                    self.assertEqual(observer.tick()['projection_revision'],running_projection)
                    wall_offset[0]=30.
                    self.assertEqual(observer.tick()['projection_revision'],running_projection)
                    connections[-1].close()
                    result=observer.tick()
                    self.assertFalse(result['resources'][0]['traits']['traits']['activity']['source_available'])
                    self.assertNotEqual(result['projection_revision'],running_projection)
                finally:
                    observer.close();server.shutdown();thread.join(2)
                    subprocess.run([*tmux,'kill-server'],capture_output=True)

    def test_default_owned_error_classification_is_redacted_through_cached_transport(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            tmux=['tmux','-S',str(root/'tmux.sock')]
            subprocess.run([*tmux,'new-session','-d','-s','fixture',
                "printf '\\033[31mError: synthetic_private_text\\033[0m\\n'; exec sleep 60"],check=True)
            path=root/'controller-tabs.json'
            path.write_text(json.dumps(dict(schema_version=1,workspaces=dict(fixture=dict(
                kind='tmux',socket_path=str(root/'tmux.sock'),session_id='$0')))));path.chmod(0o600)
            wall_offset=[-30.]
            observer=TabObserver(root,clock=lambda:time.time()+wall_offset[0])
            try:
                result=observer.tick()
                error=result['resources'][0]['traits']['panes'][0]['traits']['error']
                self.assertEqual(error['value'],'present')
                self.assertEqual(error['message'],'Terminal error (content redacted)')
                self.assertNotIn('synthetic_private_text',json.dumps(result))
                self.assertIsNotNone(result['resources'][0]['projection_valid_until'])
                original_projection=result['projection_revision']
                original_evidence=result['evidence_revision']
                wall_offset[0]=0.
                qualified=observer.tick()
                self.assertNotEqual(qualified['projection_revision'],original_projection)
                self.assertEqual(qualified['evidence_revision'],original_evidence)
                original_projection=qualified['projection_revision']
                wall_offset[0]=30.
                expired=observer.tick()
                self.assertNotEqual(expired['projection_revision'],original_projection)
                self.assertEqual(expired['evidence_revision'],original_evidence)
            finally:
                observer.close()
                subprocess.run([*tmux,'kill-server'],capture_output=True)

    def test_hundred_tab_idle_snapshots_are_independent_and_source_stays_available(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);tmux=['tmux','-S',str(root/'tmux.sock')]
            subprocess.run([*tmux,'new-session','-d','-s','fixture','sleep 60'],check=True)
            for _ in range(99):
                subprocess.run([*tmux,'new-window','-d','-t','fixture','sleep 60'],check=True)
            path=root/'controller-tabs.json'
            path.write_text(json.dumps(dict(schema_version=1,workspaces=dict(fixture=dict(
                kind='tmux',socket_path=str(root/'tmux.sock'),session_id='$0')))));path.chmod(0o600)
            observer=TabObserver(root)
            try:
                initial=observer.tick(deadline=time.monotonic()+10)
                self.assertEqual(len(initial['resources']),100)
                expected=json.loads(json.dumps(initial['resources']))
                initial['resources'][0]['window']['panes'][0]['pane_id']='caller-mutated'
                initial['resources'][0]['traits']['traits']['error']['value']='caller-mutated'
                # Subscription command responses arrive between service ticks.
                # They must not expire before the normal one-second next poll.
                time.sleep(1.05)
                snapshots=[observer.tick() for _ in range(4)]
                self.assertTrue(all(len(value['resources'])==100 for value in snapshots))
                self.assertTrue(all(not value['unavailable'] for value in snapshots))
                self.assertEqual(snapshots[-1]['resources'][0]['window'],expected[0]['window'])
                snapshots[0]['resources'][0]['window']['panes'][0]['pane_id']='second-caller-mutated'
                self.assertEqual(snapshots[-1]['resources'][0]['window'],expected[0]['window'])
                self.assertEqual(snapshots[-1]['observer']['sources'][0]['state'],'available')
                self.assertEqual(snapshots[-1]['observer']['costs']['fallback_probes'],0)
            finally:
                observer.close()
                subprocess.run([*tmux,'kill-server'],capture_output=True)

    def test_monitor_tier_controls_are_independent_and_validated(self):
        from codex_wake.managed_inventory import InventoryError
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root/'controller-tabs.json'
            path.write_text(json.dumps(dict(schema_version=1, workspaces={}))); path.chmod(0o600)
            monitor = TabMonitor(directory)
            with self.assertRaises(InventoryError):
                monitor.execute('tabs.monitor.start', dict(health_interval=10))
            try:
                result = monitor.execute('tabs.monitor.start', dict(activity=False, health=True,
                    errors=False, health_interval=90, error_interval=10, interval=.2))
                settings = result['monitor']['settings']
                self.assertFalse(settings['activity'])
                self.assertTrue(settings['health'])
                self.assertFalse(settings['errors'])
            finally:
                monitor.execute('tabs.monitor.stop', {})
