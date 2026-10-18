"""Exact-assignment interruption after the caller has paused root delivery."""
import fcntl
import hashlib
import json
import os
import stat
import tempfile
from contextlib import contextmanager
from pathlib import Path

from .native_protocol import native_request


def _private(path, directory=False):
    info = path.lstat()
    if (info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) != (0o700 if directory else 0o600)
            or not (stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode))):
        raise ValueError('unsafe_interrupt_journal_path')


@contextmanager
def _lock(path):
    descriptor = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, 'a') as stream:
        _private(path)
        current = os.fstat(stream.fileno())
        visible = path.lstat()
        if (current.st_dev, current.st_ino) != (visible.st_dev, visible.st_ino):
            raise ValueError('interrupt_lock_identity_changed')
        fcntl.flock(stream, fcntl.LOCK_EX)
        yield


def _save(path, value):
    _private(path.parent, directory=True)
    if path.exists() or path.is_symlink():
        _private(path)
    descriptor, temporary = tempfile.mkstemp(prefix='.interrupt-', dir=path.parent)
    try:
        with os.fdopen(descriptor, 'w') as stream:
            stream.write(json.dumps(value, sort_keys=True) + '\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _handoff_stopped(path, receipt):
    """Recognize only the owning supervisor's completed emergency-stop proof."""
    try:
        source = receipt['thread_id']
        target = receipt['successor_thread_id']
        goal = receipt['successor_goal']
        owner_path = path.parent / ('owner-' + hashlib.sha256(source.encode()).hexdigest() + '.json')
        owner = json.loads(owner_path.read_text())
        return (receipt.get('state') == 'blocked'
                and receipt.get('continuation_stop_reason') == 'emergency_interrupt'
                and not receipt.get('uncertain_effect') and not receipt.get('monitor_error')
                and goal.get('status') == 'paused' and goal.get('threadId') == target
                and isinstance(goal.get('objective'), str) and bool(goal['objective'])
                and type(goal.get('tokenBudget')) is int and goal['tokenBudget'] > 0
                and type(goal.get('createdAt')) is int
                and owner.get('intent_fingerprint') == receipt['fingerprint']
                and owner.get('source_thread_id') == source
                and owner.get('successor_thread_id') == target
                and owner.get('state') == 'stopped')
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return False


def interrupt_owned(root: Path) -> list[dict]:
    """Interrupt proven native assignments; delegate handoffs to their supervisor.

    A lost response is reconciled by observation on a later invocation, never
    repeated. The caller owns root selection, authorization and delivery pause.
    """
    root = Path(root)
    journal = root / 'emergency-interrupt'
    try:
        journal.mkdir(mode=0o700, parents=True, exist_ok=True)
        _private(journal, directory=True)
    except (OSError, ValueError):
        return [dict(actor=str(root), state='held', reason='unsafe_interrupt_journal_path')]
    candidates = []
    from .records import iter_records
    for found in iter_records(root):
        record = found.record
        target = record.get('target', {})
        delivery = record.get('native_delivery', {})
        if target.get('transport') == 'native' and delivery.get('submission_id'):
            from .native_delivery import native_prompt
            prompt = native_prompt(root, record)
            target = dict(target, _expected_evidence=delivery.get('evidence'))
            candidates.append((record['id'], target, delivery.get('evidence', {}).get('client_message_id'), prompt,
                               delivery.get('prompt_sha256')))
        elif record.get('status') == 'submitted':
            candidates.append((record['id'], None, None, None, None))
    for path in (root / 'lifecycle').glob('*.json'):
        if path.name.startswith('owner-') or path.name == 'supervision.json':
            continue
        try:
            receipt = json.loads(path.read_text())
            intent = receipt.get('intent', {})
            if intent.get('operation') == 'handoff':
                # Only the resident owner may pause an owned continuation goal.
                candidates.append((str(path), 'handoff_settled' if _handoff_stopped(path, receipt) else 'handoff', None, None, None))
            elif intent.get('operation') == 'spawn' and receipt.get('submission_id'):
                profile = intent['launch']
                target = dict(endpoint=profile['app_server'], codex_cmd=profile['codex_path'],
                              thread_id=receipt['thread_id'])
                candidates.append((str(path), target, receipt['submission_id'], intent['task'],
                                   hashlib.sha256(intent['task'].encode()).hexdigest()))
        except (OSError, ValueError, KeyError, TypeError):
            candidates.append((str(path), None, None, None, None))
    results = []
    for actor, target, submission, prompt, digest in candidates:
        result = dict(actor=actor)
        if target == 'handoff_settled':
            result.update(state='settled', reason='resident_handoff_emergency_stop_proven')
            results.append(result)
            continue
        if target == 'handoff':
            result.update(state='monitor_required', reason='resident_handoff_owner_required')
            results.append(result)
            continue
        if not isinstance(target, dict) or not digest:
            result.update(state='unsupported', reason='exact_native_assignment_unavailable')
            results.append(result)
            continue
        path = journal / (hashlib.sha256(actor.encode()).hexdigest() + '.json')
        try:
            with _lock(path.with_suffix('.lock')):
                if path.exists() or path.is_symlink():
                    _private(path)
                result = _interrupt_candidate(path, target, submission, prompt, digest, result)
        except Exception as exc:
            result.update(state='held', reason=str(exc) if isinstance(exc, ValueError) else type(exc).__name__)
        results.append(result)
    from .strict_runtime import stop_execution
    for binding_path in (root/'strict-execution').glob('*/binding.json'):
        try:
            binding=json.loads(binding_path.read_text())
            result=stop_execution(root,binding['objective_id'],'operator_emergency_interrupt')
            results.append(dict(actor=binding['objective_id'],state=result['state'],reason=result.get('reason')))
        except Exception as exc:
            results.append(dict(actor=str(binding_path),state='uncertain',reason=type(exc).__name__))
    return results


def _interrupt_candidate(path, target, submission, prompt, digest, result):
    try:
        if hashlib.sha256(prompt.encode()).hexdigest() != digest:
            raise ValueError('assignment_payload_changed')
        if not submission:
            from .native_delivery import native_evidence
            evidence, reason = native_evidence(target, prompt)
            if not evidence or evidence.get('source') != 'native_turn':
                raise ValueError(reason or 'owned_turn_not_observed')
            submission = evidence['client_message_id']
        def request(method, params):
            return native_request(target['endpoint'], target['codex_cmd'], method, params, 10)
        thread = request('thread/read', dict(threadId=target['thread_id'], includeTurns=True))['thread']
        if thread.get('id') != target['thread_id']:
            raise ValueError('native_thread_identity_changed')
        owned = [turn for turn in thread['turns'] if any(
            item.get('type') == 'userMessage' and item.get('clientId') == submission
            and isinstance(item.get('content'), list) and len(item['content']) == 1
            and item['content'][0].get('type') == 'text'
            and item['content'][0].get('text') == prompt
            and not item['content'][0].get('text_elements')
            for item in turn.get('items', []))]
        if len(owned) != 1:
            raise ValueError('exact_owned_turn_unavailable')
        turn = owned[0]
        evidence = target.get('_expected_evidence')
        if evidence and (evidence.get('source') != 'native_turn'
                or evidence.get('turn_id') != turn['id']
                or not any(item.get('id') == evidence.get('user_message_id')
                    and item.get('clientId') == submission for item in turn.get('items', []))):
            raise ValueError('persisted_native_evidence_changed')
        previous = json.loads(path.read_text()) if path.exists() else None
        identity = dict(thread_id=target['thread_id'], turn_id=turn['id'], submission_id=submission,
                        prompt_sha256=digest)
        if previous and previous.get('identity') != identity:
            raise ValueError('interrupt_assignment_changed')
        if turn.get('status') not in ('inProgress', 'completed', 'failed', 'interrupted'):
            raise ValueError('native_turn_status_unknown')
        if turn.get('status') != 'inProgress':
            result.update(state='settled', turn_id=turn['id'], turn_status=turn.get('status'))
            if previous:
                _save(path, dict(identity=identity, state='settled', turn_status=turn.get('status')))
        elif any(t.get('status') == 'inProgress' and t['id'] != turn['id'] for t in thread['turns']):
            raise ValueError('foreign_running_turn_preserved')
        elif previous:
            result.update(state='uncertain', reason='interrupt_unobserved', turn_id=turn['id'])
        else:
            _save(path, dict(identity=identity, state='uncertain'))
            request('turn/interrupt', dict(threadId=target['thread_id'], turnId=turn['id']))
            final = request('thread/read', dict(threadId=target['thread_id'], includeTurns=True))['thread']
            matching = [t for t in final.get('turns', []) if t.get('id') == turn['id']]
            if final.get('id') != target['thread_id'] or len(matching) != 1 or matching[0].get('status') not in ('completed', 'failed', 'interrupted'):
                result.update(state='uncertain', reason='interrupt_unobserved', turn_id=turn['id'])
            else:
                _save(path, dict(identity=identity, state='settled', turn_status=matching[0]['status']))
                result.update(state='interrupted' if matching[0]['status'] == 'interrupted' else 'settled',
                              turn_id=turn['id'], turn_status=matching[0]['status'])
    except Exception as exc:
        result.update(state='uncertain' if path.exists() else 'held', reason=str(exc) if isinstance(exc, ValueError) else type(exc).__name__)
    return result
