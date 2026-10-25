"""CLI and MCP callers share read-only managed-agent observation semantics."""
from __future__ import annotations

import json

from .agent_observation import AgentObservation, RuntimeStateObserver, STATES
from .records import WakeError


def execute(action, arguments, root, *, observer=None):
    owner = AgentObservation(root, observer=observer or RuntimeStateObserver())
    options = dict(freshness=arguments.get('freshness', 30), timeout=arguments.get('timeout', 60 if action == 'wait' else 10))
    if action == 'observe':
        return owner.observe(arguments['managed_agent_id'], **options)
    if action == 'wait':
        return owner.wait(arguments['managed_agent_id'], state=arguments['state'],
                          interval=arguments.get('interval', 1), **options)
    raise ValueError('unknown observation operation')


def register_parser(commands):
    for action in ('observe', 'wait'):
        command = commands.add_parser(action, help='read semantic runtime state without sending input')
        command.add_argument('--managed-agent-id', required=True)
        command.add_argument('--app-server', default='unix://')
        command.add_argument('--runtime-root', help='existing local Grok runtime root for read-only observation')
        command.add_argument('--binding-id')
        command.add_argument('--binding-sha256')
        command.add_argument('--freshness', type=float, default=30)
        command.add_argument('--timeout', type=float, default=60 if action == 'wait' else 10)
        command.add_argument('--json', dest='as_json', action='store_true')
        if action == 'wait':
            command.add_argument('--state', choices=STATES, required=True)
            command.add_argument('--interval', type=float, default=1)


def run(args, root):
    try:
        arguments = dict(managed_agent_id=args.managed_agent_id, freshness=args.freshness, timeout=args.timeout)
        if args.agents_command == 'wait':
            arguments.update(state=args.state, interval=args.interval)
        from .agent_observation import grok_state_source
        grok = None
        if args.runtime_root and args.binding_id and args.binding_sha256:
            grok = grok_state_source(args.runtime_root, args.binding_id, args.binding_sha256)
        value = execute(args.agents_command, arguments, root,
                        observer=RuntimeStateObserver(endpoint=args.app_server, grok_source=grok))
        print(json.dumps(value, sort_keys=True))
        return 0 if value.get('status') not in ('timeout', 'unknown') else 3
    except (WakeError, ValueError, TypeError, KeyError, OSError) as error:
        print(json.dumps(dict(status='held', error=dict(code=getattr(error, 'code', 'observation_unavailable'),
                         message='Semantic observation or request is unavailable.')), sort_keys=True))
        return 2
