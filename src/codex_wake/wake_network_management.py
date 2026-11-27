"""Live one-use management requests between a hub and an outbound spoke."""
from dataclasses import dataclass
from threading import Condition
from time import monotonic
from uuid import uuid4

from .controller_auth import AuthError
from .managed_inventory import InventoryError
from .message_policy import stable_micros
from .unified_connectors import check_action, permits
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


@dataclass
class Poll:
    envelope: dict | None = None


@dataclass
class Pending:
    peer: str
    deadline: int
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

    def trusted_now(self):
        return stable_micros(self.network.clock(), upper=True)

    def peer(self, peer, authorization):
        with self.network.connect() as db:
            self.network.authorize_peer(db, peer, authorization)

    def submit(self, actor, action, arguments):
        _check(SCHEMAS[action], arguments)
        check_action(actor, action)
        if not ACTIONS[action][1] <= actor.scopes:
            raise AuthError('insufficient_scope')
        peer, recipient = arguments['peer_id'], arguments['conversation_id']
        if not permits(actor, dict(host=self.network.host, environment=self.network.environment,
                                   peer_id=peer, conversation_id=recipient)):
            raise AuthError('insufficient_scope')
        now = self.trusted_now()
        if now is None:
            raise InventoryError('trusted_time_unavailable', 'live request needs trusted time')
        with self.network.connect() as db:
            row = db.execute('SELECT enabled,directory FROM wake_network_peers_v1 WHERE peer_id=%s',
                             (peer,)).fetchone()
        if not row or not any(item['conversation_id'] == recipient for item in row[1]):
            raise AuthError('insufficient_scope')
        with self.ready:
            polls = self.polls.get(peer, [])
            if not row[0] or not polls:
                return {'status': 'offline'}
            request = str(uuid4())
            item = Pending(peer, now + int(self.timeout * 1_000_000))
            self.pending[request] = item
            polls.pop(0).envelope = dict(id=request, action=action, deadline=item.deadline,
                                         conversation_id=recipient, name=arguments.get('name'))
            self.ready.notify_all()
            try:
                self.ready.wait_for(lambda: item.result is not None, timeout=self.timeout)
                return item.result or {'id': request, 'status': 'uncertain' if item.claimed else 'offline'}
            finally:
                self.pending.pop(request, None)

    def pull(self, peer, authorization, arguments):
        _check({'type': 'object', 'maxProperties': 0}, arguments)
        self.peer(peer, authorization)
        with self.ready:
            if self.polls.get(peer):
                return {'status': 'poll_in_progress'}
            slot = Poll()
            self.polls[peer] = [slot]
            try:
                self.ready.wait_for(lambda: slot.envelope is not None, timeout=self.timeout)
                if slot.envelope is None:
                    return {'status': 'idle'}
            finally:
                self.polls.pop(peer, None)
        self.peer(peer, authorization)
        with self.ready:
            item = self.pending.get(slot.envelope['id'])
            now = self.trusted_now()
            if item is None or now is None or now >= item.deadline:
                return {'status': 'idle'}
            item.claimed = True
            return {'status': 'claimed', 'request': slot.envelope}

    def complete(self, peer, authorization, arguments):
        self.peer(peer, authorization)
        _check({'type': 'object', 'required': ['id', 'result'], 'additionalProperties': False,
                'properties': {'id': _ID, 'result': {'type': 'object', 'minProperties': 1}}}, arguments)
        with self.ready:
            item = self.pending.get(arguments['id'])
            now = self.trusted_now()
            if not item or item.peer != peer or not item.claimed or now is None or now >= item.deadline:
                return {'status': 'expired'}
            if item.result is not None:
                return {'status': 'already_completed'}
            item.result = dict(arguments['result'], id=arguments['id'])
            self.ready.notify_all()
            return {'status': 'completed'}
