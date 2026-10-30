"""Controller messaging over the existing authenticated Mailbox owner.

Host configuration maps caller subject/client to issued native actor credentials.
Opaque request bindings never establish native session identity. No credential is
copied into an operation record, request, response or controller client.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .a2a_bus import BusStore
from .a2a_identity import RuntimeIdentity, BusError
from .a2a_mailbox import Mailbox
from .controller_operations import ControllerOperations
from .managed_inventory import ManagedInventory, InventoryError


class ControllerMailbox:
    def __init__(self, root, *, mailbox_factory=Mailbox):
        self.root = Path(root)
        self.config_path = self.root / 'controller-messaging.json'
        self.mailbox_factory = mailbox_factory

    def config(self):
        if not self.config_path.is_file() or self.config_path.stat().st_mode & 0o077:
            raise InventoryError('configuration_unavailable', 'private host messaging configuration required')
        data = json.loads(self.config_path.read_text())
        if data.get('version') != 1: raise InventoryError('configuration_unavailable', 'unsupported messaging configuration')
        return data

    def context(self, actor, binding):
        config = self.config()
        mapping = config.get('bindings', {}).get(binding)
        if not isinstance(mapping, dict) or mapping.get('subject') != actor.subject or mapping.get('client_id') != actor.client_id:
            raise InventoryError('unauthorized_target', 'caller has no host-approved native sender binding')
        native = RuntimeIdentity(**mapping['identity'])
        bus = BusStore(Path(mapping['bus_root']))
        authenticated = bus.authenticate(Path(mapping['capability']), native, invoking_cwd=Path(native.cwd))
        digest = hashlib.sha256(json.dumps(mapping, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        return config, self.mailbox_factory(bus), authenticated, digest

    def prepare(self, actor, payload):
        config, mailbox, sender, digest = self.context(actor, payload.get('sender_binding'))
        target = payload.get('expected_target')
        candidates = [row for row in config.get('recipients', []) if row.get('target') == target]
        if len(candidates) != 1: raise InventoryError('stale_target', 'recipient is not an exact host-approved binding')
        native = candidates[0]['identity']
        if native.get('namespace') != target.get('namespace') or native.get('thread_id') != target.get('conversation_id'):
            raise InventoryError('unauthorized_target', 'host mapping native recipient differs from pinned conversation')
        if target.get('host') != config['host'] or target.get('environment') != config['environment']:
            raise InventoryError('unauthorized_target', 'recipient execution environment differs from host authority')
        inventory = ManagedInventory(self.root)
        current = ControllerOperations(inventory, host=config['host'], environment=config['environment']).execute('inventory.list', {})['result']['resources']
        enrolled = {row['managed_agent_id']: row for row in inventory.inspect()['agents']}
        matches = [row for row in current if row['target'] == target
            and enrolled[row['id']]['enrollment'] == 'enrolled'
            and (row['binding_current'] or (payload['queue'] and enrolled[row['id']]['state'] == 'stale'))]
        if len(matches) != 1: raise InventoryError('stale_target', 'recipient generation is absent or replaced')
        if matches[0]['observation']['freshness'] != 'current' and not payload['queue']:
            raise InventoryError('stale_target', 'offline/stale send requires explicit inbox queue policy')
        return dict(payload, _binding_digest=digest)

    def send(self, actor, payload, operation_id, correlation_id):
        prepared = self.prepare(actor, {k: v for k, v in payload.items() if k != '_binding_digest'})
        if prepared['_binding_digest'] != payload['_binding_digest']:
            raise InventoryError('stale_target', 'native sender mapping changed after admission')
        config, mailbox, sender, digest = self.context(actor, payload['sender_binding'])
        recipient = next(row['identity'] for row in config['recipients'] if row['target'] == payload['expected_target'])
        value = mailbox.send(sender, RuntimeIdentity(**recipient), body=payload['body'],
            idempotency_key='controller:' + operation_id, kind='request', ttl=payload['ttl'],
            delivery=payload['delivery'], correlation=correlation_id,
            selector={'controller_operation_id': operation_id, 'target': payload['expected_target']})
        return dict(_pending=True, handle=dict(kind='mailbox', message_id=value['message']['message_id'],
            bus_id=mailbox.bus.bus_id, sender_binding=payload['sender_binding'], binding_digest=digest))

    def _context_record(self, actor, record):
        payload = record['payload']
        config, mailbox, sender, digest = self.context(actor, payload['sender_binding'])
        if digest != payload['_binding_digest']:
            raise InventoryError('stale_target', 'original native sender mapping changed; no identity adoption')
        return mailbox, sender, digest

    def reconcile(self, actor, record):
        mailbox, sender, digest = self._context_record(actor, record)
        cursor = 0
        for _ in range(10):
            page = mailbox.list(sender, outbox=True, cursor=cursor, limit=100)
            messages = page.get('messages', [])
            for message in messages:
                if message.get('idempotency_key') != 'controller:' + record['operation_id']: continue
                if message.get('correlation') != record['correlation_id'] or message.get('selector_observation', {}).get('target') != record['target']:
                    raise InventoryError('idempotency_conflict', 'native owner receipt differs from controller intent')
                if message['body_digest'] != hashlib.sha256(record['payload']['body'].encode()).hexdigest():
                    raise InventoryError('idempotency_conflict', 'native body differs from retained controller intent')
                return dict(kind='mailbox', message_id=message['message_id'], bus_id=mailbox.bus.bus_id,
                    sender_binding=record['payload']['sender_binding'], binding_digest=digest)
            if not page.get('next_cursor'): break
            cursor = page['next_cursor']
        return None

    def poll(self, actor, record):
        mailbox, sender, _ = self._context_record(actor, record)
        handle = record['result']
        if handle['bus_id'] != mailbox.bus.bus_id: raise InventoryError('stale_target', 'original mailbox authority changed')
        values = []
        for reply in mailbox.replies(sender, handle['message_id']):
            if reply.get('correlation') != record['correlation_id'] or reply.get('in_reply_to') != handle['message_id']:
                raise InventoryError('uncorrelated_result', 'reply is not bound to the initiating operation')
            value = mailbox.read(sender, reply['message_id'])
            values.append(dict(reply_id=reply['message_id'], kind=reply['kind'], text=value['body'],
                correlation_id=record['correlation_id'], sender=reply['sender'], peer_content_trust='untrusted'))
        return values

    def cancel(self, actor, record):
        mailbox, sender, _ = self._context_record(actor, record)
        try:
            value = mailbox.cancel(sender, record['result']['message_id'])
            return 'confirmed' if value['message']['state']['admission'] == 'cancelled' else 'uncertain'
        except BusError as error:
            if error.code in ('too_late', 'effect_uncertain', 'not_processable'): return 'uncertain'
            raise
