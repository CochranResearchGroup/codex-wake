import tempfile
import unittest
import hashlib
from pathlib import Path
from codex_wake.objective_ledger import ObjectiveLedger


def config(revision=1, limit=100, deadline=200):
    return dict(revision=revision, objective_token_limit=limit,
                objective_time_limit_seconds=100, session_token_limit=60,
                session_time_limit_seconds=50, max_correction_cycles=2,
                started_at=100, objective_deadline=deadline)


class ObjectiveLedgerTests(unittest.TestCase):
    def test_context_successor_retains_completion_assignment_and_replay_does_not_reassign(self):
        with tempfile.TemporaryDirectory() as root:
            ledger=ObjectiveLedger(root,'objective')
            ledger.configure(config(limit=200),'operator',now=100)
            ledger.bind_requests({'transport':'fixture'},{'source':0},now=100)
            evidence=Path(root)/'approved-plan';evidence.write_text('existing completion authority')
            authority={'path':str(evidence),'sha256':hashlib.sha256(evidence.read_bytes()).hexdigest()}
            obligations=[dict(id=name,kind=name,tokens=60,seconds=4,criterion='Verify '+name)
                         for name in ('acceptance','review','remediation')]
            ledger.protect_completion(obligations,source=authority,now=100)
            ledger.assign_completion('source','acceptance',source=authority,now=100)
            self.assertTrue(ledger.reserve_request('request:first','source',40,1,now=101)['admitted'])
            ledger.settle_request('request:first','response',10,'fixture',now=102)
            ledger.continue_request_thread('successor','source',{'intent':'switch'},now=103)
            self.assertTrue(ledger.reserve_request('request:continued','successor',40,1,now=104)['admitted'])
            ledger.assign_completion('source','review',source=authority,now=105)
            view=ledger.continue_request_thread('successor','source',{'intent':'switch'},now=106)
            self.assertEqual(view['request_sessions']['successor']['completion_obligation'],'acceptance')

    def test_cross_account_continuation_shares_original_session_spend_and_deadline(self):
        with tempfile.TemporaryDirectory() as root:
            ledger=ObjectiveLedger(root,'objective')
            ledger.configure(config(),'operator',prior_tokens=20,now=100)
            ledger.bind_requests({'transport':'fixture'}, {'source':20},now=100)
            before=ledger.inspect(now=110)
            linked=ledger.continue_request_thread('successor','source',{'intent':'switch'},now=110)
            self.assertEqual(linked['request_sessions']['successor']['deadline'],150)
            self.assertEqual(linked['tokens_used'],before['tokens_used'])
            self.assertEqual(linked['authorization_history'],before['authorization_history'])
            self.assertTrue(ledger.reserve_request('request:child','successor',30,10,now=110)['admitted'])
            ledger.settle_request('request:child','response',30,'fixture',now=111)
            ledger=ObjectiveLedger(root,'objective')
            self.assertFalse(ledger.reserve_request('request:source-again','source',11,1,now=112)['admitted'])
            replay=ledger.continue_request_thread('successor','source',{'intent':'switch'},now=113)
            self.assertEqual(replay['tokens_used'],50)
            self.assertEqual(replay['original_deadline'],200)
            self.assertFalse(ledger.reserve_request('request:late','successor',1,1,now=150)['admitted'])

    def test_late_sampled_floor_remains_unknown_atomically_and_cannot_readmit(self):
        with tempfile.TemporaryDirectory() as root:
            ledger=ObjectiveLedger(root,'objective');ledger.configure(config(),'operator',now=100)
            ledger.reserve('a',60,40,now=100);ledger.record('a',20,now=101)
            view=ledger.record_sampled_floor('a',35,now=102)
            self.assertEqual(view['tokens_used'],35)
            self.assertFalse(view['accounting_known'])
            self.assertFalse(view['actors']['a']['settled'])
            self.assertFalse(ledger.reserve('b',10,10,now=102)['admitted'])
            replay=ObjectiveLedger(root,'objective').record_sampled_floor('a',30,now=103)
            self.assertEqual(replay['tokens_used'],35)
            self.assertFalse(replay['accounting_known'])

    def test_correction_limit_survives_successor_replacement_and_controller_restart(self):
        with tempfile.TemporaryDirectory() as root:
            ledger=ObjectiveLedger(root,'objective')
            ledger.configure(config(),'operator',now=100)
            ledger.reserve('old-context',60,40,now=100)
            ledger.record('old-context',20,now=110)
            self.assertTrue(ledger.correction(key='old-context:review',actor_id='old-context',now=110)['admitted'])
            ledger.record('old-context',20,settled=True,now=110)
            ledger=ObjectiveLedger(root,'objective')
            self.assertTrue(ledger.reserve('replacement-context',40,30,now=110)['admitted'])
            ledger.record('replacement-context',10,now=120)
            self.assertTrue(ledger.correction(key='replacement-context:review',actor_id='replacement-context',now=120)['admitted'])
            ledger=ObjectiveLedger(root,'objective')
            stopped=ledger.correction(key='replacement-context:rejected-again',actor_id='replacement-context',now=120)
            self.assertFalse(stopped['admitted'])
            self.assertEqual(stopped['correction_cycles'],2)
            self.assertEqual(stopped['tokens_used'],30)
            self.assertEqual(stopped['actors']['replacement-context']['session_deadline'],140)
            self.assertEqual(stopped['original_deadline'],200)

    def test_active_native_parent_keeps_future_quota_reserved_before_worker_admission(self):
        with tempfile.TemporaryDirectory() as root:
            ledger=ObjectiveLedger(root,'objective')
            ledger.configure(config(),'operator',now=100)
            ledger.record_goal('parent',20,now=100)
            self.assertTrue(ledger.adopt_active_goal('parent',60,150,now=100)['admitted'])
            self.assertFalse(ledger.reserve('worker',45,20,now=100)['admitted'])
            self.assertTrue(ledger.reserve('worker',40,20,now=100)['admitted'])
            replay=ObjectiveLedger(root,'objective').adopt_active_goal('parent',60,200,now=110)
            self.assertEqual(replay['actors']['parent']['session_deadline'],150)
            late=ledger.record_goal('parent',70,now=110)
            self.assertEqual(late['tokens_used']+late['tokens_reserved'],110)
            self.assertFalse(ledger.reserve('worker',40,20,now=110)['admitted'])

    def test_successor_goal_and_preflight_are_charged_once_when_successor_becomes_source(self):
        with tempfile.TemporaryDirectory() as root:
            ledger = ObjectiveLedger(root, 'objective')
            ledger.configure(config(), 'operator', now=100)
            ledger.reserve('successor', 60, 40, now=100)
            ledger.record('successor', 10, now=110)
            ledger.bind_goal('thread:goal-created', 'successor', 10, now=110)
            ledger.record_goal('thread:goal-created', 20, now=120)
            ledger = ObjectiveLedger(root, 'objective')
            view = ledger.record_goal('thread:goal-created', 20, settled=True, now=120)
            self.assertEqual(view['tokens_used'], 30)
            self.assertEqual(view['remaining_tokens'], 70)
    def test_explicit_reset_replaces_caps_without_erasing_spend_or_cycles(self):
        with tempfile.TemporaryDirectory() as root:
            ledger = ObjectiveLedger(root, 'objective')
            ledger.configure(config(), 'initial operator grant', now=100)
            ledger.reserve('a', 50, 10, now=100)
            ledger.record('a', 40, settled=True, now=110)
            ledger.correction(now=110)
            view = ledger.reset(config(2, 60, 300), 'explicit reset', now=200)
            self.assertEqual(view['tokens_used'], 40)
            self.assertEqual(view['remaining_tokens'], 20)
            self.assertEqual(view['original_deadline'], 200)
            self.assertEqual(view['correction_cycles'], 1)
            self.assertEqual(view['authorization_history'][-1]['action'], 'reset')
            replay = ledger.reset(config(2, 60, 300), 'explicit reset', now=201)
            self.assertEqual(len(replay['authorization_history']), 2)
    def test_shared_cap_survives_restart_and_snapshots_are_idempotent(self):
        with tempfile.TemporaryDirectory() as root:
            ledger = ObjectiveLedger(root, 'objective')
            ledger.configure(config(), {'approved': True}, now=100)
            self.assertTrue(ledger.reserve('a', 60, 40, now=100)['admitted'])
            ledger.record('a', 60, settled=True, now=110)
            ledger.record('a', 60, settled=True, now=110)
            ledger = ObjectiveLedger(root, 'objective')
            self.assertTrue(ledger.reserve('b', 40, 40, now=110)['admitted'])
            ledger.record('b', 40, settled=True, now=120)
            self.assertFalse(ledger.reserve('c', 1, 1, now=120)['admitted'])
            self.assertEqual(ledger.view(now=120)['tokens_used'], 100)

    def test_unknown_decreasing_and_deadline_hold_admission(self):
        with tempfile.TemporaryDirectory() as root:
            ledger = ObjectiveLedger(root, 'objective')
            ledger.configure(config(), True, now=100)
            ledger.reserve('a', 50, 10, now=100)
            ledger.record('a', 20, now=110)
            self.assertEqual(ledger.record('a', None, now=110)['tokens_reserved'], 30)
            self.assertFalse(ledger.reserve('b', 10, 10, now=110)['admitted'])
            self.assertFalse(ledger.record('a', 19, now=110)['accounting_known'])
            ledger.record('a', 20, settled=True, now=110)
            self.assertFalse(ledger.reserve('b', 10, 10, now=200)['admitted'])
            self.assertFalse(ledger.view(now=100)['ready'])

    def test_extension_and_corrections_preserve_history(self):
        with tempfile.TemporaryDirectory() as root:
            ledger = ObjectiveLedger(root, 'objective')
            ledger.configure(config(), True, prior_tokens=10, now=100)
            ledger.record('observed', 30, settled=True, now=100)
            self.assertTrue(ledger.correction(now=100)['admitted'])
            self.assertTrue(ObjectiveLedger(root, 'objective').correction(now=100)['admitted'])
            self.assertFalse(ledger.correction(now=100)['admitted'])
            with self.assertRaises(ValueError):
                ledger.configure(config(2, 200, 300), True, now=200)
            view = ledger.extend(config(2, 200, 300), {'approval': 'explicit'}, now=200)
            self.assertEqual(view['tokens_used'], 40)
            self.assertEqual(view['original_deadline'], 200)
            self.assertEqual(len(view['authorization_history']), 2)
            self.assertEqual(view['correction_cycles'], 2)

    def test_concurrent_reservations_conserve_cap(self):
        from concurrent.futures import ProcessPoolExecutor
        with tempfile.TemporaryDirectory() as root:
            ledger = ObjectiveLedger(root, 'objective')
            ledger.configure(config(), True, now=100)
            with ProcessPoolExecutor(max_workers=4) as executor:
                results = list(executor.map(reserve_worker, [(root, str(i)) for i in range(8)]))
            self.assertEqual(sum(results), 2)
            self.assertEqual(ledger.view(now=100)['tokens_reserved'], 100)
            view = ledger.reserve('0', 50, 10, now=100)
            self.assertEqual(view['tokens_reserved'], 100)

    def test_actual_overspend_charged_and_terms_immutable(self):
        with tempfile.TemporaryDirectory() as root:
            ledger = ObjectiveLedger(root, 'objective')
            ledger.configure(config(), True, now=100)
            ledger.reserve('a', 50, 10, now=100)
            with self.assertRaises(ValueError):
                ledger.reserve('a', 40, 10, now=100)
            view = ledger.record('a', 120, settled=True, now=110)
            self.assertEqual(view['tokens_used'], 120)
            self.assertFalse(view['ready'])


    def test_replay_cannot_reopen_spent_settled_or_expired_session(self):
        with tempfile.TemporaryDirectory() as root:
            ledger = ObjectiveLedger(root, 'objective')
            ledger.configure(config(), True, now=100)
            ledger.reserve('a', 20, 10, now=100)
            self.assertTrue(ledger.reserve('a', 20, 10, now=105)['admitted'])
            ledger.record('a', 20, now=105)
            self.assertFalse(ledger.reserve('a', 20, 10, now=105)['admitted'])
            ledger.reserve('b', 20, 10, now=105)
            ledger.record('b', 1, settled=True, now=106)
            self.assertFalse(ledger.reserve('b', 20, 10, now=106)['admitted'])
            ledger.reserve('c', 20, 10, now=106)
            self.assertFalse(ledger.reserve('c', 20, 10, now=116)['admitted'])

    def test_untrusted_paths_are_rejected_without_repair(self):
        import hashlib
        import os
        from pathlib import Path
        with tempfile.TemporaryDirectory() as root:
            path = Path(root)
            os.chmod(path, 0o755)
            with self.assertRaises(ValueError):
                ObjectiveLedger(root, 'objective')
            self.assertEqual(path.stat().st_mode & 0o777, 0o755)
            os.chmod(path, 0o700)
            ledger = ObjectiveLedger(root, 'objective')
            ledger.configure(config(), True, now=100)
            directory = path / 'objective-ledgers'
            name = hashlib.sha256(b'objective').hexdigest()
            data = directory / (name + '.json')
            os.chmod(data, 0o644)
            with self.assertRaises(ValueError):
                ledger.view(now=100)
            os.chmod(data, 0o600)
            data.unlink()
            data.symlink_to(path / 'missing')
            with self.assertRaises(ValueError):
                ledger.view(now=100)
            data.unlink()
            lock = directory / (name + '.lock')
            lock.unlink()
            lock.symlink_to(path / 'missing')
            with self.assertRaises(OSError):
                ledger.view(now=100)


def reserve_worker(args):
    root, actor = args
    return ObjectiveLedger(root, 'objective').reserve(actor, 50, 10, now=100)['admitted']
