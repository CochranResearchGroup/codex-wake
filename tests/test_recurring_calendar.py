"""Explicit local clocks through public schedule registration and polling."""
import contextlib
from datetime import datetime
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from codex_wake.cli import run
from codex_wake.recurring_schedules import poll_schedules

THREAD = '11111111-1111-4111-8111-111111111111'


def cadence(**changes):
    value = dict(kind='clock', times=['02:30'], timezone='America/New_York',
                 start_at='2026-03-08T00:00:00Z', gap_policy='skip', fold_policy='first')
    value.update(changes)
    return value


def request(clock):
    return dict(idempotency_key='clock-check', thread_id=THREAD, prompt='Check status',
                session_mode='background', cadence=clock, end=dict(kind='count', count=3),
                missed=dict(policy='latest', max_lateness_seconds=172800),
                overlap=dict(policy='queue', limit=2), delivery_window_seconds=3600)


class ClockSchedules(unittest.TestCase):
    def cli(self, root, *args):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = run(['--wake-root', str(root), 'schedules', *args])
        self.assertEqual(code, 0)
        return json.loads(output.getvalue())

    def register(self, root, value):
        path = root / 'request.json'
        path.write_text(json.dumps(request(value)))
        return self.cli(root, 'register', '--request', str(path), '--codex-path', sys.executable)

    def test_spring_gap_skip_persists_the_next_real_local_time(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            registered = self.register(root, cadence())
            self.assertEqual(registered['next_due_at'], '2026-03-09T06:30:00Z')
            observed = datetime.fromisoformat('2026-03-09T06:30:00+00:00').timestamp()
            clock = dict(utc=dict(lower=observed, upper=observed, status='network', sources=['a', 'b']), counter=None)
            with patch('codex_wake.native_clock.snapshot', return_value=clock):
                poll_schedules(root, clock)
            saved = self.cli(root, 'show', registered['id'])
            self.assertEqual(saved['occurrences'][0]['due_at'], '2026-03-09T06:30:00Z')
            self.assertEqual(saved['occurrences'][0]['expires_at'], '2026-03-09T07:30:00Z')
            poll_schedules(root, clock)
            self.assertEqual(self.cli(root, 'show', registered['id'])['occurrences'], saved['occurrences'])

    def test_fall_fold_both_produces_two_distinct_original_occurrences(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            registered = self.register(root, cadence(times=['01:30'], start_at='2026-11-01T00:00:00Z', fold_policy='both'))
            self.assertEqual(registered['next_due_at'], '2026-11-01T05:30:00Z')
            observed = datetime.fromisoformat('2026-11-01T05:30:00+00:00').timestamp()
            clock = dict(utc=dict(lower=observed, upper=observed, status='network', sources=['a', 'b']), counter=None)
            with patch('codex_wake.native_clock.snapshot', return_value=clock):
                poll_schedules(root, clock)
            saved = self.cli(root, 'show', registered['id'])
            self.assertEqual(saved['next_due_at'], '2026-11-01T06:30:00Z')
            clock['utc'].update(lower=observed+3600, upper=observed+3600)
            poll_schedules(root, clock)
            saved = self.cli(root, 'show', registered['id'])
            self.assertEqual([item['due_at'] for item in saved['occurrences']],
                             ['2026-11-01T05:30:00Z', '2026-11-01T06:30:00Z'])
            self.assertNotEqual(saved['occurrences'][0]['id'], saved['occurrences'][1]['id'])

    def test_spring_gap_shift_forward_keeps_minutes_past_the_gap(self):
        with tempfile.TemporaryDirectory() as directory:
            registered = self.register(Path(directory), cadence(gap_policy='shift_forward'))
            self.assertEqual(registered['next_due_at'], '2026-03-08T07:30:00Z')

    def test_second_fold_and_missing_dst_choice_are_explicit(self):
        from codex_wake.records import WakeError
        with tempfile.TemporaryDirectory() as directory:
            registered = self.register(Path(directory), cadence(times=['01:30'], start_at='2026-11-01T00:00:00Z', fold_policy='second'))
            self.assertEqual(registered['next_due_at'], '2026-11-01T06:30:00Z')
        with tempfile.TemporaryDirectory() as directory:
            missing = cadence(); missing.pop('gap_policy')
            with self.assertRaisesRegex(WakeError, 'explicit_clock_fields_required'):
                self.register(Path(directory), missing)
