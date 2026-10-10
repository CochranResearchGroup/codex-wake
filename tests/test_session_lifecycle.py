from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch
from codex_wake.cli import run


class SessionLifecycleTests(unittest.TestCase):
    def test_open_requires_explicit_new_or_resume_before_creating_a_tab(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch('subprocess.run') as subprocess:
                with self.assertRaises(SystemExit) as error:
                    run(['sessions', 'open', '--name', 'worker', '--cwd', tmp])
                self.assertEqual(error.exception.code, 2)
                subprocess.assert_not_called()

    def test_resume_reuses_exact_existing_attachment(self):
        from codex_wake.session_lifecycle import open_session
        thread = '01a123a8-5782-7d43-a214-55b293bbd65f'
        row = {'thread_id': thread, 'attachments': [{'pane_id': '%4', 'window_id': '@3'}]}
        args = SimpleNamespace(resume=thread, new=False, extra_attachment=False,
                               tmux_socket='/tmp/fixture', app_server='unix://', timeout=10,
                               codex_path='codex', tmux_session='work', name='worker', cwd=None)
        with patch('codex_wake.session_lifecycle.observe', return_value={'complete': True}), patch(
                'codex_wake.session_lifecycle.resolve', return_value=row), patch(
                'codex_wake.session_lifecycle.subprocess.run') as command:
            result = open_session(args)
        self.assertEqual(result['thread_id'], thread)
        self.assertEqual(result['action'], 'reused')
        command.assert_not_called()

    def test_close_refuses_split_tab_without_killing_any_pane(self):
        from codex_wake.records import WakeError
        with tempfile.TemporaryDirectory() as tmp:
            row = {'thread_id': '01a123a8-5782-7d43-a214-55b293bbd65f',
                   'cwd': tmp, 'runtime_state': 'idle',
                   'attachments': [{'pane_id': '%4', 'window_id': '@3'}]}
            with patch('codex_wake.session_lifecycle.observe', return_value={'complete': True}), patch(
                    'codex_wake.session_lifecycle.resolve', return_value=row), patch(
                    'codex_wake.session_lifecycle.revalidate_attachment', return_value=True), patch(
                    'codex_wake.supervisor.default_registry_dir', return_value=Path(tmp)/'registry'), patch(
                    'codex_wake.session_lifecycle.tmux_command', return_value='%4\n%5') as command:
                with self.assertRaisesRegex(WakeError, 'multiple panes'):
                    run(['--wake-root', tmp, 'sessions', 'close', 'window:@3', '--force'])
            self.assertFalse(any('kill-pane' in call.args or 'kill-window' in call.args
                                 for call in command.call_args_list))

    def test_ambiguous_close_returns_existing_selection_error_contract(self):
        from codex_wake.sessions import SelectionError
        from contextlib import redirect_stdout
        from io import StringIO
        output = StringIO()
        with tempfile.TemporaryDirectory() as tmp, redirect_stdout(output), patch(
                'codex_wake.session_lifecycle.observe', return_value={'complete': True}), patch(
                'codex_wake.session_lifecycle.resolve',
                side_effect=SelectionError(4, 'selector matches multiple panes or windows', 'window:@3')):
            self.assertEqual(run(['--wake-root', tmp, 'sessions', 'close', 'window:@3', '--json']), 4)
        self.assertIn('selector matches multiple panes', output.getvalue())

    def test_unreadable_pending_work_prevents_ordinary_close(self):
        from codex_wake.records import WakeError
        with tempfile.TemporaryDirectory() as tmp:
            pending = Path(tmp)/'pending'
            pending.mkdir()
            (pending/'damaged.json').write_text('{"target":"invalid","status":"pending","id":"damaged"}')
            row = {'thread_id': '01a123a8-5782-7d43-a214-55b293bbd65f', 'cwd': tmp,
                   'runtime_state': 'idle', 'attachments': [{'pane_id': '%4', 'window_id': '@3'}]}
            with patch('codex_wake.session_lifecycle.observe', return_value={'complete': True}), patch(
                    'codex_wake.session_lifecycle.resolve', return_value=row), patch(
                    'codex_wake.session_lifecycle.revalidate_attachment', return_value=True), patch(
                    'codex_wake.supervisor.default_registry_dir', return_value=Path(tmp)/'registry'), patch(
                    'codex_wake.session_lifecycle.tmux_command', return_value='%4'):
                with self.assertRaisesRegex(WakeError, 'pending wakes'):
                    run(['--wake-root', tmp, 'sessions', 'close', 'window:@3'])

    def test_unpublished_signal_registration_prevents_ordinary_close(self):
        from dataclasses import replace
        from codex_wake.records import WakeError
        from codex_wake.signal_store import SQLiteSignalModule
        from codex_wake.signal_records import signal_journal_path
        from codex_wake.event_wake import EventWake
        from codex_wake.signals import Resume
        from tests.test_signals import make_adapter, make_intent, NOW
        thread = '01a123a8-5782-7d43-a214-55b293bbd65f'
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            module = SQLiteSignalModule(signal_journal_path(root))
            intent = replace(make_intent(), resume=Resume('follow up', root,
                             {'transport': 'native', 'thread_id': thread}))
            EventWake(module, adapters=(make_adapter(),), clock=lambda: NOW,
                      id_factory=lambda: 'wake_unpublished').register(intent, idempotency_key='pending-close')
            self.assertFalse((root/'pending'/'wake_unpublished.json').exists())
            row = {'thread_id': thread, 'cwd': tmp, 'runtime_state': 'idle',
                   'attachments': [{'pane_id': '%4', 'window_id': '@3'}]}
            with patch('codex_wake.session_lifecycle.observe', return_value={'complete': True}), patch(
                    'codex_wake.session_lifecycle.resolve', return_value=row), patch(
                    'codex_wake.session_lifecycle.revalidate_attachment', return_value=True), patch(
                    'codex_wake.supervisor.default_registry_dir', return_value=root/'registry'), patch(
                    'codex_wake.session_lifecycle.tmux_command', return_value='%4'):
                with self.assertRaisesRegex(WakeError, 'pending wakes'):
                    run(['--wake-root', tmp, 'sessions', 'close', 'window:@3'])

    def test_pending_mailbox_work_prevents_ordinary_close(self):
        from codex_wake.records import WakeError
        from tests.test_a2a_mailbox import MailboxTests
        fixture = MailboxTests()
        fixture.setUp()
        try:
            fixture.send()
            row = {'thread_id': 'recipient', 'cwd': str(fixture.repo), 'runtime_state': 'idle',
                   'attachments': [{'pane_id': '%4', 'window_id': '@3'}]}
            with patch('codex_wake.session_lifecycle.observe', return_value={'complete': True}), patch(
                    'codex_wake.session_lifecycle.resolve', return_value=row), patch(
                    'codex_wake.session_lifecycle.revalidate_attachment', return_value=True), patch(
                    'codex_wake.supervisor.default_registry_dir', return_value=fixture.repo/'registry'), patch(
                    'codex_wake.a2a_bus.default_bus_root', return_value=fixture.bus.root), patch(
                    'codex_wake.session_lifecycle.tmux_command', return_value='%4'):
                with self.assertRaisesRegex(WakeError, 'pending'):
                    run(['--wake-root', str(fixture.repo), 'sessions', 'close', 'window:@3'])
        finally:
            fixture.doCleanups()

    def test_terminal_mailbox_receipts_allow_ordinary_idle_tab_close(self):
        import json
        from contextlib import redirect_stdout
        from io import StringIO
        from tests.test_a2a_mailbox import MailboxTests
        fixture = MailboxTests()
        fixture.setUp()
        try:
            identifier = fixture.send(delivery='inbox')['message']['message_id']
            fixture.mailbox.read(fixture.recipient, identifier)
            fixture.mailbox.ack(fixture.recipient, identifier, outcome='accepted')
            fixture.mailbox.ack(fixture.recipient, identifier, outcome='completed')
            from codex_wake.a2a_scheduler import MailScheduler
            deferred = fixture.send('held-control')['message']['message_id']
            fixture.bus.set_paused(False, fixture.operator)
            scheduler = MailScheduler(fixture.mailbox, fixture.operator)
            lease = scheduler.acquire()
            scheduler.defer(lease, scheduler.jobs(lease)[0]['job_id'], 'offline')
            fixture.mailbox.cancel(fixture.sender, deferred)
            self.assertEqual(fixture.mailbox.pending_thread_work('recipient'), [])
            row = {'thread_id': 'recipient', 'cwd': str(fixture.repo), 'runtime_state': 'idle',
                   'attachments': [{'pane_id': '%4', 'window_id': '@3'}]}
            output = StringIO()
            with redirect_stdout(output), patch(
                    'codex_wake.session_lifecycle.observe', return_value={'complete': True}), patch(
                    'codex_wake.session_lifecycle.resolve', return_value=row), patch(
                    'codex_wake.session_lifecycle.revalidate_attachment', return_value=True), patch(
                    'codex_wake.supervisor.default_registry_dir', return_value=fixture.repo/'registry'), patch(
                    'codex_wake.a2a_bus.default_bus_root', return_value=fixture.bus.root), patch(
                    'codex_wake.session_lifecycle.tmux_command', return_value='%4') as command:
                self.assertEqual(run(['--wake-root', str(fixture.repo), 'sessions', 'close',
                                      'window:@3', '--bus-root', str(fixture.bus.root), '--json']), 0)
            closed = json.loads(output.getvalue())
            self.assertFalse(closed['forced'])
            self.assertEqual(closed['affected_messages'], [])
            self.assertTrue(any('kill-pane' in call.args for call in command.call_args_list))
        finally:
            fixture.doCleanups()
