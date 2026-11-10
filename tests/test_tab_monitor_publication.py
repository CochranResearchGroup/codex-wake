"""Public monitor publication preserves changes and bounds quiet disk writes."""
import json
from pathlib import Path
import tempfile
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
