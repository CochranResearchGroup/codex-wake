"""Completion funding through the public authenticated HTTP gateway."""
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hashlib
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import test_goal_supervision as fixtures
from codex_wake.goal_supervision import enroll
from codex_wake.objective_ledger import ObjectiveLedger
from codex_wake.request_admission import RequestGateway, contract_digest

CHILD = '00000000-0000-7000-8000-000000000358'


class CompletionReserveTests(unittest.TestCase):
    fixture = fixtures.GoalSupervisionTests.fixture
    controller = fixtures.GoalSupervisionTests.controller

    @contextmanager
    def campaign(self, *, request_timeout=2, provider_release=None, provider_arrived=None, shared_allocation=False):
        with tempfile.TemporaryDirectory() as directory:
            root, policy, log, native, _ = self.fixture(directory)
            if shared_allocation:
                config = json.loads(policy.read_text())
                grant = config['callers'][fixtures.THREAD]
                grant.pop('allocation_id')
                policy.write_text(json.dumps(dict(version=2, allocations={'allocation-1': grant}, default_allocation='allocation-1', native_caller_binding=True)))
            clock = [fixtures.NOW]
            with self.controller(root), patch('codex_wake.lifecycle_budget.trusted_upper', return_value=fixtures.NOW):
                context = dict(threadId=fixtures.THREAD, sessionId=fixtures.THREAD, callId='fixture-native',
                    **{'x-codex-turn-metadata': dict(thread_id=fixtures.THREAD, session_id=fixtures.THREAD, turn_id='work')})
                enroll(root, policy, fixtures.THREAD, 200, 120, native_context=context if shared_allocation else None)
                native['notices'] = {}
                native['siblings'] = {CHILD: dict(goal=dict(threadId=CHILD, createdAt=fixtures.NOW, status='active'), active=['work'], calls=[])}
                (log.parent / 'child.jsonl').write_text(json.dumps(dict(type='session_meta',
                    payload=dict(id=CHILD, parent_thread_id=fixtures.THREAD, source='cli'))) + '\n')
                ledger = ObjectiveLedger(root, 'allocation-1')
                ledger.configure(dict(revision=1, objective_token_limit=200, objective_time_limit_seconds=120,
                    session_token_limit=200, session_time_limit_seconds=120, max_correction_cycles=1,
                    started_at=fixtures.NOW, objective_deadline=fixtures.NOW + 120),
                    'existing-fixture-authority', prior_tokens=40, now=clock[0])
                calls = []
                class Provider(BaseHTTPRequestHandler):
                    def log_message(self, *args):
                        pass
                    def do_POST(self):
                        calls.append(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
                        if provider_arrived is not None:
                            provider_arrived.set()
                        if provider_release is not None:
                            provider_release.wait(2)
                        response = dict(id='response-' + str(len(calls)), usage=dict(input_tokens=8,
                            input_tokens_details=dict(cached_tokens=0), output_tokens=2, total_tokens=10))
                        data = ('data: ' + json.dumps(dict(type='response.completed', response=response)) + '\n\n').encode()
                        self.send_response(200)
                        self.send_header('Content-Type', 'text/event-stream')
                        self.send_header('Content-Length', str(len(data)))
                        self.end_headers()
                        self.wfile.write(data)
                provider = ThreadingHTTPServer(('127.0.0.1', 0), Provider)
                threading.Thread(target=provider.serve_forever, daemon=True).start()
                self.addCleanup(provider.server_close)
                self.addCleanup(provider.shutdown)
                contract = dict(version=1, provider='owned-inert-fixture', model='fixture-model',
                    max_input_tokens=30, max_output_tokens=10,
                    input_limit='provider_enforced_reject_before_billing', output_limit='max_output_tokens_enforced',
                    usage='response.completed:fresh-v1', review='Inert local provider enforces literal input8/output2 test contract.')
                gateway = RequestGateway(root, 'allocation-1', upstream_url=f'http://127.0.0.1:{provider.server_port}/v1/responses',
                    contract=contract, reviewed_contract_sha256=contract_digest(contract),
                    thread_ids=[fixtures.THREAD], request_timeout=request_timeout, now=lambda: clock[0])
                server = gateway.server()
                threading.Thread(target=server.serve_forever, daemon=True).start()
                self.addCleanup(server.server_close)
                self.addCleanup(server.shutdown)
                def submit(thread=fixtures.THREAD, turn='work', **claims):
                    body = dict(model='fixture-model', stream=True, input=[], client_metadata={
                        'x-codex-turn-metadata': json.dumps(dict(thread_id=thread, session_id=thread, turn_id=turn))}, **claims)
                    request = Request(f'http://127.0.0.1:{server.server_port}/v1/responses', data=json.dumps(body).encode(),
                        headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + gateway.client_token})
                    try:
                        with urlopen(request, timeout=5) as response:
                            return response.status, response.read()
                    except HTTPError as error:
                        return error.code, error.read()
                def status():
                    request = Request(f'http://127.0.0.1:{server.server_port}/status', headers={'Authorization': 'Bearer ' + gateway.client_token})
                    with urlopen(request, timeout=3) as response:
                        return json.loads(response.read())
                def source(name, text):
                    path = Path(directory) / (name + '.txt')
                    path.write_text(text)
                    return dict(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest())
                obligations = [dict(id=name, kind=name, tokens=40, seconds=4,
                    criterion='Host verifies ' + name + ' against the frozen objective') for name in ('acceptance', 'review', 'remediation')]
                yield gateway, submit, status, source, obligations, clock, native, calls, ledger

    def test_implementation_leaves_completion_funded_and_body_role_cannot_select_it(self):
        with self.campaign() as (gateway, submit, status, source, obligations, _, _, calls, _):
            gateway.protect_completion(obligations, source=source('approved-plan', 'Existing approved objective completion obligations'))
            self.assertEqual(submit()[0], 200)
            denied = submit(CHILD, purpose='review', completion_obligation='review')
            self.assertEqual(denied[0], 429, denied)
            self.assertEqual(len(calls), 1)
            self.assertIn(b'completion_resources_protected', denied[1])
            from codex_wake.goal_notices import list_notices
            notice = [event for event in list_notices(gateway.root, fixtures.THREAD) if event['identity']['kind'] == 'admission'][-1]
            self.assertIn('Used 50/200; reserved 0; remaining 150', notice['text'])
            self.assertIn('completion protected 120 tokens/12s', notice['text'])
            self.assertIn('completion_resources_protected', notice['text'])
            self.assertLessEqual(len(notice['text'].encode()), 768)
            current = status()['accounting']['completion']
            self.assertEqual(current['protected_tokens'], 120)
            self.assertFalse(current['obligations_completed'])
            self.assertEqual({item['state'] for item in current['obligations'].values()}, {'pending'})
            gateway.assign_completion(CHILD, 'acceptance', source=source('host-assignment', 'Existing controller assigns this exact child to acceptance'))
            self.assertEqual(submit(CHILD)[0], 200)
            current = status()['accounting']
            self.assertEqual(current['tokens_used'], 60)
            self.assertEqual(current['tokens_reserved'], 0)
            self.assertEqual(len(current['actors']), 2)
            self.assertEqual(len(calls), 2)

    def test_verified_completion_releases_unused_protection_without_claiming_objective_closed(self):
        with self.campaign() as (gateway, submit, status, source, obligations, clock, _, calls, _):
            authority = source('approved-plan', 'Existing approved completion path')
            gateway.protect_completion(obligations, source=authority)
            self.assertEqual(submit()[0], 200)
            for name in ('acceptance', 'review', 'remediation'):
                gateway.assign_completion(CHILD, name, source=source('assign-' + name, 'Host assignment to ' + name))
                self.assertEqual(submit(CHILD)[0], 200)
                evidence = source('result-' + name, 'Host verifies named ' + name + ' criterion against observed HTTP journey')
                gateway.resolve_completion(name, 'completed', source=evidence,
                    note='Named criterion verified from the source artifact; request/test counts are not acceptance')
                # Same approved plan is restart-safe; it cannot reset dispositions or spent resources.
                gateway.protect_completion(obligations, source=authority)
                if name == 'acceptance':
                    self.assertEqual(status()['accounting']['completion']['protected_tokens'], 80)
                    self.assertEqual(submit()[0], 200)  # unused accepted-stage funds are available without a new grant
            current = status()['accounting']
            self.assertEqual(current['tokens_used'], 90)
            self.assertEqual(current['tokens_reserved'], 0)
            self.assertEqual(len(calls), 5)
            self.assertEqual(current['completion']['protected_tokens'], 0)
            self.assertTrue(current['completion']['obligations_completed'])
            self.assertFalse(current['completion']['objective_complete'])
            self.assertEqual(current['correction_cycles'], 1)
            self.assertEqual(current['objective_token_limit'], 200)
            self.assertEqual(current['original_deadline'], fixtures.NOW + 120)
            self.assertEqual(len(current['authorization_history']), 1)
            closed = submit(CHILD)
            self.assertEqual(closed[0], 429)
            self.assertNotIn(b'obligations remain pending', closed[1])
            self.assertEqual(len(calls), 5)

    def test_time_infeasibility_and_deferral_checkpoint_without_releasing_mandatory_funds(self):
        with self.campaign() as (gateway, submit, status, source, obligations, clock, native, calls, _):
            gateway.protect_completion(obligations, source=source('approved-plan', 'Existing completion path'))
            clock[0] = fixtures.NOW + 112
            denied = submit()
            self.assertEqual(denied[0], 429)
            self.assertIn(b'completion_path_infeasible', denied[1])
            self.assertIn(b'checkpoint', denied[1].lower())
            self.assertEqual(calls, [])
            gateway.resolve_completion('remediation', 'deferred', source=source('checkpoint', 'Not enough original time remains'),
                note='Partial checkpoint; mandatory remediation remains outstanding')
            current = status()['accounting']['completion']
            self.assertEqual(current['protected_tokens'], 120)
            self.assertEqual(current['protected_seconds'], 12)
            self.assertEqual(current['deferred'], ['remediation'])
            self.assertEqual(current['outcome'], 'checkpoint_required')
            self.assertFalse(current['obligations_completed'])
            self.assertEqual(submit()[0], 429)
            self.assertEqual(calls, [])
            native.update(active=['operator-control'], user_text='Deactivate governor')
            native['goal']['status'] = 'active'
            control = submit(turn='operator-control')
            self.assertEqual(control[0], 200)
            self.assertIn(b'Governor-generated acknowledgement', control[1])
            self.assertEqual(calls, [])
            self.assertEqual(native['goal']['status'], 'paused')
            native['user_text'] = 'Already-authorized ordinary follow-up'
            self.assertEqual(submit(turn='operator-control')[0], 200)
            current = status()
            self.assertEqual(current['mode'], 'inactive')
            self.assertFalse(current['completion_enforced'])
            self.assertEqual(current['accounting']['tokens_used'], 50)
            self.assertEqual(current['accounting']['completion']['deferred'], ['remediation'])
            self.assertEqual(len(current['accounting']['authorization_history']), 1)
