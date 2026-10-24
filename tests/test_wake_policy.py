import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from codex_wake.cli import run
from codex_wake.records import all_records, classify_record
from codex_wake.daemon import poll_once
from codex_wake.injector import dispatch_firing_record
from codex_wake.runtime_delivery import RuntimeRecipient, RuntimeObservation, RuntimeSubmission, RuntimeReconciliation

THREAD = '01a1227e-a041-7b72-9c36-18349e7dd22c'
CLOCK = {'utc': None, 'counter': {'epoch': 'boot-a', 'counter': 1000, 'frequency': 1000, 'rate_ppm': 0}}


class WakePolicyTests(unittest.TestCase):
    def register(self, root, *options, key='policy-test'):
        with patch('codex_wake.native_clock.snapshot', return_value=CLOCK), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(run(['--wake-root', str(root), 'native', 'after', '--json',
                                  '--codex-path', sys.executable, '--idempotency-key', key,
                                  *options, THREAD, '1m', '--', 'Continue']), 0)
        return next(x.record for x in all_records(root) if x.record['scheduling_intent']['idempotency_key'] == key)

    def test_new_wake_freezes_configurable_startup_and_existing_intent_survives_default_change(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            original = self.register(root)
            self.assertEqual(original['schema_version'], 8)
            self.assertEqual(original['wake_policy']['startup'], 'create_load_run')
            self.assertEqual(classify_record(original), 'native_intent_v6')
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(run(['--wake-root', str(root), 'wake-policy', 'configure',
                                      '--startup', 'active_tab', '--operator']), 0)
            self.assertEqual(self.register(root), original)
            self.assertEqual(self.register(root, key='second')['wake_policy']['startup'], 'active_tab')

    def test_owner_completion_actions_are_distinct_and_closed_tab_is_not_completion(self):
        for action, expected in [('retire', 'cancelled'), ('hold', 'pending'), ('retain', 'firing')]:
            with self.subTest(action=action), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                original = self.register(root, '--wake-lifetime', 'task', '--owner-id', 'daily-report', '--owner-end', action)
                with patch('codex_wake.native_clock.snapshot', return_value={'utc': None, 'counter': dict(CLOCK['counter'], counter=62000)}):
                    poll_once(root, dispatch=False)
                self.assertEqual(all_records(root)[0].record['status'], 'firing')
                args = ['--wake-root', str(root), 'wake-policy', 'owner-complete', '--operator',
                        '--owner-kind', 'task', '--owner-id', 'daily-report', '--event-id', 'completed-1']
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(run(args), 0)
                    self.assertEqual(run(args), 0)
                with patch('codex_wake.native_clock.snapshot', return_value={'utc': None, 'counter': dict(CLOCK['counter'], counter=63000)}):
                    poll_once(root, dispatch=False)
                record = all_records(root)[0].record
                self.assertEqual(record['status'], expected)
                self.assertEqual(record['scheduling_intent'], original['scheduling_intent'])
                self.assertEqual(record['attempts'], 0)

    def test_uncertain_submission_survives_owner_retirement_and_reconciles_without_resend(self):
        class Adapter:
            submits = 0
            reconciles = 0
            def resolve(self, target):
                return RuntimeRecipient('codex', THREAD, target)
            def observe(self, recipient):
                return RuntimeObservation('ready', 'fixture_idle', {})
            def submit(self, recipient, prompt):
                self.submits += 1
                return RuntimeSubmission('uncertain', reason='response_lost')
            def reconcile(self, recipient, prompt):
                self.reconciles += 1
                return RuntimeReconciliation(reason='not_yet_observed')
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.register(root, '--wake-lifetime', 'task', '--owner-id', 'daily-report')
            adapter = Adapter()
            observed = {'utc': None, 'counter': dict(CLOCK['counter'], counter=62000)}
            with patch('codex_wake.native_clock.snapshot', return_value=observed):
                poll_once(root, dispatch=False)
                dispatch_firing_record(root, all_records(root)[0], runtime_adapter=adapter)
            self.assertEqual(adapter.submits, 1)
            with contextlib.redirect_stdout(io.StringIO()):
                run(['--wake-root', str(root), 'wake-policy', 'owner-complete', '--operator',
                     '--owner-kind', 'task', '--owner-id', 'daily-report', '--event-id', 'completed-1'])
            self.assertEqual(all_records(root)[0].record['native_delivery']['state'], 'uncertain')
            with patch('codex_wake.native_clock.snapshot', return_value=observed):
                dispatch_firing_record(root, all_records(root)[0], runtime_adapter=adapter)
            self.assertEqual(adapter.submits, 1)
            self.assertEqual(adapter.reconciles, 1)
            self.assertEqual(all_records(root)[0].record['attempts'], 1)

    def test_old_records_keep_legacy_meaning_and_malformed_policy_holds(self):
        from copy import deepcopy
        with tempfile.TemporaryDirectory() as temporary:
            record = self.register(Path(temporary))
            old = {key: value for key, value in record.items() if key not in ('wake_policy', 'intent_schema_version')}
            old['schema_version'] = 6
            self.assertEqual(classify_record(old), 'native_intent_v6')
            changed = deepcopy(record)
            changed['wake_policy']['startup'] = 'unknown_startup'
            self.assertEqual(classify_record(changed), 'hold')
            changed = deepcopy(record)
            changed['schema_version'] = 6
            self.assertEqual(classify_record(changed), 'hold')
            changed = deepcopy(record)
            changed['wake_policy']['startup'] = 'background_saved'
            self.assertEqual(classify_record(changed), 'hold')

    def test_explicit_policy_conflict_does_not_create_another_intent(self):
        from codex_wake.records import WakeError
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            original = self.register(root)
            with self.assertRaisesRegex(WakeError, 'idempotency_conflict'):
                self.register(root, '--recipient-startup', 'active_tab')
            self.assertEqual([x.record for x in all_records(root)], [original])


if __name__ == '__main__':
    unittest.main()
