"""Private stock-tmux qualification at the public feed seam."""
import shutil
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

from codex_wake.tab_tmux_feed import TmuxMetadataFeed


@unittest.skipUnless(shutil.which('tmux'), 'stock tmux required')
class TmuxFeedTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix='wake-feed543-')
        self.socket = str(Path(self.directory.name) / 'tmux.sock')
        self.tmux('new-session', '-d', '-s', 'fixture', '-x', '117', '-y', '33', 'exec sleep 90')
        self.feed = TmuxMetadataFeed(self.socket, '$0')

    def tearDown(self):
        self.feed.close()
        self.tmux('kill-server', check=False)
        self.directory.cleanup()

    def tmux(self, *args, check=True):
        return subprocess.run(['tmux', '-S', self.socket, *args], capture_output=True,
                              text=True, timeout=3, check=check).stdout.strip()

    def events_until(self, kind, timeout=3):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            events = self.feed.poll(.1)
            for event in events:
                if event['kind'] == kind:
                    return event
        self.fail('no ' + kind + ' event: ' + str(self.feed.status()))

    def test_baseline_changes_and_owned_cleanup_preserve_panes(self):
        before = self.tmux('list-panes', '-a', '-F', '#{pane_id} #{pane_pid} #{window_layout} #{window_active}')
        baseline = self.events_until('baseline')
        snapshot = baseline['data']['snapshot']
        self.assertEqual(snapshot['session_id'], '$0')
        flags = self.tmux('list-clients', '-F', '#{client_flags}')
        self.assertIn('no-output', flags)
        self.assertIn('ignore-size', flags)
        self.assertIn('read-only', flags)
        self.assertEqual(snapshot['windows'][0]['panes'][0]['pane_id'], '%0')
        self.assertEqual(before, self.tmux('list-panes', '-a', '-F', '#{pane_id} #{pane_pid} #{window_layout} #{window_active}'))
        name = 'literal ; $(touch /tmp/no-wake543) " \\ label'
        self.tmux('rename-window', '-t', '@0', name)
        update = self.events_until('update')
        self.assertEqual(update['data']['snapshot']['windows'][0]['name'], name.replace('\\', '\\\\'))
        self.assertEqual(update['epoch'], baseline['epoch'])
        self.assertGreater(update['sequence'], baseline['sequence'])
        self.feed.close()
        self.assertEqual(before, self.tmux('list-panes', '-a', '-F', '#{pane_id} #{pane_pid} #{window_layout} #{window_active}'))
        self.assertEqual(self.feed.status()['state'], 'closed')

    def test_disconnect_then_reconnect_requires_new_baseline(self):
        baseline = self.events_until('baseline')
        self.tmux('kill-server')
        unavailable = self.events_until('unavailable')
        self.assertEqual(unavailable['epoch'], baseline['epoch'])
        self.tmux('new-session', '-d', '-s', 'replacement', 'exec sleep 90')
        replacement = self.events_until('baseline', timeout=5)
        self.assertNotEqual(replacement['epoch'], baseline['epoch'])
        self.assertEqual(replacement['sequence'], 1)

    def test_metadata_flood_is_coalesced_and_names_do_not_execute(self):
        self.events_until('baseline')
        for index in range(40):
            self.tmux('rename-window', '-t', '@0', 'name ' + str(index))
        update = self.events_until('update')
        self.assertEqual(update['data']['snapshot']['windows'][0]['name'], 'name 39')
        self.assertLessEqual(self.feed.status()['pending_commands'], 2)
        self.assertLessEqual(self.feed.status()['buffered_bytes'], self.feed.MAX_BYTES)
        self.feed.close()
        self.assertEqual(self.tmux('list-clients', '-F', '#{client_pid}'), '')

    def test_idle_poll_is_bounded_and_pane_replacement_is_observed(self):
        self.events_until('baseline')
        start = time.monotonic()
        self.assertEqual(self.feed.poll(0), [])
        self.assertLess(time.monotonic() - start, .1)
        owned_pid = self.feed.status()['owned_pid']
        for _ in range(50):
            self.feed.poll(0)
        self.assertEqual(self.feed.status()['owned_pid'], owned_pid)
        self.assertEqual(len(self.tmux('list-clients', '-F', '#{client_pid}').splitlines()), 1)
        original = self.tmux('display-message', '-p', '-t', '%0', '#{pane_pid}')
        self.tmux('respawn-pane', '-k', '-t', '%0', 'exec sleep 90')
        update = self.events_until('update')
        self.assertNotEqual(str(update['data']['snapshot']['windows'][0]['panes'][0]['pid']), original)


if __name__ == '__main__':
    unittest.main()
