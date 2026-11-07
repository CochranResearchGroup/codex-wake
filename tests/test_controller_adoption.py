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

    def test_adopted_skill_references_use_the_private_copied_helper(self):
        import subprocess
        skill = self.source / 'skills/demo'
        skill.mkdir()
        helper = skill / 'helper.py'
        helper.write_text('print("private-skill-helper")\n')
        (skill / 'SKILL.md').write_text(str(helper))
        (self.home / 'skills').symlink_to(self.source / 'skills')
        owner = self.owner()
        preview = owner.execute('migration.preview', {})
        self.assertEqual(preview['status'], 'ready', preview['holds'])
        applied = owner.execute('migration.apply', {'expected_target': preview['target']})
        copied_reference = (self.home / 'skills/demo/SKILL.md').read_text()
        self.assertEqual(copied_reference, str(self.home / 'skills/demo/helper.py'))
        helper.write_text('print("changed-shared-helper")\n')
        import sys
        self.assertEqual(subprocess.check_output([sys.executable, copied_reference], text=True), 'private-skill-helper\n')
        self.assertEqual((skill / 'SKILL.md').read_text(), str(helper))
        from codex_wake.managed_inventory import InventoryError
        with self.assertRaises(InventoryError) as failure:
            owner.execute('migration.rollback', {'expected_target': owner.execute('migration.preview', {})['target'], 'receipt_id': applied['receipt_id']})
        self.assertEqual(failure.exception.code, 'target_changed')
        self.assertFalse((self.home / 'skills').is_symlink())

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
        from codex_wake.controller_accounts import ControllerAccounts
        accounts = ControllerAccounts(self.path, host='fixture-host', environment='fixture-env')
        self.assertFalse(accounts.execute('stores.resolve', {'selector':'alice'})['store']['independent'])
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

    def test_store_discovery_tracks_adoption_through_normal_activity(self):
        from codex_wake.controller_accounts import ControllerAccounts
        owner = self.owner()
        accounts = ControllerAccounts(self.path, host='fixture-host', environment='fixture-env')
        original = accounts.execute('stores.resolve', {'selector':'alice'})['store']
        self.assertFalse(original['independent'])
        result = owner.execute('migration.apply', {'expected_target':owner.execute('migration.preview', {})['target']})
        adopted = accounts.execute('stores.resolve', {'selector':'alice'})['store']
        self.assertTrue(adopted['independent'])
        self.assertEqual(adopted['store_id'], original['store_id'])
        self.assertEqual(accounts.execute('stores.list', {})['stores'][0]['store_id'], adopted['store_id'])
        history = self.home / 'history.jsonl'
        history.write_text('normal subsequent session activity')
        self.assertTrue(accounts.execute('stores.resolve', {'selector':'alice'})['store']['independent'])

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

    def test_native_package_and_control_aliases_survive_opaque_configuration_census(self):
        package = self.home / 'packages/app-server-daemon/releases/synthetic-v1'
        package.mkdir(parents=True)
        (package / 'bin').mkdir()
        (package / 'bin/codex').write_text('immutable synthetic executable')
        release_link = package / 'codex'
        release_link.symlink_to(package / 'bin/codex')
        helper = self.home / 'tmp/arg0-linux/codex-arg0fixture/apply_patch'
        helper.parent.mkdir(parents=True)
        helper.symlink_to(package / 'bin/codex')
        package_link = self.home / 'packages/app-server-daemon/current'
        package_link.symlink_to(package)
        control_dir = self.home / 'app-server-control'
        control_dir.mkdir()
        socket_path = '/tmp/codex-daemon-' + str(os.getuid()) + '/' + 'a' * 64
        control_link = control_dir / '.pre-native167-app-server-control.sock'
        control_link.symlink_to(socket_path)
        identities = {p: (p.lstat().st_ino, p.readlink()) for p in (package_link, release_link, helper, control_link)}
        probed = []
        def probe(roots):
            probed.append(roots)
            return dict(status='unknown', writers=[], reason='unrelated protected process')
        owner = self.owner(writer_probe=probe)
        preview = owner.execute('migration.preview', {})
        self.assertEqual(preview['status'], 'ready', preview['holds'])
        self.assertEqual(preview['writers']['status'], 'unknown')
        self.assertEqual(set(probed[-1]), {self.home / 'config.toml', self.source / 'config.toml'})
        applied = owner.execute('migration.apply', {'expected_target': preview['target']})
        for path, identity in identities.items():
            self.assertEqual((path.lstat().st_ino, path.readlink()), identity)
        owner.execute('migration.rollback', {'expected_target': applied['target'], 'receipt_id': applied['receipt_id']})
        for path, identity in identities.items():
            self.assertEqual((path.lstat().st_ino, path.readlink()), identity)

    def test_changed_source_after_staging_refuses_configuration_replacement(self):
        from codex_wake.managed_inventory import InventoryError
        owner = self.owner(writer_probe=lambda roots: dict(status='unknown', writers=[]))
        preview = owner.execute('migration.preview', {})
        def authorize():
            if (self.lab / 'candidate').exists():
                (self.source / 'config.toml').write_text('model="advanced"\n')
        with self.assertRaises(InventoryError) as error:
            owner.execute('migration.apply', {'expected_target': preview['target']}, authorize=authorize)
        self.assertEqual(error.exception.code, 'stale_target')
        self.assertTrue((self.home / 'config.toml').is_symlink())

    def test_native_shaped_alias_cannot_disguise_history_or_external_package(self):
        (self.home / 'packages/app-server-daemon').mkdir(parents=True)
        (self.home / 'packages/app-server-daemon/current').symlink_to(self.source / 'sessions')
        preview = self.owner().execute('migration.preview', {})
        self.assertIn('linked_native_or_unknown_state_requires_native_owner', preview['holds'])

    def test_local_cli_adoption_uses_operator_authority_and_replays_without_grant_files(self):
        import contextlib
        import io
        import json
        from types import SimpleNamespace
        from codex_wake.migration_commands import command
        def cli(verb, arguments):
            output=io.StringIO()
            with contextlib.redirect_stdout(output):
                code=command(SimpleNamespace(migration_verb=verb,arguments=arguments,as_json=True),self.root,
                             writer_probe=lambda roots:dict(status='complete',writers=[]))
            value=json.loads(output.getvalue())
            self.assertEqual(code,0,value)
            return value['result']
        self.assertFalse((self.root/'controller-messaging.json').exists())
        preview=cli('preview',{})
        arguments={'expected_target':preview['target']}
        applied=cli('apply',arguments)['operation']
        self.assertEqual(applied['execution'],'completed')
        self.assertEqual(applied['result']['status'],'applied')
        self.assertEqual(cli('apply',arguments)['operation']['operation_id'],applied['operation_id'])
        self.assertFalse((self.home/'config.toml').is_symlink())
        self.assertFalse((self.root/'controller-messaging.json').exists())
