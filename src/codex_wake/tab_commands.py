"""Controller attachment CLI adapter over the host-owned operation service."""
import json


def register_parser(subparsers):
    parser = subparsers.add_parser('tabs')
    commands = parser.add_subparsers(dest='tab_command', required=True)
    for verb in ('list','show','preview','apply','undo','capture','input'):
        item = commands.add_parser(verb)
        item.add_argument('--arguments', type=json.loads, default={})
    return parser


def command(args, owner=None):
    if owner is None:
        from .controller_tabs import controller_tabs_from_root
        owner = controller_tabs_from_root(args.wake_root)
    operation = 'tabs.' + args.tab_command
    value = owner.execute(operation,args.arguments) if args.tab_command in ('list','show') else protected_execute(operation,args.arguments,args.wake_root)
    print(json.dumps(value, sort_keys=True))
    return 0


def tool_specs():
    text = {'type':'string'}
    specs = {}
    for verb in ('list','show','preview','apply','undo','capture','input'):
        properties = {} if verb=='list' else {'workspace':text}
        required = [] if verb=='list' else ['workspace']
        if verb=='show': properties['selector']=text
        if verb not in ('list','show'):
            properties.update(expected_target={'type':'object'},_request={'type':'object'})
            required += ['expected_target','_request']
        if verb=='preview': properties.update(mode={'enum':['activity','repository']},pins={'type':'array','items':text})
        if verb=='apply': properties['plan_id']=text; required += ['plan_id']
        if verb=='undo': properties['receipt_id']=text; required += ['receipt_id']
        if verb in ('capture','input'): properties['pane']=text; required += ['pane']
        if verb=='capture': properties['lines']={'type':'integer','minimum':1,'maximum':200}
        if verb=='input':
            properties.update(input={'type':'string','maxLength':16384},custody={'type':'object'},transport={'enum':['structured','terminal']})
            required += ['input','custody','transport']
        specs['wake_tabs_'+verb]=('controller-tabs','tabs.'+verb,'Use host-enrolled presentation with exact generation and explicit input custody; no automatic replacement.',properties,required,verb in ('list','show'))
    return specs


def protected_execute(operation,arguments,root):
    from types import SimpleNamespace
    from .controller_tabs import controller_tabs_from_root
    from .controller_operations import ControllerOperations
    from .controller_http import ProtectedOperations
    from .managed_inventory import ManagedInventory
    from .operation_commands import local_actor
    tabs=controller_tabs_from_root(root)
    operations=ControllerOperations(ManagedInventory(root),host=tabs.host,environment=tabs.environment,tabs=tabs)
    authority=SimpleNamespace(authenticate=lambda unused:local_actor(root))
    return ProtectedOperations(authority,operations).execute('host-local-grant',operation,arguments)
