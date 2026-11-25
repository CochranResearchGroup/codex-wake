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
    init = commands.add_parser('database-init', help='Initialize the configured PostgreSQL message schema')
    init.add_argument('--root', type=Path, help='Select an activated Wake or mailbox scope')
    for verb in ['send','inbox','outbox','show','read','ack','reply','replies','redirect','cancel','wait','watch','reconcile','arm-reply','dnd','intervene']:
        command = commands.add_parser(verb)
        command.add_argument('--bus-root', type=Path, default=os.environ.get('CODEX_WAKE_A2A_BUS_ROOT'))
        command.add_argument('--bus-id', default='local')
        command.add_argument('--capability', type=Path, default=os.environ.get('CODEX_WAKE_A2A_CAPABILITY'))
        command.add_argument('--app-server', default='unix://')
        command.add_argument('--actor-runtime', choices=['codex','grok'], default='codex')
        command.add_argument('--caller-session-id')
        command.add_argument('--runtime-root', type=Path)
        command.add_argument('--json', action='store_true', dest='as_json')
        if verb in ('show','read','reconcile'):
            command.add_argument('--as-operator', action='store_true')
            command.add_argument('--operator-capability', type=Path)
        if verb in ('show','read','ack','reply','replies','redirect','cancel','wait','reconcile','arm-reply'):
            command.add_argument('message_id')
        if verb == 'dnd':
            command.add_argument('mode', choices=['hold', 'bounce', 'clear'])
            command.add_argument('--for', dest='dnd_duration')
        if verb == 'intervene':
            command.add_argument('message_id')
            command.add_argument('--operator-capability', type=Path, required=True)
            command.add_argument('--wake-root', type=Path)
            command.add_argument('--override-dnd', action='store_true')
            command.add_argument('--interrupt-turn')
            command.add_argument('--status', action='store_true')
        if verb == 'redirect':
            command.add_argument('--to', required=True)
            command.add_argument('--idempotency-key', required=True)
            command.add_argument('--tmux-socket')
            command.add_argument('--tmux-session')
        if verb == 'arm-reply':
            command.add_argument('--wake-root', type=Path, default=os.environ.get('CODEX_WAKE_WAKE_ROOT'))
            command.add_argument('--sender-receipt-authority', type=Path,
                                 default=os.environ.get('CODEX_WAKE_SENDER_RECEIPT_AUTHORITY'))
            command.add_argument('--idempotency-key', required=True)
            command.add_argument('--expires-at', required=True)
        if verb in ('send','reply'):
            command.add_argument('--resume-missing', action='store_true',
                                 help='explicitly authorize reopening only the same saved recipient')
            command.add_argument('--body-file', required=True)
            command.add_argument('--idempotency-key')
            command.add_argument('--human', action='store_true', help='generate and announce an intent key before attempting a human send')
            command.add_argument('--kind', choices=['notice','request','result'], default='result' if verb == 'reply' else 'request')
            command.add_argument('--ttl', default='24h')
            command.add_argument('--delivery', choices=['inbox','notify'], default='notify')
            command.add_argument('--subject')
            command.add_argument('--task-id')
            command.add_argument('--busy-policy', choices=['wait', 'queue', 'idle-only'], default='wait')
        if verb == 'send':
            command.add_argument('--host-operator-capability', type=Path,
                help='host delegation for verified recipients in existing enrolled roots')
            command.add_argument('--to', required=True)
            command.add_argument('--tmux-socket')
            command.add_argument('--tmux-session')
            command.add_argument('--correlation')
            from .tab_targets import add_target_options
            add_target_options(command)
            command.add_argument('--wake-root', type=Path)
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
        if verb == 'database-init':
            from .message_delivery import configured_store
            store = configured_store(args.root)
            if store is None:
                raise BusError('message_store_unconfigured', 'Select an activated scope or configure the test message database')
            try:
                store.initialize()
            except Exception:
                raise BusError('message_store_unavailable', 'PostgreSQL schema initialization failed') from None
            result(dict(status='ready', message_store='postgresql'))
            return 0
        if verb in ('send','reply') and not intent_key:
            if not args.human:
                raise BusError('invalid_argument', 'machine send/reply requires an explicit idempotency key')
            intent_key = 'intent_' + uuid.uuid4().hex
            print(json.dumps(dict(schema_version=1, event='intent_prepared', idempotency_key=intent_key)), file=sys.stderr, flush=True)
        bus = BusStore(args.bus_root or default_bus_root(args.bus_id))
        mailbox = Mailbox(bus)
        if verb == 'intervene':
            result(intervene(args, mailbox))
            return 0
        if getattr(args, 'as_operator', False):
            if args.operator_capability is None:
                raise BusError('authorization_denied', 'explicit operator capability is required')
            value = mailbox.operator_reconcile(args.operator_capability, args.message_id) if verb == 'reconcile' else mailbox.operator_inspect(args.operator_capability, args.message_id, body=verb == 'read')
            result(value)
            return 0
        capability = args.capability or (Path(os.environ['CODEX_WAKE_A2A_CAPABILITY']) if os.environ.get('CODEX_WAKE_A2A_CAPABILITY') else None)
        if capability is None:
            raise BusError('authorization_denied', 'explicit issued actor capability is required')
        if args.actor_runtime == 'grok':
            from .runtime_a2a import GrokMailboxRuntime
            actor = GrokMailboxRuntime.from_actor(bus, capability).authenticate(
                bus, capability, claimed_session=args.caller_session_id)
        else:
            actor = invoking_actor(bus, capability, endpoint=args.app_server)
        if verb == 'dnd':
            value = set_dnd(args, mailbox, actor)
        elif verb == 'arm-reply':
            from .a2a_reply_wake import arm_reply
            value = arm_reply(actor, args.message_id, args.wake_root,
                              args.sender_receipt_authority, args.idempotency_key, args.expires_at)
        elif verb == 'send':
            if not args.to.startswith(('thread:','grok:')):
                from .tab_routing import routed_send
                value, success = routed_send(args, bus, mailbox, actor, body_input(args.body_file),
                                              intent_key, resolve_identity)
                result(value, success=success)
                return 0 if success else 5
            if args.to.startswith('grok:'):
                from .runtime_a2a import GrokMailboxRuntime
                if args.runtime_root is None:
                    raise BusError('identity_unavailable','host runtime root is required')
                recipient,_ = GrokMailboxRuntime(args.runtime_root).resolve(args.to[5:])
            else:
                recipient = resolve_identity(args.to, endpoint=args.app_server, socket_path=args.tmux_socket,
                                             session=args.tmux_session, allow_offline=True)
            prepare_host_recipient(args, bus, actor, recipient)
            value = mailbox.send(actor, recipient, body=body_input(args.body_file), idempotency_key=intent_key,
                                 kind=args.kind, ttl=parse_duration(args.ttl).total_seconds(), delivery=args.delivery,
                                 subject=args.subject, selector=dict(selector=args.to, identity=recipient.thread_id),
                                 correlation=args.correlation, resume_missing=args.resume_missing,task_id=getattr(args,'task_id',None), busy_policy=getattr(args, 'busy_policy', 'wait'))
        elif verb == 'reply':
            value = mailbox.reply(actor, args.message_id, body=body_input(args.body_file), idempotency_key=intent_key,
                                  kind=args.kind, ttl=parse_duration(args.ttl).total_seconds(), delivery=args.delivery,
                                  subject=args.subject, outcome=args.outcome, evidence=args.evidence,
                                  resume_missing=args.resume_missing,task_id=getattr(args,'task_id',None), busy_policy=getattr(args, 'busy_policy', 'wait'))
        elif verb == 'replies':
            value = dict(message_id=args.message_id, replies=mailbox.replies(actor, args.message_id))
        elif verb == 'redirect':
            if args.message_id.startswith(('wake_', 'schedule_')):
                raise BusError('redirect_source_unavailable', 'this redirect requires a bounced mailbox message')
            if not args.to.startswith(('thread:', 'grok:')):
                raise BusError('invalid_argument', 'redirect needs an exact thread: or grok: recipient')
            if args.to.startswith('grok:'):
                from .runtime_a2a import GrokMailboxRuntime
                if args.runtime_root is None:
                    raise BusError('identity_unavailable', 'host runtime root is required')
                recipient, _ = GrokMailboxRuntime(args.runtime_root).resolve(args.to[5:])
            else:
                recipient = resolve_identity(args.to, endpoint=args.app_server, socket_path=args.tmux_socket,
                                             session=args.tmux_session, allow_offline=True)
            value = mailbox.redirect(actor, args.message_id, recipient, idempotency_key=intent_key)
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
            value = mailbox.reconcile(actor, args.message_id)
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


def prepare_host_recipient(args, bus, actor, recipient):
    """Host opt-in removes recipient first-poll ordering, never root authorization."""
    operator = getattr(args, 'host_operator_capability', None)
    if operator is None:
        return
    with bus.connection(read_only=True) as db:
        bus.operator(db, operator)
        bus.validate_actor(db, actor, permission='send')
        roots = [r['root'] for r in db.execute('SELECT root FROM enrollments')
                 if Path(recipient.cwd).is_relative_to(Path(r['root']))]
        if roots and max(roots, key=lambda r: len(Path(r).parts)) != actor.root and not bus.meta(db, 'allow_cross_root'):
            raise BusError('cross_root_denied', 'cross-root messaging requires explicit bus permission')
    from .native_mailbox_bootstrap import runtime_actor_context
    runtime_actor_context(bus, operator, recipient, permission='receive')



def _required_message_store(root):
    from .message_delivery import configured_store
    store = configured_store(root)
    if store is None:
        raise BusError('message_store_unconfigured', 'A shared message store is required for this scope')
    return store


def set_dnd(args, mailbox, actor):
    from .message_policy import stable_micros
    from .native_clock import snapshot

    store = _required_message_store(mailbox.bus.root)
    from psycopg import Error

    until = None
    if args.dnd_duration:
        if args.mode == 'clear':
            raise BusError('invalid_argument', 'Clearing DND does not take a duration')
        delta = parse_duration(args.dnd_duration)
        duration = (delta.days * 86400 + delta.seconds) * 1_000_000 + delta.microseconds
        now = stable_micros(snapshot(), upper=True)
        if not 0 < duration <= 30 * 86400 * 1_000_000:
            raise BusError('invalid_argument', 'DND duration must be positive and at most 30 days')
        if now is None:
            raise BusError('time_uncertain', 'StableTime is required for a DND deadline')
        until = now + duration
    with mailbox.bus.connection(read_only=True) as database:
        mailbox.bus.validate_actor(database, actor, permission='receive')
    try:
        store.set_dnd(actor.key, actor.thread_id, args.mode, until)
    except Error:
        raise BusError('message_store_unavailable', 'Could not commit the DND setting') from None
    return dict(recipient=actor.thread_id, dnd=args.mode, until_micros=until)


def intervene(args, mailbox):
    from .message_delivery import direct_message, scope_for_wake, wake_message
    from .message_policy import native_identity, stable_micros
    from .native_clock import snapshot
    from .permission_a2a import binding
    from .records import find_record
    from .runtime_delivery import original_submission_expiry

    if args.status and (args.override_dnd or args.interrupt_turn):
        raise BusError('invalid_argument', 'Inspect an intervention separately from changing it')
    if not args.status and not args.override_dnd and not args.interrupt_turn:
        raise BusError('invalid_argument', 'Request a DND override, an exact turn interruption, or both')
    if args.interrupt_turn and len(args.interrupt_turn) > 256:
        raise BusError('invalid_argument', 'Exact turn ID is too long')
    bus = mailbox.bus
    store = _required_message_store(args.wake_root or bus.root)
    from psycopg import Error
    try:
        with mailbox.transaction() as database:
            bus.operator(database, args.operator_capability)
            if args.wake_root:
                configured = binding(bus, database)
                root = args.wake_root.resolve()
                if configured is None or root != Path(configured['root']):
                    raise BusError('authorization_denied', 'Wake scope must match the bus-pinned permission root')
                if args.status:
                    return dict(message_id=args.message_id, policy=store.policy_status(scope_for_wake(root), args.message_id))
                record = find_record(root, args.message_id).record
                if record['status'] != 'pending' or record.get('native_delivery'):
                    raise BusError('not_processable', 'Only a pending wake without unresolved effects may be escalated')
                message = wake_message(root, record, original_submission_expiry(record))
                exact = native_identity(record['target'])
            else:
                row = mailbox._row(database, args.message_id)
                if args.status:
                    return dict(message_id=args.message_id, policy=store.policy_status('a2a:' + bus.bus_id, args.message_id))
                if row['admission'] != 'accepted' or row['notification'] not in ('pending', 'deferred', 'published'):
                    raise BusError('not_processable', 'Only a pending notification may be escalated')
                envelope = json.loads(row['envelope'])
                payload = database.execute('SELECT body FROM mail_bodies WHERE message_id=?', (args.message_id,)).fetchone()
                if payload is None:
                    raise BusError('not_processable', 'The original payload is unavailable')
                message = direct_message(envelope, payload[0])
                exact = row['recipient_key']
            now = stable_micros(snapshot(), upper=True)
            if now is None or now >= message.expires_at_micros:
                raise BusError('time_uncertain', 'The original deadline is expired or cannot be verified')
            authorization = bus.event(database, 'operator', 'message_intervention_authorized',
                                      dict(message_id=message.identifier, recipient=exact,
                                           override_dnd=args.override_dnd, turn_id=args.interrupt_turn))
            database.execute('COMMIT')
        store.intervene(message, exact, override=args.override_dnd, turn_id=args.interrupt_turn,
                        actor=authorization)
    except ValueError as error:
        raise BusError('intervention_denied', str(error)) from None
    except Error:
        raise BusError('message_store_unavailable', 'Could not commit the intervention') from None
    return dict(message_id=message.identifier, recipient=exact, authorization=authorization,
                delivery='pending', interruption='requested' if args.interrupt_turn else None,
                override_dnd=args.override_dnd)
