from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from datetime import timedelta
from pathlib import Path
from unittest.mock import Mock

from codex_wake.github_polling import GitHubPollingAdapter
from codex_wake.github_source_config import GitHubSourceStore
from codex_wake.github_source_family import github_source_family_registration
from codex_wake.signals import ArmId, ArmedSignal, Degraded, SourceAnchor, WakeId
from codex_wake.source_registry import ReconstructionCandidate, ReconstructionContext
from codex_wake.records import WakePath
from tests.test_github_polling import NOW, config


class NetworkGuardClient:
    """Provider-free client that records any accidental observation call."""

    def __init__(self) -> None:
        self.list_calls = 0
        self.attempt_calls = 0

    def list_runs(self, _query):
        self.list_calls += 1
        raise AssertionError("construction must not observe GitHub")

    def get_run_attempt(self, _repository, _run_id, _run_attempt):
        self.attempt_calls += 1
        raise AssertionError("construction must not observe GitHub")


class FixtureRunner:
    def __init__(self, adapters, *, armed_signals, health_store) -> None:
        self._adapters = dict(adapters)
        self._armed_signals = armed_signals
        self._health_store = health_store


def candidate(source, wake_id: str) -> ReconstructionCandidate:
    request = GitHubPollingAdapter(source, object()).request(
        ref="refs/heads/main", conclusions=("success",),
    )
    assert not isinstance(request, Degraded)
    armed = ArmedSignal(
        WakeId(wake_id),
        ArmId(f"arm_{wake_id}"),
        request,
        SourceAnchor(0, "github:fixture", {}, "source_replay"),
        NOW,
        None,
    )
    return ReconstructionCandidate(
        WakePath(Path("/unused") / f"{wake_id}.json", {}), armed,
    )


class GitHubSourceFamilyTests(unittest.TestCase):
    def test_registration_groups_sorted_instances_without_network_or_arm_reordering(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "wake"
            source_a = replace(config(evidence_mode="positive_only"), source_instance="github-a")
            source_b = replace(config(evidence_mode="positive_only"), source_instance="github-b")
            store = GitHubSourceStore(root)
            store.configure(source_b)
            store.configure(source_a)
            clients = {name: NetworkGuardClient() for name in ("github-a", "github-b")}
            constructed = []
            runner_factory = Mock(side_effect=FixtureRunner)

            registration = github_source_family_registration(
                runner_factory=runner_factory,
                client_factory=lambda selected: constructed.append(selected.source_instance) or clients[selected.source_instance],
            )
            self.assertEqual(registration.registration_id, "github-ci")
            self.assertEqual(registration.ownership, frozenset({("github", "workflow_run.completed")}))
            self.assertEqual(constructed, [])

            durable_order = (
                candidate(source_b, "wake_b_first"),
                candidate(source_a, "wake_a"),
                candidate(source_b, "wake_b_second"),
            )
            runners = registration.factory(
                ReconstructionContext(root, lambda _wake_id: None), durable_order,
            )

            self.assertEqual(constructed, ["github-a", "github-b"])
            self.assertEqual(len(runners), 1)
            runner = runners[0]
            runner_factory.assert_called_once()
            self.assertEqual(list(runner_factory.call_args.args[0]), ["github-a", "github-b"])
            self.assertEqual(
                [arm.wake_id for arm in runner_factory.call_args.kwargs["armed_signals"]],
                ["wake_a", "wake_b_first", "wake_b_second"],
            )
            self.assertEqual(runner_factory.call_args.kwargs["health_store"].wake_root, root)
            self.assertEqual(list(runner._adapters), ["github-a", "github-b"])
            self.assertEqual(
                [arm.wake_id for arm in runner._armed_signals],
                ["wake_a", "wake_b_first", "wake_b_second"],
            )
            self.assertEqual(
                [(client.list_calls, client.attempt_calls) for client in clients.values()],
                [(0, 0), (0, 0)],
            )

    def test_retry_health_is_restored_before_any_observation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "wake"
            source = config(evidence_mode="positive_only")
            store = GitHubSourceStore(root)
            store.configure(source)
            retry_at = NOW + timedelta(minutes=10)
            store.record_health(
                source.source_instance,
                Degraded(None, "GITHUB_RATE_LIMITED", retry_at),
                observed_at=NOW,
            )
            client = NetworkGuardClient()
            registration = github_source_family_registration(
                runner_factory=FixtureRunner,
                client_factory=lambda _selected: client,
            )

            (runner,) = registration.factory(
                ReconstructionContext(root, lambda _wake_id: None),
                (candidate(source, "wake_retry"),),
            )
            adapter = runner._adapters[source.source_instance]
            outcome = adapter.observe(
                runner._armed_signals[0].anchor,
                checkpoint=None,
                now=NOW + timedelta(seconds=1),
            )

            self.assertIsInstance(outcome, Degraded)
            self.assertEqual((outcome.code, outcome.retry_at), ("GITHUB_RATE_LIMITED", retry_at))
            self.assertEqual((client.list_calls, client.attempt_calls), (0, 0))

    def test_damaged_configuration_skips_family_without_constructing_client(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "wake"
            source = config(evidence_mode="positive_only")
            store = GitHubSourceStore(root)
            store.path.parent.mkdir(parents=True)
            store.path.write_text("{not-json", encoding="utf-8")
            constructed = []
            registration = github_source_family_registration(
                runner_factory=FixtureRunner,
                client_factory=lambda selected: constructed.append(selected.source_instance) or NetworkGuardClient(),
            )

            self.assertEqual(
                registration.factory(
                    ReconstructionContext(root, lambda _wake_id: None),
                    (candidate(source, "wake_damaged"),),
                ),
                (),
            )
            self.assertEqual(constructed, [])

    def test_disabled_and_failed_instances_are_silently_isolated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "wake"
            source_a = replace(config(evidence_mode="positive_only"), source_instance="github-a")
            source_b = replace(config(evidence_mode="positive_only"), source_instance="github-b")
            source_c = replace(config(evidence_mode="positive_only"), source_instance="github-c")
            store = GitHubSourceStore(root)
            store.configure(source_a)
            store.configure(source_b)
            store.configure(source_c)
            store.configure(replace(source_a, enabled=False))
            client = NetworkGuardClient()
            constructed = []

            def construct(selected):
                constructed.append(selected.source_instance)
                if selected.source_instance == "github-c":
                    return client
                raise ValueError("fixture construction failure")

            registration = github_source_family_registration(
                runner_factory=FixtureRunner,
                client_factory=construct,
            )
            (runner,) = registration.factory(
                ReconstructionContext(root, lambda _wake_id: None),
                (
                    candidate(source_a, "wake_disabled"),
                    candidate(source_b, "wake_failed"),
                    candidate(source_c, "wake_enabled"),
                ),
            )

            self.assertEqual(constructed, ["github-b", "github-c"])
            self.assertEqual(list(runner._adapters), ["github-c"])
            self.assertEqual([arm.wake_id for arm in runner._armed_signals], ["wake_enabled"])
            self.assertEqual((client.list_calls, client.attempt_calls), (0, 0))
