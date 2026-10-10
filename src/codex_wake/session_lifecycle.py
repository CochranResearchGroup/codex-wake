"""Explicit visible-tab lifecycle, separate from conversation archival."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shlex
import stat
import subprocess
import time
from uuid import UUID

from . import __version__
from .records import WakeError, classify_record
from .sessions import observe, resolve, revalidate_attachment


def native_request(endpoint, codex, method, params, timeout):
    from .shared_app_server import locate_shared_endpoint
    from websockets.sync.client import unix_connect
    if endpoint == 'unix://':
        endpoint = locate_shared_endpoint(codex_cmd=codex, timeout=timeout)
    if not endpoint.startswith('unix://') or not Path(endpoint[7:]).is_absolute():
        raise WakeError('session lifecycle requires an existing local Unix endpoint')
    try:
        info = Path(endpoint[7:]).lstat()
    except OSError:
        raise WakeError('native lifecycle endpoint is unavailable') from None
    if not stat.S_ISSOCK(info.st_mode) or info.st_uid != os.geteuid():
        raise WakeError('native lifecycle endpoint must be an owned Unix socket')
    deadline = time.monotonic() + timeout
    with unix_connect(endpoint[7:], open_timeout=timeout, close_timeout=1) as ws:
        def request(identifier, name, body):
            ws.send(json.dumps({'id': identifier, 'method': name, 'params': body}))
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise WakeError('native lifecycle request timed out; inspect state before retry')
                result = json.loads(ws.recv(timeout=remaining))
                if result.get('id') != identifier:
                    continue
                if 'error' in result:
                    raise WakeError('native lifecycle request rejected: ' + name)
                return result['result']
        request(1, 'initialize', {'clientInfo': {'name': 'codex_wake_lifecycle', 'version': __version__},
                                  'capabilities': {'experimentalApi': True}})
        ws.send(json.dumps({'method': 'initialized'}))
        return request(2, method, params)


def tmux_command(args, *command):
    socket = ['-S', args.tmux_socket] if args.tmux_socket else []
    try:
        return subprocess.run(['tmux', *socket, *command], check=True, text=True,
                              capture_output=True, timeout=args.timeout).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        raise WakeError('tmux lifecycle command failed; inspect the target before retry') from None


def open_session(args):
    from .app_server import resolve_codex_cmd
    kwargs = dict(endpoint=args.app_server, socket_path=args.tmux_socket, timeout=args.timeout)
    if args.resume:
        try:
            thread_id = str(UUID(args.resume))
        except ValueError:
            raise WakeError('resume requires an exact thread UUID') from None
        snapshot = observe(**kwargs)
        if not snapshot['complete']:
            raise WakeError('complete source inventory required before opening another attachment')
        try:
            row = resolve(snapshot, 'thread:' + thread_id)
        except Exception as exc:
            from .sessions import SelectionError
            if not isinstance(exc, SelectionError) or exc.code != 3:
                raise
            row = None
        if row and row['attachments'] and not args.extra_attachment:
            return dict(action='reused', thread_id=thread_id, attachments=row['attachments'])
    else:
        if not args.cwd or not Path(args.cwd).is_dir():
            raise WakeError('new conversation requires an existing --cwd directory')
        thread_id = None
    if not args.tmux_session:
        raise WakeError('opening a tab requires an explicit --tmux-session')
    if not args.name or any(c in args.name for c in '\n\r\t'):
        raise WakeError('tab name must be nonempty and single-line')
    # Validate the destination before creating a conversation.
    tmux_command(args, 'has-session', '-t', args.tmux_session)
    codex = resolve_codex_cmd(args.codex_path, required=True)
    if thread_id is None:
        response = native_request(args.app_server, codex, 'thread/start',
                                  {'cwd': str(Path(args.cwd).resolve()), 'ephemeral': False}, args.timeout)
        thread_id = response['thread']['id']
        native_request(args.app_server, codex, 'thread/name/set',
                       {'threadId': thread_id, 'name': args.name}, args.timeout)
    metadata = native_request(args.app_server, codex, 'thread/read',
                              {'threadId': thread_id, 'includeTurns': False}, args.timeout)['thread']
    cwd = metadata['cwd']
    command = shlex.join(['env', '-u', 'CODEX_THREAD_ID', '-u', 'TMUX_PANE', codex,
                          'resume', '--no-alt-screen', '-C', cwd, thread_id])
    if args.app_server != 'unix://':
        command += ' --remote ' + shlex.quote(args.app_server)
    created = tmux_command(args, 'new-window', '-d', '-P', '-F', '#{window_id}\t#{pane_id}',
                           '-t', args.tmux_session + ':', '-n', args.name, '-c', cwd, command)
    window_id, pane_id = created.split('\t')
    # Creation and readiness are distinct. Return the exact identities even if
    # startup is delayed; never create a replacement tab on observation timeout.
    deadline = time.monotonic() + args.timeout
    while time.monotonic() < deadline:
        snapshot = observe(**kwargs)
        matches = [r for r in snapshot['sessions'] if r['thread_id'] == thread_id]
        attachments = [p for r in matches for p in r['attachments'] if p['pane_id'] == pane_id]
        if attachments:
            return dict(action='opened', ready=True, thread_id=thread_id, attachments=attachments)
        time.sleep(0.2)
    return dict(action='opened', ready=False, thread_id=thread_id, window_id=window_id,
                pane_id=pane_id, message='tab created; startup not yet verified; inspect before retry')


def close_session(args, wake_root):
    snapshot = observe(endpoint=args.app_server, socket_path=args.tmux_socket, timeout=args.timeout)
    if not snapshot['complete']:
        raise WakeError('complete source inventory required to close a tab')
    row = resolve(snapshot, args.selector, session=args.tmux_session)
    attachments = row['attachments']
    if args.selector.startswith('window:'):
        attachments = [p for p in attachments if p['window_id'] == args.selector[7:]]
    if args.selector.startswith('pane:'):
        attachments = [p for p in attachments if p['pane_id'] == args.selector[5:]]
    if len(attachments) != 1:
        raise WakeError('close requires one exact attached pane')
    attachment = attachments[0]
    panes = tmux_command(args, 'list-panes', '-t', attachment['window_id'],
                         '-F', '#{pane_id}').splitlines()
    if panes != [attachment['pane_id']]:
        raise WakeError('tab has multiple panes or changed identity; refusing tab close')
    roots = {Path(wake_root).resolve(), Path(row['cwd']) / '.codex/wake'}
    from .supervisor import default_registry_dir
    registry = default_registry_dir()
    pending = []
    if registry.exists():
        for entry in registry.glob('*.json'):
            try:
                roots.add(Path(json.loads(entry.read_text())['wake_root']).resolve())
            except (OSError, ValueError, KeyError, TypeError):
                pending.append(dict(wake_id='unknown', root=str(entry),
                                    attribution='unknown', reason='registry_unavailable'))
    # A close guard must account for damaged and unpublished records too.
    for root in roots:
        from .signal_records import signal_journal_path
        from .signal_store import pending_signal_targets, SignalStoreError
        try:
            signal_work = pending_signal_targets(signal_journal_path(root))
        except SignalStoreError:
            signal_work = [dict(wake_id='signal-journal', target={},
                                publication_state='unknown')]
        for work in signal_work:
            target = work['target']
            identity = target.get('thread_id') if isinstance(target, dict) else None
            if identity == row['thread_id'] or not identity:
                if not any(item['wake_id'] == work['wake_id'] and item['root'] == str(root)
                           for item in pending):
                    pending.append(dict(wake_id=work['wake_id'], root=str(root),
                                        attribution='exact' if identity else 'unknown',
                                        publication_state=work['publication_state']))
        for state in ('pending', 'firing'):
            for path in (root / state).glob('*.json'):
                try:
                    record = json.loads(path.read_text())
                    known = (classify_record(record) != 'hold'
                             and isinstance(record.get('target'), dict)
                             and bool(record['target'].get('thread_id')))
                except (OSError, UnicodeError, json.JSONDecodeError):
                    known = False
                if not known:
                    pending.append(dict(wake_id=path.stem, root=str(root),
                                        attribution='unknown', path=str(path)))
                elif record['status'] in ('pending', 'firing') and record['target']['thread_id'] == row['thread_id']:
                    if not any(item['wake_id'] == record['id'] and item['root'] == str(root)
                               for item in pending):
                        pending.append(dict(wake_id=record['id'], root=str(root)))
    from .a2a_bus import BusStore, default_bus_root
    from .a2a_identity import BusError
    from .a2a_mailbox import Mailbox
    bus_roots = {path.parent for path in default_bus_root().parent.glob('*/mailbox.sqlite')}
    bus_roots.update(path.parent for path in
                     default_bus_root().parent.glob('*/.recovery-in-progress.json'))
    bus_roots.update(Path(path).absolute() for path in args.bus_root)
    messages = []
    for bus_root in sorted(bus_roots):
        try:
            work = Mailbox(BusStore(bus_root)).pending_thread_work(row['thread_id'])
        except BusError as exc:
            work = [dict(message_id='unknown', kind='inventory_unavailable', reason=exc.code)]
        messages.extend(dict(item, bus_root=str(bus_root)) for item in work)
    if not args.force and (row['runtime_state'] != 'idle' or pending or messages):
        raise WakeError('tab has active/unknown work or pending wakes; explicit --force required')
    if not revalidate_attachment(attachment):
        raise WakeError('attached process identity changed; refusing close')
    # Only a verified single-pane tab is eligible for this operation.
    tmux_command(args, 'kill-pane', '-t', attachment['pane_id'])
    return dict(action='closed', thread_id=row['thread_id'], attachment=attachment,
                forced=bool(args.force), affected_wakes=pending, affected_messages=messages,
                inspected_bus_roots=[str(path) for path in sorted(bus_roots)], conversation='preserved')


def lifecycle_command(args, root):
    if not 0 < args.timeout <= 60:
        raise WakeError('--timeout must be positive and at most 60 seconds')
    from .sessions import SelectionError
    from .sessions_cli import emit
    try:
        result = open_session(args) if args.sessions_command == 'open' else close_session(args, root)
    except SelectionError as exc:
        emit(dict(code=exc.code, message=str(exc), selector=exc.selector,
                  candidates=exc.candidates), args.as_json)
        return exc.code
    print(json.dumps(result, sort_keys=True))
    return 0
