"""Controller attachment CLI adapter over the host-owned operation service."""
import json


def register_parser(subparsers):
    parser = subparsers.add_parser('tabs')
    commands = parser.add_subparsers(dest='tab_command', required=True)
    for verb in ('list','show','preview','apply','undo','capture','input'):
        item = commands.add_parser(verb)
        item.add_argument('--arguments', type=json.loads, default={})
    return parser


def command(args, owner=None):
    from .managed_inventory import InventoryError
    from .shortcut_store import default_root
    try:
        args.wake_root = default_root(args.wake_root)
        if owner is None:
            from .controller_tabs import controller_tabs_from_root
            owner = controller_tabs_from_root(args.wake_root)
        operation = 'tabs.' + args.tab_command.replace('monitor-','monitor.',1)
        value = owner.execute(operation,args.arguments) if operation in owner.READS else operator_execute(operation,args.arguments,args.wake_root,owner=owner)
        print(json.dumps(value, sort_keys=True))
        return 0
    except (InventoryError, OSError, ValueError, TypeError) as error:
        print(json.dumps(dict(status='held', error=dict(
            code=getattr(error,'code','configuration_unavailable'),
            message=str(error) if isinstance(error,InventoryError) else
                    'Tab configuration is unavailable or invalid; inspect the selected controller and refresh workspaces.'))))
        return 2


def tool_specs():
    text = {'type':'string'}
    specs = {}
    for verb in ('list','show','preview','apply','undo','capture','input'):
        properties = {} if verb=='list' else {'workspace':text}
        required = [] if verb=='list' else ['workspace']
        if verb=='show': properties['selector']=text
        if verb not in ('list','show'):
            properties.update(expected_target={'type':'object'},_request={'type':'object'})
            required += ['expected_target','_request']
        if verb=='preview': properties.update(mode={'enum':['activity','repository','traits']},pins={'type':'array','items':text},criteria={'type':'array','items':text})
        if verb=='apply': properties['plan_id']=text; required += ['plan_id']
        if verb=='undo': properties['receipt_id']=text; required += ['receipt_id']
        if verb in ('capture','input'): properties['pane']=text; required += ['pane']
        if verb=='capture': properties['lines']={'type':'integer','minimum':1,'maximum':200}
        if verb=='input':
            properties.update(input={'type':'string','maxLength':16384},custody={'type':'object'},transport={'enum':['structured','terminal']})
            required += ['input','custody','transport']
        specs['wake_tabs_'+verb]=('controller-tabs','tabs.'+verb,'Use host-enrolled presentation with exact generation and explicit input custody; no automatic replacement.',properties,required,verb in ('list','show'))
    from .tab_lifecycle import TabLifecycle
    for operation, fields in TabLifecycle.ARGUMENTS.items():
        properties={key: ({'type':'object'} if key in ('expected_target','expected_destination') else
                          {'type':'boolean'} if key in ('preview','force') else
                          {'type':'integer','minimum':0} if key=='index' else text)
                    for key in fields}
        properties['_request']={'type':'object'}
        required=['workspace','expected_target','_request']
        if operation!='tabs.create':required.append('window')
        if operation in ('tabs.create','tabs.rename'):required.append('name')
        if operation in ('tabs.move','tabs.park','tabs.restore'):required+=['destination','expected_destination']
        if operation=='tabs.restore':required.append('receipt_id')
        specs['wake_tabs_'+operation.split('.')[1]]=('controller-tabs',operation,
            'Manage one exact owned attachment; preserve conversations and reconcile uncertain effects.',properties,required,False)
    from .tab_views import TabViews
    for operation in TabViews.READS|TabViews.MUTATIONS:
        props={} if operation.endswith('-list') else {'name':text}
        required=[] if operation.endswith('-list') else ['name']
        if operation=='tabs.view-save':props['definition']={'type':'object'};required.append('definition')
        if operation=='tabs.group-save':props['members']={'type':'array','items':text};required.append('members')
        if operation in TabViews.MUTATIONS:
            props.update(expected_target={'type':'object'},_request={'type':'object'});required+=['expected_target','_request']
        specs['wake_tabs_'+operation.split('.')[1].replace('-','_')]=('controller-tabs',operation,
            'Inspect or update logical tab group/view definitions without moving attachments.',props,required,operation in TabViews.READS)
    for verb in ('start','status','refresh','stop'):
        op='tabs.monitor.'+verb
        props={}
        if verb=='start':props={k:{'type':'number'} for k in ('interval','probe_timeout','stale_after','cycle_timeout')}
        if verb=='stop':props={'timeout':{'type':'number'}}
        required=[]
        if verb in ('start','stop'):
            props.update(expected_target={'type':'object'},_request={'type':'object'});required=['expected_target','_request']
        specs['wake_tabs_monitor_'+verb]=('controller-tabs',op,'Observe or control the bounded read-only tab monitor.',props,required,verb in ('status','refresh'))
    return specs


def protected_execute(operation,arguments,root):
    from types import SimpleNamespace
    from pathlib import Path
    from .controller_tabs import controller_tabs_from_root
    from .controller_operations import ControllerOperations
    from .controller_http import ProtectedOperations
    from .managed_inventory import ManagedInventory
    from .operation_commands import local_actor
    tabs=controller_tabs_from_root(root)
    operations=ControllerOperations(ManagedInventory(root),host=tabs.host,environment=tabs.environment,tabs=tabs)
    def authenticate(unused):
        if (Path(root)/'controller-messaging.json').is_file():
            return local_actor(root)
        from .daemon_commands import local_operator
        return local_operator(arguments.get('expected_target',{}),('control','observe'))
    authority=SimpleNamespace(authenticate=authenticate)
    return ProtectedOperations(authority,operations).execute('host-local-grant',operation,arguments)


def operator_execute(operation, arguments, root, *, owner=None, request_id=None):
    """UID-authorized local tab control, with retained common journal identity."""
    import hashlib
    from pathlib import Path
    from types import SimpleNamespace
    from .daemon_commands import local_operator
    from .controller_tabs import controller_tabs_from_root, AuthorizedTabs
    from .controller_runtime import ControllerRuntime
    from .tab_lifecycle import TabLifecycle
    from .managed_inventory import InventoryError
    owner = owner or controller_tabs_from_root(root)
    payload = dict(arguments)
    from .tab_views import TabViews
    if operation in TabViews.READS|TabViews.MUTATIONS or operation.startswith('tabs.monitor.'):
        payload.setdefault('expected_target',owner.monitor_target() if operation.startswith('tabs.monitor.') else owner.logical_target())
        key=request_id or hashlib.sha256(json.dumps([operation,payload],sort_keys=True).encode()).hexdigest()
        payload.setdefault('_request',dict(operation_id='tab-cli-'+key,idempotency_key='tab-cli-'+key,
            correlation_id=key,binding='local-cli',target=payload['expected_target']))
        actor=local_operator(payload['expected_target'],('control','observe'))
        return AuthorizedTabs(SimpleNamespace(authenticate=lambda unused:actor),owner,ControllerRuntime(root)).execute('local-cli',operation,payload)
    workspace = payload.get('workspace')
    if workspace is None and len(owner.workspaces) == 1:
        workspace = next(iter(owner.workspaces))
    elif workspace not in owner.workspaces:
        matches = [k for k,v in owner.workspaces.items() if v.get('label') == workspace]
        if len(matches) == 1:
            workspace = matches[0]
    if workspace not in owner.workspaces:
        raise InventoryError('ambiguous_target','Select one workspace from tabs list using --workspace.')
    payload['workspace'] = workspace
    lifecycle = TabLifecycle(root,workspaces=owner.workspaces,host=owner.host,environment=owner.environment)
    payload.setdefault('expected_target',lifecycle.inspect(workspace)['target'])
    if 'destination' in payload:
        dest = payload['destination']
        if dest not in owner.workspaces:
            matches=[k for k,v in owner.workspaces.items() if v.get('label') == dest]
            if len(matches)==1:dest=matches[0]
        payload['destination']=dest
        payload.setdefault('expected_destination',lifecycle.inspect(dest)['target'])
    if '_request' not in payload:
        key = request_id or hashlib.sha256(json.dumps([operation,payload],sort_keys=True).encode()).hexdigest()
        payload['_request']=dict(operation_id='tab-cli-'+key,idempotency_key='tab-cli-'+key,
                                 correlation_id=key,binding='local-cli',target=payload['expected_target'])
    actor=local_operator(payload['expected_target'],('control','observe'))
    if '_request' in arguments and (Path(root)/'controller-messaging.json').is_file():
        from .operation_commands import local_actor
        actor=local_actor(root)
    authority=SimpleNamespace(authenticate=lambda unused:actor)
    return AuthorizedTabs(authority,owner,ControllerRuntime(root)).execute('local-cli',operation,payload)
