import argparse
from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest

from codex_wake import attention_commands as commands
from codex_wake.a2a_bus import BusStore
from codex_wake.attention_queue import AttentionError
from codex_wake.session_permissions import Principal
from test_attention_queue import context


def payload():
    return dict(key='one', kind='decision', question='Continue?', options=['accept', 'decline'],
        evidence=['receipt:one'], priority='normal', expires_at=200,
        context=context(), permission_decision=False)


class AttentionCommandTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)

    def test_public_host_adapter_and_restart(self):
        def execute(action, arguments, principal):
            return commands.execute(action, arguments, self.root, principal=principal,
                context_validator=lambda row: context(), now=lambda: 100)
        row = execute('request', {'request': payload()}, Principal('agent-one'))
        response = execute('respond', dict(request_id=row['request_id'], choice='accept',
            expected_revision=1, fingerprint=row['fingerprint']), Principal('operator', 'operator'))
        self.assertEqual(response['status'], 'responded')
        result = execute('consume', dict(request_id=row['request_id'], expected_revision=2,
            fingerprint=row['fingerprint']), Principal('agent-one'))
        self.assertFalse(result['executes_operation'])
        shown = execute('show', {'request_id': row['request_id']}, Principal('agent-one'))
        self.assertEqual(shown['status'], 'consumed')

    def test_mcp_response_and_role_arguments_cannot_self_approve(self):
        for action, arguments in [('respond', {}), ('consume', {}), ('close', {}),
                ('request', {'operator': True}), ('request', {'role': 'operator'})]:
            with self.subTest(action=action, arguments=arguments), self.assertRaises(AttentionError):
                commands.execute(action, arguments, self.root, principal=Principal('agent-one'), mcp=True)

    def test_real_operator_capability_cli_records_response_without_validator(self):
        bus, capability = BusStore.configure(self.root / 'bus')
        parser = argparse.ArgumentParser()
        commands.register_parser(parser.add_subparsers(dest='command'))
        packet = payload()
        packet['context'] = context(owner='local-operator')
        file = self.root / 'request.json'
        file.write_text(json.dumps(packet))
        common = ['--bus-root', str(bus.root), '--operator-capability', str(capability)]

        def run(arguments):
            output = StringIO()
            with redirect_stdout(output):
                code = commands.run(parser.parse_args(['attention'] + arguments + common),
                    self.root / 'wake', now=lambda: 100)
            self.assertEqual(code, 0, output.getvalue())
            return json.loads(output.getvalue())

        row = run(['request', '--file', str(file)])
        self.assertEqual(row['status'], 'open')
        response = run(['respond', '--request-id', row['request_id'], '--choice', 'accept',
            '--expected-revision', '1', '--fingerprint', row['fingerprint']])
        self.assertEqual(response['status'], 'responded')
        shown = run(['show', '--request-id', row['request_id']])
        self.assertEqual(shown['response']['actor'], 'local-operator')
