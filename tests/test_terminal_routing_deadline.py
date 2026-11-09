"""Expired host cycle budget cannot begin a native relocation effect."""
from pathlib import Path
import tempfile
import time
import unittest
from codex_wake.controller_tabs import ControllerTabs
from codex_wake.managed_inventory import InventoryError
from codex_wake.terminal_relocation import TerminalRelocation


class RoutingDeadlineTests(unittest.TestCase):
    def test_expired_host_budget_is_explicit_before_selection_or_native_dispatch(self):
        with tempfile.TemporaryDirectory() as d:
            tabs=ControllerTabs(Path(d),workspaces={},host='fixture',environment='test')
            with self.assertRaises(InventoryError) as caught:
                TerminalRelocation(d,tabs=tabs,automatic=True,deadline=time.monotonic()-1).execute('tabs.relocate.preview',{'destination':'bots'})
            self.assertEqual(caught.exception.code,'cycle_deadline')
