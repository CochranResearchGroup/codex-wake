"""Native system UTC is available only with qualified synchronization."""
import os
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from codex_wake import linux_clock, native_clock
from codex_wake.message_policy import stable_micros


class LinuxClockTests(unittest.TestCase):
    def test_network_window_uses_synchronized_kernel_error_bound(self):
        stamp = SimpleNamespace(status=0x2000, maxerror=4500,
                                seconds=2_000_000_000, fraction=500_000_000)
        with patch.dict(os.environ, {}, clear=True), patch.object(native_clock, 'configuration', return_value=None):
            with patch.object(linux_clock.platform, 'uname', return_value=SimpleNamespace(release='7.0-generic', version='Ubuntu')):
                with patch.object(linux_clock, 'measurement', return_value=(0, stamp)):
                    snapshot = native_clock.snapshot()
                    self.assertEqual(snapshot['reason'], 'native_linux_synchronized_utc')
                    self.assertLessEqual(stable_micros(snapshot), 2_000_000_000_495_500)
                    self.assertGreaterEqual(stable_micros(snapshot, upper=True), 2_000_000_000_504_500)
                    self.assertIsNone(snapshot['counter'])
                with patch.object(linux_clock, 'measurement', return_value=(5, stamp)):
                    self.assertIsNone(stable_micros(native_clock.snapshot()))
            with patch.object(linux_clock.platform, 'uname', return_value=SimpleNamespace(release='microsoft-WSL2', version='')):
                self.assertEqual(native_clock.snapshot()['reason'], 'stable_time_configuration_required')
