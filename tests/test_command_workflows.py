"""Public CLI workflows at native-process and terminal seams."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from codex_wake.cli import main


class Terminal(io.StringIO):
    def isatty(self):
        return True


class CommandWorkflowsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'accounts/codex-alice').mkdir(parents=True)
        self.binary = self.root / 'native'
        self.binary.write_text('#!/bin/sh\ntouch "'+str(self.root/'effect')+'"\nmkdir -p "$CODEX_HOME/packages/app-server-daemon/current/bin"\ncp "$0" "$CODEX_HOME/packages/app-server-daemon/current/bin/codex"\nprintf \'{"status":"updated"}\\n\'\n')
        self.binary.chmod(0o700)
        self.manifest = self.root / 'builds.json'
        self.manifest.write_text(json.dumps({'schema_version':1,'builds':{'modded':{'executable':str(self.binary),'sha256':hashlib.sha256(self.binary.read_bytes()).hexdigest(),'upstream_version':'0.166.0','revision':'fixture','source':'fixture','read_schemas':[5],'backend':'managed'}}}))
        self.config = self.root / 'controller-accounts.toml'
        self.config.write_text('[profiles]\nstate_root='+json.dumps(str(self.root/'accounts'))+'\nknown_profiles=["alice"]\n[builds]\nmanifest='+json.dumps(str(self.manifest))+'\n')

    def cli(self, *args, stdin=None, terminal=False):
        out = Terminal() if terminal else io.StringIO()
        err = io.StringIO()
        with patch('sys.stdin', stdin or io.StringIO()), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(['--wake-root',str(self.root),*args,'--json'])
        return code, out.getvalue(), err.getvalue()

    def test_typed_build_list_matches_legacy_json_arguments(self):
        code, output, _ = self.cli('builds','list','--account','alice')
        self.assertEqual(code,0,output)
        old_code, old_output, _ = self.cli('builds','list','--arguments','{"account":"alice"}')
        self.assertEqual(old_code,0,old_output)
        self.assertEqual(json.loads(output),json.loads(old_output))

    def test_interactive_update_shows_target_and_decline_has_no_effect(self):
        code, output, error = self.cli('daemons','update','alice',stdin=Terminal('no\n'),terminal=True)
        self.assertEqual(code,2,output)
        self.assertEqual(json.loads(output)['error']['code'],'confirmation_required')
        self.assertIn('codex-alice',error)
        self.assertIn(str(self.root/'accounts/codex-alice'),error)
        self.assertIn('Intent key:',error)
        self.assertFalse((self.root/'effect').exists())

    def test_noninteractive_daemon_convenience_never_submits(self):
        code, output, _ = self.cli('daemons','update','alice','--yes')
        self.assertEqual(code,2)
        self.assertEqual(json.loads(output)['error']['code'],'explicit_target_required')
        self.assertFalse((self.root/'effect').exists())

    def test_interactive_update_accepts_once_and_changed_home_is_refused(self):
        parent = self
        class ReplacingTerminal(Terminal):
            def readline(self, *args):
                home = parent.root/'accounts/codex-alice'
                home.rename(parent.root/'accounts/retired-alice')
                home.mkdir()
                return 'yes\n'
        code, output, _ = self.cli('daemons','update','alice',stdin=ReplacingTerminal(),terminal=True)
        self.assertEqual(code,2,output)
        self.assertEqual(json.loads(output)['error']['code'],'stale_target')
        self.assertFalse((self.root/'effect').exists())
        code, output, error = self.cli('daemons','update','alice',stdin=Terminal('yes\n'),terminal=True)
        self.assertEqual(code,0,output)
        self.assertIn('selected account daemon',error)
        self.assertEqual(json.loads(output)['result']['operation']['result']['activation'],'future_start')
        self.assertTrue((self.root/'effect').exists())

    def test_build_named_argument_conflict_is_not_silently_overridden(self):
        code, output, _ = self.cli('builds','list','--account','alice','--arguments','{"account":"someone-else"}')
        self.assertEqual(code,2)
        self.assertEqual(json.loads(output)['error']['code'],'invalid_argument')
        self.assertIn('conflicts',json.loads(output)['error']['message'])

    def test_interactive_import_decline_preserves_source_and_destination(self):
        import sqlite3
        source_id = '01a123a8-5782-7d43-a214-55b293bbd65f'
        sessions = self.root/'accounts/codex-alice/sessions'
        sessions.mkdir()
        source = sessions/'source.jsonl'
        source.write_text(json.dumps({'type':'session_meta','payload':{'id':source_id}})+'\n')
        with sqlite3.connect(sessions.parent/'state_5.sqlite') as db:
            db.execute('create table threads (id text primary key,cwd text,title text,rollout_path text)')
            db.execute('insert into threads values(?,?,?,?)',(source_id,str(self.root),'test',str(source)))
        (self.root/'accounts/codex-bob').mkdir()
        config = self.config.read_text().replace('known_profiles=["alice"]','known_profiles=["alice","bob"]')
        self.config.write_text(config+'\n[history]\nreadable_accounts=["alice","bob"]\n')
        before = source.read_bytes()
        code, output, error = self.cli('history','import',source_id,'--owner','alice','--destination','bob',stdin=Terminal('no\n'),terminal=True)
        self.assertEqual(code,2,output)
        self.assertEqual(json.loads(output)['error']['code'],'confirmation_required')
        self.assertIn('Source target:',error)
        self.assertIn('codex-bob',error)
        self.assertEqual(source.read_bytes(),before)
        self.assertFalse((self.root/'effect').exists())

    def test_real_terminal_update_resolves_and_confirms_the_selected_account(self):
        import os
        import pty
        import select
        import subprocess
        import sys
        import time
        master, slave = pty.openpty()
        process = subprocess.Popen([sys.executable,'-m','codex_wake.entrypoint','--wake-root',str(self.root),
                                    'daemons','update','alice','--json'],stdin=slave,stdout=slave,stderr=slave)
        os.close(slave)
        content = b''
        answered = False
        deadline = time.monotonic()+10
        try:
            while time.monotonic()<deadline:
                if select.select([master],[],[],.1)[0]:
                    try:
                        chunk = os.read(master,65536)
                    except OSError:
                        break
                    content += chunk
                    if b'Continue? [y/N]' in content and not answered:
                        os.write(master,b'yes\n')
                        answered = True
                if process.poll() is not None:
                    while select.select([master],[],[],0)[0]:
                        try:
                            content += os.read(master,65536)
                        except OSError:
                            break
                    break
            self.assertEqual(process.wait(timeout=1),0,content.decode())
            self.assertTrue(answered,content.decode())
            self.assertIn(b'"execution": "completed"',content)
            self.assertTrue((self.root/'effect').exists())
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=5)
            os.close(master)


if __name__ == '__main__':
    unittest.main()
