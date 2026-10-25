"""HTTP request-boundary admission: a denied request never reaches the provider."""

from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import tempfile
import threading
import unittest
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from unittest.mock import patch

import test_goal_supervision as fixtures
from codex_wake.goal_supervision import enroll
from codex_wake.objective_ledger import ObjectiveLedger


class RequestAdmissionTests(unittest.TestCase):
    fixture = fixtures.GoalSupervisionTests.fixture
    controller = fixtures.GoalSupervisionTests.controller

    def test_concurrent_requests_share_allowance_before_provider_submission(self):
        from codex_wake.request_admission import RequestGateway, contract_digest

        with tempfile.TemporaryDirectory() as directory:
            root, policy, log, native, _ = self.fixture(directory)
            with (
                self.controller(root),
                patch(
                    "codex_wake.lifecycle_budget.trusted_upper",
                    return_value=fixtures.NOW,
                ),
            ):
                enroll(root, policy, fixtures.THREAD, 100, 120)
                native["notices"] = {}
                ledger = ObjectiveLedger(root, "allocation-1")
                ledger.configure(
                    dict(
                        revision=1,
                        objective_token_limit=100,
                        objective_time_limit_seconds=120,
                        session_token_limit=100,
                        session_time_limit_seconds=120,
                        max_correction_cycles=0,
                        started_at=fixtures.NOW,
                        objective_deadline=fixtures.NOW + 120,
                    ),
                    "fixture-operator",
                    prior_tokens=40,
                    now=fixtures.NOW,
                )
                arrived, release = threading.Event(), threading.Event()
                calls = []

                class Provider(BaseHTTPRequestHandler):
                    def log_message(self, *args):
                        pass

                    def do_POST(self):
                        calls.append(
                            json.loads(
                                self.rfile.read(int(self.headers["Content-Length"]))
                            )
                        )
                        arrived.set()
                        release.wait(5)
                        response = dict(
                            id="response-one",
                            usage=dict(
                                input_tokens=8,
                                input_tokens_details=dict(cached_tokens=3),
                                output_tokens=2,
                                total_tokens=10,
                            ),
                        )
                        data = (
                            "data: "
                            + json.dumps(
                                dict(type="response.completed", response=response)
                            )
                            + "\n\n"
                        ).encode()
                        self.send_response(200)
                        self.send_header("Content-Type", "text/event-stream")
                        self.send_header("Content-Length", str(len(data)))
                        self.end_headers()
                        self.wfile.write(data)

                provider = ThreadingHTTPServer(("127.0.0.1", 0), Provider)
                thread = threading.Thread(target=provider.serve_forever, daemon=True)
                thread.start()
                self.addCleanup(provider.server_close)
                self.addCleanup(provider.shutdown)
                contract = dict(
                    version=1,
                    provider="owned-inert-fixture",
                    model="fixture-model",
                    max_input_tokens=40,
                    max_output_tokens=10,
                    input_limit="provider_enforced_reject_before_billing",
                    output_limit="max_output_tokens_enforced",
                    usage="response.completed:fresh-v1",
                    review="Reviewed inert fixture maximum usage: input 8, output 2; provider-free contract proof.",
                )
                gateway = RequestGateway(
                    root,
                    "allocation-1",
                    upstream_url=f"http://127.0.0.1:{provider.server_port}/v1/responses",
                    contract=contract,
                    reviewed_contract_sha256=contract_digest(contract),
                    thread_ids=[fixtures.THREAD],
                    now=lambda: fixtures.NOW,
                )
                server = gateway.server()
                threading.Thread(target=server.serve_forever, daemon=True).start()
                self.addCleanup(server.server_close)
                self.addCleanup(server.shutdown)
                from codex_wake.goal_notices import list_notices

                activation = [
                    event
                    for event in list_notices(root, fixtures.THREAD)
                    if event["identity"]["kind"] == "request_activation"
                ]
                self.assertEqual(len(activation), 1)
                self.assertIn("Effective mode hard_admission", activation[0]["text"])
                self.assertEqual(activation[0]["delivery"]["state"], "recorded")
                self.assertIn("Used 40/100", activation[0]["text"])
                self.assertIn("reserved 0; remaining 60", activation[0]["text"])
                self.assertIn("2030-01-01T00:02:00Z", activation[0]["text"])
                self.assertLessEqual(len(activation[0]["text"].encode()), 768)

                def submit(turn="work"):
                    body = dict(
                        model="fixture-model",
                        stream=True,
                        input=[],
                        client_metadata={
                            "x-codex-turn-metadata": json.dumps(
                                dict(
                                    thread_id=fixtures.THREAD,
                                    session_id=fixtures.THREAD,
                                    turn_id=turn,
                                )
                            )
                        },
                    )
                    request = Request(
                        f"http://127.0.0.1:{server.server_port}/v1/responses",
                        data=json.dumps(body).encode(),
                        headers={
                            "Content-Type": "application/json",
                            "Authorization": "Bearer " + gateway.client_token,
                        },
                    )
                    try:
                        with urlopen(request, timeout=8) as response:
                            return response.status, response.read()
                    except HTTPError as error:
                        return error.code, error.read()

                with ThreadPoolExecutor(max_workers=2) as pool:
                    first = pool.submit(submit)
                    self.assertTrue(arrived.wait(3))
                    second = pool.submit(submit)
                    denied = second.result(timeout=3)
                    self.assertEqual(denied[0], 429, denied)
                    self.assertEqual(len(calls), 1)
                    denial_notice = [event for event in list_notices(root, fixtures.THREAD) if event["identity"]["kind"] == "admission"][-1]
                    self.assertIn("objective_token_allowance_unavailable", denial_notice["text"])
                    self.assertIn("Used 40/100; reserved 50; remaining 10", denial_notice["text"])
                    self.assertLessEqual(len(denial_notice["text"].encode()), 768)
                    release.set()
                    self.assertEqual(first.result(timeout=5)[0], 200)
                self.assertEqual(calls[0]["max_output_tokens"], 10)
                self.assertEqual(native["goal"]["status"], "paused")
                self.assertFalse(
                    any(method == "turn/interrupt" for method, _ in native["calls"])
                )
                view = ledger.inspect(now=fixtures.NOW)
                self.assertEqual(view["tokens_used"], 47)
                self.assertEqual(view["tokens_reserved"], 0)

                # Native history is no longer the accounting authority after binding.
                from codex_wake.goal_supervision import poll

                log.unlink()
                sampled = poll(root)[0]
                self.assertEqual(sampled["used_tokens"], 47)
                self.assertEqual(sampled["state"], "armed")
                self.assertTrue(native["notices"])
                self.assertTrue(
                    any(
                        "denied before provider submission" in event["text"]
                        for event in native["notices"].values()
                    )
                )
                # Same response id on another actual attempt is ambiguous billing,
                # not evidence that the second reservation may be refunded.
                duplicate = submit()
                self.assertEqual(duplicate[0], 502)
                unknown = ledger.inspect(now=fixtures.NOW)
                self.assertFalse(unknown["accounting_known"])
                self.assertGreater(unknown["tokens_reserved"], 0)
                attempts = len(calls)
                native["user_text"] = '"Deactivate governor"'
                self.assertEqual(submit()[0], 429)
                self.assertEqual(len(calls), attempts)
                # The actual whole native user message bypasses inference admission.
                native["active"] = ["operator-control"]
                native["user_text"] = "Deactivate governor"
                # Native input can autoactivate its goal; deactivation must
                # restore the already verified pause, without interrupting input.
                native["goal"]["status"] = "active"
                control = submit("operator-control")
                self.assertEqual(control[0], 200, control)
                self.assertIn(b"Governor-generated acknowledgement", control[1])
                self.assertEqual(len(calls), attempts)
                self.assertEqual(gateway.status()["mode"], "inactive")
                self.assertEqual(native["goal"]["status"], "paused")
                self.assertEqual(native["active"], ["operator-control"])
                before = ledger.inspect(now=fixtures.NOW)
                self.assertEqual(before["tokens_used"], unknown["tokens_used"])
                self.assertEqual(before["tokens_reserved"], unknown["tokens_reserved"])
                native["user_text"] = "A normal operator follow-up"
                self.assertEqual(submit("operator-control")[0], 200)
                self.assertEqual(len(calls), attempts + 1)

    def test_heartbeat_cannot_extend_request_wallclock_or_refund_missing_completion(
        self,
    ):
        from codex_wake.request_admission import RequestGateway, contract_digest
        import time

        with tempfile.TemporaryDirectory() as directory:
            root, policy, _, native, _ = self.fixture(directory)
            with (
                self.controller(root),
                patch(
                    "codex_wake.lifecycle_budget.trusted_upper",
                    return_value=fixtures.NOW,
                ),
            ):
                enroll(root, policy, fixtures.THREAD, 110, 120)
                ledger = ObjectiveLedger(root, "allocation-1")
                ledger.configure(
                    dict(
                        revision=1,
                        objective_token_limit=110,
                        objective_time_limit_seconds=120,
                        session_token_limit=110,
                        session_time_limit_seconds=120,
                        max_correction_cycles=0,
                        started_at=fixtures.NOW,
                        objective_deadline=fixtures.NOW + 120,
                    ),
                    "fixture-operator",
                    prior_tokens=40,
                    now=fixtures.NOW,
                )
                finish = threading.Event()
                beats = []

                class Heartbeat(BaseHTTPRequestHandler):
                    def log_message(self, *args):
                        pass

                    def do_POST(self):
                        self.rfile.read(int(self.headers["Content-Length"]))
                        self.send_response(200)
                        self.send_header("Content-Type", "text/event-stream")
                        self.end_headers()
                        try:
                            stop_at = time.monotonic() + 2.5
                            while not finish.wait(0.01) and time.monotonic() < stop_at:
                                self.wfile.write(
                                    b": heartbeat without a completion\n\n"
                                )
                                self.wfile.flush()
                                beats.append(1)
                        except (BrokenPipeError, ConnectionResetError):
                            pass

                provider = ThreadingHTTPServer(("127.0.0.1", 0), Heartbeat)
                threading.Thread(target=provider.serve_forever, daemon=True).start()
                self.addCleanup(provider.server_close)
                self.addCleanup(provider.shutdown)
                self.addCleanup(finish.set)
                contract = dict(
                    version=1,
                    provider="owned-inert-fixture",
                    model="fixture-model",
                    max_input_tokens=40,
                    max_output_tokens=10,
                    input_limit="provider_enforced_reject_before_billing",
                    output_limit="max_output_tokens_enforced",
                    usage="response.completed:fresh-v1",
                    review="Heartbeat fixture has zero inference and no completed usage.",
                )
                gateway = RequestGateway(
                    root,
                    "allocation-1",
                    upstream_url=f"http://127.0.0.1:{provider.server_port}/v1/responses",
                    contract=contract,
                    reviewed_contract_sha256=contract_digest(contract),
                    thread_ids=[fixtures.THREAD],
                    request_timeout=0.2,
                    now=lambda: fixtures.NOW,
                )
                body = dict(
                    model="fixture-model",
                    stream=True,
                    input=[],
                    client_metadata={
                        "x-codex-turn-metadata": json.dumps(
                            dict(
                                thread_id=fixtures.THREAD,
                                session_id=fixtures.THREAD,
                                turn_id="work",
                            )
                        )
                    },
                )
                started = time.monotonic()
                response = gateway.execute(body)
                self.assertEqual(response[0], 502)
                self.assertLess(time.monotonic() - started, 1.5)
                self.assertGreater(len(beats), 3)
                view = ledger.inspect(now=fixtures.NOW)
                self.assertEqual(view["tokens_reserved"], 50)
                self.assertEqual(view["tokens_used"], 40)
                self.assertFalse(view["accounting_known"])

    def test_native_descendant_inherits_scope_without_usage_and_session_spend_survives_retry(
        self,
    ):
        from codex_wake.request_admission import RequestGateway, contract_digest

        with tempfile.TemporaryDirectory() as directory:
            root, policy, log, native, _ = self.fixture(directory)
            with (
                self.controller(root),
                patch(
                    "codex_wake.lifecycle_budget.trusted_upper",
                    return_value=fixtures.NOW,
                ),
            ):
                enroll(root, policy, fixtures.THREAD, 200, 120)
                ledger = ObjectiveLedger(root, "allocation-1")
                ledger.configure(
                    dict(
                        revision=1,
                        objective_token_limit=200,
                        objective_time_limit_seconds=120,
                        session_token_limit=70,
                        session_time_limit_seconds=120,
                        max_correction_cycles=0,
                        started_at=fixtures.NOW,
                        objective_deadline=fixtures.NOW + 120,
                    ),
                    "fixture-operator",
                    prior_tokens=40,
                    now=fixtures.NOW,
                )
                calls = []

                class Provider(BaseHTTPRequestHandler):
                    def log_message(self, *args):
                        pass

                    def do_POST(self):
                        self.rfile.read(int(self.headers["Content-Length"]))
                        calls.append(1)
                        response = dict(
                            id="response-" + str(len(calls)),
                            usage=dict(
                                input_tokens=8,
                                input_tokens_details=dict(cached_tokens=3),
                                output_tokens=2,
                                total_tokens=10,
                            ),
                        )
                        data = (
                            "data: "
                            + json.dumps(
                                dict(type="response.completed", response=response)
                            )
                            + "\n\n"
                        ).encode()
                        self.send_response(200)
                        self.send_header("Content-Length", str(len(data)))
                        self.end_headers()
                        self.wfile.write(data)

                provider = ThreadingHTTPServer(("127.0.0.1", 0), Provider)
                threading.Thread(target=provider.serve_forever, daemon=True).start()
                self.addCleanup(provider.server_close)
                self.addCleanup(provider.shutdown)
                contract = dict(
                    version=1,
                    provider="owned-inert-fixture",
                    model="fixture-model",
                    max_input_tokens=40,
                    max_output_tokens=10,
                    input_limit="provider_enforced_reject_before_billing",
                    output_limit="max_output_tokens_enforced",
                    usage="response.completed:fresh-v1",
                    review="Reviewed inert provider input8 output2, no inference.",
                )
                options = dict(
                    upstream_url=f"http://127.0.0.1:{provider.server_port}/v1/responses",
                    contract=contract,
                    reviewed_contract_sha256=contract_digest(contract),
                    thread_ids=[fixtures.THREAD],
                    now=lambda: fixtures.NOW,
                )
                gateway = RequestGateway(root, "allocation-1", **options)

                def body(thread, turn="work"):
                    return dict(
                        model="fixture-model",
                        stream=True,
                        input=[],
                        client_metadata={
                            "x-codex-turn-metadata": json.dumps(
                                dict(thread_id=thread, session_id=thread, turn_id=turn)
                            )
                        },
                    )

                with self.assertRaisesRegex(ValueError, "unsupported or unreviewed"):
                    RequestGateway(
                        root,
                        "allocation-1",
                        **dict(options, reviewed_contract_sha256="unknown"),
                    )
                self.assertEqual(calls, [])
                # Original40 + worst-case50 exceeds session70 despite objective200.
                self.assertEqual(gateway.execute(body(fixtures.THREAD))[0], 429)
                self.assertEqual(calls, [])
                child = "00000000-0000-7000-8000-000000000290"
                meta = json.loads(log.read_text().splitlines()[0])
                meta["payload"].update(
                    id=child, session_id=child, parent_thread_id=fixtures.THREAD
                )
                (log.parent / "child-without-usage.jsonl").write_text(
                    json.dumps(meta) + "\n"
                )
                native["siblings"] = {
                    child: dict(
                        goal=dict(
                            threadId=child, createdAt=fixtures.NOW, status="active"
                        ),
                        active=["work"],
                        calls=[],
                    )
                }
                self.assertEqual(
                    [gateway.execute(body(child))[0] for _ in range(4)],
                    [200, 200, 200, 429],
                )
                self.assertEqual(len(calls), 3)
                view = ledger.inspect(now=fixtures.NOW)
                self.assertEqual(view["tokens_used"], 61)
                original_deadline = view["request_sessions"][child]["deadline"]
                self.assertEqual(
                    view["request_sessions"][child]["parent_thread_id"], fixtures.THREAD
                )
                restarted = RequestGateway(root, "allocation-1", **options)
                self.assertEqual(restarted.execute(body(child))[0], 429)
                self.assertEqual(
                    ledger.inspect(now=fixtures.NOW)["request_sessions"][child][
                        "deadline"
                    ],
                    original_deadline,
                )
                # Child control uses independently verified native text, and the
                # root allocation choice governs children without enrollment usage.
                native["siblings"][child].update(
                    active=["child-control"], user_text="Deactivate governor"
                )
                control = restarted.execute(body(child, "child-control"))
                self.assertEqual(control[0], 200)
                self.assertEqual(len(calls), 3)
                native["siblings"][child]["user_text"] = "Continue authorized repair"
                self.assertEqual(
                    restarted.execute(body(child, "child-control"))[0], 200
                )
                self.assertEqual(len(calls), 4)
                self.assertEqual(restarted.status()["mode"], "inactive")
