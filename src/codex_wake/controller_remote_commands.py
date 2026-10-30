"""Installed, disposable controller OAuth listener and authenticated CLI client."""
from __future__ import annotations

import json
import os
import secrets
import socket
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from .controller_auth import OAuthAuthority
from .controller_http import ControllerHTTPServer
from .controller_operations import ControllerOperations
from .managed_inventory import ManagedInventory


def register(commands):
    init = commands.add_parser('auth-configure', help='create private local OAuth authority; no production activation')
    init.add_argument('--issuer', required=True)
    init.add_argument('--resource', required=True)
    init.add_argument('--owner', required=True)
    serve = commands.add_parser('serve', help='serve OAuth API/MCP on loopback')
    serve.add_argument('--port', type=int, default=8768)
    approve = commands.add_parser('authorize-client', help='local operator approval of a named owner/service grant')
    approve.add_argument('--client-id', required=True)
    approve.add_argument('--redirect-uri', required=True)
    approve.add_argument('--subject', required=True)
    approve.add_argument('--principal-kind', choices=['owner', 'service'], required=True)
    approve.add_argument('--scope', action='append', required=True)
    approve.add_argument('--targets', type=json.loads, required=True)
    approve.add_argument('--code-challenge', required=True)
    revoke = commands.add_parser('revoke-grant', help='revoke one grant; read-only operations own no active work')
    revoke.add_argument('grant_id')
    remote = commands.add_parser('remote', help='perform authenticated direct controller operation')
    remote.add_argument('--endpoint', required=True)
    remote.add_argument('--token-file', type=Path, required=True)
    remote.add_argument('operation', choices=['tabs.list','tabs.show','tabs.preview','tabs.apply','tabs.undo','tabs.capture','tabs.input', 'inventory.list', 'inventory.resolve', 'accounts.list', 'accounts.resolve', 'configuration.explain', 'builds.list', 'builds.launch', 'builds.stage', 'builds.select', 'builds.rollback', 'hosts.list', 'hosts.resolve', 'hosts.route', 'history.search', 'history.read', 'history.resume', 'operations.send', 'operations.result', 'operations.wait', 'operations.stream', 'operations.cancel', 'operations.rebind', 'migration.preview', 'migration.apply', 'migration.rollback', 'flows.propose', 'flows.publish', 'flows.definition', 'flows.start', 'flows.inspect', 'flows.advance', 'flows.reconcile', 'flows.cancel', 'health.observe', 'sessions.capabilities', 'sessions.create', 'sessions.prompt', 'sessions.wait', 'sessions.cancel', 'sessions.checkpoint', 'sessions.fork'])
    remote.add_argument('--arguments', type=json.loads, default={})


def private_write(path, text):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as stream: stream.write(text)


def command(args):
    if args.controller_command == 'remote':
        # The token file is private caller OAuth, never a provider credential.
        from urllib.parse import urlsplit
        endpoint = urlsplit(args.endpoint)
        if endpoint.scheme != 'https' and not (endpoint.scheme == 'http' and endpoint.hostname in ('127.0.0.1', '::1', 'localhost')):
            raise ValueError('HTTPS endpoint required except loopback fixtures')
        if args.token_file.stat().st_mode & 0o077: raise ValueError('token file must be private')
        request = Request(args.endpoint.rstrip('/') + '/operations', data=json.dumps(dict(operation=args.operation, arguments=args.arguments)).encode(),
            headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + args.token_file.read_text().strip()})
        # Bearer credentials must never follow redirects to a different origin.
        from urllib.request import HTTPRedirectHandler, build_opener
        class NoRedirect(HTTPRedirectHandler):
            def redirect_request(self, *a, **kw): return None
        try:
            with build_opener(NoRedirect).open(request, timeout=35) as response: value = json.load(response)
        except HTTPError as error:
            value = json.load(error)
            print(json.dumps(value, sort_keys=True)); return 2
        print(json.dumps(value, sort_keys=True)); return 0
    if args.wake_root is None: raise ValueError('host Wake root is required')
    root = Path(args.wake_root) / 'controller-auth'
    config_path = root / 'authority.json'
    if args.controller_command == 'auth-configure':
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        if config_path.exists(): raise ValueError('authority already configured')
        config = dict(issuer=args.issuer, resource=args.resource, owner=args.owner)
        OAuthAuthority(root / 'authority.sqlite', issuer=args.issuer, resource=args.resource)
        private_write(root / 'consent.secret', secrets.token_urlsafe(32))
        private_write(config_path, json.dumps(config))
        print(json.dumps(dict(status='configured', authority=str(config_path), consent_secret_file=str(root / 'consent.secret'), activated=False)))
        return 0
    config = json.loads(config_path.read_text())
    from .operation_commands import owner as operation_owner
    auth = OAuthAuthority(root / 'authority.sqlite', issuer=config['issuer'], resource=config['resource'],
        on_revoke=operation_owner(args.wake_root).revoke_grant)
    if args.controller_command == 'authorize-client':
        code = auth.authorize(subject=args.subject, principal_kind=args.principal_kind,
            client_id=args.client_id, redirect_uri=args.redirect_uri, resource=auth.resource,
            scopes=args.scope, targets=args.targets, code_challenge=args.code_challenge)
        print(json.dumps({'code': code, 'expires_in': 120})); return 0
    if args.controller_command == 'revoke-grant':
        print(json.dumps(auth.revoke_grant(args.grant_id), sort_keys=True)); return 0
    host, environment = socket.gethostname(), os.environ.get('WSL_DISTRO_NAME') or os.name
    account_config = Path(args.wake_root) / 'controller-accounts.toml'
    from .host_commands import owner as host_owner
    options = {'hosts': host_owner(args.wake_root)}
    if account_config.is_file():
        # The account owner is delivered by ticket395; no caller-selected path.
        from .controller_accounts import ControllerAccounts
        options['accounts'] = ControllerAccounts(account_config, host=host, environment=environment)
    if account_config.is_file():
        import tomllib
        if 'builds' in tomllib.loads(account_config.read_text()):
            from .build_commands import owner_from_root
            options['builds'] = owner_from_root(args.wake_root)
    if account_config.is_file() and 'migration' in tomllib.loads(account_config.read_text()):
        from .migration_commands import owner_from_root as migration_owner
        options['migration'] = migration_owner(args.wake_root)
    if (Path(args.wake_root)/'controller-tabs.json').is_file():
        from .controller_tabs import controller_tabs_from_root
        options['tabs'] = controller_tabs_from_root(args.wake_root)
    service = ControllerOperations(ManagedInventory(Path(args.wake_root)), host=host, environment=environment, **options)
    server = ControllerHTTPServer(('127.0.0.1', args.port), auth, service,
        consent_secret=(root / 'consent.secret').read_text(), owner=config['owner'])
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()
    return 0
