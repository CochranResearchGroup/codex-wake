from __future__ import annotations

import json
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from codex_wake.daemon import PollResult, poll_result_dict
from codex_wake.event_wake import EventWake
from codex_wake.filesystem_signals import FilesystemSignalAdapter
from codex_wake.github_polling import GitHubPollingAdapter, GitHubPollingConfig
from codex_wake.github_source_config import GitHubSourceStore
from codex_wake.monitor import read_monitor_health, write_monitor_health
from codex_wake.signal_records import ManagedReaderCapability, WakeRecordPublisher, signal_journal_path
from codex_wake.signal_store import SQLiteSignalModule
from codex_wake.signals import Resume, WakeIntent
from codex_wake.signal_support import (
    MAX_SUPPORT_BYTES,
    MAX_SUPPORT_RECORD_BYTES,
    MAX_SUPPORT_WAKES,
    export_signal_support,
    signal_readiness,
    github_source_readiness,
)


NOW = datetime(2026, 9, 14, 18, 0, tzinfo=UTC)


class SignalSupportTests(unittest.TestCase):
    def test_github_readiness_is_sanitized_and_separates_support_dimensions(self) -> None:
        config = type("Config", (), {"enabled": True, "hostname": "github.com"})()
        result = github_source_readiness(
            config,
            health={
                "credential_capability": "ready",
                "degraded": 0,
                "checkpoint_present": True,
                "replay_lag_seconds": 12,
                "code": "GITHUB_RATE_LIMITED",
                "token": "do-not-copy",
            },
            checkpoint=object(),
        )
        self.assertEqual(result["status"], "warning")
        self.assertEqual(result["configuration"]["status"], "ready")
        self.assertEqual(result["credential_capability"]["status"], "ready")
        self.assertNotIn("value_present", result["credential_capability"])
        self.assertEqual(result["checkpoint"]["status"], "ready")
        self.assertEqual(result["replay_lag"]["seconds"], 12)
        self.assertEqual(result["health_code"], "GITHUB_RATE_LIMITED")
        self.assertEqual(result["terminal_failure"]["code"], "")
        self.assertFalse(result["disabled"])
        self.assertNotIn("do-not-copy", json.dumps(result))

        configured = github_source_readiness(type("Config", (), {"enabled": True, "hostname": "github.com", "credential_ref": "named-ref"})())
        self.assertEqual(configured["status"], "warning")
        self.assertEqual(configured["health"]["status"], "warning")
        self.assertEqual(configured["credential_capability"]["status"], "configured_reference")
        self.assertNotIn("value_present", json.dumps(configured))

        auth = github_source_readiness(
            type("Config", (), {"enabled": True, "hostname": "github.com", "credential_ref": "named-ref"})(),
            health={"code": "GITHUB_AUTH_UNAVAILABLE"},
        )
        self.assertEqual(auth["status"], "blocked")
        self.assertEqual(auth["credential_capability"]["status"], "unavailable")
        self.assertEqual(auth["terminal_failure"]["status"], "not_present")

    def test_github_readiness_distinguishes_disabled_and_unsupported(self) -> None:
        disabled = github_source_readiness(type("Config", (), {"enabled": False, "hostname": "github.com"})())
        unsupported = github_source_readiness(type("Config", (), {"enabled": True, "hostname": "github.example"})())
        self.assertEqual(disabled["status"], "disabled")
        self.assertTrue(disabled["disabled"])
        self.assertEqual(unsupported["status"], "unsupported")
        self.assertTrue(unsupported["unsupported"])

    def test_export_rejects_runtime_destination_without_touching_journal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            wake_root = Path(tmp) / "wake"
            journal = signal_journal_path(wake_root)
            SQLiteSignalModule(journal)
            original = journal.read_bytes()
            before = signal_readiness(wake_root)

            with self.assertRaisesRegex(ValueError, "outside the wake root"):
                export_signal_support(wake_root, journal)
            with self.assertRaisesRegex(ValueError, "outside the wake root"):
                export_signal_support(wake_root, wake_root / "support.json")

            self.assertEqual(journal.read_bytes(), original)
            self.assertEqual(signal_readiness(wake_root), before)
            self.assertFalse((wake_root / "support.json").exists())

    def test_export_enforces_configuration_and_input_read_ceilings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            wake_root = base / "wake"
            adapter = FilesystemSignalAdapter(base, "ready.flag")
            runtime = SQLiteSignalModule(
                signal_journal_path(wake_root),
                record_publisher=WakeRecordPublisher(
                    wake_root,
                    ManagedReaderCapability(wake_root, "reader", 1, frozenset({1, 2}), True),
                ),
            )
            EventWake(runtime, adapters=(adapter,), clock=lambda: NOW, id_factory=lambda: "wake_small").register(
                WakeIntent(adapter.request("exists"), Resume("secret prompt", base, {"transport": "tmux"})),
                idempotency_key="secret-key",
            )
            archive = wake_root / "archive"
            archive.mkdir()
            oversized_secret = "raw-secret-provider-payload"
            (archive / "0000-oversized.json").write_text(
                oversized_secret + ("x" * MAX_SUPPORT_RECORD_BYTES), encoding="utf-8"
            )

            with self.assertRaisesRegex(ValueError, "max_wakes"):
                export_signal_support(wake_root, base / "too-many.json", max_wakes=MAX_SUPPORT_WAKES + 1)
            with self.assertRaisesRegex(ValueError, "max_bytes"):
                export_signal_support(wake_root, base / "too-large.json", max_bytes=MAX_SUPPORT_BYTES + 1)

            destination = base / "bounded.json"
            result = export_signal_support(wake_root, destination, max_wakes=1, max_bytes=16_384)
            payload = json.loads(destination.read_text(encoding="utf-8"))

            self.assertLessEqual(result.size_bytes, 16_384)
            self.assertEqual(payload["input"]["oversized_records"], 1)
            self.assertGreaterEqual(payload["omitted_wakes"], 1)
            self.assertNotIn(oversized_secret, destination.read_text(encoding="utf-8"))

    def test_export_stops_directory_enumeration_at_hard_ceiling(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            wake_root = base / "wake"
            pending = wake_root / "pending"
            pending.mkdir(parents=True)
            for index in range(5):
                (pending / f"{index}.txt").write_text("ignored", encoding="utf-8")

            destination = base / "bounded-scan.json"
            with patch("codex_wake.signal_support.MAX_SUPPORT_SCANNED_ENTRIES", 3):
                export_signal_support(wake_root, destination, max_bytes=16_384)

            input_receipt = json.loads(destination.read_text(encoding="utf-8"))["input"]
            self.assertEqual(input_receipt["scanned_entries"], 3)
            self.assertEqual(input_receipt["max_scanned_entries"], 3)
            self.assertTrue(input_receipt["scan_truncated"])
            self.assertFalse(input_receipt["record_count_complete"])

    def test_readiness_uses_exact_source_instance_health(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            wake_root = base / "wake"
            runtime = SQLiteSignalModule(
                signal_journal_path(wake_root),
                record_publisher=WakeRecordPublisher(
                    wake_root,
                    ManagedReaderCapability(wake_root, "reader", 1, frozenset({1, 2}), True),
                ),
            )
            for wake_id, instance, path in (
                ("wake_ready", "instance-ready", "ready.flag"),
                ("wake_blocked", "instance-blocked", "blocked.flag"),
            ):
                adapter = FilesystemSignalAdapter(base, path, source_instance=instance)
                EventWake(runtime, adapters=(adapter,), clock=lambda: NOW, id_factory=lambda value=wake_id: value).register(
                    WakeIntent(adapter.request("exists"), Resume("continue", base, {"transport": "tmux"})),
                    idempotency_key=wake_id,
                )
            poll = PollResult(
                signal_sources=(
                    {"source": "filesystem", "source_instance": "instance-ready", "scanned": 1, "observed": 0, "degraded": 0},
                    {"source": "filesystem", "source_instance": "instance-blocked", "scanned": 1, "observed": 0, "degraded": 1},
                )
            )
            state_dir = base / "health"
            write_monitor_health(
                wake_root=wake_root,
                source="test",
                mode="once",
                poll_result=poll_result_dict(poll),
                state_dir=state_dir,
                now=NOW,
            )
            health = read_monitor_health(wake_root, state_dir=state_dir)

            readiness = signal_readiness(wake_root, health=health)
            statuses = {item["source_instance"]: item["status"] for item in readiness["sources"]}

            self.assertEqual(statuses, {"instance-blocked": "blocked", "instance-ready": "ready"})

            aggregate = signal_readiness(
                wake_root,
                health={
                    "signal_sources": [
                        {"source": "filesystem", "scanned": 2, "observed": 0, "degraded": 0}
                    ]
                },
            )
            self.assertEqual(
                {item["status"] for item in aggregate["sources"]}, {"warning"}
            )
            self.assertEqual(
                {item["health_scope"] for item in aggregate["sources"]}, {"aggregate"}
            )

    def test_readiness_reports_source_health_separately_from_dispatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            wake_root = base / "wake"
            adapter = FilesystemSignalAdapter(base, "ready.flag")
            runtime = SQLiteSignalModule(
                signal_journal_path(wake_root),
                record_publisher=WakeRecordPublisher(
                    wake_root,
                    ManagedReaderCapability(wake_root, "reader", 1, frozenset({1, 2}), True),
                ),
            )
            EventWake(
                runtime,
                adapters=(adapter,),
                clock=lambda: NOW,
                id_factory=lambda: "wake_ready",
            ).register(
                WakeIntent(
                    adapter.request("exists"),
                    Resume("secret prompt", base, {"transport": "tmux", "token": "secret-token"}),
                ),
                idempotency_key="ready",
            )

            readiness = signal_readiness(wake_root)

            self.assertEqual(readiness["capability"]["status"], "ready")
            self.assertFalse(readiness["dispatch_readiness"]["included"])
            self.assertEqual(readiness["sources"][0]["source"], "filesystem")
            self.assertEqual(readiness["sources"][0]["status"], "warning")
            self.assertIn("not yet observed", readiness["sources"][0]["message"])

    def test_journal_only_github_projection_does_not_claim_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            wake_root = base / "wake"
            config = GitHubPollingConfig(
                source_instance="github-ci", repository="example/project", repository_id=42,
                workflow_id=7, refs=frozenset({"refs/heads/main"}),
                conclusions=frozenset({"success"}), credential_ref="fixture",
            )
            class FixtureClient:
                def list_runs(self, query):
                    from codex_wake.github_polling import RunPage
                    return RunPage((), None, None, None)
                def get_run_attempt(self, repository, run_id, run_attempt):
                    raise AssertionError("journal-only readiness must not contact provider")
            runtime = SQLiteSignalModule(
                signal_journal_path(wake_root),
                record_publisher=WakeRecordPublisher(
                    wake_root, ManagedReaderCapability(wake_root, "reader", 1, frozenset({1, 2}), True),
                ),
            )
            github = GitHubPollingAdapter(config, FixtureClient())
            EventWake(runtime, adapters=(github,), clock=lambda: NOW, id_factory=lambda: "github-wake").register(
                WakeIntent(github.request(ref="refs/heads/main", conclusions=("success",)), Resume("continue", base, {"transport": "tmux"})),
                idempotency_key="github-journal",
            )
            support = signal_readiness(wake_root)["sources"][0]["support"]
            self.assertEqual(support["status"], "configured_for_journal")
            self.assertFalse(support["disabled"])
            self.assertIsNone(support["configuration"]["enabled"])

    def test_configured_github_sources_are_reported_without_journal_and_health_is_sanitized(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "wake"
            config = GitHubPollingConfig(
                source_instance="github-ci", repository="example/project", repository_id=42,
                workflow_id=7, refs=frozenset({"refs/heads/main"}), conclusions=frozenset({"success"}),
                credential_ref="fixture", enabled=False, evidence_mode="positive_only",
            )
            store = GitHubSourceStore(root)
            store.configure(config)
            readiness = signal_readiness(root)
            self.assertEqual(len(readiness["sources"]), 1)
            support = readiness["sources"][0]["support"]
            self.assertEqual(support["configuration"]["status"], "disabled")
            self.assertTrue(support["disabled"])
            self.assertEqual(support["credential_ref"], "fixture")
            self.assertNotIn("credential_value", json.dumps(readiness))

    def test_invalid_github_health_is_an_actionable_block(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "wake"
            store = GitHubSourceStore(root)
            store.configure(
                GitHubPollingConfig(
                    source_instance="github-ci",
                    repository="example/project",
                    repository_id=42,
                    workflow_id=7,
                    refs=frozenset({"refs/heads/main"}),
                    conclusions=frozenset({"success"}),
                    credential_ref="fixture",
                    enabled=True,
                    evidence_mode="positive_only",
                )
            )
            store.health_path.write_text("not-json", encoding="utf-8")

            readiness = signal_readiness(root, now=NOW)

            self.assertEqual(readiness["status"], "blocked")
            support = readiness["sources"][0]["support"]
            self.assertEqual(support["terminal_failure"]["code"], "HEALTH_INVALID")
            self.assertEqual(support["diagnostic"], "GitHub source health is invalid")

    def test_support_export_is_deterministic_bounded_and_sanitized(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            wake_root = base / "wake"
            adapter = FilesystemSignalAdapter(base, "private.flag")
            runtime = SQLiteSignalModule(
                signal_journal_path(wake_root),
                record_publisher=WakeRecordPublisher(
                    wake_root,
                    ManagedReaderCapability(wake_root, "reader", 1, frozenset({1, 2}), True),
                ),
            )
            EventWake(
                runtime,
                adapters=(adapter,),
                clock=lambda: NOW,
                id_factory=lambda: "wake_export",
            ).register(
                WakeIntent(
                    adapter.request("created"),
                    Resume("private prompt", base, {"transport": "tmux", "token": "secret-token"}),
                ),
                idempotency_key="export-secret-key",
            )
            first = base / "first.json"
            second = base / "second.json"

            one = export_signal_support(wake_root, first, max_wakes=10, max_bytes=16_384)
            two = export_signal_support(wake_root, second, max_wakes=10, max_bytes=16_384)

            self.assertEqual(first.read_bytes(), second.read_bytes())
            self.assertLessEqual(one.size_bytes, 16_384)
            self.assertEqual(one.sha256, two.sha256)
            text = first.read_text(encoding="utf-8")
            self.assertNotIn("private prompt", text)
            self.assertNotIn("secret-token", text)
            self.assertNotIn("export-secret-key", text)
            payload = json.loads(text)
            self.assertEqual(payload["wakes"][0]["wake_id"], "wake_export")
            self.assertEqual(payload["wakes"][0]["source"], "filesystem")

    def test_readiness_explains_downgrade_and_corrupt_journal_repair(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            wake_root = Path(tmp) / "wake"
            journal = signal_journal_path(wake_root)
            SQLiteSignalModule(journal)

            downgrade = signal_readiness(wake_root, max_journal_schema=1)
            self.assertEqual(downgrade["journal"]["status"], "blocked")
            self.assertIn("downgrade", downgrade["journal"]["repair"])

            journal.write_bytes(b"not sqlite")
            corrupt = signal_readiness(wake_root)
            self.assertEqual(corrupt["journal"]["status"], "blocked")
            self.assertIn("restore", corrupt["journal"]["repair"])


if __name__ == "__main__":
    unittest.main()
