"""Shared public harness tools; host authority stays outside model arguments."""
from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path
from types import SimpleNamespace

from .records import WakeError

TEXT = {'type': 'string', 'minLength': 1, 'maxLength': 256}
CALLER = {'type': 'string', 'pattern': '^[0-9a-f-]{36}$'}
ROUTES={'type':'array','minItems':1,'maxItems':4,'uniqueItems':True,'items':{'enum':['background','existing_tab','new_tab','fresh_task']}}
POLICY = {'routes':ROUTES,'wake_lifetime': {'enum': ['conversation', 'task', 'persistent']},
          'owner_id': TEXT, 'owner_end': {'enum': ['retire', 'hold', 'retain']},
          'recipient_startup': {'enum': ['active_tab', 'background_saved', 'create_load_run']}}


def tool_specs():
    result = {}
    for verb in ('list', 'show', 'enroll', 'reconcile'):
        properties = {}
        required = []
        if verb in ('enroll', 'reconcile'):
            properties.update(runtime={'enum': ['codex', 'grok']}, conversation_id=TEXT)
            required += ['runtime', 'conversation_id']
        if verb in ('show', 'reconcile'):
            properties['managed_agent_id'] = TEXT
            required.append('managed_agent_id')
        if verb == 'enroll':
            properties.update({k: TEXT for k in ('predecessor', 'task_id', 'allocation_id')})
        result['wake_agents_' + verb] = ('agents', verb,
            'Inspect or enroll exact managed conversations. Self-enrollment uses trusted native or host-bound identity; membership never grants additional operations.',
            properties, required, verb in ('list', 'show'))
    for verb in ('propose', 'approve', 'inspect', 'admit', 'pin'):
        properties = dict(caller_thread_id=CALLER, task_id=TEXT)
        required = ['caller_thread_id', 'task_id']
        if verb == 'propose':
            properties['brief'] = {'type': 'object'}
            required.append('brief')
        if verb in ('approve', 'admit'):
            properties['revision'] = {'type': 'integer', 'minimum': 1}
            if verb == 'approve':
                required.append('revision')
        if verb in ('admit', 'pin'):
            properties['assignment_id'] = TEXT
            required.append('assignment_id')
        result['wake_task_briefs_' + verb] = ('task-briefs', verb,
            'Propose, inspect or pin approved task scope. Approvals require exact task delegation in host policy; worker arguments cannot choose a role.',
            properties, required, verb in ('inspect', 'pin'))
    for verb in ('after', 'at', 'file'):
        result['wake_native_' + verb] = ('harness-native', verb,
            'Retain one exact-self native wake with frozen lifetime/startup policy. Registration is not readiness or delivery; unsupported startup stays explicit.',
            dict(caller_thread_id=CALLER, trigger={'type': 'string', 'minLength': 1, 'maxLength': 1024},
                 prompt={'type': 'string', 'minLength': 1, 'maxLength': 32768},
                 idempotency_key=TEXT, ttl=TEXT, **POLICY),
            ['caller_thread_id', 'trigger', 'prompt', 'idempotency_key'], False)
    result['wake_owner_complete'] = ('harness-owner', 'complete',
        'Reconcile an explicit operator-approved owner completion. Caller identity alone cannot declare work complete. Never retract or replay uncertain effects.',
        dict(caller_thread_id=CALLER, owner_kind={'enum': ['conversation', 'task']}, owner_id=TEXT, event_id=TEXT),
        ['caller_thread_id', 'owner_kind', 'owner_id', 'event_id'], False)
    return result


def controller_tasks(runner, caller):
    if runner.harness_policy is None:
        return ()
    from .wake_policy import _read
    policy = _read(Path(runner.harness_policy))
    if (type(policy) is not dict or set(policy) != {'version', 'controllers'}
            or type(policy['version']) is not int or policy['version'] != 1
            or type(policy['controllers']) is not dict):
        raise WakeError('invalid_harness_controller_policy')
    tasks = policy['controllers'].get(caller, [])
    if type(tasks) is not list or len(tasks) > 256 or any(type(t) is not str or not t for t in tasks):
        raise WakeError('invalid_harness_task_delegation')
    return tuple(tasks)


def native_workspace(runner, caller):
    from .shared_app_server import SharedAppServerReader, locate_shared_endpoint
    endpoint = runner.app_server
    if endpoint == 'unix://':
        endpoint = locate_shared_endpoint(timeout=10)
    with SharedAppServerReader(endpoint, timeout=10) as reader:
        thread = reader.read_thread(caller)
    if thread.get('id') != caller or not isinstance(thread.get('cwd'), str) or not Path(thread['cwd']).is_absolute():
        raise WakeError('native_workspace_unavailable')
    return Path(thread['cwd']).resolve()


def call(runner, group, verb, arguments, native_context):
    if runner.wake_root is None:
        raise WakeError('host_wake_root_required')
    root = Path(runner.wake_root)
    if group == 'agents':
        from .managed_inventory_commands import RuntimeObserver, execute
        grok = bus = None
        if runner.actor_runtime == 'grok':
            from .runtime_a2a import GrokMailboxRuntime
            from .a2a_bus import BusStore
            if runner.bus_root is None or runner.capability is None:
                raise WakeError('host_bound_runtime_capability_required')
            bus = BusStore(runner.bus_root)
            grok = GrokMailboxRuntime.from_actor(bus, runner.capability)
        observer = RuntimeObserver(endpoint=runner.app_server, socket_path=runner.tmux_socket,
                                   grok_runtime=grok, bus=bus, capability=runner.capability)
        return execute(verb, arguments, root, native_context=native_context, observer=observer)
    from .goal_supervision import verified_native_caller
    caller = arguments['caller_thread_id']
    verified_native_caller(native_context, caller)
    if group == 'task-briefs':
        from .task_briefs import BriefAuthority, TaskBriefStore
        from .task_brief_commands import execute_task_briefs
        tasks = controller_tasks(runner, caller)
        if arguments['task_id'] in tasks:
            authority = BriefAuthority('native:' + caller, 'controller', tasks)
        else:
            store = TaskBriefStore(root)
            if verb == 'propose':
                workspace = arguments['brief'].get('workspace')
            else:
                existing = store.inspect(arguments['task_id'])
                workspace = existing['revisions'][0]['content']['workspace'] if existing['revisions'] else None
            if (type(workspace) is not str or not Path(workspace).is_absolute()
                    or not Path(workspace).resolve().is_relative_to(native_workspace(runner, caller))):
                raise WakeError('brief_workspace_outside_native_caller')
            authority = BriefAuthority('native:' + caller, 'worker', (arguments['task_id'],))
        args = SimpleNamespace(task_brief_command=verb, task_id=arguments['task_id'],
                               revision=arguments.get('revision'), assignment_id=arguments.get('assignment_id'),
                               brief_json=json.dumps(arguments.get('brief')) if 'brief' in arguments else None)
        return execute_task_briefs(args, root, authority=authority)
    if group == 'harness-owner':
        kind, owner = arguments['owner_kind'], arguments['owner_id']
        if (kind == 'conversation' and owner != 'codex:' + caller) or (kind == 'task' and owner not in controller_tasks(runner, caller)):
            raise WakeError('owner_completion_authority_denied')
        from .wake_policy import reconcile_owner_completion
        return reconcile_owner_completion(root, dict(kind=kind, id=owner), arguments['event_id'])
    if group == 'harness-native':
        if any(isinstance(arguments.get(key), str) and arguments[key].startswith('-') for key in ('trigger', 'owner_id', 'idempotency_key', 'ttl')):
            raise WakeError('invalid_option_prefixed_argument')
        from .cli import run
        argv = ['--wake-root', str(root), 'native', verb, '--endpoint', runner.app_server,
                '--json', '--idempotency-key', arguments['idempotency_key'], '--ttl', arguments.get('ttl', '24h')]
        for name in POLICY:
            if name=='routes':
                for route in arguments.get('routes',[]):argv+=['--wake-route',route]
            elif name in arguments:
                argv += ['--' + name.replace('_', '-'), arguments[name]]
        argv += [caller, arguments['trigger'], '--', arguments['prompt']]
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            from .session_permissions import Principal
            tasks=controller_tasks(runner,caller)
            code = run(argv,permission_principal=Principal(caller,'controller' if tasks else 'session',tasks=tuple(tasks)))
        if code:
            raise WakeError('wake_registration_not_ready')
        return json.loads(output.getvalue())
    raise WakeError('unknown_harness_operation')
