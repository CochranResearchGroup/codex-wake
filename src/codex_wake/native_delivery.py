"""Native queue delivery for durable wakes; acceptance is not execution proof."""
from __future__ import annotations

import argparse
from datetime import timedelta
import os
from pathlib import Path
import re
import subprocess
from uuid import UUID

from .records import WakeError, append_event, format_utc, parse_duration, parse_timestamp, replace_record, utc_now


def add_native_parser(subparsers):
    native = subparsers.add_parser('native', help='schedule an exact-thread native Codex wake')
    commands = native.add_subparsers(dest='native_command', required=True)
    for verb in ('after', 'at', 'file'):
        command = commands.add_parser(verb)
        command.add_argument('--codex-path', default='codex')
        command.add_argument('--endpoint', default='unix://')
        command.add_argument('--ttl', default='24h', help='expiry after time due, or after file registration')
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
              'endpoint': args.endpoint, 'expires_at': format_utc(due + ttl)}
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
        return DispatchResult('skipped', 'native submission requires reconciliation')
    if now >= parse_timestamp(target['expires_at']):
        record['status'] = 'failed'
        record = append_event(record, 'expired', 'native recipient deadline elapsed', now)
        replace_record(root, found, record)
        return DispatchResult('failed', 'native recipient deadline elapsed')
    try:
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
                                 'acknowledgment': 'not_observed'}
    record = append_event(record, 'native_submission_started', 'native queue submission started', now)
    replace_record(root, found, record)
    env = dict(os.environ)
    for key in ('CODEX_THREAD_ID', 'TMUX', 'TMUX_PANE'):
        env.pop(key, None)
    prompt = (f"WAKE_TRIGGER_ID={record['id']}\nWAKE_TRIGGER_ROOT={root.resolve()}\n"
              + record['prompt'])
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
