"""Explicit, caller-owned bounded recovery policies over existing effect owners.

Scheduled ticks are authenticated operations; configuration never installs a
background service or grants fresh resources. Read-only probes are separated
from action/notice admission. Deactivation fences later steps before observing
original in-flight effects and never clears counters or renews authority.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sqlite3
import time

from .controller_auth import AuthError
from .controller_health import ControllerHealth, _TARGET_FIELDS
from .controller_notices import ControllerNotices
from .controller_runtime import ControllerRuntime, bounded_id, encoded, identity
from .managed_inventory import InventoryError

_FIELDS=(_TARGET_FIELDS-{'process'})|{'process_pid','process_start_ticks','process_boot_id'}


def raw_target(target):
    result={k:v for k,v in target.items() if not k.startswith('process_')}
    try:pid=int(target['process_pid'])
    except (ValueError,TypeError):raise InventoryError('invalid_argument','positive decimal process PID required') from None
    if str(pid)!=target['process_pid'] or pid<=0:raise InventoryError('invalid_argument','positive decimal process PID required')
    result['process']=dict(pid=pid,start_ticks=target['process_start_ticks'],boot_id=target['process_boot_id'])
    return result


class ControllerRecovery:
    def __init__(self,root,*,now=None,probe=None,notice=None,action=None,request=None,elapsed=None,boot=None):
        from .process import boot_id_value
        self.root,self.now=Path(root),now or time.time
        self.elapsed=elapsed or (now if now is not None else lambda:time.clock_gettime(time.CLOCK_BOOTTIME))
        self.boot=boot or boot_id_value
        self.runtime=ControllerRuntime(root,now=self.now)
        self.probe=probe or (lambda target,timeout:ControllerHealth(root).execute('health.observe',dict(expected_target=target,timeout=timeout)))
        self.notice=notice or self._native_notice
        self.action=action or self._action
        self.request=request
        directory=self.root/'controller-recovery';directory.mkdir(mode=0o700,parents=True,exist_ok=True)
        self.path=directory/'policies.sqlite'
        fd=os.open(self.path,os.O_CREAT|os.O_RDWR,0o600);os.close(fd);os.chmod(self.path,0o600)
        with self._db() as db:
            db.execute('CREATE TABLE IF NOT EXISTS policies (id TEXT PRIMARY KEY, record TEXT)')

    def _db(self):return sqlite3.connect(self.path,timeout=5)

    def _load(self,policy_id):
        bounded_id(policy_id)
        with self._db() as db:row=db.execute('SELECT record FROM policies WHERE id=?',(policy_id,)).fetchone()
        if not row:raise InventoryError('policy_not_found','recovery policy is not retained')
        return json.loads(row[0])

    def _edit(self,policy_id,change):
        with self._db() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT record FROM policies WHERE id=?',(policy_id,)).fetchone()
            if not row:raise InventoryError('policy_not_found','recovery policy is not retained')
            record=json.loads(row[0]);change(record)
            if len(encoded(record).encode())>262144:raise InventoryError('capacity','policy retained state bound reached')
            db.execute('UPDATE policies SET record=? WHERE id=?',(encoded(record),policy_id))
        return record

    def _authorize(self,actor,target,capability,authorize):
        if not isinstance(target,dict) or set(target)!=_FIELDS or any(not isinstance(v,str) or not v or len(v)>4096 for v in target.values()):
            raise InventoryError('invalid_argument','complete flat native recovery target required')
        raw_target(target)
        if not any(_FIELDS<=scope.keys() and all(target.get(k)==v for k,v in scope.items()) for scope in actor.targets):
            raise AuthError('insufficient_scope')
        return self.runtime.check_authority(actor,target,capability,authorize=authorize)

    def _owned(self,actor,policy_id,target,capability,authorize):
        self._authorize(actor,target,capability,authorize)
        record=self._load(policy_id)
        if record['target']!=target:raise InventoryError('stale_target','policy belongs to another exact native generation')
        if record['principal']!=identity(actor):raise AuthError('insufficient_scope')
        return record

    @staticmethod
    def _public(record):return {k:v for k,v in record.items() if k!='principal'}

    @staticmethod
    def _definition(value):
        fields={'interval_seconds','probe_timeout','unknown_threshold','cooldown_seconds','max_attempts','evidence','actions'}
        if not isinstance(value,dict) or set(value)!=fields:raise InventoryError('invalid_argument','explicit bounded recovery policy declaration required')
        for key,low,high in (('interval_seconds',1,86400),('probe_timeout',.05,5),('cooldown_seconds',1,86400)):
            if type(value[key]) not in (int,float) or not low<=value[key]<=high:raise InventoryError('invalid_argument','invalid bounded policy timing')
        for key,low,high in (('unknown_threshold',2,32),('max_attempts',1,32)):
            if type(value[key]) is not int or not low<=value[key]<=high:raise InventoryError('invalid_argument','invalid bounded recovery count')
        if value['evidence']!='suspected_unresponsive':raise InventoryError('unsupported_operation','only repeated exact-loop unknown escalation is supported')
        actions=value['actions']
        if not isinstance(actions,list) or not 1<=len(actions)<=8:raise InventoryError('invalid_argument','one to eight explicit recovery actions required')
        for action in actions:
            if not isinstance(action,dict):raise InventoryError('invalid_argument','typed recovery action required')
            kind=action.get('kind')
            required={'notify_operator':{'kind'},'cancel_owned_operation':{'kind','operation_id'},'thread_mcp_refresh':{'kind','profile'}}.get(kind)
            if required is None:raise InventoryError('unsupported_operation','recovery action unavailable; no restart or fallback is implied')
            if set(action)!=required:raise InventoryError('invalid_argument','unsupported recovery action fields')
            if kind=='cancel_owned_operation':bounded_id(action['operation_id'])
            if kind=='thread_mcp_refresh':bounded_id(action['profile'])
        return json.loads(encoded(value))

    def _clock(self,record):
        clock=record.get('clock')
        if not isinstance(clock,dict) or clock.get('boot_id')!=self.boot():raise InventoryError('time_uncertain','boot continuity lost; original policy clock retained')
        elapsed=self.elapsed()
        if type(elapsed) not in (int,float) or not elapsed>=clock['last_elapsed']:raise InventoryError('time_uncertain','elapsed continuity lost; original policy clock retained')
        return elapsed

    def _configure(self,actor,args):
        declaration=self._definition(args.get('policy'));policy_id=args['policy_id']
        record=dict(schema_version=1,policy_id=policy_id,principal=identity(actor),target=args['expected_target'],
            definition=declaration,definition_sha256=hashlib.sha256(encoded(declaration).encode()).hexdigest(),
            mode='observe',generation=1,created_at=self.now(),checks=0,unknown_streak=0,attempts=0,
            health_status='unobserved',last_observation=None,next_due=self.now(),last_action_at=None,
            action_status='not_started',in_flight=None,notifications={},history=[],
            clock=dict(boot_id=self.boot(),last_elapsed=self.elapsed(),next_due_elapsed=self.elapsed(),last_observation_elapsed=None,last_action_elapsed=None))
        with self._db() as db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute('SELECT 1 FROM policies WHERE id=?',(policy_id,)).fetchone():raise InventoryError('idempotency_conflict','policy ID is immutable; choose an explicit new policy ID')
            if db.execute('SELECT COUNT(*) FROM policies').fetchone()[0]>=256:raise InventoryError('capacity','recovery policy capacity reached')
            db.execute('INSERT INTO policies VALUES(?,?)',(policy_id,encoded(record)))
        return self._outcome(record,'configured','observation is default; automatic recovery is not enabled')

    @staticmethod
    def _outcome(record,outcome,reason):
        return dict(policy_id=record['policy_id'],mode=record['mode'],outcome=outcome,reason=reason,
            checks=record['checks'],attempts=record['attempts'],health_status=record['health_status'])

    def _switch(self,actor,args,authorize,enabled):
        self._owned(actor,args['policy_id'],args['expected_target'],'recovery',authorize)
        def change(record):
            record['generation']+=1
            record['mode']='activation_pending' if enabled else 'off'
            record['activation_source_id']=args['_request']['operation_id'] if enabled else None
            if not enabled and record['in_flight'] is not None:record['action_status']='deactivated_in_flight'
        record=self._edit(args['policy_id'],change)
        return self._outcome(record,'activation_requested' if enabled else 'disabled',
            'operator explicitly enabled scoped recovery' if enabled else 'operator requested immediate scoped deactivation')

    def _check(self,actor,args,authorize,*,due_only):
        record=self._owned(actor,args['policy_id'],args['expected_target'],'observe',authorize)
        now=self.now();definition=record['definition']
        elapsed=self._clock(record)
        if due_only and elapsed<record['clock']['next_due_elapsed']:return self._outcome(record,'not_due','scheduled check deadline has not arrived')
        observed=self.probe(raw_target(record['target']),definition['probe_timeout'])
        self._authorize(actor,record['target'],'observe',authorize)
        observation=observed.get('observation',{}) if isinstance(observed,dict) else {}
        if observed.get('target')!=raw_target(record['target']) or type(observation.get('observed_at')) not in (int,float) or not min(now,self.now())<=observation['observed_at']<=max(now,self.now())+definition['probe_timeout']:
            observation=dict(status='unknown',responsive=False,evidence='none',observed_at=self.now(),reason='invalid_or_stale_probe')
        if observation.get('status')=='responsive' and (observation.get('responsive') is not True or observation.get('evidence')!='tui_main_loop_ack'):
            observation=dict(status='unknown',responsive=False,evidence='none',observed_at=self.now(),reason='not_exact_tui_loop_evidence')
        def change(current):
            finished=self._clock(current)
            current['checks']+=1;current['next_due']=self.now()+definition['interval_seconds'];current['last_observation']=observation
            current['clock'].update(last_elapsed=finished,last_observation_elapsed=finished,next_due_elapsed=finished+definition['interval_seconds'])
            current['unknown_streak']=0 if observation.get('status')=='responsive' else current['unknown_streak']+1
            current['health_status']='responsive' if observation.get('status')=='responsive' else ('suspected_unresponsive' if current['unknown_streak']>=definition['unknown_threshold'] else 'unknown')
        record=self._edit(record['policy_id'],change)
        return self._outcome(record,'observed','read-only exact-loop observation; no recovery authority inferred')

    def _guard(self,actor,policy_id,target,generation,authorize):
        current=self._owned(actor,policy_id,target,'recovery',authorize)
        if current['mode']!='automatic' or current['generation']!=generation:raise InventoryError('policy_deactivated','policy was deactivated or superseded before the next automatic step')
        return actor

    def _apply(self,actor,args,authorize):
        record=self._owned(actor,args['policy_id'],args['expected_target'],'recovery',authorize)
        now=self.now();definition=record['definition'];elapsed=self._clock(record)
        if record['mode']!='automatic':return self._outcome(record,'held','scoped automatic recovery is inactive')
        if record['in_flight'] is not None:return self._outcome(record,'uncertain','original in-flight effect must be reconciled before any further action')
        if record['health_status']!='suspected_unresponsive':return self._outcome(record,'held','required repeated unknown evidence is absent')
        observation=record['last_observation']
        if record['clock']['last_observation_elapsed'] is None or not 0<=elapsed-record['clock']['last_observation_elapsed']<=definition['interval_seconds']:return self._outcome(record,'held','health evidence is stale')
        if record['attempts']>=definition['max_attempts']:
            self._edit(record['policy_id'],lambda value:value.update(action_status='exhausted'))
            return self._outcome(record,'attempt_ceiling','cumulative recovery attempt ceiling reached; escalation stopped')
        if record['clock']['last_action_elapsed'] is not None and elapsed-record['clock']['last_action_elapsed']<definition['cooldown_seconds']:
            return self._outcome(record,'cooldown','recovery cooldown has not elapsed')
        generation=record['generation'];operation_id=args['_request']['operation_id']
        def reserve(current):
            if current['mode']!='automatic' or current['generation']!=generation or current['in_flight'] is not None or current['health_status']!='suspected_unresponsive':raise InventoryError('policy_deactivated','policy changed before effect admission')
            if current['attempts']>=definition['max_attempts']:raise InventoryError('attempt_ceiling','cumulative attempt ceiling reached')
            reserved_elapsed=self._clock(current)
            if current['clock']['last_observation_elapsed'] is None or not 0<=reserved_elapsed-current['clock']['last_observation_elapsed']<=definition['interval_seconds']:raise InventoryError('stale_evidence','exact-loop evidence changed before admission')
            if current['clock']['last_action_elapsed'] is not None and reserved_elapsed-current['clock']['last_action_elapsed']<definition['cooldown_seconds']:raise InventoryError('cooldown','policy cooldown has not elapsed')
            current['attempts']+=1;current['last_action_at']=now;current['action_status']='executing'
            current['clock'].update(last_elapsed=reserved_elapsed,last_action_elapsed=reserved_elapsed)
            current['in_flight']=dict(operation_id=operation_id,generation=generation,step=0,phase='admitted',actions=[])
        self._edit(record['policy_id'],reserve)
        guard=lambda:self._guard(actor,record['policy_id'],record['target'],generation,authorize)
        for index,action in enumerate(definition['actions']):
            try:
                guard()
                def claim(current):
                    current['in_flight'].update(step=index,phase='dispatching')
                self._edit(record['policy_id'],claim)
                result=self.action(actor,record,action,operation_id,index,guard)
                guard()
            except Exception as error:
                error_code=getattr(error,'code','effect_uncertain')
                def uncertain(current):
                    if current['in_flight'] is not None:
                        current['action_status']='uncertain';current['in_flight']['phase']='uncertain'
                        current['in_flight']['reason']=error_code
                self._edit(record['policy_id'],uncertain)
                return self._outcome(self._load(record['policy_id']),'uncertain','action outcome uncertain or policy deactivated; never replay automatically')
            def finish_step(current):
                current['in_flight']['actions'].append(result);current['in_flight']['phase']='observed'
            self._edit(record['policy_id'],finish_step)
            if result.get('status') not in ('completed','confirmed'):
                self._edit(record['policy_id'],lambda value:value.update(action_status='uncertain'))
                return self._outcome(self._load(record['policy_id']),'uncertain','original action remains pending or unsupported; escalation held')
        def finish(current):
            current['history'].append(current['in_flight']);current['in_flight']=None;current['action_status']='completed'
        record=self._edit(record['policy_id'],finish)
        return self._outcome(record,'completed','explicit scoped policy action sequence completed')

    def _native_notice(self,actor,source_id,target,guard):
        key='recovery-notice-'+hashlib.sha256(source_id.encode()).hexdigest()
        meta=dict(operation_id=key,idempotency_key=key,correlation_id=source_id,binding='recovery-policy',target=target)
        return ControllerNotices(self.root).execute(actor,'notices.publish',dict(expected_target=target,source_operation_id=source_id,_request=meta),authorize=guard)

    def _publish(self,actor,args,source_id,authorize):
        policy_id,target=args['policy_id'],args['expected_target']
        record=self._owned(actor,policy_id,target,'recovery',authorize)
        if source_id in record['notifications']:return record['notifications'][source_id]
        generation=record['generation']
        pending=dict(status='uncertain',source_operation_id=source_id,operation_id='recovery-notice-'+hashlib.sha256(source_id.encode()).hexdigest())
        self._edit(policy_id,lambda value:value['notifications'].update({source_id:pending}))
        def guard():return self._authorize(actor,target,'recovery',authorize)
        try:
            value=self.notice(actor,source_id,target,guard)
            notice=value.get('result',{}).get('operation',value)
            delivery=notice.get('result',notice).get('delivery',{})
            result=dict(pending,status=delivery.get('status','uncertain'),operation_id=notice.get('operation_id',pending['operation_id']))
        except Exception as error:result=dict(pending,reason=getattr(error,'code','notice_uncertain'))
        def saved(current):
            current['notifications'][source_id]=result
            if current['mode']=='activation_pending' and current['generation']==generation and current.get('activation_source_id')==source_id and result['status']=='recorded':current['mode']='automatic'
        self._edit(policy_id,saved)
        return result

    def _action(self,actor,record,action,operation_id,index,guard):
        if action['kind']=='notify_operator':return dict(kind='notify_operator',status='completed',effect='durable_controller_notice_after_action_result')
        if action['kind']=='cancel_owned_operation':
            guard()
            original=self.runtime.operation(actor,'operations.result',dict(operation_id=action['operation_id']),authorize=guard)['result']['operation']
            if original['target']!=record['target']:raise InventoryError('stale_target','owned cancellation target differs from exact policy target')
            result=self.runtime.operation(actor,'operations.cancel',dict(operation_id=action['operation_id']),authorize=guard)['result']['operation']
            return dict(kind=action['kind'],operation_id=action['operation_id'],status='confirmed' if result['cancellation']=='confirmed' or result['phase']=='terminal' else 'uncertain')
        return self._refresh(actor,record,action,operation_id,index,guard)

    def _refresh(self,actor,record,action,operation_id,index,guard,*,reconcile=False):
        from .shared_refresh import _validate_profile
        from .scoped_refresh import poll_one
        from .native_protocol import native_request
        from .controller_health import _image_hash
        import socket,struct
        registry=self.root/'controller-recovery.json'
        if registry.is_symlink() or not registry.is_file() or registry.stat().st_uid!=os.geteuid() or registry.stat().st_mode&0o077 or registry.stat().st_size>1048576:
            raise InventoryError('configuration_unavailable','private host recovery refresh profiles required')
        config=json.loads(registry.read_text())
        if config.get('version')!=1 or not isinstance(config.get('profiles'),dict) or len(config['profiles'])>256:raise InventoryError('configuration_unavailable','bounded recovery refresh registry required')
        selected=config['profiles'].get(action['profile'])
        if not isinstance(selected,dict) or selected.get('target')!=record['target']:raise InventoryError('stale_target','refresh host profile differs from exact policy target')
        profile=selected.get('refresh')
        _validate_profile(profile)
        if profile['refresh_mode']!='thread_mcp_idle' or not profile['resources']:raise InventoryError('unsupported_operation','only exact thread MCP refresh with resource proof is supported')
        binding=ControllerNotices(self.root)._binding(record['target'])
        if profile['app_server']!=binding['endpoint']:raise InventoryError('stale_target','refresh endpoint differs from exact private binding')
        directory=self.root/'controller-recovery'/'refresh';directory.mkdir(mode=0o700,exist_ok=True)
        key=hashlib.sha256(encoded([operation_id,index]).encode()).hexdigest()
        path=directory/(key+'.json')
        if path.exists():
            if path.is_symlink() or path.stat().st_uid!=os.geteuid() or path.stat().st_mode&0o077:raise InventoryError('configuration_unavailable','private original refresh receipt required')
            receipt=json.loads(path.read_text())
            if receipt['profile']!=profile or receipt['thread_id']!=record['target']['conversation_id']:raise InventoryError('stale_target','original refresh binding changed')
        else:
            if reconcile:return dict(kind='thread_mcp_refresh',status='uncertain',reason='original refresh receipt missing')
            receipt=dict(thread_id=record['target']['conversation_id'],profile=profile,resources=sorted(profile['resources']),state='queued')
        if reconcile and receipt['state']=='queued':
            return dict(kind='thread_mcp_refresh',status='not_submitted',reason='original effect was never admitted')
        if receipt['state']=='completed':return dict(kind='thread_mcp_refresh',status='completed',receipt_id=key,goal_continuity=True)
        if receipt['state']=='blocked':return dict(kind='thread_mcp_refresh',status='uncertain',receipt_id=key,reason=receipt.get('reason'))
        def request(method,params):
            guard()
            ControllerNotices(self.root)._binding(record['target'])
            if self.request is not None:
                result=self.request(profile['app_server'],profile['codex_path'],method,params,profile['timeout'])
            else:
                def verify(connection,metadata):
                    pid,uid,unused=struct.unpack('3i',connection.socket.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))
                    if uid!=os.geteuid() or metadata.get('codexHome')!=record['target']['home'] or _image_hash(pid)!=record['target']['build_sha256']:
                        raise InventoryError('stale_target','native refresh endpoint account/build changed')
                result=native_request(profile['app_server'],profile['codex_path'],method,params,profile['timeout'],verify_connection=verify)
            guard()
            if method=='thread/read' and result.get('thread',{}).get('modelProvider')!=record['target']['provider']:
                raise InventoryError('stale_target','native refresh provider differs from policy target')
            return result
        try:
            poll_one(path,receipt,request=request,guard=guard)
        finally:
            from .goal_supervision import _save
            _save(path,receipt)
        return dict(kind='thread_mcp_refresh',status='completed' if receipt['state']=='completed' else 'uncertain',
            receipt_id=key,native_scope='thread_mcp_connections',goal_continuity=receipt.get('goal_continuity_verified',False),reason=receipt.get('reason'))

    def execute(self,actor,operation,args,*,authorize):
        allowed={'recovery.configure':{'policy_id','expected_target','policy','_request'},
            **{'recovery.'+verb:{'policy_id','expected_target','_request'} for verb in ('enable','disable','check','tick','apply')},
            'recovery.show':{'policy_id','expected_target'},'recovery.list':{'expected_target'},
            'recovery.reconcile':{'policy_id','expected_target'}}
        if operation not in allowed or not isinstance(args,dict) or set(args)-allowed[operation]:raise InventoryError('invalid_argument','unsupported recovery operation/arguments')
        target=args.get('expected_target');capability='observe' if operation in ('recovery.list','recovery.show','recovery.check') else 'recovery'
        self._authorize(actor,target,capability,authorize)
        if operation=='recovery.list':
            with self._db() as db:records=[json.loads(row[0]) for row in db.execute('SELECT record FROM policies')]
            return dict(schema_version=1,operation=operation,status='completed',result=dict(policies=[self._public(row) for row in records if row['target']==target and row['principal']==identity(actor)]))
        bounded_id(args.get('policy_id'))
        if operation=='recovery.configure':self._definition(args.get('policy'))
        if operation=='recovery.show':
            return dict(schema_version=1,operation=operation,status='completed',result=dict(policy=self._public(self._owned(actor,args['policy_id'],target,'observe',authorize))))
        if operation=='recovery.reconcile':return self._reconcile(actor,args,authorize)
        def dispatch(unused,payload):
            self._authorize(actor,target,capability,authorize)
            if operation=='recovery.configure':return self._configure(actor,args)
            if operation in ('recovery.enable','recovery.disable'):return self._switch(actor,args,authorize,operation=='recovery.enable')
            if operation=='recovery.apply':return self._apply(actor,args,authorize)
            checked=self._check(actor,args,authorize,due_only=operation=='recovery.tick')
            if operation=='recovery.check' or checked['outcome']=='not_due':return checked
            record=self._load(args['policy_id'])
            if record['mode']!='automatic':return checked
            identifier='recovery-action-'+hashlib.sha256(args['_request']['operation_id'].encode()).hexdigest()
            meta=dict(args['_request'],operation_id=identifier,idempotency_key=identifier)
            child=self.execute(actor,'recovery.apply',dict(policy_id=args['policy_id'],expected_target=target,_request=meta),authorize=authorize)
            return child['result']['operation']['result'] or self._outcome(record,'uncertain','original action result unavailable')
        result=self.runtime.execute(actor,operation,args,authorize=authorize,dispatch=dispatch,required_capability=capability)
        source=result['result']['operation']
        if operation in ('recovery.enable','recovery.disable','recovery.apply') and source['phase']=='terminal' and source['execution']=='completed':
            value=source['result']
            if operation!='recovery.apply' or value['outcome'] in ('completed','uncertain','attempt_ceiling'):
                result['result']['notification']=self._publish(actor,args,source['operation_id'],authorize)
            if operation=='recovery.disable':
                result['result']['reconciliation']=self._reconcile(actor,args,authorize)['result']
        self._authorize(actor,target,capability,authorize)
        return result

    def _reconcile(self,actor,args,authorize):
        record=self._owned(actor,args['policy_id'],args['expected_target'],'recovery',authorize)
        def guard():return self._authorize(actor,record['target'],'recovery',authorize)
        pending=record['in_flight']
        if pending is not None:
            action=record['definition']['actions'][pending['step']]
            result=None
            if action['kind']=='notify_operator':
                result=dict(kind='notify_operator',status='not_submitted',reason='notice is separately journaled after retained action result')
            elif action['kind']=='cancel_owned_operation':
                original=self.runtime.operation(actor,'operations.result',dict(operation_id=action['operation_id']),authorize=guard)['result']['operation']
                if original['target']!=record['target']:raise InventoryError('stale_target','original cancellation belongs to another exact target')
                if original['phase']=='terminal' or original['cancellation']=='confirmed':result=dict(kind=action['kind'],status='confirmed',operation_id=action['operation_id'])
            else:
                result=self._refresh(actor,record,action,pending['operation_id'],pending['step'],guard,reconcile=True)
                if result.get('status') not in ('completed','confirmed','not_submitted'):result=None
            if result is not None:
                def finish(current):
                    if current['in_flight']!=pending:return
                    current['in_flight'].update(reconciled=result,remaining_steps='not_submitted')
                    current['history'].append(current['in_flight']);current['in_flight']=None
                    current['action_status']='reconciled_no_replay'
                record=self._edit(record['policy_id'],finish)
        # Unknown notice delivery is observed only by original ID, never appended again.
        for source_id,notice in list(record['notifications'].items())[-16:]:
            if notice['status']!='uncertain':continue
            try:
                envelope=ControllerNotices(self.root).execute(actor,'notices.reconcile',dict(expected_target=record['target'],operation_id=notice['operation_id']),authorize=guard)
                value=envelope['result']['operation'];delivery=(value.get('result') or {}).get('delivery',{})
                if delivery.get('status')=='recorded':
                    def saved(current):
                        current['notifications'][source_id]=dict(notice,status='recorded')
                        if current['mode']=='activation_pending' and current.get('activation_source_id')==source_id:current['mode']='automatic'
                    record=self._edit(record['policy_id'],saved)
            except (ValueError,OSError,KeyError):pass
        guard()
        return dict(schema_version=1,operation='recovery.reconcile',status='completed',result=dict(policy=self._public(record),effects='original_only',replayed=False))
