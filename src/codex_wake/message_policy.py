"""Recipient settings and busy decisions for the shared message delivery path."""

from dataclasses import dataclass
from decimal import Decimal
import json
import math


@dataclass(frozen=True)
class Decision:
    state: str
    reason: str


READY = Decision('ready', 'recipient_ready')


def decide(observation, *, busy_policy='wait', dnd=None, override=False):
    """Apply DND before considering busy policy or an interruption."""
    if dnd and not override:
        return Decision('bounce' if dnd == 'bounce' or busy_policy == 'idle-only' else 'hold',
                        'recipient_dnd')
    if observation == 'busy':
        if busy_policy == 'idle-only':
            return Decision('bounce', 'recipient_busy')
        return Decision('hold', 'recipient_busy')
    return READY


def recipient_key(namespace, thread):
    return json.dumps([namespace, thread], separators=(',', ':'))


def stable_micros(clock, *, upper=False):
    from .native_intents import valid_utc
    utc = (clock or {}).get('utc')
    if not valid_utc(utc):
        return None
    value = Decimal(str(utc['upper' if upper else 'lower'])) * 1_000_000
    return math.ceil(value) if upper else math.floor(value)


def native_identity(target):
    from .a2a_identity import RuntimeIdentity
    from .shared_app_server import SharedAppServerReader, locate_shared_endpoint

    endpoint = target['endpoint']
    if endpoint == 'unix://':
        endpoint = locate_shared_endpoint(codex_cmd=target['codex_cmd'], timeout=5)
    with SharedAppServerReader(endpoint, timeout=5) as reader:
        identity = RuntimeIdentity.from_metadata(reader.read_thread(target['thread_id']), reader.server_metadata)
    if identity.thread_id != target['thread_id']:
        raise ValueError('message_recipient_changed')
    return recipient_key(identity.namespace, identity.thread_id)


def discover_native_identity(target):
    """Resolve ordering for available native recipients while admitting legacy records."""
    from .records import WakeError
    try:
        return native_identity(target)
    except (WakeError, OSError, TypeError, ValueError, KeyError):
        return None


def recipient_policy(store, message, *, clock, observation='ready', busy_policy='wait',
                     exact_recipient=None):
    """Read current settings. Unavailable settings hold without transport I/O."""
    from psycopg import Error

    try:
        intervention = store.intervention(message)
        setting = store.dnd(exact_recipient or message.recipient, stable_micros(clock))
    except (Error, OSError, ValueError):
        return Decision('hold', 'message_policy_unavailable'), None
    if intervention and intervention[2] != (exact_recipient or message.recipient):
        intervention = None
    # A combined request can pass the DND gate in order to interrupt. An
    # unavailable interruption restores the original DND delivery policy.
    override = bool(intervention and intervention[0] and intervention[3] != 'unavailable')
    return decide(observation, busy_policy=busy_policy, dnd=setting, override=override), intervention



def native_preflight(root, record, clock_provider, *, observation='ready', authorize=None, record_bounce=True):
    """Decide before any runtime observation that could reopen the target."""
    from .message_delivery import configured_store, wake_message
    from .native_clock import snapshot
    from .runtime_delivery import original_submission_expiry
    from .records import WakeError
    from .shared_app_server import SharedSourceError

    policy = record['target'].get('busy_policy', 'wait')
    store = configured_store(root)
    if store is None:
        return decide(observation, busy_policy=policy)
    from psycopg import Error
    try:
        message = wake_message(root, record, original_submission_expiry(record))
        intervention = store.intervention(message)
        bound = store.bound_recipient(message)
        pinned = bound[0] if bound else None
        exact = discover_native_identity(record['target'])
        if pinned and exact is not None and pinned != exact:
            return Decision('hold', 'message_policy_unavailable')
        if exact is None and (pinned or intervention or store.has_dnd(message.recipient)):
            return Decision('hold', 'message_policy_unavailable')
        if exact is not None and not pinned:
            from dataclasses import replace
            message = replace(message, order_recipient=exact)
            store.admit(message)
        clock = (clock_provider or snapshot)()
        verdict, intervention = recipient_policy(store, message, clock=clock,
                                      observation=observation, busy_policy=policy, exact_recipient=exact)
        if (verdict.state == 'ready' and intervention and intervention[1]
                and intervention[3] not in ('unavailable', 'interrupted') and authorize is not None):
            from functools import partial
            from .native_protocol import exact_message_interrupt
            target = record['target']
            transport = partial(exact_message_interrupt, target['endpoint'], target['codex_cmd'], exact,
                                target['thread_id'])
            return interrupt_decision(store, message, intervention, transport, authorize, clock_provider or snapshot)
        if verdict.state == 'bounce' and record_bounce and not store.record_bounce(message, verdict.reason):
            return Decision('hold', 'original_message_effect_requires_reconciliation')
        if verdict.state == 'ready' and record_bounce:
            waiting = store.waiting_reason(message, stable_micros(clock), stable_micros(clock, upper=True))
            if waiting:
                return Decision('hold', waiting)
        return verdict
    except (Error, OSError, ValueError, TypeError, KeyError, WakeError, SharedSourceError):
        return Decision('hold', 'message_policy_unavailable')


def persist_native_decision(root, found, record, verdict, now, clock_provider):
    from .injector import DispatchResult
    from .native_intents import defer_recipient_check
    from .records import append_event, replace_record

    bounced = verdict.state == 'bounce'
    record.update(status='cancelled' if bounced else 'pending',
                  policy_outcome=dict(state='bounced' if bounced else 'held', reason=verdict.reason))
    if bounced:
        record = append_event(record, 'message_bounced', verdict.reason, now)
    elif record.get('schema_version') in (6, 8, 9) and clock_provider is not None:
        defer_recipient_check(record, clock_provider())
    replace_record(root, found, record)
    return DispatchResult('skipped' if bounced else 'requeued', verdict.reason)


def interrupt_decision(store, message, intervention, transport, authorize, clock):
    """Verify an original turn and journal once before attempting interruption."""
    from psycopg import Error
    from .native_protocol import NativeCapabilityUnavailable
    from .records import WakeError
    from websockets.exceptions import WebSocketException

    turn = intervention[1]
    state = intervention[3]
    if state in ('interrupted', 'unavailable'):
        return READY
    try:
        if transport is None:
            if state is not None:
                return Decision('hold', 'interrupt_uncertain')
            store.disable_interrupt(message, turn)
            return Decision('hold', 'interrupt_unavailable')
        if state is not None:
            resolved = transport(turn, None)
            if resolved != 'interrupted':
                return Decision('hold', 'interrupt_uncertain')
            store.finish_interrupt(message, turn, 'interrupted')
            return Decision('hold', 'interrupt_observed')
        def begin():
            authorize()
            upper = stable_micros(clock(), upper=True)
            if upper is None or upper >= message.expires_at_micros:
                return False
            return store.begin_interrupt(message, turn)
        result = transport(turn, begin)
        if result in ('unavailable', 'turn_changed'):
            store.disable_interrupt(message, turn)
            return Decision('hold', 'interrupt_' + result)
        if result == 'requested':
            store.finish_interrupt(message, turn, 'requested')
            return Decision('hold', 'interrupt_requested')
        return Decision('hold', 'interrupt_uncertain')
    except NativeCapabilityUnavailable:
        try:
            store.disable_interrupt(message, turn)
        except (Error, OSError, ValueError):
            return Decision('hold', 'interrupt_uncertain')
        return Decision('hold', 'interrupt_unavailable')
    except (Error, OSError, ValueError, WakeError, WebSocketException):
        return Decision('hold', 'interrupt_uncertain')



def note_terminal(root, scope, identifier):
    """Release known local terminal intent when its shared delivery store is reachable."""
    from .message_delivery import configured_store
    from .records import WakeError
    try:
        store = configured_store(root)
        if store is not None:
            from psycopg import Error
            try:
                store.retire_waiting(scope, identifier)
            except Error:
                return False
    except (WakeError, ValueError, OSError):
        return False
    return True
