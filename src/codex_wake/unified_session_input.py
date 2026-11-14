"""Explicit native input policies with durable original-effect custody."""
from pathlib import Path
from functools import partial
import hashlib
import os
from .managed_inventory import InventoryError
from .controller_runtime import ControllerRuntime
from .daemon_commands import local_operator
from .local_sessions import resolve
from .local_session_operations import LocalSessionControl

POLICIES=('reject','queue','steer','interrupt_then_submit')
class SessionInputs:
    def __init__(self,root,*,request=None,authorize=None):
        self.root=Path(root);self.native=LocalSessionControl(root);self.request=request or self.native._request;self.authorize=authorize;self.runtime=ControllerRuntime(root)
    def guard(self,row,action='control'):
        target=row['target']
        if target.get('uid')!=os.getuid() or Path(target['home']).stat().st_uid!=os.getuid():raise InventoryError('foreign_target','Native account is not owned by this user.')
        if self.authorize is not None:self.authorize(target,action)
        return local_operator(target)
    def thread(self,row):
        resolve(self.root,'thread:'+row['thread_id'],row['target'],endpoint=row['endpoint'])
        value=self.request(row,'thread/read',dict(threadId=row['thread_id'],includeTurns=True))['thread']
        if value.get('id')!=row['thread_id']:raise InventoryError('stale_target','Native thread identity changed.')
        return value
    @staticmethod
    def active(thread):return [t for t in thread.get('turns',[]) if t.get('status')=='inProgress']
    def submit(self,selector,prompt,policy,idempotency_key,*,endpoint='unix://',expected_target=None):
        if policy not in POLICIES or not isinstance(prompt,str) or not 0<len(prompt.encode())<=32768 or not isinstance(idempotency_key,str) or not 0<len(idempotency_key)<=128:raise InventoryError('invalid_argument','Explicit bounded input policy, prompt and intent key required.')
        identifier='session-input-'+hashlib.sha256(idempotency_key.encode()).hexdigest()[:32]
        try:old=self.runtime._load(identifier)
        except InventoryError as error:
            if error.code!='operation_not_found':raise
            old=None
        if old is not None:
            row=old['payload']['session'];actor=self.guard(row)
            if old['payload']['prompt']!=prompt or old['payload']['policy']!=policy or selector not in (row['thread_id'],'thread:'+row['thread_id']) or expected_target is not None and expected_target!=row['target']:raise InventoryError('idempotency_conflict','Input key binds the original exact request.')
            self.runtime._owned(actor,old,lambda:self.guard(row));return self.runtime.envelope('environment.conversations.input.submit',old)
        row=resolve(self.root,selector,expected_target,endpoint=endpoint);row={k:row[k] for k in ('thread_id','target','endpoint','codex_cmd')};actor=self.guard(row);thread=self.thread(row);active=self.active(thread)
        if thread.get('status',{}).get('type') not in ('idle','active'):raise InventoryError('session_unavailable','Native session is not qualified idle or active.')
        if policy=='reject' and thread['status']['type']!='idle':raise InventoryError('session_busy','Native session is busy; reject policy sends no input.')
        if policy in ('steer','interrupt_then_submit') and len(active)!=1 and thread['status']['type']!='idle':raise InventoryError('turn_unavailable','Exact active native turn required.')
        payload=dict(session=row,prompt=prompt,policy=policy,active_turn_id=active[0]['id'] if len(active)==1 else None)
        payload['_request']=dict(operation_id=identifier,idempotency_key=idempotency_key,correlation_id=identifier,binding='explicit-session-input',target=row['target'])
        def dispatch(operation,args):
            self.guard(row);fresh=self.thread(row)
            if policy=='queue':
                response=self.request(row,'thread/queue/add',dict(threadId=row['thread_id'],clientUserMessageId=identifier,input=[dict(type='text',text=prompt)]))['queuedSubmission']
                if response.get('clientUserMessageId')!=identifier or response.get('input')!=[dict(type='text',text=prompt)] or not isinstance(response.get('id'),str):raise InventoryError('effect_unverified','Exact native queue acknowledgment required.')
                return dict(_pending=True,handle=dict(kind='native_queue',queue_id=response['id'],client_message_id=identifier,execution='not_observed'))
            if fresh.get('status',{}).get('type')=='idle':
                child=self.native.prompt('thread:'+row['thread_id'],prompt,identifier+'.prompt',endpoint=row['endpoint'],expected_target=row['target'])
                return dict(_pending=True,handle=dict(kind='owned_prompt',operation_id=child['result']['operation']['operation_id']))
            turns=self.active(fresh)
            if len(turns)!=1 or turns[0]['id']!=payload['active_turn_id']:raise InventoryError('stale_target','Active turn changed before input admission.')
            turn=turns[0]['id']
            if policy=='steer':
                self.request(row,'turn/steer',dict(threadId=row['thread_id'],expectedTurnId=turn,input=[dict(type='text',text=prompt)]))
                return dict(_pending=True,handle=dict(kind='native_steer',turn_id=turn,execution='not_observed'))
            self.request(row,'turn/interrupt',dict(threadId=row['thread_id'],turnId=turn))
            return dict(_pending=True,handle=dict(kind='interrupt_then_submit',interrupted_turn_id=turn,submission='waiting_for_confirmed_idle'))
        return self.runtime.execute(actor,'sessions.input',payload,authorize=lambda:self.guard(row),dispatch=dispatch)
    def result(self,identifier):
        record=self.runtime._load(identifier)
        if record.get('operation')!='sessions.input':raise InventoryError('unsupported_operation','Original handle is not an input request.')
        row=record['payload']['session'];actor=self.guard(row,'content');self.runtime._owned(actor,record,lambda:self.guard(row,'content'))
        if record['phase']=='terminal':return self.runtime.envelope('environment.conversations.input.result',record)
        thread=self.thread(row);handle=record.get('result') or {};turn_id=handle.get('turn_id')
        if handle.get('kind')=='interrupt_then_submit' and thread.get('status',{}).get('type')=='idle':
            old=[t for t in thread.get('turns',[]) if t.get('id')==handle['interrupted_turn_id']]
            if len(old)==1 and old[0].get('status') in ('completed','failed','interrupted'):
                self.guard(row)
                child=self.native.prompt('thread:'+row['thread_id'],record['payload']['prompt'],identifier+'.prompt',endpoint=row['endpoint'],expected_target=row['target'])
                handle=dict(kind='owned_prompt',operation_id=child['result']['operation']['operation_id']);record['result']=handle
        if handle.get('kind')=='owned_prompt':
            child=self.native.result(handle['operation_id'])['result']['operation']
            for key in ('phase','execution','delivery','acceptance','reason','answer'):
                if key in child:record[key]=child[key]
        else:
            if handle.get('kind')=='native_queue' or record['phase']=='uncertain':
                matches=[t for t in thread.get('turns',[]) if any(i.get('type')=='userMessage' and i.get('clientId')==identifier for i in t.get('items',[]))]
                if len(matches)==1:turn_id=matches[0]['id'];record['result']=dict(handle,turn_id=turn_id)
            turns=[t for t in thread.get('turns',[]) if t.get('id')==turn_id] if turn_id else []
            if len(turns)==1:
                turn=turns[0];status=turn.get('status')
                if status in ('completed','failed','interrupted'):
                    texts=[i['text'] for i in turn.get('items',[]) if i.get('type')=='agentMessage' and i.get('phase') in (None,'final_answer') and isinstance(i.get('text'),str)]
                    text=texts[-1] if texts else '';record.update(phase='terminal',execution={'completed':'completed','failed':'failed','interrupted':'cancelled'}[status],acceptance='owner_observed',reason=None,answer=dict(text=text[:32768],truncated=len(text)>32768,source='native_turn',turn_id=turn_id))
                else:record.update(phase='waiting',execution='running',acceptance='owner_observed')
        self.runtime._save(record)
        return self.runtime.envelope('environment.conversations.input.result',record)

def definitions():
    text={'type':'string','minLength':1};props=dict(selector=text,prompt=text,policy={'enum':list(POLICIES)},idempotency_key=text,endpoint=text,expected_target={'type':'object'})
    def submit(args,root):return SessionInputs(root).submit(args['selector'],args['prompt'],args['policy'],args['idempotency_key'],**{k:args[k] for k in ('endpoint','expected_target') if k in args})
    def result(args,root):return SessionInputs(root).result(args['operation_id'])
    return {'environment.conversations.input.submit':('wake_environment_conversations_input_submit','Submit one explicitly selected native busy-input policy; no fallback.',dict(type='object',properties=props,required=['selector','prompt','policy','idempotency_key'],additionalProperties=False),submit,False),
        'environment.conversations.input.result':('wake_environment_conversations_input_result','Observe original native input execution without replay.',dict(type='object',properties={'operation_id':text},required=['operation_id'],additionalProperties=False),result,True)}
