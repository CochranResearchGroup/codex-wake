"""Durable prompt/result ownership for automatically discovered local sessions."""
import hashlib
import os
from pathlib import Path
import socket
import struct
import time

from .controller_runtime import ControllerRuntime
from .daemon_commands import local_operator
from .managed_inventory import InventoryError
from .native_protocol import native_request
from .local_sessions import resolve


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

    def prompt(self,selector,prompt,key,*,endpoint='unix://',expected_target=None):
        if not isinstance(prompt,str) or not 0<len(prompt.encode())<=32768:
            raise InventoryError('invalid_argument','prompt must contain one to32768 UTF8 bytes')
        if not isinstance(key,str) or not 0<len(key)<=128:
            raise InventoryError('invalid_argument','bounded idempotency key required')
        row=resolve(self.root,selector,expected_target,endpoint=endpoint)
        row={k:row[k] for k in ('thread_id','target','endpoint','codex_cmd')}
        actor=local_operator(row['target'])
        identifier='local-prompt-'+hashlib.sha256(key.encode()).hexdigest()[:32]
        request=dict(operation_id=identifier,idempotency_key=key,correlation_id=identifier,binding='local-control',target=row['target'])
        def dispatch(operation,payload):
            current=self._current(payload['session'])
            thread=self._request(current,'thread/read',{'threadId':current['thread_id'],'includeTurns':False})['thread']
            if thread['id']!=current['thread_id'] or thread.get('status',{}).get('type') not in ('idle','notLoaded'):
                raise InventoryError('session_busy','target is busy; prompt was not intentionally queued or steered')
            turn=self._request(current,'turn/start',{'threadId':current['thread_id'],'input':[{'type':'text','text':payload['prompt']}]})['turn']
            if not isinstance(turn.get('id'),str):raise InventoryError('uncertain_effect','native turn acknowledgement missing')
            return {'_pending':True,'handle':{'kind':'native_turn','local_control':True,'turn_id':turn['id'],'target':current['target']}}
        return self.runtime.execute(actor,'sessions.prompt',{'session':row,'prompt':prompt,'_request':request},authorize=lambda:actor,dispatch=dispatch)

    def _actor(self,operation_id):
        # Reading retained owner metadata is not authority: require the stored UID,
        # account home ownership and local caller identity before disclosure.
        record=self.runtime._load(operation_id)
        target=record['target']
        if target.get('uid')!=os.getuid() or Path(target['home']).stat().st_uid!=os.getuid():raise InventoryError('foreign_target','operation belongs to another local user')
        return local_operator(target)

    def result(self,operation_id,timeout=0):
        actor=self._actor(operation_id)
        return self.runtime.operation(actor,'operations.wait' if timeout else 'operations.result',{'operation_id':operation_id,**({'timeout':timeout} if timeout else {})},authorize=lambda:actor,expected_operation='sessions.prompt')

    def cancel(self,operation_id):
        actor=self._actor(operation_id)
        return self.runtime.operation(actor,'operations.cancel',{'operation_id':operation_id},authorize=lambda:actor,expected_operation='sessions.prompt')

    def observe_native_owned(self,record):
        row=record['payload']['session'];self._current(row)
        value=self._request(row,'thread/read',{'threadId':row['thread_id'],'includeTurns':True})['thread']
        if value.get('id')!=row['thread_id']:raise InventoryError('stale_target','native response belongs to another conversation')
        handle=record['result'];turns=[t for t in value.get('turns',[]) if t.get('id')==handle['turn_id']]
        if len(turns)!=1:raise InventoryError('native_turn_unavailable','original submitted turn cannot be observed')
        turn=turns[0];status=turn.get('status')
        if status in ('completed','failed','interrupted'):
            text='\n'.join(i['text'] for i in turn.get('items',[]) if i.get('type')=='agentMessage' and isinstance(i.get('text'),str))
            encoded=text.encode();record.update(phase='terminal',execution={'completed':'completed','failed':'failed','interrupted':'cancelled'}[status],delivery='retained',acceptance='owner_observed',reason=None,answer={'text':encoded[:32768].decode(errors='replace'),'truncated':len(encoded)>32768,'source':'native_turn','turn_id':handle['turn_id']})
        else:record.update(phase='waiting',execution='running',reason=None)
        return record

    def cancel_native_owned(self,record):
        self.observe_native_owned(record)
        if record['phase']=='terminal':return 'confirmed'
        row=record['payload']['session'];self._current(row)
        self._request(row,'turn/interrupt',{'threadId':row['thread_id'],'turnId':record['result']['turn_id']})
        self.observe_native_owned(record)
        return 'confirmed' if record['phase']=='terminal' else 'requested'
