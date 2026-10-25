import json
import os
import unittest
from tempfile import TemporaryDirectory
from pathlib import Path
from unittest.mock import patch
from codex_wake.guarded_interactions import (GuardedInteractions, MenuError, BINARY_SHA256,
    automated_input_guard, assert_input_allowed)
from codex_wake.session_permissions import Principal, PermissionStore
from codex_wake.guarded_interaction_commands import execute

OP = Principal('local-operator', 'operator')
SID = 'de6bb25a-161e-4b8f-a9b2-5dc6d0ddef07'
EMPTY = 'Shell version: 1.0.40\nSession ID: '+SID+'\nminimal · /help\n❯\nGrok 4.6 (high) · 2K / 500K · ctrl+o transcript\n'
PALETTE = 'Shell version: 1.0.40\nSession ID: '+SID+'\nCommands\nsearch:\n◆ New Session\n↑/↓ nav  |  Enter select  |  Esc close\n'

class Host:
    def __init__(self, binding):
        self.binding = binding
        self.frame = EMPTY
        self.keys = []
        self.lose = None
    def snapshot(self, binding):
        return dict(self.binding, frame=self.frame)
    def _tmux(self, binding, *args):
        with automated_input_guard(None, binding):
            key = args[-1]
            self.keys.append(key)
            self.frame = PALETTE if key == 'C-p' else EMPTY
            if self.lose == key:
                raise TimeoutError()

class GuardedInteractionsTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.p = patch('codex_wake.guarded_interactions.user_state_dir', return_value=self.root/'global')
        self.p.start(); self.addCleanup(self.p.stop)
        self.binding = dict(socket=str(self.root/'tmux.sock'), pane='%0', pid=os.getpid(),
            start_ticks=1, boot_id='boot', session_id=SID, executable_sha256=BINARY_SHA256,
            executable='/test/grok', cwd=str(Path.cwd()))
        self.host = Host(self.binding)
        (self.root/'wake').mkdir(mode=0o700)
        self.service = GuardedInteractions(self.root/'wake', host=self.host)
        PermissionStore(self.root/'wake').configure({'version':1,'global':{'actions':{a:'allow' for a in ['terminal.menu','terminal.takeover','terminal.return']}}}, OP, expected_revision=0)
        self.service.configure('menu', self.binding, principal=OP, reason='isolated menu only')
        self.token = self.service.inspect('menu')['token']

    def test_missing_profile_is_held(self):
        with self.assertRaises(MenuError): self.service.inspect('missing')

    def test_real_control_sequence_and_idempotent_restart(self):
        result = self.service.run('menu', self.token, principal=OP, operation='one')
        self.assertEqual(result['state'], 'completed')
        restarted = GuardedInteractions(self.root/'wake', host=self.host)
        result = restarted.run('menu', self.token, principal=OP, operation='one')
        self.assertEqual(result['state'], 'completed')
        self.assertEqual(self.host.keys, ['C-p', 'Escape'])

    def test_takeover_fences_every_input_and_old_generation(self):
        human = self.service.change_owner('menu', self.token, principal=OP, human=True, reason='human takes control')
        with self.assertRaisesRegex(MenuError, 'human_owns_input'):
            with automated_input_guard(self.root, self.binding): pass
        returned = self.service.change_owner('menu', human['token'], principal=OP, human=False, reason='human returns')
        self.assertEqual(returned['token']['generation'], 3)
        with self.assertRaisesRegex(MenuError, 'stale_input_owner_generation'):
            self.service.run('menu', self.token, principal=OP, operation='old')
        self.assertEqual(self.host.keys, [])

    def test_lost_response_never_repeats_and_blocks_new_operation(self):
        self.host.lose = 'C-p'
        self.assertEqual(self.service.run('menu', self.token, principal=OP, operation='lost')['state'], 'uncertain')
        restarted = GuardedInteractions(self.root/'wake', host=self.host)
        row = restarted.run('menu', self.token, principal=OP, operation='lost')
        self.assertEqual(row['reconciliation_observation'], 'palette')
        self.assertFalse(row['retry_allowed'])
        with self.assertRaisesRegex(MenuError, 'unresolved_menu_effect'):
            restarted.run('menu', self.token, principal=OP, operation='different')
        self.assertEqual(self.host.keys, ['C-p'])

    def test_draft_identity_and_foreign_token_refuse_without_input(self):
        self.host.frame = EMPTY.replace('❯\n','❯ unsent human draft\n')
        with self.assertRaises(MenuError):self.service.run('menu',self.token,principal=OP,operation='draft')
        self.host.frame = EMPTY
        self.host.binding = dict(self.binding, start_ticks=2)
        with self.assertRaises(MenuError):self.service.run('menu',self.token,principal=OP,operation='changed')
        self.assertEqual(self.host.keys, [])

    def test_nonoperator_cannot_takeover_or_execute_from_model(self):
        with self.assertRaises(MenuError):execute('run',dict(profile='menu',token=self.token,operation='model'),self.root/'wake',host=self.host)
        with self.assertRaises(MenuError):self.service.change_owner('menu',self.token,principal=Principal('worker'),human=True,reason='no')
        self.assertEqual(self.host.keys, [])

    def test_corrupt_global_ownership_fails_closed(self):
        from codex_wake.guarded_interactions import _fence_path
        _fence_path(self.binding).write_text('{}')
        with self.assertRaises(MenuError):assert_input_allowed(self.root,self.binding)
        self.assertEqual(self.host.keys, [])

    def test_revocation_between_keys_prevents_escape(self):
        original = self.host._tmux
        def revoke(binding, *args):
            original(binding, *args)
            PermissionStore(self.root/'wake').configure(
                {'version':1,'global':{'actions':{'terminal.menu':'deny'}}}, OP, expected_revision=1)
        self.host._tmux = revoke
        with self.assertRaises(ValueError):
            self.service.run('menu', self.token, principal=OP, operation='revoked')
        self.assertEqual(self.host.keys, ['C-p'])
        row = self.service.reconcile('menu', 'revoked')
        self.assertEqual(row['reconciliation_observation'], 'palette')
        self.assertFalse(row['retry_allowed'])

    def test_missing_initialized_owner_and_wrong_profile_hold(self):
        from codex_wake.guarded_interactions import _fence_path
        self.service.run('menu', self.token, principal=OP, operation='done')
        self.service.configure('other',self.binding,principal=OP,reason='other named profile')
        with self.assertRaises(MenuError):self.service.reconcile('other','done')
        _fence_path(self.binding).unlink()
        with self.assertRaisesRegex(MenuError,'input_owner_state_missing'):
            with automated_input_guard(self.root,self.binding):pass

    def test_foreign_process_token_cannot_guard_reused_pane(self):
        different = dict(self.binding, start_ticks=2)
        with self.assertRaisesRegex(MenuError,'stale_input_owner_generation'):
            with automated_input_guard(self.root,different,self.token):pass
