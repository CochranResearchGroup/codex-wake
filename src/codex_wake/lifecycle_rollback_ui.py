"""Dismiss only the native restored-source paused-goal dialog."""
from types import SimpleNamespace


def leave_restored_goal_paused(path, receipt, profile, saved_goal, request):
    from .agent_lifecycle import save
    from .sessions import observe, revalidate_attachment
    from .session_lifecycle import tmux_command
    result=receipt['rollback']
    expected=result.get('restoration')
    if not expected or result.get('paused_goal_prompt_dismissal'):
        return False
    source=receipt['thread_id']
    snapshot=observe(endpoint=profile['app_server'],socket_path=profile.get('tmux_socket'),timeout=profile['timeout'])
    rows=[r for r in snapshot['sessions'] if r['thread_id']==source]
    if (not snapshot['complete'] or len(rows)!=1 or rows[0]['runtime_state']!='idle'
            or rows[0]['cwd']!=profile['cwd'] or rows[0]['can_accept_direct_input'] is not True
            or rows[0]['active_flags'] or len(rows[0]['attachments'])!=1):
        return False
    pane=rows[0]['attachments'][0]
    if (pane['pane_id']!=expected['pane_id'] or pane['window_id']!=expected['window_id']
            or pane['session_name']!=profile['tmux_session']
            or pane['client_pid']==expected['previous_client_pid'] or not revalidate_attachment(pane)):
        return False
    goal=request('thread/goal/get',dict(threadId=source))['goal']
    if (not goal or goal['status']!='paused'
            or any(goal.get(k)!=saved_goal.get(k) for k in
                ('threadId','objective','tokenBudget','createdAt','tokensUsed','timeUsedSeconds'))):
        return False
    runtime=SimpleNamespace(tmux_socket=profile.get('tmux_socket'),timeout=profile['timeout'])
    frame=tmux_command(runtime,'capture-pane','-e','-p','-t',pane['pane_id'],preserve_output=True)
    markers=('\x1b[1mResume paused goal?\x1b[0m','\x1b[1;7m› 1. Resume goal',
        'Mark it active and continue when idle','2. Leave paused',
        'Keep it paused; use /goal resume later')
    if any(frame.count(marker)!=1 for marker in markers) or not revalidate_attachment(pane):
        return False
    # Journal the exact one-shot UI effect before sending. Reconciliation must
    # observe the composer; an ambiguous response never authorizes another key.
    result.update(state='leaving_source_paused',uncertain_effect='tmux/rollback_leave_paused',
        paused_goal_prompt_dismissal=dict(attachment=pane,key='Escape',goal_before=goal))
    save(path,receipt)
    tmux_command(runtime,'send-keys','-t',pane['pane_id'],'Escape')
    if request('thread/goal/get',dict(threadId=source))['goal']!=goal:
        raise ValueError('restored paused goal changed during dialog dismissal')
    return True
