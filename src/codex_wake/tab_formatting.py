"""Durable reversible ownership of tab decoration, independent of backend."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import tempfile
import time

from .managed_inventory import InventoryError
from .tab_organization import digest

READS=frozenset(('tabs.format.status','tabs.format.inspect'))
VERBS=('status','inspect','enable','pause','resume','rollback','reenable','reset','configure')
DEFAULT_POLICY=dict(enabled=True,show_model=False,show_provider=False,ascii=True)


class TabFormatting:
    def __init__(self, root, *, tabs):
        self.root=Path(root)/'tab-formatting';self.tabs=tabs
        self.root.mkdir(parents=True,exist_ok=True,mode=0o700)
        self.path=self.root/'state.json'

    @contextmanager
    def locked(self,deadline=None):
        import fcntl
        fd=os.open(self.root/'lock',os.O_CREAT|os.O_RDWR,0o600)
        try:
            deadline=deadline or time.monotonic()+10
            while True:
                try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB);break
                except BlockingIOError:
                    if time.monotonic()>=deadline:
                        raise InventoryError('formatting_busy','Formatting owner lock deadline exhausted.')
                    time.sleep(.01)
            yield
        finally:os.close(fd)

    def read(self):
        if not self.path.exists():return dict(schema_version=1,policy=dict(DEFAULT_POLICY),workspaces={})
        value=json.loads(self.path.read_text())
        if value.get('schema_version')!=1:raise InventoryError('configuration_unavailable','Unsupported formatting state.')
        return value

    def save(self,value):
        fd,name=tempfile.mkstemp(dir=self.root,prefix='.state-')
        try:
            with os.fdopen(fd,'w') as stream:
                json.dump(value,stream,sort_keys=True,allow_nan=False);stream.flush();os.fsync(stream.fileno())
            os.replace(name,self.path)
        finally:
            if os.path.exists(name):os.unlink(name)

    def identity(self,snapshot):
        return digest({k:snapshot.get(k) for k in ('server','session_id','socket_identity','bridge_generation')})

    def execute(self,operation,arguments):
        verb=operation.removeprefix('tabs.format.')
        if verb not in VERBS or not isinstance(arguments,dict) or set(arguments)-{'workspace','policy','expected_target'}:
            raise InventoryError('invalid_argument','Unsupported formatting arguments.')
        name=arguments.get('workspace')
        if name is None and len(self.tabs.workspaces)==1:name=next(iter(self.tabs.workspaces))
        if name not in self.tabs.workspaces:raise InventoryError('ambiguous_target','Select one owned workspace.')
        config=self.tabs.workspaces[name];transport=config['transport'];deadline=time.monotonic()+10
        if not hasattr(transport,'formatting'):raise InventoryError('unsupported_target','Backend formatting is unavailable.')
        from .tab_lifecycle import TabLifecycle
        inspected=TabLifecycle(self.tabs.root,workspaces=self.tabs.workspaces,host=self.tabs.host,environment=self.tabs.environment).inspect(name,deadline=deadline)
        snapshot=inspected['snapshot'];expected=inspected['target']
        if arguments.get('expected_target') is not None and arguments['expected_target']!=expected:
            raise InventoryError('stale_target','Presentation changed before formatting.')
        with self.locked(deadline):
            state=self.read();record=state['workspaces'].get(name)
            identity=self.identity(snapshot)
            if record and record['identity']!=identity:
                raise InventoryError('stale_target','Formatting baseline belongs to a different namespace; preserve it for recovery.')
            if verb in ('status','inspect'):
                return dict(status='inspection',target=expected,policy=state['policy'],record=record,
                    windows=[dict(window=w['window_id'],options=transport.formatting('read',dict(window=w['window_id']),deadline)) for w in snapshot['windows']])
            if verb=='configure':
                policy=arguments.get('policy',{})
                if not isinstance(policy,dict) or set(policy)-set(DEFAULT_POLICY) or any(type(v) is not bool for v in policy.values()):
                    raise InventoryError('invalid_argument','Display policy accepts known boolean options.')
                state['policy'].update(policy);self.save(state)
                return dict(status='configured',policy=state['policy'])
            if record is None:
                if verb in ('rollback','reenable','resume'):
                    raise InventoryError('baseline_missing','No saved original formatting baseline; use enable first.')
                record=dict(identity=identity,enabled=False,paused=False,windows={})
                state['workspaces'][name]=record
            if verb in ('pause','rollback','reset'):
                record.update(enabled=False,paused=verb=='pause');self.save(state)
                if verb=='pause':return dict(status='paused',target=expected)
                failures=[]
                live={w['window_id'] for w in snapshot['windows']}
                for window,saved in record['windows'].items():
                    if window not in live:
                        failures.append(dict(window=window,code='window_missing'));continue
                    try:
                        wanted={k:v['value'] if v['explicit'] else None for k,v in saved['original'].items()}
                        actual=transport.formatting('write',dict(window=window,values=wanted),deadline)
                        if any(actual[k]['explicit']!=saved['original'][k]['explicit'] or actual[k]['value']!=saved['original'][k]['value'] for k in wanted):
                            raise InventoryError('restoration_mismatch','Restoration readback differs from saved original.')
                        saved['restored']=True
                    except Exception as error:failures.append(dict(window=window,code=getattr(error,'code','restoration_failed')))
                if 'session_original' in record:
                    try:
                        wanted={k:v['value'] if v['explicit'] else None for k,v in record['session_original'].items()}
                        actual=transport.formatting('write-session',dict(values=wanted),deadline)
                        if any(actual[k]['explicit']!=v['explicit'] or actual[k]['value']!=v['value'] for k,v in record['session_original'].items()):
                            raise InventoryError('restoration_mismatch','Session restoration differs from saved original.')
                    except Exception as error:failures.append(dict(code=getattr(error,'code','session_restoration_failed')))
                self.save(state)
                try:transport.formatting('refresh',{},deadline)
                except Exception as error:failures.append(dict(code=getattr(error,'code','refresh_failed')))
                return dict(status='partial' if failures else 'rolled_back',failures=failures,target=expected)
            from .tab_format_projection import project
            record.update(enabled=True,paused=False);self.save(state)
            # Explicit enable uses public observations. Automatic refresh passes
            # its already bounded snapshot directly to the same apply path.
            rows=self.tabs.execute('tabs.list',{})['resources']
            resources={r['window']['window_id']:r for r in rows if r['target']['workspace']==name}
            failures=self.apply(state,record,snapshot,resources,transport,deadline)
            return dict(status='partial' if failures else 'applied',target=expected,failures=failures)

    def apply(self,state,record,snapshot,resources,transport,deadline,*,automatic=False):
        """Apply one snapshot under the owner lock, saving originals first."""
        from .tab_format_projection import project
        from .tab_format_expiry import expiring_options
        failures=[]
        try:
            if 'session_original' not in record:
                record['session_original']=transport.formatting('read-session',{},deadline)
                self.save(state)
            if automatic and record.get('session_last_applied'):
                current=transport.formatting('read-session',{},deadline)
                if any(current[k]['value']!=v for k,v in record['session_last_applied'].items()):
                    record['paused']=True;record['pause_reason']='manual_session_style';self.save(state)
                    return [dict(code='manual_override')]
            effective=record['session_original']['status-interval']['effective']
            interval=float(effective)
            interval=str(int(interval)) if 0<interval<=5 else '5'
            session_values={'status-interval':interval,'@wake-format-clock':'%s'}
            actual=transport.formatting('write-session',dict(values=session_values),deadline)
            if any(actual[k]['value']!=v for k,v in session_values.items()):
                raise InventoryError('formatting_mismatch','Session formatting readback differs from policy.')
            record['session_last_applied']=session_values
            self.save(state)
        except Exception as error:
            return [dict(code=getattr(error,'code','session_formatting_failed'))]
        windows=snapshot['windows'][:128]
        if len(snapshot['windows'])>128:failures.append(dict(code='formatting_window_capacity'))
        eligible=[]
        for window in windows:
            wid=window['window_id']
            if window.get('linked'):
                failures.append(dict(window=wid,code='linked_window'));continue
            if automatic and record['windows'].get(wid,{}).get('paused'):continue
            eligible.append(window)
        reads=self.batch(transport,[dict(action='read',window=w['window_id']) for w in eligible],deadline)
        pending=[]
        for window,read in zip(eligible,reads):
            wid=window['window_id']
            if 'error' in read:
                failures.append(dict(window=wid,code=read['error']));continue
            try:
                current=read['result']
                if wid not in record['windows']:
                    record['windows'][wid]=dict(original=current,last_applied=None,restored=False)
                    self.save(state)
                saved=record['windows'][wid]
                if automatic and saved.get('last_applied') and any(current[k]['value']!=v for k,v in saved['last_applied'].items()):
                    saved.update(paused=True,pause_reason='manual_style');self.save(state);continue
                if not automatic:saved.pop('paused',None);saved.pop('pause_reason',None)
                rendered=project(resources.get(wid,dict(window=window)),state['policy'],now=time.time())
                resource=resources.get(wid,{})
                stamp=resource.get('monitor_observed_at',time.time())
                options=expiring_options(rendered['options'],observed_at=stamp)
                # Native deadline changes refresh the TTL; unchanged options can
                # skip writes when reliable events repeat the same sample.
                if all(current[k]['value']==v for k,v in options.items()):continue
                pending.append((wid,options,rendered))
            except Exception as error:failures.append(dict(window=wid,code=getattr(error,'code','formatting_failed')))
        writes=self.batch(transport,[dict(action='write',window=wid,values=options) for wid,options,_ in pending],deadline)
        for (wid,options,rendered),write in zip(pending,writes):
            if 'error' in write:
                failures.append(dict(window=wid,code=write['error']));continue
            actual=write['result']
            if any(actual[k]['value']!=v for k,v in options.items()):
                failures.append(dict(window=wid,code='formatting_mismatch'));continue
            record['windows'][wid].update(last_applied=options,restored=False,
                projection={k:v for k,v in rendered.items() if k!='options'})
            self.save(state)
        try:transport.formatting('refresh',{},deadline)
        except Exception as error:failures.append(dict(code=getattr(error,'code','refresh_failed')))
        return failures

    @staticmethod
    def batch(transport,requests,deadline):
        """Bounded finite batches avoid a host bridge startup per window."""
        if not requests:return []
        if hasattr(transport,'formatting_batch'):
            try:
                results=transport.formatting_batch(requests,deadline)
                if not isinstance(results,list) or len(results)!=len(requests):
                    raise InventoryError('formatting_mismatch','Native batch readback count differs.')
                return [dict(error=value['error'].get('code','formatting_failed')) if isinstance(value,dict) and 'error' in value else dict(result=value) for value in results]
            except Exception as error:
                return [dict(error=getattr(error,'code','formatting_batch_failed')) for _ in requests]
        results=[]
        for request in requests:
            args={k:v for k,v in request.items() if k!='action'}
            try:results.append(dict(result=transport.formatting(request['action'],args,deadline)))
            except Exception as error:results.append(dict(error=getattr(error,'code','formatting_failed')))
        return results

    def refresh(self,snapshot,*,deadline=None):
        """Project a trusted monitor/event snapshot without repeating probes.

        Unavailable observations retain existing native expiry rather than
        extending apparently fresh display. No observed workspace is invented.
        """
        deadline=deadline or time.monotonic()+10
        resources=snapshot.get('resources',[])
        grouped={}
        for resource in resources:
            name=resource.get('target',{}).get('workspace')
            if name in self.tabs.workspaces and not resource.get('monitor_unavailable'):
                grouped.setdefault(name,{})[resource['window']['window_id']]=resource
        results=[dict(workspace=value.get('workspace'),status='unavailable',code=value.get('reason',value.get('code','observation_unavailable'))) for value in snapshot.get('unavailable',[])[:64]]
        with self.locked(deadline):
            state=self.read()
            if not state['policy'].get('enabled',True):return dict(status='disabled',workspaces=[])
            for name,rows in grouped.items():
                if time.monotonic()>=deadline:
                    results.append(dict(workspace=name,status='unavailable',code='formatting_deadline'));continue
                record=state['workspaces'].get(name)
                if record and (not record.get('enabled') or record.get('paused')):
                    results.append(dict(workspace=name,status='paused' if record.get('paused') else 'disabled'));continue
                config=self.tabs.workspaces[name];transport=config['transport']
                try:
                    from .tab_lifecycle import TabLifecycle
                    physical=TabLifecycle(self.tabs.root,workspaces=self.tabs.workspaces,host=self.tabs.host,environment=self.tabs.environment).inspect(name,deadline=deadline)['snapshot']
                    identity=self.identity(physical)
                    if record and identity!=record['identity']:
                        raise InventoryError('stale_target','Formatting namespace changed; baseline preserved.')
                    if record is None:
                        record=dict(identity=identity,enabled=True,paused=False,windows={})
                        state['workspaces'][name]=record;self.save(state)
                    # Never project onto a newly discovered or replaced window
                    # that was not represented in the trusted bounded sample.
                    physical=dict(physical,windows=[w for w in physical['windows'] if w['window_id'] in rows
                        and w['panes']==rows[w['window_id']]['window']['panes']])
                    failures=self.apply(state,record,physical,rows,transport,deadline,automatic=True)
                    results.append(dict(workspace=name,status='partial' if failures else 'applied',failures=failures))
                except Exception as error:
                    results.append(dict(workspace=name,status='unavailable',code=getattr(error,'code','formatting_unavailable')))
        return dict(status='partial' if any(r['status'] in ('partial','unavailable') for r in results) else 'completed',workspaces=results)
