"""Current harness frontier callers; runtime configuration and roles stay host-owned."""
from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path
from types import SimpleNamespace

from .records import WakeError
from .session_permissions import Principal

TEXT = {'type': 'string', 'minLength': 1, 'maxLength': 256}
CALLER = {'type': 'string', 'pattern': '^[0-9a-f-]{36}$'}


def tool_specs():
    result = {}
    def add(name, verb, properties, required, readonly=False):
        result[name] = ('frontier', verb, 'Use exact scoped harness state. Host identity, permissions, profiles and runtime evidence are independent; no caller-selected role.', properties, required, readonly)
    for action in ('list', 'show', 'request'):
        properties = dict(caller_thread_id=CALLER)
        required = ['caller_thread_id']
        if action == 'list':
            properties['include_closed'] = {'type': 'boolean'}
        elif action == 'show':
            properties['request_id'] = TEXT
            required.append('request_id')
        else:
            properties.update(request={'type': 'object'}, assignment_id=TEXT)
            required.append('request')
        add('wake_attention_' + action, 'attention:' + action, properties, required, action != 'request')
    for action in ('define', 'evaluate', 'inspect', 'decide'):
        properties = dict(caller_thread_id=CALLER, contract_id=TEXT)
        required = ['caller_thread_id', 'contract_id']
        if action == 'define':
            properties.update(task_id=TEXT, assignment_id=TEXT, checks={'type': 'object'})
            required += ['task_id', 'assignment_id', 'checks']
        if action == 'evaluate':
            properties['managed_agent_id'] = TEXT
        if action == 'decide':
            properties.update(name=TEXT, outcome={'enum': ['accepted', 'rejected']}, expires_at={'type': 'number'})
            required += ['name', 'outcome', 'expires_at']
        add('wake_acceptance_' + action, 'acceptance:' + action, properties, required, action == 'inspect')
    for action in ('profile', 'launch', 'show', 'cancel', 'await'):
        properties = dict(caller_thread_id=CALLER)
        required = ['caller_thread_id']
        key = 'profile' if action in ('profile', 'launch') else 'job_id'
        properties[key] = TEXT
        required.append(key)
        if action == 'launch':
            properties['idempotency_key'] = TEXT
            required.append('idempotency_key')
        if action == 'cancel':
            properties['generation'] = {'type': 'integer', 'minimum': 1}
            required.append('generation')
        if action == 'await':
            properties['ttl'] = TEXT
        add('wake_jobs_' + action, 'jobs:' + action, properties, required, action in ('profile', 'show'))
    add('wake_agents_overview', 'overview:overview', dict(limit={'type': 'integer', 'minimum': 1, 'maximum': 100},
        timeout={'type': 'number', 'exclusiveMinimum': 0, 'maximum': 30}, freshness={'type': 'number', 'exclusiveMinimum': 0, 'maximum': 300}), [], True)
    add('wake_agents_navigation_plan', 'overview:navigation_plan', dict(managed_agent_id=TEXT,
        timeout={'type': 'number', 'exclusiveMinimum': 0, 'maximum': 30}), ['managed_agent_id'], True)
    for action in ('preview', 'show'):
        properties = dict(caller_thread_id=CALLER, timeout={'type': 'number', 'exclusiveMinimum': 0, 'maximum': 30})
        required = ['caller_thread_id']
        if action == 'preview':
            properties.update(session_id=TEXT, mode={'enum': ['activity', 'repository']},
                              pins={'type': 'array', 'maxItems': 100, 'items': TEXT})
            required.append('session_id')
        else:
            properties['plan_id'] = TEXT
            required.append('plan_id')
        add('wake_tabs_' + action, 'tabs:' + action, properties, required, True)
    for action in ('inspect', 'reconcile'):
        properties = dict(caller_thread_id=CALLER, profile=TEXT)
        required = ['caller_thread_id', 'profile']
        if action == 'reconcile':
            properties['operation'] = TEXT
            required.append('operation')
        add('wake_interactions_' + action, 'interactions:' + action, properties, required, True)
    return result


def native_principal(runner, arguments, native_context, task_id=None, assignment_id=None):
    from .goal_supervision import verified_native_caller
    from .harness_mcp import controller_tasks
    from .permission_enforcement import verified_tasks
    caller = arguments['caller_thread_id']
    verified_native_caller(native_context, caller)
    delegated = controller_tasks(runner, caller)
    tasks = verified_tasks(runner.wake_root, caller, task_id, assignment_id, controller_tasks=delegated) if task_id else ()
    return Principal(caller, 'controller' if task_id in delegated else 'session', tasks=tasks)


def job_awaiter(root, endpoint, principal, *, ttl='24h'):
    """Retain the existing exact-owner native file wake, not another dispatcher."""
    def register(path, key, snapshot):
        from uuid import UUID
        from .cli import run
        owner = snapshot['intent']['owner']
        UUID(owner)  # Non-conversation owners cannot acquire a guessed resume target.
        pin = snapshot['intent']['profile']['command']['task_pin']
        prompt = 'Background job ' + snapshot['job_id'] + ' has a result. Inspect its exact receipt before continuing.'
        argv = ['--wake-root', str(root), 'native', 'file', '--endpoint', endpoint,
            '--json', '--idempotency-key', key, '--ttl', ttl,
            '--wake-lifetime', 'task', '--owner-id', pin['task_id'], '--owner-end', 'retire',
            owner, str(path), '--', prompt]
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = run(argv, permission_principal=principal)
        if code:
            raise WakeError('job_result_wake_not_ready')
        return json.loads(output.getvalue())
    return register


def call(runner, verb, arguments, native_context):
    if runner.wake_root is None:
        raise WakeError('host_wake_root_required')
    root = Path(runner.wake_root)
    family, action = verb.split(':', 1)
    if family == 'overview':
        from .operator_overview import OperatorOverview
        from .operator_overview_commands import execute
        return execute(action, arguments, root, owner=OperatorOverview(root, endpoint=runner.app_server, socket_path=runner.tmux_socket))
    if family == 'attention':
        from .attention_commands import execute
        request = arguments.get('request', {})
        task_id = request.get('context', {}).get('task_id') if action == 'request' else None
        principal = native_principal(runner, arguments, native_context, task_id, arguments.get('assignment_id'))
        clean = {key:value for key,value in arguments.items() if key not in ('caller_thread_id', 'assignment_id')}
        return execute(action, clean, root, principal=principal, native_context=native_context, mcp=True)
    if family == 'acceptance':
        from .task_briefs import BriefAuthority
        from .work_acceptance import WorkAcceptance
        from .work_acceptance_commands import execute, qualified_claimant
        if action == 'define':
            task_id, assignment = arguments['task_id'], arguments['assignment_id']
        else:
            contract = WorkAcceptance(root).contract(arguments['contract_id'])
            task_id, assignment = contract['task_id'], contract['pin']['assignment_id']
        principal = native_principal(runner, arguments, native_context, task_id, assignment)
        authority = BriefAuthority('native:' + principal.subject,
            'controller' if principal.role == 'controller' else 'worker', principal.tasks)
        claimant = None
        if action == 'evaluate' and WorkAcceptance(root).contract(arguments['contract_id'])['checks']['verifiers']:
            from .managed_inventory_commands import RuntimeObserver
            claimant = qualified_claimant(root, arguments['managed_agent_id'], principal,
                observer=RuntimeObserver(endpoint=runner.app_server, socket_path=runner.tmux_socket))
        return execute(action, {key:value for key,value in arguments.items() if key not in ('caller_thread_id', 'managed_agent_id')},
            root, principal=principal, authority=authority, claimant=claimant)
    if family == 'jobs':
        from .background_jobs import BackgroundJobs
        from .background_job_commands import execute
        store = BackgroundJobs(root)
        command = (store.profile(arguments['profile'])['command'] if action in ('profile', 'launch')
                   else store.inspect(arguments['job_id'])['intent']['profile']['command'])
        pin = command['task_pin']
        principal = native_principal(runner, arguments, native_context, pin['task_id'], pin['assignment_id'])
        args = SimpleNamespace(job_command=action, **{key:value for key,value in arguments.items() if key != 'caller_thread_id'})
        from .managed_inventory_commands import RuntimeObserver
        return execute(args, root, principal=principal, observer=RuntimeObserver(endpoint=runner.app_server, socket_path=runner.tmux_socket),
            register_wake=job_awaiter(root, runner.app_server, principal, ttl=arguments.get('ttl', '24h')))
    if family == 'interactions':
        from .guarded_interaction_commands import execute
        native_principal(runner, arguments, native_context)
        return execute(action, {key:value for key,value in arguments.items() if key != 'caller_thread_id'}, root)
    if family == 'tabs':
        from .tab_organization_commands import execute
        principal = native_principal(runner, arguments, native_context)
        clean = {key:value for key,value in arguments.items() if key != 'caller_thread_id'}
        clean.update(socket_path=runner.tmux_socket, app_server=runner.app_server)
        return execute(action, clean, root, principal=principal, mcp=True, native_context=native_context)
    raise WakeError('unsupported_frontier_operation')
