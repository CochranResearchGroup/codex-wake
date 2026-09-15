import unittest
from dataclasses import replace

from codex_wake.github_source_config import GitHubSourceRegistry
from codex_wake.github_polling import GitHubPollingAdapter
from tests.test_github_polling import config, FixtureClient


class GitHubSourceConfigTests(unittest.TestCase):
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
