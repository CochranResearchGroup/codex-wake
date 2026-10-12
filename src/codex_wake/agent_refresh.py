"""Same-thread refresh with owned checkpoints and explicit resource proof."""
from __future__ import annotations

import hashlib
import json
import fcntl
import shlex
from pathlib import Path
from types import SimpleNamespace

from .records import WakeError, parse_timestamp
from .agent_lifecycle import save, before_effect


def refresh_command(args, root):
    try:
        config = json.loads(Path(args.profiles).read_text())
        profile = config['profiles'][args.profile]
        workspace = Path(profile['cwd']).resolve(strict=True)
        checkpoint = (workspace / args.checkpoint).resolve(strict=True)
        checkpoint.relative_to(workspace)
        content = checkpoint.read_bytes()
    except (OSError, ValueError, KeyError, TypeError):
        raise WakeError('approved profile and workspace checkpoint are required') from None
    if hashlib.sha256(content).hexdigest() != args.checkpoint_sha256:
        raise WakeError('checkpoint hash changed; original checkpoint must be preserved')
    resources = profile.get('resources', {})
    if not resources or any(name not in resources for name in args.resource):
        raise WakeError('requested resources require host-approved proof checks')
    if config.get('version') != 1:
        raise WakeError('approved profile registry version is required')
    if args.caller_thread_id:
        if (args.caller_thread_id != args.thread_id or args.profile not in
                config.get('callers', {}).get(args.caller_thread_id, [])):
            raise WakeError('refresh requires the host-granted source caller')
    try:
        body = json.loads(content)
        if body['source_thread_id'] != args.thread_id:
            raise ValueError
        if any(not body.get(k) for k in ('objective', 'authority', 'next_packet')):
            raise ValueError
        if body.get('pending_obligations') != []:
            raise ValueError
    except (ValueError, KeyError, TypeError):
        raise WakeError('source checkpoint must preserve work and account for obligations') from None
    parse_timestamp(args.expires_at)
    intent = dict(operation='refresh', source_thread_id=args.thread_id, launch=profile,
                  checkpoint=str(checkpoint), checkpoint_sha256=args.checkpoint_sha256,
                  resources=args.resource, expires_at=args.expires_at)
    fingerprint = hashlib.sha256(json.dumps(intent, sort_keys=True).encode()).hexdigest()
    journal = Path(root) / 'lifecycle'
    journal.mkdir(mode=0o700, parents=True, exist_ok=True)
    key = hashlib.sha256(args.intent.encode()).hexdigest()
    path = journal / (key + '.json')
    with (journal / (key + '.lock')).open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if path.exists():
            receipt = json.loads(path.read_text())
            if receipt['fingerprint'] != fingerprint:
                raise WakeError('intent key already binds a different lifecycle assignment')
        else:
            receipt = dict(version=1, intent_key=args.intent, fingerprint=fingerprint,
                           intent=intent, thread_id=args.thread_id, state='prepared')
            save(path, receipt)
        if receipt['state'] == 'prepared' and before_effect(path, receipt):
            preflight(path, receipt, profile)
        if receipt['state'] in ('stopping', 'starting', 'awaiting_preflight'):
            advance_refresh(path, receipt, profile)
        from .sessions_cli import emit
        emit(receipt, args.as_json)
        return 0 if receipt['state'] == 'completed' else 5


def preflight(path, receipt, profile):
    from .sessions import observe, revalidate_attachment
    from .session_lifecycle import tmux_command
    runtime = SimpleNamespace(**(dict(tmux_socket=None) | profile))
    snapshot = observe(endpoint=runtime.app_server, socket_path=runtime.tmux_socket,
                       timeout=runtime.timeout)
    rows = [r for r in snapshot['sessions'] if r['thread_id'] == receipt['thread_id']]
    attachments = [p for r in rows for p in r['attachments']]
    if (not snapshot['complete'] or len(rows) != 1 or len(attachments) != 1
            or rows[0]['runtime_state'] != 'idle' or rows[0]['active_flags']
            or rows[0]['can_accept_direct_input'] is not True
            or rows[0]['cwd'] != str(Path(runtime.cwd).resolve())
            or attachments[0]['session_name'] != runtime.tmux_session
            or not revalidate_attachment(attachments[0])):
        receipt.update(state='blocked', reason='exact_idle_owned_client_not_ready')
        save(path, receipt)
        return
    pane = attachments[0]
    frame = tmux_command(runtime, 'capture-pane', '-e', '-p', '-t', pane['pane_id'],
                         preserve_output=True)
    cursor = tmux_command(runtime, 'display-message', '-p', '-t', pane['pane_id'],
                          '#{cursor_x},#{cursor_y}')
    try:
        x, y = map(int, cursor.split(','))
        lines = frame.splitlines()
        empty = (x == 2 and 0 <= y < len(lines) and lines[y] ==
                 '\x1b[1m›\x1b[0m \x1b[2mAsk Codex to do anything\x1b[0m')
    except ValueError:
        empty = False
    if not empty:
        receipt.update(state='blocked', reason='local_composer_not_proven_empty')
        save(path, receipt)
        return
    from .native_protocol import native_request
    from .app_server import resolve_codex_cmd
    from .session_lifecycle import close_session
    runtime.codex = resolve_codex_cmd(runtime.codex_path, required=True)
    goal = native_request(runtime.app_server, runtime.codex, 'thread/goal/get',
                          {'threadId': receipt['thread_id']}, runtime.timeout)['goal']
    if not before_effect(path, receipt):
        return
    receipt.update(state='stopping', uncertain_effect='tmux/kill-pane',
                   old_attachment=pane, goal_before=goal, thread_name=rows[0]['name'])
    save(path, receipt)
    runtime.selector = 'thread:' + receipt['thread_id']
    runtime.force = False
    runtime.bus_root = []
    try:
        close_session(runtime, path.parent.parent)
    except WakeError as exc:
        receipt.update(state='blocked', reason=str(exc))
        # Close refuses its safety checks before the pane effect. A failed tmux
        # command remains uncertain because its external outcome is unknown.
        if 'tmux lifecycle command failed' in str(exc):
            receipt['state'] = 'uncertain'
        else:
            receipt.pop('uncertain_effect', None)
        save(path, receipt)


def advance_refresh(path, receipt, profile):
    from .app_server import resolve_codex_cmd
    from .native_protocol import native_request
    from .sessions import observe, revalidate_attachment
    from .session_lifecycle import tmux_command
    runtime = SimpleNamespace(**(dict(tmux_socket=None) | profile),
                              codex=resolve_codex_cmd(profile['codex_path'], required=True))
    def request(method, params):
        return native_request(runtime.app_server, runtime.codex, method, params, runtime.timeout)
    try:
        if receipt['state'] == 'stopping':
            old = receipt['old_attachment']
            try:
                fields = Path('/proc', str(old['client_pid']), 'stat').read_text().rsplit(')', 1)[1].split()
                gone = fields[0] == 'Z' or int(fields[19]) != old['client_start_time_ticks']
            except FileNotFoundError:
                gone = True
            except (PermissionError, ValueError, IndexError):
                gone = False
            if not gone:
                receipt['reason'] = 'old_generation_exit_not_observed'
                save(path, receipt)
                return
            receipt.pop('uncertain_effect', None)
            receipt['old_generation_exit_observed'] = True
            if not before_effect(path, receipt):
                return
            removed = ['CODEX_THREAD_ID', 'TMUX_PANE', 'CODEX_WAKE_A2A_CAPABILITY',
                       'CODEX_WAKE_A2A_BUS_ROOT', 'CODEX_WAKE_SENDER_RECEIPT_AUTHORITY']
            home = ['CODEX_HOME=' + profile['codex_home']] if 'codex_home' in profile else []
            command = shlex.join(['env', *[v for k in removed for v in ('-u', k)], *home,
                                  runtime.codex, 'resume', '--no-alt-screen', '-C', runtime.cwd,
                                  receipt['thread_id'], '--remote', runtime.app_server])
            receipt.update(state='starting', uncertain_effect='tmux/new-window')
            save(path, receipt)
            created = tmux_command(runtime, 'new-window', '-d', '-P', '-F',
                                   '#{window_id}\t#{pane_id}', '-t', runtime.tmux_session + ':',
                                   '-n', old['window_name'], '-c', runtime.cwd, command)
            window, pane = created.split('\t')
            receipt.update(state='awaiting_preflight', window_id=window, pane_id=pane)
            receipt.pop('uncertain_effect', None)
            save(path, receipt)
        if receipt['state'] == 'awaiting_preflight':
            snapshot = observe(endpoint=runtime.app_server, socket_path=runtime.tmux_socket,
                               timeout=runtime.timeout)
            rows = [r for r in snapshot['sessions'] if r['thread_id'] == receipt['thread_id']]
            panes = [p for r in rows for p in r['attachments']]
            if (not snapshot['complete'] or len(rows) != 1 or len(panes) != 1
                    or panes[0]['pane_id'] != receipt['pane_id']
                    or panes[0]['client_pid'] == receipt['old_attachment']['client_pid']
                    or not revalidate_attachment(panes[0])):
                receipt['reason'] = 'exact_replacement_client_not_ready'
                save(path, receipt)
                return
            receipt['attachment'] = panes[0]
            receipt['goal_after'] = request('thread/goal/get', {'threadId': receipt['thread_id']})['goal']
            if receipt['goal_before'] != receipt['goal_after']:
                receipt.update(state='blocked', reason='goal_changed_during_refresh')
                save(path, receipt)
                return
            checks = {}
            catalog = request('skills/list', {'cwds': [runtime.cwd], 'forceReload': True})['data']
            for name in receipt['intent']['resources']:
                check = profile['resources'][name]
                ready = False
                if check['kind'] == 'skill':
                    skills = [s for row in catalog if row['cwd'] == runtime.cwd and not row['errors']
                              for s in row['skills'] if s['path'] == check['path'] and s['enabled']]
                    digest = hashlib.sha256(Path(check['path']).read_bytes()).hexdigest()
                    ready = (len(skills) == 1 and skills[0]['description'] == check['description']
                             and digest == check['sha256'])
                    checks[name] = dict(state='ready' if ready else 'blocked',
                                        catalog=skills, observed_sha256=digest)
                elif check['kind'] == 'mcp' and check.get('read_only') is True:
                    result = request('mcpServer/tool/call', dict(threadId=receipt['thread_id'],
                        server=check['server'], tool=check['tool'], arguments=check['arguments']))
                    ready = (result.get('isError') is not True
                             and result['content'] == check['expected_content'])
                    checks[name] = dict(state='ready' if ready else 'blocked',
                                        server=check['server'], tool=check['tool'],
                                        observed_content=result['content'], is_error=result.get('isError'))
                else:
                    checks[name] = dict(state='blocked', reason='resource_proof_unavailable')
            receipt.update(resources=checks, state='completed' if all(
                c['state'] == 'ready' for c in checks.values()) else 'blocked')
            if receipt['state'] == 'completed':
                receipt.pop('reason', None)
            else:
                receipt['reason'] = 'requested_resources_not_ready'
            save(path, receipt)
    except Exception as exc:
        receipt.update(state='uncertain' if receipt.get('uncertain_effect') else 'blocked',
                       reason=type(exc).__name__)
        save(path, receipt)
