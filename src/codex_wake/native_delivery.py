"""Native queue delivery for durable wakes; acceptance is not execution proof."""
from __future__ import annotations

import argparse
from datetime import timedelta
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time
from uuid import UUID, uuid4

from .native_protocol import native_request
from .records import WakeError, append_event, format_utc, parse_duration, parse_timestamp, replace_record, utc_now


def add_native_parser(subparsers):
    native = subparsers.add_parser('native', help='schedule an exact-thread native Codex wake')
    commands = native.add_subparsers(dest='native_command', required=True)
    reconcile = commands.add_parser('reconcile', help='inspect native evidence without resubmitting')
    reconcile.add_argument('wake_id')
    for verb in ('after', 'at', 'file'):
        command = commands.add_parser(verb)
        command.add_argument('--codex-path', default='codex')
        command.add_argument('--endpoint', default='unix://')
        command.add_argument('--ttl', default='24h', help='expiry after time due, or after file registration')
        command.add_argument('--resume-missing', action='store_true',
                             help='explicitly resume the same saved thread when it is not loaded')
        command.add_argument('thread_id')
        command.add_argument('trigger')
        command.add_argument('prompt', nargs=argparse.REMAINDER)


def create_native(args, root):
    from .app_server import resolve_codex_cmd
    from .cli import create_record
    try:
        args.thread_id = str(UUID(args.thread_id))
    except ValueError:
        raise WakeError('native target requires an exact thread UUID') from None
    if not args.endpoint.startswith('unix://'):
        raise WakeError('native target requires a local unix:// endpoint')
    now = utc_now()
    if args.native_command == 'file':
        predicate = {'type': 'file_exists', 'path': str(Path(args.trigger).resolve())}
        due = now
    else:
        due = now + parse_duration(args.trigger) if args.native_command == 'after' else parse_timestamp(args.trigger)
        predicate = {'type': 'not_before', 'due_at': format_utc(due)}
    ttl = parse_duration(args.ttl)
    if ttl.total_seconds() <= 0:
        raise WakeError('native expiry must be positive')
    target = {'transport': 'native', 'thread_id': args.thread_id,
              'codex_cmd': resolve_codex_cmd(args.codex_path, required=True),
              'endpoint': args.endpoint, 'expires_at': format_utc(due + ttl),
              'resume_policy': 'same_thread' if args.resume_missing else 'hold'}
    return create_record(args.prompt, predicate, root, now, args, target=target)


def read_native_thread(target):
    from .shared_app_server import SharedAppServerReader, locate_shared_endpoint
    endpoint = target['endpoint']
    if endpoint == 'unix://':
        endpoint = locate_shared_endpoint(codex_cmd=target['codex_cmd'])
    with SharedAppServerReader(endpoint) as reader:
        return reader.read_thread(target['thread_id'])


def expire_native(root, found, now):
    target = found.record.get('target', {})
    if target.get('transport') != 'native' or now < parse_timestamp(target['expires_at']):
        return False
    from .records import WakeLifecycleLock, find_record
    with WakeLifecycleLock(root, found.record['id']):
        current = find_record(root, found.record['id'])
        if current.record['status'] != 'pending':
            return False
        record = dict(current.record, status='failed', last_error='native wake expired')
        record = append_event(record, 'expired', 'native wake expired without submission', now)
        replace_record(root, current, record)
    return True


def dispatch_native(root, found, now):
    from .injector import DispatchResult
    record = dict(found.record)
    target = record['target']
    existing = record.get('native_delivery', {})
    if existing.get('state') == 'uncertain':
        return reconcile_native(root, found, now)
    if now >= parse_timestamp(target['expires_at']):
        record['status'] = 'failed'
        record = append_event(record, 'expired', 'native recipient deadline elapsed', now)
        replace_record(root, found, record)
        return DispatchResult('failed', 'native recipient deadline elapsed')
    try:
        thread = read_native_thread(target)
        if (thread.get('id') == target['thread_id']
                and thread.get('status', {}).get('type') == 'notLoaded'
                and target.get('resume_policy') == 'same_thread'):
            resumed = native_request(target['endpoint'], target['codex_cmd'], 'thread/resume',
                                     {'threadId': target['thread_id']}, 10)
            if resumed.get('thread', {}).get('id') != target['thread_id']:
                raise WakeError('native resume returned a different thread')
            record = append_event(record, 'native_same_thread_resumed',
                                  'explicit workflow policy resumed its exact saved thread', now)
            thread = read_native_thread(target)
        ready = thread.get('id') == target['thread_id'] and thread.get('status', {}).get('type') == 'idle'
    except Exception:
        ready = False
    if not ready:
        record['status'] = 'pending'
        record['next_attempt_at'] = format_utc(now + timedelta(seconds=5))
        record = append_event(record, 'native_held', 'exact recipient is not available and idle', now)
        replace_record(root, found, record)
        return DispatchResult('requeued', 'exact recipient is not available and idle')
    # Persist ambiguity BEFORE making the external effect. A crashed caller must
    # never assume the queue did not accept its submission.
    record['native_delivery'] = {'state': 'uncertain', 'execution': 'not_observed',
                                 'acknowledgment': 'not_observed',
                                 'submission_id': str(uuid4())}
    prompt = native_prompt(root, record)
    record['native_delivery']['prompt_sha256'] = hashlib.sha256(prompt.encode()).hexdigest()
    record = append_event(record, 'native_submission_started', 'native queue submission started', now)
    replace_record(root, found, record)
    env = dict(os.environ)
    for key in ('CODEX_THREAD_ID', 'TMUX', 'TMUX_PANE'):
        env.pop(key, None)
    try:
        remote = ['--remote', target['endpoint']] if target['endpoint'] != 'unix://' else []
        result = subprocess.run([target['codex_cmd'], 'queue', *remote, '--thread', target['thread_id'],
                                 '--message', prompt], env=env, capture_output=True, text=True, timeout=30)
        match = re.fullmatch(r'Queued message ([0-9a-f-]{36}) for thread '+re.escape(target['thread_id'])+r'\.\s*', result.stdout)
        if result.returncode or match is None:
            raise WakeError('native queue did not confirm exact acceptance')
        UUID(match[1])
    except Exception as exc:
        record['last_error'] = 'uncertain native submission: ' + type(exc).__name__
        record = append_event(record, 'native_uncertain', record['last_error'], now)
        replace_record(root, found, record)
        return DispatchResult('skipped', record['last_error'])
    record['status'] = 'submitted'
    record['native_delivery'].update(state='accepted', queue_id=match[1], accepted_at=format_utc(now))
    record = append_event(record, 'native_accepted', 'native queue accepted; execution not yet observed', now)
    replace_record(root, found, record)
    return DispatchResult('submitted', 'native queue accepted')


def native_prompt(root, record):
    prefix = f"WAKE_TRIGGER_ID={record['id']}\nWAKE_TRIGGER_ROOT={root.resolve()}\n"
    submission = record.get('native_delivery', {}).get('submission_id')
    if submission:
        prefix += f"WAKE_NATIVE_SUBMISSION_ID={submission}\n"
    return prefix + record['prompt']


def native_evidence(target, prompt):
    """Observe only the selected thread; return identities, never conversation bodies."""
    deadline = time.monotonic() + 10
    def request(method, params):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise WakeError('native reconciliation observation timed out')
        return native_request(target['endpoint'], target['codex_cmd'], method, params, remaining)
    def exact(items):
        return (isinstance(items, list) and len(items) == 1
                and items[0].get('type') == 'text' and items[0].get('text') == prompt)
    evidence = {}
    cursor = None
    for _ in range(10):
        page = request('thread/queue/list', dict(threadId=target['thread_id'], limit=100, cursor=cursor))
        for queued in page['data']:
            if exact(queued['input']):
                identity = queued['clientUserMessageId']
                if identity in evidence and evidence[identity].get('queue_id') != queued['id']:
                    return None, 'multiple_native_submissions'
                evidence[identity] = dict(source='native_queue', queue_id=queued['id'],
                                          client_message_id=identity, execution='not_observed')
        cursor = page.get('nextCursor')
        if not cursor:
            break
    else:
        raise WakeError('native queue observation exceeded its page bound')
    thread = request('thread/read', dict(threadId=target['thread_id'], includeTurns=True))['thread']
    if thread['id'] != target['thread_id']:
        raise WakeError('native evidence returned a different thread')
    for turn in thread['turns']:
        for item in turn['items']:
            if item.get('type') == 'userMessage' and exact(item.get('content')):
                identity = item.get('clientId') or item['id']
                previous = evidence.get(identity, {})
                if previous.get('source') == 'native_turn' and (
                        previous['turn_id'] != turn['id'] or previous['user_message_id'] != item['id']):
                    return None, 'multiple_native_submissions'
                evidence[identity] = dict(previous, source='native_turn', turn_id=turn['id'],
                    user_message_id=item['id'], client_message_id=identity,
                    execution='turn_' + turn['status'])
    if len(evidence) != 1:
        return None, 'no_exact_native_evidence' if not evidence else 'multiple_native_submissions'
    return next(iter(evidence.values())), None


def reconcile_native(root, found, now, *, force=False):
    from .injector import DispatchResult
    record = dict(found.record)
    delivery = dict(record.get('native_delivery', {}))
    if delivery.get('state') != 'uncertain':
        return DispatchResult('skipped', 'native submission is not uncertain')
    if not force and delivery.get('next_reconciliation_at') and now < parse_timestamp(delivery['next_reconciliation_at']):
        return DispatchResult('skipped', 'native reconciliation observation deferred')
    prompt = native_prompt(root, record)
    try:
        if delivery.get('prompt_sha256') and delivery['prompt_sha256'] != hashlib.sha256(prompt.encode()).hexdigest():
            raise WakeError('native submission payload changed')
        evidence, reason = native_evidence(record['target'], prompt)
    except Exception as exc:
        evidence, reason = None, 'native_evidence_unavailable:' + type(exc).__name__
    if evidence is None:
        previous_reason = delivery.get('reconciliation', {}).get('reason')
        delivery.update(reconciliation=dict(state='unresolved', reason=reason, checked_at=format_utc(now)),
                        next_reconciliation_at=format_utc(now + timedelta(seconds=5)))
        record['native_delivery'] = delivery
        if reason != previous_reason:
            record = append_event(record, 'native_unresolved', reason, now)
        replace_record(root, found, record)
        return DispatchResult('skipped', 'native submission unresolved; no resend')
    delivery.update(state='accepted', reconciled=True, evidence=evidence,
                    execution=evidence['execution'], acknowledgment='not_observed',
                    reconciliation=dict(state='resolved', checked_at=format_utc(now)))
    if evidence.get('queue_id'):
        delivery['queue_id'] = evidence['queue_id']
    record.update(status='submitted', native_delivery=delivery)
    record = append_event(record, 'native_reconciled', 'exact native evidence confirms acceptance; no resend', now)
    replace_record(root, found, record)
    return DispatchResult('submitted', 'native acceptance reconciled')


def reconcile_command(args, root):
    from .records import WakeLifecycleLock, find_record
    with WakeLifecycleLock(root, args.wake_id):
        found = find_record(root, args.wake_id)
        if found.record.get('target', {}).get('transport') != 'native':
            raise WakeError('reconciliation requires a native wake')
        result = reconcile_native(root, found, utc_now(), force=True)
        current = find_record(root, args.wake_id).record
    print(json.dumps(dict(wake_id=args.wake_id, result=result.status,
                         status=current['status'], native_delivery=current.get('native_delivery')), sort_keys=True))
    return 0
