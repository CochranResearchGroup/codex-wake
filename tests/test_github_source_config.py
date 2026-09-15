import json
import tempfile
import unittest
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from codex_wake.github_source_config import GitHubSourceRegistry, GitHubSourceStore
from codex_wake.github_polling import GitHubPollingAdapter
from tests.test_github_polling import config, FixtureClient
from codex_wake.signals import Degraded


class GitHubSourceConfigTests(unittest.TestCase):
    def test_source_store_persists_only_valid_nonsecret_configuration(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "wake"
            source = config(
                evidence_mode="positive_only",
                credential_ref="CODEX_WAKE_GITHUB_TOKEN",
            )

            stored = GitHubSourceStore(root).configure(source)
            restarted = GitHubSourceStore(root)

            self.assertEqual(stored, source)
            self.assertEqual(restarted.registry().select("github-ci"), source)
            payload = json.loads((root / "github" / "sources.json").read_text())
            self.assertEqual(payload["schema_version"], 1)
            self.assertNotIn("fixture-secret", json.dumps(payload))
            self.assertEqual(payload["sources"][0]["credential_ref"], "CODEX_WAKE_GITHUB_TOKEN")

    def test_source_reconfiguration_is_idempotent_and_only_enabled_may_toggle(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "wake"
            store = GitHubSourceStore(root)
            source = config(evidence_mode="positive_only")
            store.configure(source)
            original = store.path.read_bytes()
            original_inode = store.path.stat().st_ino

            store.configure(source)

            self.assertEqual(store.path.read_bytes(), original)
            self.assertEqual(store.path.stat().st_ino, original_inode)
            store.configure(replace(source, enabled=False))
            disabled = store.sources()[0]
            self.assertFalse(disabled.enabled)
            self.assertEqual(replace(disabled, enabled=True), source)

    def test_material_reconfiguration_requires_a_new_instance_and_preserves_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "wake"
            store = GitHubSourceStore(root)
            source = config(evidence_mode="positive_only")
            store.configure(source)
            for changes in (
                {"repository": "example/other"},
                {"workflow_id": source.workflow_id + 1},
                {"refs": frozenset({"refs/heads/release"})},
                {"credential_ref": "different-reader"},
                {"max_requests": source.max_requests + 1},
            ):
                with self.subTest(changes=changes):
                    before = store.path.read_bytes()
                    with self.assertRaisesRegex(ValueError, "new source_instance"):
                        store.configure(replace(source, **changes))
                    self.assertEqual(store.path.read_bytes(), before)
                    self.assertEqual(store.registry().select(source.source_instance), source)

    def test_source_store_recovers_an_absolute_retry_deadline_after_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "wake"
            retry_at = datetime(2026, 9, 15, 3, 45, tzinfo=UTC)
            store = GitHubSourceStore(root)

            store.record_health(
                "github-ci",
                Degraded(None, "GITHUB_RATE_LIMITED", retry_at),
                observed_at=datetime(2026, 9, 15, 3, 40, tzinfo=UTC),
            )

            self.assertEqual(
                GitHubSourceStore(root).retry_failure("github-ci"),
                Degraded(None, "GITHUB_RATE_LIMITED", retry_at),
            )
            health = GitHubSourceStore(root).source_health("github-ci")
            self.assertEqual(health.code, "GITHUB_RATE_LIMITED")
            self.assertEqual(health.retry_at, retry_at)
            self.assertEqual(
                health.observed_at,
                datetime(2026, 9, 15, 3, 40, tzinfo=UTC),
            )

    def test_source_store_rejects_ambiguous_or_redirected_configuration(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "wake"
            store = GitHubSourceStore(root)
            store.configure(config(evidence_mode="positive_only"))
            original = store.path.read_text()
            store.path.write_text(original.replace('"enabled":true', '"enabled":false,"enabled":true'))
            with self.assertRaisesRegex(ValueError, "configuration is invalid"):
                store.sources()

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "wake"
            outside = Path(tmp) / "outside.json"
            outside.write_text('{"schema_version":1,"sources":[]}')
            path = root / "github" / "sources.json"
            path.parent.mkdir(parents=True)
            path.symlink_to(outside)
            with self.assertRaisesRegex(ValueError, "configuration is invalid"):
                GitHubSourceStore(root).sources()

    def test_disabled_or_non_branch_production_sources_cannot_arm_directly(self):
        for changes in ({"enabled": False}, {"refs": frozenset({"refs/tags/main"})}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                GitHubPollingAdapter(config(evidence_mode="positive_only", **changes), FixtureClient())

    def test_registry_selects_only_explicit_enabled_production_sources(self):
        selected = config(evidence_mode="positive_only")
        registry = GitHubSourceRegistry((selected, replace(selected, source_instance="disabled", enabled=False)))
        self.assertEqual(registry.select("github-ci"), selected)
        for name in ("disabled", "unknown", "https://example.com", []):
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, "GitHub source is not enabled"):
                registry.select(name)
        with self.assertRaises(ValueError):
            GitHubSourceRegistry((selected, selected))
        with self.assertRaises(ValueError):
            GitHubSourceRegistry((config(),))
