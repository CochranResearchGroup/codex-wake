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
    for action in ('preview', 'show', 'apply', 'undo'):
        command = verbs.add_parser(action)
        command.add_argument('--socket-path', required=True)
        command.add_argument('--session-id', required=True)
        command.add_argument('--bus-root', type=Path, required=True)
        command.add_argument('--operator-capability', type=Path)
        command.add_argument('--actor-capability', type=Path)
        command.add_argument('--app-server', default='unix://')
        command.add_argument('--timeout', type=float, default=30)
        command.add_argument('--json', dest='as_json', action='store_true')
        if action == 'preview':
            command.add_argument('--mode', choices=('activity', 'repository'), default='activity')
            command.add_argument('--pin', action='append', dest='pins', default=[])
        if action in ('show', 'apply'): command.add_argument('--plan-id', required=True)
        if action == 'undo': command.add_argument('--receipt-id', required=True)
    return parser


def run(args, root, *, observer=None):
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
