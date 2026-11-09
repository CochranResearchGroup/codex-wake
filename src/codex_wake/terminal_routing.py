"""Opt-in prioritized routing using frozen relocation receipts and birth-keyed holds."""
import math
import os
import time
import uuid
from pathlib import Path

from .managed_inventory import InventoryError
from .shortcut_store import locked, read, write
from .tab_selection import select, validate
from .tab_views import TabViews
from .terminal_sessions import TerminalSessions
from .terminal_tab_holds import TabHolds
from .terminal_relocation import TerminalRelocation


class TerminalRouting:
    OPERATIONS=frozenset('tabs.route.'+v for v in
        ('list','show','save','delete','enable','pause','tick','status','hold','resume','pin','unpin'))
    ARGUMENTS={
        'save':{'rule_id','name','destination','selection','priority','stability_seconds'},
        'show':{'rule_id','name'},'delete':{'rule_id','name'},'pause':{'rule_id','name'},
        'enable':{'rule_id','name','include_existing'},
        **{v:{'selection','reason'} for v in ('hold','resume','pin','unpin')},
        **{v:set() for v in ('list','status','tick')}}

    def __init__(self,root,*,tabs,clock=time.time):
        self.root=Path(root);self.tabs=tabs;self.clock=clock
        self.directory=self.root/'terminal-routing';self.path=self.directory/'routing.json'
        self._sessions=None;self.deadline=None
        self.holds=TabHolds(root)

    @property
    def sessions(self):
        if self._sessions is None:
            self._sessions=TerminalSessions(self.root,tabs=self.tabs,deadline=self.deadline)
        return self._sessions

    def _state(self):
        try:return read(self.path)
        except FileNotFoundError:return dict(version=1,rules={},pins={},placements={},candidates={},pending=[],outcomes=[])

    def _save(self,state):
        write(self.path,state)
        fd=os.open(self.directory,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(fd)
        finally:os.close(fd)

    def _resources(self):
        return self.tabs.execute('tabs.list',{})['resources']

    def _groups(self):
        return {g['name']:g for g in TabViews(self.root).execute('tabs.group-list',{})['groups']}

    @staticmethod
    def _rule(state,args):
        matches=[r for r in state['rules'].values() if r['id']==args.get('rule_id') or
                 not args.get('rule_id') and r['name']==args.get('name')]
        if len(matches)!=1:raise InventoryError('target_not_found','Routing rule not found.')
        return matches[0]

    def _monitor(self,start=False):
        if not getattr(self.tabs,'host_managed',False):return dict(status='manual',reason='injected_inventory')
        from .tab_monitor import TabMonitor
        monitor=TabMonitor(self.root);status=monitor.execute('tabs.monitor.status',{})
        # An installed older owner must be upgraded explicitly, never restarted here.
        owner=status['monitor']
        if owner['status']=='running':
            if 'tab-routing-v1' not in owner.get('capabilities',[]):
                return dict(status='partial',reason='monitor_upgrade_required',monitor=owner)
        elif start:
            status=monitor.execute('tabs.monitor.start',{})
        return status

    def execute(self,operation,args):
        if operation not in self.OPERATIONS:raise InventoryError('unsupported_operation','Unsupported routing operation.')
        verb=operation.rsplit('.',1)[-1]
        if not isinstance(args,dict) or set(args)-(self.ARGUMENTS[verb]|{'expected_target','_request'}):
            raise InventoryError('invalid_argument','Unsupported routing arguments.')
        with locked(self.directory):
            if args.get('expected_target') is not None and args['expected_target']!=self.sessions.target():
                raise InventoryError('stale_target','Session registry or routing rules changed; inspect again.')
            state=self._state()
            if verb=='list':return dict(rules=sorted(state['rules'].values(),key=lambda r:(r['priority'],r['id'])))
            if verb=='status':return dict(rules=list(state['rules'].values()),outcomes=state['outcomes'],pending=state['pending'],pins=list(state['pins'].values()),holds=self.holds.list(),monitor=self._monitor())
            if verb=='tick':return self._tick(state)
            if verb in ('hold','resume','pin','unpin'):
                validate(args.get('selection'))
                reason=args.get('reason','manual_hold')
                if not isinstance(reason,str) or not reason or len(reason)>512:
                    raise InventoryError('invalid_argument','A bounded hold reason is required.')
                outcomes=[]
                for resource in select(self._resources(),args['selection'],groups=self._groups()):
                    identity=self.holds.identity(resource)
                    if verb=='hold':outcome=self.holds.hold(identity,reason=reason)
                    elif verb=='resume':outcome=self.holds.resume(identity)
                    elif verb=='pin':
                        outcome=dict(identity=identity,reason=reason,pinned_at=self.clock());state['pins'][identity]=outcome
                    else:outcome=dict(identity=identity,unpinned=state['pins'].pop(identity,None) is not None)
                    # Explicit control acknowledges present manual placement.
                    state['placements'][identity]=resource['target']['workspace']
                    state['candidates'].pop(identity,None);outcomes.append(outcome)
                self._save(state);return dict(outcomes=outcomes)
            if verb=='save':
                name=TabViews._name(args.get('name'));validate(args.get('selection'))
                priority=args.get('priority',100);delay=args.get('stability_seconds',10)
                if type(priority) is not int or not -1000000<=priority<=1000000:
                    raise InventoryError('invalid_argument','priority must be a bounded integer.')
                if type(delay) not in (int,float) or not math.isfinite(delay) or not 0<=delay<=3600:
                    raise InventoryError('invalid_argument','stability_seconds must be finite and between 0 and 3600.')
                destination=self.sessions.resolve(args.get('destination'))
                old=self._rule(state,args) if args.get('rule_id') else next((r for r in state['rules'].values() if r['name']==name),None)
                if old and any(r['name']==name and r['id']!=old['id'] for r in state['rules'].values()):
                    raise InventoryError('invalid_argument','Routing rule name already exists.')
                key=old['id'] if old else 'route_'+uuid.uuid4().hex
                rule=dict(id=key,name=name,destination=destination['id'],selection=args['selection'],priority=priority,
                          stability_seconds=delay,enabled=False,revision=(old['revision']+1 if old else 1),excluded=[],updated_at=self.clock())
                state['rules'][key]=rule
                if len(state['rules'])>256:raise InventoryError('invalid_argument','Routing rule capacity reached.')
            else:
                rule=self._rule(state,args)
                if verb=='show':return dict(rule=rule)
                if verb=='delete':del state['rules'][rule['id']]
                elif verb=='pause':
                    rule['enabled']=False;rule['revision']+=1
                elif verb=='enable':
                    include=args.get('include_existing',False)
                    if type(include) is not bool:raise InventoryError('invalid_argument','include_existing must be a boolean.')
                    # Resolve the saved identity rather than a reused destination name.
                    self.sessions.resolve(rule['destination'])
                    resources=self._resources();matches=select(resources,rule['selection'],groups=self._groups())
                    rule['revision']+=1
                    rule.update(enabled=True,excluded=[] if include else [self.holds.identity(r) for r in resources],updated_at=self.clock())
                    for r in resources:state['placements'][self.holds.identity(r)]=r['target']['workspace']
                    state['candidates']={}
            self._save(state)
            result=dict(rule=rule,deleted=verb=='delete')
            if verb=='enable':result.update(existing_matches=[TabViews.identity(r) for r in matches],include_existing=include,monitor=self._monitor(start=True))
            return result

    def disable_deleted_destination(self,session_id):
        """Retire rules for a confirmed tombstone, under the routing owner lock."""
        with locked(self.directory):
            tombstone=self.sessions.state()['sessions'].get(session_id,{})
            if not tombstone.get('deleted'):
                raise InventoryError('stale_target','Destination deletion is not confirmed.')
            state=self._state();changed=[]
            for rule in state['rules'].values():
                if rule['destination']!=session_id:continue
                if rule.get('disabled_reason')=='destination_deleted' and not rule['enabled']:continue
                rule.setdefault('history',[]).append(dict(revision=rule['revision'],enabled=rule['enabled'],reason='destination_deleted',at=self.clock()))
                rule.update(enabled=False,disabled_reason='destination_deleted',revision=rule['revision']+1,updated_at=self.clock())
                changed.append(rule['id'])
            self._save(state)
            return dict(status='completed',disabled_rules=changed,destination=session_id)

    def tick(self,snapshot=None,*,deadline=None):
        """Monitor seam: one bounded observation cycle; no daemon or probes added."""
        with locked(self.directory):return self._tick(self._state(),snapshot=snapshot,deadline=deadline)

    def _tick(self,state,snapshot=None,deadline=None):
        self.deadline=deadline
        if deadline is not None and time.monotonic()>=deadline:
            return dict(status='partial',reason='cycle_deadline',outcomes=[],pending=state['pending'])
        if self._sessions is not None:self._sessions.deadline=deadline
        if not state['pending'] and not any(r['enabled'] for r in state['rules'].values()):
            state['outcomes']=[];self._save(state)
            return dict(status='completed',outcomes=[],pending=[])
        relocation=TerminalRelocation(self.root,tabs=self.tabs,automatic=True,deadline=deadline)
        # Reconciliation precedes any fresh selection/dispatch after restart.
        unresolved=[];outcomes=[]
        for pending in state['pending']:
            record=relocation.execute('tabs.relocate.status',{'plan_id':pending['plan_id']})
            if record['status']=='preview':record=relocation.execute('tabs.relocate.apply',{'plan_id':pending['plan_id']})
            uncertain=any(e['status'] in ('moving','uncertain','undoing','undo_uncertain') for e in record['outcomes'])
            status='uncertain' if uncertain else record['outcomes'][0]['status'] if record['outcomes'] else 'held'
            if uncertain:unresolved.append(pending)
            if status=='moved':
                destination=self.sessions.resolve(record['destination']['id'])
                state['placements'][pending['identity']]=destination['workspace']
            state['candidates'].pop(pending['identity'],None)
            outcomes.append(dict(identity=pending['identity'],status=status,relocation=record))
        state['pending']=unresolved
        if unresolved:
            state['outcomes']=outcomes;self._save(state);return dict(status='partial',outcomes=outcomes,pending=unresolved)
        resources=snapshot.get('resources',[]) if snapshot is not None else self._resources()
        # Failed/stale monitor rows cannot establish stable routing observations.
        resources=[r for r in resources if not r.get('monitor_unavailable') and r.get('monitor_freshness','fresh')=='fresh']
        groups=self._groups();enabled=sorted((r for r in state['rules'].values() if r['enabled']),key=lambda r:(r['priority'],r['id']))
        self.sessions.deadline=deadline
        inventory=self.sessions.inventory()
        available={s['id']:s for s in inventory}
        matches={}
        for rule in enabled:
            if rule['destination'] not in available:
                rule.update(enabled=False,disabled_reason='destination_unavailable');continue
            matches[rule['id']]={self.holds.identity(r) for r in select(resources,rule['selection'],groups=groups)}
        sessions={s['workspace']:s for s in inventory if s['workspace']}
        active=set()
        for resource in resources:
            identity=self.holds.identity(resource);active.add(identity);workspace=resource['target']['workspace']
            if deadline is not None and time.monotonic()>=deadline:
                outcomes.append(dict(identity=identity,tab=TabViews.identity(resource),status='held',reason='cycle_deadline'));break
            previous=state['placements'].get(identity)
            if previous is not None and previous!=workspace:self.holds.hold(identity,reason='external_manual_move')
            state['placements'][identity]=workspace
            candidates=[r for r in enabled if identity in matches.get(r['id'],set()) and identity not in r['excluded']]
            if not candidates:state['candidates'].pop(identity,None);continue
            base=dict(identity=identity,tab=TabViews.identity(resource))
            hold=self.holds.get(identity)
            if hold or identity in state['pins']:
                outcomes.append(base|dict(status='held',reason='pinned' if identity in state['pins'] else hold['reason']));state['candidates'].pop(identity,None);continue
            first=candidates[0];peers=[r for r in candidates if r['priority']==first['priority']]
            if len({r['destination'] for r in peers})>1:
                outcomes.append(base|dict(status='held',reason='priority_conflict',rules=[r['id'] for r in peers]));state['candidates'].pop(identity,None);continue
            if sessions.get(workspace,{}).get('id')==first['destination']:
                state['candidates'].pop(identity,None);continue
            now=self.clock();signature=[(r['id'],r['revision']) for r in peers]
            # JSON persistence changes tuples to lists; signatures remain canonical JSON lists.
            signature=[list(v) for v in signature]
            traits=resource.get('traits',{}).get('traits',{})
            signature.append({k:{f:v.get(f) for f in ('value','status','freshness')} for k,v in traits.items() if isinstance(v,dict)})
            candidate=state['candidates'].get(identity)
            if candidate is None or candidate['signature']!=signature or now<candidate['since']:
                candidate=dict(signature=signature,since=now);state['candidates'][identity]=candidate
            if now-candidate['since']<max(r['stability_seconds'] for r in peers):
                outcomes.append(base|dict(status='stabilizing',rule_id=first['id'],since=candidate['since']));continue
            try:
                plan=relocation.execute('tabs.relocate.preview',dict(destination=first['destination'],selection={'tabs':[TabViews.identity(resource)]}))
                pending=dict(identity=identity,plan_id=plan['plan_id'],rule_id=first['id'],rule_revision=first['revision'],selection=first['selection'])
                # Retain immutable rule provenance beside the exact frozen native plan.
                write(self.directory/'plans'/(plan['plan_id']+'.json'),pending)
                fd=os.open(self.directory/'plans',os.O_RDONLY|os.O_DIRECTORY)
                try:os.fsync(fd)
                finally:os.close(fd)
                state['pending'].append(pending);self._save(state)
                result=relocation.execute('tabs.relocate.apply',{'plan_id':plan['plan_id']})
                status=result['outcomes'][0]['status'] if result['outcomes'] else 'held'
                outcomes.append(base|dict(status=status,rule_id=first['id'],relocation=result))
                if status=='moved':
                    # Native window identity is placement-independent; read current destination only after confirmed success.
                    destination=self.sessions.resolve(first['destination']);state['placements'][identity]=destination['workspace']
                if status not in ('moving','uncertain'):state['pending'].remove(pending)
                state['candidates'].pop(identity,None)
            except InventoryError as error:
                outcomes.append(base|dict(status='held',reason=error.code,rule_id=first['id']))
        state['candidates']={k:v for k,v in state['candidates'].items() if k in active}
        state['outcomes']=outcomes;self._save(state)
        return dict(status='partial' if state['pending'] or any(v.get('status')!='moved' for v in outcomes) else 'completed',outcomes=outcomes,pending=state['pending'])
