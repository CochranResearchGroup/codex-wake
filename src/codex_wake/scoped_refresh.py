"""Exact native thread MCP refresh; no client replacement or global fallback."""
from .records import WakeError

METHOD='thread/mcpServer/reload'


def inspect_capability(profile,thread):
    from .native_protocol import native_request
    from .shared_refresh import _source_workspace
    def request(method,params):
        return native_request(profile['app_server'],profile['codex_path'],method,params,profile['timeout'])
    try:
        source=request('thread/read',dict(threadId=thread,includeTurns=False))['thread']
        if not _source_workspace(dict(thread_id=thread,profile=profile),source):
            raise WakeError('source_workspace_mismatch')
        result=request(METHOD,dict(threadId=thread,dryRun=True))
        if result!=dict(threadId=thread,queued=False):raise WakeError('native_scope_unverified')
        return dict(capability='supported',native_dependency=METHOD,readiness='observed')
    except (OSError,ValueError,KeyError,TypeError,WakeError):
        return dict(capability='unsupported',native_dependency=METHOD,readiness='native_scope_unavailable')


def poll_one(path,receipt):
    from .shared_refresh import _request, _source_workspace, _continuity, _resources
    from .goal_supervision import _save
    from .wake_control import delivery_guard
    thread=receipt['thread_id']
    if receipt['state']=='queued':
        source=_request(receipt,'thread/read',dict(threadId=thread,includeTurns=False))['thread']
        if not _source_workspace(receipt,source):
            receipt.update(state='blocked',reason='source_workspace_mismatch');return
        if source['status']['type']!='idle' or source['status'].get('activeFlags'):
            receipt.update(reason='waiting_for_source_idle');return
        goal=_request(receipt,'thread/goal/get',dict(threadId=thread))['goal']
        proof=_request(receipt,METHOD,dict(threadId=thread,dryRun=True))
        if proof!=dict(threadId=thread,queued=False):
            receipt.update(state='blocked',reason='native_scope_unverified');return
        # Recheck the selected conversation after capability/goal observations.
        source=_request(receipt,'thread/read',dict(threadId=thread,includeTurns=False))['thread']
        if not _source_workspace(receipt,source):
            receipt.update(state='blocked',reason='source_workspace_mismatch');return
        if source['status']['type']!='idle' or source['status'].get('activeFlags'):
            receipt.update(reason='waiting_for_source_idle');return
        receipt.update(goal_before=goal,state='reloading',reload_attempted=True,reason=None)
        _save(path,receipt)
        try:
            with delivery_guard(path.parent.parent):
                result=_request(receipt,METHOD,dict(threadId=thread))
            if result!=dict(threadId=thread,queued=True):raise WakeError('native_scope_admission_unverified')
            receipt.update(state='verifying',reload_acknowledged=True)
        except Exception as exc:
            receipt.update(state='uncertain',reason='reload_outcome_uncertain',observation_error=type(exc).__name__)
            return
        _save(path,receipt)
    if receipt['state'] in ('reloading','verifying','uncertain'):
        goal=_request(receipt,'thread/goal/get',dict(threadId=thread))['goal']
        if not _continuity(receipt['goal_before'],goal):
            receipt.update(state='blocked',reason='goal_continuity_unverified');return
        checks=_resources(receipt)
        if checks is None:
            receipt.update(state='blocked',reason='source_workspace_mismatch');return
        receipt.update(goal_after=goal,goal_continuity_verified=True,resource_status=checks)
        if all(check['state']=='ready' for check in checks.values()):
            receipt.update(state='completed',reason=None)
        elif receipt['state']!='uncertain':
            receipt.update(state='verifying',reason='requested_resources_not_ready')
