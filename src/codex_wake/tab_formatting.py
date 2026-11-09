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
    def locked(self):
        import fcntl
        fd=os.open(self.root/'lock',os.O_CREAT|os.O_RDWR,0o600)
        try:
            fcntl.flock(fd,fcntl.LOCK_EX);yield
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
        with self.locked():
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
                self.save(state)
                return dict(status='partial' if failures else 'rolled_back',failures=failures,target=expected)
            from .tab_format_projection import project
            record.update(enabled=True,paused=False);self.save(state)
            # Use public observed traits when available; projection itself never probes.
            rows=self.tabs.execute('tabs.list',{})['resources']
            resources={r['window']['window_id']:r for r in rows if r['target']['workspace']==name}
            failures=[]
            for window in snapshot['windows']:
                wid=window['window_id']
                if window.get('linked'):
                    failures.append(dict(window=wid,code='linked_window'));continue
                try:
                    if wid not in record['windows']:
                        original=transport.formatting('read',dict(window=wid),deadline)
                        record['windows'][wid]=dict(original=original,last_applied=None,restored=False)
                        self.save(state) # Write-ahead original: never decorate without durable custody.
                    rendered=project(resources.get(wid,dict(window=window)),state['policy'],now=time.time())
                    actual=transport.formatting('write',dict(window=wid,values=rendered['options']),deadline)
                    if any(actual[k]['value']!=v for k,v in rendered['options'].items()):
                        raise InventoryError('formatting_mismatch','Formatting readback differs from policy.')
                    record['windows'][wid].update(last_applied=rendered['options'],restored=False)
                    self.save(state)
                except Exception as error:failures.append(dict(window=wid,code=getattr(error,'code','formatting_failed')))
            return dict(status='partial' if failures else 'applied',target=expected,failures=failures)
