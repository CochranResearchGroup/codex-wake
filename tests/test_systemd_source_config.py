from __future__ import annotations

import json
import os
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from codex_wake.systemd_source_config import (
    SystemdSourceConfig,
    SystemdSourceRegistry,
    SystemdSourceStore,
)


def config(**changes: object) -> SystemdSourceConfig:
    return SystemdSourceConfig(**{
        "source_instance": "build-state",
        "unit": "build.service",
        "owner_uid": 1000,
        "target_states": frozenset({"active", "failed"}),
        **changes,
    })


class SystemdSourceConfigTests(unittest.TestCase):
    def test_store_persists_only_bounded_nonsecret_configuration(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "wake"
            source = config()

            self.assertEqual(SystemdSourceStore(root).configure(source), source)
            self.assertEqual(SystemdSourceStore(root).registry().select("build-state"), source)
            payload = json.loads((root / "systemd" / "sources.json").read_text())

            self.assertEqual(payload["schema_version"], 1)
            self.assertEqual(payload["sources"][0]["unit"], "build.service")
            self.assertNotIn("command", json.dumps(payload))

    def test_material_reconfiguration_requires_a_new_source_instance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = SystemdSourceStore(Path(tmp))
            source = config()
            store.configure(source)
            before = store.path.read_bytes()
            for changed in (
                {"unit": "other.service"},
                {"owner_uid": 1001},
                {"target_states": frozenset({"inactive"})},
                {"poll_timeout_seconds": 9},
            ):
                with self.subTest(changed=changed), self.assertRaisesRegex(ValueError, "new source_instance"):
                    store.configure(replace(source, **changed))
                self.assertEqual(store.path.read_bytes(), before)

    def test_registry_and_decoder_fail_closed_on_widening_or_ambiguous_data(self) -> None:
        with self.assertRaises(ValueError):
            SystemdSourceRegistry((config(unit="*.service"),))
        with self.assertRaises(ValueError):
            SystemdSourceRegistry((config(target_states=frozenset({"activating"})),))
        with tempfile.TemporaryDirectory() as tmp:
            store = SystemdSourceStore(Path(tmp))
            store.configure(config())
            store.path.write_text(store.path.read_text().replace('"enabled":true', '"enabled":false,"enabled":true'))
            with self.assertRaisesRegex(ValueError, "configuration is invalid"):
                store.sources()

    def test_source_read_rejects_foreign_owner_and_non_owner_only_modes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = SystemdSourceStore(Path(tmp))
            store.configure(config())
            with patch("codex_wake.systemd_source_config.os.geteuid", return_value=os.geteuid() + 1):
                with self.assertRaisesRegex(ValueError, "configuration is invalid"):
                    store.sources()
            os.chmod(store.path, 0o640)
            with self.assertRaisesRegex(ValueError, "configuration is invalid"):
                store.sources()
