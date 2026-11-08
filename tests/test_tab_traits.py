import os
from pathlib import Path
import tempfile
import time
import unittest

from codex_wake.process import process_identity


class TabTraitsTests(unittest.TestCase):
    def test_public_window_observation_keeps_activity_health_and_error_separate(self):
        from codex_wake.tab_traits import TabTraits
        birth = process_identity(os.getpid())
        process = dict(pid=os.getpid(), start_ticks=birth['start_time_ticks'], boot_id=birth['boot_id'])
        window = dict(window_id='@1', name='Grok title is not evidence', panes=[dict(pane_id='%1', pid=os.getpid())])
        evidence = {'%1': dict(runtime='codex', state='working', conversation_id='thread', namespace='account',
                               root='/work', account='alice', process=process, observed_at=time.time(), fresh=True)}
        with tempfile.TemporaryDirectory() as directory:
            result = TabTraits(directory).observe_window(window, evidence=evidence, deadline=time.monotonic()+1)
        traits = result['panes'][0]['traits']
        self.assertEqual(traits['harness']['value'], 'codex')
        self.assertEqual(traits['session_presence']['value'], 'present')
        self.assertEqual(traits['activity']['value'], 'running')
        self.assertEqual(traits['health']['value'], 'unknown')
        self.assertEqual(traits['error']['value'], 'unknown')
        self.assertNotIn('Grok title', str(traits))

    def test_real_registered_executable_and_ssh_are_not_inferred_from_titles(self):
        import hashlib
        import json
        import shutil
        import subprocess
        from codex_wake.tab_traits import TabTraits
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package = root / 'bin/codex'
            package.parent.mkdir()
            shutil.copyfile('/bin/sleep', package)
            package.chmod(0o700)
            manifest = root / 'builds.json'
            manifest.write_text(json.dumps(dict(schema_version=1, builds=dict(modded=dict(
                executable=str(package), sha256=hashlib.sha256(package.read_bytes()).hexdigest(),
                upstream_version='synthetic', revision='synthetic', source='synthetic')))))
            (root / 'controller-accounts.toml').write_text('[builds]\nmanifest="' + str(manifest) + '"\n')
            process = subprocess.Popen([str(package), '30'])
            try:
                owner = TabTraits(root)
                result = owner.observe_window(dict(window_id='@1', name='stock ssh grok',
                              panes=[dict(pane_id='%1', pid=process.pid)]), deadline=time.monotonic()+1)
                traits = result['traits']
                self.assertEqual(traits['harness']['value'], 'codex')
                self.assertEqual(traits['build']['value'], 'modded')
                self.assertEqual(traits['activity']['value'], 'unknown')
                self.assertEqual(traits['remote_host']['value'], 'unknown')
            finally:
                process.terminate(); process.wait(timeout=3)

    def test_structured_stale_or_replaced_process_cannot_establish_current_activity(self):
        from codex_wake.tab_traits import TabTraits
        birth = process_identity(os.getpid())
        window = dict(window_id='@1', panes=[dict(pane_id='%1', pid=os.getpid())])
        sample = dict(runtime='codex', conversation_id='thread', namespace='private', state='working',
                      process=dict(pid=os.getpid(), start_ticks=birth['start_time_ticks'], boot_id=birth['boot_id']),
                      observed_at=1, fresh=True)
        with tempfile.TemporaryDirectory() as directory:
            owner = TabTraits(directory, clock=lambda: 100)
            result = owner.observe_window(window, evidence={'%1':sample}, deadline=time.monotonic()+1)
            self.assertEqual(result['traits']['activity']['status'], 'stale')
            self.assertIsNone(result['panes'][0]['binding'])
            sample['process'] = dict(sample['process'], start_ticks=-1)
            result = owner.observe_window(window, evidence={'%1':sample}, deadline=time.monotonic()+1)
            self.assertEqual(result['traits']['activity']['value'], 'unknown')

    def test_real_visible_errors_exclude_red_text_and_old_scrollback_without_input(self):
        import shutil
        import subprocess
        from codex_wake.controller_tab_adapters import TmuxAttachmentTransport
        from codex_wake.tab_traits import TabTraits
        if not shutil.which('tmux'):
            self.skipTest('tmux unavailable')
        with tempfile.TemporaryDirectory() as directory:
            socket = str(Path(directory) / 'tmux.sock')
            def tmux(*args):
                return subprocess.check_output(['tmux','-S',socket,*args], text=True)
            command = "printf '\\033[10;1H\\033[31mError: connection failed\\033[0m\\nREADY'; exec sleep 60"
            tmux('new-session','-d','-x','80','-y','12','-s','fixture',command)
            try:
                until = time.monotonic()+3
                while 'READY' not in tmux('capture-pane','-p','-t','%0'):
                    self.assertLess(time.monotonic(), until)
                    time.sleep(.01)
                transport = TmuxAttachmentTransport(socket, '$0')
                window = transport.snapshot(time.monotonic()+2)['windows'][0]
                before = tmux('capture-pane','-p','-e','-t','%0')
                owner = TabTraits(directory)
                result = owner.observe_window(window, transport=transport, privacy=lambda pane:'safe',deadline=time.monotonic()+2)
                error = result['traits']['error']
                self.assertEqual(error['value'], 'present')
                self.assertEqual(error['message'], 'Error: connection failed')
                self.assertEqual(error['location']['region'], 'bottom')
                self.assertEqual(result['traits']['health']['value'], 'unknown')
                self.assertEqual(before, tmux('capture-pane','-p','-e','-t','%0'))
                unknown = owner.observe_window(window,transport=transport,deadline=time.monotonic()+1)
                self.assertEqual(unknown['traits']['error']['value'], 'unknown')
                for name, command in (
                    ('red', "printf '\\033[31mordinary red text\\033[0m\\nREADY'; exec sleep 60"),
                    ('history', "printf 'Error: old scrollback\\n'; seq 1 30; printf 'Resolved: connection is healthy\\nREADY'; exec sleep 60")):
                    tmux('new-window','-d','-n',name,command)
                    target = tmux('list-panes','-t','fixture:'+name,'-F','#{pane_id}').strip()
                    until = time.monotonic()+3
                    while 'READY' not in tmux('capture-pane','-p','-t',target):
                        self.assertLess(time.monotonic(),until);time.sleep(.01)
                    window = next(w for w in transport.snapshot(time.monotonic()+2)['windows'] if w['name']==name)
                    result = owner.observe_window(window,transport=transport,privacy=lambda pane:'safe',deadline=time.monotonic()+2)
                    self.assertEqual(result['traits']['error']['value'], 'absent',name)
            finally:
                tmux('kill-server')

    def test_native_session_reader_binds_fresh_activity_and_separate_health(self):
        import socket
        from types import SimpleNamespace
        from codex_wake.tab_traits import TabTraits, session_rows
        birth = process_identity(os.getpid())
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            native_home = root / 'codex-alice';native_home.mkdir()
            endpoint = root / 'native.sock'
            server = socket.socket(socket.AF_UNIX);server.bind(str(endpoint))
            left, right = socket.socketpair()
            pane = dict(pane_id='%1', window_id='@1', window_name='native', pane_title='native',
                        pane_current_path=str(root), client_pid=os.getpid(), client_start_time_ticks=birth['start_time_ticks'])
            budgets = []
            class NativeReader:
                def __init__(self, address, *, timeout):
                    budgets.append(timeout);self.path=endpoint
                    self.connection=SimpleNamespace(socket=left)
                    self.server_metadata={'codexHome':str(native_home)}
                def __enter__(self):return self
                def __exit__(self,*args):return False
                def loaded_threads(self,maximum):
                    return [dict(id='thread',name='native',cwd=str(root),status=dict(type='active',activeFlags=['waitingOnUserInput']))]
            def health(root,row,*,timeout):
                return dict(observation=dict(status='responsive',evidence='tui_main_loop_ack',observed_at=time.time()))
            try:
                view=session_rows(root, endpoints=['unix://'+str(endpoint)],panes=[pane],
                                  deadline=time.monotonic()+1,reader_factory=NativeReader)
                self.assertEqual(view['status'],'complete')
                self.assertTrue(0 < budgets[0] <= 1)
                owner=TabTraits(root,sessions=view['sessions'],health_probe=health)
                result=owner.observe_window(dict(window_id='@1',panes=[dict(pane_id='%1',pid=os.getpid())]),deadline=time.monotonic()+1)
                traits=result['traits']
                self.assertEqual(traits['activity']['value'],'waiting-for-input')
                self.assertEqual(traits['health']['value'],'responsive')
                self.assertEqual(traits['account']['value'],'codex-alice')
                self.assertEqual(result['panes'][0]['binding']['conversation_id'],'thread')
                view['sessions'][0]['active_flags'] = []
                running = TabTraits(root,sessions=view['sessions'],health_probe=health).observe_window(
                    dict(window_id='@1',panes=[dict(pane_id='%1',pid=os.getpid())]),deadline=time.monotonic()+1)
                self.assertEqual(running['traits']['activity']['value'],'running')
                self.assertEqual(running['panes'][0]['binding']['state'],'working')
                expired=session_rows(root,endpoints=['unix://'+str(endpoint)],panes=[pane],deadline=time.monotonic()-1,reader_factory=NativeReader)
                self.assertEqual(expired['status'],'partial')
                self.assertEqual(expired['sessions'],[])
            finally:
                left.close();right.close();server.close()

    def test_ssh_operand_and_mixed_panes_retain_unknown_remote_harness(self):
        from codex_wake.tab_traits import TabTraits
        birth=process_identity(os.getpid())
        identity=dict(pid=os.getpid(),start_ticks=birth['start_time_ticks'],boot_id=birth['boot_id'])
        def process_probe(pid,deadline):
            if pid==1:
                return [dict(pid=os.getpid(),process=identity,executable='/usr/bin/ssh',
                             argv=['ssh','-p','2222','-o','PasswordAuthentication=no','operator@research-host','codex'],cwd='/tmp')],True
            return [],False
        with tempfile.TemporaryDirectory() as directory:
            result=TabTraits(directory,process_probe=process_probe).observe_window(
                dict(window_id='@1',panes=[dict(pane_id='%1',pid=1),dict(pane_id='%2',pid=2)]),deadline=time.monotonic()+1)
        self.assertEqual(result['panes'][0]['traits']['remote_host']['value'],'research-host')
        self.assertEqual(result['panes'][0]['traits']['harness']['value'],'unknown')
        self.assertEqual(result['traits']['remote_host']['value'],'mixed')
        self.assertTrue(result['mixed'])
