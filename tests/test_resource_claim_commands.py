"""The caller seam binds claims to verified managed agents without role arguments."""
from pathlib import Path
import tempfile
import unittest

from codex_wake.managed_inventory import ManagedInventory, Observation
from codex_wake.resource_claim_commands import execute
from codex_wake.resource_claims import ResourceClaimError
from codex_wake.records import WakeError

THREAD = '00000000-0000-7000-8000-000000000331'
META = dict(threadId=THREAD, sessionId=THREAD, callId='call-331',
            **{'x-codex-turn-metadata': dict(thread_id=THREAD, session_id=THREAD, turn_id='turn-331')})


class ResourceClaimCommandTests(unittest.TestCase):
    def test_verified_caller_can_claim_and_check_only_its_managed_workspace(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            workspace, outside = root / 'workspace', root / 'outside'
            workspace.mkdir(); outside.mkdir()
            wake = root / 'wake'
            sample = Observation('codex', 'codex:fixture', THREAD, str(workspace), 'ready', 100,
                'native_metadata', dict(pid=123, start_ticks=42, boot_id='boot'), [], {'inspect': 'supported'})
            agent = ManagedInventory(wake, now=lambda: 100).enroll(sample, operator=True)['agent']
            arguments = dict(managed_agent_id=agent['managed_agent_id'], kind='worktree', path=str(workspace))
            observer = lambda args: sample
            with self.assertRaises((WakeError, ValueError)):
                execute('claim', arguments, wake, observer=observer, now=lambda: 100)
            claimed = execute('claim', arguments, wake, observer=observer, native_context=META, now=lambda: 100)
            checked = execute('check', dict(managed_agent_id=agent['managed_agent_id'],
                claim_id=claimed['claim_id'], generation=1), wake, observer=observer, native_context=META, now=lambda: 100)
            self.assertEqual(checked['status'], 'admitted')
            self.assertTrue(checked['point_in_time_only'])
            with self.assertRaises(ResourceClaimError) as denied:
                execute('claim', dict(arguments, path=str(outside)), wake,
                        observer=observer, native_context=META, now=lambda: 100)
            self.assertEqual(denied.exception.code, 'workspace_denied')

    def test_operator_cli_can_allocate_external_prefix_and_release_with_reason(self):
        import argparse
        import contextlib
        import io
        import json
        from codex_wake.resource_claim_commands import register_parser, run
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            workspace, prefix = root / 'workspace', root / 'prefix'
            workspace.mkdir(); prefix.mkdir()
            wake = root / 'wake'
            sample = Observation('codex', 'codex:fixture', THREAD, str(workspace), 'ready', 100,
                'native_metadata', dict(pid=123, start_ticks=42, boot_id='boot'), [], {'inspect': 'supported'})
            agent = ManagedInventory(wake, now=lambda: 100).enroll(sample, operator=True)['agent']
            parser = argparse.ArgumentParser()
            register_parser(parser.add_subparsers(dest='command', required=True))
            def cli(*arguments):
                args = parser.parse_args(['resources', *arguments])
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    code = run(args, wake, observer=lambda args: sample, now=lambda: 100)
                return code, json.loads(output.getvalue())
            code, claim = cli('claim', '--operator', '--managed-agent-id', agent['managed_agent_id'],
                '--kind', 'install_prefix', '--path', str(prefix))
            self.assertEqual(code, 0, claim)
            code, denied = cli('release', '--operator', '--claim-id', claim['claim_id'], '--generation', '1')
            self.assertEqual(code, 2, denied)
            code, released = cli('release', '--operator', '--claim-id', claim['claim_id'], '--generation', '1', '--reason', 'owner offline; reviewed effect')
            self.assertEqual(code, 0, released)
            self.assertEqual(released['status'], 'released')

    def test_changed_runtime_generation_and_model_operator_flag_cannot_recover_custody(self):
        from codex_wake.records import WakeError
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            workspace = root / 'workspace'; workspace.mkdir()
            wake = root / 'wake'
            sample = Observation('codex', 'codex:fixture', THREAD, str(workspace), 'ready', 100,
                'native_metadata', dict(pid=123, start_ticks=42, boot_id='boot'), [], {'inspect': 'supported'})
            agent = ManagedInventory(wake, now=lambda: 100).enroll(sample, operator=True)['agent']
            args = dict(managed_agent_id=agent['managed_agent_id'], kind='worktree', path=str(workspace))
            claim = execute('claim', args, wake, native_context=META, observer=lambda args: sample, now=lambda: 100)
            changed = Observation('codex', 'codex:fixture', THREAD, str(workspace), 'ready', 100,
                'native_metadata', dict(pid=123, start_ticks=43, boot_id='boot'), [], {'inspect': 'supported'})
            check = dict(managed_agent_id=agent['managed_agent_id'], claim_id=claim['claim_id'], generation=1)
            with self.assertRaises(ResourceClaimError):
                execute('check', check, wake, native_context=META, observer=lambda args: changed, now=lambda: 100)
            with self.assertRaises(ResourceClaimError):
                execute('release', dict(check, operator=True), wake, native_context=META, now=lambda: 100)
            other_meta = dict(threadId='00000000-0000-7000-8000-000000000999')
            with self.assertRaises((WakeError, ValueError)):
                execute('release', check, wake, native_context=other_meta, observer=lambda args: sample, now=lambda: 100)
            self.assertEqual(execute('show', dict(claim_id=claim['claim_id']), wake)['status'], 'active')
