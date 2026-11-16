"""Bounded native delivery at the public runtime adapter seam."""
import unittest

from codex_wake.codex_runtime import CodexRuntimeAdapter
from codex_wake.runtime_delivery import RuntimeSubmissionEnvelope


class BoundedNativeDeliveryTests(unittest.TestCase):
    def test_unqualified_backend_refuses_before_submission_io(self):
        def forbidden(*args, **kwargs):
            self.fail('unqualified native backend performed submission I/O')
        adapter = CodexRuntimeAdapter(read_thread=forbidden, request=forbidden,
            run=forbidden, project_failure=forbidden)
        recipient = adapter.resolve(dict(transport='native', thread_id='01a1227e-a041-7b72-9c36-18349e7dd22c',
            endpoint='unix://', codex_cmd='/codex'))
        outcome = adapter.submit_bounded(recipient, 'wake', RuntimeSubmissionEnvelope(
            '4d18e29e-9c05-45e7-a387-e50459dd3496', 1791504600000000))
        self.assertEqual((outcome.state, outcome.pre_io, outcome.reason),
            ('not_sent', True, 'bounded_native_backend_not_qualified'))

    def test_native_pending_is_not_observed_delivery(self):
        from codex_wake.bounded_native import BoundedNativeAdapter
        envelope = RuntimeSubmissionEnvelope('4d18e29e-9c05-45e7-a387-e50459dd3496', 1791504600000000)
        requests = []
        def request(endpoint, command, method, params, timeout):
            requests.append((method, params))
            inspection = dict(state='pending', queuedSubmission=dict(id='4d18e29e-9c05-45e7-a387-e50459dd3497',
                clientUserMessageId=envelope.client_user_message_id,
                expiresAtUnixMicros=1791504600000000,
                input=[dict(type='text', text='wake', text_elements=[])]), turnId=None, clockEvidence=None)
            return dict(queuedSubmission=inspection['queuedSubmission']) if method.endswith('/add') else dict(inspection=inspection)
        adapter = BoundedNativeAdapter(request=request)
        from codex_wake.runtime_delivery import RuntimeRecipient
        recipient = RuntimeRecipient('codex', 'thread', dict(endpoint='unix://', codex_cmd='/codex'))
        outcome = adapter.submit_bounded(recipient, 'wake', envelope)
        observed = adapter.reconcile_bounded(recipient, 'wake', envelope)
        self.assertEqual((outcome.state, observed.evidence, observed.reason),
            ('accepted', None, 'bounded_native_pending'))
        self.assertEqual(requests[0], ('thread/queue/bounded/add', dict(threadId='thread',
            input=[dict(type='text', text='wake', text_elements=[])],
            clientUserMessageId=envelope.client_user_message_id, expiresAtUnixMicros=1791504600000000)))
        self.assertEqual(requests[1], ('thread/queue/bounded/read', dict(threadId='thread',
            clientUserMessageId=envelope.client_user_message_id)))

    def test_original_expiry_preserves_microseconds_and_earlier_stop(self):
        from codex_wake.runtime_delivery import original_submission_expiry
        record = dict(scheduling_intent=dict(schedule=dict(kind='at', due_at='2026-10-09T00:00:00Z'),
            ttl_seconds=600.75, stop_at='2026-10-09T00:10:00.125Z'))
        self.assertEqual(original_submission_expiry(record), 1791504600125000)

    def test_durable_dispatch_never_downgrades_to_unbounded_cli(self):
        from datetime import UTC, datetime
        from pathlib import Path
        import tempfile
        from unittest.mock import patch
        from codex_wake.daemon import poll_once
        from codex_wake.records import all_records, build_record, write_record
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = dict(transport='native', thread_id='01a1227e-a041-7b72-9c36-18349e7dd22c', endpoint='unix://',
                codex_cmd='/codex', expires_at='2026-10-09T00:10:00Z')
            write_record(root, build_record(predicate=dict(type='not_before', due_at='2026-10-09T00:00:00Z'),
                prompt='wake', cwd=root, target=target))
            with patch('codex_wake.native_delivery.read_native_thread', return_value=dict(id='01a1227e-a041-7b72-9c36-18349e7dd22c', status=dict(type='idle'))), patch(
                'codex_wake.native_delivery.subprocess.run', side_effect=AssertionError('unbounded submission')):
                poll_once(root, datetime(2026, 10, 9, tzinfo=UTC))
            saved = all_records(root)[0].record
            self.assertEqual((saved['status'], saved['policy_outcome']['reason']),
                ('pending', 'bounded_native_backend_not_qualified'))
            self.assertNotIn('native_delivery', saved)

    def test_bounded_pending_keeps_persisted_identity_until_native_terminal(self):
        from datetime import UTC, datetime
        from pathlib import Path
        import tempfile
        from codex_wake.injector import dispatch_firing_record
        from codex_wake.records import all_records, build_record, write_record
        from codex_wake.runtime_delivery import RuntimeRecipient, RuntimeObservation, RuntimeSubmission, RuntimeReconciliation
        envelopes = []
        class Runtime:
            def resolve(self, target):
                return RuntimeRecipient('codex', target['thread_id'], target)
            def observe(self, recipient):
                return RuntimeObservation('ready', 'idle', {})
            def submit_bounded(self, recipient, prompt, envelope):
                envelopes.append(envelope)
                return RuntimeSubmission('accepted', receipt_id='4d18e29e-9c05-45e7-a387-e50459dd3497', evidence_kind='native_queue_acceptance')
            def reconcile_bounded(self, recipient, prompt, envelope):
                envelopes.append(envelope)
                return RuntimeReconciliation(None, 'bounded_native_pending' if len(envelopes) == 2 else 'bounded_native_expired')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = dict(transport='native', thread_id='01a1227e-a041-7b72-9c36-18349e7dd22c', endpoint='unix://', codex_cmd='/codex', expires_at='2026-10-09T00:10:00Z')
            record = build_record(predicate=dict(type='not_before', due_at='2026-10-09T00:00:00Z'), prompt='wake', cwd=root, target=target)
            record['status'] = 'firing'
            write_record(root, record)
            adapter = Runtime()
            for instant in (0, 10, 20):
                dispatch_firing_record(root, all_records(root)[0], now=datetime(2026, 10, 9, 0, 0, instant, tzinfo=UTC), runtime_adapter=adapter)
                if instant < 20:
                    self.assertEqual(all_records(root)[0].record['status'], 'firing')
                if instant == 0:
                    # Cancellation must not claim success while native pending
                    # work remains executable. Exact native deletion is not yet
                    # implemented, so the public command explicitly holds.
                    import contextlib
                    import io
                    import json
                    from codex_wake.cli import main
                    pending = all_records(root)[0]
                    before = pending.path.read_bytes()
                    output = io.StringIO()
                    with contextlib.redirect_stdout(output):
                        code = main(['--wake-root', str(root), 'cancel', pending.record['id'], '--json'])
                    result = json.loads(output.getvalue())['roots'][0]['results'][0]
                    self.assertEqual((code, result['state']), (5, 'held'))
                    self.assertIn('reconcile original effect before cancellation', result['reason'])
                    self.assertEqual(pending.path.read_bytes(), before)

            saved = all_records(root)[0].record
            self.assertEqual((saved['status'], saved['attempts']), ('expired', 1))
            self.assertEqual(envelopes, [envelopes[0]] * 3)
            self.assertEqual(envelopes[0].client_user_message_id, saved['native_delivery']['submission_id'])
            self.assertEqual(envelopes[0].expires_at_unix_micros, 1791504600000000)
            from unittest.mock import patch
            from codex_wake.wake_mode_runtime import registration_harness_readiness
            with patch('codex_wake.native_protocol.native_request', return_value=dict(thread=dict(id=target['thread_id'], status=dict(type='idle')))):
                readiness = registration_harness_readiness(root, dict(id='next-occurrence', target=target))
            self.assertEqual(readiness['state'], 'ready')


    def test_native_admission_requires_original_payload_and_qualified_clock(self):
        from copy import deepcopy
        from codex_wake.bounded_native import BoundedNativeAdapter
        from codex_wake.runtime_delivery import RuntimeRecipient
        envelope = RuntimeSubmissionEnvelope('4d18e29e-9c05-45e7-a387-e50459dd3496', 1791504600000000)
        authority = dict(contract_version=1, state='qualified', lower=1791504000, upper=1791504001,
            counter=dict(epoch='4d18e29e-9c05-45e7-a387-e50459dd3498', counter=123, frequency=1000, rate_ppm=10))
        response = dict(state='admitted', queuedSubmission=dict(id='4d18e29e-9c05-45e7-a387-e50459dd3497',
            clientUserMessageId=envelope.client_user_message_id, expiresAtUnixMicros=1791504600000000,
            input=[dict(type='text', text='wake', text_elements=[])]), turnId='turn-exact',
            clockEvidence=dict(lower=1791504000, upper=1791504001, authority=authority))
        recipient = RuntimeRecipient('codex', 'thread', dict(endpoint='unix://', codex_cmd='/codex'))
        for change in ('expiry', 'input', 'clock', 'late'):
            with self.subTest(change=change):
                malformed = deepcopy(response)
                if change == 'expiry': malformed['queuedSubmission']['expiresAtUnixMicros'] += 1
                if change == 'input': malformed['queuedSubmission']['input'][0]['text'] = 'changed'
                if change == 'clock': malformed['clockEvidence'] = None
                if change == 'late': malformed['clockEvidence']['upper'] = 1791504600
                adapter = BoundedNativeAdapter(request=lambda *args: dict(inspection=malformed))
                with self.assertRaises(ValueError):
                    adapter.reconcile_bounded(recipient, 'wake', envelope)
        adapter = BoundedNativeAdapter(request=lambda *args: dict(inspection=response))
        observed = adapter.reconcile_bounded(recipient, 'wake', envelope)
        self.assertEqual((observed.evidence['source'], observed.evidence['execution'], observed.evidence['turn_id']),
            ('bounded_native_admission', 'not_observed', 'turn-exact'))
