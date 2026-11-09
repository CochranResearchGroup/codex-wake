"""Journaled explicit session deletion, retaining failed/uncertain definitions."""
import os
import re
import time
import uuid

from .managed_inventory import InventoryError
from .shortcut_store import locked, read, write


class TerminalSessionDelete:
    def __init__(self,sessions):
        self.sessions=sessions;self.tabs=sessions.tabs
        self.directory=sessions.root/'terminal-session-delete'

    def _save(self,plan):
        write(self.directory/(plan['plan_id']+'.json'),plan)
        fd=os.open(self.directory,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(fd)
        finally:os.close(fd)

    def _read(self,key):
        if not isinstance(key,str) or not re.fullmatch(r'delete_[a-f0-9]{32}',key):
            raise InventoryError('invalid_argument','A deletion plan ID is required.')
        try:return read(self.directory/(key+'.json'))
        except FileNotFoundError:raise InventoryError('target_not_found','Deletion plan not found.')

    def execute(self,args):
        if not isinstance(args,dict) or set(args)-{'session','server','destination','terminate','plan_id','expected_target','_request'}:
            raise InventoryError('invalid_argument','Unsupported deletion arguments.')
        if type(args.get('terminate',False)) is not bool or args.get('destination') and args.get('terminate'):
            raise InventoryError('invalid_argument','Choose exactly one drain destination or explicit terminate.')
        # Never enter relocation or routing while holding the registry lock.
        with locked(self.directory):
            if args.get('expected_target') is not None and args['expected_target']!=self.sessions.target():
                raise InventoryError('stale_target','Session registry changed; inspect again.')
            if args.get('plan_id'):
                plan=self._read(args['plan_id'])
                if args.get('session') not in (None,plan['source']['id'],plan['source']['name']):
                    raise InventoryError('invalid_argument','Deletion plan belongs to another session.')
                return self._continue(plan)
            with locked(self.sessions.directory):
                state=self.sessions.state()
                saved=state['sessions'].get(args.get('session'),{})
                source=None
                if not saved.get('deletion_plan'):
                    source=self.sessions.resolve(args.get('session'),server=args.get('server'),state=state)
                    saved=state['sessions'].get(source['id'],{})
                if saved.get('deletion_plan'):
                    plan=self._read(saved['deletion_plan'])
                else:
                    if source['state']=='unavailable':raise InventoryError('session_not_empty','Session presence is unknown; reconcile before deleting.')
                    if source['tab_count'] and not (args.get('destination') or args.get('terminate')):
                        raise InventoryError('session_not_empty','Choose explicit drain or terminate for a populated session.')
                    record={k:v for k,v in source.items() if k not in ('workspace','snapshot','state','tab_count','managed')}
                    if source.get('snapshot'):record['native_session_id']=source['snapshot']['session_id']
                    plan=dict(version=1,plan_id='delete_'+uuid.uuid4().hex,source=record,mode='drain' if args.get('destination') else 'terminate',destination=args.get('destination'),status='prepared',outcomes=[],created_at=time.time())
                    # Adopt before the last native tab can vanish.
                    record['deletion_plan']=plan['plan_id'];state['sessions'][source['id']]=record
                    self._save(plan);self.sessions.save(state)
            return self._continue(plan)

    def _continue(self,plan):
        try:return self._apply(plan)
        except InventoryError as error:
            # Only prepared plans have issued no native intent. Retain rejection
            # history while permitting a new explicit choice after preflight fails.
            if plan['status']=='prepared':
                plan.update(status='rejected',reason=error.code);self._save(plan)
                with locked(self.sessions.directory):
                    state=self.sessions.state();record=state['sessions'].get(plan['source']['id'],{})
                    if record.get('deletion_plan')==plan['plan_id']:
                        record.pop('deletion_plan');self.sessions.save(state)
            raise

    def _resources(self):
        return self.tabs.execute('tabs.list',{})['resources']

    def _birth(self,resource):
        from .terminal_relocation import TerminalRelocation
        return TerminalRelocation._birth(resource)

    def _apply(self,plan):
        tombstone=self.sessions.state()['sessions'].get(plan['source']['id'],{})
        if tombstone.get('deleted'):
            plan.update(status='deleted',session=tombstone);self._save(plan)
        if plan['status']=='deleted':return self._cleanup(plan)
        if plan['status']=='rejected':return plan
        if plan['mode']=='drain':return self._drain(plan)
        if plan['status']=='prepared':
            source=self.sessions.resolve(plan['source']['id'])
            effects=[]
            for resource in self._resources():
                if resource['target']['workspace']!=source['workspace']:continue
                window=resource['window']
                birth_field='windows_creation_filetime' if source['backend']=='psmux' else 'process_generation'
                if window.get('linked') or not window['panes'] or any(not p.get(birth_field) for p in window['panes']):
                    raise InventoryError('stale_target','Unlinked whole tabs with exact process births are required.')
                effects.append(dict(birth=self._birth(resource),status='pending'))
            if len(effects)!=source['tab_count']:raise InventoryError('stale_target','Session tab observation is incomplete.')
            snap=source.get('snapshot')
            if snap and source['backend'] in ('tmux','byobu'):
                from .process import process_identity
                plan['server_birth']=dict(pid=int(snap['server']),process=process_identity(int(snap['server'])))
                if not plan['server_birth']['process']:raise InventoryError('stale_target','Exact server birth required.')
            plan['outcomes']=effects;plan['status']='applying';self._save(plan)
        for effect in plan['outcomes']:
            if effect['status'] in ('terminating','uncertain'):
                effect['status']='terminated' if self._absent(plan,effect) else 'uncertain'
                self._save(plan)
            if effect['status']!='pending':continue
            resource,current=self._locate(plan,effect)
            if resource is None:
                effect.update(status='held',reason='placement_or_identity_changed');self._save(plan);continue
            effect['status']='terminating';self._save(plan)
            try:
                result=self.tabs.execute('tabs.close',dict(workspace=current['workspace'],window=resource['window']['window_id'],expected_target=resource['target'],force=True))
                effect['receipt_id']=result.get('receipt_id')
                effect['status']='terminated' if result['status']=='applied' else 'uncertain'
            except Exception as error:
                effect.update(status='uncertain',reason=getattr(error,'code','native_reply_unavailable'))
            self._save(plan)
            if effect['status']=='uncertain' and self._absent(plan,effect):effect['status']='terminated';self._save(plan)
        return self._finish(plan)

    def _locate(self,plan,effect):
        if plan.get('server_birth'):
            from .process import process_identity
            birth=plan['server_birth']
            if process_identity(birth['pid'])!=birth['process']:return None,None
        try:source=self.sessions.resolve(plan['source']['id'])
        except InventoryError:return None,None
        if source.get('native_key')!=plan['source'].get('native_key') or source['state']!='running':return None,None
        matches=[r for r in self._resources() if r['target']['workspace']==source['workspace'] and self._birth(r)==effect['birth']]
        return (matches[0],source) if len(matches)==1 else (None,None)

    def _absent(self,plan,effect):
        """Confirm native absence; an unavailable inventory is never absence."""
        source=self.sessions.resolve(plan['source']['id'])
        if source['backend']=='psmux':
            # Finite native close is birth-pinned by the bridge. A disappeared
            # native namespace is confirmed separately from failed snapshots.
            if source['state']=='empty':return True
            if source['state']!='running' or source.get('native_key')!=plan['source'].get('native_key'):return False
            return not any(w['window_id']==effect['birth']['window_id'] for w in source['snapshot']['windows'])
        birth=plan.get('server_birth')
        if not birth:return not plan['outcomes']
        from .process import process_identity
        if process_identity(birth['pid'])!=birth['process']:return True
        # Read all windows on the original server, so an external move is held.
        import subprocess
        cfg=next((c for c in self.tabs.workspaces.values() if c['kind'] in ('tmux','byobu') and getattr(c['transport'],'socket',None)==plan['source']['server']),None)
        if not cfg:return False
        try:
            ids=cfg['transport'].command(self.sessions._deadline(5),'list-windows','-a','-F','#{window_id}').splitlines()
            return effect['birth']['window_id'] not in ids
        except (OSError,ValueError,subprocess.SubprocessError):return False

    def _drain(self,plan):
        from .terminal_relocation import TerminalRelocation
        relocation=TerminalRelocation(self.sessions.root,tabs=self.tabs,deadline=self.sessions.deadline)
        if not plan.get('relocation_plan'):
            source=self.sessions.resolve(plan['source']['id'])
            destination=self.sessions.resolve(plan['destination'])
            if source['id']==destination['id']:raise InventoryError('invalid_argument','Drain destination must differ from source.')
            frozen=relocation.execute('tabs.relocate.preview',dict(session=source['id'],destination=destination['id']))
            plan.update(relocation_plan=frozen['plan_id'],status='applying');self._save(plan)
        result=relocation.execute('tabs.relocate.apply',dict(plan_id=plan['relocation_plan']))
        plan['outcomes']=result['outcomes'];self._save(plan)
        return self._finish(plan)

    def _finish(self,plan):
        acceptable='moved' if plan['mode']=='drain' else 'terminated'
        with locked(self.sessions.directory):
            state=self.sessions.state();source=self.sessions.resolve(plan['source']['id'],state=state)
            if source['state']=='empty' and all(e['status']==acceptable for e in plan['outcomes']):
                record=state['sessions'][source['id']]
                record.update(deleted=True,deleted_at=time.time());self.sessions.save(state)
                plan.update(status='deleted',session=record);self._save(plan)
            else:
                plan.update(status='partial',session={k:v for k,v in source.items() if k!='snapshot'});self._save(plan)
        return self._cleanup(plan) if plan['status']=='deleted' else plan

    def _cleanup(self,plan):
        from .terminal_routing import TerminalRouting
        plan['rule_cleanup']=TerminalRouting(self.sessions.root,tabs=self.tabs).disable_deleted_destination(plan['source']['id'])
        self._save(plan);return plan
