"""Bind native lifecycle observations to one durable objective allowance."""
import hashlib
import json
from pathlib import Path

from .objective_ledger import ObjectiveLedger


def ledger_for(root, receipt):
    policy = receipt['intent']['continuation']
    return ObjectiveLedger(root, objective_identity(policy))


def objective_identity(policy):
    return policy.get('objective_id') or hashlib.sha256(json.dumps(
        [policy['objective'], policy['started_at']], sort_keys=True).encode()).hexdigest()


def trusted_upper():
    from .native_clock import snapshot
    bounds = snapshot().get('utc')
    if not bounds:
        raise ValueError('admissible time unavailable')
    return bounds['upper']


def admit_handoff(root, receipt):
    now = trusted_upper()
    config = {key: value for key, value in receipt['configuration'].items()
              if key not in ('source_thread_id', 'profile')}
    policy = receipt['intent']['continuation']
    ledger = ledger_for(root, receipt)
    ledger.configure(config, policy['approval'], policy['tokens_before_source'], now=now)
    source = receipt['source_goal']
    actor = 'goal:' + source['threadId'] + ':' + str(source['createdAt'])
    view = ledger.record_goal(actor, source['tokensUsed'], settled=True, now=now)
    successor = 'handoff:' + receipt['fingerprint']
    existing = view['actors'].get(successor)
    if existing and existing.get('terms'):
        tokens, seconds = existing['terms']
    else:
        tokens = min(config['session_token_limit'], view['remaining_tokens'], receipt['source_remaining_tokens'])
        seconds = int(min(config['session_time_limit_seconds'], view['remaining_seconds'],
                          receipt['continuation_deadline'] - now))
    if tokens <= 0 or seconds <= 0:
        receipt.update(state='blocked', reason='objective_allowance_exhausted', objective_budget=view)
        return False
    view = ledger.reserve(successor, tokens, seconds, now=now)
    receipt['objective_budget'] = view
    receipt['budget_actor'] = successor
    if not view['admitted']:
        receipt.update(state='blocked', reason='objective_admission_denied')
        return False
    owned = view['actors'][successor]
    receipt['continuation_deadline'] = min(receipt['continuation_deadline'], owned['session_deadline'])
    receipt['remaining_tokens'] = owned['tokens_remaining']
    return True


def record_successor(root, receipt, cumulative_tokens, *, settled=False):
    view = ledger_for(root, receipt).record(receipt['budget_actor'], cumulative_tokens,
                                          settled=settled, now=trusted_upper())
    receipt['objective_budget'] = view
    receipt['remaining_tokens'] = view['actors'][receipt['budget_actor']]['tokens_remaining']
    return view


def native_usage(native, profile):
    if native.get('turns') == []:
        return 0
    if not native.get('path'):
        return None
    rollout = Path(native['path']).resolve()
    rollout.relative_to(Path(profile.get('codex_home', Path.home() / '.codex')) / 'sessions')
    if not rollout.is_file():
        return None
    usage = None
    for line in rollout.read_text().splitlines():
        event = json.loads(line)
        payload = event.get('payload', {})
        info = payload.get('info') or {}
        if event.get('type') == 'event_msg' and payload.get('type') == 'token_count' and info.get('total_token_usage'):
            value = info['total_token_usage'].get('total_tokens')
            usage = value if type(value) is int and value >= 0 else None
    return usage
