"""The leaf CLI adapter exposes the same brief admission contract as MCP."""
import argparse
from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest

from codex_wake.a2a_bus import BusStore
from codex_wake.task_briefs import BriefAuthority
from codex_wake.task_brief_commands import register_parser, task_briefs_command


class TaskBriefCommandTests(unittest.TestCase):
    def test_operator_capability_approves_and_worker_pins_without_role_argument(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            bus, capability = BusStore.configure(directory / 'bus')
            parser = argparse.ArgumentParser()
            register_parser(parser.add_subparsers(dest='command', required=True))
            content = dict(objective='Implement approved packet', phase='implementation',
                non_goals=['No release'], acceptance=['Expected public behavior'], context=[],
                workspace=str(directory), allocation_ref='existing-allocation', permission_ref='existing-profile')
            content_file = directory / 'brief.json'
            content_file.write_text(json.dumps(content))
            root = directory / 'wake'
            worker = BriefAuthority('native:worker', 'worker', ('task-1',))
            def command(verb, *extra, authority=None):
                args = parser.parse_args(['task-briefs', verb, '--task-id', 'task-1', *extra])
                output = StringIO()
                with redirect_stdout(output):
                    code = task_briefs_command(args, root, authority=authority)
                return code, json.loads(output.getvalue())
            code, proposed = command('propose', '--brief-file', str(content_file), authority=worker)
            self.assertEqual(code, 0)
            self.assertEqual(proposed['brief']['status'], 'proposed')
            code, denied = command('approve', '--revision', '1', authority=worker)
            self.assertEqual(code, 5)
            self.assertEqual(denied['error']['code'], 'authority_denied')
            code, approved = command('approve', '--revision', '1', '--bus-root', str(bus.root),
                                    '--operator-capability', str(capability))
            self.assertEqual(code, 0)
            self.assertEqual(approved['brief']['status'], 'approved')
            code, admitted = command('admit', '--assignment-id', 'instruction-a', authority=worker)
            self.assertEqual(code, 0)
            self.assertEqual(admitted['brief']['pin']['revision'], 1)
            code, checkpoint = command('pin', '--assignment-id', 'instruction-a', authority=worker)
            self.assertEqual(code, 0)
            self.assertEqual(checkpoint['brief']['task_id'], 'task-1')

    def test_worker_workspace_is_enforced_for_revision_selection_and_retries(self):
        from codex_wake.task_briefs import TaskBriefStore
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a, b = root / 'A', root / 'B'
            a.mkdir(); b.mkdir()
            store = TaskBriefStore(root / 'wake')
            operator = BriefAuthority('operator:test', 'operator')
            worker = BriefAuthority('worker:test', 'worker', ('task',), workspace=str(a))
            parser = argparse.ArgumentParser()
            register_parser(parser.add_subparsers(dest='command', required=True))
            def command(verb, *extra):
                args = parser.parse_args(['task-briefs', verb, '--task-id', 'task', *extra])
                output = StringIO()
                with redirect_stdout(output):
                    code = task_briefs_command(args, root / 'wake', authority=worker)
                return code, json.loads(output.getvalue())
            for workspace in (a, b):
                proposal = store.propose('task', dict(objective='Work', phase='implementation',
                    non_goals=['Release'], acceptance=['Done'], context=[], workspace=str(workspace),
                    allocation_ref='existing', permission_ref='existing'), authority=operator)
                store.approve('task', proposal['revision'], authority=operator)
            for verb, extra in [('admit', ['--assignment-id', 'latest']),
                                ('admit', ['--assignment-id', 'explicit', '--revision', '2']),
                                ('inspect', [])]:
                with self.subTest(verb=verb, extra=extra):
                    code, value = command(verb, *extra)
                    self.assertEqual(code, 5, value)
                    self.assertEqual(value['error']['code'], 'authority_denied')
            code, value = command('admit', '--assignment-id', 'allowed', '--revision', '1')
            self.assertEqual(code, 0, value)
            self.assertEqual(command('pin', '--assignment-id', 'allowed')[0], 0)
            # Existing admissions are rechecked against the current caller workspace.
            store.admit('task', 'foreign', authority=BriefAuthority('worker:test', 'worker', ('task',)), revision=2)
            for verb, extra in [('pin', []), ('admit', ['--revision', '2'])]:
                code, value = command(verb, '--assignment-id', 'foreign', *extra)
                self.assertEqual(code, 5, value)
                self.assertEqual(value['error']['code'], 'authority_denied')
