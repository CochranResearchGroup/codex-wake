"""Refresh safety through the public lifecycle CLI."""
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import hashlib
import json
import tempfile
import os
import pty
import subprocess
import sys
import threading
from unittest.mock import patch
from websockets.sync.server import unix_serve
import unittest

from codex_wake.cli import run
from codex_wake.records import WakeError


class AgentRefreshTests(unittest.TestCase):
    def test_changed_checkpoint_is_rejected_before_runtime_or_journal_effects(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            checkpoint = root / 'checkpoint.json'
            checkpoint.write_text('{"source_thread_id":"00000000-0000-7000-8000-000000000158"}')
            original = hashlib.sha256(checkpoint.read_bytes()).hexdigest()
            checkpoint.write_text('{"source_thread_id":"changed"}')
            profiles = root / 'profiles.json'
            profiles.write_text(json.dumps({'version': 1, 'profiles': {'worker': dict(
                cwd=tmp, app_server='unix:///missing.sock', codex_path='/bin/true',
                tmux_session='owned', timeout=1)}}))
            argv = ['--wake-root', tmp, 'sessions', 'refresh', '--profiles', str(profiles),
                    '--profile', 'worker', '--intent', 'refresh-1', '--thread-id',
                    '00000000-0000-7000-8000-000000000158', '--checkpoint', 'checkpoint.json',
                    '--checkpoint-sha256', original, '--resource', 'updated-skill',
                    '--expires-at', '2030-01-01T00:00:00Z', '--json']
            with redirect_stdout(StringIO()), self.assertRaisesRegex(WakeError, 'checkpoint hash'):
                run(argv)
            self.assertFalse((root / 'lifecycle').exists())

    def test_local_draft_preserves_old_generation_and_blocks_refresh(self):
        self.refresh_scenario(draft=True)

    def test_refresh_resumes_same_thread_and_proves_changed_skill_catalog(self):
        self.refresh_scenario(draft=False)

    def test_new_client_with_old_mcp_behavior_blocks_full_refresh(self):
        self.refresh_scenario(draft=False, stale_mcp=True)

    def test_lost_new_tab_response_reconciles_existing_refresh_without_replacement(self):
        self.refresh_scenario(draft=False, loss='new-window')

    def test_lost_stop_response_observes_old_exit_without_stopping_twice(self):
        self.refresh_scenario(draft=False, loss='kill-pane')

    def test_fixed_expiry_after_stop_prevents_replacement_without_reset(self):
        self.refresh_scenario(draft=False, expire_after_stop=True)

    def test_unapproved_probe_is_rejected_before_stopping_original_client(self):
        self.refresh_scenario(draft=False, stale_mcp=True, unapproved_probe=True)

    def refresh_scenario(self, *, draft, stale_mcp=False, loss=None, expire_after_stop=False, unapproved_probe=False):
        thread_id = '00000000-0000-7000-8000-000000000158'
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            client_script = root / 'codex'
            client_script.write_text(f'#!{sys.executable}\nimport ctypes,time\n'
                "ctypes.CDLL(None).prctl(15,b'codex',0,0,0)\n"
                "print('ready',flush=True)\ntime.sleep(60)\n")
            client_script.chmod(0o700)
            master, slave = pty.openpty()
            client = subprocess.Popen([str(client_script)], stdin=slave, stdout=subprocess.PIPE)
            self.assertEqual(client.stdout.readline(), b'ready\n')
            tty = os.ttyname(slave)
            endpoint = root / 'native.sock'
            methods, effects = [], []
            original_pid = client.pid
            tab = {'name':'worker'}
            skill = root / 'skill.md'
            skill.write_text('---\nname: updated-skill\ndescription: Updated fixture\n---\nChanged instructions.\n')
            goal = dict(objective='Finish fixture', status='paused', tokenBudget=1000,
                        tokensUsed=50, timeUsedSeconds=12, createdAt=100, updatedAt=100)
            def handler(ws):
                for raw in ws:
                    request = json.loads(raw)
                    if 'id' not in request: continue
                    method = request['method']; methods.append(method)
                    if method == 'thread/loaded/list':
                        value = dict(data=[thread_id], nextCursor=None)
                    elif method == 'thread/read':
                        value = dict(thread=dict(id=thread_id, name='owned-worker', cwd=tmp,
                            status={'type':'idle'}, canAcceptDirectInput=True, turns=[]))
                    elif method == 'thread/goal/get': value = {'goal': goal}
                    elif method == 'mcpServer/tool/call':
                        value = {'content':[{'type':'text','text':'old-version'}],'isError':False}
                    elif method == 'skills/list': value = {'data': [dict(cwd=tmp, errors=[], skills=[
                        dict(name='updated-skill',path=str(skill),description='Updated fixture',enabled=True)])]}
                    else: value = {}
                    ws.send(json.dumps(dict(id=request['id'],result=value)))
            def command(argv, **kwargs):
                nonlocal client
                if 'list-panes' in argv:
                    value = ('%158' if '-a' not in argv else '\t'.join([
                        '$1','owned','@158','1',tab['name'],'%158','0','owned-worker',tmp,tty]))
                elif 'capture-pane' in argv:
                    text = 'UNSUBMITTED_DRAFT_158' if draft else '\x1b[2mAsk Codex to do anything\x1b[0m'
                    value = '\n\n\x1b[1m›\x1b[0m ' + text + '\n'
                elif 'display-message' in argv: value = '23,2' if draft else '2,2'
                elif 'kill-pane' in argv:
                    effects.append(argv); client.terminate();client.wait(timeout=2);client.stdout.close();value=''
                    if loss == 'kill-pane':raise subprocess.TimeoutExpired(argv,1)
                elif 'new-window' in argv:
                    effects.append(argv)
                    tab['name']=argv[argv.index('-n')+1]
                    client=subprocess.Popen(['sh','-c','exec '+argv[-1]],stdin=slave,stdout=subprocess.PIPE)
                    self.assertEqual(client.stdout.readline(),b'ready\n');value='@158\t%158'
                    if loss == 'new-window':raise subprocess.TimeoutExpired(argv,1)
                else:
                    effects.append(argv); value = ''
                return subprocess.CompletedProcess(argv,0,value,'')
            checkpoint = root / 'checkpoint.json'
            checkpoint.write_text(json.dumps(dict(source_thread_id=thread_id, objective='Finish fixture',
                authority='operator fixture', next_packet='Check skill', pending_obligations=[])))
            profiles = root / 'profiles.json'
            profiles.write_text(json.dumps({'version':1,'profiles':{'worker':dict(cwd=tmp,
                app_server='unix://'+str(endpoint),codex_path=str(client_script),tmux_session='owned',
                timeout=1,resources={'updated-skill':dict(kind='skill',path=str(skill),
                    description='Updated fixture',sha256=hashlib.sha256(skill.read_bytes()).hexdigest())})}}))
            if stale_mcp:
                registry=json.loads(profiles.read_text())
                registry['profiles']['worker']['resources']['updated-skill']=dict(kind='mcp',
                    server='fixture',tool='version',arguments={},read_only=not unapproved_probe,
                    expected_content=[{'type':'text','text':'new-version'}])
                profiles.write_text(json.dumps(registry))
            argv = ['--wake-root',tmp,'sessions','refresh','--profiles',str(profiles),
                '--profile','worker','--intent','refresh-1','--thread-id',thread_id,
                '--checkpoint','checkpoint.json','--checkpoint-sha256',
                hashlib.sha256(checkpoint.read_bytes()).hexdigest(),'--resource','updated-skill',
                '--expires-at','2030-01-01T00:00:00Z','--json']
            try:
                with unix_serve(handler,str(endpoint)) as server:
                    worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
                    try:
                        with patch('subprocess.run',side_effect=command), patch(
                                'codex_wake.native_clock.snapshot',side_effect=lambda: {'utc':{'upper':
                                    1893456001 if expire_after_stop and client.poll() is not None else 1001}}):
                            if unapproved_probe:
                                with redirect_stdout(StringIO()),self.assertRaisesRegex(WakeError,'read-only'):
                                    run(argv)
                                self.assertEqual(effects,[])
                                self.assertIsNone(client.poll())
                                self.assertFalse((root/'lifecycle').exists())
                                return
                            if loss:
                                first=StringIO()
                                with redirect_stdout(first):self.assertEqual(run(argv),5)
                                held=json.loads(first.getvalue())
                                self.assertEqual(held['state'],'uncertain')
                                self.assertEqual(held['uncertain_effect'],'tmux/'+loss)
                            output=StringIO()
                            with redirect_stdout(output): self.assertEqual(run(argv),5 if draft or stale_mcp or expire_after_stop else 0,output.getvalue())
                            receipt=json.loads(output.getvalue())
                            if expire_after_stop:
                                self.assertEqual(receipt['state'],'expired')
                                self.assertEqual(sum('kill-pane' in x for x in effects),1)
                                self.assertFalse(any('new-window' in x for x in effects))
                                count=len(effects)
                                with redirect_stdout(StringIO()):self.assertEqual(run(argv),5)
                                self.assertEqual(len(effects),count)
                            elif draft:
                                self.assertEqual(receipt['state'],'blocked')
                                self.assertEqual(receipt['reason'],'local_composer_not_proven_empty')
                                self.assertEqual(effects,[])
                                self.assertIsNone(client.poll())
                            elif stale_mcp:
                                self.assertEqual(receipt['state'],'blocked')
                                self.assertNotEqual(client.pid,original_pid)
                                self.assertEqual(receipt['resources']['updated-skill']['observed_content'],
                                    [{'type':'text','text':'old-version'}])
                                self.assertEqual(methods.count('mcpServer/tool/call'),1)
                                self.assertEqual(receipt['goal_after'],goal)
                            else:
                                self.assertEqual(receipt['state'],'completed')
                                self.assertEqual(sum('new-window' in x for x in effects),1)
                                self.assertEqual(sum('kill-pane' in x for x in effects),1)
                                self.assertEqual(receipt['thread_id'],thread_id)
                                self.assertNotEqual(client.pid,original_pid)
                                self.assertEqual(receipt['goal_before'],goal)
                                self.assertEqual(receipt['goal_after'],goal)
                                self.assertEqual(receipt['resources']['updated-skill']['state'],'ready')
                                count=len(effects)
                                with redirect_stdout(StringIO()):self.assertEqual(run(argv),0)
                                self.assertEqual(len(effects),count)
                            self.assertFalse(any(x in methods for x in ('thread/start','turn/start','thread/goal/set')))
                    finally:server.shutdown();worker.join(timeout=2)
            finally:
                client.terminate();client.wait(timeout=2);client.stdout.close()
                os.close(master);os.close(slave)
