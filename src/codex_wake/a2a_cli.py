"""Explicit local bus enrollment; no automatic runtime or service effects."""
from __future__ import annotations

import json
import os
from pathlib import Path

from .a2a_bus import BusStore, default_bus_root
from .a2a_identity import BusError, RuntimeIdentity
from .records import WakeError
from .sessions import SelectionError, observe, resolve
from .shared_app_server import SharedAppServerReader, SharedSourceError, locate_shared_endpoint


def add_a2a_parser(subparsers):
    parser = subparsers.add_parser('a2a', help='configure an explicitly enrolled local messaging bus')
    commands = parser.add_subparsers(dest='a2a_command', required=True)
    for verb in ['configure', 'enroll', 'status', 'doctor', 'pause', 'resume', 'revoke', 'migrate']:
        command = commands.add_parser(verb)
        command.add_argument('--bus-root', type=Path)
        command.add_argument('--bus-id', default='local')
        command.add_argument('--json', action='store_true', dest='as_json')
        if verb != 'configure':
            command.add_argument('--operator-capability', type=Path, required=True)
        if verb == 'configure':
            command.add_argument('--allow-cross-root', action='store_true')
        if verb == 'enroll':
            command.add_argument('root', type=Path)
            command.add_argument('--thread', help='optional exact live thread or qualified tab to authorize')
            command.add_argument('--app-server', default='unix://')
            command.add_argument('--tmux-socket')
            command.add_argument('--tmux-session')
            command.add_argument('--no-send', action='store_true')
            command.add_argument('--no-receive', action='store_true')
            command.add_argument('--notify', action='store_true')
        if verb == 'revoke':
            command.add_argument('actor_id')


def resolve_identity(selector: str, *, endpoint: str = 'unix://', socket_path=None, session=None) -> RuntimeIdentity:
    snapshot = observe(endpoint=endpoint, socket_path=socket_path)
    row = resolve(snapshot, selector, session=session)
    actual_endpoint = snapshot['sources']['app_server']['endpoint']
    with SharedAppServerReader(actual_endpoint) as reader:
        thread = reader.read_thread(row['thread_id'])
        return RuntimeIdentity.from_metadata(thread, reader.server_metadata)


def invoking_actor(store: BusStore, capability: Path, *, endpoint: str = 'unix://'):
    identifier = os.environ.get('CODEX_THREAD_ID')
    if not identifier:
        raise BusError('identity_unavailable', 'invoking thread claim is missing')
    if endpoint == 'unix://':
        endpoint = locate_shared_endpoint()
    with SharedAppServerReader(endpoint) as reader:
        thread = reader.read_thread(identifier)
        identity = RuntimeIdentity.from_metadata(thread, reader.server_metadata)
    return store.authenticate(capability, identity, invoking_cwd=Path.cwd())


def result(value: dict, *, success=True):
    print(json.dumps(dict(schema_version=1, success=success, **value), sort_keys=True))


def a2a_command(args):
    partial_receipts = []
    try:
        root = args.bus_root or default_bus_root(args.bus_id)
        if args.a2a_command == 'configure':
            store, capability = BusStore.configure(root, bus_id=args.bus_id, allow_cross_root=args.allow_cross_root)
            with store.connection() as database:
                receipt = store.meta(database, 'bootstrap_receipt')
            partial_receipts.append(receipt)
            from .a2a_mailbox import Mailbox
            migration = Mailbox.migrate(store, capability)
            result(dict(bus=store.status(), operator_capability_file=str(capability), receipt_id=receipt, mailbox_migration_receipt=migration))
            return 0
        store = BusStore(root)
        # Validate explicit operator authority before observing or changing peers.
        with store.connection() as database:
            store.operator(database, args.operator_capability)
        if args.a2a_command == 'enroll':
            identity = resolve_identity(args.thread, endpoint=args.app_server, socket_path=args.tmux_socket,
                                        session=args.tmux_session) if args.thread else None
            if identity is not None and not Path(identity.cwd).is_relative_to(args.root.resolve()):
                raise BusError('authorization_denied', 'thread is outside the selected enrollment root')
            receipt = store.enroll(args.root, args.operator_capability,
                                   send=not args.no_send, receive=not args.no_receive, notify=args.notify)
            partial_receipts.append(receipt)
            value = dict(bus_id=store.bus_id, receipt_id=receipt, actor_capability_file=None,
                         notification_capability='unqualified')
            if identity is not None:
                capability, issuance = store.issue_actor(identity, args.root, args.operator_capability)
                value.update(actor_capability_file=str(capability), actor_receipt_id=issuance,
                             namespace=identity.namespace, thread_id=identity.thread_id)
            result(value)
        elif args.a2a_command == 'migrate':
            from .a2a_mailbox import Mailbox
            result(dict(bus_id=store.bus_id, receipt_id=Mailbox.migrate(store, args.operator_capability)))
        elif args.a2a_command in ('pause', 'resume'):
            receipt = store.set_paused(args.a2a_command == 'pause', args.operator_capability)
            result(dict(bus_id=store.bus_id, receipt_id=receipt, paused=store.status()['paused']))
        elif args.a2a_command == 'revoke':
            receipt = store.revoke_actor(args.actor_id, args.operator_capability)
            result(dict(bus_id=store.bus_id, receipt_id=receipt))
        else:
            with store.connection() as database:
                database.execute('BEGIN IMMEDIATE')
                receipt = store.event(database, 'operator', 'inspect_' + args.a2a_command, dict(bus_id=store.bus_id))
                database.execute('COMMIT')
            result(dict(bus=store.status(), receipt_id=receipt))
        return 0
    except SelectionError as exc:
        result(dict(error=dict(code='selection_error', exit_code=exc.code, message=str(exc),
                               selector=exc.selector, candidates=exc.candidates)), success=False)
        return exc.code
    except BusError as exc:
        result(dict(error=dict(code=exc.code, message=str(exc)), partial_receipt_ids=partial_receipts,
                    reconciliation_required=bool(partial_receipts)), success=False)
        return 7 if exc.code in ('authorization_denied', 'cross_root_denied') else 8
    except SharedSourceError:
        result(dict(error=dict(code='runtime_unavailable', message='required runtime metadata is unavailable')), success=False)
        return 5
    except (OSError, WakeError):
        result(dict(error=dict(code='store_unavailable', message='operation unavailable; inspect existing state before retry'),
                    partial_receipt_ids=partial_receipts, reconciliation_required=bool(partial_receipts)), success=False)
        return 8
