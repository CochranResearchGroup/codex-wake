"""Public readiness explanations; enrollment and confirmed engagement are separate."""
from datetime import datetime, timezone
import time


def engagement(receipt, controller):
    """Describe current proof without manufacturing a watcher or resource authority."""
    status = 'waiting_for_first_poll'
    action = 'Wait for the independent watcher to poll this enrollment; inspect goal-limits show.'
    accounting = receipt.get('accounting') or {}
    ack = receipt.get('poll_ack') or {}
    if not controller.get('fresh'):
        status = 'watcher_stale' if controller.get('active') and controller.get('process_alive',True) else 'watcher_not_running'
        action = ('Run goal-limits watcher-status for the configured service. An authorized operator '
                  'can use goal-limits start-watcher; masked services require an explicit operator decision.')
    elif receipt.get('reason') == 'permission_revoked':
        status = 'not_permitted'
        action = 'Inspect session permissions for this exact session/task; request the denied action from the operator.'
    elif accounting.get('state') != 'qualified':
        status = 'accounting_unavailable'
        action = 'Inspect the accounting reason in goal-limits show; restore the original history without resetting usage.'
    elif receipt.get('state') not in ('armed', 'checkpoint_requested') or receipt.get('stop_latched'):
        status = 'continuation_held'
        action = 'Keep work stopped. Inspect the retained stop reason; native goal resume does not renew external authority.'
    elif (ack.get('enrollment_revision') == receipt.get('enrollment_revision')
            and ack.get('controller_generation') == controller.get('generation')
            and ack.get('receipt_generation') == receipt.get('generation')
            and 0 <= time.clock_gettime(time.CLOCK_BOOTTIME)-ack.get('observed_boottime',float('-inf')) <= max(3,3*controller.get('interval',1))):
        status = 'engaged'
        action = 'Continue within the displayed remaining allowance; checkpoint reserve is part of that allowance.'
    result = dict(status=status, engaged=status == 'engaged', next_action=action,
                  enrollment='registered', enforcement='verified' if status == 'engaged' else 'unverified',
                  presentation='pending', operator_read='unverified')
    if status == 'engaged':
        used, limit = receipt['used_tokens'], receipt['token_limit']
        elapsed = max(0, time.clock_gettime(time.CLOCK_BOOTTIME)-receipt['started_boottime'])
        upper = receipt['started_upper']+elapsed
        result['card'] = dict(thread_id=receipt['thread_id'], allocation_id=receipt['allocation_id'],
            generation=receipt['generation'], enrollment_revision=receipt['enrollment_revision'],
            token_limit=limit, used_tokens=used, remaining_tokens=max(0, limit-used),
            lifetime_used_tokens=receipt.get('lifetime_tokens_before_window',0)+used,
            token_accounting=receipt.get('token_accounting', 'cache_inclusive'),
            deadline_utc=datetime.fromtimestamp(receipt['deadline'], timezone.utc).isoformat().replace('+00:00', 'Z'),
            timezone='UTC', remaining_seconds=max(0, receipt['deadline']-upper),
            checkpoint_tokens=limit*receipt['checkpoint_token_percent']/100,
            checkpoint_seconds=receipt['checkpoint_seconds'], watcher_health='healthy',
            scope='shared_allocation' if receipt.get('allocation_path') else 'session',
            controller_generation=controller['generation'])
    return result


def explain_error(error):
    """Bounded actionable setup errors shared by CLI and native MCP callers."""
    message = str(error)
    code = getattr(error, 'code', None)
    status = 'setup_unavailable'
    action = 'Run goal-limits watcher-status and inspect goal-limits show for this exact session.'
    if 'accounting' in message or 'qualified original history' in message:
        status = 'accounting_unavailable'
        action = ('Restore readable original session history and inspect the accounting reason. '
                  'Do not replace the caller, erase history or reset counters to bypass this refusal.')
    elif 'maintenance' in message:
        status = 'maintenance'
        action = 'Wait for the authorized controller handover, then verify its first poll with goal-limits show.'
    elif ('permission' in message or 'grant' in message or 'caller' in message
          or type(error).__name__ in ('CallerGrantMissing', 'PermissionDenied')):
        status = 'not_permitted'
        action = 'Inspect the exact session permission decision and configured host scope; do not copy another caller grant.'
    result = dict(state='held', armed=False, reason=status, effect_attempted=False,
                error=dict(code=code or 'goal_limits_unavailable', reason=type(error).__name__, message=message),
                next_action=action, operator_interaction='available', campaign_continuation='held')
    if getattr(error,'accounting_reason',None):result['accounting_reason']=error.accounting_reason
    return result
