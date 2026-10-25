"""Bounded redacted operator projections and existing-only terminal navigation."""
from __future__ import annotations

import math
import os
from pathlib import Path
import stat
import subprocess
import time

from .agent_observation import AgentObservation, RuntimeStateObserver
from .managed_inventory import ManagedInventory
from .records import WakeError
from .session_permissions import PermissionStore, Principal, check_operation
from .sessions import observe as sessions_observe, resolve


class OverviewError(WakeError):
    pass


def _bound(value, low, high):
    if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
        raise OverviewError('invalid overview bound')


class OperatorOverview:
    def __init__(self, root, *, inventory=None, observe=None, session_source=None,
                 observer=None, monotonic=time.monotonic, socket_path=None, endpoint='unix://'):
        self.root, self.clock = root, monotonic
        self.inventory = inventory or (lambda: ManagedInventory(root).inspect())
        self.observe = observe or AgentObservation(root, observer=observer or RuntimeStateObserver(endpoint=endpoint)).observe
        self.session_source = session_source or (lambda timeout: sessions_observe(
            endpoint=endpoint, socket_path=socket_path, timeout=timeout/2))

    def snapshot(self, *, limit=50, timeout=10, freshness=30):
        if type(limit) is not int or not 1 <= limit <= 100:
            raise OverviewError('limit must be 1..100')
        _bound(timeout, .1, 30)
        _bound(freshness, .1, 300)
        deadline = self.clock() + timeout
        population = sorted(self.inventory()['agents'], key=lambda row: row['managed_agent_id'])
        rows, complete = [], len(population) <= limit
        for agent in population[:limit]:
            remaining = deadline - self.clock()
            semantic = dict(state='unknown', fresh=False, observed_at=None,
                            reason='budget_exhausted', capabilities={})
            if remaining >= .001:
                try:
                    value = self.observe(agent['managed_agent_id'], freshness=freshness,
                                         timeout=min(remaining, 60))
                    semantic = {key: value[key] for key in ('state', 'fresh', 'observed_at',
                                'reason', 'evidence_kind', 'capabilities') if key in value}
                except Exception:
                    semantic['reason'] = 'source_unavailable'
            if self.clock() >= deadline:
                semantic = dict(state='unknown', fresh=False, observed_at=None,
                                reason='budget_exhausted', capabilities={})
            if not semantic.get('fresh'):
                complete = False
            rows.append(dict(managed_agent_id=agent['managed_agent_id'], runtime=agent['runtime'],
                workspace=agent['root'], repository=self._repository(agent['root'], deadline),
                task_id=agent.get('task_id'), enrollment=agent['enrollment'],
                binding=dict(state=agent['state'], current=agent['binding_current']), semantic=semantic))
        for row in rows:
            semantic=row['semantic']
            observed=semantic.get('observed_at')
            if (semantic.get('fresh') and (type(observed) not in (int,float)
                    or not observed <= time.time() <= observed+freshness)):
                semantic.update(state='unknown',fresh=False,reason='evidence_expired_during_scan')
            if row['repository']['status']!='verified' or not semantic.get('fresh'):
                complete=False
        if self.clock() >= deadline:
            complete=False
        return dict(schema_version=1, status='overview', complete=complete,
                    truncated=len(population)>limit, population=len(population), agents=rows,
                    inventory_scope='managed_only', grants_operations=False)

    def _repository(self, workspace, deadline):
        remaining = deadline-self.clock()
        if remaining <= .001:
            return dict(status='unknown', reason='budget_exhausted')
        environment = {k:v for k,v in os.environ.items() if not k.startswith('GIT_')}
        try:
            result = subprocess.run(['git','-C',workspace,'rev-parse','--show-toplevel',
                '--path-format=absolute','--git-common-dir'], env=environment,
                capture_output=True, text=True, timeout=min(remaining, 2), check=True)
            lines=result.stdout.splitlines()
            if len(lines)!=2:
                raise ValueError('ambiguous git identity')
            top, common = (Path(value).resolve(strict=True) for value in lines)
            if any(any(ord(c)<32 for c in str(path)) for path in (top,common)):
                raise ValueError('invalid git path')
            info=common.stat()
            if not stat.S_ISDIR(info.st_mode) or not top.is_dir():
                raise ValueError('invalid Git directory')
            return dict(status='verified', worktree=str(top), common_dir=str(common),
                        device=info.st_dev, inode=info.st_ino)
        except (OSError, ValueError, subprocess.SubprocessError):
            return dict(status='unknown', reason='git_identity_unavailable')

    def _client(self, socket_path, client, timeout):
        if client is None:
            try:
                client=os.ttyname(0)
            except OSError:
                raise OverviewError('invoking client tty unavailable') from None
        if not isinstance(client,str) or not client.startswith('/dev/'):
            raise OverviewError('owned client tty required')
        tty=Path(client)
        info=tty.stat()
        if not stat.S_ISCHR(info.st_mode) or info.st_uid != os.geteuid():
            raise OverviewError('owned client tty required')
        result=subprocess.run(['tmux','-S',socket_path,'list-clients','-F',
            '#{client_tty}\t#{client_pid}'], capture_output=True,text=True,check=True,timeout=timeout)
        matches=[line.split('\t') for line in result.stdout.splitlines() if line.split('\t')[0]==client]
        if len(matches)!=1 or len(matches[0])!=2:
            raise OverviewError('invoking client ambiguous or unavailable')
        pid=int(matches[0][1])
        if Path('/proc/'+str(pid)).stat().st_uid != os.geteuid():
            raise OverviewError('foreign tmux client')
        return client, pid

    def _attachment(self, managed_agent_id, timeout):
        _bound(timeout, .1, 30)
        agent = next((a for a in self.inventory()['agents'] if a['managed_agent_id']==managed_agent_id), None)
        if (not agent or agent['runtime'] != 'codex' or agent['enrollment'] != 'enrolled'
                or not agent.get('binding_current')):
            raise OverviewError('existing native attachment unavailable')
        evidence = self.observe(managed_agent_id, freshness=30, timeout=min(timeout/2, 60))
        if not evidence.get('fresh') or evidence.get('state') == 'disconnected':
            raise OverviewError('fresh exact conversation evidence required')
        snapshot = self.session_source(timeout/2)
        if not snapshot.get('complete'):
            raise OverviewError('partial attachment inventory')
        row = resolve(snapshot, 'thread:'+agent['conversation_id'])
        panes = row['attachments']
        if row['cwd'] != agent['root'] or len(panes) != 1 or row['binding_status'] != 'metadata_matched':
            raise OverviewError('attachment identity ambiguous or changed')
        pane = panes[0]
        process = agent.get('process') or {}
        from .process import process_identity
        current = process_identity(pane.get('client_pid'))
        if (not current or pane.get('client_pid') != process.get('pid')
                or pane.get('client_start_time_ticks') != process.get('start_ticks')
                or current.get('start_time_ticks') != process.get('start_ticks')
                or current.get('boot_id') != process.get('boot_id')):
            raise OverviewError('attachment process changed')
        if not all(pane.get(k) for k in ('pane_id','window_id','session_id','socket')):
            raise OverviewError('attachment host identity incomplete')
        socket = Path(pane['socket'])
        info = socket.lstat()
        if not socket.is_absolute() or socket != socket.resolve() or not stat.S_ISSOCK(info.st_mode) or info.st_uid != os.geteuid():
            raise OverviewError('attachment socket unqualified')
        return agent, dict(pane,socket_device=info.st_dev,socket_inode=info.st_ino)

    def navigation_plan(self, managed_agent_id, *, timeout=10):
        agent, pane = self._attachment(managed_agent_id, timeout)
        return dict(status='navigation_plan', managed_agent_id=managed_agent_id,
                    runtime=agent['runtime'], conversation_id=agent['conversation_id'],
                    attachment={k:pane[k] for k in ('pane_id','window_id','session_id')},
                    grants_operations=False)

    def focus(self, managed_agent_id, *, principal, timeout=10, client=None):
        _bound(timeout, .1, 30)
        if not isinstance(principal, Principal) or principal.role != 'operator':
            raise OverviewError('verified operator required')
        if not PermissionStore(self.root).active():
            raise OverviewError('current common permission policy required')
        deadline = self.clock()+timeout
        agent, pane = self._attachment(managed_agent_id, timeout)
                # Repeat exact conversation and all host attachment coordinates, not tab position.
        remaining = deadline-self.clock()
        if remaining < .1:
            raise OverviewError('navigation deadline exhausted')
        _, latest = self._attachment(managed_agent_id, remaining)
        keys = ('socket','pane_id','window_id','session_id','client_pid','client_start_time_ticks','socket_device','socket_inode')
        if any(pane[k] != latest[k] for k in keys):
            raise OverviewError('attachment changed before focus')
        remaining=deadline-self.clock()
        if remaining <= 0:
            raise OverviewError('navigation deadline exhausted')
        client_tty,client_pid=self._client(pane['socket'],client,remaining)
        from .process import process_identity
        client_generation=process_identity(client_pid)
        if not client_generation:
            raise OverviewError('client process unavailable')
        remaining=deadline-self.clock()
        if remaining <= 0:
            raise OverviewError('navigation deadline exhausted')
        if self._client(pane['socket'],client_tty,remaining) != (client_tty,client_pid) or process_identity(client_pid)!=client_generation:
            raise OverviewError('client changed before focus')
        remaining=deadline-self.clock()
        if remaining <= 0:
            raise OverviewError('navigation deadline exhausted')
        check_operation(self.root, 'workspace.navigate', principal,
                        target=agent['conversation_id'], capability='verified_operator', readiness='exact_existing_attachment')
        subprocess.run(['tmux','-S',pane['socket'],'switch-client','-c',client_tty,'-t',pane['session_id'],
                        ';','select-window','-t',pane['window_id'],
                        ';','select-pane','-t',pane['pane_id']], check=True,
                       capture_output=True, timeout=remaining)
        return dict(status='focused', managed_agent_id=managed_agent_id, client=client_tty,
                    attachment={k:pane[k] for k in ('pane_id','window_id','session_id')})
