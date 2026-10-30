"""Schemas for host-profile session actions used by durable flow compilation."""
import json


def tool_specs():
    text = {'type': 'string', 'minLength': 1, 'maxLength': 200}
    result = {}
    for verb in ('capabilities','create','prompt','wait','cancel'):
        if verb in ('wait','cancel'):
            properties = {'operation_id': text}
            required = ['operation_id']
            if verb == 'wait':
                properties['timeout'] = {'type':'number','minimum':0,'maximum':30}
        else:
            properties = {'profile': text, 'expected_target': {'type':'object'}}
            required = list(properties)
            if verb in ('create','prompt'):
                properties['_request'] = {'type':'object'}
                required.append('_request')
            if verb == 'prompt':
                properties['prompt'] = {'type':'string','minLength':1,'maxLength':32768}
                required.append('prompt')
        result['wake_flow_sessions_' + verb] = ('controller-flow-sessions','sessions.' + verb,
            'Use an exact host-owned native session profile under inherited authority; no new allowance or fallback executor.',
            properties,required,verb in ('capabilities','wait'))
    return result


def execute(operation, arguments, root, *, actor, authorize):
    from .controller_flow_sessions import ControllerFlowSessions
    return ControllerFlowSessions(root).execute(actor,operation,arguments,authorize=authorize)


def protected_execute(operation,arguments,root):
    from .flow_commands import protected_execute as shared
    return shared(operation,arguments,root)


def register_parser(subparsers):
    parser = subparsers.add_parser('flow-sessions',help='inspect and control pinned host-profile native sessions')
    verbs = parser.add_subparsers(dest='flow_session_verb',required=True)
    for name,spec in tool_specs().items():
        command = verbs.add_parser(spec[1].split('.')[1])
        command.add_argument('--arguments',type=json.loads,required=True)


def command(args,root):
    result = protected_execute('sessions.' + args.flow_session_verb,args.arguments,root)
    print(json.dumps(result,sort_keys=True))
    return 0 if result['status']=='completed' else 2
