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
