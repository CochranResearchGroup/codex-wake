"""Public redacted same-user observation, without capture/input enrollment."""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import unittest

from codex_wake.controller_tab_adapters import TmuxAttachmentTransport
from codex_wake.tab_traits import TabTraits


@unittest.skipUnless(shutil.which('tmux'), 'tmux unavailable')
class DefaultErrorObservationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.socket = str(Path(self.directory.name) / 'tmux.sock')
        self.tmux('new-session', '-d', '-x', '100', '-y', '16', '-s', 'fixture', 'exec sleep 60')
        self.addCleanup(lambda: self.tmux('kill-server'))
        self.transport = TmuxAttachmentTransport(self.socket, '$0')
        self.owner = TabTraits(self.directory.name)

    def tmux(self, *args):
        return subprocess.check_output(['tmux', '-S', self.socket, *args], text=True, timeout=3)

    def screen(self, text):
        # Controlled fixture output only; no input is sent to an agent or shell.
        script = Path(self.directory.name) / 'display.py'
        script.write_text('import sys,time\nsys.stdout.write(' + repr(text + '\nREADY') + ');sys.stdout.flush();time.sleep(60)\n')
        self.tmux('respawn-pane', '-k', '-t', '%0', 'python3 ' + str(script))
        until = time.monotonic() + 3
        while 'READY' not in self.tmux('capture-pane', '-p', '-t', '%0'):
            self.assertLess(time.monotonic(), until)
            time.sleep(.01)
        return self.transport.snapshot(time.monotonic() + 2)['windows'][0]

    def test_owned_tmux_default_reports_only_redacted_current_error(self):
        window = self.screen('\x1b[12;1H\x1b[31mError: private-synthetic-payload\x1b[0m')
        before = self.tmux('capture-pane', '-p', '-e', '-t', '%0')
        result = self.owner.observe_window(window, transport=self.transport, deadline=time.monotonic() + 2)
        error = result['traits']['error']
        self.assertEqual(error['value'], 'present')
        self.assertEqual(error['location']['region'], 'bottom')
        self.assertNotIn('private-synthetic-payload', json.dumps(result))
        self.assertEqual(before, self.tmux('capture-pane', '-p', '-e', '-t', '%0'))

    def test_private_secret_and_wrapped_draft_remain_unknown_without_disclosure(self):
        for screen in (
            'Error: failed\nPassword: synthetic-secret',
            'Error: failed\nAPI key: synthetic-secret',
            'Error: failed\n› unsubmitted synthetic draft',
            '› \nError: wrapped draft line',
        ):
            with self.subTest(screen=screen):
                window = self.screen(screen)
                before = self.tmux('capture-pane', '-p', '-e', '-t', '%0')
                result = self.owner.observe_window(window, transport=self.transport, deadline=time.monotonic()+2)
                self.assertEqual(result['traits']['error']['value'], 'unknown')
                self.assertNotIn('synthetic', json.dumps(result))
                self.assertEqual(before, self.tmux('capture-pane', '-p', '-e', '-t', '%0'))
        window = self.screen('Error: failed')
        private = self.owner.observe_window(window, transport=self.transport, privacy=lambda _: 'private', deadline=time.monotonic()+2)
        self.assertEqual(private['traits']['error']['value'], 'unknown')

    def test_generic_capture_object_cannot_enable_default_screen_read(self):
        window = self.screen('Error: failed')
        class Unowned:
            def command(self, *args):
                raise AssertionError('unowned presentation was read')
        result = self.owner.observe_window(window, transport=Unowned(), deadline=time.monotonic()+2)
        self.assertEqual(result['traits']['error']['value'], 'unknown')
        for privacy in ('private', 'unknown'):
            class Blocked(TmuxAttachmentTransport):
                def command(self, *args):
                    raise AssertionError('explicit private presentation was read')
            transport = Blocked(self.socket, '$0')
            result = self.owner.observe_window(window, transport=transport,
                privacy=lambda _: privacy, deadline=time.monotonic()+2)
            self.assertEqual(result['traits']['error']['value'], 'unknown')
