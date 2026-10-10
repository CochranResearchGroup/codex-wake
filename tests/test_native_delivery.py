from datetime import UTC, datetime
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from codex_wake.cli import run
from codex_wake.daemon import poll_once
from codex_wake.records import all_records, build_record, write_record


class NativeDeliveryTests(unittest.TestCase):
    def test_file_wake_expires_even_if_file_never_appears(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.native_record(root, root / 'must-not-run')
            record = all_records(root)[0].record
            record['predicate'] = {'type': 'file_exists', 'path': str(root / 'missing')}
            from codex_wake.records import replace_record
            replace_record(root, all_records(root)[0], record)
            poll_once(root, datetime(2026, 10, 9, 0, 11, tzinfo=UTC))
            self.assertEqual(all_records(root)[0].record['status'], 'failed')

    def native_record(self, root, executable):
        record = build_record(predicate={'type': 'not_before', 'due_at': '2026-10-09T00:00:00Z'},
                              prompt='Execute the task', cwd=root,
                              target={'transport': 'native', 'thread_id': '01a1227e-a041-7b72-9c36-18349e7dd22c',
                                      'endpoint': 'unix://', 'codex_cmd': str(executable),
                                      'expires_at': '2026-10-09T00:10:00Z'})
        write_record(root, record)

    def test_busy_recipient_holds_until_expiry_without_submission(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.native_record(root, root / 'must-not-run')
            with patch('codex_wake.native_delivery.read_native_thread',
                       return_value={'id': '01a1227e-a041-7b72-9c36-18349e7dd22c', 'status': {'type': 'active'}}):
                result = poll_once(root, datetime(2026, 10, 9, tzinfo=UTC))
            self.assertEqual(result.requeued, 1)
            self.assertEqual(all_records(root)[0].record['status'], 'pending')
            result = poll_once(root, datetime(2026, 10, 9, 0, 11, tzinfo=UTC))
            self.assertEqual(result.failed, 1)
            self.assertNotIn('native_delivery', all_records(root)[0].record)

    def test_uncertain_acceptance_is_not_resubmitted_on_another_poll(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            executable = root / 'codex'
            counter = root / 'calls'
            executable.write_text('#!/usr/bin/env python3\nfrom pathlib import Path\n'
                                  f'with Path({str(counter)!r}).open("a") as f: f.write("call\\n")\n'
                                  'print("Unknown result")\n')
            executable.chmod(0o700)
            self.native_record(root, executable)
            with patch('codex_wake.native_delivery.read_native_thread',
                       return_value={'id': '01a1227e-a041-7b72-9c36-18349e7dd22c', 'status': {'type': 'idle'}}):
                poll_once(root, datetime(2026, 10, 9, tzinfo=UTC))
                poll_once(root, datetime(2026, 10, 9, 0, 1, tzinfo=UTC))
            self.assertEqual(counter.read_text(), 'call\n')
            self.assertEqual(all_records(root)[0].record['native_delivery']['state'], 'uncertain')

    def test_persisted_due_wake_uses_native_queue_and_records_acceptance(self):
        thread = '01a1227e-a041-7b72-9c36-18349e7dd22c'
        queue = '01a12280-80ef-7772-a00a-c68bd32ecbba'
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'wake'
            executable = Path(tmp) / 'codex'
            executable.write_text('#!/usr/bin/env python3\nimport sys\n'
                                  'assert sys.argv[1] == "queue"\n'
                                  f'print("Queued message {queue} for thread {thread}.")\n')
            executable.chmod(0o700)
            self.assertEqual(run(['--wake-root', str(root), 'native', 'at',
                                  '--codex-path', str(executable), thread,
                                  '2026-10-09T00:00:00Z', '--', 'Do the scheduled task']), 0)
            with patch('codex_wake.native_delivery.read_native_thread',
                       return_value={'id': thread, 'status': {'type': 'idle'}}), patch(
                       'codex_wake.injector.SubprocessTmuxRunner') as tmux:
                result = poll_once(root, datetime(2026, 10, 9, tzinfo=UTC))
            tmux.assert_not_called()
            self.assertEqual(result.submitted, 1)
            record = all_records(root)[0].record
            self.assertEqual(record['native_delivery']['queue_id'], queue)
            self.assertEqual(record['native_delivery']['execution'], 'not_observed')
            self.assertEqual(record['native_delivery']['acknowledgment'], 'not_observed')
