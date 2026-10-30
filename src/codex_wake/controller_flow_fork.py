"""Qualified immutable-checkpoint fork variant; unknown native APIs fail closed.

This is a provider-free adapter contract, not qualification of a packaged native
build. Readonly source observation is separate from admitted native mutation.
"""
import hashlib
import json
from .managed_inventory import InventoryError


def fork_capability(profile, metadata):
    if ('fork' not in profile['modes'] or not {'thread/fork','thread/fork@checkpoint_v1'} <= set(profile['methods'])
            or metadata.get('forkCheckpointV1') is not True):
        raise InventoryError('unsupported_fork_variant','native immutable checkpoint fork variant is not qualified')


def checkpoint(owner, profile, target):
    source = target.get('conversation_id')
    if not isinstance(source,str) or not source:
        raise InventoryError('invalid_argument','source conversation identity required')
    thread = owner.request(profile['endpoint'],profile['target']['executable'],'thread/read',
        dict(threadId=source,includeTurns=True),5)['thread']
    identity = owner._identity(profile,thread)
    identifier = thread.get('checkpointId')
    if identity.thread_id != source or not isinstance(identifier,str) or not 0<len(identifier)<=200:
        raise InventoryError('unsupported_fork_variant','native readonly immutable checkpoint identity unavailable')
    raw = json.dumps(thread,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
    if len(raw)>1048576:
        raise InventoryError('invalid_argument','source snapshot exceeds bounded checkpoint size')
    return dict(source_target=target,checkpoint_id=identifier,snapshot_sha256=hashlib.sha256(raw).hexdigest(),
                variant='checkpoint_v1',profile_revision=profile['revision'])


def fork(owner, profile, target, pinned):
    if not isinstance(pinned,dict) or checkpoint(owner,profile,target) != pinned:
        raise InventoryError('stale_checkpoint','source snapshot changed since common checkpoint selection')
    result = owner.request(profile['endpoint'],profile['target']['executable'],'thread/fork',
        dict(threadId=target['conversation_id'],checkpointId=pinned['checkpoint_id'],
             expectedSnapshotSha256=pinned['snapshot_sha256'],cwd=profile['cwd']),5)
    native = owner._identity(profile,result.get('thread'))
    proof = dict(sourceThreadId=target['conversation_id'],checkpointId=pinned['checkpoint_id'],
                 sourceSnapshotSha256=pinned['snapshot_sha256'])
    if native.thread_id == target['conversation_id'] or result.get('forkProvenance') != proof:
        raise InventoryError('uncertain_effect','native fork did not prove distinct child and pinned checkpoint provenance')
    with owner.runtime.connect() as db:
        rows = db.execute("SELECT record FROM operations").fetchall()
    for (raw,) in rows:
        previous = json.loads(raw)
        child = (previous.get('result') or {}).get('target',{})
        if previous['operation']=='sessions.fork' and child.get('conversation_id') == native.thread_id and child.get('namespace') == target['namespace']:
            raise InventoryError('uncertain_effect','native fork reused an existing child identity')
    if checkpoint(owner,profile,target) != pinned:
        raise InventoryError('uncertain_effect','source snapshot changed during native fork; do not replay')
    return dict(target=dict(target,conversation_id=native.thread_id),checkpoint=pinned,provenance=proof,
                account_identity='unverified',authority='inherited',allocation_created=False)
