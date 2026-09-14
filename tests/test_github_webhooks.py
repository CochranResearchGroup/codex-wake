from __future__ import annotations

import hashlib
import hmac
import json
import io
from datetime import UTC, datetime, timedelta
from pathlib import Path
import tempfile
import unittest
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor

from codex_wake.github_polling import GitHubPollingAdapter, GitHubReadError
from codex_wake.github_webhooks import GitHubWebhookIngress, WebhookConfig
from codex_wake.signals import ArmContext, EvaluationLimits, Ingested, Matched, WakeId
from tests.test_github_polling import NOW, FixtureClient, config, run
from tests.test_signal_store import make_module
from tests.test_signals import make_intent


SECRET = b"fixture-only-webhook-key-32-bytes!"


def payload(value=None, **changes):
    value = value or run()
    data = {
        "action": "completed",
        "repository": {"id": value.repository_id, "full_name": value.repository},
        "workflow_run": {
            "id": value.run_id, "run_attempt": value.run_attempt,
            "workflow_id": value.workflow_id, "head_branch": "main",
            "head_sha": value.head_sha, "status": value.status,
            "conclusion": value.conclusion, "updated_at": value.completed_at.isoformat(),
        },
        **changes,
    }
    return json.dumps(data, ensure_ascii=False).encode()


def headers(body, secret=SECRET, **changes):
    return {"X-Hub-Signature-256": "sha256=" + hmac.new(secret, body, hashlib.sha256).hexdigest(),
            "X-GitHub-Event": "workflow_run", "X-GitHub-Delivery": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            **changes}


class GitHubWebhookTests(unittest.TestCase):
    def setup_ingress(self, database, *, client=None, settings=None, resolver=None, monotonic=None, **store_options):
        self.client = client or FixtureClient([run()])
        self.adapter = GitHubPollingAdapter(config(), self.client)
        self.module = make_module(database, **store_options)
        spec = self.adapter.request(ref="refs/heads/main", conclusions=("success",))
        self.armed = self.module.arm(WakeId("wake_hook"), spec,
                                    ArmContext("hook", "hook", NOW, None, make_intent().resume, self.adapter))
        return GitHubWebhookIngress(
            self.adapter, self.client, self.module, checkpoints=self.module, anchor=self.armed.anchor,
            config=settings or WebhookConfig(secret_refs=("current",)),
            resolve_secret=resolver or (lambda ref: SECRET), **({"monotonic": monotonic} if monotonic else {}),
        )

    def test_signed_delivery_is_durable_before_ack_and_polling_is_exact_duplicate(self):
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "signals.sqlite3"
            ingress = self.setup_ingress(database)
            body = payload()
            result = ingress.ingest(body, headers(body), now=NOW + timedelta(seconds=2))
            self.assertEqual((result.status, result.code), (200, "COMMITTED"))
            reopened = make_module(database)
            matched = reopened.evaluate(self.armed.wake_id, self.armed, NOW + timedelta(seconds=2), EvaluationLimits(1))
            self.assertIsInstance(matched, Matched)
            self.assertEqual(matched.receipt.verification_method, "github-run-attempt-read")
            batch = self.adapter.observe(self.armed.anchor, checkpoint=reopened.source_checkpoint("github", "github-ci"),
                                         now=NOW + timedelta(seconds=3))
            poll_result = reopened.ingest(batch.observations, batch.commit)
            self.assertTrue(poll_result.receipts[0].duplicate)
            self.assertEqual(poll_result.receipts[0].receipt_id, matched.receipt.receipt_id)

    def test_exact_byte_authentication_rotation_and_bounded_parse(self):
        calls = []
        def resolver(ref):
            calls.append(ref)
            return {"current": SECRET, "previous": b"prior-fixture-only-webhook-secret"}[ref]
        with tempfile.TemporaryDirectory() as tmp:
            ingress = self.setup_ingress(Path(tmp) / "signals.sqlite3", resolver=resolver,
                                         settings=WebhookConfig(secret_refs=("current", "previous"), max_body_bytes=2048))
            body = payload(note="Unicode \u2603")
            for original, supplied, expected in (
                (body + b" ", headers(body), (401, "SIGNATURE_INVALID")),
                (b"not-json", headers(b"not-json", b"wrong-key"), (401, "SIGNATURE_INVALID")),
                (b"not-json", headers(b"not-json"), (400, "PAYLOAD_INVALID")),
                (b"x" * 2049, headers(b"x" * 2049), (413, "BODY_TOO_LARGE")),
                (body, headers(body, **{"x-hub-signature-256": "ambiguous"}), (400, "HEADERS_INVALID")),
            ):
                with self.subTest(expected=expected):
                    result = ingress.ingest(original, supplied, now=NOW + timedelta(seconds=2))
                    self.assertEqual((result.status, result.code), expected)
                    self.assertIsNone(self.module.source_checkpoint("github", "github-ci"))
            result = ingress.ingest(io.BytesIO(body), headers(body, b"prior-fixture-only-webhook-secret"),
                                    now=NOW + timedelta(seconds=2))
            self.assertEqual(result.status, 200)
            self.assertEqual(calls[-2:], ["current", "previous"])

    def test_claim_allowlists_freshness_and_authoritative_identity_fail_before_commit(self):
        variants = (
            ({"action": "requested"}, {}, "EVENT_NOT_ALLOWED"),
            ({}, {"X-GitHub-Event": "push"}, "EVENT_NOT_ALLOWED"),
            ({}, {"X-GitHub-Delivery": ""}, "DELIVERY_INVALID"),
            ({"repository": {"id": 999, "full_name": "example/project"}}, {}, "EVENT_NOT_ALLOWED"),
            ({"workflow_id": 999}, {}, "EVENT_NOT_ALLOWED"),
            ({"head_branch": "elsewhere"}, {}, "EVENT_NOT_ALLOWED"),
            ({"conclusion": "neutral"}, {}, "EVENT_NOT_ALLOWED"),
            ({"run_attempt": True}, {}, "PAYLOAD_INVALID"),
            ({"updated_at": (NOW - timedelta(days=2)).isoformat()}, {}, "EVENT_STALE"),
            ({"updated_at": (NOW + timedelta(hours=1)).isoformat()}, {}, "EVENT_STALE"),
            ({"updated_at": "2026-09-14T00:00:00"}, {}, "PAYLOAD_INVALID"),
            ({"head_sha": "b" * 40}, {}, "VERIFICATION_FAILED"),
        )
        with tempfile.TemporaryDirectory() as tmp:
            ingress = self.setup_ingress(Path(tmp) / "signals.sqlite3")
            for changes, header_changes, expected in variants:
                data = json.loads(payload())
                for key, value in changes.items():
                    (data if key in {"repository", "action"} else data["workflow_run"])[key] = value
                body = json.dumps(data).encode()
                with self.subTest(changes=changes):
                    result = ingress.ingest(body, headers(body, **header_changes), now=NOW + timedelta(seconds=2))
                    self.assertEqual(result.code, expected)
                    self.assertIsNone(self.module.source_checkpoint("github", "github-ci"))
            self.client.verified[(101, 1)] = run(run_id=102)
            body = payload()
            self.assertEqual(ingress.ingest(body, headers(body), now=NOW + timedelta(seconds=2)).code, "VERIFICATION_FAILED")
            self.client.verified[(101, 1)] = GitHubReadError("auth")
            self.assertEqual(ingress.ingest(body, headers(body), now=NOW + timedelta(seconds=2)).code, "VERIFICATION_UNAVAILABLE")

    def test_storm_admission_has_one_inflight_no_queue_and_a_fixed_rate_ceiling(self):
        entered, release = threading.Event(), threading.Event()
        class BlockingClient(FixtureClient):
            def get_run_attempt(self, *args):
                entered.set()
                if not release.wait(5):
                    raise RuntimeError("fixture timeout")
                return super().get_run_attempt(*args)
        ticks = [0.0]
        with tempfile.TemporaryDirectory() as tmp:
            ingress = self.setup_ingress(Path(tmp) / "signals.sqlite3", client=BlockingClient([run()]),
                                         settings=WebhookConfig(secret_refs=("current",), requests_per_window=2),
                                         monotonic=lambda: ticks[0])
            body = payload()
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(ingress.ingest, body, headers(body), now=NOW + timedelta(seconds=2))
                try:
                    self.assertTrue(entered.wait(5))
                    self.assertEqual(ingress.ingest(body, headers(body), now=NOW + timedelta(seconds=2)).code, "BUSY")
                finally:
                    release.set()
                self.assertEqual(future.result().code, "COMMITTED")
            self.assertEqual(ingress.ingest(body, headers(body), now=NOW + timedelta(seconds=2)).code, "DUPLICATE")
            for _ in range(50):
                self.assertEqual(ingress.ingest(body, headers(body), now=NOW + timedelta(seconds=2)).code, "RATE_LIMITED")
            ticks[0] = 60.0
            self.assertEqual(ingress.ingest(body, headers(body), now=NOW + timedelta(seconds=2)).code, "DUPLICATE")

    def test_delivery_reuse_is_bounded_and_never_replaces_durable_occurrence_deduplication(self):
        values = [run(), run(run_id=102)]
        with tempfile.TemporaryDirectory() as tmp:
            ingress = self.setup_ingress(Path(tmp) / "signals.sqlite3", client=FixtureClient(values),
                                         settings=WebhookConfig(secret_refs=("current",), delivery_cache_size=1))
            first, second = (payload(value) for value in values)
            self.assertEqual(ingress.ingest(first, headers(first), now=NOW + timedelta(seconds=2)).code, "COMMITTED")
            self.assertEqual(ingress.ingest(second, headers(second), now=NOW + timedelta(seconds=2)).code, "DELIVERY_CONFLICT")
            other = {"X-GitHub-Delivery": "11111111-2222-3333-4444-555555555555"}
            self.assertEqual(ingress.ingest(second, headers(second, **other), now=NOW + timedelta(seconds=2)).code, "COMMITTED")
            self.assertEqual(ingress.ingest(first, headers(first), now=NOW + timedelta(seconds=2)).code, "DUPLICATE")

    def test_crash_before_or_after_commit_is_reconciled_by_fresh_process_retry(self):
        script = '''
import os, sys
from pathlib import Path
from datetime import timedelta
from tests.test_github_webhooks import GitHubWebhookTests, payload, headers, NOW
def fault(label):
    if label == sys.argv[2]:
        os._exit(73)
ingress = GitHubWebhookTests().setup_ingress(Path(sys.argv[1]), checkpoint=fault)
body = payload()
result = ingress.ingest(body, headers(body), now=NOW + timedelta(seconds=2))
print(result.code, flush=True)
'''
        for fault, expected in (("before_ingest_commit", "COMMITTED"), ("after_ingest_commit", "DUPLICATE")):
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as tmp:
                database = Path(tmp) / "signals.sqlite3"
                crashed = subprocess.run([sys.executable, "-c", script, str(database), fault], capture_output=True, text=True)
                self.assertEqual(crashed.returncode, 73, crashed.stderr)
                self.assertEqual(crashed.stdout, "")
                retry = subprocess.run([sys.executable, "-c", script, str(database), "no_fault"], capture_output=True, text=True)
                self.assertEqual(retry.returncode, 0, retry.stderr)
                self.assertEqual(retry.stdout.strip(), expected)

    def test_out_of_order_and_missed_deliveries_converge_without_advancing_poll_coverage(self):
        values = [run(), run(run_id=103, completed_at=NOW + timedelta(seconds=2)),
                  run(run_id=104, completed_at=NOW + timedelta(seconds=3)),
                  run(run_id=100, completed_at=NOW + timedelta(seconds=4))]
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "signals.sqlite3"
            ingress = self.setup_ingress(database, client=FixtureClient(values),
                                         settings=WebhookConfig(secret_refs=("current",), max_age_seconds=5))
            for index in (3, 0):
                body = payload(values[index])
                result = ingress.ingest(body, headers(body, **{"X-GitHub-Delivery": f"00000000-0000-0000-0000-{index:012d}"}),
                                        now=NOW + timedelta(seconds=5))
                self.assertEqual(result.code, "COMMITTED")
            stale = payload(values[2])
            self.assertEqual(ingress.ingest(stale, headers(stale), now=NOW + timedelta(seconds=10)).code, "EVENT_STALE")
            checkpoint = self.module.source_checkpoint("github", "github-ci")
            self.assertEqual(checkpoint.observed_through, datetime(1970, 1, 1, tzinfo=UTC))
            reopened = make_module(database)
            batch = self.adapter.observe(self.armed.anchor, checkpoint=checkpoint, now=NOW + timedelta(seconds=10))
            result = reopened.ingest(batch.observations, batch.commit)
            self.assertIsInstance(result, Ingested)
            self.assertEqual([receipt.duplicate for receipt in result.receipts], [True, False, False, True])
            attempt = run(run_attempt=2, completed_at=NOW + timedelta(seconds=11))
            self.client.runs += (attempt,)
            body = payload(attempt)
            self.assertEqual(ingress.ingest(body, headers(body), now=NOW + timedelta(seconds=12)).code, "COMMITTED")
            self.assertEqual(reopened.source_checkpoint("github", "github-ci"), batch.commit)
            follow = self.adapter.observe(self.armed.anchor, checkpoint=batch.commit, now=NOW + timedelta(seconds=12))
            self.assertTrue(all(item.duplicate for item in reopened.ingest(follow.observations, follow.commit).receipts))

    def test_commit_failure_and_checkpoint_race_return_no_success_and_retry_safely(self):
        fail = [True]
        def fault(label):
            if label == "before_ingest_commit" and fail[0]:
                raise OSError("credential=private-canary")
        with tempfile.TemporaryDirectory() as tmp:
            ingress = self.setup_ingress(Path(tmp) / "signals.sqlite3", checkpoint=fault)
            body = payload()
            self.assertEqual(ingress.ingest(body, headers(body), now=NOW + timedelta(seconds=2)).code, "COMMIT_FAILED")
            self.assertIsNone(self.module.source_checkpoint("github", "github-ci"))
            fail[0] = False
            seed = self.adapter.checkpoint_for_anchor(self.armed.anchor)
            batch = self.adapter.observe(self.armed.anchor, checkpoint=None, now=NOW + timedelta(seconds=3))
            module = self.module
            class RacingReader:
                def source_checkpoint(self, *args):
                    module.ingest(batch.observations, batch.commit)
                    return seed
            ingress.checkpoints = RacingReader()
            self.assertEqual(ingress.ingest(body, headers(body), now=NOW + timedelta(seconds=4)).code, "COMMIT_FAILED")
            ingress.checkpoints = module
            self.assertEqual(ingress.ingest(body, headers(body), now=NOW + timedelta(seconds=4)).code, "DUPLICATE")

    def test_short_reads_consume_to_eof_and_cannot_hide_trailing_bytes(self):
        class ShortReads:
            def __init__(self, data, size):
                self.stream = io.BytesIO(data)
                self.size = size
                self.consumed = 0
            def read(self, limit):
                value = self.stream.read(min(limit, self.size))
                self.consumed += len(value)
                return value
        with tempfile.TemporaryDirectory() as tmp:
            ingress = self.setup_ingress(Path(tmp) / "signals.sqlite3", settings=WebhookConfig(secret_refs=("current",), max_body_bytes=1024))
            body = payload()
            hidden_tail = ShortReads(body + b"UNSIGNED-TRAILING-CONTENT", len(body))
            self.assertEqual(ingress.ingest(hidden_tail, headers(body), now=NOW + timedelta(seconds=2)).code, "SIGNATURE_INVALID")
            self.assertEqual(hidden_tail.consumed, len(body) + len(b"UNSIGNED-TRAILING-CONTENT"))
            stream = ShortReads(body, 7)
            self.assertEqual(ingress.ingest(stream, headers(body), now=NOW + timedelta(seconds=2)).code, "COMMITTED")
            self.assertEqual(stream.consumed, len(body))
            oversized = ShortReads(b"x" * 3000, 23)
            self.assertEqual(ingress.ingest(oversized, headers(body), now=NOW + timedelta(seconds=2)).code, "BODY_TOO_LARGE")
            self.assertEqual(oversized.consumed, 1025)

    def test_sanitized_boundaries_and_raw_payload_are_never_persisted(self):
        canary = "ghp_RAW_PAYLOAD_PRIVATE_CANARY"
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "signals.sqlite3"
            ingress = self.setup_ingress(database)
            malformed = (b'{"workflow_run":{},"workflow_run":{}}', b"[1,2]", b"\xff",
                         b"[" * 2000 + b"]" * 2000, payload(note=float("nan")))
            for body in malformed:
                with self.subTest(body=body[:40]):
                    result = ingress.ingest(body, headers(body), now=NOW + timedelta(seconds=2))
                    self.assertEqual(result.code, "PAYLOAD_INVALID")
            def unavailable(ref):
                raise RuntimeError(canary)
            ingress.resolve_secret = unavailable
            body = payload(note=canary)
            self.assertEqual(ingress.ingest(body, headers(body), now=NOW + timedelta(seconds=2)).code, "SECRET_UNAVAILABLE")
            ingress.resolve_secret = lambda ref: SECRET
            self.assertEqual(ingress.ingest(body, headers(body), now=NOW + timedelta(seconds=2)).code, "COMMITTED")
            for path in Path(tmp).rglob("*"):
                if path.is_file():
                    self.assertNotIn(canary.encode(), path.read_bytes(), str(path))
                    self.assertNotIn(SECRET, path.read_bytes(), str(path))
            for settings in (WebhookConfig(secret_refs=([],)), WebhookConfig(secret_refs=("same", "same")),
                             WebhookConfig(secret_refs=("current",), max_body_bytes=True),
                             WebhookConfig(secret_refs=("current",), requests_per_window=0)):
                with self.subTest(settings=settings), self.assertRaisesRegex(ValueError, "configuration is invalid"):
                    self.setup_ingress(database, settings=settings)

    def test_ingress_does_not_fan_out_or_evaluate_wakes(self):
        with tempfile.TemporaryDirectory() as tmp:
            ingress = self.setup_ingress(Path(tmp) / "signals.sqlite3")
            module = self.module
            arms = [self.armed]
            for index in range(2):
                name = f"wake_extra_{index}"
                arms.append(module.arm(WakeId(name), self.armed.spec,
                            ArmContext(name, name, NOW, None, make_intent().resume, self.adapter)))
            class IngestOnly:
                def ingest(self, observations, commit):
                    if len(observations) != 1:
                        raise AssertionError("one delivery must commit one normalized observation")
                    return module.ingest(observations, commit)
                def evaluate(self, *args):
                    raise AssertionError("ingress must not spend evaluation/fanout budget")
            ingress.module = IngestOnly()
            body = payload()
            self.assertEqual(ingress.ingest(body, headers(body), now=NOW + timedelta(seconds=2)).code, "COMMITTED")
            matches = [module.evaluate(arm.wake_id, arm, NOW + timedelta(seconds=2), EvaluationLimits(1)) for arm in arms]
            self.assertTrue(all(isinstance(match, Matched) for match in matches))
            self.assertEqual(len({match.receipt.receipt_id for match in matches}), 1)

    def test_first_webhook_from_a_newer_arm_cannot_hide_an_older_arms_polling_history(self):
        values = [run(), run(run_id=102, completed_at=NOW + timedelta(hours=1, seconds=1))]
        with tempfile.TemporaryDirectory() as tmp:
            ingress = self.setup_ingress(Path(tmp) / "signals.sqlite3", client=FixtureClient(values))
            newer = self.module.arm(WakeId("wake_newer"), self.armed.spec,
                                   ArmContext("newer", "newer", NOW + timedelta(hours=1), None,
                                              make_intent().resume, self.adapter))
            ingress.anchor = newer.anchor
            body = payload(values[1])
            self.assertEqual(ingress.ingest(body, headers(body), now=NOW + timedelta(hours=1, seconds=2)).code, "COMMITTED")
            checkpoint = self.module.source_checkpoint("github", "github-ci")
            batch = self.adapter.observe(self.armed.anchor, checkpoint=checkpoint, now=NOW + timedelta(hours=1, seconds=3))
            self.assertEqual([item.attributes["run_id"] for item in batch.observations], [101, 102])


if __name__ == "__main__":
    unittest.main()
