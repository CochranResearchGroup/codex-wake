from __future__ import annotations

import tempfile
import json
import subprocess
import sqlite3
import sys
import unittest
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

from codex_wake.event_wake import EventWake
from codex_wake.github_polling import (
    GitHubPollingAdapter, GitHubPollingConfig, GitHubReadError, PollBatch, RunPage, WorkflowRun,
)
from codex_wake.signals import (
    ArmContext, ArmedSignal, Degraded, Eq, EvaluationLimits, In, InMemorySignalModule,
    Ingested, Invalid, Matched, NotReady, Registration, ScriptedSourceAdapter, SignalRequest, SourceAnchor, WakeId,
)
from tests.test_signal_store import make_module
from tests.test_signals import make_intent


NOW = datetime(2026, 9, 14, 14, 0, tzinfo=UTC)


def config(**changes):
    return GitHubPollingConfig(**{
        "source_instance": "github-ci", "repository": "example/project",
        "repository_id": 42, "workflow_id": 7,
        "refs": frozenset({"refs/heads/main"}),
        "conclusions": frozenset({"success", "failure", "cancelled", "timed_out"}),
        "credential_ref": "ci-reader", **changes,
    })


def run(**changes):
    return WorkflowRun(**{
        "repository": "example/project", "repository_id": 42, "workflow_id": 7,
        "run_id": 101, "run_attempt": 1, "ref": "refs/heads/main",
        "head_sha": "a" * 40, "status": "completed", "conclusion": "success",
        "completed_at": NOW + timedelta(seconds=1), **changes,
    })


class FixtureClient:
    def __init__(self, runs=(), *, pages=None, verified=None):
        self.runs = tuple(runs)
        self.pages = pages
        self.verified = verified or {}
        self.requests = []

    def list_runs(self, query):
        self.requests.append(query)
        if self.pages is not None:
            value = self.pages[query.page - 1]
            if isinstance(value, Exception):
                raise value
            return value
        return RunPage(self.runs, None, NOW - timedelta(days=1), query.until)

    def get_run_attempt(self, repository, run_id, run_attempt):
        value = self.verified.get((run_id, run_attempt))
        if isinstance(value, Exception):
            raise value
        if value is not None:
            return value
        return next(item for item in self.runs if (item.run_id, item.run_attempt) == (run_id, run_attempt))


class GitHubPollingTests(unittest.TestCase):
    def test_hostile_request_and_clause_subclasses_are_rejected_without_equality_dispatch(self):
        class HostileRequest(SignalRequest):
            def __eq__(self, other):
                raise AssertionError("request equality must not run")
        class HostileEq(Eq):
            def __eq__(self, other):
                raise AssertionError("clause equality must not run")
        class HostileIn(In):
            def __eq__(self, other):
                raise AssertionError("clause equality must not run")
        client = FixtureClient()
        adapter = GitHubPollingAdapter(config(), client)
        spec = adapter.request(ref="refs/heads/main", conclusions=("success",))
        hostile = HostileRequest(spec.contract_version, spec.source, spec.source_instance, spec.semantics,
                                 spec.kind, spec.subject, spec.condition, spec.where, spec.verification)
        workflow, ref, conclusion = spec.where
        variants = (
            hostile,
            replace(spec, where=(HostileEq(workflow.field, workflow.value), ref, conclusion)),
            replace(spec, where=(workflow, HostileEq(ref.field, ref.value), conclusion)),
            replace(spec, where=(workflow, ref, HostileIn(conclusion.field, conclusion.values))),
        )
        for number, invalid in enumerate(variants):
            with self.subTest(variant=number):
                self.assertIsInstance(adapter.establish_anchor(invalid, NOW), Invalid)
        self.assertEqual(client.requests, [])

    def test_damaged_durable_anchor_and_missing_journal_do_not_replay_authority(self):
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "signals.sqlite3"
            module = make_module(database)
            adapter = GitHubPollingAdapter(config(), FixtureClient([run()]))
            spec = adapter.request(ref="refs/heads/main", conclusions=("success",))
            armed = module.arm(WakeId("wake_damage"), spec, ArmContext("damage", "damage", NOW, None, make_intent().resume, adapter))
            batch = adapter.observe(armed.anchor, checkpoint=None, now=NOW + timedelta(seconds=2))
            module.ingest(batch.observations, batch.commit)
            self.assertIsInstance(module.evaluate(armed.wake_id, armed, NOW + timedelta(seconds=2), EvaluationLimits(20)), Matched)
            with sqlite3.connect(database) as connection:
                connection.execute("UPDATE arms SET baseline_json = '{}' WHERE wake_id = 'wake_damage'")
            result = module.evaluate(armed.wake_id, armed, NOW + timedelta(seconds=2), EvaluationLimits(20))
            self.assertIsInstance(result, Invalid)
            self.assertEqual(result.code, "OCCURRENCE_ANCHOR_INVALID")
            database.rename(database.with_suffix(".saved"))
            self.assertIsInstance(module.source_checkpoint("github", "github-ci"), Degraded)
            self.assertFalse(database.exists())

    def test_ordering_contract_requires_occurrence_integer_field_and_integer_anchor(self):
        for engine in ("memory", "sqlite"):
            with self.subTest(engine=engine), tempfile.TemporaryDirectory() as tmp:
                module = InMemorySignalModule() if engine == "memory" else make_module(Path(tmp) / "signals.sqlite3")
                adapter = GitHubPollingAdapter(config(), FixtureClient())
                spec = adapter.request(ref="refs/heads/main", conclusions=("success",))
                anchor = adapter.establish_anchor(spec, NOW)
                variants = (
                    (replace(adapter.contract(), occurrence_order_attribute="head_sha"), spec, anchor),
                    (replace(adapter.contract(), occurrence_order_attribute="missing"), spec, anchor),
                    (adapter.contract(), replace(spec, semantics="state", condition="holds"), anchor),
                    (adapter.contract(), spec, replace(anchor, baseline={})),
                    (adapter.contract(), spec, replace(anchor, baseline={"completed_at_us": True})),
                )
                for number, (contract, request, selected_anchor) in enumerate(variants):
                    scripted = ScriptedSourceAdapter(contract, anchor=selected_anchor)
                    result = module.arm(WakeId(f"wake_invalid_{number}"), request,
                                        ArmContext(str(number), str(number), NOW, None, make_intent().resume, scripted))
                    self.assertIsInstance(result, Invalid)

    def test_missing_observation_order_evidence_fails_closed_in_both_engines(self):
        for engine in ("memory", "sqlite"):
            with self.subTest(engine=engine), tempfile.TemporaryDirectory() as tmp:
                module = InMemorySignalModule() if engine == "memory" else make_module(Path(tmp) / "signals.sqlite3")
                adapter = GitHubPollingAdapter(config(), FixtureClient([run()]))
                spec = adapter.request(ref="refs/heads/main", conclusions=("success",))
                armed = module.arm(WakeId("wake_missing"), spec, ArmContext("missing", "missing", NOW, None, make_intent().resume, adapter))
                batch = adapter.observe(armed.anchor, checkpoint=None, now=NOW + timedelta(seconds=2))
                attributes = dict(batch.observations[0].attributes)
                del attributes["completed_at_us"]
                observation = replace(batch.observations[0], attributes=attributes)
                self.assertIsInstance(module.ingest((observation,), batch.commit), Ingested)
                invalid = module.evaluate(armed.wake_id, armed, NOW + timedelta(seconds=2), EvaluationLimits(20))
                self.assertIsInstance(invalid, Invalid)
                self.assertEqual(invalid.code, "OCCURRENCE_ORDER_INVALID")
                self.assertEqual(module.source_checkpoint("github", "github-ci"), batch.commit)

    def test_shared_engines_reject_pre_second_arm_receipt_but_accept_later_lower_run_id(self):
        for engine in ("memory", "sqlite"):
            with self.subTest(engine=engine), tempfile.TemporaryDirectory() as tmp:
                module = InMemorySignalModule() if engine == "memory" else make_module(Path(tmp) / "signals.sqlite3")
                adapter = GitHubPollingAdapter(config(), FixtureClient([run()]))
                spec = adapter.request(ref="refs/heads/main", conclusions=("success",))
                arms = []
                for name, at in (("wake_a", NOW), ("wake_b", NOW + timedelta(seconds=2))):
                    armed = module.arm(WakeId(name), spec, ArmContext(name, name, at, None, make_intent().resume, adapter))
                    self.assertIsInstance(armed, ArmedSignal)
                    arms.append(armed)
                batch = adapter.observe(arms[0].anchor, checkpoint=None, now=NOW + timedelta(seconds=3))
                self.assertIsInstance(module.ingest(batch.observations, batch.commit), Ingested)
                self.assertIsInstance(module.evaluate(arms[0].wake_id, arms[0], NOW + timedelta(seconds=3), EvaluationLimits(20)), Matched)
                self.assertIsInstance(module.evaluate(arms[1].wake_id, arms[1], NOW + timedelta(seconds=3), EvaluationLimits(20)), NotReady)
                later = GitHubPollingAdapter(config(), FixtureClient([run(run_id=100, completed_at=NOW + timedelta(seconds=4))]))
                batch = later.observe(arms[0].anchor, checkpoint=batch.commit, now=NOW + timedelta(seconds=5))
                self.assertIsInstance(module.ingest(batch.observations, batch.commit), Ingested)
                matched = module.evaluate(arms[1].wake_id, arms[1], NOW + timedelta(seconds=5), EvaluationLimits(20))
                self.assertIsInstance(matched, Matched)
                self.assertEqual(matched.receipt.attributes["run_id"], 100)

    def test_completion_order_cutoffs_do_not_use_run_creation_order(self):
        values = (run(run_id=101, completed_at=NOW + timedelta(seconds=1)),
                  run(run_id=100, completed_at=NOW + timedelta(seconds=4)))
        adapter = GitHubPollingAdapter(config(), FixtureClient(values))
        spec = adapter.request(ref="refs/heads/main", conclusions=("success",))
        older = adapter.establish_anchor(spec, NOW)
        newer = adapter.establish_anchor(spec, NOW + timedelta(seconds=2))
        for anchor, expected in ((older, [101, 100]), (newer, [100])):
            batch = adapter.observe(anchor, checkpoint=None, now=NOW + timedelta(seconds=5))
            self.assertEqual([item.attributes["run_id"] for item in batch.observations], expected)
            self.assertTrue(all(item.attributes["completed_at_us"] > anchor.baseline["completed_at_us"] for item in batch.observations))

    def test_restart_reuses_checkpoint_overlap_identity_and_restored_retry_deadline(self):
        client = FixtureClient([run()])
        adapter = GitHubPollingAdapter(config(), client)
        anchor = adapter.establish_anchor(adapter.request(ref="refs/heads/main", conclusions=("success",)), NOW)
        first = adapter.observe(anchor, checkpoint=None, now=NOW + timedelta(seconds=2))
        restarted = GitHubPollingAdapter(config(), FixtureClient([run(), run(run_attempt=2, completed_at=NOW + timedelta(seconds=3))]))
        second = restarted.observe(anchor, checkpoint=first.commit, now=NOW + timedelta(seconds=4))
        self.assertEqual(second.observations[0], first.observations[0])
        self.assertNotEqual(second.observations[0].occurrence_value, second.observations[1].occurrence_value)
        failure = Degraded(None, "GITHUB_RATE_LIMITED", NOW + timedelta(minutes=30))
        no_calls = FixtureClient()
        after_crash = GitHubPollingAdapter(config(), no_calls, previous_failure=failure)
        self.assertEqual(after_crash.observe(anchor, checkpoint=first.commit, now=NOW + timedelta(seconds=4)), failure)
        self.assertEqual(no_calls.requests, [])

    def test_poll_runner_advances_only_with_a_successful_atomic_ingest(self):
        fail = [True]
        def fault(label):
            if label == "before_ingest_commit" and fail[0]:
                raise OSError("private-store-detail")
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "signals.sqlite3"
            module = make_module(database, checkpoint=fault)
            adapter = GitHubPollingAdapter(config(), FixtureClient([run()]))
            spec = adapter.request(ref="refs/heads/main", conclusions=("success",))
            armed = module.arm(WakeId("wake_poll"), spec, ArmContext("poll", "poll", NOW, None, make_intent().resume, adapter))
            self.assertIsNone(module.source_checkpoint("github", "github-ci"))
            self.assertEqual(adapter.poll_into(module, armed.anchor, checkpoints=module, now=NOW + timedelta(seconds=2)).code, "STORE_UNAVAILABLE")
            self.assertIsNone(module.source_checkpoint("github", "github-ci"))
            fail[0] = False
            self.assertIsInstance(adapter.poll_into(module, armed.anchor, checkpoints=module, now=NOW + timedelta(seconds=2)), Ingested)
            committed = module.source_checkpoint("github", "github-ci")
            self.assertEqual(committed.observed_through, NOW + timedelta(seconds=2))
            self.assertEqual(make_module(database).source_checkpoint("github", "github-ci"), committed)
            self.assertIsNone(module.source_checkpoint("github", "unknown"))

    def test_stale_outside_allowlist_and_nonterminal_runs_never_become_receipts(self):
        values = [run(run_id=number + 1, **changes) for number, changes in enumerate((
            {"completed_at": NOW}, {"completed_at": NOW - timedelta(seconds=1)},
            {"completed_at": NOW + timedelta(hours=1)}, {"repository": "other/repository"},
            {"repository_id": 43}, {"workflow_id": 8}, {"ref": "refs/heads/other"},
            {"conclusion": "neutral"}, {"status": "in_progress", "conclusion": None, "completed_at": None},
        ))]
        adapter = GitHubPollingAdapter(config(), FixtureClient(values))
        anchor = adapter.establish_anchor(adapter.request(ref="refs/heads/main", conclusions=("success",)), NOW)
        self.assertEqual(adapter.observe(anchor, checkpoint=None, now=NOW + timedelta(seconds=2)).observations, ())

    def test_pagination_commits_only_after_complete_coverage_and_holds_on_late_failure(self):
        value = run()
        end = NOW + timedelta(seconds=2)
        first_page = RunPage((value,), 2, None, None)
        final_page = RunPage((value,), None, NOW, end)
        for terminal, code in ((GitHubReadError("auth"), "GITHUB_AUTH_UNAVAILABLE"),
                               (replace(final_page, covered_from=NOW + timedelta(seconds=1)), "GITHUB_HISTORY_GAP"),
                               (replace(final_page, next_page=2), "GITHUB_PAGINATION_INVALID"),
                               (replace(final_page, next_page=3), "GITHUB_POLL_BUDGET_EXHAUSTED")):
            with self.subTest(code=code):
                client = FixtureClient([value], pages=[first_page, terminal])
                adapter = GitHubPollingAdapter(config(max_pages=2), client)
                anchor = adapter.establish_anchor(adapter.request(ref="refs/heads/main", conclusions=("success",)), NOW)
                result = adapter.observe(anchor, checkpoint=None, now=end)
                self.assertIsInstance(result, Degraded)
                self.assertEqual(result.code, code)
        client = FixtureClient([value], pages=[first_page, final_page])
        adapter = GitHubPollingAdapter(config(), client)
        anchor = adapter.establish_anchor(adapter.request(ref="refs/heads/main", conclusions=("success",)), NOW)
        result = adapter.observe(anchor, checkpoint=None, now=end)
        self.assertIsInstance(result, PollBatch)
        self.assertEqual(len(result.observations), 1)
        self.assertEqual([query.page for query in client.requests], [1, 2])

    def test_invalid_checkpoint_and_clock_regression_never_contact_provider(self):
        adapter = GitHubPollingAdapter(config(), FixtureClient())
        anchor = adapter.establish_anchor(adapter.request(ref="refs/heads/main", conclusions=("success",)), NOW)
        first = adapter.observe(anchor, checkpoint=None, now=NOW + timedelta(seconds=2))
        for checkpoint in (
            replace(first.commit, checkpoint="not-json"), replace(first.commit, checkpoint_order=1),
            replace(first.commit, source_instance="other"),
            replace(first.commit, observed_through=NOW),
        ):
            with self.subTest(checkpoint=checkpoint):
                client = FixtureClient()
                restarted = GitHubPollingAdapter(config(), client)
                result = restarted.observe(anchor, checkpoint=checkpoint, now=NOW + timedelta(seconds=3))
                self.assertIsInstance(result, Invalid)
                self.assertEqual(result.code, "GITHUB_CHECKPOINT_INVALID")
                self.assertEqual(client.requests, [])
        client = FixtureClient()
        restarted = GitHubPollingAdapter(config(), client)
        result = restarted.observe(anchor, checkpoint=first.commit, now=NOW + timedelta(seconds=1))
        self.assertIsInstance(result, Invalid)
        self.assertEqual(client.requests, [])

    def test_anchor_tampering_and_malformed_caller_values_fail_closed(self):
        client = FixtureClient()
        adapter = GitHubPollingAdapter(config(), client)
        spec = adapter.request(ref="refs/heads/main", conclusions=("success",))
        anchor = adapter.establish_anchor(spec, NOW)
        for changed in (replace(anchor, baseline={"completed_at_us": 0}),
                        replace(anchor, recovery="local_journal"),
                        replace(anchor, local_after_sequence=-1)):
            result = adapter.observe(changed, checkpoint=None, now=NOW + timedelta(seconds=2))
            self.assertIsInstance(result, Invalid)
            self.assertEqual(result.code, "GITHUB_ANCHOR_INVALID")
        self.assertIsInstance(adapter.request(ref=[], conclusions=("success",)), Invalid)
        self.assertIsInstance(adapter.request(ref="refs/heads/main", conclusions=([],)), Invalid)
        self.assertEqual(client.requests, [])

    def test_auth_rate_and_verification_errors_preserve_checkpoint_and_suppress_early_retries(self):
        for kind, code in (("auth", "GITHUB_AUTH_UNAVAILABLE"), ("rate_limit", "GITHUB_RATE_LIMITED"),
                           ("unavailable", "GITHUB_SOURCE_UNAVAILABLE")):
            with self.subTest(kind=kind):
                retry_at = NOW + timedelta(minutes=10)
                client = FixtureClient(pages=[GitHubReadError(kind, retry_at=retry_at)])
                adapter = GitHubPollingAdapter(config(), client)
                anchor = adapter.establish_anchor(adapter.request(ref="refs/heads/main", conclusions=("success",)), NOW)
                result = adapter.observe(anchor, checkpoint=None, now=NOW + timedelta(seconds=2))
                self.assertEqual(result.code, code)
                self.assertEqual(result.retry_at, retry_at)
                again = adapter.observe(anchor, checkpoint=None, now=NOW + timedelta(seconds=3))
                self.assertEqual(again, result)
                self.assertEqual(len(client.requests), 1)
        client = FixtureClient([run()], verified={(101, 1): run(head_sha="b" * 40)})
        adapter = GitHubPollingAdapter(config(), client)
        anchor = adapter.establish_anchor(adapter.request(ref="refs/heads/main", conclusions=("success",)), NOW)
        self.assertEqual(adapter.observe(anchor, checkpoint=None, now=NOW + timedelta(seconds=2)).code, "GITHUB_VERIFICATION_FAILED")

    def test_terminal_results_are_verified_and_duplicates_are_stable_across_poll_times(self):
        for conclusion in ("success", "failure", "cancelled", "timed_out"):
            with self.subTest(conclusion=conclusion):
                value = run(conclusion=conclusion)
                adapter = GitHubPollingAdapter(config(), FixtureClient([value, value]))
                spec = adapter.request(ref="refs/heads/main", conclusions=(conclusion,))
                anchor = adapter.establish_anchor(spec, NOW)
                first = adapter.observe(anchor, checkpoint=None, now=NOW + timedelta(seconds=2))
                second = adapter.observe(anchor, checkpoint=first.commit, now=NOW + timedelta(seconds=3))
                self.assertEqual(len(first.observations), 1)
                self.assertEqual(first.observations, second.observations)
                self.assertEqual(first.observations[0].attributes["conclusion"], conclusion)

    def test_untrusted_terminal_fields_are_rejected_before_normalized_evidence(self):
        for changes in ({"run_id": True}, {"run_attempt": 0}, {"head_sha": "secret=" + "x" * 10000},
                        {"completed_at": NOW.replace(tzinfo=None)}, {"run_id": -1}):
            with self.subTest(changes=changes):
                adapter = GitHubPollingAdapter(config(), FixtureClient([run(**changes)]))
                anchor = adapter.establish_anchor(adapter.request(ref="refs/heads/main", conclusions=("success",)), NOW)
                result = adapter.observe(anchor, checkpoint=None, now=NOW + timedelta(seconds=2))
                self.assertIsInstance(result, Degraded)
                self.assertEqual(result.code, "GITHUB_RESPONSE_INVALID")
                self.assertNotIn("secret=", repr(result))

    def test_configuration_and_raw_registration_cannot_bypass_exact_allowlists(self):
        for changes in (
            {"repository": "https://attacker.example/api"}, {"repository_id": True},
            {"workflow_id": 0}, {"refs": frozenset({"*"})},
            {"conclusions": frozenset({"anything"})}, {"credential_ref": "token=private"},
            {"permissions": frozenset({"actions:write"})}, {"max_pages": 0},
            {"page_size": 101}, {"overlap_seconds": -1},
        ):
            with self.subTest(changes=changes), self.assertRaisesRegex(ValueError, "GitHub polling configuration is invalid"):
                GitHubPollingAdapter(config(**changes), FixtureClient())
        adapter = GitHubPollingAdapter(config(), FixtureClient())
        spec = adapter.request(ref="refs/heads/main", conclusions=("success",))
        for invalid in (
            replace(spec, verification="not_required"), replace(spec, where=()),
            replace(spec, subject="repo:other/repo"),
            replace(spec, where=(Eq("workflow_id", 8), Eq("ref", "refs/heads/main"), In("conclusion", ("success",)))),
            replace(spec, where=(Eq("workflow_id", 7), Eq("ref", "refs/heads/other"), In("conclusion", ("success",)))),
        ):
            self.assertIsInstance(adapter.establish_anchor(invalid, NOW), Invalid)
        self.assertIsInstance(adapter.request(ref="refs/heads/*", conclusions=("success",)), Invalid)

    def test_verified_post_anchor_completion_registers_ingests_and_reserves(self):
        client = FixtureClient([run()])
        adapter = GitHubPollingAdapter(config(), client)
        spec = adapter.request(ref="refs/heads/main", conclusions=("success",))
        with tempfile.TemporaryDirectory() as tmp:
            module = make_module(Path(tmp) / "signals.sqlite3")
            registration = EventWake(
                module, adapters=[adapter], clock=lambda: NOW, id_factory=lambda: "wake_github",
            ).register(replace(make_intent(), when=spec), idempotency_key="github-1")
            self.assertIsInstance(registration, Registration)
            armed = module.load_armed_signal(registration.wake_id)
            batch = adapter.observe(armed.anchor, checkpoint=None, now=NOW + timedelta(seconds=2))
            self.assertIsInstance(batch, PollBatch)
            self.assertEqual(batch.observations[0].occurrence_value, "42:101:1")
            self.assertIsInstance(module.ingest(batch.observations, batch.commit), Ingested)
            matched = module.evaluate(armed.wake_id, armed, NOW + timedelta(seconds=2), EvaluationLimits(20))
            self.assertIsInstance(matched, Matched)
            self.assertEqual(matched.receipt.verification_state, "verified")
            self.assertEqual(matched.receipt.attributes["conclusion"], "success")

    def test_fresh_process_replay_keeps_one_durable_receipt_and_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "signals.sqlite3"
            module = make_module(database)
            adapter = GitHubPollingAdapter(config(), FixtureClient([run()]))
            spec = adapter.request(ref="refs/heads/main", conclusions=("success",))
            registration = EventWake(module, adapters=[adapter], clock=lambda: NOW, id_factory=lambda: "wake_restart").register(
                replace(make_intent(), when=spec), idempotency_key="github-restart")
            armed = module.load_armed_signal(registration.wake_id)
            batch = adapter.observe(armed.anchor, checkpoint=None, now=NOW + timedelta(seconds=2))
            first = module.ingest(batch.observations, batch.commit)
            script = '''
import json, sys
from pathlib import Path
from datetime import timedelta
from codex_wake.github_polling import GitHubPollingAdapter
from codex_wake.signals import SourceCommit, EvaluationLimits
from tests.test_github_polling import config, FixtureClient, run, NOW
from tests.test_signal_store import make_module
module = make_module(Path(sys.argv[1]))
armed = module.load_armed_signal("wake_restart")
adapter = GitHubPollingAdapter(config(), FixtureClient([run()]))
checkpoint = SourceCommit("github", "github-ci", sys.argv[2], int(sys.argv[3]), NOW + timedelta(seconds=2))
batch = adapter.observe(armed.anchor, checkpoint=checkpoint, now=NOW + timedelta(seconds=3))
ingested = module.ingest(batch.observations, batch.commit)
matched = module.evaluate(armed.wake_id, armed, NOW + timedelta(seconds=3), EvaluationLimits(20))
print(json.dumps({"duplicate": ingested.receipts[0].duplicate, "receipt": ingested.receipts[0].receipt_id, "match": matched.receipt.receipt_id}))
'''
            result = subprocess.run([sys.executable, "-c", script, str(database), batch.commit.checkpoint,
                                     str(batch.commit.checkpoint_order)], capture_output=True, text=True, check=True, timeout=10)
            replay = json.loads(result.stdout)
            self.assertTrue(replay["duplicate"])
            self.assertEqual(replay["receipt"], first.receipts[0].receipt_id)
            self.assertEqual(replay["match"], first.receipts[0].receipt_id)


if __name__ == "__main__":
    unittest.main()
