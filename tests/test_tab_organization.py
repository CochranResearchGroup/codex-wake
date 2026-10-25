import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from codex_wake.process import process_identity
from codex_wake.session_permissions import Principal
from codex_wake.tab_organization_commands import execute


@unittest.skipUnless(shutil.which('tmux'), 'tmux required')
class TabOrderingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.socket = str(self.root / 'tmux.sock')
        self.tmux('new-session', '-d', '-s', 'fixture', '-n', 'focused', 'sleep 120')
        self.addCleanup(lambda: subprocess.run(['tmux', '-S', self.socket, 'kill-server'], capture_output=True))
        self.session = self.tmux('display-message', '-p', '#{session_id}').strip()
        for name in ('ready', 'working'):
            self.tmux('new-window', '-d', '-t', self.session, '-n', name, 'sleep 120')
        self.repo = self.root / 'repo'
        subprocess.run(['git', 'init', '-q', str(self.repo)], check=True)
        self.principal = Principal('local-operator', 'operator')
        self.args = dict(socket_path=self.socket, session_id=self.session)
        self.route = self.root / 'pending-route.json'
        self.route.write_text('{"pane":"stable","deadline":"original"}')

    def tmux(self, *args):
        return subprocess.check_output(['tmux', '-f', '/dev/null', '-S', self.socket, *args], text=True, timeout=5)

    def evidence(self, timeout):
        rows = self.tmux('list-panes', '-a', '-F', '#{pane_id}\t#{pane_pid}\t#{window_name}').splitlines()
        result = {}
        for row in rows:
            pane, pid, name = row.split('\t')
            result[pane] = dict(conversation_id='fixture-' + pane, namespace='fixture',
                process=dict(pid=int(pid), start_ticks=process_identity(int(pid))['start_time_ticks'],
                             boot_id=process_identity(int(pid))['boot_id']), root=str(self.repo),
                state='working' if name == 'working' else 'ready', fresh=True)
        return result

    def call(self, action, **options):
        return execute(action, dict(self.args, **options), self.root / 'wake',
                       principal=self.principal, observer=self.evidence)

    def layout(self):
        return self.tmux('list-windows', '-t', self.session, '-F', '#{window_name}').splitlines()

    def test_public_preview_apply_and_conditional_undo_preserve_processes_and_routes(self):
        before = self.evidence(5)
        route = self.route.read_bytes()
        preview = self.call('preview')
        self.assertEqual([w['name'] for w in preview['plan']['target']], ['focused', 'working', 'ready'])
        applied = self.call('apply', plan_id=preview['plan']['plan_id'])
        self.assertEqual(applied['receipt']['status'], 'applied', applied['receipt'])
        self.assertEqual(self.layout(), ['focused', 'working', 'ready'])
        self.assertEqual(before, self.evidence(5))
        self.assertEqual(route, self.route.read_bytes())
        undone = self.call('undo', receipt_id=applied['receipt']['receipt_id'])
        self.assertEqual(undone['receipt']['status'], 'undone')
        self.assertEqual(self.layout(), ['focused', 'ready', 'working'])
        self.assertEqual(before, self.evidence(5))

    def test_stale_plan_refuses_before_effect_and_newer_layout_holds_undo(self):
        from codex_wake.tab_organization import TabError
        preview = self.call('preview')
        self.tmux('rename-window', '-t', self.session + ':@1', 'human-edit')
        before = self.layout()
        with self.assertRaises(TabError) as held:
            self.call('apply', plan_id=preview['plan']['plan_id'])
        self.assertEqual(held.exception.code, 'workspace_stale_plan')
        self.assertEqual(self.layout(), before)
        self.tmux('rename-window', '-t', self.session + ':@1', 'ready')
        preview = self.call('preview')
        applied = self.call('apply', plan_id=preview['plan']['plan_id'])
        self.tmux('select-window', '-t', self.session + ':@1')
        before = self.layout()
        with self.assertRaises(TabError):
            self.call('undo', receipt_id=applied['receipt']['receipt_id'])
        self.assertEqual(self.layout(), before)

    def test_uncertain_swap_is_receipted_and_replay_never_swaps_again(self):
        from codex_wake.tab_organization import TmuxTransport, TabError
        base = TmuxTransport(self.socket, self.session)
        class LostResponse:
            calls = 0
            snapshot = base.snapshot
            def swap(inner, first, second, deadline):
                inner.calls += 1
                base.swap(first, second, deadline)
                raise TimeoutError('response lost after effect')
        transport = LostResponse()
        def call(action, **options):
            return execute(action, dict(self.args, **options), self.root / 'wake',
                principal=self.principal, observer=self.evidence, transport=transport)
        preview = call('preview')
        applied = call('apply', plan_id=preview['plan']['plan_id'])
        self.assertEqual(applied['receipt']['status'], 'uncertain')
        self.assertEqual(self.layout(), ['focused', 'working', 'ready'])
        replay = call('apply', plan_id=preview['plan']['plan_id'])
        self.assertEqual(replay['receipt']['receipt_id'], applied['receipt']['receipt_id'])
        self.assertEqual(transport.calls, 1)
        with self.assertRaises(TabError):
            call('undo', receipt_id=applied['receipt']['receipt_id'])

    def test_unqualified_explicit_and_linked_windows_pin_exact_slots(self):
        preview = self.call('preview', pins=['@1'])
        self.assertEqual(preview['plan']['before']['windows'][1]['pins'], ['explicit'])
        self.assertEqual([w['name'] for w in preview['plan']['target']], ['focused', 'ready', 'working'])
        self.tmux('new-session', '-d', '-s', 'other', 'sleep 120')
        self.tmux('link-window', '-d', '-s', self.session + ':@2', '-t', 'other:5')
        preview = self.call('preview')
        self.assertIn('linked', preview['plan']['before']['windows'][2]['pins'])
        original = self.evidence
        def unqualified(timeout):
            values = original(timeout)
            values.pop('%1')
            return values
        result = execute('preview', self.args, self.root / 'wake', principal=self.principal,
                         observer=unqualified)
        self.assertIn('unqualified', result['plan']['before']['windows'][1]['pins'])

    def test_changed_permission_revision_refuses_original_plan(self):
        from codex_wake.session_permissions import PermissionStore
        from codex_wake.tab_organization import TabError
        store = PermissionStore(self.root / 'wake')
        store.configure({'version': 1}, self.principal, expected_revision=0)
        preview = self.call('preview')
        store.configure({'version': 1}, self.principal, expected_revision=1)
        with self.assertRaises(TabError) as held:
            self.call('apply', plan_id=preview['plan']['plan_id'])
        self.assertEqual(held.exception.code, 'workspace_stale_plan')
        self.assertEqual(self.layout(), ['focused', 'ready', 'working'])

    def test_verified_operator_cli_uses_actual_tmux_and_capability(self):
        import argparse
        import contextlib
        import io
        from codex_wake.a2a_bus import BusStore
        from codex_wake.tab_organization_commands import register_parser, run
        bus, capability = BusStore.configure(self.root / 'bus')
        parser = argparse.ArgumentParser()
        register_parser(parser.add_subparsers(dest='command', required=True))
        def cli(verb, *options, cap=capability):
            args = parser.parse_args(['tabs', verb, '--socket-path', self.socket,
                '--session-id', self.session, '--bus-root', str(bus.root),
                '--operator-capability', str(cap), *options])
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = run(args, self.root / 'wake', observer=self.evidence)
            return code, json.loads(output.getvalue())
        code, preview = cli('preview')
        self.assertEqual(code, 0, preview)
        code, applied = cli('apply', '--plan-id', preview['plan']['plan_id'])
        self.assertEqual(code, 0, applied)
        self.assertEqual(self.layout(), ['focused', 'working', 'ready'])
        code, undone = cli('undo', '--receipt-id', applied['receipt']['receipt_id'])
        self.assertEqual(code, 0, undone)
        self.assertEqual(self.layout(), ['focused', 'ready', 'working'])
        fake = self.root / 'fake-capability'
        fake.write_text('{}')
        code, denied = cli('apply', '--plan-id', preview['plan']['plan_id'], cap=fake)
        self.assertEqual(code, 2, denied)
        self.assertEqual(self.layout(), ['focused', 'ready', 'working'])

    def test_git_common_directory_joins_worktrees_and_mixed_split_is_pinned(self):
        subprocess.run(['git', '-C', str(self.repo), '-c', 'user.name=Fixture',
            '-c', 'user.email=fixture@example.invalid', 'commit', '-q', '--allow-empty', '-m', 'fixture'], check=True)
        worktree = self.root / 'worktree'
        subprocess.run(['git', '-C', str(self.repo), 'worktree', 'add', '-q', '-b', 'fixture', str(worktree)], check=True)
        other = self.root / 'other'
        subprocess.run(['git', 'init', '-q', str(other)], check=True)
        original = self.evidence
        def worktrees(timeout):
            result = original(timeout)
            result['%1']['root'] = str(worktree)
            return result
        result = execute('preview', dict(self.args, mode='repository'), self.root / 'wake',
                         principal=self.principal, observer=worktrees)
        rows = result['plan']['before']['windows']
        self.assertEqual(rows[1]['repository'], rows[2]['repository'])
        self.tmux('split-window', '-d', '-t', '@1', 'sleep 120')
        def mixed(timeout):
            result = worktrees(timeout)
            result['%3']['root'] = str(other)
            return result
        result = execute('preview', self.args, self.root / 'wake', principal=self.principal, observer=mixed)
        self.assertIn('mixed', result['plan']['before']['windows'][1]['pins'])

    def test_mandatory_deny_and_invalid_budget_cannot_change_layout(self):
        from codex_wake.session_permissions import PermissionStore, PermissionDenied
        from codex_wake.tab_organization import TabError
        store = PermissionStore(self.root / 'wake')
        store.configure(dict(version=1, mandatory=['workspace.order']), self.principal, expected_revision=0)
        preview = self.call('preview')
        with self.assertRaises(PermissionDenied):
            self.call('apply', plan_id=preview['plan']['plan_id'])
        with self.assertRaises(TabError):
            self.call('preview', timeout=31)
        with self.assertRaises(TabError):
            execute('apply', dict(self.args, plan_id=preview['plan']['plan_id']),
                    self.root / 'wake', principal=Principal('session'), observer=self.evidence)
        self.assertEqual(self.layout(), ['focused', 'ready', 'working'])

    def test_private_journal_can_be_inspected_after_socket_disappears(self):
        preview = self.call('preview')
        self.tmux('kill-server')
        shown = self.call('show', plan_id=preview['plan']['plan_id'])
        self.assertEqual(shown['record']['plan_id'], preview['plan']['plan_id'])
