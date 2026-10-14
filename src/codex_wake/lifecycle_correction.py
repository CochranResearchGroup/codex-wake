"""Frozen, owned correction assignments under an existing objective reservation."""
import hashlib
import json
from pathlib import Path

from .agent_lifecycle import advance_spawn, save
from .lifecycle_budget import ledger_for, trusted_upper


def prepare_correction(path, receipt, policy, profile, review):
    packet = review.get('correction_packet', {})
    workspace = Path(profile['cwd']).resolve()
    scope = policy.get('correction_scope', [])
    try:
        if (not scope or packet['criterion'] not in policy['acceptance_criteria']
                or not isinstance(packet['instructions'], str) or not packet['instructions'].strip()
                or len(packet['instructions']) > 8192
                or not isinstance(review.get('selected_review'), str) or not review['selected_review'].strip()
                or not isinstance(packet['paths'], list) or not 0 < len(packet['paths']) <= 16
                or not isinstance(packet.get('evidence'), list) or not packet['evidence']
                or any(item not in scope for item in packet['paths'])):
            return False
        for item in packet['paths']:
            relative = Path(item)
            if relative.is_absolute() or '..' in relative.parts:
                return False
            target = workspace / relative
            if target.resolve() != target or target.resolve() == Path(receipt['intent']['checkpoint']):
                return False
            target.resolve().relative_to(workspace)
        for evidence in packet['evidence']:
            target = (workspace / evidence['path']).resolve(strict=True)
            target.relative_to(workspace)
            if hashlib.sha256(target.read_bytes()).hexdigest() != evidence['sha256']:
                return False
        worker = receipt['successor']
        cycle_key = receipt['fingerprint'] + ':' + worker['submission_id']
        view = ledger_for(path.parent.parent, receipt).correction(now=trusted_upper(),
            key=cycle_key, actor_id=receipt['budget_actor'])
        receipt['objective_budget'] = view
        if not view['admitted']:
            receipt.update(state='blocked', reason='correction_cycles_exhausted' if
                view['correction_cycles'] >= receipt['configuration']['max_correction_cycles'] else
                'correction_budget_unavailable')
            return True
        identity = hashlib.sha256(cycle_key.encode()).hexdigest()
        correction_path = path.parent / ('correction-' + identity + '.json')
        task = ('Bounded correction only. The outgoing work is not accepted. Repair only the '
            'frozen packet paths within the approved objective. Preserve the original checkpoint, '
            'scope, resource ceilings and deadline. Then apply the selected review again and '
            'produce fresh criterion evidence; no continuation or goal activation.\n' +
            receipt['preflight_task'] + '\nCORRECTION_PACKET=' + json.dumps(packet, sort_keys=True) +
            '\nCORRECTION_ID=' + identity)
        if not correction_path.exists():
            assignment = dict(version=1, fingerprint=identity, state='awaiting_preflight',
                thread_id=worker['thread_id'], pane_id=worker['pane_id'], window_id=worker['window_id'],
                intent=dict(operation='correction', task=task,
                    expires_at=receipt['intent']['expires_at']))
            # The session deadline remains narrower than the original intent expiry.
            from datetime import UTC, datetime
            assignment['intent']['expires_at'] = datetime.fromtimestamp(receipt['continuation_deadline'], UTC).isoformat()
            save(correction_path, assignment)
        receipt.setdefault('review_history', []).append(receipt['preflight'])
        receipt['correction_assignment'] = str(correction_path)
        receipt.update(state='correcting', reason='bounded_correction_admitted')
        return True
    except (KeyError, TypeError, ValueError, OSError):
        return False


def advance_correction(path, receipt, profile, request):
    correction_path = Path(receipt['correction_assignment'])
    correction_path.relative_to(path.parent)
    assignment = json.loads(correction_path.read_text())
    worker = receipt['successor']
    target = assignment['thread_id']
    if target != worker['thread_id'] or request('thread/goal/get', {'threadId': target})['goal'] is not None:
        raise ValueError('correction successor authority changed')
    from .agent_handoff import source_guard
    guard = dict(thread_id=target, reason='successor_preflight_not_verified')
    # Re-check attachment when admitting the new correction, not while observing its turn.
    if not assignment.get('submission_id'):
        source_guard(guard, profile, path.parent.parent)
        expected = worker['attachment']
        if guard.get('source_attachment') != expected:
            raise ValueError('correction attachment generation changed')
    advance_spawn(correction_path, assignment, profile)
    return assignment
