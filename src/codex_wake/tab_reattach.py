"""Verified same-conversation presentation replacement; never transfers a process.

The shared ControllerRuntime owns operation admission/replay. Existing layout
plans retain source/destination custody and the one attempted launch, including
uncertainty. Native account history and resource records are never copied.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import pwd
import re
import shlex
import socket
import stat
import subprocess
import sys
import time
import uuid

from .agent_resume import SavedRuntime
from .managed_inventory import InventoryError
from .process import process_identity
from .shortcut_store import locked, read, write
from .tab_lifecycle import TabLifecycle
from .tab_organization import TabOrganization, digest


def _sha(path):
    value=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1048576),b''):value.update(block)
    return value.hexdigest()


class TabReattach:
    ARGUMENTS={
        'tabs.reattach-preview':{'workspace','expected_target','window','destination','expected_destination','force','retire_source'},
        'tabs.reattach-apply':{'plan_id','expected_target'},'tabs.reattach-status':{'plan_id','expected_target'},
    }

    def __init__(self,root,*,workspaces,host,environment,runtime=None):
        self.root=Path(root)
        self.workspaces=dict(workspaces)
        self.lifecycle=TabLifecycle(root,workspaces=workspaces,host=host,environment=environment)
        self.records=TabOrganization(root,transport=None)
        self.runtime=runtime or NativeReattachRuntime(root,workspaces=workspaces,host=host,environment=environment)

    @staticmethod
    def _public(plan,*,replayed=False):
        return dict(status=plan['state'],plan_id=plan['plan_id'],target=dict(plan['before'],reattach_plan=plan['plan_id']),identity=plan['source']['identity'],
                    source_preserved=(None if plan.get('retirement_attempted') and plan['state']!='applied' else not bool(plan.get('retirement'))),
                    source_retired=bool(plan.get('retirement')),source_retirement=('verified' if plan.get('retirement') else 'uncertain' if plan.get('retirement_attempted') else 'retained'),destination=plan.get('verified'),
                    reason=plan.get('reason'),replayed=replayed,launch_attempts=plan.get('launch_attempts',0))

    def execute(self,operation,arguments):
        if operation not in self.ARGUMENTS or not isinstance(arguments,dict) or set(arguments)-self.ARGUMENTS[operation]:
            raise InventoryError('invalid_argument','Unsupported exact-conversation reattachment request.')
        if operation=='tabs.reattach-preview':return self._preview(arguments)
        with locked(self.root/'tab-reattach-control'):
            plan=self.records.read(arguments.get('plan_id'))
            if plan.get('kind')!='reattach':raise InventoryError('invalid_argument','Not a reattachment plan.')
            expected=arguments.get('expected_target')
            if expected is not None and expected!=self._public(plan)['target']:
                raise InventoryError('stale_target','Pinned reattachment plan target changed.')
            if operation=='tabs.reattach-status':return self._public(plan)
            return self._apply(plan)

    def binding_for(self,workspace,window):
        if not hasattr(self.runtime,'binding_for'):return None
        return self.runtime.binding_for(workspace,window)

    def authorization_targets(self,plan_id):
        plan=self.records.read(plan_id)
        if plan.get('kind')!='reattach':raise InventoryError('invalid_argument','Not a reattachment plan.')
        return [plan['before'],plan['before_destination']]

    def _preview(self,args):
        if any(key in args and type(args[key]) is not bool for key in ('force','retire_source')):
            raise InventoryError('invalid_argument','force must be Boolean.')
        before=self.lifecycle.inspect(args.get('workspace'))
        destination=self.lifecycle.inspect(args.get('destination'))
        if args.get('expected_target')!=before['target'] or args.get('expected_destination')!=destination['target']:
            raise InventoryError('stale_target','Exact current source and destination generations required.')
        if args['workspace']==args['destination']:
            raise InventoryError('invalid_argument','Select a different destination workspace.')
        window=self.lifecycle._window(before['snapshot'],args.get('window'))
        if len(window['panes'])!=1 or window.get('linked'):
            return dict(status='unsupported',reason='single_exact_unlinked_conversation_required',source_preserved=True)
        source=self.runtime.capture(args['workspace'],window)
        if source.get('identity',{}).get('runtime')!='codex':
            return dict(status='unsupported',reason='runtime_exact_reattachment_unqualified',source_preserved=True)
        if source.get('pending_work') or source.get('state')!='idle' or source.get('health',{}).get('evidence')!='tui_main_loop_ack' or source['health'].get('responsive') is not True:
            return dict(status='held',reason='source_idle_and_exact_tui_health_required',source_preserved=True)
        if not self.runtime.supports(args['destination'],source):
            return dict(status='unsupported',reason='destination_exact_reattachment_unqualified',source_preserved=True)
        if args.get('retire_source') and not self._input_safe(source):
            return dict(status='held',reason='source_input_custody_unknown_or_nonempty',source_preserved=True)
        if args.get('retire_source') and window.get('focused') and not args.get('force'):
            return dict(status='held',reason='source_focused_explicit_force_required',source_preserved=True)
        identifier='plan_'+uuid.uuid4().hex
        plan=dict(version=1,kind='reattach',plan_id=identifier,state='ready',reason=None,
            workspace=args['workspace'],destination=args['destination'],before=before['target'],
            before_destination=destination['target'],window=window,source=source,
            source_sha256=digest(source['identity'] | {'profile':source['profile'],'process':source['process']}),
            force=bool(args.get('force')),retire_source=bool(args.get('retire_source')),name='reattach-'+identifier[5:21],launch_attempts=0)
        self.records.save(identifier,plan)
        return self._public(plan)

    @staticmethod
    def _input_safe(source):
        safety=source.get('ui_safety',{})
        return (safety.get('controller_owned') is True and safety.get('known_empty') is True
                and safety.get('private_input') is False and safety.get('queue_empty') is True
                and safety.get('process')==source.get('process')
                and 0<=time.time()-safety.get('observed_at',0)<=2)

    def _source_guard(self,plan):
        before=self.lifecycle.inspect(plan['workspace'])
        window=self.lifecycle._window(before['snapshot'],plan['window']['window_id'])
        if before['target']!=plan['before'] or window['panes']!=plan['window']['panes']:
            raise InventoryError('stale_target','Source layout or process generation changed; source retained.')
        current=self.runtime.capture(plan['workspace'],window)
        if (digest(current['identity'] | {'profile':current['profile'],'process':current['process']})!=plan['source_sha256']
                or current.get('pending_work') or current.get('state')!='idle' or current.get('health',{}).get('responsive') is not True
                or current['health'].get('evidence')!='tui_main_loop_ack'):
            raise InventoryError('stale_target','Source native conversation/account/health changed; source retained.')
        if plan.get('retire_source') and not self._input_safe(current):
            raise InventoryError('source_input_custody_unknown_or_nonempty','Source input safety is unknown or nonempty; source retained.')
        return before

    def _apply(self,plan):
        if plan['state']=='applied':return self._public(plan,replayed=True)
        if plan['state'] not in ('ready',):return self._public(plan,replayed=True)
        # An unresolved prior launch for this conversation fences differently
        # keyed plans as well as ordinary ControllerRuntime retries.
        deadline=time.monotonic()+5
        for count,path in enumerate(self.records.directory.glob('plan_*.json')):
            if count>=4096 or time.monotonic()>deadline:
                raise InventoryError('capacity','Reattachment custody inventory exceeds its bound.')
            if path.stem==plan['plan_id']:continue
            other=self.records.read(path.stem)
            if (other.get('kind')=='reattach' and other.get('source',{}).get('identity')==plan['source']['identity']
                    and other.get('state') in ('launching','uncertain','destination_verified','retiring_source')):
                raise InventoryError('reattach_original_plan_required','Reconcile the original uncertain launch; no duplicate client will be created.')
        self._source_guard(plan)
        if self.lifecycle.inspect(plan['destination'])['target']!=plan['before_destination']:
            raise InventoryError('stale_target','Destination changed before launch; source retained.')
        plan.update(state='launching',launch_attempts=1)
        self.records.save(plan['plan_id'],plan)
        try:
            handle=self.runtime.launch(plan,lambda:self._source_guard(plan))
            plan['launch_handle']=handle
            self.records.save(plan['plan_id'],plan)
            verified=self.runtime.verify(plan,handle)
            if (verified.get('identity')!=plan['source']['identity']
                    or verified.get('health',{}).get('responsive') is not True
                    or verified['health'].get('evidence')!='tui_main_loop_ack'):
                plan.update(state='uncertain',reason='destination_same_conversation_health_not_verified')
                self.records.save(plan['plan_id'],plan)
                return self._public(plan)
            plan.update(state='destination_verified',verified=verified)
            self.records.save(plan['plan_id'],plan)
            if not plan.get('retire_source'):
                plan.update(state='applied',reason='source_retained_by_request')
                self.records.save(plan['plan_id'],plan)
                return self._public(plan)
            before=self._source_guard(plan)
            plan.update(state='retiring_source',retirement_attempted=True)
            self.records.save(plan['plan_id'],plan)
            result=self.lifecycle.execute('tabs.close',dict(workspace=plan['workspace'],expected_target=before['target'],
                window=plan['window']['window_id'],force=plan['force']))
            if result['status']!='applied':raise InventoryError('effect_uncertain','Source retirement is not verified.')
            plan.update(state='applied',reason=None,retirement=result)
            self.records.save(plan['plan_id'],plan)
            return self._public(plan)
        except Exception as error:
            plan.update(state='uncertain',reason=getattr(error,'code','launch_or_retirement_outcome_uncertain'),reason_details=str(error)[:1024])
            self.records.save(plan['plan_id'],plan)
            return self._public(plan)


class NativeReattachRuntime:
    def __init__(self,root,*,workspaces,host,environment):
        self.root=Path(root)
        self.workspaces=workspaces
        self.host,self.environment=host,environment

    def capture(self,workspace,window):
        from .local_sessions import discover
        from .tab_traits import _processes
        config=self.workspaces[workspace]
        if config['kind'] not in ('tmux','byobu'):
            raise InventoryError('unsupported_target','Native source association for this presentation is not qualified.')
        transport=config['transport']
        view=discover(self.root,endpoint=config.get('app_server','unix://'),socket_path=transport.socket)
        panes={p['pane_id'] for p in window['panes']}
        rows=[row for row in view['sessions'] if any(a.get('pane_id') in panes and a.get('window_id')==window['window_id'] for a in row.get('attachments',[]))]
        if len(rows)!=1:raise InventoryError('ambiguous_target','Source must identify one exact native conversation.')
        row=rows[0];target=row['target']
        profile=dict(cwd=row['cwd'],app_server=row['endpoint'],codex_path=target['executable'],
            codex_home=target['home'],timeout=10,codex_sha256=target['build_sha256'],
            execution_uid=os.getuid(),wake_python=config.get('wake_python',sys.executable),wsl_distribution=os.environ.get('WSL_DISTRO_NAME'),
            execution_host=self.host,execution_environment=self.environment)
        home=Path(profile['codex_home']);h=home.stat()
        profile['home_generation']=[h.st_dev,h.st_ino]
        endpoint=Path(profile['app_server'][7:]).stat()
        profile['endpoint_generation']=[endpoint.st_dev,endpoint.st_ino]
        profile['daemon_process']=target['process']
        identity=SavedRuntime().identity({'conversation_id':row['thread_id']},profile)
        candidates=[]
        for pane in window['panes']:
            processes,complete=_processes(pane['pid'],time.monotonic()+2)
            if not complete:raise InventoryError('source_unavailable','Source process ancestry is incomplete.')
            candidates.extend(p['pid'] for p in processes if p['executable']==str(Path(profile['codex_path']).resolve()))
        if len(set(candidates))!=1:raise InventoryError('ambiguous_target','Source native controlling process is not unique.')
        pid=candidates[0]
        health=self.health(pid,identity,profile)
        from .session_lifecycle import pending_thread_work
        work=pending_thread_work(row,self.root)
        process=dict(pid=pid,**(process_identity(pid) or {}))
        inspector=config.get('ui_safety')
        observed=inspector(identity,process) if callable(inspector) else {}
        # Persist only input-custody assertions, never composer/private-input text.
        fields=('controller_owned','known_empty','private_input','queue_empty','process','observed_at')
        safety={key:observed[key] for key in fields if key in observed}
        return dict(ui_safety=safety,pending_work=bool(work['pending'] or work['messages']),identity=identity,profile=profile,process=process,
                    state=row.get('runtime_state','unknown'),health=health['observation'])

    def health(self,pid,identity,profile):
        from .controller_health import ControllerHealth
        from .native_protocol import native_request
        actual=process_identity(pid)
        if not actual:raise InventoryError('source_unavailable','Pinned native TUI process is gone.')
        frame=native_request(profile['app_server'],profile['codex_path'],'tui/health/describe',{'pid':pid},2)
        bindings=[b for b in frame.get('bindings',[]) if b.get('pid')==pid and b.get('home')==profile['codex_home']
            and str(b.get('startTicks'))==str(actual['start_time_ticks']) and b.get('bootId')==actual.get('boot_id')]
        if len(bindings)!=1:raise InventoryError('source_unavailable','Exact native controlling TUI binding is unavailable.')
        binding=bindings[0]
        namespace='codex:'+hashlib.sha256(json.dumps([str(Path(binding['home']).resolve()),binding['provider']],separators=(',',':')).encode()).hexdigest()
        if namespace!=identity['namespace']:raise InventoryError('stale_target','Native account/provider namespace changed.')
        target=dict(host=self.host,environment=self.environment,runtime='codex',namespace=namespace,
            build_sha256=profile['codex_sha256'],conversation_id=identity['conversation_id'],home=binding['home'],
            provider=binding['provider'],backend_id=binding['backendId'],channel=binding['channel'],
            connection_generation=binding['connectionGeneration'],
            process=dict(pid=pid,start_ticks=binding['startTicks'],boot_id=binding['bootId']))
        return ControllerHealth(self.root).observe_binding(target,
            dict(target=target,endpoint=profile['app_server'],codex_cmd=[profile['codex_path']]),timeout=2)

    def binding_for(self,workspace,window):
        """Fresh managed WSL binding for a native Windows relay, no PID guessing.

        Only the retained plan, current bridge/pane birth and private child marker
        can identify a Linux PID. Raw native Windows PIDs never enter /proc.
        """
        intent=window.get('attach_intent')
        if not isinstance(intent,str) or not re.fullmatch(r'[0-9a-f]{32}',intent):return None
        records=TabOrganization(self.root,transport=None)
        try:
            plan=records.read('plan_'+intent)
            if (plan.get('kind')!='reattach' or plan.get('destination')!=workspace
                    or not plan.get('verified') or not plan.get('launch_handle')):return None
            handle=plan['launch_handle'];transport=self.workspaces[workspace]['transport']
            if handle.get('bridge_generation')!=transport.pinned_server_id or handle.get('window_id')!=window['window_id']:return None
            pane=next(p for p in window['panes'] if p['pane_id']==handle['pane_id'])
            if pane['pid']!=handle['windows_pid'] or pane['windows_creation_filetime']!=handle['windows_creation_filetime']:return None
            verified=self.verify(plan,handle)
            from .local_sessions import discover
            rows=discover(self.root,endpoint=plan['source']['profile']['app_server'])['sessions']
            row=next(r for r in rows if r['thread_id']==plan['source']['identity']['conversation_id'])
            return dict(identity=verified['identity'],process=verified['process'],native_row=row,
                        health=dict(target=verified['native_health_target'],observation=verified['health']),
                        provenance='verified_managed_reattachment',application_effects=False)
        except (ValueError,OSError,KeyError,StopIteration):return None

    def _mirror(self,destination):
        command=getattr(getattr(self.workspaces[destination]['transport'],'bridge',None),'command',[])
        if '--attach-directory' not in command:return None
        path=command[command.index('--attach-directory')+1]
        result=subprocess.run(['wslpath','-u',path],text=True,capture_output=True,check=True,timeout=2)
        return Path(result.stdout.strip())

    def supports(self,destination,source):
        config=self.workspaces[destination]
        if config['kind'] in ('tmux','byobu'):return True
        return bool(config['kind']=='psmux' and self._mirror(destination) is not None
                    and source['profile'].get('wsl_distribution') and hasattr(config['transport'],'attach_saved'))

    def launch(self,plan,guard):
        profile=plan['source']['profile'];identity=plan['source']['identity']
        launch_id=plan['plan_id'][5:]
        directory=self.root/'tab-reattach-launches'
        directory.mkdir(mode=0o700,exist_ok=True)
        manifest_path=directory/(launch_id+'.json')
        marker=directory/(launch_id+'.process.json')
        config=self.workspaces[plan['destination']]
        manifest=dict(version=1,intent=launch_id,identity=identity,profile=profile,
            marker=str(marker),wsl_manifest=str(manifest_path),window_name=plan['name'],
            execution_user=pwd.getpwuid(os.getuid()).pw_name,
            windows_destination=config['transport'].pinned_server_id if config['kind']=='psmux' else None)
        write(manifest_path,manifest)
        raw=manifest_path.read_bytes();sha=hashlib.sha256(raw).hexdigest()
        guard()
        if config['kind']=='psmux':
            mirror=self._mirror(plan['destination']);mirror.mkdir(parents=True,exist_ok=True)
            mirrored=mirror/(launch_id+'.json');mirrored.write_bytes(raw)
            result=config['transport'].attach_saved(launch_id,sha,time.monotonic()+15)
            return dict(**result,marker=str(marker),manifest=str(manifest_path),manifest_sha256=sha)
        from .session_lifecycle import tmux_command
        wrapper=shlex.join([profile['wake_python'],'-m','codex_wake.tab_reattach','--launch-child',str(manifest_path),'--manifest-sha',sha])
        def terminal(args,*command,**kwargs):
            command=list(command)
            if command[0]=='new-window':command[-1]=wrapper
            return tmux_command(args,*command,**kwargs)
        target=dict(profile,tmux_socket=config['transport'].socket,tmux_session=config['transport'].session)
        result=SavedRuntime(terminal=terminal).launch(identity,target,guard,plan['name'])
        window,pane=result.split('\t')
        return dict(window_id=window,pane_id=pane,marker=str(marker),manifest=str(manifest_path),manifest_sha256=sha)

    def verify(self,plan,handle):
        deadline=time.monotonic()+15
        profile=plan['source']['profile'];identity=plan['source']['identity']
        while time.monotonic()<deadline:
            try:
                marker=read(Path(handle['marker']))
                if marker.get('intent')!=plan['plan_id'][5:] or marker.get('identity')!=identity:
                    raise InventoryError('stale_target','Destination launch marker identity mismatch.')
                pid=marker['process']['pid'];actual=process_identity(pid)
                if actual!={k:v for k,v in marker['process'].items() if k!='pid'} or pid==plan['source']['process']['pid']:
                    raise InventoryError('stale_target','Destination native process generation is not distinct and live.')
                if str(Path('/proc',str(pid),'exe').resolve())!=str(Path(profile['codex_path']).resolve()):
                    raise FileNotFoundError('native exec not ready')
                if SavedRuntime().identity(identity,profile)!=identity:
                    raise InventoryError('stale_target','Destination saved conversation identity changed.')
                health=self.health(pid,identity,profile)
                config=self.workspaces[plan['destination']]
                snapshot=config['transport'].snapshot(time.monotonic()+5)
                window=next(w for w in snapshot['windows'] if w['window_id']==handle['window_id'])
                if config['kind']=='psmux':
                    pane=next(p for p in window['panes'] if p['pane_id']==handle['pane_id'])
                    if pane['pid']!=handle['windows_pid'] or pane['windows_creation_filetime']!=handle['windows_creation_filetime']:
                        raise InventoryError('stale_target','Windows destination process generation changed.')
                if health['observation'].get('responsive'):
                    return dict(identity=identity,process=marker['process'],handle=handle,
                        window=window,health=health['observation'],native_health_target=health['target'])
            except (FileNotFoundError,KeyError,StopIteration):pass
            except InventoryError as error:
                if error.code!='source_unavailable':raise
            time.sleep(.05)
        raise InventoryError('destination_unverified','Destination native attachment did not verify; source retained.')


def launch_child(path,expected_sha):
    """Host-selected WSL child: privately witness this PID, then native exec."""
    path=Path(path)
    info=path.lstat()
    if path.is_symlink() or info.st_uid!=os.getuid() or stat.S_IMODE(info.st_mode)&0o077 or _sha(path)!=expected_sha:
        raise InventoryError('unauthorized_target','Private launch manifest/hash mismatch.')
    manifest=read(path);profile=manifest['profile'];identity=manifest['identity']
    home=Path(profile['codex_home']);native=Path(profile['codex_path'])
    h=home.stat()
    endpoint=Path(profile['app_server'][7:]).stat()
    daemon=profile['daemon_process']
    current_daemon=process_identity(daemon['pid'])
    if (not current_daemon or str(current_daemon['start_time_ticks'])!=str(daemon['start_ticks'])
            or current_daemon.get('boot_id')!=daemon['boot_id'] or endpoint.st_uid!=os.getuid()
            or [endpoint.st_dev,endpoint.st_ino]!=profile['endpoint_generation']
            or not stat.S_ISSOCK(endpoint.st_mode)):
        raise InventoryError('stale_target','Native endpoint execution-owner generation changed.')
    if (profile['execution_uid']!=os.getuid() or home.is_symlink() or h.st_uid!=os.getuid()
            or [h.st_dev,h.st_ino]!=profile['home_generation'] or _sha(native)!=profile['codex_sha256']
            or SavedRuntime().identity(identity,profile)!=identity):
        raise InventoryError('stale_target','Exact saved account/build/execution ownership changed.')
    marker=dict(version=1,intent=manifest['intent'],identity=identity,
                process=dict(pid=os.getpid(),**(process_identity(os.getpid()) or {})))
    write(Path(manifest['marker']),marker)
    environment=dict(os.environ,CODEX_HOME=str(home),CODEX_WAKE_ATTACHMENT_ID=manifest['intent'])
    for key in ('CODEX_THREAD_ID','CODEX_TURN_ID','CODEX_SESSION_ID','TMUX_PANE'):environment.pop(key,None)
    argv=[str(native),'resume','--no-alt-screen','-C',identity['root'],identity['conversation_id'],'--remote',profile['app_server']]
    os.execve(native,argv,environment)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--launch-child',type=Path,required=True)
    parser.add_argument('--manifest-sha',required=True)
    args=parser.parse_args(argv)
    launch_child(args.launch_child,args.manifest_sha)


if __name__=='__main__':main()
