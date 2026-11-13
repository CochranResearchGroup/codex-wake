"""Dirty projection with a bounded shared lease on the existing monitor owner."""
import copy
import hashlib
import json
import math
from pathlib import Path
import time

LEASE_RENEW_SECONDS=10.0
_DIMENSIONS=('harness','build','profile','account','model_identity','model',
             'inference_provider','execution_host','remote_host','session_presence',
             'activity','health','error')
_EVIDENCE=('value','status','freshness','source','source_available','source_epoch',
           'reason','redacted_message','location')


def _state_identity(root):
    try:
        info=(Path(root)/'tab-formatting'/'state.json').stat()
        return info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns,info.st_ctime_ns
    except FileNotFoundError:
        return None


def semantic_revision(value, *, trusted=False):
    """Accept only a bounded host-produced token whose display lease is valid."""
    token=value.get('projection_revision')
    if not trusted or not isinstance(token,str) or not 0<len(token)<=128:return None
    until=value.get('projection_valid_until')
    if until is not None and (type(until) not in (int,float) or not math.isfinite(until) or until<=time.time()):return None
    return token


def _sources_key(tabs):
    sources=[]
    for name,config in tabs.workspaces.items():
        transport=config.get('transport');socket=getattr(transport,'socket',None)
        live=None
        if socket:
            try:
                info=Path(socket).lstat()
                live=(info.st_dev,info.st_ino,info.st_mode,info.st_uid)
            except OSError as error:live=('unavailable',error.errno)
        sources.append((name,config.get('kind'),socket,getattr(transport,'session',None),
                        getattr(transport,'socket_identity',None),live))
    return tuple(sources)


def _projection_key(snapshot):
    """Hash display-relevant evidence, excluding sample clocks and cost counters."""
    token=semantic_revision(snapshot,trusted=snapshot.get('origin')=='daemon')
    if token is not None:return ('revision',snapshot.get('monitor_generation'),token)
    resources=[]
    for resource in snapshot.get('resources',[]):
        observation=resource.get('traits',{})
        panes=observation.get('panes') or [dict(traits=observation.get('traits',{}))]
        traits=[]
        for pane in panes:
            dimensions=pane.get('traits',{})
            traits.append((pane.get('pane_id'),[(name,[(key,dimensions[name].get(key))
                for key in _EVIDENCE]) for name in _DIMENSIONS if isinstance(dimensions.get(name),dict)]))
        resources.append((resource.get('target'),resource.get('window'),resource.get('backend_identity'),
                          resource.get('monitor_unavailable'),resource.get('bot_family'),traits))
    raw=json.dumps((resources,snapshot.get('unavailable',[])),sort_keys=True,
                   separators=(',',':'),allow_nan=False).encode()
    return hashlib.sha256(raw).hexdigest()


def refresh_formatting(root,snapshot,*,tabs=None,deadline=None,resources_loader=None):
    """Project semantic changes immediately; renew the shared lease every ten seconds.

    The cache belongs to the retained trusted host owner, never a global/per-tab
    process. Its one small result is invalidated by source/binding changes or any
    external formatting state replacement (pause, rollback, policy or resume).
    Native custody audits still run in the formatter; failures are never cached.
    """
    from .controller_tabs import controller_tabs_from_root
    from .tab_formatting import TabFormatting
    tabs=tabs or controller_tabs_from_root(root)
    # Monitor resources bypass public inventory. Requalify family identity here
    # rather than trusting retained labels or semantic trait revision tokens.
    family_path=Path(root)/'bot-families'/'registry.json'
    if family_path.exists():
        from .bot_families import BotFamilies
        if resources_loader is not None:
            resources_loader()
            resources_loader=None
        snapshot=copy.deepcopy(snapshot)
        snapshot.pop('projection_revision',None)
        for resource in snapshot.get('resources',[]):
            resource.pop('bot_family',None)
            resource.pop('projection_revision',None)
        BotFamilies(root,tabs=tabs).annotate(snapshot.get('resources',[]))
    now=time.monotonic()
    if (resources_loader is not None and 'resources' not in snapshot
            and semantic_revision(snapshot,trusted=snapshot.get('origin')=='daemon') is None):
        resources_loader()
        resources_loader=None
    key=(str(root),_projection_key(snapshot),_state_identity(root),_sources_key(tabs))
    cache=getattr(tabs,'_format_projection_cache',None)
    if cache and cache['key']==key and now<cache['renew_at']:
        return copy.deepcopy(cache['result'])
    if resources_loader is not None:
        resources_loader()
    trusted=key[1][0]=='revision' if isinstance(key[1],tuple) else False
    formatter=TabFormatting(root,tabs=tabs)
    result=None
    if trusted and cache and cache['key']==key:
        result=formatter.renew_unchanged(snapshot,cache['result'],deadline=deadline or now+10)
    if result is None:
        result=formatter.refresh(snapshot,deadline=deadline or now+10,trusted_revisions=trusted)
    if result.get('status') in ('completed','disabled'):
        tabs._format_projection_cache=dict(key=(key[0],key[1],_state_identity(root),key[3]),
            renew_at=now+LEASE_RENEW_SECONDS,result=copy.deepcopy(result))
    else:
        tabs._format_projection_cache=None
    return result
