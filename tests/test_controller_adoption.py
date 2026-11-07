import os
import unittest
import test_controller_migration as migration_fixture


class IndependentAdoptionTests(unittest.TestCase):
    owner = migration_fixture.ControllerMigrationTests.owner
    # Reuse fixture construction, not legacy behavior tests.
    def setUp(self):
        migration_fixture.ControllerMigrationTests.setUp(self)
        self.path.write_text(self.path.read_text() + 'strategy="adopt_independent"\n')

    def test_adoption_private_configuration_and_rollback_preserve_native_state(self):
        auth_inode = (self.home / 'auth.json').stat().st_ino
        history = (self.home / 'sessions/owned.jsonl').read_bytes()
        (self.home / 'local.txt').write_text('local setting')
        (self.source / 'skills/example').write_text('skill asset')
        (self.home / 'skills').symlink_to(self.source / 'skills')
        owner = self.owner()
        preview = owner.execute('migration.preview', {})
        self.assertEqual(preview['status'], 'ready')
        applied = owner.execute('migration.apply', {'expected_target': preview['target']})
        self.assertEqual(applied['status'], 'applied')
        self.assertFalse((self.home / 'config.toml').is_symlink())
        self.assertFalse((self.home / 'skills').is_symlink())
        self.assertEqual((self.home / 'skills/example').read_text(), 'skill asset')
        self.assertEqual((self.home / 'auth.json').stat().st_ino, auth_inode)
        self.assertEqual((self.home / 'sessions/owned.jsonl').read_bytes(), history)
        self.assertEqual((self.home / 'local.txt').read_text(), 'local setting')
        self.assertEqual((self.source / 'config.toml').read_text(), 'model="fixture"\n')
        self.assertEqual(os.stat(self.home / 'config.toml').st_mode & 0o777, 0o600)
        rolled = owner.execute('migration.rollback', {'expected_target': applied['target'], 'receipt_id': applied['receipt_id']})
        self.assertEqual(rolled['status'], 'rolled_back')
        self.assertTrue((self.home / 'config.toml').is_symlink())
        self.assertEqual((self.home / 'auth.json').stat().st_ino, auth_inode)

    def test_mcp_sensitive_settings_and_hooks_are_private_remapped_and_redacted(self):
        hooks = self.source / 'hooks'
        hooks.mkdir()
        (hooks / 'run.sh').write_text('#!/bin/sh\nprintf hook-ok\n')
        (hooks / 'run.sh').chmod(0o755)
        external = '/usr/bin/python3'
        (self.source / 'config.toml').write_text(
            'hook="' + str(hooks / 'run.sh') + '"\n'
            '[mcp_servers.fixture]\ncommand="' + external + '"\n'
            '[mcp_servers.fixture.env]\nAPI_KEY="synthetic-sensitive"\n')
        owner = self.owner()
        preview = owner.execute('migration.preview', {})
        self.assertEqual(preview['status'], 'ready', preview['holds'])
        self.assertNotIn('synthetic-sensitive', str(preview))
        self.assertIn(external, str(preview['external_dependencies']))
        applied = owner.execute('migration.apply', {'expected_target': preview['target']})
        import subprocess
        import tomllib
        config = tomllib.loads((self.home / 'config.toml').read_text())
        self.assertEqual(config['hook'], str(self.home / 'hooks/run.sh'))
        self.assertEqual(config['mcp_servers']['fixture']['env']['API_KEY'], 'synthetic-sensitive')
        self.assertEqual(subprocess.check_output([config['hook']], text=True), 'hook-ok')
        self.assertEqual((self.home / 'hooks/run.sh').stat().st_mode & 0o777, 0o700)
        receipt = self.root / 'controller-migration' / (applied['receipt_id'] + '.json')
        self.assertNotIn('synthetic-sensitive', receipt.read_text())
        self.assertNotIn('synthetic-sensitive', str(applied))
        owner.execute('migration.rollback', {'expected_target': applied['target'], 'receipt_id': applied['receipt_id']})
        self.assertTrue((self.home / 'config.toml').is_symlink())
        self.assertFalse((self.home / 'hooks').exists())
        self.assertEqual((hooks / 'run.sh').stat().st_mode & 0o777, 0o755)

    def test_changed_input_writer_and_linked_native_state_refuse_effects(self):
        from codex_wake.managed_inventory import InventoryError
        owner = self.owner()
        before = owner.execute('migration.preview', {})
        (self.source / 'config.toml').write_text('model="changed"\n')
        with self.assertRaises(InventoryError) as error:
            owner.execute('migration.apply', {'expected_target': before['target']})
        self.assertEqual(error.exception.code, 'stale_target')
        held = self.owner(writer_probe=lambda roots: dict(status='complete', writers=[dict(pid=1)])).execute('migration.preview', {})
        self.assertIn('competing_writer', held['holds'])
        (self.home / 'history.jsonl').symlink_to(self.source / 'sessions/unassigned.jsonl')
        self.assertIn('linked_native_or_unknown_state_requires_native_owner', owner.execute('migration.preview', {})['holds'])
        self.assertTrue((self.home / 'config.toml').is_symlink())

    def test_rollback_preserves_new_private_work(self):
        from codex_wake.managed_inventory import InventoryError
        owner = self.owner()
        result = owner.execute('migration.apply', {'expected_target': owner.execute('migration.preview', {})['target']})
        (self.home / 'config.toml').write_text('model="local-new"\n')
        with self.assertRaises(InventoryError) as error:
            owner.execute('migration.rollback', {'expected_target': owner.execute('migration.preview', {})['target'], 'receipt_id': result['receipt_id']})
        self.assertEqual(error.exception.code, 'target_changed')
        self.assertEqual((self.home / 'config.toml').read_text(), 'model="local-new"\n')
    def test_native_auth_references_are_not_materialized(self):
        (self.source / 'auth.json').write_text('synthetic-do-not-copy')
        (self.source / 'config.toml').write_text('credential_file="' + str(self.source / 'auth.json') + '"\n')
        preview = self.owner().execute('migration.preview', {})
        self.assertIn('configuration_asset_reference_requires_native_owner', preview['holds'])
        self.assertNotIn('synthetic-do-not-copy', str(preview))

    def test_writer_arriving_after_staging_refuses_profile_changes(self):
        from codex_wake.managed_inventory import InventoryError
        busy = False
        def probe(roots):
            return dict(status='complete', writers=[dict(pid=1)] if busy else [])
        def authorize():
            nonlocal busy
            if (self.lab / 'candidate').exists():
                busy = True
        owner = self.owner(writer_probe=probe)
        preview = owner.execute('migration.preview', {})
        with self.assertRaises(InventoryError) as error:
            owner.execute('migration.apply', {'expected_target': preview['target']}, authorize=authorize)
        self.assertEqual(error.exception.code, 'migration_held')
        self.assertTrue((self.home / 'config.toml').is_symlink())
