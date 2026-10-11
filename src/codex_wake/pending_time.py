"""Durable native scheduling intents whose UTC origin is not yet bounded."""
from datetime import timedelta
import hashlib
import json
import os
from pathlib import Path
from uuid import uuid4

from .network_wakes import creation_time, mark_network_record, precise_deadline
from .records import (
    WakeError, WakeLifecycleLock, all_records, build_record, normalize_prompt,
    parse_duration, write_record,
)
from .time_provider import NETWORK_TIME_POLICY


def _stamp(value):
    return value.isoformat().replace('+00:00', 'Z')


def _intent(args):
    ttl = int(parse_duration(args.ttl).total_seconds())
    intent = {'kind': args.native_command, 'ttl_seconds': ttl, 'provider': 'stable-time',
              'origin_policy': 'first_finite_upper_bound'}
    if args.native_command == 'after':
        intent['delay_seconds'] = int(parse_duration(args.trigger).total_seconds())
    elif args.native_command == 'at':
        due = precise_deadline(args.trigger)
        intent.update(due_at=_stamp(due), expires_at=_stamp(due + timedelta(seconds=ttl)))
    else:
        intent['path'] = str(Path(args.trigger).resolve())
    return intent


def _sync(path):
    # The receipt is accepted only once its file and rename are durable.
    for selected in (path, path.parent):
        descriptor = os.open(selected, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


def _stable_time_observation(observation):
    return (observation is not None and observation.status == 'network'
            and len(set(observation.sources)) >= 2
            and all(source.startswith('stable-time:') for source in observation.sources))


def admissible_intent_observation(record, observation):
    """New StableTime intents keep their source authority across future polls."""
    if 'time_intent' not in record:
        return True  # Existing generic schema5 remains compatible.
    intent = record.get('time_intent')
    return (isinstance(intent, dict) and intent.get('provider') == 'stable-time'
            and _stable_time_observation(observation))


def register_intent(args, root, target, observation):
    """Persist once per overlapping identical active intent, even during an outage."""
    if not _stable_time_observation(observation):
        observation = None
    intent = _intent(args)
    prompt = normalize_prompt(args.prompt)
    if getattr(args, 'require_monitor', False):
        from .monitor import monitor_readiness, require_monitor_ready
        require_monitor_ready(monitor_readiness(wake_root=root, repo_root=Path.cwd()))
    digest = hashlib.sha256(json.dumps({'intent': intent, 'target': target, 'prompt': prompt,
                                       'cwd': str(Path.cwd().resolve())}, sort_keys=True).encode()).hexdigest()
    with WakeLifecycleLock(root, 'pending-time-intent-' + digest):
        for found in all_records(root):
            if found.record.get('intent_key') == digest and found.record.get('status') in ('pending', 'firing'):
                print(f"{found.record['id']} {found.path}")
                return 0
        target = dict(target)
        if observation is None:
            target['expires_at'] = intent.get('expires_at')
            record = {'schema_version': 6, 'id': 'wake_pending_' + uuid4().hex,
                      'created_at': None, 'updated_at': None, 'cwd': str(Path.cwd().resolve()),
                      'target': target, 'predicate': {'type': 'pending_time'}, 'prompt': prompt,
                      'status': 'pending', 'attempts': 0, 'max_attempts': 3,
                      'ack_timeout_seconds': 30, 'next_attempt_at': None,
                      'time_policy': dict(NETWORK_TIME_POLICY),
                      'time_observation': {'status': 'uncertain', 'sources': [], 'lower': None,
                                           'upper': None, 'reason': 'stable_time_unbounded_or_unavailable'},
                      'events': [{'type': 'time_intent_retained', 'at': None,
                                  'time_status': 'not_observed',
                                  'message': 'Intent retained; relative delay starts at first finite upper bound'}]}
        else:
            now = creation_time(observation)
            due = precise_deadline(intent['due_at']) if intent['kind'] == 'at' else now
            if intent['kind'] == 'after':
                due += timedelta(seconds=intent['delay_seconds'])
            predicate = ({'type': 'file_exists', 'path': intent['path']} if intent['kind'] == 'file'
                         else {'type': 'not_before', 'due_at': _stamp(due)})
            target['expires_at'] = intent.get('expires_at', _stamp(due + timedelta(seconds=intent['ttl_seconds'])))
            record = build_record(predicate=predicate, prompt=prompt, cwd=Path.cwd(), target=target, now=now)
            mark_network_record(record, observation)
        record.update(time_intent=intent, intent_key=digest)
        path = write_record(root, record)
        _sync(path)
        print(f"{record['id']} {path}")
        return 0


def valid_pending_record(record):
    """Version6 has no established UTC origin and cannot be dispatched as a timer."""
    try:
        target, intent = record['target'], record['time_intent']
        if (record['schema_version'] != 6 or record['status'] not in ('pending', 'cancelled', 'archived')
                or not isinstance(record['id'], str) or not record['id']
                or record['predicate'] != {'type': 'pending_time'}
                or type(record['attempts']) is not int or record['attempts'] != 0
                or record.get('created_at') is not None
                or record.get('next_attempt_at') is not None
                or record['time_policy'] != NETWORK_TIME_POLICY
                or record['time_observation']['status'] != 'uncertain'
                or record['time_observation']['lower'] is not None
                or record['time_observation']['upper'] is not None
                or intent['provider'] != 'stable-time'
                or intent['origin_policy'] != 'first_finite_upper_bound'
                or type(intent['ttl_seconds']) is not int or intent['ttl_seconds'] <= 0
                or target['transport'] != 'native'
                or str(__import__('uuid').UUID(target['thread_id'])) != target['thread_id']
                or not target['endpoint'].startswith('unix://')
                or not Path(target['codex_cmd']).is_absolute()
                or not isinstance(record['prompt'], str) or not record['prompt']
                or not isinstance(record.get('events'), list) or not record['events']
                or any(not isinstance(event, dict)
                       or not isinstance(event.get('type'), str) or not event['type']
                       or not isinstance(event.get('message'), str) or event.get('at') is not None
                       for event in record['events'])
                or not isinstance(record['intent_key'], str) or len(record['intent_key']) != 64):
            return False
        if intent['kind'] == 'after':
            return type(intent['delay_seconds']) is int and intent['delay_seconds'] > 0 and target['expires_at'] is None
        if intent['kind'] == 'file':
            return isinstance(intent['path'], str) and Path(intent['path']).is_absolute() and target['expires_at'] is None
        if intent['kind'] == 'at':
            due, expiry = precise_deadline(intent['due_at']), precise_deadline(intent['expires_at'])
            return expiry == due + timedelta(seconds=intent['ttl_seconds']) and target['expires_at'] == intent['expires_at']
        return False
    except (KeyError, TypeError, ValueError, AttributeError, OverflowError):
        return False


def evaluate_intent(root, identifier, provider=None):
    """Admit finite evidence once under the cancellation/dispatch lifecycle lock."""
    from .network_wakes import read_time, evaluate_native_pending
    from .records import classify_record, find_record, replace_record, append_event
    try:
        observation = read_time(provider)
    except WakeError:
        return 'pending'
    if not _stable_time_observation(observation):
        return 'pending'
    now = creation_time(observation)
    with WakeLifecycleLock(root, identifier):
        found = find_record(root, identifier)
        if classify_record(found.record) != 'native_pending_time_v6' or found.record['status'] != 'pending':
            return 'inactive'
        record = dict(found.record)
        intent = record['time_intent']
        due = precise_deadline(intent['due_at']) if intent['kind'] == 'at' else now
        if intent['kind'] == 'after':
            due += timedelta(seconds=intent['delay_seconds'])
        record['predicate'] = ({'type': 'file_exists', 'path': intent['path']} if intent['kind'] == 'file'
                               else {'type': 'not_before', 'due_at': _stamp(due)})
        record['target'] = dict(record['target'], expires_at=intent.get(
            'expires_at', _stamp(due + timedelta(seconds=intent['ttl_seconds']))))
        record.update(updated_at=_stamp(now), next_attempt_at=_stamp(due), time_admitted_at=_stamp(now))
        mark_network_record(record, observation)
        record = append_event(record, 'time_intent_admitted',
                              'Finite evidence admitted; relative origin fixed once at its upper bound', now)
        path = replace_record(root, found, record)
        _sync(path)
    return evaluate_native_pending(root, identifier, lambda: observation)
