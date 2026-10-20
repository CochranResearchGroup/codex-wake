"""Private host maintenance permits, separate from resource allocation authority.

Same-UID code is trusted by the host, as for the allocation policy. This is not a
security boundary against hostile same-UID processes. No MCP permit API exists.
"""
from contextlib import ExitStack
import hashlib
import json
from pathlib import Path
import time

from .goal_supervision import _directory, _heartbeat, _lock, _native, _private, _save
from .process import boot_id_value

# Runtime observations/effect acknowledgements may change during preparation;
# authority, stop latches and fixed accounting boundaries may not.
AUTHORITY = ('thread_id','generation','allocation_id','grant','policy_path','allocation_path',
    'goal_created_at','deadline','time_origin','token_limit','time_limit_seconds','token_accounting',
    'boot_id','started_upper','started_boottime','reset_anchor','stop_latched',
    'checkpoint_token_percent','checkpoint_seconds','winddown_deadline','allocation_winddown_deadline')
ALLOCATION_AUTHORITY=('allocation_id','grant','token_limit','time_limit_seconds','token_accounting',
    'time_origin','deadline','members','stop_latched','boot_id','winddown_deadline')


def _permit_path(directory):
    child=directory/'maintenance'
    child.mkdir(exist_ok=True,mode=0o700);_private(child,True)
    return child/'permit.json'


def _read(path):
    _private(path)
    return json.loads(path.read_text())


def _policy(path, root):
    path=Path(path).absolute()
    if path!=path.resolve():raise ValueError('maintenance policy cannot traverse symlinks')
    value=_read(path)
    if (set(value)!= {'version','enabled','controller_root','max_seconds'} or
            type(value['version']) is not int or value['version']!=1 or value['enabled'] is not True or
            value['controller_root']!=str(root) or type(value['max_seconds']) is not int or
            not 1<=value['max_seconds']<=60):
        raise ValueError('host maintenance policy unavailable or malformed')
    return value,hashlib.sha256(path.read_bytes()).hexdigest()


def admission_guard(directory):
    path=_permit_path(directory)
    if path.exists():
        permit=_read(path)
        heartbeat=_heartbeat(directory)
        if (permit.get('state')=='prepared' and heartbeat.get('fresh') and
                heartbeat.get('generation')==permit['controller']['generation'] and
                time.clock_gettime(time.CLOCK_BOOTTIME)>=permit['expires_boottime']):
            permit['state']='preparation_expired';_save(path,permit)
        if permit.get('state') not in ('prepared','handoff'):return
        raise ValueError('controller maintenance pending; wait for verified replacement')


def _receipts(directory):
    return sorted(p for p in directory.glob('*.json') if p.name!='controller.json')


def _snapshot(receipt):
    return {key:receipt.get(key) for key in AUTHORITY}


def prepare(root,policy_path,seconds):
    directory=_directory(root);root=directory.parent
    permission,digest=_policy(policy_path,root)
    if type(seconds) is not int or not 1<=seconds<=permission['max_seconds']:
        raise ValueError('maintenance interval exceeds host permission')
    with _lock(directory,'maintenance'),ExitStack() as stack:
        admission_guard(directory)
        heartbeat=_heartbeat(directory)
        if not heartbeat['fresh']:raise ValueError('fresh controller required for maintenance')
        receipts={};allocations={}
        for path in _receipts(directory):
            stack.enter_context(_lock(directory,path.stem));receipt=_read(path)
            if not receipt.get('stop_latched'):
                goal,active=_native(receipt['grant'],receipt['thread_id'])
                if (goal and goal.get('status') not in ('paused','blocked','complete','budgetLimited','usageLimited')) or active:
                    raise ValueError('all unlatched campaigns must be inactive before maintenance')
            receipts[path.name]=dict(authority=_snapshot(receipt),used_tokens=receipt['used_tokens'])
            if receipt.get('allocation_path'):
                allocation_path=Path(receipt['allocation_path'])
                with _lock(allocation_path.parent,allocation_path.stem):
                    allocation=_read(allocation_path)
                    allocations[str(allocation_path)]=dict(authority={key:allocation.get(key) for key in ALLOCATION_AUTHORITY},
                        used_tokens=allocation['used_tokens'])
        now=time.clock_gettime(time.CLOCK_BOOTTIME)
        permit=dict(version=1,state='prepared',controller={key:heartbeat[key] for key in
            ('generation','pid','identity','boot_id')},policy_path=str(Path(policy_path).absolute()),
            policy_sha256=digest,prepared_boottime=now,expires_boottime=now+seconds,receipts=receipts,allocations=allocations)
        _save(_permit_path(directory),permit)
        return dict(state='prepared',controller_generation=heartbeat['generation'],
            expires_boottime=permit['expires_boottime'],seconds=seconds,receipt_count=len(receipts),
            next_action='Gracefully stop only the exact controller, then start its replacement within the fixed interval. Goals remain inactive; allocations and latches are preserved.')


def authorize_exit(directory,heartbeat):
    """Caller holds maintenance lock. Any uncertainty follows normal stop path."""
    path=_permit_path(directory)
    if not path.exists():return False
    try:
        permit=_read(path)
        if permit.get('state')!='prepared':return False
        now=time.clock_gettime(time.CLOCK_BOOTTIME)
        if not permit['prepared_boottime']<=now<permit['expires_boottime']:return False
        if permit['controller']!={key:heartbeat[key] for key in ('generation','pid','identity','boot_id')}:return False
        _,digest=_policy(permit['policy_path'],directory.parent)
        if digest!=permit['policy_sha256']:return False
        paths=_receipts(directory)
        if {p.name for p in paths}!=set(permit['receipts']):return False
        with ExitStack() as stack:
            for receipt_path in paths:
                stack.enter_context(_lock(directory,receipt_path.stem));receipt=_read(receipt_path)
                before=permit['receipts'][receipt_path.name]
                if _snapshot(receipt)!=before['authority'] or receipt['used_tokens']<before['used_tokens']:return False
                from .goal_supervision import _grant
                if _grant(receipt['policy_path'],receipt['thread_id'],receipt['allocation_id'],directory.parent)!=receipt['grant']:return False
                if not receipt.get('stop_latched'):
                    goal,active=_native(receipt['grant'],receipt['thread_id'])
                    if (goal and goal.get('status') not in ('paused','blocked','complete','budgetLimited','usageLimited')) or active:return False
            for name,before in permit['allocations'].items():
                allocation_path=Path(name)
                with _lock(allocation_path.parent,allocation_path.stem):
                    allocation=_read(allocation_path)
                    if ({key:allocation.get(key) for key in ALLOCATION_AUTHORITY}!=before['authority'] or
                            allocation['used_tokens']<before['used_tokens']):return False
            # The controller is exiting, not renewing authority. Public readiness
            # still fails on its inactive/stale heartbeat until a new poll succeeds.
            permit.update(state='handoff',departed_boottime=time.clock_gettime(time.CLOCK_BOOTTIME))
            if permit['departed_boottime']>=permit['expires_boottime']:return False
            _save(path,permit)
            return True
    except (OSError,ValueError,KeyError,TypeError):return False


def replacement_observed(directory,heartbeat):
    with _lock(directory,'maintenance'):
        path=_permit_path(directory)
        if not path.exists():return
        permit=_read(path)
        if permit.get('state') not in ('handoff','prepared'):return
        now=time.clock_gettime(time.CLOCK_BOOTTIME)
        if permit['controller']['generation']==heartbeat['generation']:
            if permit['state']=='prepared' and now>=permit['expires_boottime']:
                permit['state']='preparation_expired';_save(path,permit)
            return
        # Poll has already rechecked the original budgets, policy and latches.
        # A missed window becomes an ordinary fail-closed shutdown on restart.
        expired=now>=permit['expires_boottime'] or heartbeat['boot_id']!=permit['controller']['boot_id']
        if expired:
            from .goal_supervision import _stop
            for receipt_path in _receipts(directory):
                with _lock(directory,receipt_path.stem):
                    receipt=_read(receipt_path);_stop(receipt_path,receipt,'maintenance_expired')
        permit.update(state='expired' if expired else 'replaced',replacement_generation=heartbeat['generation'],
            replacement_boottime=now)
        _save(path,permit)
