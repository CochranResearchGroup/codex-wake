"""Frozen same-server whole-window moves with durable effect reconciliation."""
import re
import os
import time
import uuid
from pathlib import Path

from .managed_inventory import InventoryError
from .shortcut_store import read, write, locked
from .terminal_sessions import TerminalSessions
from .terminal_tab_holds import TabHolds


class TerminalRelocation:
    OPERATIONS=frozenset('tabs.relocate.'+v for v in ('preview','apply','status','undo'))

    def __init__(self,root,*,tabs,automatic=False,deadline=None):
        self.root=Path(root);self.tabs=tabs;self.automatic=automatic;self.deadline=deadline
        self.directory=self.root/'terminal-relocation'
        self.sessions=TerminalSessions(root,tabs=tabs,deadline=deadline)

    def _save(self,record):
        write(self.directory/(record['plan_id']+'.json'),record)
        fd=os.open(self.directory,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(fd)
        finally:os.close(fd)

    def _read(self,key):
        if not isinstance(key,str) or not re.fullmatch(r'(?:plan|receipt)_[a-f0-9]{32}',key):
            raise InventoryError('invalid_argument','A relocation plan or receipt ID is required.')
        key='plan_'+key.split('_',1)[1]
        try:return read(self.directory/(key+'.json'))
        except FileNotFoundError:raise InventoryError('target_not_found','Relocation record not found.')

    @staticmethod
    def _session(record):
        value={k:record.get(k) for k in ('id','name','server','backend','native_key','native_session_id')}
        snapshot=record.get('snapshot')
        if snapshot:
            from .process import process_identity
            birth=process_identity(int(snapshot['server']))
            if not birth or not snapshot.get('socket_identity'):raise InventoryError('stale_target','Exact terminal server birth is unavailable.')
            value['server_birth']=dict(socket=snapshot['socket_identity'],process=birth)
        return value

    @staticmethod
    def _birth(resource):
        return dict(identity=TabHolds.identity(resource),window_id=resource['window']['window_id'],
                    panes=resource['window']['panes'])

    def _resources(self):
        self.sessions._timeout(10)
        return self.tabs.execute('tabs.list',{})['resources']

    def _current(self,reference):
        try:current=self.sessions.resolve(reference['id'])
        except InventoryError:return None
        if current['server']!=reference['server'] or current['backend']!=reference['backend']:return None
        if current['state']=='running' and current.get('native_key')!=reference.get('native_key'):return None
        live=current if current['state']=='running' else next((s for s in self.sessions.inventory() if s['server']==current['server'] and s['state']=='running'),None)
        try:
            if reference.get('server_birth') and (not live or self._session(live).get('server_birth')!=reference['server_birth']):return None
        except InventoryError:return None
        return current

    def execute(self,operation,args):
        self.sessions._timeout(10)
        if operation not in self.OPERATIONS:raise InventoryError('unsupported_operation','Unsupported relocation operation.')
        if not isinstance(args,dict) or set(args)-{'session','destination','selection','plan_id','receipt_id','expected_target','_request'}:
            raise InventoryError('invalid_argument','Unsupported relocation arguments.')
        with locked(self.directory):
            if args.get('expected_target') is not None and args['expected_target']!=self.sessions.target():
                raise InventoryError('stale_target','Session registry changed; inspect again.')
            if operation.endswith('.preview'):return self._preview(args)
            record=self._read(args.get('plan_id') or args.get('receipt_id'))
            if operation.endswith('.status'):
                self._reconcile(record);return record
            if operation.endswith('.undo'):return self._undo(record)
            return self._apply(record)

    def _preview(self,args):
        destination=self.sessions.resolve(args.get('destination'))
        source=self.sessions.resolve(args['session']) if args.get('session') else None
        resources=self._resources()
        by_workspace={v['workspace']:v for v in self.sessions.inventory() if v['workspace']}
        resources=[r for r in resources if r['target']['workspace'] in by_workspace
                   and (not source or by_workspace[r['target']['workspace']]['id']==source['id'])
                   and by_workspace[r['target']['workspace']]['id']!=destination['id']]
        if args.get('selection') is not None:
            from .tab_selection import select
            from .tab_views import TabViews
            groups={g['name']:g for g in TabViews(self.root).execute('tabs.group-list',{})['groups']}
            resources=select(resources,args['selection'],groups=groups)
        if destination['backend'] not in ('tmux','byobu'):raise InventoryError('unsupported_target','Live whole-tab movement requires same-server tmux.')
        destination=self._session(destination) | {'state':destination['state']}
        if not destination.get('server_birth'):
            live=next((v for v in by_workspace.values() if v['server']==destination['server'] and v['backend'] in ('tmux','byobu')),None)
            if live:destination['server_birth']=self._session(live).get('server_birth')
        effects=[]
        for resource in resources:
            src=by_workspace[resource['target']['workspace']]
            if src['backend'] not in ('tmux','byobu') or src['server']!=destination['server']:
                raise InventoryError('unsupported_target','Live whole-tab movement requires same-server tmux.')
            if resource['window'].get('linked'):raise InventoryError('unsupported_target','Linked windows cannot be relocated.')
            if any(not p.get('process_generation') for p in resource['window']['panes']):
                raise InventoryError('stale_target','Exact native process births are required.')
            effects.append(dict(source=self._session(src),birth=self._birth(resource),status='pending'))
        key=uuid.uuid4().hex
        record=dict(version=1,plan_id='plan_'+key,receipt_id='receipt_'+key,status='preview',
                    destination=destination,selection=args.get('selection'),outcomes=effects,created_at=time.time(),automatic=self.automatic)
        self._save(record);return record

    def _locate(self,effect):
        matches=[r for r in self._resources() if self._birth(r)==effect['birth']]
        if len(matches)!=1 or matches[0]['window'].get('linked'):return None,None
        resource=matches[0]
        session=next((s for s in self.sessions.inventory() if s['workspace']==resource['target']['workspace']),None)
        return resource,session

    def _reconcile(self,record):
        if record['status']=='preview' and all(e['status']=='pending' for e in record['outcomes']):return
        for effect in record['outcomes']:
            if effect['status'] not in ('moving','uncertain','undoing','undo_uncertain'):continue
            undo=effect['status'] in ('undoing','undo_uncertain')
            resource,current=self._locate(effect)
            destination=effect.get('undo_destination') if undo else record['destination']
            if current and current['id']==destination['id'] and self._current(destination):
                effect['status']='undone' if undo else 'moved'
                if undo or not record.get('automatic',False):
                    TabHolds(self.root).hold(effect['birth']['identity'],receipt_id=record['receipt_id'])
            else:
                # Source placement after a lost reply does not establish non-submission.
                effect['status']='undo_uncertain' if undo else 'uncertain'
        statuses=[e['status'] for e in record['outcomes']]
        record['status']='completed' if all(s in ('moved','undone') for s in statuses) else 'partial' if any(s in ('moved','undone') for s in statuses) else 'held'
        self._save(record)

    def _adopt(self,session):
        # Save an unmanaged source before its final native window disappears.
        with locked(self.sessions.directory):
            state=self.sessions.state()
            if session['id'] not in state['sessions']:
                value={k:v for k,v in session.items() if k not in ('workspace','snapshot','state','tab_count','managed')}
                value['native_session_id']=session['snapshot']['session_id']
                state['sessions'][session['id']]=value;self.sessions.save(state)

    def _apply(self,record):
        if record['status']!='preview':self._reconcile(record);self._cleanup(record);return record
        record['status']='applying';self._save(record)
        for effect in record['outcomes']:
            self._move(record,effect,record['destination'])
        self._reconcile(record);return record

    def _move(self,record,effect,destination,*,undo=False):
        resource,current=self._locate(effect)
        expected=record['destination'] if undo else effect['source']
        dest=self._current(destination)
        if not resource or not current or current['id']!=expected['id'] or not self._current(expected) or not dest:
            effect['status']='skipped' if undo else 'held';effect['reason']='placement_or_identity_changed';self._save(record);return
        if dest['state']!='running':
            if dest['state']!='empty' or record.get('materializing'):
                effect['status']='held';effect['reason']='destination_materialization_uncertain';self._save(record);return
            # Opening is itself journaled by TerminalSessions. A crash between
            # opening and binding the bootstrap is held, never blindly retried.
            record['materializing']=destination['id'];self._save(record)
            try:
                dest=self.sessions.open(dest,container_only=True)
            except Exception:
                effect['status']='held';effect['reason']='destination_materialization_uncertain';self._save(record);return
            bootstrap=[r for r in self._resources() if r['target']['workspace']==dest['workspace']]
            if len(bootstrap)!=1:
                effect['status']='held';effect['reason']='bootstrap_identity_uncertain';self._save(record);return
            record.setdefault('bootstraps',[]).append(dict(session=dest['id'],birth=self._birth(bootstrap[0]),status='owned'))
            previous=dict(destination);replacement=self._session(dest)
            references=[record['destination'],*[row['source'] for row in record['outcomes']],
                        *[row.get('undo_destination') for row in record['outcomes']]]
            # One owned rematerialization may serve several tabs from the same
            # saved session. Carry only references to that exact prior identity.
            fields=('id','server','backend','native_key','native_session_id','server_birth')
            for reference in references:
                if reference is not None and all(reference.get(k)==previous.get(k) for k in fields):
                    reference.update(replacement)
            destination.update(replacement)
            record.pop('materializing',None);self._save(record)
        # Materializing a destination may take time; refresh the whole-window
        # birth and both namespaces immediately before the move intent.
        resource,current=self._locate(effect)
        if not current or current['id']!=expected['id'] or not self._current(expected) or not self._current(destination):
            effect['status']='skipped' if undo else 'held';effect['reason']='placement_or_identity_changed';self._save(record);return
        self._adopt(current)
        effect['status']='undoing' if undo else 'moving'
        if undo:effect['undo_destination']=destination
        self._save(record)  # Intent is durable before sending the native effect.
        transport=self.tabs.workspaces[current['workspace']]['transport']
        try:
            transport.command(self.sessions._deadline(10),'move-window','-d','-s',resource['window']['window_id'],
                              '-t',dest['snapshot']['session_id']+':')
        except Exception:
            effect['status']='undo_uncertain' if undo else 'uncertain'
            self._save(record)
        self._reconcile(record)
        self._cleanup(record)

    def _cleanup(self,record):
        for bootstrap in record.get('bootstraps',[]):
            if bootstrap['status']!='owned':continue
            resource,current=self._locate(bootstrap)
            if not current or current['id']!=bootstrap['session'] or current['tab_count']<=1:continue
            transferred=False
            for effect in record['outcomes']:
                if effect['status'] not in ('moved','undone'):continue
                _,placement=self._locate(effect)
                if placement and placement['id']==current['id']:transferred=True;break
            if not transferred:continue
            bootstrap['status']='removing';self._save(record)
            try:
                self.tabs.workspaces[current['workspace']]['transport'].command(self.sessions._deadline(5),'kill-window','-t',resource['window']['window_id'])
                bootstrap['status']='removed'
            except Exception:bootstrap['status']='uncertain'
            self._save(record)

    def _undo(self,record):
        self._reconcile(record)
        for effect in record['outcomes']:
            if effect['status']=='moved':self._move(record,effect,effect['source'],undo=True)
        self._reconcile(record);return record
