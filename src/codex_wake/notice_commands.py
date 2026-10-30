"""One public controller notice contract for CLI, API and MCP."""
import json

from .controller_health import _TARGET_FIELDS


def tool_specs():
    text = dict(type='string',minLength=1,maxLength=4096)
    keys = sorted((_TARGET_FIELDS-{'process'}) | {'process_pid','process_start_ticks','process_boot_id'})
    target = dict(type='object',properties={key:text for key in keys},required=keys,additionalProperties=False)
    result = {}
    for verb in ('list','publish','reconcile'):
        properties, required = {'expected_target':target}, ['expected_target']
        if verb == 'list':
            properties['cursor'] = dict(type='integer',minimum=0,maximum=10000)
        else:
            key = 'source_operation_id' if verb=='publish' else 'operation_id'
            properties[key] = dict(type='string',minLength=1,maxLength=200)
            required.append(key)
        if verb == 'publish':
            properties['_request'] = dict(type='object',properties={
                **{key:dict(type='string',minLength=1,maxLength=200) for key in
                    ('operation_id','idempotency_key','correlation_id','binding')},'target':target},
                required=['operation_id','idempotency_key','correlation_id','binding','target'],additionalProperties=False)
            required.append('_request')
        result['wake_controller_notices_'+verb] = ('controller-notices','notices.'+verb,
            'Inspect or publish owned controller action notices without a model turn; uncertain delivery requires original readback.',
            properties,required,verb=='list')
    return result


def protected_execute(operation,arguments,root):
    from .flow_commands import protected_execute as shared
    return shared(operation,arguments,root)


def register_parser(subparsers):
    parser = subparsers.add_parser('notices',help='inspect controller intervention and action notices')
    verbs = parser.add_subparsers(dest='notice_verb',required=True)
    for verb in ('list','publish','reconcile'):
        verbs.add_parser(verb).add_argument('--arguments',type=json.loads,required=True)


def command(args,root):
    result = protected_execute('notices.'+args.notice_verb,args.arguments,root)
    print(json.dumps(result,sort_keys=True))
    return 0 if result['status']=='completed' else 2
