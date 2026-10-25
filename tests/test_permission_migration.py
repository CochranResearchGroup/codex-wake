"""Operator adoption preserves explicit legacy authority and original intent (#325)."""
from contextlib import redirect_stdout
from io import StringIO
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from codex_wake.session_permissions import PermissionStore,Principal,PermissionDenied


class PermissionMigrationTests(unittest.TestCase):
    def test_public_operator_adoption_preserves_legacy_profile_grants_and_denials(self):
        from codex_wake.cli import run
        from codex_wake.a2a_bus import BusStore
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);bus,cap=BusStore.configure(base/'bus');root=base/'wake'
            legacy=base/'profiles.json';legacy.write_text(json.dumps({'version':1,
                'profiles':{'self':{},'worker':{}},'callers':{'denied':[],'limited':['worker']}}));legacy.chmod(0o600)
            original=legacy.read_bytes()
            policy=base/'policy.json';policy.write_text('{"version":1}');policy.chmod(0o600)
            argv=['--wake-root',str(root),'permissions','adopt','--bus-root',str(bus.root),
                '--operator-capability',str(cap),'--file',str(policy),'--legacy-profiles',str(legacy),
                '--expected-revision','0','--json']
            out=StringIO()
            with redirect_stdout(out):code=run(argv)
            self.assertEqual(code,0,out.getvalue())
            store=PermissionStore(root)
            self.assertEqual(store.evaluate('refresh.self',Principal('denied'),launch_profile='self')['permission'],'deny')
            self.assertEqual(store.evaluate('refresh.self',Principal('limited'),launch_profile='self')['permission'],'deny')
            self.assertEqual(store.evaluate('refresh.self',Principal('limited'),launch_profile='worker')['permission'],'allow')
            self.assertEqual(store.evaluate('refresh.self',Principal('new'),launch_profile='self')['permission'],'allow')
            self.assertEqual(legacy.read_bytes(),original)
            store.configure({'version':1,'global':{'default':'allow'}},Principal('op','operator'),expected_revision=1)
            self.assertEqual(store.evaluate('refresh.self',Principal('denied'),launch_profile='self')['permission'],'deny')
            self.assertEqual(store._read()['policy']['adoption']['source_sha256'],hashlib.sha256(original).hexdigest())

    def test_unmapped_legacy_entry_is_actionable_and_never_adopted(self):
        from codex_wake.permission_migration import plan,adopt
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'profiles.json';path.write_text(json.dumps({'version':1,'profiles':{},'callers':{'actor':['missing']}}));path.chmod(0o600)
            result=plan(tmp,{'version':1},legacy_profiles=path)
            self.assertFalse(result['can_adopt']);self.assertIn('unmapped_legacy_profile_entry',result['issues'])
            store=PermissionStore(tmp)
            with self.assertRaises(PermissionDenied):adopt(store,{'version':1},Principal('op','operator'),expected_revision=0,legacy_profiles=path)
            self.assertFalse(store.active())

    def test_legacy_pending_wake_requires_explicit_hold_and_retains_original_bytes(self):
        from test_wake_policy import WakePolicyTests,THREAD
        from codex_wake.permission_migration import plan,adopt
        from codex_wake.records import all_records
        from codex_wake.native_delivery import dispatch_native
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);WakePolicyTests().register(root)
            found=all_records(root)[0];before=found.path.read_bytes()
            proposal=plan(root,{'version':1})
            self.assertFalse(proposal['can_adopt']);self.assertEqual(len(proposal['pending']),1)
            store=PermissionStore(root);op=Principal('op','operator')
            with self.assertRaises(PermissionDenied):adopt(store,{'version':1},op,expected_revision=0)
            self.assertFalse(store.active());self.assertEqual(found.path.read_bytes(),before)
            adopted=adopt(store,{'version':1},op,expected_revision=0,hold_legacy_pending=True)
            self.assertEqual(adopted['legacy_pending_held'],1)
            with patch('codex_wake.native_delivery._codex_adapter') as adapter:
                result=dispatch_native(root,found,None,clock_provider=lambda:None)
                adapter.assert_not_called()
            self.assertIn('legacy_permission_adoption_required',result.message)
            self.assertEqual(found.path.read_bytes(),before)
            self.assertEqual(found.record['target']['thread_id'],THREAD)

    def test_bound_bus_conflict_is_rejected_before_another_policy_is_adopted(self):
        from codex_wake.a2a_bus import BusStore
        from codex_wake.cli import run
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);bus,cap=BusStore.configure(base/'bus')
            file=base/'policy.json';file.write_text('{"version":1}');file.chmod(0o600)
            options=['permissions','configure','--bus-root',str(bus.root),'--operator-capability',str(cap),
                '--file',str(file),'--expected-revision','0','--json']
            with redirect_stdout(StringIO()):self.assertEqual(run(['--wake-root',str(base/'first'),*options]),0)
            output=StringIO()
            with redirect_stdout(output):code=run(['--wake-root',str(base/'second'),*options])
            self.assertEqual(code,2)
            self.assertEqual(json.loads(output.getvalue())['error']['code'],'permission_root_binding_conflict')
            self.assertFalse(PermissionStore(base/'second').active())
