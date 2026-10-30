"""OAuth resource and stateless JSON MCP transport over common controller reads.

The listener is loopback only; TLS ingress is a separate deployment boundary.
No identity headers are trusted. Every request verifies the current grant.
"""
from __future__ import annotations

import html
import json
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlencode, urlsplit

from .controller_auth import AuthError, SCOPES
from .managed_inventory import InventoryError

TOOLS = {
    'wake_builds_list': ('builds.list', {'type': 'object', 'properties': {'account': {'type': 'string'}}, 'required': ['account'], 'additionalProperties': False}),
    'wake_controller_list': ('inventory.list', {'type': 'object', 'properties': {'query': {'type': 'string'}}, 'additionalProperties': False}),
    'wake_controller_accounts': ('accounts.list', {'type': 'object', 'properties': {}, 'additionalProperties': False}),
    'wake_controller_account_resolve': ('accounts.resolve', {'type': 'object', 'properties': {'selector': {'type': 'string'}, 'expected_target': {'type': 'object'}}, 'required': ['selector'], 'additionalProperties': False}),
    'wake_controller_configuration': ('configuration.explain', {'type': 'object', 'properties': {'selector': {'type': 'string'}, 'expected_target': {'type': 'object'}}, 'required': ['selector'], 'additionalProperties': False}),
    'wake_controller_resolve': ('inventory.resolve', {'type': 'object', 'properties': {'selector': {'type': 'string'}, 'expected_target': {'type': 'object'}}, 'required': ['selector'], 'additionalProperties': False}),
}


# Native-MCP caller identity is not part of the OAuth-MCP argument schema.
from .history_commands import tool_specs as history_specs
for name, spec in history_specs().items():
    properties = {key: value for key, value in spec[3].items() if key != 'caller_thread_id'}
    TOOLS[name] = ('history.' + spec[1], {'type': 'object', 'properties': properties,
        'required': [key for key in spec[4] if key != 'caller_thread_id'], 'additionalProperties': False})
TOOLS.update({
    'wake_hosts_list': ('hosts.list', {'type': 'object', 'properties': {}, 'additionalProperties': False}),
    'wake_hosts_resolve': ('hosts.resolve', {'type': 'object', 'properties': {'host': {'type': 'string'}, 'environment': {'type': 'string'}, 'expected_target': {'type': 'object'}}, 'required': ['host', 'environment'], 'additionalProperties': False}),
    'wake_hosts_route': ('hosts.route', {'type': 'object', 'properties': {'target': {'type': 'object'}, 'operation': {'type': 'string'}, 'arguments': {'type': 'object'}, 'operation_id': {'type': 'string'}, 'idempotency_key': {'type': 'string'}}, 'required': ['target', 'operation', 'arguments', 'operation_id', 'idempotency_key'], 'additionalProperties': False}),
})


def operation_failure(operation, error):
    return {'schema_version': 1, 'operation': operation, 'status': 'failed',
            'error': {'code': error.code, 'message': str(error)}}


def permitted(actor, target):
    return any(all(target.get(key) == value for key, value in scope.items()) for scope in actor.targets)


class ProtectedOperations:
    """Shared API/MCP admission. Binding and client registration confer no grant."""
    # operation: (capability, list collection or None, singleton key).
    # Account/config reads require their own capabilities and an exact account
    # identity grant; inventory observe never authorizes reading native config.
    READ_POLICIES = {
        'hosts.list': ('observe', 'environments', None),
        'hosts.resolve': ('observe', None, 'environment'),
        'hosts.route': ('observe', None, None),
        'history.search': ('history.observe', None, None),
        'history.read': ('history.observe', None, None),
        'history.resume': ('history.resume', None, None),
        'builds.list': ('account.observe', 'builds', None),
        'inventory.list': ('observe', 'resources', None),
        'inventory.resolve': ('observe', None, 'resource'),
        'accounts.list': ('account.observe', 'accounts', None),
        'accounts.resolve': ('account.observe', None, 'account'),
        'configuration.explain': ('configuration.observe', None, 'account'),
    }

    def __init__(self, authority, operations):
        self.authority, self.operations = authority, operations

    def execute(self, token, operation, arguments):
        actor = self.authority.authenticate(token)
        policy = self.READ_POLICIES.get(operation)
        required = policy[0] if policy else {'runtime.input': 'control', 'runtime.recover': 'recovery',
                    'grants.revoke': 'admin'}.get(operation)
        if required is None:
            raise InventoryError('unsupported_operation', 'operation is unsupported')
        if required not in actor.scopes:
            raise AuthError('insufficient_scope')
        if operation.startswith('history.'):
            from .controller_history_authorization import HistoryAuthorization
            if self.operations.inventory is None:
                raise InventoryError('configuration_unavailable', 'host history owner is unavailable')
            result = HistoryAuthorization(self.authority, self.operations.inventory.root,
                host=self.operations.host, environment=self.operations.environment,
                runtime=self.operations.history_runtime, now=self.operations.history_now).execute(token, operation, arguments)
        elif operation == 'hosts.route':
            result = self.operations.execute(operation, arguments, actor=actor,
                authorize=lambda: self.authority.authenticate(token))
        else:
            if policy is None:
                raise InventoryError('unsupported_operation', 'operation is unsupported')
            result = self.operations.execute(operation, arguments)
            def allowed(row):
                if policy[0] == 'observe':
                    return permitted(actor, row['target'])
                fields = {'host', 'environment', 'provider', 'account', 'home', 'home_generation', 'configuration_revision'}
                return any(fields <= set(scope) and all(row['target'].get(key) == val for key, val in scope.items()) for scope in actor.targets)
            if policy[1]:
                result['result'][policy[1]] = [row for row in result['result'][policy[1]] if allowed(row)]
            elif not allowed(result['result'][policy[2]]):
                raise AuthError('insufficient_scope')
        current = self.authority.authenticate(token)
        if current.grant_id != actor.grant_id:
            raise AuthError()
        result['actor'] = dict(subject=actor.subject, principal_kind=actor.principal_kind,
            client_id=actor.client_id, grant_id=actor.grant_id, issuer=actor.issuer,
            resource=actor.resource, scopes=sorted(actor.scopes))
        return result


class ControllerHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    def __init__(self, address, authority, operations, *, consent_secret=None, owner='owner'):
        if address[0] not in ('127.0.0.1', '::1', 'localhost'):
            raise ValueError('controller listener must bind loopback; use authenticated TLS ingress')
        self._slots = threading.BoundedSemaphore(16)
        self.authority = authority
        self.operations = ProtectedOperations(authority, operations)
        self.consent_secret, self.owner = consent_secret, owner
        super().__init__(address, ControllerHandler)

    def process_request(self, request, address):
        request.settimeout(5)
        if not self._slots.acquire(blocking=False):
            request.close()
            return
        try: super().process_request(request, address)
        except BaseException:
            self._slots.release()
            raise

    def process_request_thread(self, request, address):
        try: super().process_request_thread(request, address)
        finally: self._slots.release()


class ControllerHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # Tokens/codes/consent secrets never enter HTTP request logs.

    def reply(self, status, value, headers=None):
        body = json.dumps(value).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(body)))
        for key, val in (headers or {}).items(): self.send_header(key, val)
        self.end_headers(); self.wfile.write(body)

    def fail(self, error):
        code = getattr(error, 'code', 'invalid_request')
        status = 401 if code == 'invalid_token' else 403 if code == 'insufficient_scope' else 400
        headers = {}
        if status == 401:
            headers['WWW-Authenticate'] = 'Bearer resource_metadata="' + self.server.authority.issuer + '/.well-known/oauth-protected-resource"'
        self.reply(status, {'error': code}, headers)

    def do_GET(self):
        path = urlsplit(self.path).path
        auth = self.server.authority
        if path == '/mcp':
            bearer = self.headers.get('Authorization', '')
            try:
                if not bearer.startswith('Bearer '): raise AuthError()
                auth.authenticate(bearer[7:])
            except AuthError as error: return self.fail(error)
            return self.reply(405, {'error': 'streaming_not_supported'}, {'Allow': 'POST'})
        if path == '/.well-known/oauth-authorization-server': return self.reply(200, auth.metadata())
        if path == '/.well-known/oauth-protected-resource': return self.reply(200, auth.protected_metadata())
        if path == '/authorize':
            if self.server.consent_secret is None: return self.reply(503, {'error': 'operator_consent_unconfigured'})
            values = {k: v[0] for k, v in parse_qs(urlsplit(self.path).query).items()}
            # Display the complete requested grant; submission requires the private operator secret.
            fields = ''.join('<input type="hidden" name="' + html.escape(k, quote=True) + '" value="' + html.escape(v, quote=True) + '">' for k, v in values.items())
            body = ('<!doctype html><title>Wake consent</title><h1>Authorize Wake client</h1><pre>' + html.escape(json.dumps(values, indent=2)) + '</pre><p>Enter operator consent secret only after reviewing client, scopes and exact targets.</p><form method="post" action="/authorize">' + fields + '<label>Consent secret <input type="password" name="consent_secret" autocomplete="off"></label><button>Approve requested grant</button></form>').encode()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Security-Policy', "default-src 'none'; form-action 'self'; frame-ancestors 'none'")
            self.send_header('Content-Length', str(len(body))); self.end_headers(); self.wfile.write(body)
            return
        self.reply(404, {'error': 'not_found'})

    def body(self):
        length = int(self.headers.get('Content-Length', '0'))
        if not 0 < length <= 65536: raise AuthError('invalid_request')
        raw = self.rfile.read(length)
        content_type = self.headers.get('Content-Type', '').split(';')[0]
        if content_type == 'application/x-www-form-urlencoded':
            return {k: v[0] for k, v in parse_qs(raw.decode(), keep_blank_values=True).items()}
        if content_type != 'application/json': raise AuthError('invalid_request')
        value = json.loads(raw)
        if not isinstance(value, dict): raise AuthError('invalid_request')
        return value

    def do_POST(self):
        try:
            if any(key.lower().startswith(('x-wake-', 'x-auth', 'x-forwarded-user', 'x-forwarded-subject', 'x-forwarded-email', 'x-forwarded-groups', 'x-user-', 'x-principal-')) or key.lower() in ('remote-user', 'x-remote-user') for key in self.headers):
                raise AuthError('untrusted_identity_header')
            origin = self.headers.get('Origin')
            if origin and origin != self.server.authority.issuer: raise AuthError('invalid_origin')
            path, auth = urlsplit(self.path).path, self.server.authority
            args = self.body()
            if path == '/register': return self.reply(201, auth.register(args))
            if path == '/token': return self.reply(200, auth.token(args))
            if path == '/revoke':
                auth.revoke_token(args.get('token', ''), args.get('client_id'))
                return self.reply(200, {})
            if path == '/authorize':
                secret = args.pop('consent_secret', '')
                if not self.server.consent_secret or not secrets.compare_digest(secret, self.server.consent_secret): raise AuthError('access_denied')
                if args.get('response_type') != 'code' or args.get('code_challenge_method') != 'S256': raise AuthError('invalid_request')
                code = auth.authorize(subject=self.server.owner, principal_kind='owner', client_id=args.get('client_id'), redirect_uri=args.get('redirect_uri'), resource=args.get('resource'), scopes=args.get('scope', '').split(), targets=json.loads(args.get('targets', '[]')), code_challenge=args.get('code_challenge'))
                location = args['redirect_uri'] + ('&' if '?' in args['redirect_uri'] else '?') + urlencode(dict(code=code, state=args.get('state', '')))
                return self.reply(303, {}, {'Location': location})
            bearer = self.headers.get('Authorization', '')
            if not bearer.startswith('Bearer '): raise AuthError()
            token = bearer[7:]
            auth.authenticate(token)
            if path == '/operations':
                try:
                    value = self.server.operations.execute(token, args.get('operation'), args.get('arguments', {}))
                except InventoryError as error:
                    return self.reply(400, operation_failure(args.get('operation'), error))
                return self.reply(200, value)
            if path == '/mcp': return self.mcp(token, args)
            self.reply(404, {'error': 'not_found'})
        except (AuthError, InventoryError) as error: self.fail(error)
        except (ValueError, TypeError, KeyError, AttributeError): self.fail(AuthError('invalid_request'))

    def mcp(self, token, request):
        identifier = request.get('id')
        if request.get('jsonrpc') != '2.0': raise AuthError('invalid_request')
        method, params = request.get('method'), request.get('params', {})
        if method == 'notifications/initialized':
            self.send_response(202); self.send_header('Content-Length', '0'); self.end_headers(); return
        if method == 'initialize':
            result = dict(protocolVersion='2025-03-26', capabilities={'tools': {'listChanged': False}}, serverInfo={'name': 'codex-wake-controller', 'version': '1'})
        elif method == 'ping': result = {}
        elif method == 'tools/list':
            actor = self.server.authority.authenticate(token)
            result = {'tools': [dict(name=name, description='Read scoped controller resource', inputSchema=schema)
                for name, (operation, schema) in TOOLS.items()
                if ProtectedOperations.READ_POLICIES[operation][0] in actor.scopes
                and (operation.startswith('inventory.')
                     or (operation.startswith('hosts.') and self.server.operations.operations.hosts is not None)
                     or (operation.startswith('builds.') and self.server.operations.operations.builds is not None)
                     or (not operation.startswith(('hosts.', 'builds.')) and self.server.operations.operations.accounts is not None))]}
        elif method == 'tools/call':
            name = params.get('name')
            if name not in TOOLS:
                return self.reply(200, dict(jsonrpc='2.0', id=identifier, error={'code': -32602, 'message': 'unsupported tool'}))
            try:
                value = self.server.operations.execute(token, TOOLS[name][0], params.get('arguments', {}))
                result = dict(content=[dict(type='text', text=json.dumps(value))], structuredContent=value, isError=False)
            except InventoryError as error:
                value = operation_failure(TOOLS[name][0], error)
                result = dict(content=[dict(type='text', text=json.dumps(value))], structuredContent=value, isError=True)
        else:
            return self.reply(200, dict(jsonrpc='2.0', id=identifier, error={'code': -32601, 'message': 'method not found'}))
        self.reply(200, dict(jsonrpc='2.0', id=identifier, result=result))
