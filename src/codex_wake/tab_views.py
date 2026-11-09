"""Persistent view definitions and named groups over observed attachments."""
import hashlib
import json
import time
from pathlib import Path
from .managed_inventory import InventoryError
from .shortcut_store import read, write, locked

FIELDS = frozenset(('harness','build','account','repository','remote_host','activity','health','error','session_presence'))


class TabViews:
    READS = frozenset(('tabs.view-list','tabs.view-show','tabs.view-evaluate','tabs.group-list','tabs.group-show'))
    MUTATIONS = frozenset(('tabs.view-save','tabs.view-delete','tabs.group-save','tabs.group-delete'))

    def __init__(self,root):
        self.directory=Path(root)/'tab-views'
        self.path=self.directory/'definitions.json'

    def _read(self):
        try:return read(self.path)
        except FileNotFoundError:return dict(version=1,views={},groups={})

    @staticmethod
    def _name(name):
        if not isinstance(name,str) or not name or len(name)>128 or any(ord(c)<32 for c in name):
            raise InventoryError('invalid_argument','A bounded group/view name is required.')
        return name

    @staticmethod
    def _values(resource):
        traits=resource.get('traits',{}).get('traits',{})
        return {key: value.get('value','unknown') if value.get('status')=='observed' else 'unknown'
                for key,value in traits.items() if isinstance(value,dict)}

    @staticmethod
    def identity(resource):
        window=resource['window'];target=resource['target']
        key=target['workspace']+'/'+window['window_id']
        identity=hashlib.sha256(json.dumps([(v['pane_id'],dict(platform='windows',creation_filetime=v.get('windows_creation_filetime')) if v.get('platform')=='windows' else v.get('process_generation')) for v in window['panes']],sort_keys=True).encode()).hexdigest()
        return dict(id=key,identity=identity)

    def execute(self,operation,arguments,*,resources=()):
        if operation not in self.READS|self.MUTATIONS:
            raise InventoryError('unsupported_operation','Unsupported saved tab view operation.')
        allowed={'name','definition'} if operation=='tabs.view-save' else {'name','members','labels'} if operation=='tabs.group-save' else {'name'}
        if operation in ('tabs.view-list','tabs.group-list'):allowed=set()
        if not isinstance(arguments,dict) or set(arguments)-allowed:
            raise InventoryError('invalid_argument','Unsupported saved-view arguments.')
        if operation in self.MUTATIONS:
            with locked(self.directory):
                return self._execute(operation,arguments,resources,self._read())
        return self._execute(operation,arguments,resources,self._read())

    def _execute(self,operation,args,resources,state):
        kind='groups' if operation.startswith('tabs.group-') else 'views'
        table=state[kind]
        if operation.endswith('-list'):
            return {kind:[table[k] for k in sorted(table)],'physical_effects':False}
        name=self._name(args.get('name'))
        if operation=='tabs.view-save':
            definition=args.get('definition')
            if not isinstance(definition,dict) or set(definition)-{'filters','group_by','sort_by','group','selection'}:
                raise InventoryError('invalid_argument','A view definition with filters/group_by/sort_by is required.')
            for field in ('group_by','sort_by'):
                keys=definition.get(field,[])
                if not isinstance(keys,list) or len(keys)>len(FIELDS) or any(v not in FIELDS for v in keys):
                    raise InventoryError('invalid_argument','Unknown tab trait in '+field)
            filters=definition.get('filters',{})
            if not isinstance(filters,dict) or set(filters)-FIELDS or any(not isinstance(v,(str,list)) or isinstance(v,list) and (len(v)>32 or any(not isinstance(i,str) for i in v)) for v in filters.values()):
                raise InventoryError('invalid_argument','Filters must match supported traits to bounded values.')
            if 'group' in definition:self._name(definition['group'])
            if 'selection' in definition:
                from .tab_selection import validate
                validate(definition['selection'])
            table[name]=dict(name=name,definition=definition,updated_at=time.time())
        elif operation=='tabs.group-save':
            members=args.get('members',[])
            if not isinstance(members,list) or len(members)>4096 or any(not isinstance(v,str) for v in members):
                raise InventoryError('invalid_argument','Group members must be observed attachment IDs.')
            labels=args.get('labels',[])
            if not isinstance(labels,list) or len(labels)>32:
                raise InventoryError('invalid_argument','Labels must be a bounded list of names.')
            labels=list(dict.fromkeys(self._name(label) for label in labels))
            inventory={self.identity(r)['id']:self.identity(r) for r in resources}
            if set(members)-inventory.keys():
                raise InventoryError('stale_target','A group member is absent; refresh tabs before saving.')
            table[name]=dict(name=name,members=[inventory[k] for k in dict.fromkeys(members)],labels=labels,updated_at=time.time())
        elif operation.endswith('-delete'):
            if name not in table:raise InventoryError('target_not_found','Saved group/view not found.')
            del table[name]
        elif name not in table:
            raise InventoryError('target_not_found','Saved group/view not found.')
        if operation in self.MUTATIONS:
            if len(state['views'])+len(state['groups'])>256:
                raise InventoryError('invalid_argument','Saved view/group limit reached.')
            write(self.path,state)
        if operation=='tabs.view-evaluate':
            definition=table[name]['definition'];selected=[];group=None
            if definition.get('group'):
                group=state['groups'].get(definition['group'])
                if group is None:raise InventoryError('target_not_found','Referenced named group is unavailable.')
            if 'selection' in definition:
                from .tab_selection import select
                resources=select(resources,definition['selection'],groups=state['groups'])
            for resource in resources:
                if group is not None and self.identity(resource) not in group['members']:continue
                values=self._values(resource)
                if all(values.get(k,'unknown') in (v if isinstance(v,list) else [v]) for k,v in definition.get('filters',{}).items()):selected.append(resource)
            keys=definition.get('group_by',[])+definition.get('sort_by',[])
            selected.sort(key=lambda r:tuple(str(self._values(r).get(k,'unknown')) for k in keys)+(self.identity(r)['id'],))
            groups=[]
            for resource in selected:
                grouping=[self._values(resource).get(k,'unknown') for k in definition.get('group_by',[])]
                if not groups or groups[-1]['key']!=grouping:groups.append(dict(key=grouping,attachments=[]))
                groups[-1]['attachments'].append(self.identity(resource)['id'])
            return dict(view=table[name],resources=selected,groups=groups,physical_effects=False)
        return dict(**{kind[:-1]:table.get(name)},deleted=operation.endswith('-delete'),physical_effects=False)
