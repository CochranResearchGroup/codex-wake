"""Public monitor publication preserves changes and bounds quiet disk writes."""
import json
from pathlib import Path
import tempfile
import shutil
import subprocess
import time
import unittest

from codex_wake.tab_monitor import TabMonitor


class MonitorPublicationTests(unittest.TestCase):
    def test_background_owner_heartbeats_without_rewriting_unchanged_inventory(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            path=root/'controller-tabs.json'
            path.write_text(json.dumps(dict(schema_version=1,workspaces={})));path.chmod(0o600)
            monitor=TabMonitor(root)
            monitor.execute('tabs.monitor.start',dict(interval=.2,stale_after=2.))
            try:
                until=time.monotonic()+3
                while True:
                    status=monitor.execute('tabs.monitor.status',{})
                    owner_record=json.loads((root/'tab-monitor'/'owner.json').read_text())
                    if status['snapshot'] and owner_record.get('last_cycle_at') is not None:
                        break
                    self.assertLess(time.monotonic(),until)
                    time.sleep(.01)
                snapshot_path=root/'tab-monitor'/'snapshot.json'
                owner_path=root/'tab-monitor'/'owner.json'
                original_snapshot=snapshot_path.stat().st_mtime_ns
                original_owner=owner_path.stat().st_mtime_ns
                original_ticks=status['monitor']['observer']['costs']['ticks']
                # Watch real atomic filesystem writes, not a mocked save helper.
                until=time.monotonic()+.7
                while owner_path.stat().st_mtime_ns==original_owner:
                    self.assertLess(time.monotonic(),until)
                    time.sleep(.01)
                self.assertEqual(snapshot_path.stat().st_mtime_ns,original_snapshot)
                current=monitor.execute('tabs.monitor.status',{})
                self.assertEqual(current['snapshot']['freshness'],'fresh')
                self.assertGreater(current['monitor']['observer']['costs']['ticks'],original_ticks)
                until=time.monotonic()+1.4
                while snapshot_path.stat().st_mtime_ns==original_snapshot:
                    self.assertLess(time.monotonic(),until)
                    time.sleep(.01)
                self.assertEqual(monitor.execute('tabs.monitor.status',{})['snapshot']['freshness'],'fresh')
            finally:
                monitor.execute('tabs.monitor.stop',{})

    @unittest.skipUnless(shutil.which('tmux'),'tmux unavailable')
    def test_daemon_persists_full_rows_and_enabled_routing_receives_them(self):
        from codex_wake.controller_tabs import controller_tabs_from_root
        from codex_wake.terminal_routing import TerminalRouting
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);tmux=['tmux','-S',str(root/'tmux.sock')]
            subprocess.run([*tmux,'new-session','-d','-s','source','exec sleep 60'],check=True)
            subprocess.run([*tmux,'new-session','-d','-s','destination','exec sleep 60'],check=True)
            path=root/'controller-tabs.json'
            path.write_text(json.dumps(dict(schema_version=1,workspaces=dict(
                source=dict(kind='tmux',socket_path=str(root/'tmux.sock'),session_id='$0'),
                destination=dict(kind='tmux',socket_path=str(root/'tmux.sock'),session_id='$1')))));path.chmod(0o600)
            monitor=TabMonitor(root)
            try:
                monitor.execute('tabs.monitor.start',dict(interval=.2,stale_after=2.,health=False,errors=False))
                owner=controller_tabs_from_root(root)
                routing=TerminalRouting(root,tabs=owner)
                rule=routing.execute('tabs.route.save',dict(name='future',destination='destination',
                    selection=dict(field='harness',unknown=True),stability_seconds=0))['rule']
                routing.execute('tabs.route.enable',dict(rule_id=rule['id']))
                window=subprocess.check_output([*tmux,'new-window','-d','-t','source','-P','-F','#{window_id}','exec sleep 60'],text=True).strip()
                until=time.monotonic()+5
                while subprocess.check_output([*tmux,'display-message','-p','-t',window,'#{session_name}'],text=True).strip()!='destination':
                    self.assertLess(time.monotonic(),until,'enabled routing did not receive resource rows')
                    time.sleep(.02)
                until=time.monotonic()+3
                while True:
                    report=monitor.execute('tabs.monitor.status',{})
                    snapshot=report['snapshot']
                    if snapshot and snapshot.get('resource_count')==3:
                        break
                    self.assertLess(time.monotonic(),until)
                    time.sleep(.02)
                self.assertIsInstance(snapshot['resources'],list)
                self.assertEqual(len(snapshot['resources']),3)
                self.assertEqual(snapshot['freshness'],'fresh')
                self.assertIn('last_formatting',report['monitor'])
            finally:
                monitor.execute('tabs.monitor.stop',{})
                subprocess.run([*tmux,'kill-server'],capture_output=True)

    def test_metadata_frames_are_materialized_only_for_actual_publication(self):
        from codex_wake.managed_inventory import InventoryError
        with tempfile.TemporaryDirectory() as directory:
            mono=[0.];loads=[]
            monitor=TabMonitor(directory,monotonic=lambda:mono[0])
            record={}
            def frame(revision):
                return dict(schema_version=1,origin='manual',observed_at=time.time(),resource_count=1,
                    projection_revision=revision,evidence_revision=revision,workspaces=['fixture'],unavailable=[],
                    observer=dict(costs=dict(ticks=len(loads)),sources=[]))
            def loader(snapshot):
                def load():
                    loads.append(snapshot['observed_at'])
                    snapshot['resources']=[dict(target=dict(workspace='fixture'),window=dict(window_id='@1'),
                        monitor_observed_at=snapshot['observed_at'],traits={})]
                return load
            first=frame('first')
            self.assertTrue(monitor.publish_observation(first,record,resources_loader=loader(first)))
            self.assertEqual(len(loads),1)
            quiet=frame('first');mono[0]=1.
            self.assertFalse(monitor.publish_observation(quiet,record,resources_loader=loader(quiet)))
            self.assertNotIn('resources',quiet)
            self.assertEqual(len(loads),1)
            changed=frame('changed')
            self.assertTrue(monitor.publish_observation(changed,record,resources_loader=loader(changed)))
            self.assertEqual(len(loads),2)
            self.assertEqual(len(monitor.execute('tabs.monitor.status',{})['snapshot']['resources']),1)
            with self.assertRaises(InventoryError):
                monitor.publish_observation(frame('missing-loader'),record)
            self.assertEqual(len(monitor.execute('tabs.monitor.status',{})['snapshot']['resources']),1)
            mono[0]=6.
            pulse=frame('changed')
            self.assertTrue(monitor.publish_observation(pulse,record,resources_loader=loader(pulse)))
            self.assertEqual(len(loads),3)

    def test_publisher_writes_changed_evidence_immediately_before_heartbeat(self):
        with tempfile.TemporaryDirectory() as directory:
            mono=[0.]
            monitor=TabMonitor(directory,monotonic=lambda:mono[0])
            record={}
            snapshot=dict(schema_version=1,origin='manual',observed_at=time.time(),resources=[],
                workspaces=[],unavailable=[],evidence_revision='evidence-one',projection_revision='display-one',
                observer=dict(costs=dict(ticks=1),sources=[]))
            self.assertTrue(monitor.publish_observation(snapshot,record))
            target=Path(directory)/'tab-monitor'/'snapshot.json'
            written=target.stat().st_mtime_ns
            mono[0]=1.
            snapshot['observer']['costs']['ticks']=2
            self.assertFalse(monitor.publish_observation(snapshot,record))
            self.assertEqual(target.stat().st_mtime_ns,written)
            self.assertEqual(record['observer']['costs']['ticks'],2)
            snapshot.update(projection_revision='display-two')
            self.assertTrue(monitor.publish_observation(snapshot,record))
            snapshot.update(evidence_revision='evidence-two')
            self.assertTrue(monitor.publish_observation(snapshot,record))
            self.assertEqual(monitor.execute('tabs.monitor.status',{})['snapshot']['evidence_revision'],'evidence-two')
            mono[0]=6.
            self.assertTrue(monitor.publish_observation(snapshot,record))


if __name__=='__main__':
    unittest.main()
