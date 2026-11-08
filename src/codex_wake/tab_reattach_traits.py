"""Bounded projection of verified WSL clients onto Windows presentation traits."""
from __future__ import annotations

import copy
import subprocess
import threading
import time

from .process import process_identity
from .tab_traits import TabTraits

_OVERRIDES=('harness','build','account','repository','session_presence','activity','health')


def observe_managed(owner,workspace,window,existing_evidence,deadline):
    """Return unchanged evidence unless one exact managed WSL binding verifies.

    The caller shares one monotonic deadline across its entire observation. At
    most two managed windows are probed within that owner/deadline interval,
    each receiving at most two seconds. No workers, background retries or native
    Windows PIDs enter Linux process observation. Existing Windows process/pane
    identity and visible-screen error evidence remain authoritative.
    """
    if (not window.get('attach_intent') or len(window.get('panes',[]))!=1
            or window['panes'][0].get('platform')!='windows'
            or not isinstance(existing_evidence,dict) or time.monotonic()>=deadline-.1):
        return existing_evidence
    budget=owner.__dict__.setdefault('_managed_traits_budget',dict(lock=threading.Lock(),until=0,count=0))
    with budget['lock']:
        if time.monotonic()>=budget['until']:
            budget.update(until=deadline,count=0)
        if budget['count']>=2:return existing_evidence
        budget['count']+=1
    bounded=min(deadline,time.monotonic()+2)
    try:
        binding=owner.binding_for(workspace,window,deadline=bounded)
        if (not binding or binding.get('provenance')!='verified_managed_reattachment'
                or time.monotonic()>=bounded):return existing_evidence
        process=binding['process'];identity=binding['identity'];row=copy.deepcopy(binding['native_row'])
        actual=process_identity(process['pid'])
        if (actual!={k:v for k,v in process.items() if k!='pid'}
                or identity.get('runtime')!='codex' or not identity.get('namespace')
                or not identity.get('conversation_id')):return existing_evidence
        health=binding['health']['observation']
        if health.get('responsive') is not True or health.get('evidence')!='tui_main_loop_ack':
            return existing_evidence
        pane_id=window['panes'][0]['pane_id']
        linux=dict(pid=process['pid'],start_ticks=process['start_time_ticks'],boot_id=process.get('boot_id'))
        row['attachments']=[dict(pane_id=pane_id,client_pid=linux['pid'],client_start_time_ticks=linux['start_ticks'])]
        target=row['target'];target.update(provider='codex',conversation_id=identity['conversation_id'])
        state=row.get('runtime_state','unknown')
        if state=='active' and row.get('active_flags'):
            state='awaiting-human' if set(row['active_flags'])<={'waitingOnApproval','waitingOnUserInput'} else 'unknown'
        state={'active':'working','idle':'ready','not_loaded':'disconnected'}.get(state,state)
        sample=dict(runtime='codex',namespace=identity['namespace'],conversation_id=identity['conversation_id'],
                    account=target.get('account'),root=row.get('cwd'),state=state,process=linux,
                    observed_at=time.time(),fresh=True,source='verified_managed_reattachment')
        def processes(pid,probe_deadline):
            if pid!=linux['pid'] or time.monotonic()>=min(probe_deadline,bounded):return [],False
            return [dict(pid=pid,process=linux,executable=target['executable'],argv=[],cwd=row.get('cwd'))],True
        traits=TabTraits(owner.root,sessions=[row],process_probe=processes,
                         health_probe=lambda *args,**kwargs:binding['health'])
        observed=traits.observe_window(dict(panes=[dict(pane_id=pane_id,pid=linux['pid'])]),
                                       evidence={pane_id:sample},deadline=bounded)
        if time.monotonic()>=bounded:return existing_evidence
        result=copy.deepcopy(existing_evidence)
        panes=[p for p in result.get('panes',[]) if p.get('pane_id')==pane_id]
        if len(panes)!=1:return existing_evidence
        projected=observed['panes'][0]
        for key in _OVERRIDES:
            panes[0]['traits'][key]=projected['traits'][key]
            result['traits'][key]=observed['traits'][key]
        # The existing Windows process identity remains in processes; the
        # separate binding explicitly carries Linux namespace provenance.
        panes[0]['binding']=projected['binding']
        panes[0]['managed_process']=dict(process,platform='wsl')
        result['managed_projection']='verified_managed_reattachment'
        return result
    except (OSError,ValueError,KeyError,TypeError,TimeoutError,subprocess.SubprocessError):
        return existing_evidence
