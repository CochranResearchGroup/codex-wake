"""Account shortcut behavior at existing public CLI/history/native seams."""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch


class ShortcutTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root / 'accounts/codex-alice'
        (self.home / 'sessions').mkdir(parents=True, mode=0o700)
        self.config = self.root / 'controller-accounts.toml'
        self.config.write_text(f'[profiles]\nstate_root="{self.root / "accounts"}"\nknown_profiles=["alice"]\n[history]\nreadable_accounts=["alice"]\n')
        self.ids = ['00000000-0000-4000-8000-000000000001', '00000000-0000-4000-8000-000000000002']
        with sqlite3.connect(self.home / 'state_5.sqlite') as db:
            db.execute('create table threads(id text,cwd text,title text,rollout_path text,updated_at integer)')
            for tid,stamp in zip(self.ids, [10,20]):
                path=self.home/'sessions'/(tid+'.jsonl')
                path.write_text(json.dumps({'type':'session_meta','payload':{'id':tid}})+'\n')
                db.execute('insert into threads values(?,?,?,?,?)',(tid,str(self.root),'title '+tid[-1],str(path),stamp))

    def test_recent_limits_before_opening_older_unavailable_rollouts(self):
        from codex_wake.controller_history import ControllerHistory
        (self.home/'sessions'/(self.ids[0]+'.jsonl')).unlink()
        owner=ControllerHistory(self.config,root=self.root,host='fixture',environment='test',authorized_accounts=['alice'])
        result=owner.execute('history.search',{'owners':['alice'],'sort':'recent','limit':1})
        self.assertEqual([s['thread_id'] for s in result['sessions']],[self.ids[1]])
        self.assertEqual(result['holds'],[])
        self.assertEqual(result['sessions'][0]['recency_source'],'native_updated_at')

    def build_fixture(self, backend='private'):
        shared=self.root/'shared';shared.mkdir(mode=0o700,exist_ok=True)
        executable=self.root/'native'
        executable.write_text('#!/usr/bin/env python3\nimport os,json,sys\nfrom pathlib import Path\nPath(os.environ["CODEX_HOME"],"native-result").write_text(json.dumps({"home":os.environ["CODEX_HOME"],"args":sys.argv[1:]}))\nsys.exit(7)\n')
        executable.chmod(0o700)
        manifest=self.root/'builds.json'
        manifest.write_text(json.dumps({'schema_version':1,'builds':{'modded':{'executable':str(executable),'sha256':hashlib.sha256(executable.read_bytes()).hexdigest(),'upstream_version':'fixture','revision':'fixture','source':'fixture','read_schemas':[5],'backend':backend}}}))
        self.config.write_text(self.config.read_text().replace('[profiles]','[profiles]\nsource_root='+json.dumps(str(shared)))+'\n[builds]\nmanifest='+json.dumps(str(manifest))+'\n')

    def cli(self,*args,explicit=True):
        from codex_wake.cli import main
        output=io.StringIO();errors=io.StringIO()
        prefix=['--wake-root',str(self.root)] if explicit else []
        with patch.dict(os.environ,{'XDG_CONFIG_HOME':str(self.root/'preferences')}),contextlib.redirect_stdout(output),contextlib.redirect_stderr(errors):
            code=main(prefix+list(args))
        return code,output.getvalue(),errors.getvalue()

    def test_open_and_resume_resolve_home_build_uuid_and_preserve_exit_code(self):
        self.build_fixture()
        self.assertEqual(self.cli('configuration','default-root',str(self.root))[0],0)
        self.assertEqual(self.cli('open','alice',explicit=False)[0],7)
        result=json.loads((self.home/'native-result').read_text())
        self.assertEqual(result['home'],str(self.home))
        self.assertNotIn('--version',result['args'])
        self.assertEqual(self.cli('resume','alice','--last',explicit=False)[0],7)
        result=json.loads((self.home/'native-result').read_text())
        self.assertEqual(result['args'][-2:],['resume',self.ids[1]])
        self.assertEqual(self.cli('resume','alice',self.ids[0])[0],7)
        self.assertEqual(self.cli('resume','alice','--all-roots')[0],2)
        self.assertEqual(self.cli('resume','--last')[0],2)
        self.assertEqual(self.cli('resume','--channel','stock')[0],2)
        self.assertFalse((self.root/'emergency-control').exists())

    def test_recent_preview_freezes_selection_and_never_starts_a_daemon(self):
        self.build_fixture('managed')
        bob=self.root/'accounts/codex-bob';bob.mkdir(mode=0o700)
        self.config.write_text(self.config.read_text().replace('known_profiles=["alice"]','known_profiles=["alice","bob"]'))
        code,out,err=self.cli('history','recent','--owner','alice','--limit','1','--json')
        self.assertEqual(code,0,(out,err));self.assertEqual(json.loads(out)['sessions'][0]['thread_id'],self.ids[1])
        code,out,err=self.cli('history','import-recent','--owner','alice','--destination','bob','--limit','1','--preview','--json')
        self.assertEqual(code,0,(out,err));batch=json.loads(out)
        self.assertEqual([e['thread_id'] for e in batch['entries']],[self.ids[1]])
        (self.home/'sessions'/(self.ids[1]+'.jsonl')).unlink()
        code,out,err=self.cli('history','import-recent','--batch',batch['id'],'--preview','--json')
        self.assertEqual(code,0,(out,err));self.assertEqual(json.loads(out),batch)
        self.assertFalse((self.home/'native-result').exists())
        self.assertFalse((bob/'packages').exists())
        code,out,err=self.cli('history','import-recent','--batch','../escape','--preview','--json')
        self.assertEqual(code,2)

    def test_unsafe_root_symlink_is_refused_before_creating_batch_storage(self):
        outside=self.root/'outside';outside.mkdir(mode=0o700)
        link=self.root/'linked';link.symlink_to(outside,target_is_directory=True)
        code,out,err=self.cli('--wake-root',str(link),'history','import-recent','--batch','0'*32,'--preview')
        self.assertEqual(code,2,(out,err))
        self.assertFalse((outside/'controller-history-batches').exists())
