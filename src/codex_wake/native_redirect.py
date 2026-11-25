"""Redirect a proven timed native bounce through normal wake admission."""
from datetime import UTC, datetime, timedelta
import math
from uuid import UUID

from .records import WakeError, find_record


def redirect(args, root):
    from .message_delivery import configured_store, scope_for_wake
    from .native_clock import snapshot
    from .native_intents import existing_receipt, retain, schedule_projection, valid_utc
    from .network_wakes import precise_deadline
    from .runtime_delivery import original_submission_expiry
    from .session_permissions import PermissionStore
    from .wake_policy import registration_guard

    if PermissionStore(root).active():
        from .permission_commands import verified_cli_principal
        principal = getattr(args, '_permission_principal', None) or verified_cli_principal(args)
        if principal.role != 'operator':
            raise WakeError('native_redirect_operator_required')
        args._permission_principal = principal

    original = find_record(root, args.wake_id).record
    target = original.get('target', {})
    intent = original.get('scheduling_intent', {})
    outcome = original.get('policy_outcome', {})
    reason = outcome.get('reason')
    if (target.get('transport') != 'native' or intent.get('schedule', {}).get('kind') not in ('at', 'after')
            or original.get('status') != 'cancelled' or original.get('native_delivery')
            or outcome.get('state') != 'bounced' or reason not in ('recipient_busy', 'recipient_dnd')
            or not any(event.get('type') == 'message_bounced' and event.get('message') == reason
                       for event in original.get('events', []))):
        raise WakeError('native_redirect_requires_confirmed_timed_bounce')
    if str(UUID(args.to)) != args.to or args.to == target['thread_id']:
        raise WakeError('native_redirect_requires_distinct_exact_recipient')
    if not args.endpoint.startswith('unix://'):
        raise WakeError('native redirect requires a local unix:// endpoint')
    store = configured_store(root)
    if store is not None:
        from psycopg import Error
        try:
            shared = store.policy_status(scope_for_wake(root), original['id'])
        except (Error, OSError, ValueError):
            raise WakeError('native_redirect_shared_bounce_unavailable') from None
        if not shared or shared['bounce_reason'] != reason:
            raise WakeError('native_redirect_shared_bounce_unavailable')

    due = precise_deadline(schedule_projection(original)['due_at'])
    expiry_micros = original_submission_expiry(original)
    expiry = datetime(1970, 1, 1, tzinfo=UTC) + timedelta(microseconds=expiry_micros)
    if expiry <= due:
        raise WakeError('native_redirect_original_window_unavailable')
    args.native_command = 'at'
    args.thread_id = args.to
    args.trigger = due.isoformat()
    args.stop_at = expiry.isoformat()
    args.ttl = f'{math.ceil((expiry - due).total_seconds())}s'
    args.prompt = ['--', original['prompt']]
    args.busy_policy = target.get('busy_policy', 'wait')
    args._redirected_from = original['id']
    with registration_guard(root, args):
        existing = existing_receipt(args, root)
        if existing is not None:
            return existing
        observed = snapshot().get('utc')
        if not valid_utc(observed):
            raise WakeError('native_redirect_time_unavailable')
        if math.ceil(observed['upper'] * 1_000_000) >= expiry_micros:
            raise WakeError('native_redirect_original_window_closed')
        return retain(args, root)
