"""OAuth Streamable HTTP transport; the protected controller owns every effect."""
from contextlib import asynccontextmanager
from pathlib import Path
from functools import partial
import json

import anyio
from mcp import types
from mcp.server.auth.middleware.auth_context import get_access_token
from urllib.parse import urlsplit

from mcp.server.auth.middleware.auth_context import AuthContextMiddleware
from mcp.server.auth.middleware.bearer_auth import BearerAuthBackend, RequireAuthMiddleware
from mcp.server.auth.provider import AccessToken
from mcp.server.lowlevel import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from mcp.server.transport_security import TransportSecuritySettings
from pydantic import AnyHttpUrl
from starlette.applications import Starlette
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.responses import JSONResponse
from starlette.routing import Route

from . import __version__
from .controller_auth import AuthError, OAuthAuthority, SCOPES
from .external_connector_consent import BrowserConsent


_OPERATION_CONTROLS = {'operations.send', 'operations.cancel', 'operations.rebind'}
_OPERATION_METADATA = {
    'operation', 'operation_id', 'idempotency_key', 'correlation_id', 'binding', 'original_binding',
    'target', 'phase', 'execution', 'acceptance', 'delivery', 'cancellation', 'reason',
    'admitted_at', 'updated_at',
}
_OPERATION_RECEIPT = {'kind', 'message_id', 'receipt_id', 'bus_id', 'job_id', 'turn_id'}


def _check_content_scope(actor, operation):
    from .unified_connectors import delegated_content_scope

    scope = delegated_content_scope(operation)
    if scope is not None and scope not in actor.scopes:
        raise AuthError('insufficient_scope')


def _control_arguments(operation, arguments, actor):
    if operation == 'operations.send' and 'content.observe' not in actor.scopes:
        # Core callers still default to waiting. External control alone may
        # admit a request and receive its receipt without reading its response.
        if arguments.get('response_requested', False) is not False or 'wait_timeout' in arguments:
            raise AuthError('insufficient_scope')
        return dict(arguments, response_requested=False)
    return arguments


def _control_result(operation, value, actor):
    if operation not in _OPERATION_CONTROLS or 'content.observe' in actor.scopes:
        return value
    envelope = value.get('result')
    record = envelope.get('operation') if isinstance(envelope, dict) else None
    if not isinstance(record, dict):
        return value
    # A replay or cancellation can read an operation that already retained
    # an answer. Reconstruct the metadata receipt instead of returning it.
    visible = {key: record[key] for key in _OPERATION_METADATA if key in record}
    handle = record.get('result')
    if isinstance(handle, dict):
        visible['result'] = {key: handle[key] for key in _OPERATION_RECEIPT
                             if isinstance(handle.get(key), str)}
    return {**value, 'result': {'operation': visible}}


class ConnectorVerifier:
    def __init__(self, authority, config):
        self.authority, self.config = authority, config

    def actor(self, token):
        actor = self.authority.authenticate(token)
        if actor.subject != self.config['owner'] or not actor.scopes <= set(self.config['scopes']):
            raise AuthError()
        if any(not any(all(target.get(key)==value for key,value in allowed.items())
                       for allowed in self.config['targets']) for target in actor.targets):
            raise AuthError()
        from .external_consent_delegation import check_grant
        check_grant(self.authority,self.config,actor.grant_id)
        return actor

    async def verify_token(self, token):
        try:
            actor = self.actor(token)
            return AccessToken(token=token, client_id=actor.client_id, subject=actor.subject,
                               scopes=sorted(actor.scopes), expires_at=int(actor.expires_at),
                               resource=actor.resource)
        except AuthError:
            return None


def create_app(config, root, *, identify=None, operations=None):
    """Fixed host policy and owner identity; no request-selected executable/root."""
    validate_config(config)
    issuer = config['issuer'].rstrip('/')
    url = urlsplit(issuer)
    root = Path(root)
    directory = root / 'external-oauth'
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    from .a2a_bus import private_path
    private_path(directory,directory=True)
    if (directory/'authority.sqlite').exists() or (directory/'authority.sqlite').is_symlink():
        private_path(directory/'authority.sqlite')
    from .operation_commands import owner as operation_owner
    authority = OAuthAuthority(directory / 'authority.sqlite', issuer=issuer, resource=issuer + '/mcp',
                               on_revoke=operation_owner(root).revoke_grant)
    if operations is None:
        from .controller_remote_commands import operations_from_root
        operations = operations_from_root(root)
    from .controller_http import ProtectedOperations, TOOLS, operation_failure, describe_operation
    from .unified_contract import canonical, tool_name
    if operations.host != config['host'] or operations.environment != config['environment']:
        raise ValueError('connector policy does not match this host owner')
    from .unified_connectors import check_action, delegated_content_scope
    from .mcp_server import SPECS
    protected = ProtectedOperations(authority, operations)
    verifier = ConnectorVerifier(authority, config)
    consent = BrowserConsent(authority, config, identify)
    entries = {tool_name(canonical(operation)): (operation, schema) for operation, schema in TOOLS.values()}
    network = management = None
    network_messages = None
    network_message_operations = {}
    network_message_policies = {}
    from .wake_network_catalog import CATALOG, EXECUTE, TOOLS_PUBLIC
    management_catalog = set()
    if 'wake_network' in config:
        from .wake_network import WakeNetwork, TOOLS as network_tools
        network = WakeNetwork(config['wake_network'], operations.host, operations.environment)
        entries.update(network_tools)
        from .wake_network_management import ACTIONS as management_actions, LiveManagement, TOOLS as management_tools
        management = LiveManagement(network)
        entries.update(management_tools)
        entries.update(TOOLS_PUBLIC)
        management_catalog = {CATALOG, EXECUTE}
        from .wake_network_messages import NetworkMessages, POLICIES, SEND, STATUS, TOOLS as network_message_tools
        network_messages = NetworkMessages(network)
        network_message_operations = {SEND: network_messages.client_send, STATUS: network_messages.client_status}
        network_message_policies = POLICIES
        entries.update(network_message_tools)
    schedules = None
    if 'windows_message_owner' in config:
        from .external_owner_schedules import OwnerSchedules, TOOLS as owner_schedule_tools
        schedules = OwnerSchedules(config['windows_message_owner'], operations.host, operations.environment)
        entries.update(owner_schedule_tools)

    def current_actor():
        token = get_access_token()
        if token is None: raise AuthError()
        actor = verifier.actor(token.token)
        return token.token, actor

    async def list_tools(context, params):
        unused, actor = current_actor()
        tools = []
        for name, (operation, schema) in sorted(entries.items()):
            try:
                check_action(actor, operation)
                _check_content_scope(actor, operation)
                policy = schedules.policy(operation) if schedules is not None else None
                if operation in network_message_policies:
                    policy, description, readonly = network_message_policies[operation]
                    if policy not in actor.scopes or not any(target.get('peer_id') for target in actor.targets):
                        continue
                elif network is not None and operation == 'network.recipients':
                    policy, description, readonly = 'observe', 'Find authorized Wake network recipients.', True
                    if policy not in actor.scopes:
                        continue
                elif operation in management_catalog:
                    if not management.has_target(actor):
                        continue
                    policy = None
                    readonly = operation == CATALOG
                    description = ('List the exact peer’s authorized live controller argument contracts.'
                                   if readonly else 'Execute an operation on the exact peer using its current contract.')
                elif management is not None and operation in management_actions:
                    controller_operation = management_actions[operation][0]
                    if not management.visible(actor, operation):
                        continue
                    policy = 'history.observe' if controller_operation.startswith('history.') else 'control'
                    description = 'Run one live authorized operation on the owning Wake peer: ' + controller_operation
                    readonly = controller_operation.startswith('history.')
                elif policy:
                    if not schedules.visible(actor, operation):
                        continue
                    from .external_owner_schedules import DESCRIPTIONS, STATUS
                    description, readonly = DESCRIPTIONS[operation], operation == STATUS
                else:
                    policy = ProtectedOperations.READ_POLICIES[operation][0]
                    if policy not in actor.scopes:
                        continue
                    description = describe_operation(operation)
                    readonly = SPECS.get(name, (None,) * 6)[-1] is True
                    if operation == 'operations.send':
                        description += ' Waiting for its reply requires content.observe. Control-only calls receive a metadata receipt.'
            except AuthError:
                continue
            scopes = sorted(set(filter(None, (policy, delegated_content_scope(operation)))))
            if management is not None and operation in management_actions:
                scopes = sorted(management_actions[operation][1])
            tools.append(types.Tool(name=name, description=description, input_schema=schema,
                annotations=types.ToolAnnotations(read_only_hint=readonly,destructive_hint=not readonly,idempotent_hint=readonly or operation == 'network.messages.send',open_world_hint=True),
                meta={'securitySchemes': [{'type':'oauth2', 'scopes':scopes}]}))
        return types.ListToolsResult(tools=tools)

    async def call_tool(context, params):
        try:
            token, actor = current_actor()
            if params.name not in entries: raise AuthError('insufficient_scope')
            operation = entries[params.name][0]
            _check_content_scope(actor, operation)
            arguments = _control_arguments(operation, params.arguments or {}, actor)
            if operation in network_message_operations:
                dispatch = partial(network_message_operations[operation], actor, arguments)
            elif network is not None and operation == 'network.recipients':
                dispatch = partial(network.discover, actor, arguments)
            elif operation == CATALOG and operation in management_catalog:
                dispatch = partial(management.list_catalog, actor, arguments)
            elif operation == EXECUTE and operation in management_catalog:
                dispatch = partial(management.execute_catalog, actor, arguments, partial(verifier.actor, token))
            elif management is not None and operation in management_actions:
                dispatch = partial(management.submit, actor, operation, arguments, partial(verifier.actor, token))
            elif schedules is not None and schedules.policy(operation):
                dispatch = partial(schedules.execute, verifier.actor, token, operation, arguments)
            else:
                dispatch = partial(protected.execute, token, operation, arguments)
            value = await anyio.to_thread.run_sync(dispatch)
            value = _control_result(operation, value, verifier.actor(token))
            failed = value.get('status') == 'failed'
        except AuthError as error:
            value, failed = {'error': error.code}, True
        except InventoryError as error:
            value, failed = operation_failure(entries[params.name][0], error), True
        return types.CallToolResult(content=[types.TextContent(type='text', text=json.dumps(value))],
                                    structured_content=value, is_error=failed)

    from .managed_inventory import InventoryError
    server = Server('codex-wake', version=__version__, on_list_tools=list_tools, on_call_tool=call_tool)
    manager = StreamableHTTPSessionManager(server, json_response=True, stateless=True,
        max_request_body_size=65536, max_sessions=64,
        security_settings=TransportSecuritySettings(enable_dns_rebinding_protection=True,
            allowed_hosts=[url.netloc], allowed_origins=[issuer]))

    @asynccontextmanager
    async def lifespan(app):
        if network is not None:
            await anyio.to_thread.run_sync(network.initialize)
        if network_messages is not None:
            await anyio.to_thread.run_sync(network_messages.initialize)
        async with manager.run():
            yield

    async def metadata(request):
        value = authority.metadata() if request.url.path.endswith('oauth-authorization-server') else authority.protected_metadata()
        value['scopes_supported'] = sorted(config['scopes'])
        if request.url.path.endswith('oauth-authorization-server'):
            value['authorization_response_iss_parameter_supported'] = True
        return JSONResponse(value, headers={'Cache-Control': 'no-store'})

    mcp = RequireAuthMiddleware(manager.handle_request, required_scopes=[],
        resource_metadata_url=AnyHttpUrl(issuer + '/.well-known/oauth-protected-resource/mcp'))
    mcp = AuthContextMiddleware(mcp)
    mcp = AuthenticationMiddleware(mcp, backend=BearerAuthBackend(
        verifier, resource_server_url=AnyHttpUrl(issuer + '/mcp')))
    def guarded(handler):
        async def endpoint(request):
            try:
                if request.headers.get('host','').lower() != url.netloc.lower():
                    raise AuthError('invalid_request')
                return await handler(request)
            except AuthError as error:
                status = 503 if error.code == 'identity_provider_unavailable' else 429 if error.code == 'rate_limited' else 403 if error.code in ('access_denied','invalid_origin') else 400
                return JSONResponse({'error': error.code}, status_code=status, headers={'Cache-Control': 'no-store'})
            except (ValueError, TypeError, KeyError):
                return JSONResponse({'error': 'invalid_request'}, status_code=400, headers={'Cache-Control': 'no-store'})
        return endpoint

    network_routes = []
    if network is not None:
        from .wake_network_http import routes
        network_routes = routes(network, verifier, url.netloc)
        from .wake_network_management import routes as management_routes
        network_routes += management_routes(management, verifier, url.netloc)
        from .wake_network_messages_http import message_routes
        network_routes += message_routes(network_messages, verifier, url.netloc)
    return Starlette(routes=network_routes + [Route('/register', guarded(consent.register), methods=['POST']),
        Route('/token', guarded(consent.token), methods=['POST']),
        Route('/revoke', guarded(consent.revoke), methods=['POST']),
        Route('/authorize', guarded(consent.authorize), methods=['GET','POST']),
        Route('/mcp', mcp, methods=['GET','POST','DELETE']),
        Route('/.well-known/oauth-protected-resource', guarded(metadata)),
        Route('/.well-known/oauth-protected-resource/mcp', guarded(metadata)),
        Route('/.well-known/oauth-authorization-server', guarded(metadata))], lifespan=lifespan)


def load_config(path):
    """Load only an operator-owned private deployment policy."""
    import os
    import stat
    path = Path(path)
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ValueError('connector policy must be an owner-private regular file')
    value = json.loads(path.read_text())
    validate_config(value)
    if not Path(value['wake_root']).is_absolute() or type(value['port']) is not int or not 1024 <= value['port'] <= 65535:
        raise ValueError('fixed absolute Wake root and unprivileged port required')
    return value


def validate_config(config):
    from .unified_connectors import intersect_targets
    issuer = config['issuer'].rstrip('/')
    url = urlsplit(issuer)
    if url.scheme != 'https' or url.path or url.query or url.fragment or url.username or not url.hostname:
        raise ValueError('canonical HTTPS issuer without path required')
    if not isinstance(config['owner'], str) or not config['owner'] or not isinstance(config['scopes'],list) or not config['scopes'] or not set(config['scopes']) <= SCOPES:
        raise ValueError('explicit owner and permitted scopes required')
    if type(config['grant_seconds']) is not int or not 1 <= config['grant_seconds'] <= 2592000:
        raise ValueError('explicit bounded grant lifetime required')
    targets = config['targets']
    if not isinstance(targets,list) or not 1 <= len(targets) <= 64 or any(not isinstance(t,dict) or t.get('host') != config['host'] or t.get('environment') != config['environment'] for t in targets):
        raise ValueError('explicit host-owned target policy required')
    intersect_targets(targets,targets)
    if 'wake_network' in config:
        from .wake_network import validate
        validate(config['wake_network'])
    if 'windows_message_owner' in config:
        from .external_owner_schedules import validate
        validate(config['windows_message_owner'], config['host'], config['environment'])
    from .external_consent_delegation import validate_delegations
    validate_delegations(config)
    redirects = config['redirect_uris']
    if not isinstance(redirects,list) or not 1 <= len(redirects) <= 10:
        raise ValueError('exact client redirect allowlist required')
    for redirect in redirects:
        u = urlsplit(redirect)
        if not u.netloc or u.fragment or u.username or u.password or any(ord(c)<=32 or ord(c)==127 for c in redirect) or not (u.scheme=='https' or u.scheme=='http' and u.hostname in ('127.0.0.1','::1','localhost')):
            raise ValueError('invalid exact client redirect')
    u = urlsplit(config['authelia_url'])
    if u.scheme != 'http' or u.hostname not in ('127.0.0.1','::1') or u.username or u.password or u.query or u.fragment or u.path != '/api/authz/forward-auth':
        raise ValueError('fixed loopback Authelia verifier required')
    if config.get('login_url'):
        u = urlsplit(config['login_url'])
        if u.scheme != 'https' or not u.hostname or u.username or u.password or u.query or u.fragment:
            raise ValueError('fixed HTTPS sign-in portal required')


def serve(path):
    import uvicorn
    config = load_config(path)
    app = create_app(config, Path(config['wake_root']))
    uvicorn.run(app, host='127.0.0.1', port=config['port'], access_log=False,
                proxy_headers=False, server_header=False, log_level='warning',
                limit_concurrency=32, timeout_keep_alive=5, timeout_graceful_shutdown=30)
    return 0
