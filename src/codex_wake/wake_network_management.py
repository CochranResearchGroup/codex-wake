"""Live one-use management requests between a hub and an outbound spoke."""
from collections.abc import Callable
from dataclasses import dataclass
from threading import Condition
from uuid import uuid4

from .controller_auth import AuthError
from .controller_http import ProtectedOperations
from .managed_inventory import InventoryError
from .message_policy import stable_micros
from .unified_connectors import check_action
from .wake_network import _ID, _check

ACTIONS = {
    'network.history.search': ('history.search', {'history.observe'}),
    'network.history.read': ('history.read', {'history.observe', 'content.observe'}),
    'network.tabs.rename': ('tabs.rename', {'control'}),
}
TOOLS = {
    'wake_' + action.replace('.', '_'): (action, {
        'type': 'object', 'additionalProperties': False,
        'required': ['peer_id', 'conversation_id'] + (['name'] if action.endswith('rename') else []),
        'properties': dict(peer_id=_ID, conversation_id=_ID, **(
            {'name': {'type': 'string', 'minLength': 1, 'maxLength': 128}}
            if action.endswith('rename') else {})),
    }) for action in ACTIONS
}
SCHEMAS = dict(TOOLS.values())
_SLOT_LIMIT = 8


@dataclass
class Poll:
    envelope: dict | None = None


@dataclass
class Pending:
    peer: str
    deadline: int
    verify: Callable[[], None]
    claimed: bool = False
    result: dict | None = None


class LiveManagement:
    """Single-process rendezvous. A hub restart discards every live request."""
    def __init__(self, network, *, timeout=8):
        self.network = network
        self.timeout = timeout
        self.ready = Condition()
        self.polls = {}
        self.pending = {}

    def visible(self, actor, action):
        fields = {'host', 'environment', 'peer_id', 'conversation_id'}
        return ACTIONS[action][1] <= actor.scopes and any(
            set(target) == fields and target['host'] == self.network.host
            and target['environment'] == self.network.environment for target in actor.targets)

    def trusted_now(self):
        return stable_micros(self.network.clock(), upper=True)

    def peer(self, peer, authorization):
        with self.network.connect() as db:
            self.network.authorize_peer(db, peer, authorization)

    def submit(self, actor, action, arguments, verify):
        _check(SCHEMAS[action], arguments)
        check_action(actor, action)
        if not ACTIONS[action][1] <= actor.scopes:
            raise AuthError('insufficient_scope')
        peer, recipient = arguments['peer_id'], arguments['conversation_id']
        scope = dict(host=self.network.host, environment=self.network.environment,
                     peer_id=peer, conversation_id=recipient)
        if scope not in actor.targets:
            raise AuthError('insufficient_scope')
        with self.network.connect() as db:
            row = db.execute('SELECT enabled,directory FROM wake_network_peers_v1 WHERE peer_id=%s',
                             (peer,)).fetchone()
        if not row or not any(item['conversation_id'] == recipient for item in row[1]):
            raise AuthError('insufficient_scope')
        now = self.trusted_now()
        if now is None:
            raise InventoryError('trusted_time_unavailable', 'live request needs trusted time')

        def reverify():
            if verify() != actor:
                raise AuthError()

        reverify()
        with self.ready:
            poll = self.polls.get(peer)
            if not row[0] or poll is None or poll.envelope is not None:
                return {'status': 'offline'}
            if len(self.pending) >= _SLOT_LIMIT:
                return {'status': 'capacity'}
            request = str(uuid4())
            deadline = min(now + int(self.timeout * 1_000_000), int(actor.expires_at * 1_000_000))
            if deadline <= now:
                raise AuthError()
            item = Pending(peer, deadline, reverify)
            self.pending[request] = item
            poll.envelope = dict(id=request, action=action, deadline=item.deadline,
                                         conversation_id=recipient, name=arguments.get('name'))
            self.ready.notify_all()
            try:
                self.ready.wait_for(lambda: item.result is not None, timeout=self.timeout)
                response = item.result or {'id': request, 'status': 'uncertain' if item.claimed else 'offline'}
            finally:
                self.pending.pop(request, None)
        reverify()
        return response

    def pull(self, peer, authorization, arguments):
        _check({'type': 'object', 'maxProperties': 0}, arguments)
        self.peer(peer, authorization)
        with self.ready:
            if peer in self.polls:
                return {'status': 'poll_in_progress'}
            if len(self.polls) >= _SLOT_LIMIT:
                return {'status': 'capacity'}
            slot = Poll()
            self.polls[peer] = slot
            try:
                self.ready.wait_for(lambda: slot.envelope is not None, timeout=self.timeout)
                if slot.envelope is None:
                    return {'status': 'idle'}
            finally:
                self.polls.pop(peer, None)
        self.peer(peer, authorization)
        with self.ready:
            item = self.pending.get(slot.envelope['id'])
        if item is None:
            return {'status': 'idle'}
        try:
            item.verify()
        except AuthError:
            return {'status': 'idle'}
        now = self.trusted_now()
        with self.ready:
            item = self.pending.get(slot.envelope['id'])
            if item is None or now is None or now >= item.deadline:
                return {'status': 'idle'}
            item.claimed = True
            return {'status': 'claimed', 'request': slot.envelope}

    def complete(self, peer, authorization, arguments):
        self.peer(peer, authorization)
        _check({'type': 'object', 'required': ['id', 'result'], 'additionalProperties': False,
                'properties': {'id': _ID, 'result': {'type': 'object', 'minProperties': 1}}}, arguments)
        now = self.trusted_now()
        with self.ready:
            item = self.pending.get(arguments['id'])
            if not item or item.peer != peer or not item.claimed or now is None or now >= item.deadline:
                return {'status': 'expired'}
            if item.result is not None:
                return {'status': 'already_completed'}
            item.result = dict(arguments['result'], id=arguments['id'])
            self.ready.notify_all()
            return {'status': 'completed'}



class DeadlineAuthority:
    def __init__(self, authority, clock, deadline, scopes):
        self.authority, self.clock, self.deadline, self.scopes = authority, clock, deadline, scopes

    def __getattr__(self, name):
        return getattr(self.authority, name)

    def authenticate(self, token):
        actor = self.authority.authenticate(token)
        now = stable_micros(self.clock(), upper=True)
        if now is None or now >= self.deadline or not self.scopes <= actor.scopes:
            raise AuthError('insufficient_scope')
        return actor


class SpokeManagement:
    """A local operator binds each network identity to existing controller arguments."""
    def __init__(self, bindings, protected, token, clock):
        self.bindings, self.protected = bindings, protected
        self.token, self.clock = token, clock

    def execute(self, envelope):
        from copy import deepcopy

        action = envelope['action']
        try:
            arguments = deepcopy(self.bindings[envelope['conversation_id']][action])
            operation = ACTIONS[action][0]
        except KeyError:
            return {'status': 'denied'}
        if operation == 'history.search' and not arguments.get('former_tab'):
            return {'status': 'denied'}
        if operation == 'history.read' and arguments.get('thread_id') != envelope['conversation_id']:
            return {'status': 'denied'}
        if action == 'network.tabs.rename':
            identifier = envelope['id']
            arguments.update(name=envelope['name'], _request=dict(
                operation_id=identifier, idempotency_key=identifier, correlation_id=identifier,
                binding='wake-network-live', target=arguments['expected_target']))
        now = stable_micros(self.clock(), upper=True)
        if now is None or now >= envelope['deadline']:
            return {'status': 'expired'}
        try:
            authority = DeadlineAuthority(
                self.protected.authority, self.clock, envelope['deadline'], ACTIONS[action][1])
            protected = ProtectedOperations(authority, self.protected.operations)
            value = protected.execute(self.token, operation, arguments)
            if operation != 'history.search':
                return value
            # One directory identity never grants all aliases of a former name.
            history = value['result']
            identifier = envelope['conversation_id']
            visible = [row for row in history.get('bindings', [])
                       if row.get('conversation_id') == identifier]
            return {'status': 'completed', 'result': {'bindings': visible}}
        except AuthError:
            return {'status': 'denied'}
        except InventoryError as error:
            return {'status': 'failed', 'error': error.code}


def routes(management, verifier, host):
    from functools import partial

    from starlette.routing import Route
    from .wake_network_http import guard

    endpoint = guard(verifier, host)
    return [
        Route('/network/v1/peers/{peer_id}/management/pull', endpoint(management.pull), methods=['POST']),
        Route('/network/v1/peers/{peer_id}/management/complete', endpoint(management.complete), methods=['POST']),
    ] + [
        Route('/network/v1/management/' + action.removeprefix('network.').replace('.', '/'),
              endpoint(partial(_submit, management, action), client=True, reverify=True), methods=['POST'])
        for action in ACTIONS
    ]


def _submit(management, action, actor, arguments, verify):
    return management.submit(actor, action, arguments, verify)


def spoke_tick(request, local):
    """Poll once through a peer-authenticated client. A lost claim is never repulled."""
    answer = request('pull', {})
    if answer['status'] != 'claimed':
        return answer
    envelope = answer['request']
    result = local.execute(envelope)
    return request('complete', {'id': envelope['id'], 'result': result})


def main(argv=None):
    import argparse
    import json
    from pathlib import Path
    from urllib.parse import urlsplit
    from urllib.request import HTTPRedirectHandler, Request, build_opener

    from .a2a_bus import private_path
    from .controller_auth import OAuthAuthority
    from .controller_remote_commands import operations_from_root
    from .native_clock import snapshot
    from .operation_commands import owner as operation_owner

    parser = argparse.ArgumentParser(description='Pull and complete one live Wake network management request')
    parser.add_argument('--config', type=Path, required=True)
    args = parser.parse_args(argv)
    private_path(args.config)
    config = json.loads(args.config.read_text())
    issuer = config['hub'].rstrip('/')
    url = urlsplit(issuer)
    peer = config['peer_id']
    if (url.scheme != 'https' or not url.hostname or url.username or url.path or url.query or url.fragment):
        raise ValueError('fixed HTTPS hub origin required')
    _check(_ID, peer)

    def secret(field):
        path = Path(config[field])
        private_path(path)
        return path.read_text().strip()

    root = Path(config['wake_root'])
    authority = root / 'controller-auth'
    auth_config = json.loads((authority / 'authority.json').read_text())
    auth = OAuthAuthority(authority / 'authority.sqlite', issuer=auth_config['issuer'],
                          resource=auth_config['resource'], on_revoke=operation_owner(root).revoke_grant)
    protected = ProtectedOperations(auth, operations_from_root(root))
    local = SpokeManagement(config['bindings'], protected, secret('controller_token_file'), snapshot)
    credential = secret('peer_token_file')

    class NoRedirect(HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None

    transport = build_opener(NoRedirect())

    def request(operation, value):
        path = f'/network/v1/peers/{peer}/management/{operation}'
        data = json.dumps(value).encode()
        if len(data) > 65536 and operation == 'complete':
            data = json.dumps({'id': value['id'], 'result': {'status': 'failed', 'error': 'response_too_large'}}).encode()
        call = Request(issuer + path, data=data, headers={
            'Authorization': 'Bearer ' + credential, 'Content-Type': 'application/json'})
        with transport.open(call, timeout=12) as response:
            return json.loads(response.read(65537))

    print(json.dumps(spoke_tick(request, local)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
