"""Cached-inclusive sampled usage from native 0.163 response identities.

No native RPC or display counters. Unsupported/incomplete history is unknown.
"""
from datetime import datetime
from pathlib import Path
import json
import hashlib


def _epoch(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00')).timestamp()


def observe_usage(codex_home, thread_id, goal_created_at, *, reset_anchor=None):
    """Observe original-goal response spending, or an explicitly authorized anchor."""
    try:
        paths = sorted((Path(codex_home) / 'sessions').rglob('*.jsonl'))
        sessions = {}
        for path in paths:
            rows = [json.loads(line) for line in path.read_text().splitlines()]
            if not rows or rows[0].get('type') != 'session_meta':
                raise ValueError('missing_session_metadata')
            meta = rows[0]['payload']
            if meta['id'] in sessions:
                raise ValueError('ambiguous_rollout_identity')
            sessions[meta['id']] = (meta, rows[1:])
        if thread_id not in sessions:
            raise ValueError('root_rollout_missing')
        rows = sessions[thread_id][1]
        boundaries = [i for i, r in enumerate(rows)
            if r.get('type') == 'event_msg'
            and r['payload'].get('type') == 'thread_goal_updated'
            and r['payload'].get('goal', {}).get('createdAt') == goal_created_at]
        if not boundaries:
            raise ValueError('goal_start_missing')
        boundary = boundaries[0]
        creation = rows[boundary]
        if (creation['payload'].get('threadId') != thread_id
                or creation['payload']['goal'].get('threadId') != thread_id):
            raise ValueError('goal_identity_mismatch')
        if int(_epoch(creation['timestamp'])) != goal_created_at:
            raise ValueError('goal_start_not_original')
        active = set()
        for r in rows[:boundary]:
            if r.get('type') != 'event_msg':
                continue
            p = r['payload']
            if p.get('type') == 'task_started':
                active.add(p['turn_id'])
            elif p.get('type') in ('task_complete', 'turn_aborted'):
                active.discard(p['turn_id'])
        if active:
            raise ValueError('goal_start_during_active_turn')
        turns = {r['payload']['turn_id'] for r in rows[boundary+1:]
            if r.get('type') == 'event_msg' and r['payload'].get('type') == 'task_started'}
        owned = {thread_id}
        changed = True
        while changed:
            changed = False
            for identity, (meta, _) in sessions.items():
                parent = meta.get('parent_thread_id')
                source = meta.get('source', {})
                if isinstance(source, dict):
                    subagent = source.get('subagent', {})
                    spawn = subagent.get('thread_spawn', {}) if isinstance(subagent, dict) else {}
                    if not isinstance(spawn, dict):
                        raise ValueError('malformed_parent_identity')
                    source_parent = spawn.get('parent_thread_id')
                    if parent and source_parent and parent != source_parent:
                        raise ValueError('conflicting_parent_identity')
                    parent = parent or source_parent
                if parent in owned and identity not in owned:
                    owned.add(identity); changed = True
        records = {}
        charged = set()
        for identity in owned:
            meta, history = sessions[identity]
            if meta.get('history_base') or (identity == thread_id and meta.get('forked_from_id')):
                raise ValueError('referenced_or_root_fork_history_unqualified')
            if meta.get('session_id') != sessions[thread_id][0].get('session_id'):
                raise ValueError('descendant_session_identity_mismatch')
            for r in history:
                p = r['payload']
                if r.get('type') == 'event_msg' and p.get('type') == 'collab_agent_spawn_end':
                    child = p.get('new_thread_id')
                    if child and child not in owned:
                        raise ValueError('descendant_rollout_missing')
                if r.get('type') != 'token_usage_record':
                    continue
                key = (p['thread_id'], p['response_id'])
                total = p['usage']['total_tokens']
                if type(total) is not int or total < 0:
                    raise ValueError('malformed_usage')
                if p['thread_id'] not in owned:
                    raise ValueError('inherited_record_owner_missing')
                if key in records and records[key] != p:
                    raise ValueError('conflicting_response_identity')
                records[key] = p
                if p['root_turn_id'] in turns:
                    charged.add(key)
        prior_turns = {r['payload']['root_turn_id'] for r in rows[:boundary]
                       if r.get('type') == 'token_usage_record'}
        for identity in owned:
            _, history = sessions[identity]
            pending_spawns = set()
            for r in history:
                p = r['payload']
                if r.get('type') == 'token_usage_record':
                    if p['root_turn_id'] not in turns | prior_turns:
                        raise ValueError('response_goal_attribution_unknown')
                if r.get('type') != 'event_msg':
                    continue
                if p.get('type') == 'collab_agent_spawn_begin':
                    pending_spawns.add(p['call_id'])
                if p.get('type') == 'collab_agent_spawn_end':
                    pending_spawns.discard(p.get('call_id'))
                if p.get('type') == 'raw_response_completed':
                    key = (identity, p['response_id'])
                    if key not in records or p.get('token_usage') is None:
                        raise ValueError('response_usage_missing')
                    if records[key]['usage'] != p['token_usage']:
                        raise ValueError('response_usage_mismatch')
            if pending_spawns:
                raise ValueError('descendant_spawn_incomplete')
        if turns and not charged:
            raise ValueError('first_usage_unavailable')
        anchor = dict(version=1, thread_id=thread_id, goal_created_at=goal_created_at,
            boundary=creation['timestamp'], response_ids=[list(k) for k in sorted(records)],
            response_hashes={json.dumps(k): hashlib.sha256(json.dumps(v, sort_keys=True).encode()).hexdigest()
                             for k, v in records.items()})
        excluded = set()
        if reset_anchor is not None:
            if any(reset_anchor.get(k) != anchor[k] for k in
                   ('version', 'thread_id', 'goal_created_at', 'boundary')):
                raise ValueError('reset_anchor_identity_mismatch')
            excluded = {tuple(k) for k in reset_anchor['response_ids']}
            if not excluded.issubset(records):
                raise ValueError('reset_anchor_history_missing')
            if any(reset_anchor['response_hashes'].get(json.dumps(k)) !=
                   anchor['response_hashes'][json.dumps(k)] for k in excluded):
                raise ValueError('reset_anchor_history_changed')
        return dict(state='qualified', used_tokens=sum(records[k]['usage']['total_tokens']
            for k in charged - excluded), anchor=anchor, reason=None, sampled=True)
    except (ValueError, KeyError, TypeError, OSError, OverflowError) as exc:
        return dict(state='unknown', used_tokens=None, anchor=None,
                    reason=str(exc), sampled=True)
