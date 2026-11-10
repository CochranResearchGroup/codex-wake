"""Bounded host-owned metadata cache shared across inventory and enrichment.

Cached evidence is never input authority. Process births and presentation generations
fence entries; live process metadata also detects new descendants below a stable shell.
No terminal capture or conversation contents are stored here.
"""
from copy import deepcopy
import json
from pathlib import Path
import time
import os
import math

from .process import process_identity


class ObservationCache:
    def __init__(self, root, *, process_probe=None, identity_probe=process_identity,
                 monotonic=time.monotonic, ttl=2.0, max_entries=512, session_reader=None, health_probe=None):
        self.root = Path(root)
        from .tab_observation_checks import TieredChecks
        self.checks=TieredChecks(monotonic=monotonic)
        self.activity_enabled=True
        self.health_probe=health_probe
        self.session_reader = session_reader
        self.process_probe = process_probe
        self.identity_probe = identity_probe
        self.monotonic = monotonic
        self.ttl = min(5.0, max(.1, float(ttl)))
        self.process_ttl = self.ttl
        self.max_entries = min(4096, max(1, int(max_entries)))
        self._processes = {}
        self._observations = {}
        self._generations = {}
        self._dirty_panes = {}

    def _birth(self, pid):
        try:
            value = self.identity_probe(pid)
            return (pid, value['boot_id'], str(value['start_time_ticks']))
        except (OSError, ValueError, KeyError, TypeError, ProcessLookupError):
            return None

    def _put(self, mapping, key, value):
        if key not in mapping and len(mapping) >= self.max_entries:
            mapping.pop(next(iter(mapping)))
        mapping[key] = value

    def _pending_dirty(self, workspace=None):
        now=self.monotonic()
        for key,until in list(self._dirty_panes.items()):
            if now>=until:
                self._dirty_panes.pop(key,None)
        return {pane for (name,pane) in self._dirty_panes if workspace is None or name==workspace}

    def mark_dirty(self, workspace, pane_ids):
        """Prioritize host-observed changes for bounded recent error checks."""
        if not isinstance(workspace,str):
            raise ValueError('workspace must be a string')
        self._pending_dirty()
        for pane in list(pane_ids)[:self.max_entries]:
            if isinstance(pane,str) and 0<len(pane)<=256:
                self._put(self._dirty_panes,(workspace,pane),self.monotonic()+30)

    def has_dirty(self, workspace=None):
        return bool(self._pending_dirty(workspace))

    def set_process_ttl(self, seconds):
        """Retained owners can reuse complete trees while live metadata agrees."""
        if type(seconds) not in (int,float) or not math.isfinite(seconds) or not .1<=seconds<=30:
            raise ValueError('process cache lifetime must be .1..30 seconds')
        self.process_ttl=float(seconds)

    def _tree_matches(self, pid, rows, deadline):
        if self.process_probe is not None:
            # Injected host-owned process observers provide their own metadata fence.
            return True
        try:
            children=set()
            for row in rows:
                if time.monotonic()>=deadline:
                    return False
                current=row['process']['pid'];base=Path('/proc')/str(current)
                if os.readlink(base/'exe')!=row['executable'] or os.readlink(base/'cwd')!=row['cwd']:
                    return False
                if (base/'cmdline').read_bytes()[:16384].decode(errors='replace').split('\0')!=row['argv']:
                    return False
                children.update(int(value) for value in (base/'task'/str(current)/'children').read_text().split())
            return children=={row['process']['pid'] for row in rows}-{pid}
        except (OSError,ValueError,KeyError,TypeError):
            return False

    def processes(self, pid, deadline):
        from .tab_traits import _processes
        birth = self._birth(pid)
        now = self.monotonic()
        previous = self._processes.get(pid)
        if birth is not None and previous and previous[0] == birth and now < previous[1]:
            # Validate all retained descendants, not just the pane's shell.
            rows, complete = previous[2]
            valid = all(time.monotonic()<deadline and (birth if row['process']['pid']==pid else self._birth(row['process']['pid'])) ==
                        (row['process']['pid'],row['process']['boot_id'],str(row['process']['start_ticks']))
                        for row in rows)
            if valid and self._tree_matches(pid,rows,deadline):
                return deepcopy((rows, complete))
        result = (self.process_probe or _processes)(pid, deadline)
        if birth is not None and result[1]:
            self._put(self._processes, pid, (birth, now+self.process_ttl, deepcopy(result)))
        return result

    def observe(self, workspace, snapshot, *, socket_path=None, transport=None,
                privacy=None, deadline=None, explicit_checks=False, dirty_panes=()):
        from .tab_organization import digest
        from .tab_traits import TabTraits, session_rows
        deadline=deadline or time.monotonic()+2
        dirty_panes=set(dirty_panes)|self._pending_dirty(workspace)
        generation = digest(snapshot)
        if self._generations.get(workspace) != generation:
            self._processes.clear()
            self._observations.pop(workspace, None)
            self._put(self._generations,workspace,generation)
        panes = [p for w in snapshot['windows'] for p in w.get('panes', [])]
        # Controller inventory already captured these same-user pane births.
        # Reuse that host-owned evidence here; processes() independently checks
        # the live root again before reusing any retained descendant tree.
        births = tuple((p.get('pid'),p['process_generation'].get('boot_id'),
                        str(p['process_generation'].get('start_time_ticks')))
                       if isinstance(p.get('process_generation'),dict) else self._birth(p.get('pid'))
                       for p in panes)
        now = self.monotonic()
        prior = self._observations.get(workspace)
        if not explicit_checks and not dirty_panes and prior and prior[0] == (generation,births) and all(b is not None for b in births) and now < prior[1]:
            # Descendant birth validation prevents retaining a dead agent under a live shell.
            for p in panes:
                self.processes(p.get('pid'),deadline)
            if prior[3] == digest(self._processes):
                observed,rows=json.loads(prior[2])
                return observed,rows
        # Discover each pane once, then enrich that evidence with native metadata.
        needs_native = False
        investigated = {}
        native_panes = []
        for pane in panes:
            if pane.get('platform') == 'windows':
                continue
            rows, _ = self.processes(pane.get('pid'),deadline)
            investigated[pane.get('pid')] = (rows, _)
            clients = [row for row in rows if Path(row['executable']).name.lower() == 'codex']
            needs_native |= bool(clients)
            client = clients[0]['process'] if len(clients) == 1 else {}
            native_panes.append(dict(pane, client_pid=client.get('pid'),
                client_start_time_ticks=client.get('start_ticks'),
                pane_title=pane.get('pane_title',''),pane_current_path=pane.get('pane_current_path',''),
                session_id=snapshot.get('session_id'),session_name=snapshot.get('session_id'),
                window_id=next(w['window_id'] for w in snapshot['windows'] if pane in w.get('panes',[])),
                socket=socket_path))
        rows = (self.session_reader or session_rows)(self.root,socket_path=socket_path,panes=native_panes,
                            deadline=min(deadline,time.monotonic()+2)) if needs_native else dict(sessions=[],holds=[])
        traits = TabTraits(self.root,sessions=rows['sessions'],process_probe=lambda pid,limit: investigated.get(pid,([],False)),
                           health_probe=self.health_probe,check_scheduler=self.checks,
                           check_namespace=(workspace,snapshot.get('server'),tuple(snapshot.get('socket_identity',()))),
                           explicit_checks=explicit_checks,dirty_panes=dirty_panes)
        observed = {w['window_id']:traits.observe_window(w,transport=transport,privacy=privacy,deadline=deadline)
                    for w in snapshot['windows']}
        if not self.activity_enabled:
            from .tab_traits import _trait
            for window in observed.values():
                window['traits']['activity']=_trait(reason='activity_observation_disabled')
                for pane in window['panes']:
                    pane['traits']['activity']=_trait(reason='activity_observation_disabled')
                    pane['binding']=None
        result = (observed,rows)
        self._put(self._observations,workspace,((generation,births),now+self.ttl,json.dumps(result,separators=(',',':'),allow_nan=False),digest(self._processes)))
        return result

    def configure_checks(self, *, activity=True, health=True, errors=True, health_interval=60,error_interval=5):
        """Configure independent tiers; interval floors preserve the resource budget."""
        if type(activity) is not bool:
            raise ValueError('activity switch must be boolean')
        previous=(self.activity_enabled,self.checks.enabled,self.checks.intervals)
        self.checks.configure(health=health,errors=errors,health_interval=health_interval,error_interval=error_interval)
        self.activity_enabled=activity
        if previous != (activity,self.checks.enabled,self.checks.intervals):
            self._observations.clear()

    def invalidate(self, workspace=None):
        """Fence retained evidence when a feed disconnects or changes epoch."""
        self._processes.clear()
        for key in list(self._dirty_panes):
            if workspace is None or key[0]==workspace:
                self._dirty_panes.pop(key,None)
        if workspace is None:
            self._observations.clear()
            self._generations.clear()
        else:
            self._observations.pop(workspace,None)
            self._generations.pop(workspace,None)
