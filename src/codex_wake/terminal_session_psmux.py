"""Finite session lifecycle over the existing host-approved native bridge."""
import json
from contextlib import ExitStack
import subprocess
import time
from .managed_inventory import InventoryError
from .controller_tab_adapters import ConfiguredBridge, PsmuxAttachmentTransport


def _command(owner, record):
    command=record.get('psmux_bridge_command')
    if command is None:
        for cfg in owner.tabs.workspaces.values():
            if cfg.get('kind')!='psmux':continue
            candidate=getattr(getattr(cfg.get('transport'),'bridge',None),'command',None)
            if candidate and '--namespace' in candidate and candidate[candidate.index('--namespace')+1]==record['server']:
                command=candidate;break
    if not command:raise InventoryError('unsupported_target','No host-approved psmux bridge for this namespace.')
    command=list(command)
    for option in ('--server-pid','--server-birth','--session'):
        if option in command:
            index=command.index(option);del command[index:index+2]
    return command+['--session',record['name']]


def _bootstrap(command, action, arguments=None):
    reply=subprocess.run(command+['--session-management'],input=json.dumps(dict(action=action,arguments=arguments or {})),text=True,capture_output=True,timeout=12)
    if len(reply.stdout)>1048576:raise InventoryError('capacity','Native session reply exceeds bound.')
    try:value=json.loads(reply.stdout)
    except ValueError:raise InventoryError('attachment_unavailable','Native session reply unavailable.') from None
    if 'error' in value:raise InventoryError(value['error']['code'],value['error']['message'])
    return value['result']


def presence(owner,record):
    try:return 'present' if _bootstrap(_command(owner,record),'session_probe')['present'] else 'absent'
    except (OSError,ValueError,subprocess.SubprocessError):return 'unknown'


def native(owner,record,verb,**kwargs):
    from .terminal_sessions import _digest
    with ExitStack() as stack:
        command=_command(owner,record)
        formatter=None;previous=None
        if verb=='rename':
            from .tab_formatting import TabFormatting
            formatter=TabFormatting(owner.root,tabs=owner.tabs)
            stack.enter_context(formatter.locked())
            previous=owner.tabs.workspaces[record['workspace']]['transport'].snapshot(time.monotonic()+10)
        if verb=='rename':
            cfg=owner.tabs.workspaces[record['workspace']]
            cfg['transport'].request('session_rename',dict(name=kwargs['name']),time.monotonic()+10)
            # Session name participates in the host generation. Re-pin after rename.
            command[command.index('--session')+1]=kwargs['name']
        elif verb=='open':
            if any(k in record.get('defaults',{}) for k in ('profile','argv')):raise InventoryError('unsupported_target','psmux launch defaults require a qualified profile launcher; no shell substitution.')
            if record.get('opening'):raise InventoryError('uncertain_effect','Prior psmux opening requires reconciliation; no replay.')
            record['opening']=True;record['psmux_bridge_command']=command
            state=owner.state();state['sessions'][record['id']]=record;owner.save(state)
            _bootstrap(command,'session_create',record.get('defaults',{}))
        else:raise InventoryError('unsupported_operation','Unsupported native session action.')
        description=subprocess.run(command+['--describe'],text=True,capture_output=True,timeout=10,check=True)
        value=json.loads(description.stdout)
        if 'error' in value:raise InventoryError(value['error']['code'],value['error']['message'])
        identity=value['identity'];fixed=command+['--server-pid',str(identity['pid']),'--server-birth',str(identity['creation_filetime'])]
        transport=PsmuxAttachmentTransport(ConfiguredBridge(fixed),generation=value['generation'])
        snap=transport.snapshot(time.monotonic()+10)
        workspace=record.get('workspace') or record['id']
        if previous is not None:
            # Rename changes the bridge generation, not the native process. Transfer
            # custody only from this exact old snapshot to its verified successor.
            def continuity(snapshot):
                identity=snapshot.get('server_identity',{})
                server=tuple(identity.get(k) for k in ('platform','namespace','pid','creation_filetime','executable_sha256'))
                panes=sorted((w['window_id'],p['pane_id'],p['pid'],p.get('windows_creation_filetime'))
                             for w in snapshot['windows'] for p in w['panes'])
                return server,panes
            state=formatter.read();saved=state['workspaces'].get(workspace)
            if (saved and saved['identity']==formatter.identity(previous)
                    and continuity(previous)==continuity(snap)
                    and all(continuity(snap)[0])
                    and all(p[3] for p in continuity(snap)[1])):
                saved['identity']=formatter.identity(snap)
                formatter.save(state)
        owner.tabs.workspaces[workspace]=dict(kind='psmux',label=kwargs.get('name',record['name']),transport=transport)
        record.update(native_session_id=snap['session_id'],native_key=_digest({k:snap.get(k) for k in ('server','session_id','socket_identity','bridge_generation')}),psmux_bridge_command=command)
        record.pop('opening',None)
        state=owner.state();state['sessions'][record['id']]=record;owner.save(state)
        return record


def restore(owner,record):
    """Recover only the saved native generation; never launch during reads."""
    from .terminal_sessions import _digest
    try:
        command=_command(owner,record)
        reply=subprocess.run(command+['--describe'],text=True,capture_output=True,timeout=8,check=True)
        value=json.loads(reply.stdout);identity=value['identity']
        fixed=command+['--server-pid',str(identity['pid']),'--server-birth',str(identity['creation_filetime'])]
        transport=PsmuxAttachmentTransport(ConfiguredBridge(fixed),generation=value['generation'])
        snap=transport.snapshot(time.monotonic()+8)
        key=_digest({k:snap.get(k) for k in ('server','session_id','socket_identity','bridge_generation')})
        existing=any(cfg['kind']=='psmux' and getattr(cfg['transport'],'generation',None)==value['generation'] for cfg in owner.tabs.workspaces.values())
        if key==record['native_key'] and not existing:owner.tabs.workspaces[record['id']]=dict(kind='psmux',label=record['name'],transport=transport)
    except (OSError,ValueError,KeyError,subprocess.SubprocessError):pass
