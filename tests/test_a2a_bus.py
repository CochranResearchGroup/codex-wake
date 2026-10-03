from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from codex_wake.a2a_bus import BusStore, read_capability
from codex_wake.a2a_identity import BusError, RuntimeIdentity


class BusIdentityTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / 'bus'
        self.repo = Path(self.temporary.name) / 'repo'
        self.repo.mkdir()
        self.store, self.operator = BusStore.configure(self.root)
        self.identity = RuntimeIdentity('runtime', 'exact-thread', str(self.repo))

    def grant(self):
        self.store.enroll(self.repo, self.operator)
        return self.store.issue_actor(self.identity, self.repo, self.operator)[0]

    def test_explicit_grant_authenticates_exact_runtime_and_root(self):
        capability = self.grant()
        actor = self.store.authenticate(capability, self.identity, invoking_cwd=self.repo)
        self.assertEqual(actor.thread_id, 'exact-thread')
        self.assertEqual(actor.root, str(self.repo))
        self.assertEqual(actor.generation, 1)
        for path, mode in [(self.root, 0o700), (self.store.path, 0o600), (capability, 0o600), (self.operator, 0o600)]:
            self.assertEqual(path.stat().st_mode & 0o777, mode)

    def test_unenrolled_root_cannot_issue_actor(self):
        with self.assertRaises(BusError) as error:
            self.store.issue_actor(self.identity, self.repo, self.operator)
        self.assertEqual(error.exception.code, 'authorization_denied')

    def test_capability_rejects_parent_child_namespace_and_cwd_claims(self):
        capability = self.grant()
        contexts = [RuntimeIdentity('runtime', 'parent', str(self.repo)),
                    RuntimeIdentity('other-runtime', 'exact-thread', str(self.repo)),
                    RuntimeIdentity('runtime', 'exact-thread', str(self.root))]
        for identity in contexts:
            with self.assertRaises(BusError) as error:
                self.store.authenticate(capability, identity, invoking_cwd=self.repo)
            self.assertEqual(error.exception.code, 'authorization_denied')
        with self.assertRaises(BusError):
            self.store.authenticate(capability, self.identity, invoking_cwd=self.root)

    def test_token_tampering_and_operator_impersonation_fail(self):
        capability = self.grant()
        value = read_capability(capability)
        value['secret'] = 'different'
        capability.write_text(json.dumps(value))
        with self.assertRaises(BusError):
            self.store.authenticate(capability, self.identity, invoking_cwd=self.repo)
        with self.assertRaises(BusError):
            self.store.enroll(self.root, capability)

    def test_revocation_survives_reopen_and_does_not_reset_generation(self):
        capability = self.grant()
        actor = self.store.authenticate(capability, self.identity, invoking_cwd=self.repo)
        self.store.revoke_actor(actor.actor_id, self.operator)
        reopened = BusStore(self.root)
        with self.assertRaises(BusError):
            reopened.authenticate(capability, self.identity, invoking_cwd=self.repo)
        with reopened.connection() as database:
            self.assertEqual(database.execute('SELECT generation FROM actors').fetchone()[0], 2)

    def test_copied_store_rejected_at_different_root(self):
        copied = self.root.with_name('copy')
        shutil.copytree(self.root, copied)
        with self.assertRaises(BusError) as error:
            BusStore(copied)
        self.assertEqual(error.exception.code, 'bus_identity_mismatch')

    def test_future_schema_rejected_without_repair(self):
        with sqlite3.connect(self.store.path) as database:
            database.execute('UPDATE meta SET value=? WHERE key=?', ('999', 'schema_version'))
        with self.assertRaises(BusError) as error:
            BusStore(self.root)
        self.assertEqual(error.exception.code, 'unsupported_schema')
        with sqlite3.connect(self.store.path) as database:
            self.assertEqual(database.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()[0], '999')

    def test_missing_store_never_implicitly_created(self):
        absent = self.root.with_name('absent')
        with self.assertRaises(BusError):
            BusStore(absent)
        self.assertFalse(absent.exists())

    def test_symlink_and_public_permissions_rejected(self):
        link = self.root.with_name('link')
        link.symlink_to(self.root)
        with self.assertRaises(BusError):
            BusStore(link)
        self.store.path.chmod(0o644)
        with self.assertRaises(BusError):
            BusStore(self.root)

    def test_unsupported_filesystem_cannot_initialize(self):
        absent = self.root.with_name('network-bus')
        with patch('codex_wake.a2a_bus.Path.read_text', return_value='1 0 0:1 / / rw - nfs server rw'):
            with self.assertRaises(BusError) as error:
                BusStore.configure(absent)
        self.assertEqual(error.exception.code, 'filesystem_unsupported')
        self.assertFalse(absent.exists())

    def test_interrupted_actor_publication_rolls_back_authority(self):
        self.store.enroll(self.repo, self.operator)
        with patch('codex_wake.a2a_bus.write_capability', side_effect=BusError('store_unavailable', 'fixture interruption')):
            with self.assertRaises(BusError):
                self.store.issue_actor(self.identity, self.repo, self.operator)
        with self.store.connection() as database:
            self.assertEqual(database.execute('SELECT count(*) FROM actors').fetchone()[0], 0)

    def test_operator_receipts_never_contain_capability_secret(self):
        capability = self.grant()
        secret = read_capability(capability)['secret']
        with self.store.connection() as database:
            events = '\n'.join(row['subject'] for row in database.execute('SELECT * FROM events'))
        self.assertNotIn(secret, events)
        self.assertNotIn(read_capability(self.operator)['secret'], events)

    def test_namespace_uses_server_home_and_thread_provider(self):
        thread = dict(id='id', cwd=str(self.repo), modelProvider='provider')
        first = RuntimeIdentity.from_metadata(thread, dict(codexHome=str(self.root)))
        second = RuntimeIdentity.from_metadata(thread, dict(codexHome=str(self.repo)))
        self.assertNotEqual(first.namespace, second.namespace)
        with self.assertRaises(BusError):
            RuntimeIdentity.from_metadata(thread, {})

    def test_route_requires_active_recipient_and_explicit_cross_root_permission(self):
        sender_capability = self.grant()
        sender = self.store.authenticate(sender_capability, self.identity, invoking_cwd=self.repo)
        other = self.repo.with_name('other')
        other.mkdir()
        identity = RuntimeIdentity('runtime', 'recipient', str(other))
        with self.store.connection() as database:
            with self.assertRaises(BusError):
                self.store.authorize_pair(database, sender, identity)
        self.store.enroll(other, self.operator)
        self.store.issue_actor(identity, other, self.operator)
        with self.store.connection() as database:
            with self.assertRaises(BusError) as error:
                self.store.authorize_pair(database, sender, identity)
        self.assertEqual(error.exception.code, 'cross_root_denied')

    def test_stale_authenticated_actor_cannot_bypass_revocation(self):
        capability = self.grant()
        actor = self.store.authenticate(capability, self.identity, invoking_cwd=self.repo)
        self.store.revoke_actor(actor.actor_id, self.operator)
        with self.store.connection() as database:
            with self.assertRaises(BusError):
                self.store.validate_actor(database, actor)

    def test_bus_starts_paused_and_operator_changes_are_receipted(self):
        self.assertTrue(self.store.status()['paused'])
        receipt = self.store.set_paused(False, self.operator)
        self.assertTrue(receipt.startswith('receipt_'))
        self.assertFalse(self.store.status()['paused'])
        self.assertEqual(self.store.status()['notification_capability'], 'unqualified')
