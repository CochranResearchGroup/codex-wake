"""Outbound HTTPS Wake owner worker with a persistent local effect journal."""
from __future__ import annotations

import argparse
from contextlib import closing
from dataclasses import replace
import json
import os
from pathlib import Path
import re
import sqlite3
import ssl
import sys
import time
from urllib import error, parse, request
from uuid import uuid4

from .message_delivery import DeliveryReceipt, Message, PostgresMessages, deliver
from .message_handoff import MessageHandoff
from .message_owner import _driver, _object, _private
from .message_policy import recipient_policy
from .native_clock import NoRedirect, snapshot
from .wake_network import _IDENTIFIER, _check
from .wake_network_messages import _PEER_SEND, _RECEIPT


_FINAL = {'submitted', 'uncertain', 'expired', 'bounced'}
_MESSAGE_REFUSALS = {'message_conflict', 'invalid_argument', 'unknown_recipient', 'insufficient_scope', 'restore_held'}


class ExchangeUnavailable(OSError):
    pass


class PeerHTTPS:
    def __init__(self, origin, peer, credential_file, *, ca_file=None):
        url = parse.urlsplit(origin)
        self.credential_file = credential_file
        if (url.scheme != 'https' or not url.hostname or url.username or url.password
                or url.path not in ('', '/') or url.query or url.fragment
                or not re.fullmatch(_IDENTIFIER, peer)):
            raise ValueError('explicit HTTPS Wake peer and private credential required')
        context = ssl.create_default_context(cafile=ca_file)
        self.opener = request.build_opener(request.ProxyHandler({}), NoRedirect(),
                                           request.HTTPSHandler(context=context))
        self.origin = origin.rstrip('/') + '/network/v1/peers/' + parse.quote(peer, safe='')
    def _authorization(self):
        try:
            with _private(self.credential_file).open(encoding='utf-8') as stream:
                raw = stream.read(258)
            secret = raw.removesuffix('\n')
            if len(raw) > 257 or not re.fullmatch(r'[A-Za-z0-9_-]{32,256}', secret):
                raise ValueError('invalid peer credential')
        except (OSError, ValueError):
            raise ExchangeUnavailable('peer_credential_unavailable') from None
        return 'Bearer ' + secret

    def __call__(self, verb, value):
        suffix = '/directory' if verb == 'directory' else '/messages/' + verb
        body = json.dumps(value, ensure_ascii=False).encode()
        req = request.Request(self.origin + suffix, data=body,
            headers={'Authorization': self._authorization(), 'Content-Type': 'application/json'},
            method='PUT' if verb == 'directory' else 'POST')
        try:
            with self.opener.open(req, timeout=5) as response:
                raw = response.read(1024 * 1024 + 1)
            if len(raw) > 1024 * 1024:
                raise ExchangeUnavailable('network_response_too_large')
            result = json.loads(raw)
            if not isinstance(result, dict):
                raise ExchangeUnavailable('network_response_invalid')
            return result
        except error.HTTPError as exc:
            with exc:
                raw = exc.read(4097)
            try:
                reason = json.loads(raw)['error'] if len(raw) <= 4096 else None
            except (ValueError, TypeError, KeyError):
                reason = None
            raise ExchangeUnavailable(reason if isinstance(reason, str) and re.fullmatch(_IDENTIFIER, reason)
                                      else 'network_request_refused') from None
        except (OSError, ValueError):
            raise ExchangeUnavailable('network_unavailable') from None


class NetworkSpoke:
    def __init__(self, root, peer, store, exchange, bindings, *, hub, recipient_keys=None, clock=snapshot):
        self.root, self.peer, self.store = root, peer, store
        self.hub, self.recipient_keys = hub, recipient_keys or {}
        self.exchange, self.bindings, self.clock = exchange, bindings, clock
        self._schema_ready = False
        for name in ('work.sqlite', 'pump.sqlite'):
            file = root / name
            try:
                fd = os.open(file, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            except FileExistsError:
                pass
            else:
                os.close(fd)
            _private(file)
        with self._db() as db, db:
            db.execute('''CREATE TABLE IF NOT EXISTS owner (singleton integer PRIMARY KEY CHECK(singleton=1),
                        id text NOT NULL, hub text NOT NULL, pull_after integer NOT NULL DEFAULT 0)''')
            db.execute('INSERT OR IGNORE INTO owner (singleton,id,hub) VALUES (1,?,?)', (peer, hub))
            if db.execute('SELECT id,hub FROM owner').fetchone() != (peer, hub):
                raise ValueError('spoke journal belongs to an unrelated peer')
            db.execute('''CREATE TABLE IF NOT EXISTS transfers (
                id text NOT NULL, direction text NOT NULL, request text NOT NULL,
                outcome text NOT NULL, reported integer NOT NULL DEFAULT 0,
                PRIMARY KEY(id,direction))''')

    def _db(self):
        return closing(sqlite3.connect(self.root / 'work.sqlite', timeout=1))

    @staticmethod
    def _encode(value):
        return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)

    def _retain(self, db, identifier, direction, value, initial):
        raw = self._encode(value)
        db.execute('INSERT OR IGNORE INTO transfers VALUES (?,?,?,?,0)',
                   (identifier, direction, raw, self._encode(initial)))
        old, result = db.execute('SELECT request,outcome FROM transfers WHERE id=? AND direction=?',
                                 (identifier, direction)).fetchone()
        if old != raw:
            raise ValueError('original network message identity is immutable')
        return json.loads(result)

    @staticmethod
    def _save(db, identifier, direction, outcome):
        db.execute('UPDATE transfers SET outcome=?,reported=0 WHERE id=? AND direction=?',
                   (NetworkSpoke._encode(outcome), identifier, direction))

    def send(self, value):
        _check(_PEER_SEND, value)
        if value['sender_conversation_id'] not in self.bindings:
            raise ValueError('exact local sending conversation is not owned')
        if not value['body'].strip() or '\x00' in value['body'] or len(value['body'].encode()) > 65536:
            raise ValueError('invalid message body')
        due = value.get('not_before_micros')
        if due is not None and due >= value['expires_at_micros']:
            raise ValueError('message eligibility must precede expiry')
        identifier = value['id']
        value = dict(value, not_before_micros=due, in_reply_to=value.get('in_reply_to'))
        with self._db() as db, db:
            outcome = self._retain(db, identifier, 'out', value, {'status': 'waiting_for_hub'})
        return dict(outcome, id=identifier)

    def status(self, identifier, *, inbound=False, refresh=False):
        direction = 'in' if inbound else 'out'
        with self._db() as db:
            row = db.execute('SELECT request,outcome FROM transfers WHERE id=? AND direction=?',
                             (identifier, direction)).fetchone()
        if row is None:
            return dict(id=identifier, status='not_found')
        if refresh and not inbound:
            try:
                remote = self.exchange('status', {'id': identifier})
                self._check_summary(json.loads(row[0]), remote)
                return dict(remote, status=remote['outcome']['status'])
            except ExchangeUnavailable:
                pass
        return dict(json.loads(row[1]), id=identifier)

    @staticmethod
    def _check_summary(original, reply):
        fields = ('id', 'peer_id', 'conversation_id', 'expires_at_micros', 'not_before_micros', 'in_reply_to')
        outcome = reply.get('outcome')
        if (any(reply.get(key) != original.get(key) for key in fields)
                or not isinstance(outcome, dict) or not isinstance(outcome.get('status'), str)):
            raise ExchangeUnavailable('network_custody_mismatch')

    def _pull(self):
        with self._db() as db:
            after = db.execute('SELECT pull_after FROM owner').fetchone()[0]
        frame = {'limit': 16, 'after': after}
        try:
            pull = self.exchange('pull', dict(frame, restore_allowlist=True))
        except ExchangeUnavailable as exc:
            if str(exc) != 'invalid_argument':
                raise
            # Healthy earlier hubs reject the capability field before
            # returning work. A restored hub refuses capability-free pulls.
            pull = self.exchange('pull', frame)
        replies = pull.get('deliveries')
        authorized = set() if pull.get('restore_allowlist') else None
        if not isinstance(replies, list) or len(replies) > 16:
            raise ExchangeUnavailable('network_response_invalid')
        try:
            with self._db() as db, db:
                for result in replies:
                    sequence = result['sequence']
                    if type(sequence) is not int or sequence <= after:
                        raise ValueError('out-of-order network delivery')
                    after = sequence
                    envelope = result['message']
                    message = Message(**envelope)
                    if message.scope != 'peer:' + self.peer or message.source != 'direct':
                        raise ValueError('hub delivery is addressed to another owner')
                    self._retain(db, message.identifier, 'in', envelope, {'status': 'owner_admitted'})
                    if authorized is not None:
                        authorized.add(message.identifier)
                db.execute('UPDATE owner SET pull_after=?', (after if len(replies) == 16 else 0,))
        except (KeyError, TypeError, ValueError):
            raise ExchangeUnavailable('network_response_invalid') from None
        return authorized

    def _outgoing(self):
        with self._db() as db:
            rows = db.execute("SELECT id,request,outcome FROM transfers WHERE direction='out' ORDER BY rowid").fetchall()
        refusal = None
        for identifier, value, raw in rows:
            previous = json.loads(raw)
            if previous.get('outcome', {}).get('status') in _FINAL | {'reply_available', 'restore_held'}:
                continue
            original = json.loads(value)
            try:
                reply = self.exchange('send', original)
                self._check_summary(original, reply)
            except ExchangeUnavailable as exc:
                if str(exc) == 'restore_held':
                    with self._db() as db, db:
                        self._save(db, identifier, 'out',
                                   dict(status='restore_held', outcome={'status': 'restore_held'}))
                    continue
                if str(exc) not in _MESSAGE_REFUSALS:
                    raise
                refusal = exc
                continue
            with self._db() as db, db:
                self._save(db, identifier, 'out', dict(reply, status=reply['outcome']['status']))
        if refusal is not None:
            raise refusal

    def _observe_attempt(self, message, saved):
        with self.store._connect() as db:
            row = MessageHandoff._attempt(db, (message.scope, message.identifier, saved['attempt_id']))
        if row and row[0] in ('submitted', 'uncertain'):
            return MessageHandoff._outcome(saved['attempt_id'], DeliveryReceipt(*row))
        if row and row[0] == 'unsent':
            return dict(status='held_recipient', **({'reason': row[2]} if row[2] else {}))
        return dict(status='uncertain', attempt_id=saved['attempt_id'], reason='local_attempt_requires_reconciliation')

    def _execute(self, db, message, saved):
        if saved['status'] == 'submitting':
            return self._observe_attempt(message, saved)
        clock = self.clock()
        window = MessageHandoff._window(message, clock)
        if window != 'eligible':
            return {'status': window}
        decision, _ = recipient_policy(self.store, message, clock=clock, exact_recipient=message.order_recipient)
        if decision.state == 'bounce':
            if self.store.record_bounce(message, decision.reason):
                return dict(status='bounced', reason=decision.reason)
            return dict(status='held_policy', reason='original_message_effect_requires_reconciliation')
        if decision.state == 'hold':
            return dict(status='held_dnd' if decision.reason == 'recipient_dnd' else 'held_policy',
                        reason=decision.reason)
        if decision.state != 'ready':
            return {'status': 'held_policy', 'reason': decision.reason}
        driver = self.bindings.get(message.recipient)
        if driver is None:
            return {'status': 'held_recipient', 'reason': 'recipient_binding_unavailable'}
        attempt = str(uuid4())
        with db:
            self._save(db, message.identifier, 'in', dict(status='submitting', attempt_id=attempt))
        receipt = deliver(self.store, message, attempt, lambda: driver(message), clock=self.clock)
        if receipt.state == 'unsent':
            if receipt.reason in {'recipient_dnd', 'recipient_busy'}:
                with self.store._connect() as connection:
                    evidence = connection.execute('SELECT bounce_reason FROM wake_messages_v1 WHERE scope=%s AND message_id=%s',
                                                  (message.scope, message.identifier)).fetchone()
                if evidence and evidence[0] == receipt.reason:
                    return dict(status='bounced', reason=receipt.reason)
            return dict(status='held_recipient', reason=receipt.reason)
        if receipt.state == 'submitted' and not receipt.receipt_id:
            return dict(status='uncertain', attempt_id=attempt, reason='owner_receipt_unverified')
        return MessageHandoff._outcome(attempt, receipt)

    def _incoming(self, authorized=None):
        with self._db() as db:
            rows = db.execute("SELECT id,request,outcome FROM transfers WHERE direction='in' ORDER BY rowid").fetchall()
            pending = []
            for identifier, raw, saved in rows:
                saved = json.loads(saved)
                if saved['status'] in _FINAL or authorized is not None and identifier not in authorized:
                    continue
                message = Message(**json.loads(raw))
                message = replace(message, order_recipient=self.recipient_keys.get(message.recipient, message.recipient))
                self.store.admit(message)
                pending.append((identifier, message, saved))
            for identifier, message, saved in pending:
                outcome = self._execute(db, message, saved)
                if outcome != saved:
                    with db:
                        self._save(db, identifier, 'in', outcome)

    def _report(self):
        with self._db() as db:
            queue = db.execute("""SELECT id,request,outcome FROM transfers
                                  WHERE direction='in' AND reported=0 ORDER BY rowid""").fetchall()
        refusal = None
        for identifier, raw, saved in queue:
            envelope, outcome = json.loads(raw), json.loads(saved)
            if outcome['status'] == 'submitting':
                continue
            frame = dict(id=identifier, conversation_id=envelope['recipient'], in_reply_to=envelope['in_reply_to'],
                         expires_at_micros=envelope['expires_at_micros'], not_before_micros=envelope['not_before_micros'],
                         outcome=outcome)
            _check(_RECEIPT, frame)
            try:
                reply = self.exchange('receipt', frame)
            except ExchangeUnavailable as exc:
                if str(exc) not in _MESSAGE_REFUSALS:
                    raise
                refusal = exc
                continue
            if reply.get('id') != identifier or reply.get('outcome') != outcome:
                raise ExchangeUnavailable('network_receipt_mismatch')
            with self._db() as db, db:
                db.execute("UPDATE transfers SET reported=1 WHERE id=? AND direction='in' AND outcome=?",
                           (identifier, saved))
        if refusal is not None:
            raise refusal

    def tick(self, directory=None):
        from psycopg import Error

        with closing(sqlite3.connect(self.root / 'pump.sqlite', timeout=.5)) as lock:
            try:
                lock.execute('BEGIN EXCLUSIVE')
            except sqlite3.OperationalError:
                return {'status': 'owner_busy'}
            if not self._schema_ready:
                try:
                    self.store.initialize()
                except (Error, OSError):
                    return {'status': 'waiting_for_owner_database'}
                self._schema_ready = True
            failures = {}
            stages = {'outgoing': self._outgoing, 'pull': self._pull}
            if directory is not None:
                stages = {'directory': lambda: self.exchange('directory', directory), **stages}
            authorized = None
            for name, stage in stages.items():
                try:
                    result = stage()
                    if name == 'pull':
                        authorized = result
                except ExchangeUnavailable as exc:
                    failures[name] = str(exc)
            # A fresh authenticated pull proves the hub still entrusts this
            # peer. Previously retained inbox entries remain durable during a
            # disconnect or revocation, alongside untouched non-network work.
            if 'pull' not in failures:
                try:
                    self._incoming(authorized)
                except (Error, OSError):
                    self._schema_ready = False
                    failures['owner'] = 'network_owner_database_unavailable'
            try:
                self._report()
            except ExchangeUnavailable as exc:
                failures['receipt'] = str(exc)
            result = dict(status='network_attention' if failures else 'ready', failures=failures)
            pull_failure = failures.get('pull')
            if pull_failure == 'invalid_token':
                result['peer_access'] = 'authorization_denied'
            elif pull_failure is not None:
                result['peer_access'] = 'unavailable'
            return result


def main(argv=None):
    parser = argparse.ArgumentParser(description='Run one outbound Wake network spoke')
    parser.add_argument('--config', type=Path, required=True)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('tick')
    runner = commands.add_parser('run')
    runner.add_argument('--interval', type=float, default=3)
    send = commands.add_parser('send')
    send.add_argument('--request', type=Path, required=True)
    status = commands.add_parser('status')
    status.add_argument('id')
    status.add_argument('--inbound', action='store_true')
    args = parser.parse_args(argv)
    from .managed_inventory import InventoryError

    try:
        config = _object(_private(args.config))
        expected = {'root', 'peer_id', 'origin', 'credential_file', 'owner_dsn_file', 'bindings', 'directory'}
        if not expected <= set(config) <= expected | {'ca_file'}:
            raise ValueError('invalid operator-owned spoke configuration')
        root = _private(config['root'], directory=True)
        clock = snapshot
        bindings, recipient_keys = {}, {}
        for identity, value in config['bindings'].items():
            if not re.fullmatch(_IDENTIFIER, identity):
                raise ValueError('invalid pinned conversation identity')
            if isinstance(value, dict) and set(value) == {'argv', 'namespace'}:
                from .message_policy import recipient_key
                namespace = value['namespace']
                if not isinstance(namespace, str) or not 0 < len(namespace) <= 512:
                    raise ValueError('invalid pinned conversation namespace')
                recipient_keys[identity] = recipient_key(namespace, identity)
                value = value['argv']
            bindings[identity] = _driver(value, identity, clock)
        exchange = PeerHTTPS(config['origin'], config['peer_id'], config['credential_file'],
                             ca_file=config.get('ca_file'))
        dsn = _private(config['owner_dsn_file']).read_text().strip()
        if not dsn or len(dsn) > 16384:
            raise ValueError('invalid local owner database configuration')
        worker = NetworkSpoke(root, config['peer_id'], PostgresMessages(dsn), exchange, bindings,
                              hub=exchange.origin, recipient_keys=recipient_keys, clock=clock)
        directory = _private(config['directory'])
        if args.command == 'tick':
            result = worker.tick(_object(directory))
        elif args.command == 'send':
            result = worker.send(_object(args.request))
        elif args.command == 'status':
            result = worker.status(args.id, inbound=args.inbound, refresh=True)
        else:
            if not .25 <= args.interval <= 60:
                raise ValueError('invalid spoke polling interval')
            previous = None
            while True:
                result = worker.tick(_object(directory))
                if result != previous:
                    print(json.dumps(result, sort_keys=True), flush=True)
                    previous = result
                time.sleep(args.interval)
        print(json.dumps(result, sort_keys=True))
        return 0
    except KeyboardInterrupt:
        return 0
    except (KeyError, TypeError, ValueError, OSError, sqlite3.Error, InventoryError):
        print(json.dumps({'status': 'error', 'reason': 'network_spoke_configuration_or_state_invalid'}))
        return 2


if __name__ == '__main__':
    sys.exit(main())
