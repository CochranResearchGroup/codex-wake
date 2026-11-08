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
    parser = subparsers.add_parser('tabs', help='preview and conditionally apply managed workspace tab ordering')
    verbs = parser.add_subparsers(dest='tabs_command', required=True)
    for action in ('list','capture','input','preview','show','apply','undo','create','rename','focus','move','park','restore','close','view-list','view-show','view-save','view-delete','view-evaluate','group-list','group-show','group-save','group-delete','monitor-start','monitor-status','monitor-refresh','monitor-stop','policy-configure','policy-status','policy-enable','policy-pause','policy-disable','policy-tick','recovery-capture','recovery-preview','recovery-apply','recovery-status'):
        command = verbs.add_parser(action)
        if action.startswith(('view-','group-')) and not action.endswith('-list'):
            command.add_argument('view_name',nargs='?')
        for field in ('debounce-seconds','min-interval-seconds','stale-after-seconds'):
            command.add_argument('--'+field,type=float)
        command.add_argument('--max-swaps-per-tick',type=int)
        command.add_argument('--capture-id')
        command.add_argument('--intent')
        command.add_argument('--restore-layout',action='store_true',default=None)
        command.add_argument('--view')
        command.add_argument('--reason')
        command.add_argument('--acknowledge-pending',action='store_true',default=None)
        for field in ('interval','probe-timeout','stale-after','cycle-timeout'):
            command.add_argument('--'+field,type=float)
        command.add_argument('--filter',action='append',dest='filters',default=[])
        command.add_argument('--group-by',action='append',default=[])
        command.add_argument('--sort-by',action='append',default=[])
        command.add_argument('--group')
        command.add_argument('--member',action='append',dest='members',default=[])
        command.add_argument('--arguments',type=json.loads)
        for field in ('workspace','window','name','cwd','destination'):
            command.add_argument('--'+field)
        command.add_argument('--index',type=int)
        command.add_argument('--force',action='store_true',default=None)
        command.add_argument('--dry-run',dest='preview',action='store_true',default=None)
        command.add_argument('--socket-path')
        command.add_argument('--session-id')
        command.add_argument('--bus-root', type=Path)
        command.add_argument('--operator-capability', type=Path)
        command.add_argument('--actor-capability', type=Path)
        command.add_argument('--app-server', default='unix://')
        command.add_argument('--timeout', type=float, default=30)
        command.add_argument('--json', dest='as_json', action='store_true')
        if action == 'policy-configure':
            command.add_argument('--mode',choices=('activity','repository','traits'),default='activity')
            command.add_argument('--pin',action='append',dest='pins',default=[])
        if action == 'preview':
            command.add_argument('--mode', choices=('activity','repository','traits'), default='activity')
            command.add_argument('--pin', action='append', dest='pins', default=[])
        if action in ('show', 'apply'): command.add_argument('--plan-id')
        if action in ('undo','restore'): command.add_argument('--receipt-id')
    return parser


def run(args, root, *, observer=None):
    if args.arguments is not None or getattr(args,'workspace',None) is not None or args.tabs_command in ('list','capture','input','create','rename','focus','move','park','restore','close','view-list','view-show','view-save','view-delete','view-evaluate','group-list','group-show','group-save','group-delete','monitor-start','monitor-status','monitor-refresh','monitor-stop','policy-configure','policy-status','policy-enable','policy-pause','policy-disable','policy-tick','recovery-capture','recovery-preview','recovery-apply','recovery-status'):
        from .tab_commands import command
        args.tab_command = args.tabs_command
        args.arguments = args.arguments or {}
        if getattr(args,'view_name',None):args.arguments.setdefault('name',args.view_name)
        if args.tabs_command.startswith('recovery-'):
            for field in ('capture_id','intent','restore_layout'):
                value=getattr(args,field,None)
                if value is not None:args.arguments.setdefault(field,value)
            if args.tabs_command=='recovery-apply' and 'intent' not in args.arguments:
                from uuid import uuid4
                args.arguments['intent']='restore-'+uuid4().hex
        if args.tabs_command.startswith('policy-'):
            for field in ('workspace','reason','view','debounce_seconds','min_interval_seconds','max_swaps_per_tick','stale_after_seconds','acknowledge_pending'):
                value=getattr(args,field,None)
                if value is not None:args.arguments.setdefault(field,value)
            if args.tabs_command=='policy-configure':
                args.arguments.setdefault('mode','traits' if args.group_by or args.sort_by else args.mode)
                args.arguments.setdefault('pins',args.pins)
                if args.group_by or args.sort_by:args.arguments.setdefault('criteria',args.group_by+args.sort_by)
        if args.tabs_command=='monitor-start':
            for field in ('interval','probe_timeout','stale_after','cycle_timeout'):
                value=getattr(args,field,None)
                if value is not None:args.arguments.setdefault(field,value)
        if args.tabs_command=='preview':
            args.arguments.setdefault('mode','traits' if args.group_by or args.sort_by else args.mode)
            args.arguments.setdefault('pins',args.pins)
            if args.group_by or args.sort_by:args.arguments.setdefault('criteria',args.group_by+args.sort_by)
        if args.tabs_command=='view-save':
            filters={}
            for value in args.filters:
                if '=' not in value:
                    print(json.dumps(dict(status='held',error=dict(code='invalid_argument',message='Use --filter trait=value.'))));return 2
                key,value=value.split('=',1);filters[key]=value
            definition=dict(filters=filters,group_by=args.group_by,sort_by=args.sort_by)
            if args.group:definition['group']=args.group
            args.arguments.setdefault('definition',definition)
        if args.tabs_command=='group-save':args.arguments.setdefault('members',args.members)
        for field in ('workspace','window','name','cwd','destination','index','force','preview','receipt_id','plan_id'):
            value=getattr(args,field,None)
            if value is not None:args.arguments.setdefault(field,value)
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
