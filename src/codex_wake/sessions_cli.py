"""Session CLI; metadata only, with explicit source and selection outcomes."""
from __future__ import annotations

import argparse
import json
import os
import time

from .records import WakeError, parse_duration
from .sessions import SelectionError, observe, resolve


def add_sessions_parser(subparsers):
    parser = subparsers.add_parser('sessions', help='discover live Codex sessions by exact thread or Byobu tab')
    commands = parser.add_subparsers(dest='sessions_command', required=True)
    for verb in ('open', 'close'):
        command = commands.add_parser(verb)
        command.add_argument('--json', dest='as_json', action='store_true')
        command.add_argument('--app-server', default='unix://')
        command.add_argument('--tmux-socket')
        command.add_argument('--tmux-session')
        command.add_argument('--timeout', type=float, default=30)
        if verb == 'open':
            mode = command.add_mutually_exclusive_group(required=True)
            mode.add_argument('--new', action='store_true')
            mode.add_argument('--resume')
            command.add_argument('--cwd')
            command.add_argument('--name', required=True)
            command.add_argument('--codex-path', default='codex')
            command.add_argument('--extra-attachment', action='store_true')
        else:
            command.add_argument('selector')
            command.add_argument('--force', action='store_true')
            command.add_argument('--bus-root', action='append', default=[],
                                 help='also inspect this explicitly located durable mailbox bus')
    for verb in ['list', 'show', 'resolve', 'current', 'watch']:
        command = commands.add_parser(verb)
        command.add_argument('--json', dest='as_json', action='store_true')
        command.add_argument('--app-server', default='unix://')
        command.add_argument('--tmux-socket')
        command.add_argument('--tmux-session')
        command.add_argument('--timeout', type=float, default=10)
        if verb in ('show', 'resolve'):
            command.add_argument('selector')
        if verb == 'resolve':
            command.add_argument('--require-attested', action='store_true')
        if verb in ('list', 'watch'):
            command.add_argument('--roots-only', action='store_true')
            command.add_argument('--state', choices=['active', 'idle', 'unknown'])
            command.add_argument('--cwd')
            command.add_argument('--all-panes', action='store_true')
            command.add_argument('--limit', type=int, default=1000)
        if verb == 'watch':
            command.add_argument('selector', nargs='?')
            command.add_argument('--interval', type=float, default=5)
            command.add_argument('--duration', default='5m')


def selected_rows(snapshot, args):
    rows = snapshot['sessions']
    if not args.all_panes:
        rows = [r for r in rows if r['binding_status'] != 'not_codex']
    if args.roots_only:
        rows = [r for r in rows if r['parent_thread_id'] is None]
    if args.state:
        rows = [r for r in rows if r['runtime_state'] == args.state]
    if args.cwd:
        rows = [r for r in rows if r['cwd'] == args.cwd]
    if args.limit <= 0:
        raise WakeError('--limit must be positive')
    return dict(snapshot, sessions=rows[:args.limit], truncated=len(rows) > args.limit)


def emit(value, as_json):
    if as_json:
        print(json.dumps(value, sort_keys=True), flush=True)
    elif 'sessions' in value:
        print('TAB\tTHREAD\tSTATE\tBINDING\tNAME\tCWD')
        for row in value['sessions']:
            tabs = ','.join(p['window_index'] + ':' + p['window_name'] for p in row['attachments']) or '-'
            print('\t'.join(str(x or '-') for x in (tabs, row['thread_id'], row['runtime_state'],
                                                    row['binding_status'], row['name'], row['cwd'])))
        if not value['complete']:
            print('Sources incomplete: ' + json.dumps(value['sources'], sort_keys=True))
    else:
        print(json.dumps(value, indent=2, sort_keys=True), flush=True)


def _sessions_command(args):
    if not 0 < args.timeout <= 60:
        raise WakeError('--timeout must be positive and at most 60 seconds')
    kwargs = dict(endpoint=args.app_server, socket_path=args.tmux_socket, timeout=args.timeout)
    snapshot = observe(**kwargs)
    try:
        verb = args.sessions_command
        if verb == 'list':
            emit(selected_rows(snapshot, args), args.as_json)
            return 0 if snapshot['complete'] else 5
        if verb == 'watch':
            return watch(args, snapshot, kwargs)
        selector = getattr(args, 'selector', None)
        if verb == 'current':
            thread_id = os.environ.get('CODEX_THREAD_ID')
            if not thread_id:
                raise SelectionError(6, 'invoking thread identity is unavailable', 'current')
            selector = 'thread:' + thread_id
        row = resolve(snapshot, selector, session=args.tmux_session, eligible=verb != 'show',
                      require_attested=getattr(args, 'require_attested', False))
        # An inherited pane is never attached to the current thread by claim alone.
        if verb == 'current' and os.environ.get('TMUX_PANE'):
            if snapshot['sources']['tmux']['availability'] != 'available':
                raise SelectionError(5, 'invoking pane source is unavailable', 'current')
            pane = os.environ['TMUX_PANE']
            other = [r for r in snapshot['sessions'] for p in r['attachments']
                     if p['pane_id'] == pane and r['thread_id'] != row['thread_id']]
            if other:
                raise SelectionError(6, 'inherited pane conflicts with invoking thread', 'current')
        emit(dict(schema_version=1, observed_at=snapshot['observed_at'], complete=snapshot['complete'],
                  sources=snapshot['sources'], session=row), args.as_json)
        return 0
    except SelectionError as exc:
        emit(dict(code=exc.code, message=str(exc), selector=exc.selector, candidates=exc.candidates,
                  sources=snapshot['sources']), args.as_json)
        return exc.code


def watch(args, snapshot, kwargs):
    if not 1 <= args.interval <= 60:
        raise WakeError('--interval must be between 1 and 60 seconds')
    duration = parse_duration(args.duration).total_seconds()
    if duration > 3600:
        raise WakeError('--duration must be at most 1 hour')
    pinned = None
    if args.selector:
        pinned = resolve(snapshot, args.selector, session=args.tmux_session)['thread_id']
    deadline = time.monotonic() + duration
    previous = None
    count = 0
    try:
        while True:
            current = selected_rows(snapshot, args)
            if pinned:
                current['sessions'] = [r for r in snapshot['sessions'] if r['thread_id'] == pinned]
            if previous is None:
                emit(dict(event='initial', **current), args.as_json)
            else:
                for source, report in current['sources'].items():
                    before = previous['sources'][source]['availability']
                    after = report['availability']
                    if before != after:
                        emit(dict(event='source_recovered' if after == 'available' else 'source_unavailable',
                                  source=source, observed_at=current['observed_at'],
                                  snapshot=current if after == 'available' else None), args.as_json)
                if current['complete'] and previous['complete'] and not current['truncated'] and not previous['truncated']:
                    def keyed(value):
                        return {r['thread_id'] or 'pane:' + r['attachments'][0]['pane_id']: r for r in value['sessions']}
                    old, new = keyed(previous), keyed(current)
                    for key in sorted(old.keys() | new.keys()):
                        event = ('session_added' if key not in old else 'session_removed' if key not in new
                                 else 'status_changed' if old[key]['provider_status'] != new[key].get('provider_status')
                                 else 'attachment_changed' if old[key]['attachments'] != new[key]['attachments'] else None)
                        if event:
                            emit(dict(event=event, identity=key, observed_at=current['observed_at'],
                                      session=new.get(key)), args.as_json)
            previous = current
            count += 1
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            time.sleep(min(args.interval, remaining))
            snapshot = observe(**kwargs)
    except KeyboardInterrupt:
        pass
    emit(dict(event='summary', observations=count, pinned_thread_id=pinned,
              complete=snapshot['complete']), args.as_json)
    return 0 if snapshot['complete'] else 5


def sessions_command(args):
    try:
        return _sessions_command(args)
    except WakeError as exc:
        emit(dict(code=2, message=str(exc), selector=getattr(args, 'selector', None),
                  candidates=[], sources={}), args.as_json)
        return 2
