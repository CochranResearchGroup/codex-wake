import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from codex_wake.cli import main
from codex_wake.a2a_bus import BusStore
from codex_wake.a2a_identity import RuntimeIdentity


class BusCLITests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / 'bus'
        self.repo = Path(self.temporary.name) / 'repo'
        self.repo.mkdir()

    def invoke(self, arguments):
        with patch('sys.stdout', new_callable=io.StringIO) as out:
            code = main(['a2a', *arguments, '--bus-root', str(self.root), '--json'])
        return code, json.loads(out.getvalue())

    def test_configure_enroll_status_pause_with_explicit_operator_capability(self):
        code, configured = self.invoke(['configure'])
        self.assertEqual(code, 0)
        capability = configured['operator_capability_file']
        self.assertNotIn('secret', json.dumps(configured))
        identity = RuntimeIdentity('runtime', 'fixture-thread', str(self.repo))
        with patch('codex_wake.a2a_cli.resolve_identity', return_value=identity):
            code, enrolled = self.invoke(['enroll', str(self.repo), '--thread', 'thread:fixture-thread', '--operator-capability', capability])
        self.assertEqual(code, 0)
        self.assertTrue(enrolled['actor_receipt_id'])
        code, status = self.invoke(['status', '--operator-capability', capability])
        self.assertEqual(code, 0)
        self.assertEqual(status['bus']['active_actors'], 1)
        self.assertEqual(status['bus']['notification_capability'], 'unqualified')
        code, resumed = self.invoke(['resume', '--operator-capability', capability])
        self.assertEqual(code, 0)
        self.assertFalse(resumed['paused'])

    def test_bad_operator_never_reads_peer_runtime(self):
        self.invoke(['configure'])
        wrong = self.root / 'wrong.json'
        wrong.write_text(json.dumps(dict(bus_id='local', secret='wrong')))
        wrong.chmod(0o600)
        with patch('codex_wake.a2a_cli.resolve_identity') as resolver:
            code, denied = self.invoke(['enroll', str(self.repo), '--thread', 'thread:fixture', '--operator-capability', str(wrong)])
        self.assertEqual(code, 7)
        self.assertEqual(denied['error']['code'], 'authorization_denied')
        resolver.assert_not_called()

    def test_repeated_actor_issuance_returns_policy_receipt_for_reconciliation(self):
        _, configured = self.invoke(['configure'])
        arguments = ['enroll', str(self.repo), '--thread', 'thread:fixture', '--operator-capability', configured['operator_capability_file']]
        with patch('codex_wake.a2a_cli.resolve_identity', return_value=RuntimeIdentity('runtime', 'fixture', str(self.repo))):
            self.assertEqual(self.invoke(arguments)[0], 0)
            code, duplicate = self.invoke(arguments)
        self.assertEqual(code, 8)
        self.assertEqual(duplicate['error']['code'], 'already_authorized')
        self.assertTrue(duplicate['partial_receipt_ids'])
        self.assertTrue(duplicate['reconciliation_required'])

    def test_wrong_thread_root_rejected_before_enrollment(self):
        _, configured = self.invoke(['configure'])
        with patch('codex_wake.a2a_cli.resolve_identity', return_value=RuntimeIdentity('runtime', 'fixture', str(self.root))):
            code, denied = self.invoke(['enroll', str(self.repo), '--thread', 'thread:fixture', '--operator-capability', configured['operator_capability_file']])
        self.assertEqual(code, 7)
        self.assertEqual(BusStore(self.root).status()['enrolled_roots'], 0)

    def test_filesystem_failure_retains_committed_enrollment_receipt(self):
        _, configured = self.invoke(['configure'])
        (self.root / 'capabilities').write_text('fixture obstruction')
        with patch('codex_wake.a2a_cli.resolve_identity', return_value=RuntimeIdentity('runtime', 'fixture', str(self.repo))):
            code, failed = self.invoke(['enroll', str(self.repo), '--thread', 'thread:fixture', '--operator-capability', configured['operator_capability_file']])
        self.assertEqual(code, 8)
        self.assertEqual(BusStore(self.root).status()['enrolled_roots'], 1)
        self.assertTrue(failed['partial_receipt_ids'])
        self.assertTrue(failed['reconciliation_required'])

    def test_issued_actor_context_does_not_inherit_pane_authority(self):
        from codex_wake.a2a_cli import invoking_actor
        class Reader:
            server_metadata = dict(codexHome='/fixture/codex')
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read_thread(self, identifier):
                return dict(id=identifier, cwd=str(self.repo), modelProvider='fixture')
        reader = Reader()
        reader.repo = self.repo
        identity = RuntimeIdentity.from_metadata(reader.read_thread('fixture'), reader.server_metadata)
        store, operator = BusStore.configure(self.root)
        store.enroll(self.repo, operator)
        capability, _ = store.issue_actor(identity, self.repo, operator)
        with patch.dict('os.environ', {'CODEX_THREAD_ID': 'fixture', 'TMUX_PANE': '%parent'}), patch('codex_wake.a2a_cli.SharedAppServerReader', return_value=reader), patch('codex_wake.a2a_cli.Path.cwd', return_value=self.repo):
            actor = invoking_actor(store, capability, endpoint='unix:///fixture/socket')
        self.assertEqual(actor.thread_id, 'fixture')
        self.assertEqual(actor.root, str(self.repo))
