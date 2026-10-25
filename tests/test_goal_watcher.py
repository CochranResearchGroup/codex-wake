"""Configured watcher repair never unmasks or selects an unrelated runtime root."""
import tempfile
import unittest
from types import SimpleNamespace
from pathlib import Path
from codex_wake.session_permissions import Principal


class GoalWatcherTests(unittest.TestCase):
    def service(self, root, *, masked=False, wrong_root=False):
        calls=[]
        state=dict(active='inactive')
        def run(argv, **kwargs):
            calls.append(argv)
            if argv[2]=='start':
                state['active']='active'
                return SimpleNamespace(returncode=0,stdout='',stderr='')
            body='\n'.join(['LoadState=masked' if masked else 'LoadState=loaded',
                'UnitFileState=masked' if masked else 'UnitFileState=enabled',
                'ActiveState='+state['active'],'SubState=running' if state['active']=='active' else 'SubState=dead',
                'MainPID=123' if state['active']=='active' else 'MainPID=0',
                'ExecStart={ path=/opt/wake/bin/codex-wake ; argv[]=/opt/wake/bin/codex-wake --wake-root '+('/other' if wrong_root else str(root))+' goal-limits watch ; }'])
            return SimpleNamespace(returncode=0,stdout=body,stderr='')
        return run,calls

    def test_masked_watcher_requires_operator_decision_without_start(self):
        from codex_wake.goal_watcher import start_watcher
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            runner,calls=self.service(root,masked=True)
            result=start_watcher(root,principal=Principal('operator','operator'),runner=runner)
            self.assertEqual(result['reason'],'watcher_masked')
            self.assertFalse(result['start_attempted'])
            self.assertFalse(any('start' in call for call in calls))
            self.assertIn('operator',result['next_action'].lower())

    def test_wrong_configured_root_is_never_started(self):
        from codex_wake.goal_watcher import start_watcher
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            runner,calls=self.service(root,wrong_root=True)
            result=start_watcher(root,principal=Principal('operator','operator'),runner=runner)
            self.assertEqual(result['reason'],'watcher_scope_mismatch')
            self.assertFalse(any('start' in call for call in calls))

    def test_authorized_start_is_not_enforcement_or_engagement_proof(self):
        from codex_wake.goal_watcher import start_watcher
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            runner,calls=self.service(root)
            result=start_watcher(root,principal=Principal('operator','operator'),runner=runner)
            self.assertTrue(result['start_attempted'])
            self.assertEqual(result['active_state'],'active')
            self.assertFalse(result['enforcement_verified'])
            self.assertEqual([a for a in calls if a[2]=='start'],[['systemctl','--user','start','codex-wake-goal-limits.service']])

    def test_model_cannot_start_watcher_without_separate_standing_permission(self):
        from codex_wake.goal_watcher import start_watcher
        from codex_wake.session_permissions import PermissionStore, PermissionDenied
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            store=PermissionStore(root)
            store.configure({'version':1},Principal('operator','operator'),expected_revision=0)
            runner,calls=self.service(root)
            with self.assertRaises(PermissionDenied):
                start_watcher(root,principal=Principal('session'),runner=runner)
            self.assertFalse(calls)
            store.configure({'version':1,'global':{'actions':{'enforcement.watcher_start':'allow'}}},
                Principal('operator','operator'),expected_revision=1)
            result=start_watcher(root,principal=Principal('session'),runner=runner)
            self.assertTrue(result['start_attempted'])
