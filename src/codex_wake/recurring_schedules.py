"""Wake-owned schedules; each original occurrence feeds the existing native core."""
from __future__ import annotations

import contextlib
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import io
import json
import math
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

from .records import WakeError, WakeLifecycleLock, all_records
from .wake_policy import _read, _write

MAX_POLL_OCCURRENCES = 256
TERMINAL = {'cancelled', 'failed', 'expired', 'archived', 'skipped', 'coalesced'}


def timestamp(value):
    from .network_wakes import precise_deadline
    return precise_deadline(value).astimezone(timezone.utc)


def iso(value):
    return value.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')


def positive(value, name, *, integer=False):
    if type(value) not in ((int,) if integer else (int, float)) or not math.isfinite(value) or value <= 0:
        raise WakeError('invalid_' + name)
    return value


def validate_request(request):
    required = {'idempotency_key', 'thread_id', 'prompt', 'session_mode', 'cadence', 'end', 'missed', 'overlap', 'delivery_window_seconds'}
    if not isinstance(request, dict) or set(request) != required:
        raise WakeError('explicit_schedule_fields_required: ' + ','.join(sorted(required)))
    from .wake_session_modes import MODES
    if request['session_mode'] not in MODES:
        raise WakeError('explicit_session_mode_required')
    try:
        if str(UUID(request['thread_id'])) != request['thread_id']:
            raise ValueError()
    except (ValueError, TypeError, AttributeError):
        raise WakeError('exact_schedule_thread_required') from None
    for key, maximum in (('prompt', 32768), ('idempotency_key', 160)):
        if not isinstance(request[key], str) or not request[key].strip() or len(request[key].encode()) > maximum:
            raise WakeError('invalid_schedule_' + key)
    positive(request['delivery_window_seconds'], 'delivery_window')
    cadence = request['cadence']
    if not isinstance(cadence, dict):
        raise WakeError('invalid_cadence')
    if cadence.get('kind') == 'interval':
        if set(cadence) != {'kind', 'seconds', 'start_at'}:
            raise WakeError('explicit_interval_fields_required')
        positive(cadence['seconds'], 'interval')
        start = timestamp(cadence['start_at'])
        try:
            start + timedelta(seconds=cadence['seconds'])
        except (OverflowError, ValueError):
            raise WakeError('interval_outside_supported_calendar') from None
    elif cadence.get('kind') == 'clock':
        from .recurring_calendar import validate_cadence
        validate_cadence(cadence)
    else:
        raise WakeError('unsupported_schedule_cadence')
    end = request['end']
    if not isinstance(end, dict):
        raise WakeError('explicit_end_required')
    if end.get('kind') == 'count' and set(end) == {'kind', 'count'}:
        positive(end['count'], 'occurrence_count', integer=True)
    elif end.get('kind') == 'until' and set(end) == {'kind', 'at'}:
        timestamp(end['at'])
    elif end != {'kind': 'until_cancelled'}:
        raise WakeError('explicit_end_required')
    for key, policies in (('missed', {'skip', 'latest', 'catch_up'}), ('overlap', {'skip', 'latest', 'queue'})):
        policy = request[key]
        if not isinstance(policy, dict) or policy.get('policy') not in policies:
            raise WakeError('explicit_' + key + '_policy_required')
        fields = {'policy', 'max_lateness_seconds'} if key == 'missed' else {'policy'}
        if key == 'missed':
            positive(policy['max_lateness_seconds'], 'maximum_lateness')
        if policy['policy'] in ('catch_up', 'queue'):
            fields.add('limit')
            positive(policy.get('limit'), key + '_bound', integer=True)
            if policy['limit'] > MAX_POLL_OCCURRENCES:
                raise WakeError('schedule_bound_exceeds_256')
        if set(policy) != fields:
            raise WakeError('invalid_' + key + '_fields')
    return deepcopy(request)


def first_due(cadence):
    if cadence['kind'] == 'interval':
        return timestamp(cadence['start_at'])
    from .recurring_calendar import first_due as calendar_first
    return timestamp(calendar_first(cadence))


def next_due(cadence, due):
    if cadence['kind'] == 'interval':
        return due + timedelta(seconds=cadence['seconds'])
    from .recurring_calendar import next_due as calendar_next
    return timestamp(calendar_next(cadence, iso(due)))


class ScheduleStore:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.directory = self.root / 'schedules'

    def path(self, schedule_id):
        if not isinstance(schedule_id, str) or len(schedule_id) != 41 or not schedule_id.startswith('schedule_') or any(c not in '0123456789abcdef' for c in schedule_id[9:]):
            raise WakeError('invalid_schedule_id')
        return self.directory / (schedule_id + '.json')

    def read(self, schedule_id):
        value = _read(self.path(schedule_id))
        if value.get('version') != 1 or value.get('id') != schedule_id or value.get('root') != str(self.root):
            raise WakeError('invalid_schedule_record')
        validate_request(value['request'])
        return value

    def records(self):
        return [self.read(p.stem) for p in sorted(self.directory.glob('schedule_*.json'))]

    def save(self, value):
        _write(self.path(value['id']), value)

    def register(self, request, *, codex_path='codex', endpoint='unix://', principal=None):
        request = validate_request(request)
        key = request['idempotency_key']
        identifier = 'schedule_' + hashlib.sha256(key.encode()).hexdigest()[:32]
        with WakeLifecycleLock(self.root, 'recurring-schedules'):
            if self.path(identifier).exists():
                old = self.read(identifier)
                if old['request'] != request:
                    raise WakeError('idempotency_conflict: schedule differs')
                self.authorize(old, principal)
                return self.receipt(old)
            due = first_due(request['cadence'])
            args = self.native_args(request, due, 'schedule-admission:' + identifier, codex_path, endpoint)
            args._permission_principal = principal
            from .native_intents import _request
            _, content, *_ = _request(args, self.root)
            # Policy provenance is frozen once; dispatch rechecks current permissions.
            policy = content.get('wake_policy')
            value = dict(version=1, id=identifier, root=str(self.root), revision=1, state='enabled',
                request=request, target=content['target'], wake_policy=policy,
                next_due_at=iso(due), next_index=0, occurrences=[], revisions=[])
            self.save(value)
            return self.receipt(value)

    @staticmethod
    def native_args(request, due, key, codex_path, endpoint):
        return SimpleNamespace(native_command='at', thread_id=request['thread_id'], trigger=iso(due),
            ttl=str(request['delivery_window_seconds'])+'s', prompt=[request['prompt']],
            codex_path=codex_path, endpoint=endpoint, resume_missing=False,
            wake_policy_enabled=True, wake_lifetime=None, recipient_startup=None,
            owner_id=None, owner_end=None, session_mode=request['session_mode'],
            wake_routes=None, idempotency_key=key, time_tolerance='5m', stop_at=None,
            as_json=True, require_monitor=False, busy_policy='wait')

    def authorize(self, value, principal):
        context = (value.get('wake_policy') or {}).get('permission_context')
        if context and (principal is None or principal.role != 'operator' and principal.subject != context['subject']):
            raise WakeError('schedule_authority_denied')

    def receipt(self, value):
        from .monitor import read_monitor_health
        from .signal_records import probe_managed_reader_capability
        health = read_monitor_health(self.root) or {}
        reader = probe_managed_reader_capability(self.root)
        ready = bool(reader and 8 in reader.schema_versions and health.get('mode') == 'loop')
        return dict(value, session_mode=value['request']['session_mode'],
            armed=ready and value['state'] == 'enabled',
            scheduling_status='armed' if ready and value['state']=='enabled' else 'retained_unmonitored' if not ready and value['state']=='enabled' else value['state'],
            monitor=dict(ready=ready, wake_root=str(self.root)))

    def emit(self, value, occurrence):
        due = timestamp(occurrence['due_at'])
        request = occurrence['request']
        target = occurrence['target']
        args = self.native_args(request, due, occurrence['id'], target['codex_cmd'], target['endpoint'])
        args._schedule_target = target
        args._schedule_wake_policy = occurrence['wake_policy']
        from .native_intents import retain
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            retain(args, self.root)
        occurrence['wake_id'] = json.loads(output.getvalue())['id']
        occurrence['state'] = 'pending'


def poll_schedules(root, clock):
    """Bounded scheduling only; existing daemon owns native dispatch and evidence."""
    store = ScheduleStore(root)
    if not store.directory.exists():
        return []
    from .native_intents import valid_utc
    if not valid_utc(clock.get('utc')):
        return []
    now = clock['utc']['lower']
    results = []
    with WakeLifecycleLock(store.root, 'recurring-schedules'):
        wakes = {w.record['id']: w.record for w in all_records(store.root, include_archive=True)}
        for value in store.records():
            if value['state'] not in ('enabled', 'exhausted'):
                continue
            from .wake_session_modes import session_state
            state = session_state(value['target'])
            if state == 'closed':
                value['state'] = 'cancelled'
                value['reason'] = 'session_closed'
                store.save(value)
                continue
            if state == 'unknown':
                value['attention'] = 'session_owner_unverified'
                store.save(value)
                continue
            for item in value['occurrences']:
                wake = wakes.get(item.get('wake_id'))
                if wake:
                    item['state'] = wake['status']
                    if wake.get('native_delivery', {}).get('execution') == 'completed':
                        item['state'] = 'completed'
            request = value['request']
            newly_due = []
            for _ in range(MAX_POLL_OCCURRENCES):
                due = timestamp(value['next_due_at'])
                end = request['end']
                if (end['kind'] == 'count' and value['next_index'] >= end['count'] or
                        end['kind'] == 'until' and due >= timestamp(end['at'])):
                    value['state'] = 'exhausted'
                    break
                if due.timestamp() > now:
                    break
                index = value['next_index']
                occurrence = dict(id=f"{value['id']}:{value['revision']}:{index}", revision=value['revision'], index=index,
                    due_at=iso(due), expires_at=iso(due+timedelta(seconds=request['delivery_window_seconds'])),
                    state='queued', request=deepcopy(request), target=deepcopy(value['target']), wake_policy=deepcopy(value['wake_policy']))
                value['occurrences'].append(occurrence)
                newly_due.append(occurrence)
                value['next_index'] += 1
                try:
                    value['next_due_at'] = iso(next_due(request['cadence'], due))
                except (ValueError, OverflowError):
                    value['state'] = 'attention'
                    value['attention'] = 'cadence_outside_supported_calendar'
                    break
            # Save occurrence identity before any downstream registration.
            store.save(value)
            eligible = []
            for item in value['occurrences']:
                if item['state'] != 'queued':
                    continue
                lateness = now - timestamp(item['due_at']).timestamp()
                if now >= timestamp(item['expires_at']).timestamp() or lateness > item['request']['missed']['max_lateness_seconds']:
                    item['state'] = 'expired'
                else:
                    eligible.append(item)
            missed = request['missed']
            behind = [item for item in newly_due if item in eligible and timestamp(item['due_at']).timestamp() < now]
            if missed['policy'] == 'skip':
                for item in behind:
                    item['state'] = 'skipped'
            elif missed['policy'] == 'latest' and len(eligible) > 1:
                for item in eligible[:-1]:
                    item['state'] = 'coalesced'
            elif missed['policy'] == 'catch_up':
                for item in eligible[:-missed['limit']]:
                    item['state'] = 'skipped'
            pending = [item for item in value['occurrences'] if item['state'] == 'queued']
            active = any(item['state'] in ('pending', 'firing', 'submitted') for item in value['occurrences'])
            overlap = request['overlap']
            if active:
                if overlap['policy'] == 'skip':
                    for item in pending: item['state'] = 'skipped'
                elif overlap['policy'] == 'latest':
                    for item in pending[:-1]: item['state'] = 'coalesced'
                elif len(pending) > overlap['limit']:
                    for item in pending[:-overlap['limit']]: item['state'] = 'skipped'
            elif pending and (value['state'] == 'exhausted' or timestamp(value['next_due_at']).timestamp() > now):
                candidate = pending[0]
                store.save(value)
                try:
                    store.emit(value, candidate)
                except (WakeError, OSError, ValueError) as exc:
                    candidate['state'] = 'attention'
                    candidate['reason'] = str(exc)
                    value['attention'] = str(exc)
            store.save(value)
            results.append(store.receipt(value))
    return results
