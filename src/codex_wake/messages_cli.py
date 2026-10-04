"""Agent-facing mailbox verbs using one exact-capability service boundary."""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import time
import uuid

from .a2a_bus import BusStore, default_bus_root
from .a2a_cli import invoking_actor, resolve_identity, result
from .a2a_identity import BusError
from .a2a_mailbox import Mailbox
from .records import WakeError, parse_duration
from .sessions import SelectionError
from .shared_app_server import SharedSourceError


def add_messages_parser(subparsers):
    parser = subparsers.add_parser('messages', help='send and consume explicitly authorized local mailbox messages')
    commands = parser.add_subparsers(dest='messages_command', required=True)
    for verb in ['send','inbox','outbox','show','read','ack','reply','cancel','wait','watch','reconcile','arm-reply']:
        command = commands.add_parser(verb)
        command.add_argument('--bus-root', type=Path, default=os.environ.get('CODEX_WAKE_A2A_BUS_ROOT'))
        command.add_argument('--bus-id', default='local')
        command.add_argument('--capability', type=Path, default=os.environ.get('CODEX_WAKE_A2A_CAPABILITY'))
        command.add_argument('--app-server', default='unix://')
        command.add_argument('--json', action='store_true', dest='as_json')
        if verb in ('show','read','reconcile'):
            command.add_argument('--as-operator', action='store_true')
            command.add_argument('--operator-capability', type=Path)
        if verb in ('show','read','ack','reply','cancel','wait','reconcile','arm-reply'):
            command.add_argument('message_id')
        if verb == 'arm-reply':
            command.add_argument('--wake-root', type=Path, default=os.environ.get('CODEX_WAKE_WAKE_ROOT'))
            command.add_argument('--sender-receipt-authority', type=Path,
                                 default=os.environ.get('CODEX_WAKE_SENDER_RECEIPT_AUTHORITY'))
            command.add_argument('--idempotency-key', required=True)
            command.add_argument('--expires-at', required=True)
        if verb in ('send','reply'):
            command.add_argument('--body-file', required=True)
            command.add_argument('--idempotency-key')
            command.add_argument('--human', action='store_true', help='generate and announce an intent key before attempting a human send')
            command.add_argument('--kind', choices=['notice','request','result'], default='result' if verb == 'reply' else 'request')
            command.add_argument('--ttl', default='24h')
            command.add_argument('--delivery', choices=['inbox','notify'], default='notify')
            command.add_argument('--subject')
        if verb == 'send':
            command.add_argument('--to', required=True)
            command.add_argument('--tmux-socket')
            command.add_argument('--tmux-session')
            command.add_argument('--correlation')
        if verb in ('ack','reply'):
            command.add_argument('--outcome', choices=['accepted','declined','completed','failed'], required=verb == 'ack')
            command.add_argument('--evidence')
        if verb in ('inbox','outbox'):
            command.add_argument('--cursor', type=int, default=0)
            command.add_argument('--limit', type=int, default=100)
            command.add_argument('--state')
        if verb == 'wait':
            command.add_argument('--for', dest='wait_for', choices=['received','reply','accepted','declined','completed','failed'], required=True)
            command.add_argument('--timeout', default='5m')
        if verb == 'watch':
            command.add_argument('message_id', nargs='?')
            command.add_argument('--duration', default='5m')
        if verb in ('wait','watch'):
            command.add_argument('--interval', type=float, default=1)


def body_input(path):
    if path == '-':
        raw = sys.stdin.buffer.read(32769)
    else:
        with Path(path).open('rb') as stream:
            raw = stream.read(32769)
    if len(raw) > 32768:
        raise BusError('body_limit', 'body exceeds 32768 UTF-8 bytes')
    try:
        return raw.decode('utf-8')
    except UnicodeError:
        raise BusError('invalid_argument', 'body must be valid UTF-8') from None


def observe_receipts(mailbox, actor, args):
    if not 0.1 <= args.interval <= 10:
        raise BusError('invalid_argument', 'poll interval must be between 0.1 and 10 seconds')
    duration = parse_duration(args.timeout if args.messages_command == 'wait' else args.duration).total_seconds()
    if duration > 300:
        raise BusError('invalid_argument', 'foreground observation is limited to five minutes')
    deadline = time.monotonic() + duration
    previous = None
    count = 0
    try:
        while True:
            value = mailbox.show(actor, args.message_id) if args.message_id else mailbox.list(actor)
            if args.messages_command == 'wait':
                if args.wait_for != 'reply':
                    receipt = mailbox.disposition_receipt(actor, args.message_id, args.wait_for)
                    if receipt:
                        result(dict(event='satisfied', message=value, condition=args.wait_for, receipt=receipt))
                        return 0
                if args.wait_for == 'reply':
                    replies = mailbox.replies(actor, args.message_id)
                    if replies:
                        result(dict(event='satisfied', message=value, condition='reply', replies=replies))
                        return 0
            elif previous != value:
                result(dict(event='initial' if previous is None else 'changed', observation=value))
            previous = value
            count += 1
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            time.sleep(min(args.interval, remaining))
    except KeyboardInterrupt:
        result(dict(event='summary', interrupted=True, observations=count))
        return 0
    if args.messages_command == 'wait':
        result(dict(error=dict(code='observation_timeout', message='receipt condition was not observed'),
                    message_id=args.message_id, condition=args.wait_for, observations=count), success=False)
        return 10
    result(dict(event='summary', observations=count))
    return 0


def messages_command(args):
    intent_key = getattr(args, 'idempotency_key', None)
    try:
        verb = args.messages_command
        if verb in ('send','reply') and not intent_key:
            if not args.human:
                raise BusError('invalid_argument', 'machine send/reply requires an explicit idempotency key')
            intent_key = 'intent_' + uuid.uuid4().hex
            print(json.dumps(dict(schema_version=1, event='intent_prepared', idempotency_key=intent_key)), file=sys.stderr, flush=True)
        bus = BusStore(args.bus_root or default_bus_root(args.bus_id))
        mailbox = Mailbox(bus)
        if getattr(args, 'as_operator', False):
            if args.operator_capability is None:
                raise BusError('authorization_denied', 'explicit operator capability is required')
            value = mailbox.operator_inspect(args.operator_capability, args.message_id, body=verb == 'read')
            if verb == 'reconcile':
                value['reconciliation'] = 'held_for_exact_evidence' if value['message']['state']['notification'] == 'uncertain' else 'no_uncertain_effect'
            result(value)
            return 0
        capability = args.capability or (Path(os.environ['CODEX_WAKE_A2A_CAPABILITY']) if os.environ.get('CODEX_WAKE_A2A_CAPABILITY') else None)
        if capability is None:
            raise BusError('authorization_denied', 'explicit issued actor capability is required')
        actor = invoking_actor(bus, capability, endpoint=args.app_server)
        if verb == 'arm-reply':
            from .a2a_reply_wake import arm_reply
            value = arm_reply(actor, args.message_id, args.wake_root,
                              args.sender_receipt_authority, args.idempotency_key, args.expires_at)
        elif verb == 'send':
            recipient = resolve_identity(args.to, endpoint=args.app_server, socket_path=args.tmux_socket,
                                         session=args.tmux_session, allow_offline=True)
            value = mailbox.send(actor, recipient, body=body_input(args.body_file), idempotency_key=intent_key,
                                 kind=args.kind, ttl=parse_duration(args.ttl).total_seconds(), delivery=args.delivery,
                                 subject=args.subject, selector=dict(selector=args.to, identity=recipient.thread_id),
                                 correlation=args.correlation)
        elif verb == 'reply':
            value = mailbox.reply(actor, args.message_id, body=body_input(args.body_file), idempotency_key=intent_key,
                                  kind=args.kind, ttl=parse_duration(args.ttl).total_seconds(), delivery=args.delivery,
                                  subject=args.subject, outcome=args.outcome, evidence=args.evidence)
        elif verb in ('inbox','outbox'):
            value = mailbox.list(actor, outbox=verb == 'outbox', cursor=args.cursor, limit=args.limit, state=args.state)
        elif verb == 'show':
            value = dict(message=mailbox.show(actor, args.message_id))
        elif verb == 'read':
            value = mailbox.read(actor, args.message_id)
        elif verb == 'ack':
            value = mailbox.ack(actor, args.message_id, outcome=args.outcome, evidence=args.evidence)
        elif verb == 'cancel':
            value = mailbox.cancel(actor, args.message_id)
        elif verb in ('wait','watch'):
            return observe_receipts(mailbox, actor, args)
        else:
            value = dict(message=mailbox.show(actor, args.message_id))
            value['reconciliation'] = 'held_for_exact_evidence' if value['message']['state']['notification'] == 'uncertain' else 'no_uncertain_effect'
        result(value)
        return 0
    except SelectionError as exc:
        result(dict(error=dict(code='selection_error', message=str(exc), selector=exc.selector, candidates=exc.candidates), idempotency_key=intent_key), success=False)
        return exc.code
    except BusError as exc:
        result(dict(error=dict(code=exc.code, message=str(exc), details=getattr(exc, 'details', {})),
                    idempotency_key=intent_key, reconciliation_required=exc.code == 'effect_uncertain'), success=False)
        return 7 if exc.code in ('authorization_denied','cross_root_denied') else 9 if exc.code in ('idempotency_conflict','receipt_conflict') else 11 if exc.code == 'effect_uncertain' else 8
    except SharedSourceError:
        result(dict(error=dict(code='runtime_unavailable', message='required runtime identity is unavailable'), idempotency_key=intent_key), success=False)
        return 5
    except (OSError, WakeError):
        result(dict(error=dict(code='operation_unavailable', message='operation unavailable; reconcile the original key before retry'), idempotency_key=intent_key), success=False)
        return 8
