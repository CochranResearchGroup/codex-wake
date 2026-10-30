"""Concurrent account admission through the public process-lifetime guard."""
import json
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from codex_profiles.config import Settings
from codex_profiles.layout import ActiveProfileGuard, ensure_layout


class ConcurrentProfileTests(unittest.TestCase):
    def test_private_accounts_run_together_and_keep_credentials_separate(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            settings = Settings(state_root=root/'state', source_root=root/'seed')
            for name in ['alice', 'bob']:
                home = ensure_layout(settings, name)
                (home/'auth.json').write_text(json.dumps({'fixture_account': name}))
            with ActiveProfileGuard(settings, 'codex-alice', private_runtime=True):
                with ActiveProfileGuard(settings, 'codex-bob', private_runtime=True):
                    self.assertEqual(ActiveProfileGuard(settings,'observer').active_profiles(), ('codex-alice','codex-bob'))
                    self.assertEqual(json.loads((settings.account_root('alice')/'auth.json').read_text()), {'fixture_account':'alice'})
                    self.assertEqual(json.loads((settings.account_root('bob')/'auth.json').read_text()), {'fixture_account':'bob'})
            self.assertEqual(ActiveProfileGuard(settings,'observer').active_profiles(), ())

    def test_shared_credential_inode_is_not_concurrent_isolation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            settings = Settings(state_root=root/'state', source_root=root/'seed')
            alice = ensure_layout(settings, 'alice')
            bob = ensure_layout(settings, 'bob')
            (alice/'auth.json').write_text('{"fixture_account":"alice"}')
            os.link(alice/'auth.json', bob/'auth.json')
            with ActiveProfileGuard(settings, 'codex-alice', private_runtime=True):
                with self.assertRaisesRegex(BlockingIOError, 'shared|mutable|isolation'):
                    ActiveProfileGuard(settings, 'codex-bob', private_runtime=True).acquire()


    def test_effective_shared_configuration_reports_mcp_identity_scope_without_secrets(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            seed = root/'seed'
            seed.mkdir()
            (seed/'config.toml').write_text('mcp_oauth_credentials_store = "auto"\n[mcp_servers.shared]\nurl = "http://fixture.invalid/mcp"\nbearer_token = "never-print-me"\n')
            settings = Settings(state_root=root/'state', source_root=seed)
            for name in ['alice','bob']:
                ensure_layout(settings, name)
            alice = settings.configuration_view('alice')
            bob = settings.configuration_view('bob')
            self.assertEqual(alice['settings']['source'], bob['settings']['source'])
            self.assertEqual(alice['skills']['source'], bob['skills']['source'])
            self.assertEqual(alice['mcp']['servers'], ['shared'])
            self.assertEqual(alice['mcp']['oauth_store'], 'auto')
            self.assertIn('operator keyring', alice['mcp']['identity_scope'])
            self.assertNotIn('never-print-me', json.dumps(alice))
            self.assertNotIn('fixture.invalid', json.dumps(alice))


    def test_private_launch_cannot_bypass_an_existing_legacy_client(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            settings = Settings(state_root=root/'state', source_root=root/'seed')
            ensure_layout(settings, 'alice')
            with ActiveProfileGuard(settings, 'codex-alice'):
                with self.assertRaisesRegex(BlockingIOError, 'legacy|private|shared'):
                    ActiveProfileGuard(settings, 'codex-alice', private_runtime=True).acquire()


    def test_projection_and_shared_session_policies_keep_exclusion(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for selection_mode, links in [('projection', ('config.toml','skills','rules')), ('launcher', ('config.toml','sessions'))]:
                settings = Settings(state_root=root/selection_mode/str(len(links)), source_root=root/'seed', selection_mode=selection_mode, shared_links=links)
                ensure_layout(settings, 'alice')
                with self.assertRaises(BlockingIOError):
                    ActiveProfileGuard(settings, 'codex-alice', private_runtime=True).acquire()

    def test_retained_old_generation_does_not_qualify_a_private_peer(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            settings = Settings(state_root=root/'state', source_root=root/'seed')
            for name in ['alice','bob']:
                ensure_layout(settings, name)
            with ActiveProfileGuard(settings, 'codex-alice', private_runtime=True) as active:
                record = json.loads(active.pid_file.read_text())
                record['generation']['start_ticks'] = '0'
                active.pid_file.write_text(json.dumps(record))
                with self.assertRaisesRegex(BlockingIOError, 'unverified'):
                    ActiveProfileGuard(settings, 'codex-bob', private_runtime=True).acquire()


    def test_distinct_process_clients_restart_without_switching_the_peer_account(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            settings = Settings(state_root=root/'state', source_root=root/'seed')
            for name in ['alice','bob']:
                home = ensure_layout(settings, name)
                (home/'auth.json').write_text(json.dumps({'fixture_account': name}))
            runner = root/'guard-client.py'
            runner.write_text('import sys,json\nfrom pathlib import Path\nfrom codex_profiles.config import Settings\nfrom codex_profiles.layout import ActiveProfileGuard\nr=Path(sys.argv[1]);p=sys.argv[2];s=Settings(state_root=r/"state",source_root=r/"seed")\nwith ActiveProfileGuard(s,"codex-"+p,private_runtime=True):\n print((s.account_root(p)/"auth.json").read_text(),flush=True)\n sys.stdin.readline()\n')
            env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1]/'src'))
            children = []
            def start(name):
                p = subprocess.Popen([sys.executable,str(runner),str(root),name],env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
                children.append(p)
                import select
                self.assertTrue(select.select([p.stdout],[],[],5)[0])
                self.assertEqual(json.loads(p.stdout.readline()),{'fixture_account':name})
                return p
            try:
                alice, bob = start('alice'), start('bob')
                alice.communicate('stop\n',timeout=5)
                self.assertEqual(alice.returncode,0)
                restarted = start('alice')
                self.assertIsNone(bob.poll())
                self.assertEqual(json.loads((settings.account_root('bob')/'auth.json').read_text()),{'fixture_account':'bob'})
                restarted.communicate('stop\n',timeout=5)
                bob.communicate('stop\n',timeout=5)
                self.assertEqual(bob.returncode,0)
            finally:
                for p in children:
                    if p.poll() is None:p.kill()
                    p.communicate(timeout=5)
            self.assertEqual(ActiveProfileGuard(settings,'observer').active_profiles(),())


if __name__ == '__main__':
    unittest.main()
