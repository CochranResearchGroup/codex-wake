"""Completed persisted prefixes using the existing native thread/fork API.

Native admission enforces canonical persisted turn IDs. Wake additionally compares
full retained turns before returning a child that may receive its first prompt.
No goal inheritance/defer option or destructive child-repair fallback is used.
"""
import hashlib
import json
from .managed_inventory import InventoryError


def fork_capability(profile, metadata):
    if 'fork' not in profile['modes'] or not {'thread/fork', 'thread/read'} <= set(profile['methods']):
        raise InventoryError('unsupported_fork_variant', 'native completed-prefix fork method is not configured')


def _read(owner, profile, identifier):
    thread = owner.request(profile['endpoint'], profile['target']['executable'], 'thread/read',
                           dict(threadId=identifier, includeTurns=True), 5)['thread']
    if owner._identity(profile, thread).thread_id != identifier:
        raise InventoryError('unsupported_fork_variant', 'native thread identity changed')
    if thread.get('ephemeral') is not False or not isinstance(thread.get('path'), str) or not thread['path']:
        raise InventoryError('unsupported_fork_variant', 'checkpoint requires persisted non-ephemeral history')
    return thread


def _prefix(thread, turn_id=None):
    turns = thread.get('turns')
    if not isinstance(turns, list) or not turns:
        raise InventoryError('unsupported_fork_variant', 'completed persisted checkpoint is unavailable')
    if turn_id is None:
        # Do not silently select an earlier checkpoint while a newer turn runs.
        turn_id = turns[-1].get('id')
    ids = [turn.get('id') for turn in turns]
    if (not isinstance(turn_id, str) or not turn_id or turn_id not in ids or
            any(not isinstance(item, str) or not item for item in ids) or len(set(ids)) != len(ids)):
        raise InventoryError('unsupported_fork_variant', 'checkpoint turn identity is unavailable or ambiguous')
    prefix = turns[:ids.index(turn_id) + 1]
    if prefix[-1].get('status') != 'completed' or any(turn.get('status') == 'inProgress' for turn in prefix):
        raise InventoryError('unsupported_fork_variant', 'checkpoint must end at a completed persisted turn')
    if any(not isinstance(turn.get('items'), list) or turn.get('itemsView', 'full') != 'full' for turn in prefix):
        raise InventoryError('unsupported_fork_variant', 'full checkpoint items are unavailable')
    # Thread metadata changes on fork; retained turn identities, order and items do not.
    raw = json.dumps(prefix, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    if len(raw) > 1048576:
        raise InventoryError('invalid_argument', 'source prefix exceeds bounded checkpoint size')
    return turn_id, prefix, hashlib.sha256(raw).hexdigest()


def checkpoint(owner, profile, target, turn_id=None):
    source = target.get('conversation_id')
    if not isinstance(source, str) or not source:
        raise InventoryError('invalid_argument', 'source conversation identity required')
    identifier, unused, digest = _prefix(_read(owner, profile, source), turn_id)
    return dict(source_target=target, last_turn_id=identifier, snapshot_sha256=digest,
                variant='completed_turn', profile_revision=profile['revision'])


def fork(owner, profile, target, pinned):
    if (not isinstance(pinned, dict) or not isinstance(pinned.get('last_turn_id'), str) or
            checkpoint(owner, profile, target, pinned['last_turn_id']) != pinned):
        raise InventoryError('stale_checkpoint', 'source completed prefix changed since selection')
    result = owner.request(profile['endpoint'], profile['target']['executable'], 'thread/fork',
                           dict(threadId=target['conversation_id'], lastTurnId=pinned['last_turn_id'],
                                cwd=profile['cwd'], ephemeral=False), 5)
    native = owner._identity(profile, result.get('thread'))
    if native.thread_id == target['conversation_id']:
        raise InventoryError('uncertain_effect', 'native fork returned the source identity')
    with owner.runtime.connect() as db:
        rows = db.execute('SELECT record FROM operations').fetchall()
    for (raw,) in rows:
        previous = json.loads(raw)
        child = (previous.get('result') or {}).get('target', {})
        if previous['operation'] == 'sessions.fork' and child.get('conversation_id') == native.thread_id and child.get('namespace') == target['namespace']:
            raise InventoryError('uncertain_effect', 'native fork reused an existing child identity')
    child = _read(owner, profile, native.thread_id)
    identifier, prefix, digest = _prefix(child)
    if identifier != pinned['last_turn_id'] or digest != pinned['snapshot_sha256']:
        raise InventoryError('uncertain_effect', 'child retained turns do not match the pinned completed prefix')
    if checkpoint(owner, profile, target, pinned['last_turn_id']) != pinned:
        raise InventoryError('uncertain_effect', 'source prefix changed during fork; do not replay')
    proof = dict(sourceThreadId=target['conversation_id'], lastTurnId=identifier,
                 retainedTurnIds=[turn['id'] for turn in prefix], retainedPrefixSha256=digest,
                 verification='wake_child_readback')
    return dict(target=dict(target, conversation_id=native.thread_id), checkpoint=pinned, provenance=proof,
                account_identity='unverified', authority='inherited', allocation_created=False)
