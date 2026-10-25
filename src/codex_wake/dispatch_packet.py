"""Compact spawn inputs reference existing authority; they never grant resources."""
from __future__ import annotations

import hashlib
import json

from .records import WakeError


MAX_PACKET_BYTES = 65536


def render_assignment(intent, *, root, brief=None, pin=None, admission=None, receipt_path=None):
    """Render a fresh worker's bounded assignment without inheriting history."""
    brief = brief or {}
    options = brief.get('dispatch', {})
    configuration = intent.get('configuration', {})
    policy = intent.get('continuation', {})
    configured = bool(configuration)
    mode = 'configured_objective' if configured else 'explicit_expiry_only_legacy_profile'
    allocation_ref = brief.get('allocation_ref')
    if configured and allocation_ref is None:
        from .lifecycle_budget import objective_identity
        allocation_ref = objective_identity(policy)
    authority = dict(permission_ref=brief.get('permission_ref', intent['profile']),
                     source_thread_id=intent.get('source_thread_id'),
                     approval=policy.get('approval'), task_brief=pin)
    allowance = dict(allocation_ref=allocation_ref,
                     expires_at=intent['expires_at'],
                     objective_ref=intent.get('objective_ref'),
                     parent_objective=policy.get('objective'),
                     inherited_actor=intent.get('budget_inherited'),
                     limits={key: configuration[key] for key in (
                         'session_token_limit', 'session_time_limit_seconds',
                         'objective_token_limit', 'objective_time_limit_seconds',
                         'objective_deadline') if key in configuration})
    if configured:
        allowance['limits']['session_token_limit'] = policy.get(
            'spawn_token_limit', configuration['session_token_limit'])
    control = intent.get('governance_snapshot') or {}
    packet = dict(version=1, context_mode='compact',
        objective=brief.get('objective', intent['task']),
        instructions=intent['task'], authority=authority,
        scope=dict(workspace=intent['launch']['cwd'], phase=brief.get('phase'),
                   non_goals=brief.get('non_goals', ['Do not expand the assignment or its authority.'])),
        acceptance=brief.get('acceptance', ['Report the requested result with evidence, or a partial/blocked outcome.']),
        evidence=brief.get('context', []), evidence_summaries=options.get('evidence_summaries', []),
        evidence_admission=(dict(observed_at=admission['admitted_at'],
            sources=admission['context_evidence'], freshness='Admission snapshot; recheck source digests before relying on them.')
            if admission else None),
        allowance=allowance,
        stop_conditions=options.get('stop_conditions', []) + [
            'Stop at the original expiry or earlier authorized resource limit.',
            'Return partial evidence when blocked; do not renew allowance or expand scope.',
            'Honor the existing authorized allowance and operator choices; unknown governor availability alone does not revoke work authority.'],
        governance=dict(budget_mode=mode, configuration_revision=configuration.get('revision'),
                        state=control.get('mode', 'unknown'), snapshot=control,
                        enabled=control.get('enabled'),
                        required_action='Use available public governance status; do not insert a governor or block already-authorized repair merely because its status is unavailable.',
                        lifecycle_root=str(root), receipt_path=str(receipt_path),
                        source='Host launch configuration and durable lifecycle/objective receipts; packet is a snapshot.',
                        controls='Existing controls and operator choices remain authoritative; this packet changes none.'),
        return_contract='Return compact status, result, evidence locators, freshness, coverage, ambiguity and remaining obligations. Keep raw evidence available at its source.')
    if 'history' in options:
        packet['context_mode'] = 'full_history'
        packet['history'] = options['history']
    text = 'BOUNDED_ASSIGNMENT=' + json.dumps(packet, sort_keys=True, separators=(',', ':'), allow_nan=False)
    size = len(text.encode())
    if size > MAX_PACKET_BYTES:
        raise WakeError('rendered dispatch exceeds the bounded assignment input')
    return text, dict(version=1, context_mode=packet['context_mode'], input_bytes=size,
                      input_sha256=hashlib.sha256(text.encode()).hexdigest(),
                      history_reason=options.get('history', {}).get('reason'))
