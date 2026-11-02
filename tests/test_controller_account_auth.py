"""Users sign in by account name; native authentication owns all secret input."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class AccountAuthTests(unittest.TestCase):
    def fixture(self, root):
        native=root/'native'
        native.write_text('#!'+sys.executable+'\nimport os,sys,json\nfrom pathlib import Path\nh=Path(os.environ["CODEX_HOME"])\na=sys.argv[1:]\n'
            'if "status" in a: sys.exit(0 if (h/"auth.json").exists() else 1)\n'
            'value=sys.stdin.readline().strip() if "--with-api-key" in a else "synthetic-browser-login"\n'
            '(h/"auth.json").write_text(value)\n'
            '(h/"invocation.json").write_text(json.dumps({"args":a,"inherited_key":os.environ.get("OPENAI_API_KEY")}))\n')
        native.chmod(0o700)
        manifest=root/'builds.json'
        manifest.write_text(json.dumps(dict(schema_version=1,builds=dict(modded=dict(executable=str(native),
            sha256=hashlib.sha256(native.read_bytes()).hexdigest(),upstream_version='0.166.0',revision='fixture',source='fixture')))))
        self.cli(root,'init')
        registry=root/'controller-accounts.toml'
        registry.write_text(registry.read_text()+f'\n[builds]\nmanifest={json.dumps(str(manifest))}\n')
        return native

    def cli(self, root, *args, stdin=None):
        env=dict(os.environ,PYTHONPATH=str(Path(__file__).resolve().parents[1]/'src'),OPENAI_API_KEY='must-not-leak')
        return subprocess.run([sys.executable,'-m','codex_wake.cli','--wake-root',str(root),'accounts',*args],
            input=stdin,text=True,capture_output=True,env=env,timeout=15)

    def test_login_creates_named_home_and_reports_status_without_shell_setup(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.fixture(root)
            result=self.cli(root,'login','alice','--device-auth')
            self.assertEqual(result.returncode,0,result.stderr+result.stdout)
            home=root/'accounts/codex-alice'
            self.assertEqual((home/'auth.json').read_text(),'synthetic-browser-login')
            self.assertEqual((home/'auth.json').stat().st_mode & 0o777,0o600)
            invoked=json.loads((home/'invocation.json').read_text())
            self.assertEqual(invoked['args'],['-c','cli_auth_credentials_store="file"','login','--device-auth'])
            self.assertIsNone(invoked['inherited_key'])
            self.assertEqual(self.cli(root,'status','alice').returncode,0)
            self.assertFalse((root/'accounts/shared/auth.json').exists())

    def test_api_key_enters_only_native_stdin_and_alias_preserves_peer(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.fixture(root)
            self.assertEqual(self.cli(root,'create','alice','--alias','work').returncode,0)
            self.assertEqual(self.cli(root,'create','bob').returncode,0)
            peer=root/'accounts/codex-bob/auth.json';peer.write_text('synthetic-peer')
            self.assertEqual(self.cli(root,'status','work').returncode,1)
            key='synthetic-input-key'
            result=self.cli(root,'login','work','--with-api-key',stdin=key+'\n')
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual((root/'accounts/codex-alice/auth.json').read_text(),key)
            self.assertNotIn(key,result.stdout+result.stderr)
            self.assertEqual(peer.read_text(),'synthetic-peer')
            self.assertEqual(self.cli(root,'status','work').returncode,0)

    def test_login_refuses_managed_endpoint_and_private_client_but_status_stays_readable(self):
        import fcntl
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.fixture(root);self.cli(root,'create','alice')
            home=root/'accounts/codex-alice'
            endpoint=home/'app-server-control/app-server-control.sock';endpoint.parent.mkdir();endpoint.touch()
            refused=self.cli(root,'login','alice')
            self.assertEqual(refused.returncode,2)
            self.assertIn('stop this account daemon',refused.stderr)
            self.assertFalse((home/'auth.json').exists())
            self.assertEqual(self.cli(root,'status','alice').returncode,1)
            endpoint.unlink()
            with (home/'.build-channel.lock').open('w') as lock:
                os.chmod(lock.name,0o600);fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
                refused=self.cli(root,'login','alice')
                self.assertEqual(refused.returncode,2)
                self.assertIn('private build client',refused.stderr)
                self.assertFalse((home/'auth.json').exists())
            with (home/'.wake-daemon.lock').open('w') as lock:
                os.chmod(lock.name,0o600);fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
                refused=self.cli(root,'login','alice')
                self.assertEqual(refused.returncode,2)
                self.assertIn('scoped daemon operation',refused.stderr)
                self.assertFalse((home/'auth.json').exists())

    def test_changed_build_bytes_refuse_before_authentication(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);native=self.fixture(root);self.cli(root,'create','alice')
            native.write_text(native.read_text()+'\n# replaced bytes\n')
            result=self.cli(root,'login','alice')
            self.assertEqual(result.returncode,2)
            self.assertIn('bytes changed',result.stderr)
            self.assertFalse((root/'accounts/codex-alice/auth.json').exists())
