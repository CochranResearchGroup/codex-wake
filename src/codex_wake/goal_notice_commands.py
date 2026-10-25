"""Inspect retained supervision notices while campaign work is held."""
from .goal_notices import list_notices, read_notice


def execute(root, policy_path, caller_thread_id, *, event_id=None, allocation_id=None,
            permission_principal=None, native_context=None):
    # Existing public inspection owns grant/caller verification. It remains usable
    # when resources are exhausted; this adapter never renews or starts a turn.
    from .goal_supervision import show
    current = show(root, policy_path, caller_thread_id, allocation_id,
        permission_principal=permission_principal, native_context=native_context)
    if event_id is None:
        notices = list_notices(root, caller_thread_id)
    else:
        event = read_notice(root, event_id)
        if event['identity']['thread_id'] != caller_thread_id:
            raise ValueError('supervision notice belongs to another session')
        notices = [event]
    return dict(state='available', campaign_state=current['state'], notices=notices,
        renders_operator_ui=False, resumes_goal=False, renews_resources=False)
