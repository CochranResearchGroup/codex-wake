"""Durable external-supervision notices; control and presentation stay independent.

The controller records intent before presentation. A native acknowledgement proves
only append/notification publication, never rendering or a human reading it.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from datetime import datetime, timezone

KINDS = frozenset(('activation', 'engagement', 'checkpoint', 'stop', 'recovery', 'deactivation', 'reactivation', 'admission','request_activation'))
_EVENT = re.compile(r'notice_[a-f0-9]{64}')


def _directory(root):
    from .goal_supervision import _directory as supervision_directory, _private
    directory = supervision_directory(root) / 'notices'
    directory.mkdir(mode=0o700, exist_ok=True)
    _private(directory, True)
    return directory


def _path(directory, event_id):
    if not isinstance(event_id, str) or not _EVENT.fullmatch(event_id):
        raise ValueError('exact supervision notice identifier required')
    return directory / (event_id + '.json')


def _read(path):
    from .goal_supervision import _private
    _private(path)
    with path.open() as source:
        raw = source.read(65537)
    if len(raw.encode()) > 65536:
        raise ValueError('supervision notice exceeds retained bounds')
    event = json.loads(raw)
    if event.get('version') != 1 or event.get('event_id') != path.stem:
        raise ValueError('supervision notice identity unavailable')
    return event


def read_notice(root, event_id):
    return _read(_path(_directory(root), event_id))


def list_notices(root, thread_id):
    from .goal_supervision import _name
    _name(thread_id)
    paths = list(_directory(root).glob('notice_*.json'))
    if len(paths) > 10000:
        raise ValueError('supervision notice capacity reached; history retained')
    return [event for path in sorted(paths) if (event := _read(path))['identity']['thread_id'] == thread_id]


def record_notice(root, receipt, kind, *, controller=None):
    """Retain one semantic event across repeated polls and watcher restarts."""
    from .goal_supervision import _lock, _name, _save
    if kind not in KINDS:
        raise ValueError('unsupported supervision notice kind')
    _name(receipt['thread_id'])
    if kind == 'engagement':
        acknowledgement = receipt.get('poll_ack') or {}
        generation = (controller or {}).get('generation', receipt.get('controller_generation'))
        if (acknowledgement.get('enrollment_revision') != receipt.get('enrollment_revision')
                or not generation or acknowledgement.get('controller_generation') != generation
                or receipt.get('accounting', {}).get('state') != 'qualified'
                or receipt.get('state') not in ('armed', 'checkpoint_requested')):
            raise ValueError('engagement notice requires qualified first-poll acknowledgement')
    stop = receipt.get('first_stop') or {}
    if kind=='recovery' and receipt.get('recovery_events'):
        recovery=receipt['recovery_events'][-1]
        receipt=dict(receipt,active_stop_id=recovery['stop_episode_id'],reason=recovery['reason'])
    identity = dict(thread_id=receipt['thread_id'], allocation_id=receipt['allocation_id'],
        generation=receipt['generation'], enrollment_revision=receipt.get('enrollment_revision', 1),
        kind=kind,governor_revision=receipt.get('governor_revision',0))
    if kind in ('stop', 'recovery'):
        identity.update(stop_episode=receipt.get('active_stop_id') or receipt.get('stop_episode_id') or
            [stop.get('boot_id'), stop.get('observed_boottime'), receipt.get('pause_epoch', 0)],
            reason=receipt.get('reason') or stop.get('reason'), work_turns=sorted(receipt.get('stop_turns', [])))
    if kind=='request_activation':identity['request_accounting']=receipt['request_accounting']
    if kind=='admission':identity['request_admission_event']=receipt['request_admission_event']
    stable_identity=dict(identity)
    if receipt.get('active_stop_id'):
        # Captured turns may be refined by later control readback in this episode.
        stable_identity.pop('work_turns',None)
    event_id = 'notice_' + hashlib.sha256(json.dumps(stable_identity, sort_keys=True).encode()).hexdigest()
    directory = _directory(root)
    with _lock(directory, event_id):
        path = _path(directory, event_id)
        if path.exists():
            event = _read(path)
            event['proof']['control'] = dict(stop_verified=receipt.get('stop_proof') is True,
                state=receipt.get('state'), reason=receipt.get('reason'))
            if event['delivery']['attempts'] == 0:
                event['text'] = render_notice(event)
            _save(path, event)
            return event
        if sum(1 for _ in directory.glob('notice_*.json')) >= 10000:
            raise ValueError('supervision notice capacity reached; history retained')
        snapshot = {key: receipt.get(key) for key in ('used_tokens', 'token_limit', 'token_accounting',
            'deadline', 'checkpoint_token_percent', 'checkpoint_seconds', 'state', 'reason', 'lifetime_tokens_before_window','governor_enabled')}
        event = dict(version=1, event_id=event_id, identity=identity, snapshot=snapshot,
            recorded_at=datetime.now(timezone.utc).isoformat(),
            controller_generation=(controller or {}).get('generation', receipt.get('controller_generation')),
            proof=dict(control=dict(stop_verified=receipt.get('stop_proof') is True,
                state=receipt.get('state'), reason=receipt.get('reason')),
                recorded=dict(state='recorded'), transcript=dict(state='pending'),
                model_context=dict(state='pending'), notification=dict(state='pending'),
                ui=dict(state='unverified'), human_response=dict(state='unobserved')),
            delivery=dict(state='pending', attempts=0))
        event['text'] = render_notice(event)
        _save(path, event)
        return event


def render_notice(event):
    identity, snapshot = event['identity'], event['snapshot']
    used, limit = snapshot.get('used_tokens'), snapshot.get('token_limit')
    usage = f'{used:,} of {limit:,}' if type(used) is int and type(limit) is int else 'usage unavailable'
    remaining = f'{max(0, limit-used):,}' if type(used) is int and type(limit) is int else 'unknown'
    kind = identity['kind']
    if kind=='request_activation':
        selected=identity['request_accounting']
        return (f"Governor request-path owner configured. Effective mode {'inactive' if snapshot.get('governor_enabled') is False else selected['mode']} for reviewed HTTP Responses path only; WS/compact/bypass remain unqualified. "
            f"Scope {identity['allocation_id']}; session {identity['thread_id']}. "
            'ObjectiveLedger owns aggregate request accounting; original prior usage, caps and deadlines retained. No work resumed or resources renewed. '
            'Say "Deactivate governor"; verified operator control needs no model inference. '
            f"[External supervision event {event['event_id']}]")
    if kind=='admission':
        return (f"Model request denied before provider submission. Scope {identity['allocation_id']}; session {identity['thread_id']}. "
            'Reason: objective/session resources unavailable or accounting uncertain. Mode hard_admission applies only to the selected qualified HTTP path. '
            'Say "Deactivate governor" in this conversation; verified operator control needs no provider inference. No work resumed or resources renewed. '
            f"[External supervision event {event['event_id']}]")
    if kind in ('deactivation','reactivation'):
        text=('Governor inactive. Drop stale governor checkpoint/stop instructions. Independent platform controls remain. '
              'Say "Reactivate governor" to enable sampled stopping. ' if kind=='deactivation' else
              'Governor reactivated. Mode sampled_stop; maximum overshoot is not bounded. Say "Deactivate governor" to disable. ')
        text += (f"Governor revision {identity.get('governor_revision',0)} supersedes older notices; latest durable scope state is authoritative. "
                 f"Scope {identity['allocation_id']}; session {identity['thread_id']}. "
                 'Accounting and checkpoints preserved; no resource renewal or work resume. '
                 f"At {event.get('recorded_at','unknown')}. [External supervision event {event['event_id']}]")
        if len(text.encode())>768:raise ValueError('governor notice exceeds native bound')
        return text
    if kind == 'stop':
        title = 'Goal paused' if event['proof']['control']['stop_verified'] else 'Stop requested; interruption unverified'
    elif kind == 'checkpoint':
        title = 'Checkpoint now within the remaining allowance'
    elif kind == 'activation':
        title = 'Governor activated'
    elif kind == 'engagement':
        title = 'External goal watcher engaged'
    else:
        title = 'Supervision recovered; goal remains paused'
    deadline = snapshot.get('deadline')
    deadline_text = datetime.fromtimestamp(deadline, timezone.utc).isoformat() if type(deadline) in (int, float) else 'unknown'
    text = (f"{title}. Reason: {snapshot.get('reason') or kind}. Used {usage} tokens "
        f"({snapshot.get('token_accounting') or 'unknown'}); remaining {remaining}. "
        f"Deadline {deadline_text} (UTC). Scope {identity['allocation_id']}; session {identity['thread_id']}. ")
    lifetime=(snapshot.get('lifetime_tokens_before_window') or 0)+(used if type(used) is int else 0)
    text += f'Current window; lifetime used {lifetime:,}. '
    if kind == 'engagement':
        text += (f"Checkpoint reserve {snapshot.get('checkpoint_token_percent')}% tokens / "
            f"{snapshot.get('checkpoint_seconds')} seconds. Watcher healthy. ")
    else:
        text += ('Extend allowance / Reset budget window / Keep stopped. '
            'Native /goal resume alone does not renew this external allowance. ')
    text += ('Mode sampled_stop; maximum overshoot is not bounded. '
        'Say "Deactivate governor". '
        f"At {event.get('recorded_at', 'unknown')}. " )
    return text + f"[External supervision event {event['event_id']}]"


class NativeNoticeAdapter:
    """The qualified no-turn native extension; stock runtimes refuse explicitly."""
    def __init__(self, root):
        self.root = Path(root)

    def _request(self, event, method):
        from .goal_supervision import _directory as supervision_directory, _name, _private
        from .native_protocol import native_request
        identity = event['identity']
        path = supervision_directory(self.root) / (_name(identity['thread_id']) + '.json')
        _private(path)
        receipt = json.loads(path.read_text())
        if any(receipt.get(key) != identity[key] for key in ('thread_id', 'allocation_id', 'generation')):
            raise ValueError('notice target allocation or generation changed')
        grant = receipt['grant']
        params = dict(threadId=identity['thread_id'], eventId=event['event_id'])
        if method == 'thread/notice/append':
            params['text'] = event['text']
        return native_request(grant['app_server'], grant['codex_path'], method, params, grant['rpc_timeout'])

    def append(self, event):
        result = self._request(event, 'thread/notice/append')
        if result.get('eventId') != event['event_id'] or result.get('recorded') is not True:
            raise ValueError('native notice append acknowledgement differs')
        return dict(transcript=True, model_context=result.get('modelContextAvailable') is True,
            notification_published=result.get('notificationPublished') is True)

    def reconcile(self, event):
        result = self._request(event, 'thread/notice/read')
        notice = result.get('notice')
        if notice is None:
            return dict(transcript=False, model_context=False, notification_published=None)
        if notice != dict(eventId=event['event_id'], text=event['text']):
            raise ValueError('native retained notice differs from original event')
        return dict(transcript=True, model_context=result.get('modelContextAvailable') is True,
            notification_published=None)


def _proof(event, result):
    for field, key, yes in (('transcript', 'transcript', 'appended'),
            ('model_context', 'model_context', 'available'),
            ('notification', 'notification_published', 'published')):
        if result.get(key) is True:
            event['proof'][field] = dict(state=yes)
    if result.get('transcript') is True:
        event['delivery']['state'] = 'recorded'
    return event


def present_notice(root, event_id, *, adapter=None):
    """Append once, then reconcile unknown I/O; never dispatch or interrupt a turn.

    Reconciliation proving absence cannot authorize replay of ambiguous append.
    Reconnection renders persisted native history; it does not repeat append.
    """
    from .goal_supervision import _lock, _save
    directory = _directory(root)
    adapter = adapter or NativeNoticeAdapter(root)
    with _lock(directory, event_id):
        path = _path(directory, event_id)
        event = _read(path)
        if event['delivery']['state'] == 'recorded':
            return event
        if event['delivery']['state'] in ('unknown', 'inflight'):
            try:
                result = adapter.reconcile(event)
                _proof(event, result)
            except Exception as error:
                event['delivery']['last_error'] = type(error).__name__
            _save(path, event)
            return event
        # Unsubmitted historical events still explain their original outcome,
        # without presenting an old activation/stop as today's control choice.
        # Never rewrite text after any append attempt (including an unknown one).
        if event['delivery']['attempts']==0:
            from .goal_governance import snapshot
            current=snapshot(root,event['identity']['thread_id'])
            if (current['state']=='available' and current['revision']!=event['identity'].get('governor_revision',0)):
                event.setdefault('historical',dict(original_text=event['text']))
                mode=current['mode']
                identity=event['identity'];observed=event['snapshot']
                event['text']=(f"Historical {identity['kind']} event: {observed.get('reason') or identity['kind']}; "
                    f"usage {observed.get('used_tokens')}/{observed.get('token_limit')}. "
                    f"Current governor revision {current['revision']} is {mode}. This historical delivery does not reactivate governance. "
                    'Honor latest durable scope state; drop superseded governor instructions. Independent platform controls remain. '
                    f"Scope {identity['allocation_id']}; session {identity['thread_id']}. "
                    f"[External supervision event {event['event_id']}]")
                if len(event['text'].encode())>768:
                    raise ValueError('historical notice exceeds native bound')
                _save(path,event)
        # The read-only lookup also qualifies support before append. Only this
        # positively unsubmitted path can return pending/unsupported and retry.
        try:
            found = adapter.reconcile(event)
        except Exception as error:
            from .native_protocol import NativeCapabilityUnavailable
            from .records import WakeError
            unsupported=(isinstance(error,NativeCapabilityUnavailable) or
                (isinstance(error,ValueError) and not isinstance(error,WakeError)))
            event['delivery'].update(state='unsupported' if unsupported else 'pending',
                last_error=type(error).__name__,next_action=(
                    'Use a native runtime with thread/notice/append and thread/notice/read; '
                    'keep this notice pending. No notification turn is started.' if unsupported else
                    'Restore the native connection; the unsubmitted notice remains pending.'))
            _save(path, event)
            return event
        if found.get('transcript') is True:
            _proof(event, found)
            _save(path, event)
            return event
        event['delivery'].update(state='inflight', attempts=event['delivery']['attempts'] + 1)
        _save(path, event)
        try:
            _proof(event, adapter.append(event))
            if event['delivery']['state'] == 'inflight':
                event['delivery']['state'] = 'unknown'
        except Exception as error:
            event['delivery'].update(state='unknown', last_error=type(error).__name__)
        _save(path, event)
        return event


def run_presenter(root, stop):
    """Bounded independent I/O lane; never delays the enforcement poll loop.

    Retained unknown effects are reconciled by readback, never blindly replayed.
    Unsupported native capability is retried after watcher restart/upgrade.
    """
    unsupported=set()
    while True:
        finishing=stop.is_set()
        try:
            paths=list(_directory(root).glob('notice_*.json'))
            if len(paths)>10000:
                return  # retain capacity failure; never discard history
            for path in sorted(paths):
                if stop.is_set() and not finishing:break
                if path.stem in unsupported:continue
                event=_read(path)
                if event['delivery']['state']=='recorded':continue
                result=present_notice(root,event['event_id'])
                if result['delivery']['state']=='unsupported':unsupported.add(event['event_id'])
        except Exception:
            # Per-event durable state records native errors; corrupt local state
            # cannot stop enforcement. Inspection retains the original evidence.
            pass
        if finishing:return
        stop.wait(.2)


def governor_status(root, receipt):
    """Independent inspection exposes control state even if notice delivery fails."""
    status = dict(identity='Codex Wake governor', scope=receipt['allocation_id'],
        mode='inactive' if receipt.get('governor_enabled',True) is False else receipt.get('request_accounting',{}).get('mode','sampled_stop'),
        enabled=receipt.get('governor_enabled',True), maximum_token_overshoot=None,
        controls=['Inspect governor', 'Reactivate governor' if receipt.get('governor_enabled',True) is False else 'Deactivate governor', 'Keep stopped'],
        intervention=None)
    ids = receipt.get('notice_ids', {})
    for kind in ('activation', 'engagement', 'checkpoint', 'stop', 'recovery', 'deactivation', 'reactivation','admission','request_activation'):
        event_id = ids.get(kind)
        if not event_id:
            continue
        try:
            event = read_notice(root, event_id)
            summary = dict(event_id=event_id, kind=kind, text=event['text'],
                reason=event['snapshot'].get('reason'),
                presentation=event['delivery']['state'],
                next_action=event['delivery'].get('next_action') or
                    'Inspect retained notices; verify native model delivery and operator display separately.',
                ui=event['proof']['ui']['state'],
                model_context=event['proof']['model_context']['state'])
        except (OSError, ValueError, KeyError):
            summary = dict(event_id=event_id, kind=kind, presentation='unavailable',
                next_action='Inspect governor notice storage and native delivery; intervention remains in effect.')
        status[kind] = summary
        if kind in ('checkpoint', 'stop', 'recovery','admission'):
            status['intervention'] = summary
    if receipt.get('notice_record_error'):
        status['notice_error'] = receipt['notice_record_error']
    return status
