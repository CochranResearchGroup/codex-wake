"""Saved psmux session selection through the public owner."""
import tempfile
import unittest
from pathlib import Path
from codex_wake.controller_tabs import ControllerTabs


class PsmuxSessionTests(unittest.TestCase):
    def test_psmux_requires_host_namespace_instead_of_inheriting_tmux_socket(self):
        with tempfile.TemporaryDirectory() as d:
            tabs=ControllerTabs(Path(d),workspaces={},host='test',environment='fixture')
            with self.assertRaisesRegex(ValueError,'psmux'):
                tabs.execute('tabs.session.create',dict(name='bots',backend='psmux'))

    def test_empty_psmux_definition_preserves_explicit_namespace_without_native_launch(self):
        with tempfile.TemporaryDirectory() as d:
            tabs=ControllerTabs(Path(d),workspaces={},host='test',environment='fixture')
            record=tabs.execute('tabs.session.create',dict(name='bots',backend='psmux',server='test529'))['session']
            self.assertEqual(record['server'],'test529')
            self.assertEqual(record['state'],'empty')
            tabs.execute('tabs.session.delete',dict(session=record['id']))
            self.assertEqual(tabs.execute('tabs.session.list',{})['sessions'],[])

    def test_open_without_host_bridge_refuses_without_fallback_launch(self):
        with tempfile.TemporaryDirectory() as d:
            tabs=ControllerTabs(Path(d),workspaces={},host='test',environment='fixture')
            record=tabs.execute('tabs.session.create',dict(name='bots',backend='psmux',server='test529'))['session']
            with self.assertRaisesRegex(ValueError,'host-approved psmux bridge'):
                tabs.execute('tabs.session.open',dict(session=record['id']))
            self.assertEqual(tabs.execute('tabs.session.show',dict(session='bots'))['session']['state'],'empty')
