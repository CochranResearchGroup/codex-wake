"""Retained host observer: bounded metadata feeds, shared cache and projection.

One owner retains source connections across ticks. Native notifications never
confer input authority; exact pane process births and existing title/CWD matching
remain the attachment boundary. No transcript subscription is created here.
"""
from copy import deepcopy
import json
import hashlib
import math
from pathlib import Path
import time

from .managed_inventory import InventoryError
from .process import process_identity
from .tab_organization import TmuxTransport


_REVISION_FIELDS=frozenset(('projection_revision','evidence_revision','projection_valid_until'))
_CLOCK_FIELDS=frozenset(('observed_at','monitor_observed_at','age_seconds'))


def _revision(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def _semantic(value, now, boundaries, trait_name=None):
    """Timeless display facts plus qualified freshness, with scheduled boundaries."""
    if isinstance(value,dict):
        result={key:_semantic(item,now,boundaries,key) for key,item in value.items()
                if key not in _REVISION_FIELDS and key not in _CLOCK_FIELDS}
        if {'value','status','source'}<=value.keys():
            stamp=value.get('observed_at')
            finite=type(stamp) in (int,float) and math.isfinite(stamp)
            eligible=(value.get('source_available') is not False
                      and value.get('status') not in ('unknown','unsupported','stale','configured',None)
                      and value.get('freshness') not in ('stale','unknown','unsupported','configured'))
            result['_display_known']=bool(finite and stamp<=now and value.get('status') in ('observed','stale'))
            dynamic=(trait_name=='activity' or trait_name=='error' and value.get('value')=='present'
                     or trait_name=='health' and value.get('value') in
                     ('unresponsive','offline','degraded','warning','error'))
            if dynamic:
                result['_display_fresh']=bool(finite and eligible and stamp<=now
                    and (value.get('source_available') is True or now-stamp<=20))
            if finite and stamp>now and (eligible or value.get('status') in ('observed','stale')):
                boundaries.append(stamp)
            if dynamic and finite and eligible and value.get('source_available') is not True and stamp<=now<=stamp+20:
                boundaries.append(stamp+20+.000001)
        return result
    if isinstance(value,(list,tuple)):
        return [_semantic(item,now,boundaries,trait_name) for item in value]
    return value


class _SnapshotTransport:
    def __init__(self, original):
        self.original, self.value, self.available = original, None, False

    def snapshot(self, deadline):
        if not self.available or self.value is None:
            raise InventoryError('attachment_unavailable', 'Metadata source is unavailable.')
        return deepcopy(self.value)

    def __getattr__(self, name):
        return getattr(self.original, name)


class _TmuxSnapshotTransport(_SnapshotTransport, TmuxTransport):
    """Preserve the concrete ownership guard of an already qualified adapter."""
    def __init__(self, original):
        if not isinstance(original,TmuxTransport):
            raise ValueError('A qualified tmux adapter is required.')
        super().__init__(original)

    def command(self, deadline, *arguments):
        return self.original.command(deadline, *arguments)


class _NativeReader:
    """Existing session_rows binding logic over retained metadata-only feeds."""
    def __init__(self, observer, endpoint, timeout):
        self.owner, self.endpoint, self.timeout = observer, endpoint, timeout
        self.path = Path(endpoint[7:]).resolve()
        self.fallback = None

    def __enter__(self):
        from .tab_native_feed import NativeStatusFeed
        feed = self.owner.native.get(self.endpoint)
        if feed is None:
            if len(self.owner.native)>=64:
                retired=next(iter(self.owner.native))
                self.owner.native.pop(retired).close()
                self.owner.native_state.pop(retired,None)
            factory = self.owner.native_factory or NativeStatusFeed
            feed = self.owner.native[self.endpoint] = factory(self.endpoint, timeout=min(.5, self.timeout))
        self.owner._native_events(self.endpoint, feed.poll())
        state = self.owner.native_state.get(self.endpoint)
        if feed.status()['state'] != 'connected' or state is None:
            # Unsupported passive feeds retain existing bounded metadata fallback.
            from .shared_app_server import SharedAppServerReader
            self.fallback = SharedAppServerReader(self.endpoint, timeout=min(.5, self.timeout))
            result = self.fallback.__enter__()
            self.connection, self.server_metadata = result.connection, result.server_metadata
            self.owner.fallback_sources[self.endpoint] = self.owner.clock()
        else:
            self.connection = feed.connection
            self.server_metadata = state['server']
        return self

    def loaded_threads(self, maximum=1000):
        if self.fallback is not None:
            return self.fallback.loaded_threads(maximum=maximum)
        values = list(self.owner.native_state[self.endpoint]['threads'].values())
        if len(values) > maximum:
            raise ValueError('thread_population_exceeded')
        return deepcopy(values)

    def __exit__(self, *args):
        if self.fallback is not None:
            self.fallback.__exit__(*args)


class TabObserver:
    """Public retained observation seam used by the existing TabMonitor owner."""
    def __init__(self, root, *, owner=None, settings=None, clock=time.time,
                 monotonic=time.monotonic, tmux_feed_factory=None,
                 native_feed_factory=None, native_endpoints=(), fallback_probe=None):
        from .controller_tabs import controller_tabs_from_root
        self.root = Path(root)
        self.clock, self.monotonic = clock, monotonic
        self.settings = dict(activity=True, health=True, errors=True,
                             health_interval=60., error_interval=5., fallback_interval=5.)
        self.settings.update(settings or {})
        self.owner_factory = controller_tabs_from_root
        self.owner = owner or self.owner_factory(self.root)
        self.external_owner = owner is not None
        self.tmux_factory, self.native_factory = tmux_feed_factory, native_feed_factory
        self.native_endpoints = tuple(native_endpoints)
        self.fallback_probe = fallback_probe
        self.tmux, self.native, self.native_state = {}, {}, {}
        self.fallback_sources = {}
        self.metadata_at = {}
        self.metadata_due = set()
        self.resources, self.unavailable = [], []
        self._resource_json = None
        self._projection_dirty = True
        self._all_revisions_dirty = True
        self._dirty_resources = set()
        self._resource_revisions = {}
        self._next_projection_boundary = None
        self._snapshot_projection_revision = self._snapshot_evidence_revision = None
        self.closed = False
        self.last_inventory = self.last_discovery = -float('inf')
        self.cursor = self.tmux_cursor = self.native_cursor = 0
        self.epochs, self.sequences = {}, {}
        self.source_errors = {}
        self.costs = dict(ticks=0, inventory_passes=0, native_events=0,
                          fallback_probes=0, last_tick_seconds=0., total_seconds=0.)
        self.configuration = self._configuration()
        self._prepare_owner()

    def _configuration(self):
        result = []
        for name in ('controller-tabs.json', 'controller-accounts.toml'):
            try:
                info = (self.root/name).stat()
                result.append((name, info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns))
            except OSError:
                result.append((name, None))
        return tuple(result)

    def _prepare_owner(self):
        from .tab_tmux_feed import TmuxMetadataFeed
        cache = self.owner.observation_cache
        if hasattr(cache, 'configure_checks'):
            cache.configure_checks(**{k:self.settings[k] for k in
                ('activity', 'health', 'errors', 'health_interval', 'error_interval')})
        if hasattr(cache, 'set_process_ttl'):
            cache.set_process_ttl(30)
        cache.session_reader = self._session_rows
        for name, config in list(self.owner.workspaces.items())[:64]:
            if config['kind'] not in ('tmux', 'byobu'):
                continue
            self.tmux[name] = (self.tmux_factory or TmuxMetadataFeed)(
                config['socket_path'], config['session_id'], timeout=2.)
            wrapper = _TmuxSnapshotTransport if isinstance(config['transport'],TmuxTransport) else _SnapshotTransport
            config['transport'] = wrapper(config['transport'])

    def _session_rows(self, root, **kwargs):
        from .tab_traits import session_rows
        if self.native_endpoints:
            kwargs['endpoints'] = self.native_endpoints
        result = session_rows(root, reader_factory=lambda endpoint, timeout:
                              _NativeReader(self, endpoint, timeout), **kwargs)
        for row in result['sessions']:
            source = row.get('endpoint')
            state = self.native_state.get(source)
            row['source_available'] = bool(state and source in self.native and
                                           self.native[source].status()['state'] == 'connected')
            row['source_epoch'] = state.get('epoch') if state else None
        return result

    def _accept(self, key, event):
        epoch, sequence = event.get('epoch'), event.get('sequence')
        if event.get('kind') == 'unavailable':
            return True
        if event.get('kind') == 'baseline':
            self.epochs[key], self.sequences[key] = epoch, sequence
            return True
        if epoch != self.epochs.get(key) or sequence != self.sequences.get(key, 0)+1:
            return False
        self.sequences[key] = sequence
        return True

    def _native_events(self, endpoint, events):
        for event in events:
            self.costs['native_events'] += 1
            valid=self._accept(endpoint,event)
            if not valid or event['kind'] == 'unavailable':
                self.source_errors[endpoint]=event.get('data',{}).get('reason','native_sequence_gap')
                if not valid and endpoint in self.native:
                    self.native.pop(endpoint).close()
                    self.last_inventory=-float('inf')
                self.native_state.pop(endpoint, None)
                self._source_lost(endpoint)
                continue
            if event['kind'] == 'baseline':
                self.source_errors.pop(endpoint,None)
                data = event['data']
                self.native_state[endpoint] = dict(threads={v['id']:v for v in data['threads']},
                    server=data['server'], peer=data['peer'], epoch=event['epoch'])
                self.metadata_at[endpoint] = self.monotonic()
                self.last_inventory = -float('inf')
            else:
                data, state = event['data'], self.native_state.get(endpoint)
                if state and data['thread_id'] in state['threads']:
                    state['threads'][data['thread_id']]['status'] = data['status']
                elif state:
                    self.metadata_due.add(endpoint)
                self._project_activity(endpoint, data['thread_id'], data['status'], event['epoch'])

    @staticmethod
    def _resource_key(resource):
        return (resource.get('target',{}).get('workspace'),resource.get('window',{}).get('window_id'))

    def _prepare_revisions(self, now):
        """Hash changed producer records once; idle ticks reuse opaque tokens."""
        active=set()
        for resource in self.resources:
            key=self._resource_key(resource);active.add(key)
            previous=self._resource_revisions.get(key)
            expired=bool(previous and previous[2] is not None and now>=previous[2])
            if self._all_revisions_dirty or key in self._dirty_resources or previous is None or expired:
                evidence={name:value for name,value in resource.items()
                          if name not in _REVISION_FIELDS and name!='monitor_observed_at'}
                boundaries=[]
                semantic=_semantic(evidence,now,boundaries)
                previous=(_revision(semantic),_revision(evidence),min(boundaries) if boundaries else None)
                self._resource_revisions[key]=previous
            resource['projection_revision'],resource['evidence_revision'],resource['projection_valid_until']=previous
        self._resource_revisions={key:value for key,value in self._resource_revisions.items() if key in active}
        self._next_projection_boundary=min((value[2] for value in self._resource_revisions.values()
                                            if value[2] is not None),default=None)
        source_facts=sorted((key,self.epochs.get(key),self.source_errors.get(key))
                            for key in set(self.epochs)|set(self.source_errors))
        self._snapshot_projection_revision=_revision(dict(resources=[(self._resource_key(row),row['projection_revision'])
            for row in self.resources],workspaces=list(self.owner.workspaces),
            unavailable=_semantic(self.unavailable,now,[]),source_errors=source_facts))
        self._snapshot_evidence_revision=_revision(dict(resources=[(self._resource_key(row),row['evidence_revision'])
            for row in self.resources],workspaces=list(self.owner.workspaces),
            unavailable=self.unavailable,source_errors=source_facts))
        self._dirty_resources.clear();self._all_revisions_dirty=False

    def _source_lost(self, endpoint):
        self._projection_dirty = True
        for resource in self.resources:
            for pane in resource.get('traits', {}).get('panes', []):
                if pane.get('native_endpoint') == endpoint:
                    self._dirty_resources.add(self._resource_key(resource))
                    pane['traits']['activity'].update(source_available=False, status='unknown',freshness='unknown',
                        source_reason='native_source_unavailable',reason='native_source_unavailable')
            self._summary(resource)

    @staticmethod
    def _activity(status):
        kind = status.get('type')
        if kind == 'active':
            flags = set(status.get('activeFlags', []))
            return ('waiting-for-input' if flags and flags <= {'waitingOnApproval', 'waitingOnUserInput'}
                    else 'unknown' if flags else 'running')
        return {'idle':'idle', 'notLoaded':'disconnected'}.get(kind, 'unknown')

    def _project_activity(self, endpoint, thread_id, status, epoch):
        if not self.settings['activity']:
            return
        self._projection_dirty = True
        for resource in self.resources:
            for pane in resource.get('traits', {}).get('panes', []):
                binding = pane.get('binding') or {}
                if pane.get('native_endpoint') != endpoint or binding.get('conversation_id') != thread_id:
                    continue
                self._dirty_resources.add(self._resource_key(resource))
                expected = binding.get('process') or {}
                current = process_identity(expected.get('pid', 0))
                valid = bool(current and str(current.get('start_time_ticks')) == str(expected.get('start_ticks'))
                             and current.get('boot_id') == expected.get('boot_id'))
                pane['traits']['activity'].update(value=self._activity(status), status='observed' if valid else 'unknown',
                    freshness='fresh' if valid else 'unknown', source_available=valid,
                    source_epoch=epoch, observed_at=self.clock())
            self._summary(resource)

    @staticmethod
    def _summary(resource):
        observation = resource.get('traits', {})
        panes = observation.get('panes', [])
        if not panes:
            return
        values = [p['traits']['activity'] for p in panes]
        summary = deepcopy(values[0])
        if len({v['value'] for v in values}) > 1:
            summary.update(value='mixed')
        summary['source_available'] = all(v.get('source_available') is not False for v in values)
        observation.setdefault('traits', {})['activity'] = summary

    def _inventory(self, deadline):
        self._projection_dirty = True
        self._all_revisions_dirty = True
        from .controller_tabs import ControllerTabs
        rows, unavailable = [], []
        names = list(self.owner.workspaces)[:64]
        start = self.cursor % len(names) if names else 0
        for name in names[start:] + names[:start]:
            if self.monotonic() >= deadline:
                unavailable.append(dict(workspace=name, reason='observer_cycle_deadline'))
                rows.extend(v for v in self.resources if v['target']['workspace'] == name)
                continue
            config = self.owner.workspaces[name]
            if name not in self.tmux:
                if self.fallback_probe:
                    self.costs['fallback_probes'] += 1
                    value = self.fallback_probe(name, min(.5, max(.1, deadline-self.monotonic())))
                    value = value.get('result', {}) if value.get('status') == 'completed' else dict(unavailable=[dict(workspace=name,reason=value.get('reason','fallback_unavailable'))])
                else:
                    value = dict(unavailable=[dict(workspace=name, reason='event_feed_unsupported')])
            else:
                scoped = ControllerTabs(self.root, workspaces={name:config}, host=self.owner.host,
                    environment=self.owner.environment, observation_cache=self.owner.observation_cache)
                value = scoped.execute('tabs.list', {})
            rows.extend(value.get('resources', []))
            unavailable.extend(value.get('unavailable', []))
        self.cursor = (start+1) % len(names) if names else 0
        represented = {v.get('target',{}).get('workspace') for v in rows}
        missing = {v.get('workspace') for v in unavailable} - represented
        for previous in self.resources:
            if previous.get('target',{}).get('workspace') in missing:
                retained = deepcopy(previous)
                retained['monitor_unavailable'] = True
                for pane in retained.get('traits',{}).get('panes',[]):
                    for key in ('activity','health','error'):
                        pane.get('traits',{}).get(key,{}).update(source_available=False,status='unknown',freshness='unknown')
                self._summary(retained)
                rows.append(retained)
        self.resources, self.unavailable = rows, unavailable
        # Attach source identities only after exact existing metadata/process binding.
        for resource in self.resources:
            workspace=resource.get('target',{}).get('workspace')
            if workspace in self.tmux:
                resource['presentation_source']=dict(epoch=self.tmux[workspace].status().get('epoch'),
                    available=self.owner.workspaces[workspace]['transport'].available)
            if resource.get('monitor_unavailable'):
                for pane in resource.get('traits',{}).get('panes',[]):
                    for key in ('activity','health','error'):
                        pane.get('traits',{}).get(key,{}).update(source_available=False,status='unknown',freshness='unknown')
                self._summary(resource)
                continue
            for pane in resource.get('traits', {}).get('panes', []):
                binding = pane.get('binding') or {}
                endpoints = [endpoint for endpoint, state in self.native_state.items()
                    if binding.get('conversation_id') in state['threads'] and
                    binding.get('namespace') == Path(state['server'].get('codexHome', '/')).name]
                endpoint = endpoints[0] if len(endpoints)==1 else None
                pane['native_endpoint'] = endpoint
                available = bool(endpoint and self.native[endpoint].status()['state'] == 'connected')
                pane['traits']['activity'].update(source_available=available,
                    source_epoch=self.native_state[endpoint]['epoch'] if available else None)
                if available and self.settings['activity']:
                    status = self.native_state[endpoint]['threads'][binding['conversation_id']]['status']
                    pane['traits']['activity'].update(value=self._activity(status), status='observed',
                        freshness='fresh', observed_at=self.clock())
            self._summary(resource)
        self.last_inventory = self.monotonic()
        self.costs['inventory_passes'] += 1

    def tick(self, *, deadline=None):
        if self.closed:
            raise ValueError('Observer is closed.')
        started = self.monotonic()
        deadline = deadline or started+2
        configuration = self._configuration()
        if configuration != self.configuration and not self.external_owner:
            self._close_feeds()
            self.owner = self.owner_factory(self.root)
            self._prepare_owner()
            self.configuration = configuration
            self.last_inventory = -float('inf')
        dirty = False
        tmux_items=list(self.tmux.items())
        offset=self.tmux_cursor % len(tmux_items) if tmux_items else 0
        self.tmux_cursor+=1
        for name, feed in tmux_items[offset:]+tmux_items[:offset]:
            if self.monotonic() >= deadline:
                break
            for event in feed.poll():
                transport = self.owner.workspaces[name]['transport']
                valid = self._accept('tmux:'+name, event)
                if not valid or event['kind'] == 'unavailable':
                    transport.available = False
                    self.source_errors['tmux:'+name]=event.get('data',{}).get('reason','tmux_sequence_gap')
                    if not valid:
                        from .tab_tmux_feed import TmuxMetadataFeed
                        feed.close()
                        config=self.owner.workspaces[name]
                        self.tmux[name]=(self.tmux_factory or TmuxMetadataFeed)(config['socket_path'],config['session_id'],timeout=2.)
                else:
                    self.source_errors.pop('tmux:'+name,None)
                    transport.value, transport.available = event['data']['snapshot'], True
                self.owner.observation_cache.invalidate(name)
                dirty = True
        native_items=list(self.native.items())
        offset=self.native_cursor % len(native_items) if native_items else 0
        self.native_cursor+=1
        for endpoint, feed in native_items[offset:]+native_items[:offset]:
            if self.monotonic() >= deadline:
                break
            self._native_events(endpoint, feed.poll())
            age = self.monotonic()-self.metadata_at.get(endpoint,-float('inf'))
            if hasattr(feed,'refresh_metadata') and (age>=30 or (endpoint in self.metadata_due and age>=1)):
                self._native_events(endpoint,feed.refresh_metadata())
                self.metadata_due.discard(endpoint)
        if dirty or started-self.last_inventory >= self.settings['fallback_interval']:
            self._inventory(deadline)
        now = self.clock()
        self.costs['ticks'] += 1
        if self._next_projection_boundary is not None and now>=self._next_projection_boundary:
            self._projection_dirty=True
        # Resources are JSON contract data. Keep the canonical encoding until
        # evidence changes; C decoding gives each caller fully independent nested
        # containers without Python deepcopy walking the same idle graph each tick.
        if self._projection_dirty or self._resource_json is None:
            self._prepare_revisions(now)
            self._resource_json = json.dumps(self.resources, separators=(',', ':'), allow_nan=False)
            self._projection_dirty = False
        resources = json.loads(self._resource_json)
        for row in resources:
            row.update(monitor_observed_at=now)
            row.setdefault('monitor_unavailable',False)
            name = row['target']['workspace']
            if name in self.tmux and not self.owner.workspaces[name]['transport'].available:
                row['monitor_unavailable'] = True
        self.costs['last_tick_seconds'] = self.monotonic()-started
        self.costs['total_seconds'] += self.costs['last_tick_seconds']
        return dict(schema_version=1, observed_at=now, resources=resources,
                    projection_revision=self._snapshot_projection_revision,
                    evidence_revision=self._snapshot_evidence_revision,
                    projection_valid_until=self._next_projection_boundary,
                    unavailable=deepcopy(self.unavailable), workspaces=list(self.owner.workspaces)[:64],
                    status='partial' if self.unavailable else 'complete' if self.owner.workspaces else 'not_found',
                    observer=self.status())

    def status(self):
        return dict(mode='persistent', sources=[dict(workspace=name, **feed.status()) for name,feed in self.tmux.items()]+
                    [feed.status() for feed in self.native.values()], costs=dict(self.costs),
                    backlog=sum(feed.status().get('backlog', feed.status().get('pending_commands', 0))
                                for feed in [*self.tmux.values(), *self.native.values()]),
                    tiers={k:self.settings[k] for k in ('activity','health','errors','health_interval','error_interval')},
                    fallback_sources=len(self.fallback_sources),
                    checks=self.owner.observation_cache.checks.status(),
                    unknown_reasons=sorted(set(self.source_errors.values()) | {v.get('reason',v.get('code','observation_unavailable'))
                                            for v in self.unavailable}), closed=self.closed)

    def _close_feeds(self):
        for feed in [*self.tmux.values(), *self.native.values()]:
            feed.close()
        self.tmux.clear()
        self.native.clear()
        self.native_state.clear()

    def close(self):
        self._close_feeds()
        self.closed = True


def render_status(value):
    """Human monitor readback; JSON/API/MCP continue returning the same object."""
    result = value.get('result', {}).get('operation', {}).get('result', value)
    monitor = result.get('monitor', {})
    snapshot = result.get('snapshot') or {}
    observer = monitor.get('observer') or snapshot.get('observer') or {}
    lines = ['Tab monitor: '+monitor.get('status','unknown'),
             'Tabs: '+str(len(snapshot.get('resources', [])))+'; observation: '+snapshot.get('status','unavailable')]
    settings = monitor.get('settings', {})
    lines.append('Tiers: '+', '.join(key+'='+('on' if settings.get(key,True) else 'off')
                                    for key in ('activity','health','errors')))
    for source in observer.get('sources', []):
        lines.append(source.get('source_kind','source')+': '+source.get('state','unknown')+
                     (' ('+str(source['reason'])+')' if source.get('reason') else ''))
    lines.append('Backlog: '+str(observer.get('backlog',0)))
    costs = observer.get('costs', {})
    if costs:
        lines.append('Last observation: '+format(costs.get('last_tick_seconds',0),'.3f')+'s; inventory passes: '+str(costs.get('inventory_passes',0)))
    return '\n'.join(lines)
