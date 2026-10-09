"""Network-clock operations for opt-in schema-3 deadline wakes."""
from datetime import UTC, datetime
from dataclasses import asdict
import math

from .records import WakeError
from .time_provider import NETWORK_TIME_POLICY, require_time_decision


def read_time(provider=None):
    from .time_inspection import network_time_decision
    try:
        return require_time_decision((provider or network_time_decision)())
    except (OSError,ValueError,TypeError) as error:
        raise WakeError('time_uncertain: bounded network time unavailable; retry the original intent') from error


def creation_time(decision):
    # Legacy record timestamps have whole-second precision; round upward to avoid early deadlines.
    return datetime.fromtimestamp(math.ceil(decision.upper),UTC)


def evaluation_time(decision):
    return datetime.fromtimestamp(decision.lower,UTC)


def mark_network_record(record, decision):
    record['schema_version'] = 3
    record['time_policy'] = dict(NETWORK_TIME_POLICY)
    record['time_observation'] = asdict(decision)
    return record


def evaluate_pending(root, identifier, provider=None):
    """Acquire first, then serialize and re-read before changing durable wake status."""
    from .records import WakeLifecycleLock, classify_record, find_record, move_record
    current = evaluation_time(read_time(provider))
    with WakeLifecycleLock(root,identifier):
        found = find_record(root,identifier)
        record = found.record
        if classify_record(record) != 'network_v3' or record['status'] != 'pending':
            return 'inactive'
        due = precise_deadline(record['predicate']['due_at'])
        retry = precise_deadline(record.get('next_attempt_at',record['predicate']['due_at']))
        if current < due or current < retry:
            return 'pending'
        move_record(root,found,'firing',event_type='predicate_matched',message='Network lower bound reached original deadline',now=current)
        return 'firing'


def precise_deadline(value):
    try:
        due = datetime.fromisoformat(value.replace('Z','+00:00'))
        if due.tzinfo is None:
            raise ValueError('timezone required')
        return due.astimezone(UTC)
    except ValueError as error:
        raise WakeError('deadline must be an ISO timestamp with timezone') from error
