"""Human target orchestration; a descriptor is never durable recipient identity."""
from pathlib import Path

from .sessions import SelectionError, observe, resolve

POLICIES = ('error', 'tab_only', 'fresh', 'resume')
CONDITIONS = {2: 'invalid_descriptor', 3: 'tab_not_found', 4: 'ambiguous_target',
              5: 'inventory_unavailable', 6: 'no_live_codex'}


def canonical(path):
    value = Path(path).expanduser()
    if not value.is_absolute():
        raise ValueError('CWD must be absolute')
    return str(value.resolve())


def inspect_target(snapshot, selector, *, session=None, expected_cwd=None):
    value = dict(schema_version=1, selector=selector, normalized_selector=selector,
                 status='resolved', effects=[], candidates=[], session=None, next_actions=[], sources=snapshot.get('sources', {}))
    try:
        row = resolve(snapshot, selector, session=session, eligible=False)
    except SelectionError as exc:
        value.update(status=getattr(exc, 'condition', CONDITIONS[exc.code]),
                     message=str(exc), candidates=exc.candidates[:10])
        return value
    value.update(row.get('resolution', {}))
    value['session'] = row
    value['thread_id'] = row['thread_id']
    try:
        value['cwd'] = canonical(row['cwd'])
        if expected_cwd and canonical(expected_cwd) != value['cwd']:
            value['status'] = 'cwd_mismatch'
            return value
    except (OSError, ValueError, TypeError):
        value['status'] = 'inventory_unavailable'
        return value
    if not row['thread_id']:
        attachment=row.get('selected_attachment')
        if attachment and attachment.get('pane_current_command') not in (None,'bash','zsh','fish','sh','dash'):
            value['status']='target_busy'
            return value
        value['status'] = ('ambiguous_target' if row['binding_status'] == 'ambiguous'
                           else 'no_live_codex' if row['binding_status'] == 'not_codex'
                           else 'inventory_unavailable')
    elif row['runtime_state'] != 'idle' or row.get('active_flags'):
        value['status'] = 'target_busy'
    return value


def prepare_target(args, root=None):
    if not 0 < args.timeout <= 60:
        return dict(status='invalid_descriptor', effects=[], message='timeout must be positive and <=60')
    if root and args.intent and args.profiles and args.profile:
        from .target_lifecycle import replay
        existing = replay(args, root)
        if existing is not None:
            return existing
    snapshot = observe(endpoint=args.app_server, socket_path=args.tmux_socket, timeout=args.timeout, shell_metadata=True)
    value = inspect_target(snapshot, args.selector, session=args.tmux_session,
                           expected_cwd=args.expected_cwd)
    policy = (args.on_missing if value['status'] == 'tab_not_found' else
              args.on_inactive if value['status'] == 'no_live_codex' else 'error')
    value['requested_policy'] = dict(on_missing=args.on_missing, on_inactive=args.on_inactive)
    value['applied_policy'] = policy
    if value['status'] in ('tab_not_found', 'no_live_codex'):
        value['next_actions'] = list(POLICIES)
    if policy != 'error':
        if not all((args.profiles, args.profile, args.intent, args.expires_at, root)):
            value.update(status='policy_denied', message='host profile, intent, expiry and wake root required')
        else:
            from .target_lifecycle import prepare
            value = prepare(args, root, value)
    return value


def target_command(args, root):
    from .sessions_cli import emit
    value = prepare_target(args, root)
    emit(value, args.as_json)
    return 0 if value['status'] in ('resolved', 'tab_created', 'tab_ready') else 5


def add_target_options(parser):
    for option in ('on-missing', 'on-inactive'):
        parser.add_argument('--' + option, choices=POLICIES, default='error')
    for option in ('expected-cwd', 'cwd', 'resume-thread-id', 'profile', 'profiles', 'intent', 'expires-at', 'caller-thread-id'):
        parser.add_argument('--' + option)


def revalidate_target(report, args):
    from .target_lifecycle import same_attachment
    snapshot = observe(endpoint=args.app_server, socket_path=args.tmux_socket, timeout=args.timeout, shell_metadata=True)
    row = report['session']
    old = row.get('selected_attachment')
    if not snapshot['complete']:
        return dict(report, status='inventory_unavailable')
    if old:
        matches = [(r,p) for r in snapshot['sessions'] for p in r['attachments'] if p['pane_id']==old['pane_id']]
        if len(matches)!=1 or matches[0][0]['thread_id']!=row['thread_id'] or not same_attachment(old,matches[0][1]):
            return dict(report,status='target_changed')
        current=matches[0][0]
    else:
        matches=[r for r in snapshot['sessions'] if r['thread_id']==row['thread_id']]
        if len(matches)!=1:return dict(report,status='target_changed')
        current=matches[0]
    if canonical(current['cwd'])!=report['cwd']:
        return dict(report,status='target_changed')
    if current['runtime_state']!='idle' or current.get('active_flags'):
        return dict(report,status='target_busy')
    return dict(report,status='resolved')
