"""Live-mode preparation reuses an exact recipient and fails closed on ambiguity."""
from pathlib import Path
import json
import os
import subprocess
import sys
import time
import tempfile
import unittest
from unittest.mock import patch

from codex_wake.runtime_delivery import RuntimeTargetError
from codex_wake.wake_live_restore import LiveWakeRestorer

THREAD = '11111111-1111-4111-8111-111111111111'

class LiveWakeRestoreTests(unittest.TestCase):
    def target(self):
        return dict(transport='native', session_mode='reopen_live', thread_id=THREAD,
                    endpoint='unix:///fixture', codex_cmd='/bin/true')

    def test_live_exact_conversation_is_reused_without_launch_configuration(self):
        row = dict(thread_id=THREAD, binding_status='metadata_matched', cwd='/tmp',
                   attachments=[dict(pane_id='%1', client_pid=123, client_start_time_ticks=456)])
        with tempfile.TemporaryDirectory() as directory, patch('codex_wake.sessions.observe', return_value=dict(complete=True, sessions=[row])), patch('codex_wake.sessions.revalidate_attachment', return_value=True):
            result = LiveWakeRestorer(Path(directory)).prepare(self.target())
        self.assertEqual(result['thread_id'], THREAD)
        self.assertEqual(result['startup_policy'], 'active_tab')
        self.assertEqual(result['resume_policy'], 'hold')

    def test_unknown_inventory_holds_without_launching(self):
        with tempfile.TemporaryDirectory() as directory, patch('codex_wake.sessions.observe', return_value=dict(complete=False, sessions=[])):
            with self.assertRaisesRegex(RuntimeTargetError, 'live_recipient_ownership_unverified'):
                LiveWakeRestorer(Path(directory)).prepare(self.target())

    def test_absent_recipient_requires_existing_host_profile_binding(self):
        with tempfile.TemporaryDirectory() as directory, patch('codex_wake.sessions.observe', return_value=dict(complete=True, sessions=[])):
            with self.assertRaisesRegex(RuntimeTargetError, 'live_restore_configuration_required'):
                LiveWakeRestorer(Path(directory)).prepare(self.target())

    def test_absent_recipient_uses_latest_private_profile_through_existing_resume_owner(self):
        from codex_wake.a2a_identity import RuntimeIdentity
        from codex_wake.managed_inventory import ManagedInventory, Observation
        from codex_wake.process import process_identity
        from codex_wake.session_permissions import PermissionStore, Principal
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory); root = base / 'wake'; home = base / 'home'; home.mkdir()
            cwd = base / 'latest-directory'; cwd.mkdir()
            thread = dict(id=THREAD, cwd=str(cwd), modelProvider='openai', status={'type':'idle'})
            metadata = dict(codexHome=str(home))
            namespace = RuntimeIdentity.from_metadata(thread, metadata).namespace
            identity = process_identity(os.getpid())
            process = dict(pid=os.getpid(), start_ticks=identity['start_time_ticks'], boot_id=identity['boot_id'])
            inv = ManagedInventory(root)
            agent = inv.enroll(Observation('codex', namespace, THREAD, str(cwd), 'ready', time.time(),
                'native_metadata', process, [dict(pane_id='%7')], {'inspect':'supported'}))['agent']
            PermissionStore(root).configure({'version':1}, Principal('operator','operator'), expected_revision=0)
            profiles = base / 'profiles.json'
            profiles.write_text(json.dumps(dict(version=1, profiles=dict(latest=dict(cwd=str(cwd),
                app_server='unix:///fixture', codex_path=sys.executable, tmux_session='work', timeout=1)),
                callers={THREAD:['latest']}))); profiles.chmod(0o600)
            mapping = root / 'wake-live-restore.json'
            mapping.write_text(json.dumps(dict(version=1, bindings={THREAD:dict(profiles=str(profiles),
                managed_agent_id=agent['managed_agent_id'], profile='latest')}))); mapping.chmod(0o600)
            target = self.target() | dict(codex_cmd='/missing-old-harness', _wake_permission_context=dict(
                subject=THREAD, role='session', tasks=[], target=THREAD, task_id=None, revision=1),
                _wake_expires_at='2035-01-01T00:00:00Z', _wake_occurrence_id='wake-original')
            live = False; commands = []
            def observe(**kwargs):
                pane = dict(pane_id='%7', client_pid=os.getpid(), client_start_time_ticks=identity['start_time_ticks'])
                return dict(complete=True, sources=dict(app_server=dict(availability='available')),
                    sessions=[dict(thread_id=THREAD,cwd=str(cwd),binding_status='metadata_matched',attachments=[pane] if live else [])])
            def terminal(argv, **kwargs):
                nonlocal live
                commands.append(argv)
                if 'new-window' in argv: live = True
                return subprocess.CompletedProcess(argv, 0, stdout='@4\t%7', stderr='')
            with patch('codex_wake.sessions.observe', side_effect=observe), patch('codex_wake.sessions.revalidate_attachment', return_value=True), patch('codex_wake.shared_app_server.SharedAppServerReader') as reader, patch('codex_wake.session_lifecycle.subprocess.run', side_effect=terminal):
                reader.return_value.__enter__.return_value.read_thread.return_value = thread
                reader.return_value.__enter__.return_value.server_metadata = metadata
                thread['status'] = {'type':'unknown'}
                with self.assertRaisesRegex(RuntimeTargetError, 'live_restore_runtime_state_unverified'):
                    LiveWakeRestorer(root, now=time.time).prepare(target)
                self.assertEqual(commands, [])
                thread['status'] = {'type':'idle'}
                prepared = LiveWakeRestorer(root, now=time.time).prepare(target)
                self.assertEqual(LiveWakeRestorer(root, now=time.time).prepare(target)['thread_id'], THREAD)
            launches = [cmd for cmd in commands if 'new-window' in cmd]
            self.assertEqual(len(launches), 1)
            self.assertIn(THREAD, launches[0][-1])
            self.assertIn(str(cwd), launches[0][-1])
            self.assertEqual(prepared['codex_cmd'], sys.executable)
            self.assertEqual(prepared['startup_policy'], 'active_tab')
