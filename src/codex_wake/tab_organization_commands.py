"""Public tab organization adapter. Roles and runtime evidence are host supplied."""
import json
import math
import subprocess
from pathlib import Path
import time

from .records import WakeError
from .session_permissions import Principal
from .tab_organization import TabOrganization, TabError, TmuxTransport


class WorkspaceObserver:
    """Refresh enrolled Codex bindings and exact native semantic metadata.

    Unknown runtimes and any incomplete observation remain unqualified/pinned.
    """
    def __init__(self, root, socket_path, endpoint='unix://'):
        self.root, self.socket, self.endpoint = root, socket_path, endpoint

    def __call__(self, timeout):
        from .managed_inventory import ManagedInventory
        from .managed_inventory_commands import RuntimeObserver
        from .agent_observation import RuntimeStateObserver
        deadline = time.monotonic() + timeout
        result = {}
        agents = ManagedInventory(self.root).inspect()['agents']
        if len(agents) > 256:
            raise TabError('workspace_unavailable', 'inventory exceeds 256 managed agents')
        duplicates = set()
        for agent in agents:
            if agent['enrollment'] != 'enrolled' or agent['runtime'] != 'codex': continue
            remaining = deadline-time.monotonic()
            if remaining <= 0: raise TabError('workspace_timeout', 'binding inventory deadline exhausted')
            try:
                binding = RuntimeObserver(endpoint=self.endpoint, socket_path=self.socket,
                    timeout=min(remaining / 4, 5))._codex(agent['conversation_id'])
                if binding.state != 'ready' or binding.namespace != agent['namespace'] or binding.root != agent['root']:
                    continue
                refreshed = dict(agent, process=binding.process)
                state = RuntimeStateObserver(endpoint=self.endpoint)(refreshed, max(.001, deadline-time.monotonic()))
                if (not state.complete or state.process != binding.process or state.root != binding.root
                        or state.namespace != binding.namespace or state.conversation_id != binding.conversation_id):
                    continue
                value = dict(conversation_id=binding.conversation_id, namespace=binding.namespace,
                    root=binding.root, process=binding.process, state=state.state, fresh=True)
                for attachment in binding.attachments:
                    pane = attachment['pane_id']
                    if pane in result: duplicates.add(pane)
                    result[pane] = value
            except Exception:
                continue
        for pane in duplicates: result.pop(pane, None)
        return result


def execute(action, arguments, root, *, principal, observer=None, transport=None,
            mcp=False, native_context=None):
    if not isinstance(principal, Principal) or any(k in arguments for k in ('principal', 'operator', 'observer', 'transport')):
        raise TabError('workspace_authority_denied', 'authority and runtime evidence are host supplied')
    if mcp:
        from .goal_supervision import verified_native_caller
        verified_native_caller(native_context, principal.subject)
        if action not in ('preview', 'show'):
            raise TabError('workspace_operator_required', 'mutation requires the local verified operator CLI')
    if action not in ('preview', 'show', 'apply', 'undo'):
        raise TabError('workspace_invalid_argument', 'unsupported tab operation')
    if action in ('apply', 'undo') and principal.role != 'operator':
        raise TabError('workspace_operator_required', 'verified operator required')
    timeout = arguments.get('timeout', 30)
    if type(timeout) not in (int, float) or not math.isfinite(timeout) or not 0 < timeout <= 30:
        raise TabError('workspace_invalid_argument', 'timeout must be positive and at most 30 seconds')
    deadline = time.monotonic() + timeout
    if action == 'show':
        owner = TabOrganization(root, transport=None)
        record = owner.read(arguments.get('plan_id') or arguments['receipt_id'])
        return dict(status='inspection', record=record)
    if action != 'show':
        transport = transport or TmuxTransport(arguments['socket_path'], arguments['session_id'])
    from .permission_enforcement import authorize
    from .session_permissions import PermissionStore
    policy = PermissionStore(root)
    owner = TabOrganization(root, transport=transport,
        observer=observer or WorkspaceObserver(root, arguments['socket_path'], arguments.get('app_server', 'unix://')),
        policy_revision=lambda: policy._read()['revision'] if policy.active() else 0,
        authorize=lambda operation: authorize(root, operation, principal, operation_id=arguments.get('plan_id') or arguments.get('receipt_id')))
    if action == 'show':
        record = owner.read(arguments.get('plan_id') or arguments['receipt_id'])
        return dict(status='inspection', record=record)
    if action == 'preview':
        return owner.preview(mode=arguments.get('mode', 'activity'), pins=arguments.get('pins', []), deadline=deadline)
    if action == 'apply': return owner.apply(arguments['plan_id'], deadline=deadline)
    return owner.undo(arguments['receipt_id'], deadline=deadline)


def register_parser(subparsers):
    from .tab_contract import tool_specs, cli_verb
    parser = subparsers.add_parser('tabs', help='observe, group and control exact owned terminal attachments')
    verbs = parser.add_subparsers(dest='tabs_command', required=True)
    aliases = {'pins':'pin', 'members':'member', 'criteria':'criterion'}
    for _, operation, summary, properties, required, readonly in tool_specs().values():
        action=cli_verb(operation)
        command=verbs.add_parser(action, help=summary, description=summary)
        command.set_defaults(group_by=[],sort_by=[],filters=[],pins=[],members=[],mode='activity')
        if action.startswith(('view-','group-')) and not action.endswith('-list'):
            command.add_argument('view_name',nargs='?',help='Saved logical view or group name.')
        command.add_argument('--arguments',type=json.loads,help='Advanced operation JSON; typed flags fill only omitted fields.')
        command.add_argument('--json',dest='as_json',action='store_true',help='Emit structured results.')
        if not readonly:
            command.add_argument('--request-id',help='Stable intent ID; reuse only for identical inputs. Retrieve with tabs result.')
        for field, schema in sorted(properties.items()):
            if field=='_request':continue
            option='--'+aliases.get(field,field.replace('_','-'))
            settings={'dest':field,'default':None,'help':schema.get('description',field.replace('_',' ')+'.').replace('%','%%')}
            kind=schema.get('type')
            if kind=='boolean':settings['action']='store_true'
            elif kind=='array':settings.update(action='append')
            elif kind=='object':settings['type']=json.loads
            elif kind=='integer':settings['type']=int
            elif kind=='number':settings['type']=float
            if 'enum' in schema:settings['choices']=schema['enum']
            if field=='preview':option='--dry-run'
            command.add_argument(option,**settings)
        if action in ('preview','view-save','policy-configure'):
            command.add_argument('--group-by',action='append',default=[],help='Layered grouping trait; repeat in order.')
            command.add_argument('--sort-by',action='append',default=[],help='Layered sorting trait; repeat in order.')
        if action=='view-save':
            command.add_argument('--filter',action='append',dest='filters',default=[],help='Read-only trait=value filter.')
            command.add_argument('--group',help='Saved named group restriction.')
        if action in ('preview','show','apply','undo'):
            for field in ('socket-path','session-id','app-server'):
                command.add_argument('--'+field,help='Legacy explicit tmux adapter option.')
            command.add_argument('--timeout',type=float,default=30)
            for field in ('bus-root','operator-capability','actor-capability'):
                command.add_argument('--'+field,type=Path)
            if action=='show':
                command.add_argument('--plan-id');command.add_argument('--receipt-id')
    result=verbs.add_parser('result',help='Read the retained same-user request result, including after a workspace closes.')
    result.add_argument('--request-id',required=True)
    result.add_argument('--json',dest='as_json',action='store_true')
    result.set_defaults(arguments=None)
    return parser


def run(args, root, *, observer=None):
    legacy = args.tabs_command in ('preview','show','apply','undo') and (
        getattr(args,'socket_path',None) is not None or getattr(args,'session_id',None) is not None or
        (args.tabs_command=='show' and (getattr(args,'plan_id',None) or getattr(args,'receipt_id',None))))
    if args.arguments is not None or not legacy:
        from .tab_commands import command
        from .tab_contract import BY_OPERATION
        args.tab_command=args.tabs_command
        args.arguments=dict(args.arguments or {})
        operation='tabs.'+args.tabs_command.replace('monitor-','monitor.',1).replace('policy-','policy.',1).replace('recovery-','recovery.',1)
        if operation in BY_OPERATION:
            properties=BY_OPERATION[operation][1][3]
            for field in properties:
                value=getattr(args,field,None)
                if value is not None:args.arguments.setdefault(field,value)
        if getattr(args,'view_name',None):args.arguments.setdefault('name',args.view_name)
        if args.tabs_command=='recovery-apply' and 'intent' not in args.arguments:
            from uuid import uuid4
            args.arguments['intent']='restore-'+(getattr(args,'request_id',None) or uuid4().hex)
        if args.tabs_command in ('preview','policy-configure'):
            criteria=(args.group_by or [])+(args.sort_by or [])
            args.arguments.setdefault('mode','traits' if criteria else 'activity')
            if criteria:args.arguments.setdefault('criteria',criteria)
        if args.tabs_command=='view-save' and 'definition' not in args.arguments:
            filters={}
            for value in args.filters:
                if '=' not in value:
                    print(json.dumps(dict(status='held',error=dict(code='invalid_argument',message='Use --filter trait=value.'))));return 2
                key,value=value.split('=',1);filters[key]=value
            definition=dict(filters=filters,group_by=args.group_by,sort_by=args.sort_by)
            if args.group:definition['group']=args.group
            args.arguments['definition']=definition
        if args.tabs_command=='group-save':args.arguments.setdefault('members',[])
        return command(args)
    from .permission_commands import verified_cli_principal
    try:
        principal = verified_cli_principal(args)
        names = ('socket_path', 'session_id', 'app_server', 'timeout', 'mode', 'pins', 'plan_id', 'receipt_id')
        arguments = {k: getattr(args, k) for k in names if getattr(args, k, None) is not None}
        result = execute(args.tabs_command, arguments, root, principal=principal, observer=observer)
        print(json.dumps(result, sort_keys=True))
        return 0 if result['status'] not in ('uncertain', 'partial') else 3
    except (WakeError, ValueError, TypeError, KeyError, OSError, TimeoutError, subprocess.SubprocessError) as error:
        print(json.dumps(dict(status='held', error=dict(code=getattr(error, 'code', 'workspace_unavailable'),
            message=str(error) if isinstance(error, WakeError) else 'Workspace evidence or request unavailable.'))))
        return 2
