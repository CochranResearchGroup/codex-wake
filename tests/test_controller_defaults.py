"""Account commands find user state without changing project wake ownership."""
import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from codex_wake.cli import main


class ControllerDefaultTests(unittest.TestCase):
    def test_first_use_accounts_share_user_controller_from_any_project(self):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory);project=base/'project';project.mkdir();(project/'.codex').mkdir(mode=0o700)
            env={'HOME':str(base/'home'),'XDG_CONFIG_HOME':str(base/'config'),'XDG_STATE_HOME':str(base/'state'),'CODEX_WAKE_ROOT':'','CODEX_WAKE_ACCOUNTS_CONFIG':'','CODEX_PROFILES_CONFIG':''}
            with patch.dict(os.environ,env),contextlib.chdir(project):
                def invoke(*args):
                    out=io.StringIO()
                    with contextlib.redirect_stdout(out):code=main(list(args))
                    self.assertEqual(code,0,out.getvalue());return json.loads(out.getvalue())
                invoke('accounts','init','--json')
                canonical=base/'state/codex-wake/controller'
                self.assertTrue((canonical/'controller-accounts.toml').is_file())
                invoke('accounts','create','soylei','--json')
                elsewhere=base/'another-project';elsewhere.mkdir()
                with contextlib.chdir(elsewhere):
                    account=invoke('accounts','resolve','soylei','--json')['result']['account']
                    self.assertEqual(account['home'],str(canonical/'accounts/codex-soylei'))
                    view=invoke('configuration','explain','soylei','--json')
                    self.assertEqual(view['status'],'completed')
                self.assertFalse((project/'.codex/wake/controller-accounts.toml').exists())

    def test_compatibility_launcher_uses_the_same_user_controller(self):
        from codex_wake.profile_compat import main as profiles
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory);base.chmod(0o700)
            with patch.dict(os.environ,{'HOME':str(base),'XDG_CONFIG_HOME':str(base/'config'),'XDG_STATE_HOME':str(base/'state'),'CODEX_WAKE_ROOT':'','CODEX_WAKE_ACCOUNTS_CONFIG':'','CODEX_PROFILES_CONFIG':''}),contextlib.chdir(base):
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(main(['accounts','init','--json']),0)
                    self.assertEqual(main(['accounts','create','soylei','--json']),0)
                out=io.StringIO()
                with contextlib.redirect_stdout(out):code=profiles(['list'])
                self.assertEqual(code,0,out.getvalue())
                self.assertIn('soylei',out.getvalue())

    def test_local_mcp_account_reads_use_the_same_default(self):
        from codex_wake.mcp_server import CommandRunner
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory)
            with patch.dict(os.environ,{'HOME':str(base),'XDG_CONFIG_HOME':str(base/'config'),'XDG_STATE_HOME':str(base/'state'),'CODEX_WAKE_ROOT':'','CODEX_WAKE_ACCOUNTS_CONFIG':'','CODEX_PROFILES_CONFIG':''}),contextlib.chdir(base):
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(main(['accounts','init','--json']),0)
                    self.assertEqual(main(['accounts','create','soylei','--json']),0)
                result,failed=CommandRunner().call('wake_controller_account_resolve',{'selector':'soylei'})
                self.assertFalse(failed,result)
                self.assertEqual(result['result']['account']['home'],str(base/'state/codex-wake/controller/accounts/codex-soylei'))

    def test_saved_default_explicit_override_and_project_wakes_remain_separate(self):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory);project=base/'project';project.mkdir();chosen=base/'chosen'
            env={'HOME':str(base),'XDG_CONFIG_HOME':str(base/'config'),'XDG_STATE_HOME':str(base/'state'),'CODEX_WAKE_ROOT':'','CODEX_WAKE_ACCOUNTS_CONFIG':'','CODEX_PROFILES_CONFIG':''}
            with patch.dict(os.environ,env),contextlib.chdir(project):
                def invoke(*args,expected=0):
                    out=io.StringIO()
                    with contextlib.redirect_stdout(out),contextlib.redirect_stderr(io.StringIO()):code=main(list(args))
                    self.assertEqual(code,expected,out.getvalue());return out.getvalue()
                invoke('--wake-root',str(chosen),'accounts','init','--json')
                local=project/'.codex/wake'
                invoke('--wake-root',str(local),'accounts','init','--json')
                invoke('configuration','default-root',str(chosen))
                invoke('accounts','create','soylei','--json')
                self.assertEqual(json.loads(invoke('accounts','resolve','soylei','--json'))['result']['account']['home'],str(chosen/'accounts/codex-soylei'))
                self.assertEqual(json.loads(invoke('--wake-root',str(local),'accounts','list','--json'))['result']['accounts'],[])
                with patch.dict(os.environ,{'CODEX_WAKE_ROOT':str(local)}):
                    self.assertEqual(json.loads(invoke('accounts','list','--json'))['result']['accounts'],[])
                    self.assertEqual(len(json.loads(invoke('--wake-root',str(chosen),'accounts','list','--json'))['result']['accounts']),1)
                self.assertIn('soylei',invoke('profiles','--','list'))
                self.assertNotIn('soylei',invoke('--wake-root',str(local),'profiles','--','list'))
                invoke('after','--app-server-thread-id','thread-project','1m','--','project-only')
                self.assertIn('project-only',invoke('list','--json'))
                self.assertNotIn('project-only',invoke('--wake-root',str(chosen),'list','--json'))
                preference=base/'config/codex-wake/shortcuts.json'
                preference.write_text('{"version":1,"wake_root":"relative-invalid"}')
                invoke('accounts','list','--json',expected=2)
                invoke('profiles','--','list',expected=2)
                invoke('configuration','default-root',str(chosen))
                self.assertEqual(json.loads(invoke('accounts','list','--json'))['result']['accounts'][0]['id'],'codex-soylei')
