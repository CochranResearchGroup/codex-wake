"""Program-callable Wake operations using the existing durable intent owners."""
from functools import partial
from pathlib import Path
import os
from .managed_inventory import InventoryError
from .recurring_schedules import ScheduleStore

class WakeControls:
    def __init__(self,root,*,principal,codex_path='codex',endpoint='unix://',authorize=None):
        self.root=Path(root);self.principal=principal;self.codex_path=codex_path;self.endpoint=endpoint;self.authorize=authorize
    def execute(self,operation,args):
        if self.authorize is not None:self.authorize(operation,args)
        if self.principal is None:raise InventoryError('permission_identity_unverified','Wake owner requires a verified principal.')
        store=ScheduleStore(self.root);verb=operation.rsplit('.',1)[-1]
        if operation.startswith('wakes.intents.'):
            if verb not in ('after','at','file'):raise InventoryError('unsupported_operation','Unsupported intent operation.')
            request=dict(thread_id=args['thread_id'],prompt=args['prompt'],session_mode=args['session_mode'],delivery_window_seconds=args['delivery_window_seconds'])
            from .native_intents import retain
            native=store.native_args(request,2000000000,args['idempotency_key'],self.codex_path,self.endpoint)
            native.native_command=verb;native.trigger=args['trigger'];native._permission_principal=self.principal
            return retain(native,self.root)
        if operation not in definitions():raise InventoryError('unsupported_operation','Unsupported Wake operation.')
        if verb=='register':return store.register(args['request'],codex_path=self.codex_path,endpoint=self.endpoint,principal=self.principal)
        if verb=='revise':return store.revise(args['schedule_id'],args['request'],args['expected_revision'],principal=self.principal,codex_path=self.codex_path,endpoint=self.endpoint)
        if verb=='cancel':return store.cancel(args['schedule_id'],args['expected_revision'],principal=self.principal)
        if verb=='show':
            value=store.read(args['schedule_id']);store.authorize(value,self.principal);return store.receipt(value)
        values=[]
        for value in store.records():
            try:store.authorize(value,self.principal)
            except ValueError:continue
            values.append(store.receipt(value))
        return values

def local_invoke(operation,args,root):
    from .session_permissions import Principal
    root=Path(root)
    if root.exists() and root.stat().st_uid!=os.getuid():raise InventoryError('foreign_target','Wake root belongs to another user.')
    return WakeControls(root,principal=Principal('local-operator','operator')).execute(operation,args)

def definitions():
    text={'type':'string','minLength':1};result={}
    for verb in ('register','list','show','revise','cancel'):
        props={};required=[]
        if verb in ('register','revise'):props['request']={'type':'object'};required.append('request')
        if verb in ('show','revise','cancel'):props['schedule_id']=text;required.append('schedule_id')
        if verb in ('revise','cancel'):props['expected_revision']={'type':'integer','minimum':1};required.append('expected_revision')
        operation='wakes.schedules.'+verb
        result[operation]=('wake_'+operation.replace('.','_'),'Control exact durable schedules without changing their timing or permission rules.',dict(type='object',properties=props,required=required,additionalProperties=False),partial(local_invoke,operation),verb in ('list','show'))
    for verb in ('after','at','file'):
        operation='wakes.intents.'+verb
        props=dict(thread_id=text,prompt=text,trigger=text,idempotency_key=text,session_mode={'enum':['session_only','reopen_live','background']},delivery_window_seconds={'type':'integer','minimum':1})
        result[operation]=('wake_'+operation.replace('.','_'),'Retain one explicit-mode native intent; retained readiness is not execution.',dict(type='object',properties=props,required=list(props),additionalProperties=False),partial(local_invoke,operation),False)
    return result
