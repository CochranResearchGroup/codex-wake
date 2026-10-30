"""OAuth history admission before source access, including per-step revocation."""
from pathlib import Path
import os
import socket

from codex_profiles.config import load_settings
from .controller_accounts import ControllerAccounts
from .controller_auth import AuthError
from .controller_history import ControllerHistory, ManagedHistoryResume
from .managed_inventory import InventoryError
from .session_permissions import PermissionStore, Principal

_ACCOUNT_FIELDS = {'host', 'environment', 'provider', 'account', 'home', 'home_generation', 'configuration_revision'}
_HISTORY_FIELDS = {'conversation_id', 'rollout_revision'}


class HistoryAuthorization:
    def __init__(self, authority, root, *, host=None, environment=None, runtime=None, now=None):
        self.authority, self.root = authority, Path(root)
        self.host = host or socket.gethostname()
        self.environment = environment or os.environ.get('WSL_DISTRO_NAME') or os.name
        self.runtime, self.now = runtime, now

    def execute(self, token, operation, arguments):
        if operation not in ('history.search', 'history.read', 'history.resume'):
            raise InventoryError('unsupported_operation', 'unsupported history operation')
        if not isinstance(arguments, dict):
            raise InventoryError('invalid_argument', 'history arguments must be an object')
        capability = 'history.resume' if operation == 'history.resume' else 'history.observe'
        initial = self.authority.authenticate(token)
        path = self.root / 'controller-accounts.toml'
        settings = load_settings(path)
        def admission():
            actor = self.authority.authenticate(token)
            if actor.grant_id != initial.grant_id or actor.subject != initial.subject or capability not in actor.scopes:
                raise AuthError('insufficient_scope')
            accounts = ControllerAccounts(path, host=self.host, environment=self.environment).execute('accounts.list', {})['accounts']
            granted = {}
            for account in accounts:
                scopes = [scope for scope in actor.targets if _ACCOUNT_FIELDS <= set(scope)
                          and set(scope) <= _ACCOUNT_FIELDS | _HISTORY_FIELDS
                          and all(account['target'].get(key) == scope[key] for key in _ACCOUNT_FIELDS)]
                if operation == 'history.search':
                    # Account search requires an account grant, not a grant to
                    # one conversation that would open unrelated rollouts.
                    scopes = [scope for scope in scopes if not set(scope) & _HISTORY_FIELDS]
                else:
                    scopes = [scope for scope in scopes if scope.get('conversation_id', arguments.get('thread_id')) == arguments.get('thread_id')]
                    expected = arguments.get('expected_target')
                    if expected is not None:
                        scopes = [scope for scope in scopes if isinstance(expected, dict)
                                  and all(expected.get(key) == value for key, value in scope.items())]
                    else:
                        scopes = [scope for scope in scopes if 'rollout_revision' not in scope]
                if scopes:
                    granted[account['id']] = account
            if not granted:
                raise AuthError('insufficient_scope')
            if operation == 'history.search':
                selected = arguments.get('owners', sorted(granted))
                if not isinstance(selected, list) or any(not isinstance(name, str) for name in selected):
                    raise InventoryError('invalid_argument', 'owners must be an account list')
                owners = {settings.resolve_profile_name(name) for name in selected}
            else:
                name = arguments.get('owner')
                if not isinstance(name, str):
                    raise InventoryError('invalid_argument', 'history owner is required')
                owners = {settings.resolve_profile_name(name)}
            if not owners <= set(granted):
                raise AuthError('insufficient_scope')
            if operation == 'history.resume':
                action = 'resume.self' if actor.subject == arguments.get('thread_id') else 'resume.recover'
                store = PermissionStore(self.root)
                delegation = store._read()['policy'].get('delegations', {}).get(actor.subject, {}) if store.active() else {}
                if action not in delegation.get('actions', []) or arguments.get('thread_id') not in delegation.get('sessions', []):
                    raise AuthError('insufficient_scope')
            return actor, sorted(owners)
        actor, owners = admission()
        def guard(unused_operation, unused_arguments):
            admission()
        resume = ManagedHistoryResume(self.root, Principal(actor.subject, 'controller'),
            runtime=self.runtime, now=self.now) if operation == 'history.resume' else None
        owner = ControllerHistory(path, root=self.root, host=self.host, environment=self.environment,
            authorized_accounts=owners, resume_owner=resume, authorization_guard=guard)
        result = owner.execute(operation, arguments)
        # A revoked caller cannot receive a newly read private result.
        admission()
        status = 'held' if operation == 'history.resume' and result['resume']['status'] != 'resumed' else 'completed'
        return dict(schema_version=1, operation=operation, status=status, result=result,
            actor=dict(subject=actor.subject, principal_kind=actor.principal_kind, client_id=actor.client_id,
                grant_id=actor.grant_id, issuer=actor.issuer, resource=actor.resource, scopes=sorted(actor.scopes)))
