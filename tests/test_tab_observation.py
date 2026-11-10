"""Public inventory regression: one process investigation across native enrichment."""
import os
import tempfile
import time
import unittest
from pathlib import Path

from codex_wake.controller_tabs import ControllerTabs
from codex_wake.process import process_identity


class ObservationTests(unittest.TestCase):
    def test_inventory_reuses_investigation_and_invalidates_on_source_generation(self):
        from codex_wake.tab_observation import ObservationCache
        calls = []
        birth = process_identity(os.getpid())
        def processes(pid, deadline):
            calls.append(pid)
            return [dict(process=dict(pid=pid, start_ticks=birth['start_time_ticks'], boot_id=birth['boot_id']),
                         executable='/bin/sleep', argv=['sleep'], cwd='/tmp')], True
        class Transport:
            generation = 1
            def snapshot(self, deadline):
                return dict(server='fixture', session_id='$1', socket_identity=[1,self.generation],
                            windows=[dict(window_id='@1',name='fixture',panes=[dict(pane_id='%1',pid=os.getpid())])])
        with tempfile.TemporaryDirectory() as directory:
            transport = Transport()
            cache = ObservationCache(directory, process_probe=processes)
            owner = ControllerTabs(directory, workspaces={'fixture':dict(kind='tmux', transport=transport)},
                                   host='fixture', environment='fixture', observation_cache=cache)
            first = owner.execute('tabs.list', {})
            second = owner.execute('tabs.list', {})
            self.assertEqual(first['resources'][0]['traits'], second['resources'][0]['traits'])
            self.assertEqual(calls, [os.getpid()])
            transport.generation = 2
            owner.execute('tabs.list', {})
            self.assertEqual(calls, [os.getpid(), os.getpid()])

    def test_cache_expiry_and_replaced_birth_never_reuse_old_process(self):
        from codex_wake.tab_observation import ObservationCache
        calls=[]; now=[0.0]; generation=[1]
        def identity(pid):
            return dict(pid=pid, start_time_ticks=generation[0], boot_id='fixture')
        def processes(pid, deadline):
            calls.append(generation[0])
            return [], True
        cache=ObservationCache(Path('/tmp'),process_probe=processes,identity_probe=identity,monotonic=lambda:now[0])
        cache.processes(42,time.monotonic()+1)
        cache.processes(42,time.monotonic()+1)
        generation[0]=2
        cache.processes(42,time.monotonic()+1)
        now[0]=3
        cache.processes(42,time.monotonic()+1)
        self.assertEqual(calls,[1,2,2])

    def test_native_metadata_enriches_the_same_investigated_pane_once(self):
        from codex_wake.tab_observation import ObservationCache
        birth=process_identity(os.getpid()); calls=[]; inventories=[]
        def processes(pid,deadline):
            calls.append(pid)
            return [dict(process=dict(pid=pid,start_ticks=birth['start_time_ticks'],boot_id=birth['boot_id']),
                         executable='/fixture/codex',argv=['codex'],cwd='/tmp')],True
        def reader(root,**options):
            inventories.append(options['panes'])
            return dict(holds=[],sessions=[dict(target=dict(provider='codex',account='fixture',conversation_id='thread'),
                runtime_state='active',active_flags=[],cwd='/tmp',attachments=[dict(pane_id='%1',
                client_pid=os.getpid(),client_start_time_ticks=birth['start_time_ticks'])])])
        with tempfile.TemporaryDirectory() as directory:
            cache=ObservationCache(directory,process_probe=processes,session_reader=reader)
            snapshot=dict(server='fixture',session_id='$1',socket_identity=[1,2],windows=[dict(window_id='@1',
                name='fixture',panes=[dict(pane_id='%1',pid=os.getpid(),pane_title='thread',pane_current_path='/tmp')])])
            result,_=cache.observe('fixture',snapshot,deadline=time.monotonic()+1)
            self.assertEqual(result['@1']['traits']['activity']['value'],'running')
            self.assertEqual(calls,[os.getpid()])
            self.assertEqual(len(inventories),1)
            self.assertEqual(inventories[0][0]['client_pid'],os.getpid())
