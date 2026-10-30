"""Controller Grok ACP contracts, separate from legacy terminal wake commands."""
import json


def tool_specs():
    text=dict(type='string',minLength=1,maxLength=200)
    result={}
    for verb in ('capabilities','create','load','prompt','wait','cancel','health','checkpoint','fork'):
        if verb in ('wait','cancel'):
            properties={'operation_id':text};required=['operation_id']
            if verb=='wait':properties['timeout']=dict(type='number',minimum=0,maximum=30)
        else:
            properties=dict(profile=text,expected_target=dict(type='object'));required=['profile','expected_target']
            if verb in ('create','load','prompt','fork'):
                properties['_request']=dict(type='object');required.append('_request')
            if verb=='prompt':properties['prompt']=dict(type='string',minLength=1,maxLength=32768);required.append('prompt')
        result['wake_controller_grok_'+verb]=('controller-grok','grok.'+verb,
            'Use negotiated Grok ACP on a host-owned structured endpoint; unsupported health/fork/metering never falls back to terminal input.',
            properties,required,verb in ('capabilities','wait','health','checkpoint'))
    return result


def protected_execute(operation,arguments,root):
    from .flow_commands import protected_execute as shared
    return shared(operation,arguments,root)


def register_verbs(commands):
    """Extend the existing grok resource tree without replacing legacy verbs."""
    for verb in ('capabilities','create','load','prompt','wait','cancel','health','checkpoint','fork'):
        commands.add_parser(verb).add_argument('--arguments',type=json.loads,required=True)


def command(args,root):
    result=protected_execute('grok.'+args.grok_command,args.arguments,root)
    print(json.dumps(result,sort_keys=True))
    return 0 if result['status']=='completed' else 2
