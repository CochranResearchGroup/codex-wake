"""Explicit operational goal pause; resource-stop decisions are never cleared."""
from .agent_lifecycle import save


def settle_ui(path, receipt, profile, pane, request):
    """Dismiss only the exact paused-goal prompt, never a draft or unknown dialog."""
    from types import SimpleNamespace
    from .session_lifecycle import tmux_command
    from .sessions import revalidate_attachment
    runtime = SimpleNamespace(tmux_socket=profile.get('tmux_socket'), timeout=profile['timeout'])
    frame = tmux_command(runtime, 'capture-pane', '-e', '-p', '-t', pane['pane_id'], preserve_output=True)
    cursor = tmux_command(runtime, 'display-message', '-p', '-t', pane['pane_id'], '#{cursor_x},#{cursor_y}')
    x, y = map(int, cursor.split(','))
    lines = frame.splitlines()
    if x == 2 and 0 <= y < len(lines) and lines[y] == '\x1b[1m›\x1b[0m \x1b[2mAsk Codex to do anything\x1b[0m':
        return True
    markers = ('\x1b[1mResume paused goal?\x1b[0m', '\x1b[1;7m› 1. Resume goal',
               'Mark it active and continue when idle', '2. Leave paused',
               'Keep it paused; use /goal resume later')
    goal = request('thread/goal/get', dict(threadId=receipt['thread_id']))['goal']
    if (receipt.get('paused_goal_prompt_dismissal') or not goal or goal.get('status') != 'paused'
            or not continuous(receipt['goal_before'], goal, 'paused')
            or any(frame.count(marker) != 1 for marker in markers)
            or not revalidate_attachment(pane)):
        receipt.update(state='blocked', reason='refresh_composer_or_dialog_unverified')
        save(path, receipt)
        return False
    receipt.update(paused_goal_prompt_dismissal=dict(attachment=pane, key='Escape', goal_before=goal),
                   reason='awaiting_composer_after_goal_dialog')
    save(path, receipt)
    tmux_command(runtime, 'send-keys', '-t', pane['pane_id'], 'Escape')
    if not continuous(goal, request('thread/goal/get', dict(threadId=receipt['thread_id']))['goal'], 'paused'):
        raise ValueError('goal changed while leaving modal paused')
    return False


def continuous(before, after, status):
    if not isinstance(before, dict) or not isinstance(after, dict):
        return before == after
    counters = {'tokensUsed', 'timeUsedSeconds', 'updatedAt'}
    expected = dict(before, status=status)
    return (all(after.get(k) == v for k, v in expected.items() if k not in counters)
            and all(type(before.get(k)) in (int, float)
                    and type(after.get(k)) in (int, float)
                    and after[k] >= before[k] for k in counters))


def resource_ready(root, receipt, profile, goal):
    from .lifecycle_budget import track_refresh_budget, trusted_upper
    configured = bool(receipt['intent'].get('configuration'))
    if configured and not track_refresh_budget(root, receipt, goal):
        return False
    binding = profile.get('goal_supervision')
    if binding is None:
        return configured
    if not isinstance(binding, dict) or set(binding) != {'root', 'policy', 'allocation_id'}:
        return False
    from .goal_supervision import show
    proof = show(binding['root'], binding['policy'], receipt['thread_id'], binding['allocation_id'])
    receipt['refresh_resource_proof'] = proof
    return (proof.get('state') == 'armed' and not proof.get('stop_latched')
            and proof.get('controller', {}).get('fresh') is True
            and proof.get('accounting', {}).get('state') == 'qualified'
            and type(proof.get('used_tokens')) is int
            and proof['used_tokens'] < proof.get('token_limit', 0)
            and trusted_upper() < proof.get('deadline', 0))


def pause(path, receipt, profile, goal, request):
    if not goal or goal.get('status') != 'active':
        return True
    if not resource_ready(path.parent.parent, receipt, profile, goal):
        receipt.update(state='blocked', reason='refresh_resume_resources_unqualified')
        save(path, receipt)
        return False
    receipt.update(state='pausing_goal', operational_goal_pause=dict(original=goal, state='requested'))
    save(path, receipt)
    try:
        request('thread/goal/set', dict(threadId=receipt['thread_id'], status='paused', origin='automatic'))
        observed = request('thread/goal/get', dict(threadId=receipt['thread_id']))['goal']
        if not continuous(goal, observed, 'paused'):
            raise ValueError('goal pause continuity unavailable')
    except Exception:
        receipt.update(state='blocked', reason='refresh_goal_pause_unverified')
        save(path, receipt)
        return False
    receipt['operational_goal_pause'].update(state='acknowledged', paused=observed)
    receipt['goal_before'] = observed
    receipt['state'] = 'prepared'
    save(path, receipt)
    return True


def restore(path, receipt, profile, request):
    transition = receipt.get('operational_goal_pause')
    if not transition:
        return True
    before = transition['original']
    observed = request('thread/goal/get', dict(threadId=receipt['thread_id']))['goal']
    if transition.get('state') in ('restore_requested', 'restored'):
        if (continuous(transition['paused'], observed, 'active')
                and resource_ready(path.parent.parent, receipt, profile, observed)):
            transition.update(state='restored', after=observed)
            receipt['goal_after'] = observed
            receipt.pop('uncertain_effect', None)
            return True
        receipt.update(state='blocked', reason='refresh_goal_restore_outcome_unverified')
        save(path, receipt)
        return False
    if (before.get('status') != 'active' or transition.get('state') != 'acknowledged'
            or not continuous(transition['paused'], observed, 'paused')
            or not resource_ready(path.parent.parent, receipt, profile, observed)):
        receipt.update(state='blocked', reason='refresh_goal_restore_held')
        save(path, receipt)
        return False
    # Persist before activation. An ambiguous effect is never replayed.
    transition['state'] = 'restore_requested'
    receipt['uncertain_effect'] = 'native/goal_resume'
    save(path, receipt)
    request('thread/goal/set', dict(threadId=receipt['thread_id'], status='active', origin='automatic'))
    after = request('thread/goal/get', dict(threadId=receipt['thread_id']))['goal']
    if not continuous(observed, after, 'active'):
        raise ValueError('goal restore continuity unavailable')
    transition.update(state='restored', after=after)
    receipt.pop('uncertain_effect', None)
    receipt['goal_after'] = after
    save(path, receipt)
    return True
