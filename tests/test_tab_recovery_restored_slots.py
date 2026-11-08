"""Restored shell placement is not conversation identity and must remain intact."""
import shutil
import subprocess
import tempfile
from pathlib import Path
import unittest

from codex_wake.controller_tabs import ControllerTabs
from codex_wake.controller_tab_adapters import TmuxAttachmentTransport
from codex_wake.tab_recovery import TabRecovery,WorkspaceRecoveryRuntime,_MARKER


@unittest.skipUnless(shutil.which('tmux'),'tmux unavailable')
class RestoredSlotTests(unittest.TestCase):
    def test_restored_owned_shell_is_preserved_while_exact_conversation_reclaims_slot(self):
        for marked,busy in ((True,False),(False,False),(True,True)):
            with self.subTest(marked=marked,busy=busy),tempfile.TemporaryDirectory() as directory:
                root=Path(directory);sock=str(root/'tmux.sock')
                def tm(*args):return subprocess.check_output(['tmux','-S',sock,*args],text=True).strip()
                tm('new-session','-d','-s','fixture','-n','notes','sleep 120')
                try:
                    tm('set-option','-g','automatic-rename','off')
                    original=tm('new-window','-d','-P','-F','#{window_id}','-t','$0:1','-n','coding','-c',directory,'sleep 120')
                    transport=TmuxAttachmentTransport(sock,'$0')
                    tabs=ControllerTabs(root,workspaces={'fixture':dict(kind='tmux',transport=transport)},host='fixture',environment='fixture')
                    class Runtime(WorkspaceRecoveryRuntime):
                        calls=0
                        attached=original
                        def capture(self,context):
                            return {w['window_id']:(dict(kind='codex',identity=dict(runtime='codex',namespace='account',conversation_id='exact',root=directory),profile=dict(cwd=directory,timeout=1)) if w['name']=='coding' else dict(kind='noncoding')) for w in context['windows']}
                        def identity(self,record,context):return record['identity']
                        def binding(self,record,context):return dict(state='ready' if self.attached else 'absent',window_id=self.attached)
                    runtime=Runtime(root,tabs)
                    class Saved:
                        def launch(self,record,profile,guard,name):
                            guard();runtime.calls+=1
                            value=tm('new-window','-d','-P','-F','#{window_id}\t#{pane_id}','-t','$0:','-n',name,'-c',directory,'sleep 120')
                            runtime.attached=value.split('\t')[0]
                            return value
                    runtime.saved=Saved()
                    owner=TabRecovery(root,tabs=tabs,runtime=runtime)
                    captured=owner.execute('tabs.recovery.capture',dict(workspace='fixture',capture_id='saved'))
                    logical=next(r['logical_id'] for r in captured['snapshot']['rows'] if r['kind']=='codex')
                    tm('kill-window','-t',original);runtime.attached=None
                    command='bash --noprofile --norc -c \"sleep 120 & wait\"' if busy else 'bash --noprofile --norc -i'
                    restored=tm('new-window','-d','-P','-F','#{window_id}','-t','$0:1','-n','coding','-c',directory,command)
                    pane=tm('display-message','-p','-t',restored,'#{pane_id}')
                    pid=tm('display-message','-p','-t',restored,'#{pane_pid}')
                    if marked:tm('set-option','-w','-t',restored,_MARKER,logical)
                    if busy:
                        held=owner.execute('tabs.recovery.preview',dict(workspace='fixture',capture_id='saved',restore_layout=True))
                        self.assertEqual(held['status'],'held')
                        self.assertEqual(runtime.calls,0)
                        continue
                    tm('send-keys','-l','-t',pane,'UNSUBMITTED_SYNTHETIC_DRAFT')
                    tabs.workspaces['fixture']['pins']=[restored]
                    pinned=owner.execute('tabs.recovery.preview',dict(workspace='fixture',capture_id='saved',restore_layout=True))
                    self.assertEqual(pinned['status'],'held')
                    self.assertEqual(tm('display-message','-p','-t',restored,'#{window_name}'),'coding')
                    tabs.workspaces['fixture']['pins']=[]
                    preview=owner.execute('tabs.recovery.preview',dict(workspace='fixture',capture_id='saved',restore_layout=True))
                    self.assertEqual(preview['status'],'ready',preview)
                    row=next(r for r in preview['rows'] if r['kind']=='codex')
                    self.assertEqual(row['restored_slot']['window_id'],restored)
                    args=dict(workspace='fixture',capture_id='saved',restore_layout=True,intent='restore-once',expected_target=preview['target'])
                    result=owner.execute('tabs.recovery.apply',args)
                    self.assertEqual(result['status'],'completed',result)
                    windows=transport.snapshot(__import__('time').monotonic()+2)['windows']
                    coding=next(w for w in windows if w['name']=='coding')
                    self.assertEqual(coding['index'],1)
                    self.assertNotEqual(coding['window_id'],restored)
                    self.assertEqual(tm('display-message','-p','-t',pane,'#{pane_pid}'),pid)
                    self.assertIn('UNSUBMITTED_SYNTHETIC_DRAFT',tm('capture-pane','-p','-t',pane))
                    self.assertTrue(owner.execute('tabs.recovery.apply',args)['replayed'])
                    self.assertEqual(runtime.calls,1)
                finally:subprocess.run(['tmux','-S',sock,'kill-server'],capture_output=True)
