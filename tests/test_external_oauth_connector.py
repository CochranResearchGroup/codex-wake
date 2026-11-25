"""External connector behavior through its OAuth/HTTP interface."""
import asyncio
from contextlib import asynccontextmanager
import base64
import hashlib
import json
import re
from urllib.parse import urlsplit,parse_qs,urlencode
from pathlib import Path
import tempfile
import unittest

import httpx2 as httpx


class ExternalConnectorTests(unittest.TestCase):
    def config(self):
        return dict(issuer='https://wake.example',owner='operator',host='h',environment='e',
                    targets=[dict(host='h',environment='e')],scopes=['observe','content.observe'],
                    redirect_uris=['https://client.example/callback'],grant_seconds=3600,
                    authelia_url='http://127.0.0.1:19097/api/authz/forward-auth')

    def operations(self,root):
        from codex_wake.controller_operations import ControllerOperations
        from codex_wake.managed_inventory import ManagedInventory
        from codex_wake.controller_tabs import ControllerTabs
        return ControllerOperations(ManagedInventory(root),host='h',environment='e',tabs=ControllerTabs(root,workspaces={},host='h',environment='e'))

    def test_discovery_and_anonymous_mcp_challenge_share_exact_resource(self):
        from codex_wake.external_connector import create_app
        async def scenario(root):
            app=create_app(self.config(),Path(root),identify=lambda request:'operator',operations=self.operations(Path(root)))
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app),base_url='https://wake.example') as client:
                metadata=await client.get('/.well-known/oauth-protected-resource/mcp')
                self.assertEqual(metadata.status_code,200)
                self.assertEqual(metadata.json()['resource'],'https://wake.example/mcp')
                denied=await client.post('/mcp',json=dict(jsonrpc='2.0',id=1,method='initialize',params={}))
                self.assertEqual(denied.status_code,401)
                self.assertIn('https://wake.example/.well-known/oauth-protected-resource/mcp',denied.headers['www-authenticate'])
        with tempfile.TemporaryDirectory() as root:asyncio.run(scenario(root))

    def test_explicit_subset_consent_pkce_and_refresh_retain_action_scope(self):
        from codex_wake.external_connector import create_app
        async def scenario(root):
            app=create_app(self.config(),Path(root),identify=lambda request:'operator',operations=self.operations(Path(root)))
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app),base_url='https://wake.example') as client:
                registered=await client.post('/register',json=dict(redirect_uris=['https://client.example/callback'],client_name='My connector'))
                self.assertEqual(registered.status_code,201)
                client_id=registered.json()['client_id'];verifier='v'*43
                challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
                params=dict(client_id=client_id,redirect_uri='https://client.example/callback',resource='https://wake.example/mcp',response_type='code',code_challenge_method='S256',code_challenge=challenge,state='client-state',scope='observe')
                landing=await client.get('/authorize',params=params)
                self.assertEqual(landing.status_code,200)
                self.assertIn('My connector',landing.text)
                self.assertEqual(landing.headers['referrer-policy'],'same-origin')
                self.assertIn('https://client.example/callback',landing.headers['content-security-policy'])
                flow=re.search(r'name="flow" value="([^"]+)"',landing.text)[1]
                form=dict(flow=flow,decision='approve',mode='subset',scopes='observe',targets='0',actions='environment.snapshot')
                approved=await client.post('/authorize',data=form,headers={'Origin':'https://wake.example'})
                self.assertEqual(approved.status_code,303)
                callback=parse_qs(urlsplit(approved.headers['location']).query)
                self.assertEqual(callback['state'],['client-state']);self.assertEqual(callback['iss'],['https://wake.example'])
                exchange=dict(grant_type='authorization_code',client_id=client_id,code=callback['code'][0],redirect_uri=params['redirect_uri'],code_verifier=verifier,resource=params['resource'])
                wrong=await client.post('/token',data=dict(exchange,code_verifier='wrong'*12));self.assertEqual(wrong.status_code,400)
                token=await client.post('/token',data=exchange);self.assertEqual(token.status_code,200)
                replay=await client.post('/token',data=exchange);self.assertEqual(replay.status_code,400)
                refresh=await client.post('/token',data=dict(grant_type='refresh_token',client_id=client_id,refresh_token=token.json()['refresh_token'],resource=params['resource']))
                self.assertEqual(refresh.status_code,200);self.assertEqual(refresh.json()['scope'],'observe')
                from mcp import ClientSession
                from mcp.client.streamable_http import streamable_http_client
                async with app.router.lifespan_context(app):
                    async with httpx.AsyncClient(transport=httpx.ASGITransport(app),headers={'Authorization':'Bearer '+refresh.json()['access_token']}) as mcp_http:
                        async with streamable_http_client('https://wake.example/mcp',http_client=mcp_http) as streams:
                            async with ClientSession(streams[0],streams[1]) as session:
                                await session.initialize()
                                tools=await session.list_tools()
                                self.assertEqual([tool.name for tool in tools.tools],['wake_environment_snapshot'])
                                read=await session.call_tool('wake_environment_snapshot',{})
                                self.assertFalse(read.is_error)
                                self.assertEqual(read.structured_content['result']['schema_version'],1)
                                denied=await session.call_tool('wake_wakes_schedules_list',{})
                                self.assertTrue(denied.is_error)
                revoked=await client.post('/revoke',data=dict(token=refresh.json()['access_token'],client_id=client_id))
                self.assertEqual(revoked.status_code,200)
                blocked=await client.post('/mcp',json=dict(jsonrpc='2.0',id=2,method='ping'),headers={'Authorization':'Bearer '+refresh.json()['access_token']})
                self.assertEqual(blocked.status_code,401)
                reused=await client.post('/authorize',data=form,headers={'Origin':'https://wake.example'});self.assertEqual(reused.status_code,400)
        with tempfile.TemporaryDirectory() as root:asyncio.run(scenario(root))

    def test_owner_csrf_redirect_and_explicit_mode_are_required_before_consent(self):
        from codex_wake.external_connector import create_app
        identity=[None]
        async def scenario(root):
            app=create_app(self.config(),Path(root),identify=lambda request:identity[0],operations=self.operations(Path(root)))
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app),base_url='https://wake.example') as client:
                bad=await client.post('/register',json=dict(redirect_uris=['https://unregistered.example/callback']))
                self.assertEqual(bad.status_code,400)
                registered=await client.post('/register',json=dict(redirect_uris=['https://client.example/callback']))
                params=dict(client_id=registered.json()['client_id'],redirect_uri='https://client.example/callback',resource='https://wake.example/mcp',response_type='code',code_challenge_method='S256',code_challenge='x'*43,scope='observe')
                spoofed=await client.get('/authorize',params=params,headers={'Remote-User':'operator'})
                self.assertEqual(spoofed.status_code,403)
                identity[0]='other-user'
                denied=await client.get('/authorize',params=params);self.assertEqual(denied.status_code,403)
                identity[0]='operator'
                wrong_redirect=await client.get('/authorize',params=dict(params,redirect_uri='https://unregistered.example/callback'))
                self.assertEqual(wrong_redirect.status_code,400)
                landing=await client.get('/authorize',params=params)
                self.assertIn('Secure',landing.headers['set-cookie']);self.assertIn('HttpOnly',landing.headers['set-cookie'])
                flow=re.search(r'name="flow" value="([^"]+)"',landing.text)[1]
                form=dict(flow=flow,decision='approve',mode='operator',scopes='observe',targets='0')
                no_origin=await client.post('/authorize',data=form);self.assertEqual(no_origin.status_code,403)
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app),base_url='https://wake.example') as attacker:
                    no_cookie=await attacker.post('/authorize',data=form,headers={'Origin':'https://wake.example'})
                    self.assertEqual(no_cookie.status_code,400)
                no_mode=await client.post('/authorize',data={k:v for k,v in form.items() if k!='mode'},headers={'Origin':'https://wake.example'})
                self.assertEqual(no_mode.status_code,400)
        with tempfile.TemporaryDirectory() as root:asyncio.run(scenario(root))

    def test_wrong_signed_in_owner_gets_denial_without_login_loop(self):
        from codex_wake.external_connector import create_app
        async def scenario(root):
            config=dict(self.config(),login_url='https://auth.example/')
            app=create_app(config,Path(root),identify=lambda request:'other-user',operations=self.operations(Path(root)))
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app),base_url='https://wake.example') as client:
                registered=await client.post('/register',json=dict(redirect_uris=['https://client.example/callback']))
                result=await client.get('/authorize',params=dict(client_id=registered.json()['client_id'],redirect_uri='https://client.example/callback',resource='https://wake.example/mcp',response_type='code',code_challenge_method='S256',code_challenge='x'*43,scope='observe'))
                self.assertEqual(result.status_code,403)
                self.assertNotIn('location',result.headers)
        with tempfile.TemporaryDirectory() as root:asyncio.run(scenario(root))

    def test_deployment_policy_requires_private_file_and_fixed_client_redirect(self):
        from codex_wake.external_connector import load_config
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'policy.json'
            config=dict(self.config(),wake_root=directory,port=37186)
            p.write_text(json.dumps(config));p.chmod(0o644)
            with self.assertRaises(ValueError):load_config(p)
            p.chmod(0o600)
            self.assertEqual(load_config(p)['owner'],'operator')
            p.write_text(json.dumps(dict(config,redirect_uris=[])))
            with self.assertRaises(ValueError):load_config(p)

    def test_default_identity_verifier_uses_local_idp_not_headers_or_redirected_identity(self):
        from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
        import threading
        from codex_wake.external_connector import create_app
        class IdentityProvider(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_GET(self):
                if self.headers.get('Cookie')=='synthetic-owner':
                    self.send_response(200);self.send_header('Remote-User','operator')
                elif self.path=='/redirected-identity':
                    self.send_response(200);self.send_header('Remote-User','operator')
                else:
                    self.send_response(302);self.send_header('Location','/redirected-identity')
                self.send_header('Content-Length','0');self.end_headers()
        idp=ThreadingHTTPServer(('127.0.0.1',0),IdentityProvider)
        worker=threading.Thread(target=idp.serve_forever,daemon=True);worker.start()
        async def scenario(root):
            config=dict(self.config(),authelia_url=f'http://127.0.0.1:{idp.server_port}/api/authz/forward-auth')
            app=create_app(config,Path(root),operations=self.operations(Path(root)))
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app),base_url='https://wake.example') as client:
                registered=await client.post('/register',json=dict(redirect_uris=['https://client.example/callback']))
                params=dict(client_id=registered.json()['client_id'],redirect_uri='https://client.example/callback',resource='https://wake.example/mcp',response_type='code',code_challenge_method='S256',code_challenge='x'*43,scope='observe')
                denied=await client.get('/authorize',params=params,headers={'Remote-User':'operator'})
                self.assertEqual(denied.status_code,403)
                owner=await client.get('/authorize',params=params,headers={'Cookie':'synthetic-owner'})
                self.assertEqual(owner.status_code,200)
        try:
            with tempfile.TemporaryDirectory() as root:asyncio.run(scenario(root))
        finally:idp.shutdown();idp.server_close();worker.join(3)

    def test_operator_consent_accepts_browser_multiselect_rights_without_widening_request(self):
        from codex_wake.external_connector import create_app
        async def scenario(root):
            app=create_app(self.config(),Path(root),identify=lambda request:'operator',operations=self.operations(Path(root)))
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app),base_url='https://wake.example') as client:
                registered=await client.post('/register',json=dict(redirect_uris=['https://client.example/callback']))
                verifier='o'*43;challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
                params=dict(client_id=registered.json()['client_id'],redirect_uri='https://client.example/callback',resource='https://wake.example/mcp',response_type='code',code_challenge_method='S256',code_challenge=challenge,scope='observe content.observe')
                landing=await client.get('/authorize',params=params)
                self.assertIn('Read conversation and operation content',landing.text)
                flow=re.search(r'name="flow" value="([^"]+)"',landing.text)[1]
                form=urlencode([('flow',flow),('decision','approve'),('mode','operator'),('scopes','observe'),('scopes','content.observe'),('targets','0')])
                approved=await client.post('/authorize',content=form,headers={'Origin':'https://wake.example','Content-Type':'application/x-www-form-urlencoded'})
                self.assertEqual(approved.status_code,303)
                code=parse_qs(urlsplit(approved.headers['location']).query)['code'][0]
                token=await client.post('/token',data=dict(grant_type='authorization_code',client_id=params['client_id'],redirect_uri=params['redirect_uri'],resource=params['resource'],code=code,code_verifier=verifier))
                self.assertEqual(token.status_code,200)
                self.assertEqual(set(token.json()['scope'].split()),{'observe','content.observe'})
                wrong_resource=await client.post('/token',data=dict(grant_type='refresh_token',client_id=params['client_id'],refresh_token=token.json()['refresh_token'],resource='https://other.example/mcp'))
                self.assertEqual(wrong_resource.status_code,400)
                narrowed=create_app(dict(self.config(),scopes=['observe']),Path(root),identify=lambda request:'operator',operations=self.operations(Path(root)))
                async with narrowed.router.lifespan_context(narrowed):
                    async with httpx.AsyncClient(transport=httpx.ASGITransport(narrowed),base_url='https://wake.example') as other:
                        response=await other.post('/mcp',headers={'Authorization':'Bearer '+token.json()['access_token'],'Accept':'application/json, text/event-stream'},json=dict(jsonrpc='2.0',id=1,method='initialize',params=dict(protocolVersion='2025-03-26',capabilities={},clientInfo={'name':'test','version':'1'})))
                        self.assertEqual(response.status_code,401)
        with tempfile.TemporaryDirectory() as root:asyncio.run(scenario(root))

    @asynccontextmanager
    async def external_client(self, app, config):
        from mcp import ClientSession
        from mcp.client.streamable_http import streamable_http_client

        transport = httpx.ASGITransport(app)
        async with httpx.AsyncClient(transport=transport, base_url=config['issuer']) as client:
            registered = await client.post('/register', json=dict(redirect_uris=config['redirect_uris']))
            self.assertEqual(registered.status_code, 201)
            client_id = registered.json()['client_id']

            async def grant(scope, targets='0'):
                verifier = 'v' * 43
                challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
                auth = dict(client_id=client_id, redirect_uri=config['redirect_uris'][0],
                            resource=config['issuer'] + '/mcp', response_type='code', code_challenge=challenge,
                            code_challenge_method='S256', scope=scope)
                landing = await client.get('/authorize', params=auth)
                self.assertEqual(landing.status_code, 200, landing.text)
                flow = re.search(r'name="flow" value="([^"]+)"', landing.text)[1]
                approved = await client.post('/authorize',
                    data=dict(flow=flow, decision='approve', mode='operator', scopes=scope, targets=targets),
                    headers={'Origin': config['issuer']})
                self.assertEqual(approved.status_code, 303)
                code = parse_qs(urlsplit(approved.headers['location']).query)['code'][0]
                token = await client.post('/token', data=dict(grant_type='authorization_code', code=code,
                    client_id=client_id, redirect_uri=auth['redirect_uri'], resource=auth['resource'],
                    code_verifier=verifier))
                self.assertEqual(token.status_code, 200)
                return token.json()['access_token']

            @asynccontextmanager
            async def connector(token):
                async with httpx.AsyncClient(transport=transport, headers={
                        'Authorization': 'Bearer ' + token}) as mcp_http:
                    async with streamable_http_client(config['issuer'] + '/mcp', http_client=mcp_http) as streams:
                        async with ClientSession(streams[0], streams[1]) as session:
                            await session.initialize()
                            yield session

            async with app.router.lifespan_context(app):
                yield client_id, grant, connector

    def test_control_only_mailbox_send_does_not_wait_or_return_conversation_content(self):
        from test_controller_runtime import RuntimeTests
        from codex_wake.controller_operations import ControllerOperations
        from codex_wake.external_connector import create_app
        from codex_wake.managed_inventory import ManagedInventory

        async def scenario(directory):
            runtime, owner, arguments, mailbox, natives = RuntimeTests().fixture(directory)
            root = runtime.root
            config = dict(self.config(), owner=owner.subject, host='fixture', environment='linux',
                          targets=owner.targets, scopes=['observe', 'control', 'content.observe'])
            operations = ControllerOperations(ManagedInventory(root), host='fixture', environment='linux')
            app = create_app(config, root, identify=lambda request: owner.subject, operations=operations)
            async with self.external_client(app, config) as (client_id, grant, connector):
                path = root / 'controller-messaging.json'
                messaging = json.loads(path.read_text())
                messaging['bindings']['native-sender']['client_id'] = client_id
                path.write_text(json.dumps(messaging))
                limited = await grant('observe control')
                async with connector(limited) as session:
                    tools = {tool.name for tool in (await session.list_tools()).tools}
                    self.assertIn('wake_operations_send', tools)
                    self.assertNotIn('wake_operations_result', tools)
                    intent = dict(arguments)
                    intent.pop('response_requested')
                    denied = await session.call_tool('wake_operations_send',
                                                     dict(intent, response_requested=True, wait_timeout=0))
                    self.assertTrue(denied.is_error)
                    self.assertEqual(denied.structured_content, {'error': 'insufficient_scope'})
                    self.assertEqual(mailbox.list(natives[0], outbox=True)['messages'], [])
                    sent = await session.call_tool('wake_operations_send', intent)
                    self.assertFalse(sent.is_error, sent.structured_content)
                    operation = sent.structured_content['result']['operation']
                    self.assertNotIn('wait', sent.structured_content['result'])
                    self.assertIn('message_id', operation['result'])
                    self.assertNotIn('answer', operation)

                full = await grant('observe control content.observe')
                async with connector(full) as session:
                    positive = dict(arguments,
                        _request=dict(arguments['_request'], operation_id='permitted-reply',
                                      idempotency_key='permitted-reply', correlation_id='permitted-reply'))
                    sent = await session.call_tool('wake_operations_send', positive)
                    self.assertFalse(sent.is_error, sent.structured_content)
                    message = sent.structured_content['result']['operation']['result']['message_id']
                    mailbox.reply(natives[1], message, body='Scoped synthetic reply',
                                  idempotency_key='permitted-reply', kind='result', delivery='inbox')
                    result = await session.call_tool('wake_operations_result',
                                                     {'operation_id': 'permitted-reply'})
                    self.assertFalse(result.is_error, result.structured_content)
                    self.assertEqual(result.structured_content['result']['operation']['answer']['text'],
                                     'Scoped synthetic reply')

        with tempfile.TemporaryDirectory() as directory:
            asyncio.run(scenario(directory))

    def test_windows_schedule_is_grant_pinned_and_keeps_original_delivery_window(self):
        import sqlite3
        from uuid import uuid4
        from codex_wake.controller_hosts import HostRegistry
        from codex_wake.external_connector import create_app

        async def scenario(directory):
            root = Path(directory)
            bridge = root / 'message-owner'
            bridge.mkdir(mode=0o700)
            registry = HostRegistry(root / 'hosts.sqlite')
            local = registry.register('h', 'wsl', kind='wsl', authority='fixture-wsl',
                                      destination='localhost', operator=True)['target']
            peer = registry.register('h', 'windows', kind='windows', authority='fixture-windows',
                                     destination='localhost', operator=True)['target']
            owner_config = root / 'owner.json'
            owner_config.write_text(json.dumps(dict(root=str(bridge), registry=str(registry.path),
                                                    owner=local, peer=peer)))
            owner_config.chmod(0o600)
            target = dict(host='h', environment='e', presentation='psmux', conversation_id=str(uuid4()),
                          namespace=peer['environment'], authority=peer['authority'], generation=peer['generation'])
            config = dict(self.config(), scopes=['control', 'observe'],
                          targets=[dict(host='h', environment='e'), target],
                          windows_message_owner=dict(owner_config=str(owner_config), targets=[target]))
            app = create_app(config, root, identify=lambda request: 'operator', operations=self.operations(root))
            schedule = 'wake_wakes_messages_schedule'
            status = 'wake_wakes_messages_status'
            identifier = str(uuid4())
            request = dict(expected_target=target, message_id=identifier, body='Private fixture message',
                           due_at='2033-05-18T03:33:20.000001Z', expires_at='2033-05-18T03:33:40.000099Z')
            selector = dict(expected_target=target, message_id=identifier)
            async with self.external_client(app, config) as (_, grant, connector):
                broad = await grant('observe control')
                async with connector(broad) as session:
                    names = {tool.name for tool in (await session.list_tools()).tools}
                    self.assertFalse({schedule, status} & names)
                    rejected = await session.call_tool(schedule, request)
                    self.assertTrue(rejected.is_error)
                    self.assertFalse((bridge / 'message-owner.sqlite3').exists())

                exact = await grant('observe control', targets='1')
                async with connector(exact) as session:
                    self.assertTrue({schedule, status} <= {tool.name for tool in (await session.list_tools()).tools})
                    refused = await session.call_tool(schedule, dict(request,
                        expected_target=dict(target, generation='different-generation')))
                    self.assertTrue(refused.is_error)
                    admitted = await session.call_tool(schedule, request)
                    self.assertFalse(admitted.is_error, admitted.structured_content)
                    self.assertEqual(admitted.structured_content['result'], dict(
                        id=identifier, status='waiting_for_database',
                        not_before_micros=2000000000000001, expires_at_micros=2000000020000099))
                    retry = await session.call_tool(schedule, request)
                    self.assertEqual(retry.structured_content, admitted.structured_content)
                    changed = await session.call_tool(schedule, dict(request, expires_at='2033-05-18T04:00:00Z'))
                    self.assertTrue(changed.is_error)
                    found = await session.call_tool(status, selector)
                    self.assertEqual(found.structured_content['result'], admitted.structured_content['result'])
                    self.assertNotIn(request['body'], json.dumps(found.structured_content))

                peer_grant = await grant('observe', targets='1')
                async with connector(peer_grant) as session:
                    hidden = await session.call_tool(status, selector)
                    self.assertEqual(hidden.structured_content['result'], dict(id=identifier, status='not_found'))

            with sqlite3.connect(bridge / 'message-owner.sqlite3') as db:
                raw, = db.execute('SELECT request FROM transfers WHERE direction=\'out\'').fetchone()
                stored = json.loads(raw)
                self.assertEqual(stored['message']['identifier'], identifier)
                self.assertEqual(stored['message']['recipient'], target['conversation_id'])
                self.assertEqual(stored['message']['not_before_micros'], 2000000000000001)
                self.assertEqual(stored['message']['expires_at_micros'], 2000000020000099)
                self.assertRegex(stored['origin'], r'^[0-9a-f]{64}$')

        with tempfile.TemporaryDirectory() as directory:
            asyncio.run(scenario(directory))
