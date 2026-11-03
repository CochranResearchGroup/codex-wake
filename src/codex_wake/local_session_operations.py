"""Durable prompt/result ownership for automatically discovered local sessions."""
import hashlib
import json
import os
from pathlib import Path
import socket
import struct
import time
from uuid import uuid4

from .controller_runtime import ControllerRuntime, encoded
from .daemon_commands import local_operator
from .managed_inventory import InventoryError
from .native_protocol import native_request
from .local_sessions import resolve
from websockets.exceptions import WebSocketException


class LocalSessionControl:
    def __init__(self,root,*,request=native_request):
        self.root=root
        self.request=request
        self.runtime=ControllerRuntime(root,adapter=self)

    def _request(self,row,method,params):
        def verify(connection,metadata):
            pid,uid,gid=struct.unpack('3i',connection.socket.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))
            target=row['target']
            if uid!=os.getuid() or pid!=target['process']['pid'] or metadata.get('codexHome')!=target['home']:
                raise InventoryError('stale_target','native conversation endpoint identity changed')
        return self.request(row['endpoint'],row['codex_cmd'],method,params,10,verify_connection=verify)

    def _current(self,row):
        return resolve(self.root,'thread:'+row['thread_id'],row['target'],endpoint=row['endpoint'])

    def prompt(self,selector,prompt,key=None,*,endpoint='unix://',expected_target=None):
        if not isinstance(prompt,str) or not 0<len(prompt.encode())<=32768:
            raise InventoryError('invalid_argument','prompt must contain one to32768 UTF8 bytes')
        if key is None:key=uuid4().hex
        if not isinstance(key,str) or not 0<len(key)<=128:
            raise InventoryError('invalid_argument','bounded idempotency key required')
        identifier='local-prompt-'+hashlib.sha256(key.encode()).hexdigest()[:32]
        try:previous=self.runtime._load(identifier)
        except InventoryError as error:
            if error.code!='operation_not_found':raise
            previous=None
        if previous is not None:
            actor=self._actor(identifier);previous=self._owned_record(actor,identifier)
            session=previous['payload']['session']
            if previous['payload']['prompt']!=prompt:
                raise InventoryError('idempotency_conflict','intent key already binds another prompt')
            if expected_target is not None and expected_target!=previous['target']:
                raise InventoryError('stale_target','retry cannot replace the original pinned target')
            address='unix://'+str(Path(endpoint[7:]).resolve()) if isinstance(endpoint,str) and endpoint.startswith('unix:///') else endpoint
            if address not in ('unix://',session['endpoint']):
                raise InventoryError('idempotency_conflict','retry cannot replace the original native endpoint')
            if selector not in (session['thread_id'],'thread:'+session['thread_id']):
                resolve(self.root,selector,previous['target'],endpoint=session['endpoint'])
            return self.runtime.envelope('sessions.prompt',previous)
        row=resolve(self.root,selector,expected_target,endpoint=endpoint)
        row={k:row[k] for k in ('thread_id','target','endpoint','codex_cmd')}
        actor=local_operator(row['target'])
        request=dict(operation_id=identifier,idempotency_key=key,correlation_id=identifier,binding='local-control',target=row['target'])
        def dispatch(operation,payload):
            from .local_session_events import launch
            return {'_pending':True,'handle':launch(self.root,identifier)}
        value=self.runtime.execute(actor,'sessions.prompt',{'session':row,'prompt':prompt,'_request':request},authorize=lambda:actor,dispatch=dispatch)
        record=self.runtime._load(value['result']['operation']['operation_id'])
        if record['phase']=='waiting' and (record.get('result') or {}).get('turn_id'):
            record.update(acceptance='harness_accepted',execution='running')
            self.runtime._save(record)
        return self.runtime.envelope('sessions.prompt',record)

    def _actor(self,operation_id):
        # Reading retained owner metadata is not authority: require the stored UID,
        # account home ownership and local caller identity before disclosure.
        record=self.runtime._load(operation_id)
        target=record['target']
        if target.get('uid')!=os.getuid() or Path(target['home']).stat().st_uid!=os.getuid():raise InventoryError('foreign_target','operation belongs to another local user')
        return local_operator(target)

    def _owned_record(self,actor,identifier):
        record=self.runtime._owned(actor,self.runtime._load(identifier),lambda:actor)
        if record['operation']!='sessions.prompt':
            raise InventoryError('unsupported_operation','original operation belongs to another effect owner')
        return record

    def _retain_observation(self,record,*,cancelling=False):
        # Merge against current custody under the existing journal transaction.
        # A pre-ack read must never erase a later native ack or terminal result.
        with self.runtime.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            current=json.loads(db.execute('SELECT record FROM operations WHERE id=?',(record['operation_id'],)).fetchone()[0])
            current_turn=(current.get('result') or {}).get('turn_id')
            observed_turn=(record.get('result') or {}).get('turn_id')
            if current['phase']!='terminal' and not (current_turn and not observed_turn):
                if current_turn and observed_turn and current_turn!=observed_turn:
                    current.update(phase='uncertain',execution='unknown',reason='conflicting_native_turn_identity')
                else:
                    for key in ('result','answer','phase','execution','delivery','acceptance','reason'):
                        if key in record:current[key]=record[key]
            if cancelling:
                strength={'not_requested':0,'uncertain':1,'requested':2,'confirmed':3}
                if strength.get(record['cancellation'],0)>=strength.get(current.get('cancellation'),0):
                    current['cancellation']=record['cancellation']
            current['_revision']=current.get('_revision',0)+1
            db.execute('UPDATE operations SET record=? WHERE id=?',(encoded(current),record['operation_id']))
        if current['phase']=='terminal' and current.get('answer') is not None:
            self.runtime._event(current,'native_terminal',dict(kind='answer',**current['answer']))
        return current

    def result(self,operation_id,timeout=0):
        if type(timeout) not in (int,float) or not 0<=timeout<=30:
            raise InventoryError('invalid_argument','caller wait timeout must be zero to thirty seconds')
        actor=self._actor(operation_id);deadline=time.monotonic()+timeout
        while True:
            record=self._owned_record(actor,operation_id)
            if record['phase']!='terminal':
                try:self.observe_native_owned(record)
                except (ValueError,OSError,WebSocketException) as error:
                    record.update(phase='uncertain',execution='unknown',reason=getattr(error,'code','native_owner_unavailable'))
                record=self._retain_observation(record)
            self.runtime._owned(actor,record,lambda:actor)
            if record['phase']=='terminal' or time.monotonic()>=deadline:break
            time.sleep(min(.05,max(0,deadline-time.monotonic())))
        return self.runtime.envelope('operations.wait' if timeout else 'operations.result',record,
            **({'wait':dict(status='completed' if record['phase']=='terminal' else 'timeout',ends_work=False)} if timeout else {}))

    def output(self,operation_id,*,mode='final',cursor=0,limit=100,timeout=0):
        from .local_session_events import TurnEvents,MODES
        if mode not in MODES or type(timeout) not in (int,float) or not 0<=timeout<=30:
            raise InventoryError('invalid_argument','output mode and timeout0..30 required')
        actor=self._actor(operation_id)
        self.runtime._owned(actor,self.runtime._load(operation_id),lambda:actor)
        store=TurnEvents(self.root);deadline=time.monotonic()+timeout
        while True:
            record=self.runtime._load(operation_id)
            if store.state(operation_id)['status']=='uncertain' and record.get('result') and record['phase']!='terminal':
                # Read-only terminal reconciliation cannot reconstruct missing live events.
                self.result(operation_id)
                record=self.runtime._load(operation_id)
            page=store.read(operation_id,cursor,limit)
            terminal=record['phase']=='terminal'
            if terminal or (mode in ('stream','transcript') and page['events']) or store.state(operation_id)['status'] in ('uncertain','unavailable') or time.monotonic()>=deadline:break
            time.sleep(min(.02,max(0,deadline-time.monotonic())))
        value=dict(operation_id=operation_id,turn_id=(record.get('result') or {}).get('turn_id'),
            mode=mode,terminal=terminal,execution=record['execution'],phase=record['phase'],reason=record.get('reason'),
            next_cursor=page['next_cursor'],latest_cursor=page['latest_cursor'],retention=page['retention'],wait=dict(status='completed' if terminal else 'timeout',ends_work=False))
        if mode=='transcript':value['events']=page['events']
        elif mode=='stream':value['text']=''.join(event['params'].get('delta','') for event in page['events'] if event['kind']=='item/agentMessage/delta')
        elif mode=='final':
            value['text']=(record.get('answer') or {}).get('text','') if terminal else ''
            value['truncated']=(record.get('answer') or {}).get('truncated',False)
        return value

    def cancel(self,operation_id):
        actor=self._actor(operation_id);record=self._owned_record(actor,operation_id)
        self.runtime.check_authority(actor,record['target'],'control',authorize=lambda:actor)
        if record['phase']=='terminal':return self.runtime.envelope('operations.cancel',record)
        try:record['cancellation']=self.cancel_native_owned(record)
        except (ValueError,OSError,WebSocketException) as error:
            record.update(cancellation='uncertain',phase='uncertain',execution='unknown',reason=getattr(error,'code','native_owner_unavailable'))
        record=self._retain_observation(record,cancelling=True)
        self.runtime._event(record,'cancel',dict(kind='cancellation',status=record['cancellation']))
        self.runtime._owned(actor,record,lambda:actor,capability='control')
        return self.runtime.envelope('operations.cancel',record)

    def observe_native_owned(self,record):
        row=record['payload']['session'];self._current(row)
        value=self._request(row,'thread/read',{'threadId':row['thread_id'],'includeTurns':True})['thread']
        if value.get('id')!=row['thread_id']:raise InventoryError('stale_target','native response belongs to another conversation')
        handle=record.get('result')
        if not isinstance(handle,dict) or not isinstance(handle.get('turn_id'),str):
            from .local_session_events import TurnEvents
            client_id=TurnEvents(self.root).state(record['operation_id']).get('native_client_id')
            if client_id!=record['operation_id']:
                record.update(phase='uncertain',execution='unknown',reason='native_acknowledgement_unavailable')
                return record
            matches=[]
            for turn in value.get('turns',[]):
                users=[item for item in turn.get('items',[]) if item.get('type')=='userMessage' and item.get('clientId')==record['operation_id']]
                if len(users)==1 and isinstance(users[0].get('content'),list) and len(users[0]['content'])==1:
                    content=users[0]['content'][0]
                    if isinstance(content,dict) and content.get('type')=='text' and content.get('text')==record['payload']['prompt']:matches.append(turn)
            if len(matches)!=1 or not isinstance(matches[0].get('id'),str) or not matches[0]['id']:
                record.update(phase='uncertain',execution='unknown',reason='native_acknowledgement_unavailable')
                return record
            handle=dict(kind='native_turn',local_control=True,turn_id=matches[0]['id'],target=record['target'],
                evidence='native_client_message_id',native_client_id=record['operation_id'])
            record.update(result=handle,delivery='submitted',acceptance='harness_accepted')
        turns=[t for t in value.get('turns',[]) if t.get('id')==handle['turn_id']]
        if len(turns)!=1:raise InventoryError('native_turn_unavailable','original submitted turn cannot be observed')
        turn=turns[0];status=turn.get('status')
        if status in ('completed','failed','interrupted'):
            answers=[item['text'] for item in turn.get('items',[]) if item.get('type')=='agentMessage' and item.get('phase') in (None,'final_answer') and isinstance(item.get('text'),str)]
            text=answers[-1] if answers else ''
            encoded=text.encode();record.update(phase='terminal',execution={'completed':'completed','failed':'failed','interrupted':'cancelled'}[status],delivery='retained',acceptance='owner_observed',reason=None,answer={'text':encoded[:32768].decode(errors='replace'),'truncated':len(encoded)>32768,'source':'native_turn','turn_id':handle['turn_id']})
        else:record.update(phase='waiting',execution='running',reason=None)
        return record

    def cancel_native_owned(self,record):
        self.observe_native_owned(record)
        if record['phase']=='terminal':return 'confirmed'
        if not isinstance(record.get('result'),dict) or not record['result'].get('turn_id'):return 'uncertain'
        row=record['payload']['session'];self._current(row)
        self._request(row,'turn/interrupt',{'threadId':row['thread_id'],'turnId':record['result']['turn_id']})
        self.observe_native_owned(record)
        return 'confirmed' if record['phase']=='terminal' else 'requested'
