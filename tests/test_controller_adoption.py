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

    def test_home_local_references_require_qualified_asset_mapping(self):
        (self.source / 'config.toml').write_text('hook="' + str(self.source / 'hooks/run.sh') + '"\n')
        preview = self.owner().execute('migration.preview', {})
        self.assertIn('configuration_home_references_require_asset_mapping', preview['holds'])

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
