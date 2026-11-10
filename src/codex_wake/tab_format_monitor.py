"""Dirty projection with a bounded shared lease on the existing monitor owner."""
import copy
import hashlib
import json
from pathlib import Path
import time

LEASE_RENEW_SECONDS=5.0
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


def _projection_key(snapshot):
    """Hash display-relevant evidence, excluding sample clocks and cost counters."""
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
                          resource.get('monitor_unavailable'),traits))
    raw=json.dumps((resources,snapshot.get('unavailable',[])),sort_keys=True,
                   separators=(',',':'),allow_nan=False).encode()
    return hashlib.sha256(raw).hexdigest()


def refresh_formatting(root,snapshot,*,tabs=None,deadline=None):
    """Project semantic changes immediately; renew the shared lease every five seconds.

    The cache belongs to the retained trusted host owner, never a global/per-tab
    process. Its one small result is invalidated by source/binding changes or any
    external formatting state replacement (pause, rollback, policy or resume).
    Native custody audits still run in the formatter; failures are never cached.
    """
    from .controller_tabs import controller_tabs_from_root
    from .tab_formatting import TabFormatting
    tabs=tabs or controller_tabs_from_root(root)
    now=time.monotonic()
    key=(str(root),_projection_key(snapshot),_state_identity(root))
    cache=getattr(tabs,'_format_projection_cache',None)
    if cache and cache['key']==key and now<cache['renew_at']:
        return copy.deepcopy(cache['result'])
    result=TabFormatting(root,tabs=tabs).refresh(snapshot,deadline=deadline or now+10)
    if result.get('status') in ('completed','disabled'):
        tabs._format_projection_cache=dict(key=(key[0],key[1],_state_identity(root)),
            renew_at=now+LEASE_RENEW_SECONDS,result=copy.deepcopy(result))
    else:
        tabs._format_projection_cache=None
    return result
