import tempfile
import unittest
from pathlib import Path
from codex_wake.controller_tabs import ControllerTabs
from codex_wake.managed_inventory import InventoryError


class Transport:
    def snapshot(self, deadline):
        return dict(server='fixture', session_id='$1', socket_identity=[1,2], windows=[
            dict(window_id='@1', index=0, name='friendly', focused=True, linked=False,
                 panes=[dict(pane_id='%1', pid=123)])])


class ControllerTabsTests(unittest.TestCase):
    def test_friendly_selector_and_exact_generation(self):
        with tempfile.TemporaryDirectory() as directory:
            owner = ControllerTabs(directory, workspaces={'fixture': dict(transport=Transport(), kind='psmux')}, host='h', environment='fixture')
            resource = owner.execute('tabs.show', {'workspace':'fixture','selector':'friendly'})['resources'][0]
            self.assertEqual(resource['window']['window_id'], '@1')
            self.assertFalse(resource['input_custody']['available'])
            with self.assertRaises(InventoryError) as caught:
                owner.execute('tabs.capture', {'workspace':'fixture','expected_target':{},'pane':'%1'})
            self.assertEqual(caught.exception.code, 'stale_target')

    def test_owned_stdio_never_falls_back_or_steals_pipe(self):
        from codex_wake.controller_tab_adapters import OwnedStdioBroker
        class Client:
            def start_turn(self, thread, text):
                return dict(thread=thread, text=text)
        with tempfile.TemporaryDirectory() as directory:
            broker = OwnedStdioBroker(Client(), bindings={'%1':'thread'}, owner_id='host-owner')
            owner = ControllerTabs(directory, workspaces={'fixture': dict(transport=Transport(), kind='stdio', broker=broker)}, host='h', environment='fixture')
            row = owner.execute('tabs.show', {'workspace':'fixture'})['resources'][0]
            args = dict(workspace='fixture', expected_target=row['target'], pane='%1', input='fixture', custody=row['input_custody'], transport='structured')
            self.assertEqual(owner.execute('tabs.input', args)['result']['thread'], 'thread')
            broker.relinquish()
            with self.assertRaises(InventoryError): owner.execute('tabs.input', args)

    def test_real_isolated_tmux_capture_preview_apply(self):
        import shutil
        import subprocess
        from codex_wake.controller_tab_adapters import TmuxAttachmentTransport
        if not shutil.which('tmux'): self.skipTest('tmux unavailable')
        with tempfile.TemporaryDirectory() as directory:
            socket = str(Path(directory) / 'tmux.sock')
            subprocess.run(['tmux','-S',socket,'new-session','-d','-s','fixture','sleep 60'], check=True)
            try:
                transport = TmuxAttachmentTransport(socket, '$0')
                for name in ('ready','working'):
                    subprocess.run(['tmux','-S',socket,'new-window','-d','-n',name,'sleep 60'], check=True)
                from codex_wake.process import process_identity
                import time
                initial = transport.snapshot(time.monotonic()+5)
                evidence = {}
                for window in initial['windows']:
                    for pane in window['panes']:
                        identity = process_identity(pane['pid'])
                        evidence[pane['pane_id']] = dict(fresh=True, conversation_id=pane['pane_id'],
                            namespace='fixture', root=str(Path.cwd()), state='working' if window['name']=='working' else 'ready',
                            process=dict(pid=pane['pid'],start_ticks=identity['start_time_ticks'],boot_id=identity['boot_id']))
                owner = ControllerTabs(directory, workspaces={'fixture':dict(transport=transport,kind='byobu',observer=lambda timeout:evidence)}, host='h', environment='fixture')
                row = owner.execute('tabs.list', {})['resources'][0]
                base = dict(workspace='fixture', expected_target=row['target'])
                capture = owner.execute('tabs.capture', dict(base,pane=row['window']['panes'][0]['pane_id'], lines=5))
                self.assertTrue(capture['fallback'])
                plan = owner.execute('tabs.preview', base)['plan']
                result = owner.execute('tabs.apply', dict(base,plan_id=plan['plan_id']))
                self.assertEqual(result['receipt']['status'], 'applied')
                self.assertTrue(result['receipt']['swaps'])
                current = owner.execute('tabs.list', {})['resources'][0]['target']
                undone = owner.execute('tabs.undo', dict(workspace='fixture',expected_target=current,receipt_id=result['receipt']['receipt_id']))
                self.assertEqual(undone['receipt']['status'], 'undone')
            finally:
                subprocess.run(['tmux','-S',socket,'kill-server'], check=False)

    def test_psmux_finite_protocol_and_replaced_generation(self):
        from codex_wake.controller_tab_adapters import PsmuxAttachmentTransport
        import time
        generation = ['fixture-1']
        calls = []
        def bridge(action, args, deadline):
            calls.append((action,args))
            return dict(generation=generation[0],result=Transport().snapshot(deadline) if action=='snapshot' else 'fixture output')
        transport = PsmuxAttachmentTransport(bridge,generation='fixture-1')
        with tempfile.TemporaryDirectory() as directory:
            owner = ControllerTabs(directory, workspaces={'fixture':dict(transport=transport,kind='psmux')},host='h',environment='fixture')
            row = owner.execute('tabs.list', {})['resources'][0]
            result = owner.execute('tabs.capture', dict(workspace='fixture',expected_target=row['target'],pane='%1',lines=2))
            self.assertEqual(result['text'],'fixture output')
            self.assertEqual(calls[-1],('capture',{'pane':'%1','lines':2}))
            generation[0] = 'replacement'
            with self.assertRaises(InventoryError): owner.execute('tabs.list',{})
