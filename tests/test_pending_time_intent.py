import contextlib
from datetime import UTC, datetime
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from codex_wake.cli import run
from codex_wake.daemon import poll_once
from codex_wake.records import all_records, classify_record
from codex_wake.time_provider import TimeDecision

THREAD = '01a1227e-a041-7b72-9c36-18349e7dd22c'


class PendingTimeIntentTests(unittest.TestCase):
    def arm(self, root, verb='after', trigger='1m', reading=None):
        with patch.dict(os.environ, {'CODEX_WAKE_STABLE_TIME_CONFIG': '/private/client.json'}), patch(
                'codex_wake.time_inspection.network_time_decision',
                return_value=reading or TimeDecision('uncertain', reason='stable_time_unbounded')), contextlib.redirect_stdout(io.StringIO()):
            return run(['--wake-root', str(root), 'native', verb, '--codex-path', sys.executable,
                        '--ttl', '2m', THREAD, trigger, '--', 'Continue'])

    def test_unknown_creation_retains_inspectable_intent_without_guest_timestamp(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'wake'
            with patch('codex_wake.records.utc_now', side_effect=AssertionError('guest clock forbidden')):
                self.assertEqual(self.arm(root), 0)
            record = all_records(root)[0].record
            self.assertEqual(record['schema_version'], 6)
            self.assertEqual(classify_record(record), 'native_pending_time_v6')
            self.assertIsNone(record['created_at'])
            self.assertIsNone(record['target']['expires_at'])
            self.assertEqual(record['time_intent']['delay_seconds'], 60)
            self.assertEqual(record['time_intent']['ttl_seconds'], 120)
            self.assertEqual(record['time_observation']['status'], 'uncertain')
            self.assertIsNone(record['time_observation']['lower'])
            self.assertIsNone(record['events'][0]['at'])
            self.assertNotIn('due_at', record['predicate'])
            result = poll_once(root, now=datetime(2100, 1, 1, tzinfo=UTC), dispatch=False,
                               time_provider=lambda: TimeDecision('uncertain'))
            self.assertEqual(result.pending, 1)
            self.assertEqual(result.fired, 0)
            self.assertEqual(all_records(root)[0].record, record)

    def test_recovery_preserves_id_and_waits_full_relative_delay_before_single_submission(self):
        import subprocess
        import json
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'wake'
            self.arm(root)
            original = all_records(root)[0].record
            identifier = original['id']
            restored = json.loads(subprocess.check_output([sys.executable, '-c',
                'import json,sys;from pathlib import Path;from codex_wake.records import all_records;print(json.dumps(all_records(Path(sys.argv[1]))[0].record))', str(root)], text=True))
            self.assertEqual(restored, original)
            finite = TimeDecision('network', ('stable-time:a', 'stable-time:b'), 1800000000, 1800000003)
            result = poll_once(root, now=datetime(2100, 1, 1, tzinfo=UTC), dispatch=False,
                               time_provider=lambda: finite)
            self.assertEqual(result.fired, 0)
            promoted = all_records(root)[0].record
            self.assertEqual(promoted['id'], identifier)
            self.assertEqual(promoted['schema_version'], 5)
            self.assertEqual(promoted['predicate']['due_at'], '2027-01-15T08:01:03Z')
            self.assertEqual(promoted['target']['expires_at'], '2027-01-15T08:03:03Z')
            self.assertEqual(promoted['events'][0], original['events'][0])
            before = TimeDecision('network', ('stable-time:a', 'stable-time:b'), 1800000062, 1800000064)
            self.assertEqual(poll_once(root, dispatch=False, time_provider=lambda: before).fired, 0)
            due = TimeDecision('network', ('stable-time:a', 'stable-time:b'), 1800000063, 1800000065)
            accepted = subprocess.CompletedProcess([], 0,
                f'Queued message 11111111-1111-1111-1111-111111111111 for thread {THREAD}.\n', '')
            with patch('codex_wake.native_delivery.read_native_thread',
                       return_value={'id': THREAD, 'status': {'type': 'idle'}}), patch(
                       'codex_wake.native_delivery.subprocess.run', return_value=accepted) as submit:
                self.assertEqual(poll_once(root, time_provider=lambda: due).submitted, 1)
                self.assertEqual(poll_once(root, time_provider=lambda: due).submitted, 0)
            self.assertEqual(submit.call_count, 1)
            self.assertEqual(all_records(root)[0].record['attempts'], 1)

    def test_absolute_deadline_and_ttl_are_never_extended_during_recovery(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'wake'
            self.arm(root, 'at', '2027-01-15T08:01:00.123456Z')
            original = all_records(root)[0].record
            self.assertEqual(original['time_intent']['due_at'], '2027-01-15T08:01:00.123456Z')
            self.assertEqual(original['target']['expires_at'], '2027-01-15T08:03:00.123456Z')
            # Recovery exactly straddling expiry cannot establish eligibility or expiry.
            crossing = TimeDecision('network', ('stable-time:a', 'stable-time:b'), 1800000180, 1800000181)
            self.assertEqual(poll_once(root, dispatch=False, time_provider=lambda: crossing).failed, 0)
            promoted = all_records(root)[0].record
            self.assertEqual(promoted['target']['expires_at'], original['target']['expires_at'])
            elapsed = TimeDecision('network', ('stable-time:a', 'stable-time:b'), 1800000181, 1800000182)
            self.assertEqual(poll_once(root, dispatch=False, time_provider=lambda: elapsed).failed, 1)
            self.assertEqual(all_records(root)[0].record['attempts'], 0)
            self.assertEqual(all_records(root)[0].record['target']['expires_at'], original['target']['expires_at'])

    def test_identical_overlapping_creation_and_recovery_retries_preserve_one_intent(self):
        from concurrent.futures import ThreadPoolExecutor
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'wake'
            self.arm(root)
            identifier = all_records(root)[0].record['id']
            self.arm(root)
            # A successful new observation does not silently replace an outstanding request.
            finite = TimeDecision('network', ('stable-time:a', 'stable-time:b'), 1800000000, 1800000003)
            self.arm(root, reading=finite)
            self.assertEqual(len(all_records(root)), 1)
            self.assertEqual(all_records(root)[0].record['id'], identifier)
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(lambda _: poll_once(root, dispatch=False, time_provider=lambda: finite), range(2)))
            self.assertEqual(sum(result.fired for result in results), 0)
            record = all_records(root)[0].record
            self.assertEqual(record['schema_version'], 5)
            self.assertEqual(sum(event['type'] == 'time_intent_admitted' for event in record['events']), 1)
            self.assertEqual(record['predicate']['due_at'], '2027-01-15T08:01:03Z')

    def test_cancellation_wins_when_time_recovers_before_promotion_lock(self):
        from codex_wake.records import cancel_record
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'wake'
            self.arm(root)
            identifier = all_records(root)[0].record['id']
            def recovery():
                cancel_record(root, identifier)
                return TimeDecision('network', ('stable-time:a', 'stable-time:b'), 1800000000, 1800000003)
            self.assertEqual(poll_once(root, dispatch=False, time_provider=recovery).fired, 0)
            record = all_records(root)[0].record
            self.assertEqual(record['status'], 'cancelled')
            self.assertEqual(record['schema_version'], 6)
            self.assertEqual(record['events'][-1]['type'], 'cancelled')
            self.assertIsNone(record['events'][-1]['at'])
            self.assertEqual(classify_record(record), 'native_pending_time_v6')

    def test_schema_discovery_advertises_pending_time_compatibility(self):
        from codex_wake.records import schema_summary
        summary = schema_summary()
        self.assertIn(6, summary['read_versions'])
        self.assertEqual(summary['native_pending_time_write_version'], 6)

    def test_read_only_reconcile_never_invents_guest_time_for_unknown_intent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'wake'
            self.arm(root)
            identifier = all_records(root)[0].record['id']
            with patch('codex_wake.native_delivery.utc_now', side_effect=AssertionError('guest clock forbidden')), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(run(['--wake-root', str(root), 'native', 'reconcile', identifier]), 0)
            self.assertIsNone(all_records(root)[0].record['updated_at'])

    def test_direct_dispatch_reports_retained_unknown_intent_without_any_effect(self):
        from codex_wake.injector import dispatch_firing_record
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'wake'
            self.arm(root)
            found = all_records(root)[0]
            with patch('codex_wake.native_delivery.subprocess.run') as submit, patch(
                    'codex_wake.injector.utc_now', side_effect=AssertionError('guest clock forbidden')):
                result = dispatch_firing_record(root, found)
            self.assertEqual(result.status, 'skipped')
            self.assertIn('pending time', result.message)
            submit.assert_not_called()
            self.assertEqual(all_records(root)[0].record, found.record)

    def test_simultaneous_public_creation_returns_one_durable_wake(self):
        from concurrent.futures import ThreadPoolExecutor
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'wake'
            with patch.dict(os.environ, {'CODEX_WAKE_STABLE_TIME_CONFIG': '/private/client.json'}), patch(
                    'codex_wake.time_inspection.network_time_decision', return_value=TimeDecision('uncertain')), contextlib.redirect_stdout(io.StringIO()):
                def create(_):
                    return run(['--wake-root', str(root), 'native', 'after', '--codex-path', sys.executable,
                                '--ttl', '2m', THREAD, '1m', '--', 'Continue'])
                with ThreadPoolExecutor(max_workers=2) as pool:
                    self.assertEqual(list(pool.map(create, range(2))), [0, 0])
            self.assertEqual(len(all_records(root)), 1)
            self.assertEqual(classify_record(all_records(root)[0].record), 'native_pending_time_v6')

    def test_malformed_pending_intents_and_forced_firing_are_held_without_native_effect(self):
        import json
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'wake'
            self.arm(root)
            found = all_records(root)[0]
            original = found.record
            for change in ({'status': 'firing'}, {'time_intent': {}}, {'attempts': True},
                           {'time_observation': {'status': 'network', 'lower': 1, 'upper': 2}},
                           {'target': dict(original['target'], expires_at='2100-01-01T00:00:00Z')}):
                with self.subTest(change=change):
                    found.path.write_text(json.dumps(dict(original, **change)))
                    before = found.path.read_bytes()
                    with patch('codex_wake.native_delivery.subprocess.run') as submit:
                        result = poll_once(root, time_provider=lambda: TimeDecision(
                            'network', ('stable-time:a', 'stable-time:b'), 1800009999, 1800010002))
                    self.assertEqual(result.dispatched, 0)
                    submit.assert_not_called()
                    self.assertEqual(found.path.read_bytes(), before)

    def test_file_intent_recovers_with_fixed_ttl_and_cannot_expire_from_guest_skew(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'wake'
            self.arm(root, 'file', str(Path(tmp) / 'missing'))
            finite = TimeDecision('network', ('stable-time:a', 'stable-time:b'), 1800000000, 1800000003)
            self.assertEqual(poll_once(root, dispatch=False, time_provider=lambda: finite).fired, 0)
            record = all_records(root)[0].record
            self.assertEqual(record['predicate']['type'], 'file_exists')
            self.assertEqual(record['target']['expires_at'], '2027-01-15T08:02:03Z')
            self.assertEqual(poll_once(root, datetime(2100, 1, 1, tzinfo=UTC), dispatch=False,
                                      time_provider=lambda: TimeDecision('uncertain')).failed, 0)
            expired = TimeDecision('network', ('stable-time:a', 'stable-time:b'), 1800000123, 1800000125)
            self.assertEqual(poll_once(root, dispatch=False, time_provider=lambda: expired).failed, 1)
            self.assertEqual(all_records(root)[0].record['target'], record['target'])

    def test_cancelled_unknown_intent_can_archive_without_inventing_a_retention_age(self):
        from codex_wake.records import archive_record, cancel_record, cleanup_archived_records
        from datetime import timedelta
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'wake'
            self.arm(root)
            identifier = all_records(root)[0].record['id']
            cancel_record(root, identifier)
            with patch('codex_wake.records.utc_now', side_effect=AssertionError('guest clock forbidden')):
                archive_record(root, identifier)
            archived = all_records(root, include_archive=True)[0].record
            self.assertEqual(archived['status'], 'archived')
            self.assertIsNone(archived['archived_at'])
            self.assertIsNone(archived['updated_at'])
            self.assertIsNone(archived['events'][-1]['at'])
            self.assertEqual(cleanup_archived_records(root, older_than=timedelta(days=1),
                             now=datetime(2100, 1, 1, tzinfo=UTC), delete=True), [])
            self.assertEqual(len(all_records(root, include_archive=True)), 1)

    def test_retained_stable_time_intent_cannot_promote_from_a_different_provider(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'wake'
            self.arm(root, 'at', '2027-01-15T08:01:00Z')
            original = all_records(root)[0].record
            for reading in (TimeDecision('network', ('legacy:a', 'legacy:b'), 1800000061, 1800000062),
                            TimeDecision('windows', ('windows',), 1800000061, 1800000062),
                            TimeDecision('network', ('stable-time:a', 'legacy:b'), 1800000061, 1800000062)):
                with self.subTest(reading=reading), patch('codex_wake.native_delivery.subprocess.run') as submit:
                    result = poll_once(root, time_provider=lambda: reading)
                    self.assertEqual(result.fired, 0)
                    submit.assert_not_called()
                    self.assertEqual(all_records(root)[0].record, original)

    def test_configured_creation_retains_intent_if_finite_read_has_wrong_provider_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'wake'
            self.arm(root, reading=TimeDecision('network', ('legacy:a', 'legacy:b'), 1800000000, 1800000001))
            record = all_records(root)[0].record
            self.assertEqual(record['schema_version'], 6)
            self.assertIsNone(record['created_at'])

    def test_promoted_intent_keeps_stable_time_authority_after_selector_is_disabled(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'wake'
            self.arm(root)
            finite = TimeDecision('network', ('stable-time:a', 'stable-time:b'), 1800000000, 1800000003)
            poll_once(root, dispatch=False, time_provider=lambda: finite)
            promoted = all_records(root)[0].record
            alternate = TimeDecision('network', ('legacy:a', 'legacy:b'), 1800000064, 1800000065)
            with patch.dict(os.environ, {'CODEX_WAKE_STABLE_TIME_CONFIG': ''}):
                result = poll_once(root, dispatch=False, time_provider=lambda: alternate)
            self.assertEqual(result.fired, 0)
            self.assertEqual(all_records(root)[0].record, promoted)

    def test_direct_dispatch_of_admitted_intent_cannot_switch_provider(self):
        from codex_wake.injector import dispatch_firing_record
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'wake'
            self.arm(root)
            finite = TimeDecision('network', ('stable-time:a', 'stable-time:b'), 1800000000, 1800000003)
            poll_once(root, dispatch=False, time_provider=lambda: finite)
            due = TimeDecision('network', ('stable-time:a', 'stable-time:b'), 1800000064, 1800000065)
            self.assertEqual(poll_once(root, dispatch=False, time_provider=lambda: due).fired, 1)
            firing = all_records(root)[0]
            alternate = TimeDecision('network', ('legacy:a', 'legacy:b'), 1800000064, 1800000065)
            with patch.dict(os.environ, {'CODEX_WAKE_STABLE_TIME_CONFIG': ''}), patch(
                    'codex_wake.native_delivery.subprocess.run', return_value=__import__('subprocess').CompletedProcess(
                        [], 0, f'Queued message 11111111-1111-1111-1111-111111111111 for thread {THREAD}.\n', '')) as submit, patch(
                    'codex_wake.native_delivery.read_native_thread',
                    return_value={'id': THREAD, 'status': {'type': 'idle'}}):
                result = dispatch_firing_record(root, firing, time_provider=lambda: alternate)
            self.assertEqual(result.status, 'skipped')
            submit.assert_not_called()
            self.assertEqual(all_records(root)[0].record, firing.record)

    def test_malformed_required_event_history_holds_before_promotion(self):
        import json
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'wake'
            self.arm(root)
            found = all_records(root)[0]
            original = found.record
            finite = TimeDecision('network', ('stable-time:a', 'stable-time:b'), 1800000000, 1800000003)
            for history in (1, None, {}, [1], [{'message': 'missing explicit event identity'}]):
                with self.subTest(history=history):
                    found.path.write_text(json.dumps(dict(original, events=history)))
                    before = found.path.read_bytes()
                    self.assertEqual(classify_record(all_records(root)[0].record), 'hold')
                    self.assertEqual(poll_once(root, dispatch=False, time_provider=lambda: finite).fired, 0)
                    self.assertEqual(found.path.read_bytes(), before)
