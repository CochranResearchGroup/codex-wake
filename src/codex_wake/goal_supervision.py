"""Independent native supervision for one exact existing Codex session.

This module requests checkpoints, pauses goals and interrupts exact turns. It
never kills a shared executor, promises tool termination, or renews an allocation.
"""
from contextlib import contextmanager
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import stat
import tempfile
import time
from uuid import UUID, uuid4

from .native_protocol import native_request
from .process import boot_id_value, process_exists, process_identity


def _private(path, directory=False):
    info=path.lstat()
    if path.is_symlink() or info.st_uid!=os.geteuid() or stat.S_IMODE(info.st_mode)&0o077:
        raise ValueError('goal supervision paths must be private and owned')
    if directory and not stat.S_ISDIR(info.st_mode):raise ValueError('goal supervision directory unavailable')
    if not directory and not stat.S_ISREG(info.st_mode):raise ValueError('goal supervision file unavailable')


def _directory(root):
    root=Path(root).absolute()
    if root!=root.resolve():raise ValueError('supervision root cannot traverse symlinks')
    root.mkdir(parents=True,exist_ok=True,mode=0o700);_private(root,True)
    directory=root/'goal-supervision';directory.mkdir(exist_ok=True,mode=0o700);_private(directory,True)
    return directory


def _save(path,value):
    descriptor,temporary=tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(descriptor,'w') as stream:
            json.dump(value,stream,sort_keys=True);stream.flush();os.fsync(stream.fileno())
        os.replace(temporary,path)
        descriptor=os.open(path.parent,os.O_RDONLY)
        try:os.fsync(descriptor)
        finally:os.close(descriptor)
    finally:
        if os.path.exists(temporary):os.unlink(temporary)


@contextmanager
def _lock(directory,name):
    descriptor=os.open(directory/(name+'.lock'),os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    with os.fdopen(descriptor,'a') as stream:
        fcntl.flock(stream,fcntl.LOCK_EX)
        yield


def _name(thread):
    if not isinstance(thread,str) or str(UUID(thread))!=thread:raise ValueError('exact caller UUID required')
    return hashlib.sha256(thread.encode()).hexdigest()


def _load_grant(policy_path,thread):
    path=Path(policy_path).absolute();_private(path)
    if path!=path.resolve():raise ValueError('policy cannot traverse symlinks')
    def unique(pairs):
        result={}
        for key,value in pairs:
            if key in result:raise ValueError('duplicate host policy key')
            result[key]=value
        return result
    policy=json.loads(path.read_text(),object_pairs_hook=unique)
    if type(policy.get('version')) is not int or policy.get('version')!=1:raise ValueError('unsupported goal limits policy')
    grant=policy['callers'][thread]
    for key in ('max_tokens','max_seconds'):
        if type(grant[key]) is not int or grant[key]<=0:raise ValueError('invalid host allocation cap')
    if not isinstance(grant['allocation_id'],str) or not grant['allocation_id']:raise ValueError('allocation identity unavailable')
    for key in ('codex_path','codex_home'):
        selected=Path(grant[key])
        if not selected.is_absolute() or (key=='codex_home' and selected!=selected.resolve()):raise ValueError('host path must be exact and absolute')
    if not Path(grant['codex_path']).is_file():raise ValueError('host Codex executable unavailable')
    endpoint=grant['app_server']
    if not isinstance(endpoint,str) or not endpoint.startswith('unix:///') or not Path(endpoint[7:]).is_absolute():
        raise ValueError('host must approve an exact absolute Unix endpoint')
    timeout=grant.get('rpc_timeout',5)
    if type(timeout) not in (int,float) or not math.isfinite(timeout) or not 0<timeout<=5:raise ValueError('invalid RPC timeout')
    return dict(grant,rpc_timeout=timeout)


def _grant(policy_path,thread):
    try:return _load_grant(policy_path,thread)
    except (KeyError,TypeError,AttributeError) as exc:raise ValueError('host caller grant unavailable or malformed') from exc


def _public(receipt):
    return {key:value for key,value in receipt.items() if key not in ('grant','policy_path','prior_allocation')}


def _request(grant,method,params):
    return native_request(grant['app_server'],grant['codex_path'],method,params,grant['rpc_timeout'])


def _native(grant,thread):
    goal=_request(grant,'thread/goal/get',dict(threadId=thread))['goal']
    native=_request(grant,'thread/read',dict(threadId=thread,includeTurns=True))['thread']
    if native.get('id')!=thread or (goal and goal.get('threadId')!=thread):raise ValueError('native thread identity changed')
    turns=native.get('turns')
    if not isinstance(turns,list):raise ValueError('native turn state unavailable')
    active=[turn['id'] for turn in turns if turn.get('status')=='inProgress']
    if len(active)>1:raise ValueError('native active turn ambiguous')
    return goal,active


def _usage(receipt):
    from .goal_usage import observe_usage
    return observe_usage(receipt['grant']['codex_home'],receipt['thread_id'],receipt['goal_created_at'],
        reset_anchor=receipt.get('reset_anchor'))


def _heartbeat(directory):
    try:
        path=directory/'controller.json';_private(path)
        value=json.loads(path.read_text())
        age=time.clock_gettime(time.CLOCK_BOOTTIME)-value['observed_boottime']
        valid=(value['active'] is True and value['pid']!=os.getpid()
            and value['boot_id']==boot_id_value() and process_exists(value['pid'])
            and process_identity(value['pid'])==value['identity']
            and 0<=age<=max(3,3*value['interval']))
        return dict(value,fresh=valid,age_seconds=age)
    except (OSError,ValueError,KeyError,TypeError):return dict(fresh=False,reason='controller_unavailable')


def show(root,policy_path,caller_thread_id):
    name=_name(caller_thread_id);grant=_grant(policy_path,caller_thread_id)
    directory=_directory(root);path=directory/(name+'.json')
    if not path.exists():return dict(state='held',reason='not_enrolled',thread_id=caller_thread_id,controller=_heartbeat(directory))
    with _lock(directory,name):
        _private(path);receipt=json.loads(path.read_text())
        if receipt['grant']!=grant:
            receipt.update(state='held',reason='host_policy_changed')
        receipt['controller']=_heartbeat(directory)
        if receipt['state'] in ('armed','checkpoint_requested') and not receipt['controller']['fresh']:
            receipt.update(state='held',reason='controller_unavailable')
        receipt['sampled']=True;receipt['maximum_token_overshoot']=None
        return _public(receipt)


def enroll(root,policy_path,caller_thread_id,token_limit,time_limit_seconds,
           checkpoint_token_percent=5,checkpoint_seconds=60):
    name=_name(caller_thread_id);grant=_grant(policy_path,caller_thread_id)
    for key,value,maximum in [('tokens',token_limit,grant['max_tokens']),('seconds',time_limit_seconds,grant['max_seconds'])]:
        if type(value) is not int or not 0<value<=maximum:raise ValueError('requested '+key+' exceed host allocation')
    if type(checkpoint_token_percent) not in (int,float) or not math.isfinite(checkpoint_token_percent) or not 0<=checkpoint_token_percent<=100:
        raise ValueError('invalid checkpoint token reserve')
    if type(checkpoint_seconds) not in (int,float) or not math.isfinite(checkpoint_seconds) or checkpoint_seconds<0:raise ValueError('invalid checkpoint time reserve')
    directory=_directory(root);path=directory/(name+'.json')
    with _lock(directory,name):
        old=None
        if path.exists():_private(path);old=json.loads(path.read_text())
        same=bool(old and old['allocation_id']==grant['allocation_id'])
        if old and any(old['grant'][key]!=grant[key] for key in ('app_server','codex_home')):
            raise ValueError('cross-native session migration is unsupported')
        if same and (token_limit>old['token_limit'] or time_limit_seconds>old['time_limit_seconds']):
            raise ValueError('same allocation may only tighten limits')
        goal,active=_native(grant,caller_thread_id)
        if not goal:raise ValueError('existing native goal required')
        created=old['goal_created_at'] if old else goal['createdAt']
        if type(created) not in (int,float) or not math.isfinite(created):raise ValueError('native goal start unavailable')
        from .lifecycle_budget import trusted_upper
        now=trusted_upper();boottime=time.clock_gettime(time.CLOCK_BOOTTIME)
        if created>now:raise ValueError('native goal start is after qualified current time')
        receipt=dict(old) if same else dict(thread_id=caller_thread_id,generation=uuid4().hex,
            allocation_id=grant['allocation_id'],goal_created_at=created,used_tokens=0,
            started_upper=now,started_boottime=boottime,boot_id=boot_id_value(),
            time_origin=now if old else created,effects={},checkpoint=None,
            prior_allocation=old if old else None)
        receipt.update(grant=grant,policy_path=str(Path(policy_path).absolute()),token_limit=token_limit,
            time_limit_seconds=time_limit_seconds,checkpoint_token_percent=checkpoint_token_percent,
            checkpoint_seconds=checkpoint_seconds)
        receipt['deadline']=receipt['time_origin']+time_limit_seconds
        observation=_usage(receipt)
        if old and not same:
            if observation.get('state')!='qualified' or not observation.get('anchor'):
                raise ValueError('explicit reset requires qualified response history')
            receipt['reset_anchor']=observation['anchor']
            observation=_usage(receipt)
        if observation.get('state')=='qualified' and type(observation.get('used_tokens')) is int:
            if observation['used_tokens']<receipt['used_tokens']:
                receipt.update(state='held',reason='accounting_decreased',stop_latched=True)
            else:
                receipt.update(used_tokens=observation['used_tokens'],accounting=observation,state='armed',reason=None)
        else:receipt.update(state='held',reason='accounting_unknown',accounting=observation,stop_latched=True)
        controller=_heartbeat(directory);receipt['controller_generation']=controller.get('generation')
        if not controller['fresh']:receipt.update(state='held',reason='controller_unavailable')
        if receipt.get('used_tokens',0)>=token_limit or now>=receipt['deadline']:
            receipt.update(state='held',reason='allocation_exhausted',stop_latched=True)
        if same and (old.get('stop_latched') or old['state'] in ('stopped','stop_unverified')):
            receipt.update(state='held',reason='continuation_held',stop_latched=True)
        if receipt['boot_id']!=boot_id_value():
            receipt.update(state='held',reason='boot_identity_changed',stop_latched=True)
        if goal.get('status')=='paused':
            receipt.update(state='held' if active else 'stopped',reason='native_goal_paused',stop_latched=True,stop_proof=not active)
        elif goal.get('status')!='active':
            receipt.update(state='held',reason='native_goal_state_unknown',stop_latched=True)
        _save(path,receipt)
        return dict(_public(receipt),controller=controller,sampled=True,maximum_token_overshoot=None)


def _effect(path,receipt,key,method,params):
    effects=receipt.setdefault('effects',{})
    if key in effects:return effects[key]['state']=='acknowledged'
    effects[key]=dict(state='intended',method=method,params=params)
    _save(path,receipt)
    try:
        _request(receipt['grant'],method,params)
        effects[key]['state']='acknowledged';_save(path,receipt)
        return True
    except Exception as exc:
        effects[key].update(state='uncertain',error=type(exc).__name__);_save(path,receipt)
        return False


def _stop(path,receipt,reason,goal=None,active=None):
    receipt.update(reason=reason,state='stop_unverified',stop_latched=True)
    try:
        if active is None:goal,active=_native(receipt['grant'],receipt['thread_id'])
        if receipt.get('stop_proof') and ((goal and goal.get('status')!='paused') or active):
            receipt['effects']={};receipt['stop_proof']=False
        thread=receipt['thread_id']
        if goal and goal.get('status')!='paused':
            _effect(path,receipt,'pause:'+str(goal['createdAt']),'thread/goal/set',dict(threadId=thread,status='paused',origin='automatic'))
        for turn in active:
            _effect(path,receipt,'interrupt:'+turn,'turn/interrupt',dict(threadId=thread,turnId=turn))
        final_goal,final_active=_native(receipt['grant'],thread)
        proven=(not final_goal or final_goal.get('status')=='paused') and not final_active
        receipt.update(state='stopped' if proven else 'stop_unverified',stop_proof=proven)
    except Exception as exc:receipt['control_error']=type(exc).__name__
    _save(path,receipt)
    return receipt


def poll(root):
    directory=_directory(root);results=[]
    for path in directory.glob('*.json'):
        if path.name=='controller.json':continue
        with _lock(directory,path.stem):
            _private(path);receipt=json.loads(path.read_text())
            try:
                grant=_grant(receipt['policy_path'],receipt['thread_id'])
                if grant!=receipt['grant']:
                    results.append(_stop(path,receipt,'host_policy_changed'));continue
                if boot_id_value()!=receipt['boot_id']:
                    results.append(_stop(path,receipt,'boot_identity_changed'));continue
                elapsed=time.clock_gettime(time.CLOCK_BOOTTIME)-receipt['started_boottime']
                if elapsed<0:
                    results.append(_stop(path,receipt,'elapsed_time_invalid'));continue
                upper=receipt['started_upper']+elapsed
                goal,active=_native(grant,receipt['thread_id'])
                observation=_usage(receipt);receipt['accounting']=observation
                used=observation.get('used_tokens')
                if observation.get('state')!='qualified' or type(used) is not int or used<receipt['used_tokens']:
                    results.append(_stop(path,receipt,'accounting_unknown',goal,active));continue
                receipt['used_tokens']=used;receipt['observed_boottime']=time.clock_gettime(time.CLOCK_BOOTTIME)
                if used>=receipt['token_limit'] or upper>=receipt['deadline']:
                    results.append(_stop(path,receipt,'allocation_exhausted',goal,active));continue
                if receipt.get('stop_latched') or receipt.get('state') in ('stopped','stop_unverified'):
                    results.append(_stop(path,receipt,receipt.get('reason','continuation_held'),goal,active));continue
                checkpoint=(receipt['token_limit']-used<=receipt['token_limit']*receipt['checkpoint_token_percent']/100
                    or receipt['deadline']-upper<=receipt['checkpoint_seconds'])
                if checkpoint:
                    if not receipt.get('checkpoint'):
                        receipt['checkpoint']=dict(state='queued',message='Stop work and write a restart-safe checkpoint now. The original resource allowance remains in force.')
                        _save(path,receipt)
                    if active and receipt['checkpoint']['state']=='queued':
                        key='checkpoint:'+active[0]
                        delivered=_effect(path,receipt,key,'turn/steer',dict(threadId=receipt['thread_id'],expectedTurnId=active[0],
                            input=[dict(type='text',text=receipt['checkpoint']['message'])]))
                        receipt['checkpoint']['state']='acknowledged' if delivered else 'uncertain'
                    receipt.update(state='checkpoint_requested',reason='checkpoint_reserve')
                else:receipt.update(state='armed',reason=None)
                _save(path,receipt);results.append(receipt)
            except Exception as exc:
                receipt['observation_error']=type(exc).__name__
                results.append(_stop(path,receipt,'observation_unavailable'))
    return results


def watch(root,interval=1):
    if type(interval) not in (int,float) or not .05<=interval<=5:raise ValueError('invalid controller interval')
    directory=_directory(root);generation=uuid4().hex
    descriptor=os.open(directory/'watch.lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    with os.fdopen(descriptor,'a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        running=True
        def finish(signum,frame):
            nonlocal running
            running=False
        prior={sig:signal.signal(sig,finish) for sig in (signal.SIGTERM,signal.SIGINT)}
        heartbeat=dict(generation=generation,pid=os.getpid(),identity=process_identity(os.getpid()),
            boot_id=boot_id_value(),interval=interval)
        try:
            while running:
                _save(directory/'controller.json',dict(heartbeat,active=True,observed_boottime=time.clock_gettime(time.CLOCK_BOOTTIME)))
                poll(root);time.sleep(interval)
        finally:
            for path in directory.glob('*.json'):
                if path.name=='controller.json':continue
                with _lock(directory,path.stem):
                    _private(path);receipt=json.loads(path.read_text());_stop(path,receipt,'controller_stopped')
            _save(directory/'controller.json',dict(heartbeat,active=False,observed_boottime=time.clock_gettime(time.CLOCK_BOOTTIME)))
            for sig,handler in prior.items():signal.signal(sig,handler)
