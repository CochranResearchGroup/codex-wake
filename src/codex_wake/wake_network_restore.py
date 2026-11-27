"""Reconcile a restored, quiesced hub against private authoritative spoke journals."""
import argparse
from contextlib import closing
import json
from pathlib import Path
import sqlite3
from urllib.parse import quote, urlsplit
from uuid import UUID

from .managed_inventory import InventoryError
from .message_delivery import DeliveryReceipt
from .message_handoff import MessageHandoff
from .wake_network import WakeNetwork, _check
from .wake_network_messages import NetworkMessages, _RECEIPT, _SELECT, _TERMINAL


def _journal(spec, hub):
    from .message_owner import _private

    path = _private(spec['journal'])
    with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=2)) as db:
        db.execute('BEGIN')
        peer = spec['peer_id']
        owners = db.execute('SELECT id,hub FROM owner').fetchall()
        if owners != [(peer, hub.rstrip('/') + '/network/v1/peers/' + quote(peer, safe=''))]:
            raise ValueError('journal belongs to a different peer or hub')
        return {identifier: (json.loads(envelope), json.loads(outcome))
                for identifier, envelope, outcome in db.execute(
                    "SELECT id,request,outcome FROM transfers WHERE direction='in'")}


def _outcome(spec, envelope, recorded):
    from .message_owner import _private
    import psycopg

    state = recorded.get('status')
    # A committed recipient journal needs no live recipient database. If it
    # only retained a submission intent, consult the exact local attempt.
    if state == 'submitting' and 'owner_dsn_file' in spec:
        dsn = _private(spec['owner_dsn_file']).read_text().strip()
        with psycopg.connect(dsn, connect_timeout=3) as db:
            saved = db.execute('''SELECT source,recipient,expires_at_micros,payload,sender,in_reply_to,not_before_micros
                FROM wake_messages_v1 WHERE scope=%s AND message_id=%s''',
                (envelope['scope'], envelope['identifier'])).fetchone()
            expected = tuple(envelope[key] for key in ('source','recipient','expires_at_micros',
                'payload','sender','in_reply_to','not_before_micros'))
            if saved != expected:
                return None
            attempt = MessageHandoff._attempt(db, (envelope['scope'], envelope['identifier'], recorded['attempt_id']))
            if attempt and attempt[0] in ('submitted', 'uncertain'):
                recorded = MessageHandoff._outcome(recorded['attempt_id'], DeliveryReceipt(*attempt))
                state = recorded['status']
    if state not in _TERMINAL:
        return None
    frame = dict(id=envelope['identifier'], conversation_id=envelope['recipient'], in_reply_to=envelope['in_reply_to'],
                 expires_at_micros=envelope['expires_at_micros'], not_before_micros=envelope['not_before_micros'],
                 outcome=recorded)
    try:
        _check(_RECEIPT, frame)
    except InventoryError:
        return None
    if (('attempt_id' in recorded) != (state in {'submitted', 'uncertain'})
            or ('receipt_id' in recorded) != (state == 'submitted')
            or state == 'bounced' and recorded.get('reason') not in {'recipient_dnd', 'recipient_busy'}):
        return None
    return recorded


def quarantine(network):
    """Commit a hold before consulting any potentially unavailable owner."""
    with network.connect() as db:
        db.execute('LOCK TABLE wake_network_peers_v1, wake_network_messages_v1 IN ACCESS EXCLUSIVE MODE')
        db.execute('UPDATE wake_network_peers_v1 SET enabled=false')
        db.execute('INSERT INTO wake_network_restore_mode_v1 VALUES (true) ON CONFLICT DO NOTHING')
        db.execute("""INSERT INTO wake_network_restore_holds_v1 (id)
            SELECT id FROM wake_network_messages_v1 WHERE left(destination, 5) = 'peer:'
            AND coalesce(outcome->>'status','') <> ALL(%s)
            ON CONFLICT DO NOTHING""", (sorted(_TERMINAL),))


def reconcile(network, hub, owners):
    """Converge only exact owner evidence while restored credentials remain disabled."""
    from psycopg import Error
    from psycopg.types.json import Jsonb

    url = urlsplit(hub)
    if url.scheme != 'https' or not url.hostname or url.username or url.path not in ('', '/') or url.query or url.fragment:
        raise ValueError('canonical HTTPS hub origin required')
    if len({spec['peer_id'] for spec in owners}) != len(owners):
        raise ValueError('duplicate recipient journal')
    quarantine(network)
    journals, unavailable = {}, set()
    for spec in owners:
        if not {'peer_id', 'journal'} <= set(spec) <= {'peer_id', 'journal', 'owner_dsn_file'}:
            raise ValueError('invalid owner journal configuration')
        try:
            journals[spec['peer_id']] = spec, _journal(spec, hub)
        except (OSError, sqlite3.Error, ValueError):
            unavailable.add(spec['peer_id'])
    counts = dict(reconciled=0, held=0, post_backup_ids=0)
    with network.connect() as db:
        db.execute('LOCK TABLE wake_network_peers_v1, wake_network_messages_v1 IN ACCESS EXCLUSIVE MODE')
        seen = set()
        rows = db.execute(_SELECT + " WHERE left(destination, 5) = 'peer:'").fetchall()
        for row in rows:
            identifier, peer, original, prior = row[1], row[4][5:], row[6], row[7]
            seen.add(identifier)
            spec, receipts = journals.get(peer, (None, {}))
            evidence = receipts.get(identifier)
            try:
                outcome = _outcome(spec, *evidence) if evidence and evidence[0] == original else None
            except (Error, OSError, TypeError, ValueError, KeyError):
                unavailable.add(peer)
                outcome = None
            established = prior and prior['status'] in _TERMINAL
            if outcome and (not established or prior == outcome):
                db.execute('UPDATE wake_network_messages_v1 SET outcome=%s WHERE id=%s',
                           (Jsonb(outcome), identifier))
                db.execute('DELETE FROM wake_network_restore_holds_v1 WHERE id=%s', (identifier,))
                counts['reconciled'] += 1
            elif not established or evidence and (evidence[0] != original or outcome != prior):
                db.execute('INSERT INTO wake_network_restore_holds_v1 (id) VALUES (%s) ON CONFLICT DO NOTHING',
                           (identifier,))
                counts['held'] += 1
        for spec, receipts in journals.values():
            for identifier, (envelope, _) in receipts.items():
                if str(UUID(identifier)) != identifier or envelope['identifier'] != identifier or (
                        envelope['scope'] != 'peer:' + spec['peer_id']):
                    raise ValueError('invalid owner message binding')
                if identifier not in seen:
                    db.execute('INSERT INTO wake_network_restore_holds_v1 (id) VALUES (%s) ON CONFLICT DO NOTHING',
                               (identifier,))
                    counts['post_backup_ids'] += 1
    return dict(counts, status='reconciled', restored_peer_credentials='disabled',
                unavailable_owner_receipts=sorted(unavailable))


def main(argv=None):
    from .message_owner import _private

    parser = argparse.ArgumentParser(description='Reconcile a stopped, restored Wake network hub')
    parser.add_argument('--config', required=True, type=Path)
    parser.add_argument('--quiesced-restored-hub', required=True, action='store_true')
    args = parser.parse_args(argv)
    config = json.loads(_private(args.config).read_text())
    if set(config) != {'network', 'hub', 'owners'}:
        raise ValueError('explicit recovery scope required')
    network = WakeNetwork(config['network'], '', '')
    network.initialize()
    NetworkMessages(network).initialize()
    print(json.dumps(reconcile(network, config['hub'], config['owners']), sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
