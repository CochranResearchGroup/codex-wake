"""Keep modern lifecycle acceptance strict about append-only native history."""

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


_SPEC = importlib.util.spec_from_file_location(
    "native_qualification",
    Path(__file__).parents[1] / "scripts/scoped_refresh_native_qualification.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)


class ModernHistoryTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.fixture = object.__new__(_MODULE.ModernManagedFixture)
        self.fixture.root = Path(self.directory.name)
        self.before = b'{"type":"session_meta","payload":{"id":"owned"}}\n'

    def event(self, kind="thread_settings_applied", owner="owned"):
        return (
            json.dumps(
                {
                    "type": "event_msg",
                    "payload": {
                        "type": kind,
                        "thread_id": owner,
                        "thread_settings": {
                            "cwd": str(self.fixture.root / "workspace"),
                            "model_provider_id": "owned_no_provider",
                        },
                    },
                }
            ).encode()
            + b"\n"
        )

    def test_accepts_settings_checkpoint_without_changing_original_bytes(self):
        result = self.fixture.preserve_prefix(
            self.before, self.before + self.event(), "owned"
        )
        self.assertEqual(
            result, {"original_bytes_preserved": True, "appended_settings_events": 1}
        )

    def test_rejects_rewrite_truncation_model_work_and_foreign_settings(self):
        for after in [
            self.before[:-1],
            self.before.replace(b"owned", b"other"),
            self.before + self.event("task_started"),
            self.before + self.event("token_count"),
            self.before + self.event("unknown"),
            self.before + self.event(owner="other"),
        ]:
            with self.subTest(after=after), self.assertRaises(RuntimeError):
                self.fixture.preserve_prefix(self.before, after, "owned")

    def test_startup_counts_include_only_the_modern_baseline(self):
        self.assertEqual(
            _MODULE.expected_toy_startup_versions(False), ["v1", "v1", "v2"]
        )
        self.assertEqual(
            _MODULE.expected_toy_startup_versions(True), ["v1", "v1", "v1", "v2"]
        )
