"""Public CLI migration boundaries: old readers must not reinterpret native state."""
import contextlib
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from codex_wake.cli import run
from codex_wake.records import all_records, WakeError, write_record

THREAD = '01a1227e-a041-7b72-9c36-18349e7dd22c'

class NativeMigrationTests(unittest.TestCase):
    def test_native_registration_uses_a_fail_closed_version_for_old_readers(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            root = Path(tmp)
            self.assertEqual(run(['--wake-root', tmp, 'native', 'after',
                                  '--codex-path', sys.executable, THREAD, '1h', '--', 'Continue']), 0)
            record = all_records(root)[0].record
            self.assertEqual(record['schema_version'], 4)
            self.assertEqual(record['target']['thread_id'], THREAD)

    def test_classic_registration_requires_explicit_tmux_compatibility(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(WakeError, 'legacy-tmux'):
                run(['--wake-root', tmp, 'after', '1h', '--', 'Continue'])
            self.assertEqual(all_records(Path(tmp)), [])

    def test_migration_preserves_uncertainty_and_original_without_submission(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            root = Path(tmp)
            run(['--wake-root', tmp, 'native', 'after', '--codex-path', sys.executable,
                 THREAD, '1h', '--', 'Keep original prompt'])
            found = all_records(root)[0]
            record = dict(found.record, schema_version=1, status='firing',
                          native_delivery={'state': 'uncertain', 'submission_id': 'retained-nonce'})
            found.path.unlink()
            original_path = write_record(root, record)
            original = original_path.read_bytes()
            run(['--wake-root', tmp, 'native', 'migrate', record['id']])
            self.assertEqual(original_path.read_bytes(), original)
            run(['--wake-root', tmp, 'native', 'migrate', record['id'], '--apply'])
            promoted = all_records(root)[0].record
            self.assertEqual(promoted, dict(record, schema_version=4))
            backup = root / 'migration' / (record['id'] + '.schema1.json')
            self.assertEqual(backup.read_bytes(), original)
            run(['--wake-root', tmp, 'native', 'migrate', record['id'], '--apply'])
            self.assertEqual(all_records(root)[0].record, promoted)

    def test_malformed_native_state_is_held_without_crashing_scheduler(self):
        import json
        from codex_wake.daemon import poll_once
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            root = Path(tmp)
            run(['--wake-root', tmp, 'native', 'after', '--codex-path', sys.executable,
                 THREAD, '1h', '--', 'Continue'])
            found = all_records(root)[0]
            base = json.loads(found.path.read_text())
            cases = [('target', 'expires_at', 'unreadable'),
                     ('predicate', 'due_at', 123), ('predicate', 'type', []),
                     (None, 'status', [])]
            for section, key, value in cases:
                with self.subTest(field=key):
                    record = json.loads(json.dumps(base))
                    (record[section] if section else record)[key] = value
                    # Deliberately damaged JSON still belongs in pending custody.
                    found.path.write_text(json.dumps(record))
                    original = found.path.read_bytes()
                    result = poll_once(root)
                    self.assertEqual(result.dispatched, 0)
                    self.assertEqual(result.failed, 0)
                    self.assertEqual(found.path.read_bytes(), original)

    def test_migration_refuses_legacy_transport_without_mutating_it(self):
        from codex_wake.records import build_record
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            root = Path(tmp)
            record = build_record(predicate={'type': 'file_exists', 'path': '/tmp/owned-marker'},
                                  prompt='Preserve legacy work', cwd=root,
                                  target={'transport': 'tmux', 'thread_id': THREAD})
            path = write_record(root, record)
            original = path.read_bytes()
            with self.assertRaisesRegex(WakeError, 'schema1 native'):
                run(['--wake-root', tmp, 'native', 'migrate', record['id'], '--apply'])
            self.assertEqual(path.read_bytes(), original)
            self.assertFalse((root / 'migration').exists())
