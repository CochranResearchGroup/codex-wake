import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

FIXTURE = '12345678-1234-4234-8234-123456789abc'
THREAD = '01a123a8-5782-7d43-a214-55b293bbd65f'


class ControllerMigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.lab = self.root / 'lab'
        self.lab.mkdir()
        (self.lab / '.codex-wake-migration-fixture.json').write_text(json.dumps(
            dict(schema_version=1, fixture_id=FIXTURE, purpose='codex-wake-migration-fixture')))
        self.source = self.lab / 'legacy-shared'
        self.source.mkdir()
        (self.source / 'config.toml').write_text('model="fixture"\n')
        (self.source / 'skills').mkdir()
        (self.source / 'rules').mkdir()
        (self.source / 'sessions').mkdir()
        (self.source / 'sessions' / 'unassigned.jsonl').write_text('{"unassigned":true}\n')
        self.accounts = self.lab / 'legacy-accounts'
        self.home = self.accounts / 'codex-alice'
        self.home.mkdir(parents=True)
        (self.home / 'auth.json').write_text('{"synthetic_account":"alice"}')
        bridge = self.lab / 'config-bridge'
        bridge.symlink_to(self.source / 'config.toml')
        (self.home / 'config.toml').symlink_to(bridge)
        (self.home / 'sessions').mkdir()
        rollout = self.home / 'sessions' / 'owned.jsonl'
        rollout.write_text(json.dumps({'type': 'session_meta', 'payload': {'id': THREAD}}) + '\n')
        with sqlite3.connect(self.home / 'state_5.sqlite') as db:
            db.execute('create table threads(id text primary key,cwd text,title text,rollout_path text)')
            db.execute('insert into threads values(?,?,?,?)', (THREAD, str(self.lab), 'owned fixture', str(rollout)))
        self.legacy = self.lab / 'legacy-profiles.toml'
        self.legacy.write_text('[profiles]\nstate_root=' + json.dumps(str(self.accounts)) + '\n')
        self.pointer = self.lab / 'active-config'
        self.pointer.symlink_to(self.legacy)
        self.path = self.root / 'controller-accounts.toml'
        self.path.write_text(f'''[profiles]
state_root="{self.accounts}"
source_root="{self.source}"
known_profiles=["alice"]
[migration]
fixture_root="{self.lab}"
candidate_root="{self.lab / 'candidate'}"
pointer="{self.pointer}"
legacy_config="{self.legacy}"
''')

    def owner(self, **kwargs):
        from codex_wake.controller_migration import ControllerMigration
        return ControllerMigration(self.path, root=self.root / 'wake', host='fixture-host', environment='fixture-env',
                                   writer_probe=kwargs.pop('writer_probe', lambda unused: dict(status='complete', writers=[])), **kwargs)

    def test_preview_inventories_indirect_links_and_unassigned_history_without_effect(self):
        before = self.pointer.readlink()
        preview = self.owner().execute('migration.preview', {})
        self.assertEqual(preview['status'], 'ready')
        self.assertEqual(preview['target']['fixture_id'], FIXTURE)
        link = next(row for row in preview['links'] if row['path'] == str(self.home / 'config.toml'))
        self.assertEqual(link['resolved'], str(self.source / 'config.toml'))
        self.assertEqual(len(link['chain']), 2)
        self.assertEqual(preview['history']['qualified_sessions'], 1)
        self.assertEqual(preview['history']['unassigned_policy'], 'preserve_original_store')
        self.assertEqual(self.pointer.readlink(), before)
        self.assertFalse((self.lab / 'candidate').exists())

    def test_apply_and_rollback_preserve_native_credential_inode_and_original_shared_store(self):
        owner = self.owner()
        self.path.write_text(self.path.read_text() + '\n[configuration.base]\nmodel="shared-policy"\n')
        ledger = self.home / 'wake' / 'objective-ledgers' / 'prior.json'
        ledger.parent.mkdir(parents=True)
        ledger.write_bytes(b'{"used":93,"deadline":1800000010,"uncertain":true}')
        ledger_before = ledger.read_bytes()
        before_auth = (self.home / 'auth.json').stat().st_ino
        source_before = (self.source / 'config.toml').read_bytes()
        history_before = (self.source / 'sessions' / 'unassigned.jsonl').read_bytes()
        target = owner.execute('migration.preview', {})['target']
        applied = owner.execute('migration.apply', {'expected_target': target})
        self.assertEqual(applied['status'], 'applied')
        candidate_home = self.lab / 'candidate' / 'accounts' / 'codex-alice'
        self.assertEqual((candidate_home / 'auth.json').stat().st_ino, before_auth)
        self.assertTrue(self.home.is_symlink())
        self.assertEqual((candidate_home / 'wake' / 'objective-ledgers' / 'prior.json').read_bytes(), ledger_before)
        import tomllib
        candidate_policy = tomllib.loads((self.lab / 'candidate' / 'controller-accounts.toml').read_text())
        self.assertEqual(candidate_policy['configuration']['base']['model'], 'shared-policy')
        self.assertEqual(self.pointer.resolve(), self.lab / 'candidate' / 'controller-accounts.toml')
        self.assertEqual((self.source / 'config.toml').read_bytes(), source_before)
        self.assertEqual((self.source / 'sessions' / 'unassigned.jsonl').read_bytes(), history_before)
        rolled = owner.execute('migration.rollback', {'receipt_id': applied['receipt_id'], 'expected_target': applied['target']})
        self.assertEqual(rolled['status'], 'rolled_back')
        self.assertFalse(self.home.is_symlink())
        self.assertEqual((self.home / 'auth.json').stat().st_ino, before_auth)
        self.assertEqual(self.pointer.resolve(), self.legacy)
        self.assertEqual(ledger.read_bytes(), ledger_before)
        self.assertFalse((self.lab / 'candidate').exists())

    def test_unknown_writer_stale_plan_and_changed_rollback_target_are_held(self):
        from codex_wake.managed_inventory import InventoryError
        unknown = self.owner(writer_probe=lambda unused: dict(status='unknown', writers=[]))
        held = unknown.execute('migration.preview', {})
        self.assertIn('writer_census_unknown', held['holds'])
        with self.assertRaises(InventoryError) as error:
            unknown.execute('migration.apply', {'expected_target': held['target']})
        self.assertEqual(error.exception.code, 'migration_held')
        owner = self.owner()
        stale = owner.execute('migration.preview', {})['target']
        (self.source / 'config.toml').write_text('model="changed"\n')
        with self.assertRaises(InventoryError) as error:
            owner.execute('migration.apply', {'expected_target': stale})
        self.assertEqual(error.exception.code, 'stale_target')
        applied = owner.execute('migration.apply', {'expected_target': owner.execute('migration.preview', {})['target']})
        edited = self.lab / 'candidate' / 'accounts' / 'codex-alice' / 'operator-note'
        edited.write_text('retain this post-cutover work')
        fresh = owner.execute('migration.preview', {})['target']
        with self.assertRaises(InventoryError) as error:
            owner.execute('migration.rollback', {'receipt_id': applied['receipt_id'], 'expected_target': fresh})
        self.assertEqual(error.exception.code, 'target_changed')
        self.assertEqual(edited.read_text(), 'retain this post-cutover work')
        self.assertTrue(self.home.is_symlink())

    def test_unmarked_real_scope_can_preview_but_production_effects_remain_unapproved(self):
        from codex_wake.managed_inventory import InventoryError
        (self.lab / '.codex-wake-migration-fixture.json').unlink()
        preview = self.owner().execute('migration.preview', {})
        self.assertEqual(preview['status'], 'ready')
        self.assertEqual(preview['production_effect_status'], 'not_authorized')
        self.assertEqual(preview['production_gate'], 'issue380')
        self.assertEqual(preview['disposable_effect_status'], 'not_authorized')
        self.assertEqual(preview['target']['migration_id'], 'legacy')
        with self.assertRaises(InventoryError) as error:
            self.owner().execute('migration.apply', {'expected_target': preview['target']})
        self.assertEqual(error.exception.code, 'production_not_authorized')
        self.assertFalse((self.lab / 'candidate').exists())

    def test_interrupted_effect_is_retained_without_retry_or_destructive_rollback(self):
        from codex_wake.managed_inventory import InventoryError
        owner = self.owner()
        target = owner.execute('migration.preview', {})['target']
        def revoke_after_rename():
            if self.home.is_symlink():
                raise ValueError('simulated caller revocation')
        with self.assertRaises(InventoryError) as error:
            owner.execute('migration.apply', {'expected_target': target}, authorize=revoke_after_rename)
        self.assertEqual(error.exception.code, 'uncertain_effect')
        self.assertEqual(self.pointer.resolve(), self.legacy)
        self.assertTrue(self.home.is_symlink())
        # The original receipt, not an invented new migration, owns uncertainty.
        current = owner.execute('migration.preview', {})['target']
        with self.assertRaises(InventoryError) as error:
            owner.execute('migration.rollback', {'receipt_id': target['migration_revision'], 'expected_target': current})
        self.assertIn(error.exception.code, ('migration_held', 'uncertain_effect'))
        self.assertTrue(self.home.is_symlink())

    def test_real_writer_descriptor_is_reported_and_source_history_remains_unassigned(self):
        import subprocess
        import sys
        from codex_wake.controller_migration import probe_writers
        process = subprocess.Popen([sys.executable, '-c',
            'import sys; f=open(sys.argv[1],"r+"); print("ready",flush=True); sys.stdin.readline()',
            str(self.source / 'config.toml')], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        try:
            self.assertEqual(process.stdout.readline().strip(), 'ready')
            result = probe_writers((self.source, self.accounts))
            self.assertTrue(any(row['pid'] == process.pid for row in result['writers']))
            held = self.owner(writer_probe=lambda unused: result).execute('migration.preview', {})
            self.assertIn('competing_writer', held['holds'])
            self.assertEqual(held['history']['qualified_sessions'], 1)
        finally:
            process.communicate('stop\n', timeout=5)

    def test_indirect_link_cycle_is_visible_unknown_hold_not_a_guessed_target(self):
        (self.home / 'config.toml').unlink()
        (self.home / 'config.toml').symlink_to(self.lab / 'loop-a')
        (self.lab / 'loop-a').symlink_to(self.lab / 'loop-b')
        (self.lab / 'loop-b').symlink_to(self.lab / 'loop-a')
        preview = self.owner().execute('migration.preview', {})
        self.assertEqual(preview['status'], 'held')
        self.assertIn('indirect_dependency_unqualified', preview['holds'])
        self.assertTrue(any(link['scope'] == 'unknown' for link in preview['links']))
        self.assertEqual(self.pointer.resolve(), self.legacy)
