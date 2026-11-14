import tempfile
import unittest
from codex_wake.controller_tabs import ControllerTabs
from codex_wake.managed_inventory import InventoryError


class BotFamilyTests(unittest.TestCase):
    def test_public_lineage_is_durable_and_not_a_presentation_identity(self):
        with tempfile.TemporaryDirectory() as root:
            tabs = ControllerTabs(root, workspaces={}, host='host', environment='test')
            for descriptor in (
                dict(bot_id='chatgpt', name='ChatGPT'),
                dict(bot_id='work', parent_bot_id='chatgpt', name='Work', scope_kind='account', scope_ref='work'),
                dict(bot_id='task', parent_bot_id='work', name='Ticket 42', scope_kind='task', scope_ref='#42'),
            ):
                tabs.execute('tabs.family.register', descriptor)
            reopened = ControllerTabs(root, workspaces={}, host='host', environment='test')
            family = reopened.execute('tabs.family.show', dict(bot_id='task'))
            self.assertEqual(family['bot']['root_bot_id'], 'chatgpt')
            self.assertEqual([b['bot_id'] for b in family['ancestors']], ['chatgpt', 'work'])
            self.assertEqual(family['bindings'], [])
            self.assertFalse(family['grants_authority'])
            self.assertEqual(len(reopened.execute('tabs.family.list', {})['bots']), 3)

    def test_registration_reuses_equal_identity_and_rejects_parent_changes(self):
        with tempfile.TemporaryDirectory() as root:
            tabs = ControllerTabs(root, workspaces={}, host='host', environment='test')
            descriptor = dict(bot_id='root', name='Root')
            first = tabs.execute('tabs.family.register', descriptor)['bot']
            self.assertEqual(tabs.execute('tabs.family.register', descriptor)['bot'], first)
            renamed=tabs.execute('tabs.family.register',dict(descriptor,name='Renamed'))['bot']
            self.assertEqual(renamed['root_bot_id'],'root')
            self.assertEqual(renamed['name'],'Renamed')
            with self.assertRaises(InventoryError):
                tabs.execute('tabs.family.register', dict(bot_id='child', name='Child', parent_bot_id='missing'))
            tabs.execute('tabs.family.register', dict(bot_id='child', name='Child', parent_bot_id='root'))
            with self.assertRaises(InventoryError):
                tabs.execute('tabs.family.register', dict(bot_id='root', name='Root', parent_bot_id='child'))

    def test_real_bindings_keep_clients_distinct_and_fence_replaced_panes(self):
        import shutil
        import subprocess
        import time
        from pathlib import Path
        from codex_wake.controller_tab_adapters import TmuxAttachmentTransport
        from codex_wake.bot_families import BotFamilies
        if not shutil.which('tmux'):
            self.skipTest('tmux unavailable')
        with tempfile.TemporaryDirectory() as root:
            socket = str(Path(root)/'tmux.sock')
            def tmux(*args):
                return subprocess.check_output(['tmux','-S',socket,*args], text=True)
            tmux('new-session','-d','-s','family','exec sleep 60')
            try:
                tmux('new-window','-d','-t','family','exec sleep 60')
                transport = TmuxAttachmentTransport(socket, '$0')
                tabs = ControllerTabs(root, workspaces={'w':dict(kind='tmux',transport=transport,socket_path=socket)},host='h',environment='test')
                tabs.execute('tabs.family.register',dict(bot_id='root',name='Root'))
                tabs.execute('tabs.family.register',dict(bot_id='child',name='Child',parent_bot_id='root'))
                windows=transport.snapshot(time.monotonic()+2)['windows']
                for client, window in zip(('a','b'), windows):
                    tabs.execute('tabs.family.bind',dict(bot_id='child',client_id=client,workspace='w',window_id=window['window_id'],pane_id=window['panes'][0]['pane_id']))
                self.assertEqual(len(tabs.execute('tabs.family.show',dict(bot_id='child'))['bindings']),2)
                family=tabs.execute('tabs.list',{})['resources'][0]['bot_family']
                self.assertEqual(family['parent_name'],'Root')
                self.assertFalse(family['root_tab_available'])
                with self.assertRaises(InventoryError):
                    tabs.execute('tabs.family.bind',dict(bot_id='root',client_id='a',workspace='w',window_id=windows[0]['window_id'],pane_id=windows[0]['panes'][0]['pane_id']))
                registry=BotFamilies(root,tabs=tabs)
                self.assertIsNotNone(registry.resolve_binding(registry.get('child'),'a'))
                tmux('respawn-pane','-k','-t',windows[0]['panes'][0]['pane_id'],'exec sleep 60')
                self.assertIsNone(registry.resolve_binding(registry.get('child'),'a'))
                self.assertEqual(len(tabs.execute('tabs.family.list',{})['bots']),2)
            finally:
                tmux('kill-server')

    def test_cli_register_and_show_use_the_same_durable_interface(self):
        import subprocess
        import sys
        import json
        with tempfile.TemporaryDirectory() as root:
            for args in [('register','--bot-id','root','--name','ChatGPT'),('show','--bot-id','root')]:
                result=subprocess.run([sys.executable,'-m','codex_wake.entrypoint','--wake-root',root,'tabs','family',*args,'--json'],capture_output=True,text=True)
                self.assertEqual(result.returncode,0,result.stderr+result.stdout)
            self.assertEqual(json.loads(result.stdout)['bot']['root_bot_id'],'root')
