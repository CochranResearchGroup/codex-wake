"""Durable whole-workspace exact-conversation capture and operator restoration.

Snapshots retain supported launch profiles and logical terminal markers, never
shell restart commands or private history contents. Legacy layouts without an
exact captured binding stay unknown; old tmux IDs, names and CWD are not proof.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time
from uuid import uuid4

from .agent_resume import SavedRuntime, fingerprint
from .goal_supervision import _save, _private
from .managed_inventory import InventoryError
from .tab_monitor import _lock

_MARKER='@codex-wake-recovery-id'
_LIMIT=1048576


def _key(value):
    if not isinstance(value,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}',value):
        raise InventoryError('invalid_argument','A bounded capture or recovery intent identifier is required.')
    return value


def _load(path):
    _private(path)
    with path.open('rb') as stream:raw=stream.read(_LIMIT+1)
    if len(raw)>_LIMIT:raise InventoryError('recovery_capacity','Workspace recovery record exceeds1MiB.')
    value=json.loads(raw)
    if not isinstance(value,dict) or value.get('schema_version')!=1:
        raise InventoryError('recovery_state_unavailable','Unsupported workspace recovery record.')
    return value


class WorkspaceRecoveryRuntime:
    """Reuse native identity/resume and host terminal owners without enrollment."""
    def __init__(self,root,tabs=None):
        self.root=Path(root);self.tabs=tabs;self.saved=SavedRuntime()

    def _tabs(self):
        if self.tabs is not None:return self.tabs
        from .controller_tabs import controller_tabs_from_root
        return controller_tabs_from_root(self.root)

    def context(self,workspace):
        tabs=self._tabs()
        if workspace not in tabs.workspaces:
            raise InventoryError('unsupported_target','Selected restored workspace is not available.')
        config=tabs.workspaces[workspace]
        if config['kind'] not in ('byobu','tmux'):
            raise InventoryError('unsupported_target','Exact workspace recovery currently requires Byobu/tmux.')
        transport=config['transport'];deadline=time.monotonic()+5
        view=transport.snapshot(deadline)
        windows=[]
        for window in view['windows']:
            try:logical=transport.command(deadline,'show-options','-w','-v','-t',window['window_id'],_MARKER).strip()
            except subprocess.CalledProcessError:logical=None
            windows.append(dict(window,logical_id=logical))
        identity=fingerprint({k:view[k] for k in ('server','session_id','socket_identity')})
        return dict(workspace=workspace,identity=identity,windows=windows,
                    socket_path=transport.socket,session_id=transport.session)

    def _rows(self,context,endpoint=None):
        from .tab_traits import session_rows
        return session_rows(self.root,socket_path=context['socket_path'],
                            endpoints=[endpoint] if endpoint else (),deadline=time.monotonic()+3)

    def capture(self,context):
        from .tab_traits import TabTraits
        from .local_health import observe_row
        view=self._rows(context);records={}
        for window in context['windows']:
            observation=TabTraits(self.root,sessions=view['sessions']).observe_window(window,deadline=time.monotonic()+3)
            coding=[pane for pane in observation['panes'] if pane['traits']['harness']['value'] in ('codex','grok','mixed')]
            if not coding:
                records[window['window_id']]=dict(kind='noncoding')
                continue
            if len(window['panes'])!=1 or len(coding)!=1 or coding[0]['traits']['harness']['value']!='codex':
                records[window['window_id']]=dict(kind='unsupported',reason='mixed_or_unsupported_runtime')
                continue
            matches=[row for row in view['sessions'] if any(attachment['pane_id']==window['panes'][0]['pane_id']
                      for attachment in row.get('attachments',[]))]
            if len(matches)!=1:
                records[window['window_id']]=dict(kind='unsupported',reason='exact_live_binding_unavailable')
                continue
            row=matches[0];target=row['target']
            from .process import process_identity
            attachment=next((a for a in row.get('attachments',[]) if a['pane_id']==window['panes'][0]['pane_id']),None)
            current=process_identity(attachment.get('client_pid')) if attachment else None
            if current is None or str(current['start_time_ticks'])!=str(attachment.get('client_start_time_ticks')):
                records[window['window_id']]=dict(kind='unsupported',reason='exact_client_process_changed')
                continue
            client=dict(pid=attachment['client_pid'],start_ticks=current['start_time_ticks'],boot_id=current['boot_id'])
            health=observe_row(self.root,row,timeout=1,client_process=client)
            if not health['observation'].get('responsive') or health['observation'].get('evidence')!='tui_main_loop_ack':
                records[window['window_id']]=dict(kind='unsupported',reason='exact_tui_binding_unqualified')
                continue
            profile=dict(cwd=row['cwd'],app_server=row['endpoint'],codex_path=target['executable'],codex_home=target['home'],timeout=2)
            identity=self.saved.identity(dict(conversation_id=row['thread_id']),profile)
            records[window['window_id']]=dict(kind='codex',identity=identity,profile=profile,
                native={k:target[k] for k in ('account','home','home_generation','build_sha256')})
        return records

    def mark(self,context,window,logical_id):
        config=self._tabs().workspaces[context['workspace']]
        config['transport'].command(time.monotonic()+3,'set-option','-w','-t',window,_MARKER,logical_id)

    def _profile(self,record,context):
        return dict(record['profile'],tmux_socket=context['socket_path'],tmux_session=context['session_id'])

    def identity(self,record,context):
        from .tab_traits import _image_digest
        home=Path(record['native']['home']);info=home.stat()
        if f'{info.st_dev}:{info.st_ino}'!=record['native']['home_generation']:
            raise InventoryError('recovery_home_changed','Saved native home identity changed; no account substitution is allowed.')
        if _image_digest(Path(record['profile']['codex_path']),time.monotonic()+2)!=record['native']['build_sha256']:
            raise InventoryError('recovery_build_changed','Saved immutable native build is missing or changed.')
        return self.saved.identity(record['identity'],self._profile(record,context))

    def binding(self,record,context):
        from .local_health import observe_row
        view=self._rows(context,record['profile']['app_server'])
        matches=[row for row in view['sessions'] if row['thread_id']==record['identity']['conversation_id']]
        if len(matches)>1:return dict(state='ambiguous')
        attachments=matches[0].get('attachments',[]) if matches else []
        if len(attachments)>1:return dict(state='ambiguous')
        if attachments:
            probe=observe_row(self.root,matches[0],timeout=1)
            if probe['observation'].get('responsive') and probe['observation'].get('evidence')=='tui_main_loop_ack':
                return dict(state='ready',window_id=attachments[0]['window_id'],pane_id=attachments[0]['pane_id'])
            return dict(state='unknown',reason='native_attachment_not_yet_verified')
        if view['status']!='complete':return dict(state='unknown',reason='native_inventory_partial')
        # A native thread read already verified the exact saved history. Absence
        # means no qualified attachment, not permission to overwrite any shell.
        return dict(state='absent')

    def launch(self,record,context,guard):
        profile=self._profile(record,context)
        value=self.saved.launch(record['identity'],profile,guard,record['name'])
        window,pane=value.strip().split('\t')
        fresh=self.context(context['workspace'])
        if fresh['identity']!=context['identity']:
            raise InventoryError('stale_target','Restore server changed after launching; reconcile the created attachment.')
        created=next((row for row in fresh['windows'] if row['window_id']==window),None)
        if created is None:raise InventoryError('recovery_uncertain','Created attachment is not observable.')
        if created['index']!=record['index']:
            if any(row['window_id']!=window and row['index']==record['index'] for row in fresh['windows']):
                raise InventoryError('placement_conflict','Original position was occupied during recovery; preserve the created attachment.')
            self._tabs().workspaces[context['workspace']]['transport'].command(time.monotonic()+3,
                'move-window','-d','-s',window,'-t',context['session_id']+':'+str(record['index']))
        return dict(window_id=window,pane_id=pane)


class TabRecovery:
    ARGUMENTS={'tabs.recovery.capture':{'workspace','capture_id'},
               'tabs.recovery.preview':{'capture_id','workspace','restore_layout'},
               'tabs.recovery.apply':{'capture_id','workspace','restore_layout','intent','expected_target'},
               'tabs.recovery.status':{'capture_id','intent'}}

    def __init__(self,root,*,tabs=None,runtime=None):
        self.root=Path(root).resolve();self.root.mkdir(parents=True,exist_ok=True,mode=0o700);_private(self.root,True)
        self.directory=self.root/'tab-recovery';self.directory.mkdir(mode=0o700,exist_ok=True);_private(self.directory,True)
        self.runtime=runtime or WorkspaceRecoveryRuntime(self.root,tabs)

    def execute(self,operation,arguments):
        if operation not in self.ARGUMENTS:raise InventoryError('unsupported_operation','Unsupported workspace recovery operation.')
        if not isinstance(arguments,dict) or set(arguments)-self.ARGUMENTS[operation]:
            raise InventoryError('invalid_argument','Unsupported workspace recovery arguments.')
        if 'restore_layout' in arguments and type(arguments['restore_layout']) is not bool:
            raise InventoryError('invalid_argument','restore_layout must be Boolean.')
        if operation=='tabs.recovery.status':return self.status(arguments)
        workspace=arguments.get('workspace')
        if not isinstance(workspace,str) or not workspace or len(workspace)>256:
            raise InventoryError('invalid_argument','One exact available workspace is required.')
        if operation=='tabs.recovery.capture':return self.capture(workspace,arguments.get('capture_id'))
        capture_id=_key(arguments.get('capture_id'))
        if operation=='tabs.recovery.preview':return self.preview(capture_id,workspace,arguments.get('restore_layout',False))
        return self.apply(capture_id,workspace,arguments)

    def _path(self,capture_id):return self.directory/('capture-'+_key(capture_id)+'.json')

    def capture(self,workspace,capture_id=None):
        capture_id=_key(capture_id or uuid4().hex)
        with _lock(self.directory/'capture.lock'):
            path=self._path(capture_id)
            if path.exists():
                saved=_load(path)
                if saved['workspace']!=workspace:raise InventoryError('recovery_capture_conflict','Capture identity belongs to another workspace.')
                return dict(status='captured',capture_id=capture_id,snapshot=saved,replayed=True)
            context=self.runtime.context(workspace)
            if len(context['windows'])>256:raise InventoryError('recovery_capacity','Capture exceeds256windows.')
            identities=self.runtime.capture(context);rows=[];markers=set()
            for window in context['windows']:
                marker=window.get('logical_id') or uuid4().hex
                if marker in markers:raise InventoryError('recovery_marker_conflict','Logical marker is present on multiple windows.')
                markers.add(marker)
                data=identities.get(window['window_id'],dict(kind='unsupported',reason='binding_unknown'))
                rows.append(dict(data,logical_id=marker,name=window['name'],index=window['index'],
                                 original_window=window['window_id'],original_panes=[p['pane_id'] for p in window['panes']]))
            # Persist intent before setting non-input metadata markers. A crash
            # leaves the immutable capture available, never arbitrary shell argv.
            snapshot=dict(schema_version=1,capture_id=capture_id,workspace=workspace,captured_at=time.time(),
                          source_identity=context['identity'],rows=rows)
            if len(json.dumps(snapshot).encode())>_LIMIT:raise InventoryError('recovery_capacity','Capture exceeds1MiB.')
            _save(path,snapshot)
            for row in rows:
                self.runtime.mark(context,row['original_window'],row['logical_id'])
            return dict(status='captured',capture_id=capture_id,snapshot=snapshot,replayed=False)

    def _preview(self,snapshot,context,restore_layout):
        rows=[]
        for saved in snapshot['rows']:
            row=dict(logical_id=saved['logical_id'],name=saved['name'],kind=saved['kind'])
            if saved['kind']=='noncoding':
                rows.append(dict(row,status='preserved',reason='noncoding_commands_not_replayed'));continue
            if saved['kind']!='codex':
                rows.append(dict(row,status='held',reason=saved.get('reason','binding_unknown')));continue
            row.update(conversation_id=saved['identity']['conversation_id'],namespace=saved['identity']['namespace'])
            try:
                if self.runtime.identity(saved,context)!=saved['identity']:
                    rows.append(dict(row,status='held',reason='native_identity_changed'));continue
                marked=[w for w in context['windows'] if w.get('logical_id')==saved['logical_id']]
                binding=self.runtime.binding(saved,context)
                if len(marked)>1 or binding['state']=='ambiguous':
                    rows.append(dict(row,status='held',reason='binding_ambiguous'));continue
                if binding['state']=='ready':
                    target=next((w for w in context['windows'] if w['window_id']==binding.get('window_id')),None)
                    if target is None or (marked and target['window_id']!=marked[0]['window_id']):
                        rows.append(dict(row,status='held',reason='conversation_attached_elsewhere'));continue
                    rows.append(dict(row,status='already_attached',window_id=target['window_id']));continue
                if marked:
                    rows.append(dict(row,status='held',reason='existing_marked_slot_unqualified'));continue
                if binding['state']!='absent':
                    rows.append(dict(row,status='held',reason=binding.get('reason','attachment_unknown')));continue
                if any(w['name']==saved['name'] or w['index']==saved['index'] for w in context['windows']):
                    rows.append(dict(row,status='held',reason='unmarked_placement_conflict'));continue
                rows.append(dict(row,status='restoreable' if restore_layout else 'held',reason=None if restore_layout else 'explicit_layout_restore_required'))
            except (OSError,ValueError,KeyError,InventoryError) as error:
                rows.append(dict(row,status='held',reason=getattr(error,'code','native_history_unavailable')))
        return rows

    def preview(self,capture_id,workspace,restore_layout=False):
        snapshot=_load(self._path(capture_id));context=self.runtime.context(workspace)
        rows=self._preview(snapshot,context,restore_layout)
        target=dict(capture_id=capture_id,capture_sha256=fingerprint(snapshot),workspace=workspace,
                    workspace_identity=context['identity'],presentation_generation=fingerprint(context['windows']))
        return dict(status='held' if any(row['status']=='held' for row in rows) else 'ready',target=target,rows=rows,application_effects=False)

    def apply(self,capture_id,workspace,arguments):
        intent=_key(arguments.get('intent'));receipt_path=self.directory/('restore-'+fingerprint(intent)+'.json')
        selection=dict(capture_id=capture_id,workspace=workspace,restore_layout=arguments.get('restore_layout',False),intent=intent)
        with _lock(self.directory/'restore.lock'):
            receipt=_load(receipt_path) if receipt_path.exists() else None
            if receipt:
                if receipt['selection']!=selection:raise InventoryError('recovery_intent_conflict','Recovery intent cannot select different work.')
                if receipt['status']=='completed':return dict(receipt,replayed=True)
            preview=self.preview(capture_id,workspace,selection['restore_layout'])
            if arguments.get('expected_target')!=preview['target']:
                raise InventoryError('stale_target','Workspace/capture changed; preview before restoring.')
            snapshot=_load(self._path(capture_id));context=self.runtime.context(workspace)
            selected={(row['identity']['namespace'],row['identity']['conversation_id']) for row in snapshot['rows'] if row['kind']=='codex'}
            for other in list(self.directory.glob('restore-*.json'))[:256]:
                if other==receipt_path:continue
                pending=_load(other)
                if any(row.get('effects_attempted') and row.get('status') not in ('resumed','preserved')
                       and (row.get('namespace'),row.get('conversation_id')) in selected for row in pending['rows']):
                    raise InventoryError('recovery_original_intent_required','Reconcile the original uncertain recovery intent before starting another.')
            if receipt is None:
                receipt=dict(schema_version=1,intent=intent,selection=selection,target=preview['target'],status='running',rows=[])
                _save(receipt_path,receipt)
            elif receipt['target']['workspace_identity']!=context['identity']:
                raise InventoryError('stale_target','Original recovery destination was replaced; reconcile before a new intent.')
            for saved in snapshot['rows']:
                previous=next((row for row in receipt['rows'] if row['logical_id']==saved['logical_id']),None)
                current_context=self.runtime.context(workspace)
                row=self._preview(dict(rows=[saved]),current_context,selection['restore_layout'])[0]
                if row['status']=='already_attached':
                    self.runtime.mark(current_context,row['window_id'],saved['logical_id'])
                    result=dict(row,status='resumed')
                elif row['status']=='restoreable':
                    if previous and previous.get('effects_attempted'):
                        result=dict(row,status='uncertain',reason='original_launch_not_observed',effects_attempted=previous['effects_attempted'])
                    else:
                        result=dict(row,status='starting',effects_attempted=1)
                        receipt['rows']=[r for r in receipt['rows'] if r['logical_id']!=saved['logical_id']]+[result]
                        _save(receipt_path,receipt)
                        def guard():
                            fresh=self.runtime.context(workspace)
                            if (fresh['identity']!=context['identity'] or fingerprint(fresh['windows'])!=fingerprint(current_context['windows'])
                                    or fingerprint(_load(self._path(capture_id)))!=preview['target']['capture_sha256']):
                                raise InventoryError('stale_target','Recovery source/destination changed before launch.')
                            if self.runtime.identity(saved,fresh)!=saved['identity']:
                                raise InventoryError('stale_target','Saved native identity changed before launch.')
                        try:
                            launch=self.runtime.launch(saved,current_context,guard)
                            result.update(launch=launch)
                            _save(receipt_path,receipt)
                            self.runtime.mark(self.runtime.context(workspace),launch['window_id'],saved['logical_id'])
                            deadline=time.monotonic()+min(5,saved['profile'].get('timeout',2))
                            while time.monotonic()<deadline:
                                binding=self.runtime.binding(saved,self.runtime.context(workspace))
                                if binding['state']=='ready' and binding.get('window_id')==launch['window_id']:
                                    result.update(status='resumed',window_id=launch['window_id'],reason=None);break
                                time.sleep(.05)
                        except Exception:
                            result.update(status='uncertain',reason='native_launch_outcome_unknown')
                else:
                    result=dict(row,status='uncertain',effects_attempted=previous['effects_attempted']) if previous and previous.get('effects_attempted') else row
                receipt['rows']=[r for r in receipt['rows'] if r['logical_id']!=saved['logical_id']]+[result]
                _save(receipt_path,receipt)
            receipt['status']='completed' if all(row['status'] in ('resumed','preserved') for row in receipt['rows']) else 'partial'
            _save(receipt_path,receipt)
            return dict(receipt,replayed=False)

    def status(self,arguments):
        if arguments.get('intent'):
            return _load(self.directory/('restore-'+fingerprint(_key(arguments['intent']))+'.json'))
        if arguments.get('capture_id'):return dict(snapshot=_load(self._path(arguments['capture_id'])))
        captures=[]
        for path in sorted(self.directory.glob('capture-*.json'))[:256]:
            row=_load(path);captures.append(dict(capture_id=row['capture_id'],workspace=row['workspace'],captured_at=row['captured_at'],windows=len(row['rows'])))
        return dict(captures=captures)


def main(argv=None):
    """Whole-workspace save/restore wrapper; never replay recorded shell commands."""
    import argparse
    from .shortcut_store import default_root
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wake-root',type=Path)
    parser.add_argument('action',choices=('save','preview','restore','status'))
    parser.add_argument('--workspace')
    parser.add_argument('--capture-id')
    parser.add_argument('--intent')
    args=parser.parse_args(argv)
    try:
        owner=TabRecovery(default_root(args.wake_root))
        arguments={key:value for key,value in vars(args).items() if key in ('workspace','capture_id','intent') and value is not None}
        action={'save':'capture','restore':'apply'}.get(args.action,args.action)
        if action in ('preview','apply'):
            arguments['restore_layout']=True
        if action=='apply':
            if not args.intent:raise InventoryError('invalid_argument','Restore requires a stable --intent for safe restart/retry.')
            preview=owner.execute('tabs.recovery.preview',{k:v for k,v in arguments.items() if k!='intent'})
            arguments['expected_target']=preview['target']
        result=owner.execute('tabs.recovery.'+action,arguments)
        print(json.dumps(dict(status='completed',result=result),sort_keys=True))
        return 0
    except (InventoryError,OSError,ValueError,KeyError) as error:
        print(json.dumps(dict(status='failed',error=dict(code=getattr(error,'code','recovery_unavailable'),message=str(error)))))
        return 2


if __name__=='__main__':
    raise SystemExit(main())
