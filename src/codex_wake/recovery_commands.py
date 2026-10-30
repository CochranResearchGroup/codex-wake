"""Shared public contracts for explicit scoped controller recovery policies."""
import json


def tool_specs():
    from .notice_commands import tool_specs as notice_specs
    target=notice_specs()['wake_controller_notices_list'][3]['expected_target']
    request=notice_specs()['wake_controller_notices_publish'][3]['_request']
    text=dict(type='string',minLength=1,maxLength=200)
    action=dict(oneOf=[dict(type='object',properties=dict(kind=dict(const='notify_operator')),required=['kind'],additionalProperties=False),
        dict(type='object',properties=dict(kind=dict(const='cancel_owned_operation'),operation_id=text),required=['kind','operation_id'],additionalProperties=False),
        dict(type='object',properties=dict(kind=dict(const='thread_mcp_refresh'),profile=text),required=['kind','profile'],additionalProperties=False)])
    definition=dict(type='object',properties=dict(interval_seconds=dict(type='number',minimum=1,maximum=86400),
        probe_timeout=dict(type='number',minimum=.05,maximum=5),unknown_threshold=dict(type='integer',minimum=2,maximum=32),
        cooldown_seconds=dict(type='number',minimum=1,maximum=86400),max_attempts=dict(type='integer',minimum=1,maximum=32),
        evidence=dict(const='suspected_unresponsive'),actions=dict(type='array',minItems=1,maxItems=8,items=action)),
        required=['interval_seconds','probe_timeout','unknown_threshold','cooldown_seconds','max_attempts','evidence','actions'],additionalProperties=False)
    specs={}
    for verb in ('list','show','configure','enable','disable','check','tick','apply','reconcile'):
        properties={'expected_target':target};required=['expected_target']
        if verb!='list':properties['policy_id']=text;required.append('policy_id')
        if verb=='configure':properties['policy']=definition;required.append('policy')
        if verb not in ('list','show','reconcile'):properties['_request']=request;required.append('_request')
        specs['wake_controller_recovery_'+verb]=('controller-recovery','recovery.'+verb,
            'Inspect or drive an explicit scoped recovery policy; observation is default, deactivation preserves accounting and original in-flight outcomes.',
            properties,required,verb in ('list','show','check'))
    return specs


def protected_execute(operation,arguments,root):
    from .flow_commands import protected_execute as shared
    return shared(operation,arguments,root)


def register_parser(subparsers):
    parser=subparsers.add_parser('recovery',help='inspect, drive and deactivate explicit scoped recovery policies')
    commands=parser.add_subparsers(dest='recovery_verb',required=True)
    for verb in ('list','show','configure','enable','disable','check','tick','apply','reconcile'):
        commands.add_parser(verb).add_argument('--arguments',type=json.loads,required=True)


def command(args,root):
    result=protected_execute('recovery.'+args.recovery_verb,args.arguments,root)
    print(json.dumps(result,sort_keys=True))
    return 0 if result['status']=='completed' else 2
