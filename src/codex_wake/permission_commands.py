"""Public policy callers; roles are verified from host metadata/capabilities."""
import json
from pathlib import Path
from .session_permissions import PermissionStore, Principal, PermissionDenied


def tool_specs():
    from .harness_mcp import CALLER, TEXT
    result={'wake_permissions_show': ('permissions', 'show',
        'Explain effective action permission separately from runtime capability/readiness. Native identity is host verified; arguments cannot assign roles.',
        dict(caller_thread_id=CALLER, action=TEXT, target=TEXT),
        ['caller_thread_id', 'action'], True)}
    result['wake_permissions_update']=('permissions','update',
        'Restrict your own permissions or select an operator-preauthorized profile. Increases require existing scoped host delegation; arguments cannot assign authority.',
        dict(caller_thread_id=CALLER,subject=TEXT,layer={'type':'object'},expected_revision={'type':'integer','minimum':1}),
        ['caller_thread_id','subject','layer','expected_revision'],False)
    return result


def mcp_call(runner, arguments, native_context, verb="show"):
    from .goal_supervision import verified_native_caller
    verified_native_caller(native_context, arguments['caller_thread_id'])
    if runner.wake_root is None:
        raise PermissionDenied('permission_host_root_required')
    store=PermissionStore(runner.wake_root)
    if verb=='update':
        delegated=arguments['caller_thread_id'] in store._read()['policy'].get('delegations',{})
        principal=Principal(arguments['caller_thread_id'],'controller' if delegated else 'session')
        return store.change_session(arguments['subject'],arguments['layer'],principal,expected_revision=arguments['expected_revision'])
    return store.evaluate(arguments['action'],
        Principal(arguments['caller_thread_id']), target=arguments.get('target'))


def register_parser(subparsers):
    group=subparsers.add_parser('permissions',help='configure and explain common session action permissions')
    verbs=group.add_subparsers(dest='permission_command',required=True)
    for verb in ('configure','show','restrict'):
        p=verbs.add_parser(verb)
        p.add_argument('--bus-root',type=Path,required=True)
        p.add_argument('--operator-capability',type=Path)
        p.add_argument('--actor-capability',type=Path)
        p.add_argument('--app-server',default='unix://')
        p.add_argument('--json',action='store_true')
        if verb in ('configure','restrict'):
            p.add_argument('--file',type=Path,required=True)
            p.add_argument('--expected-revision',type=int,required=True)
        if verb=='restrict':p.add_argument('--subject',required=True)
        if verb=='show':
            p.add_argument('--action',required=True)
            p.add_argument('--target')
            p.add_argument('--subject')


def verified_cli_principal(args):
    from .a2a_bus import BusStore
    from .a2a_cli import invoking_actor
    bus=BusStore(args.bus_root)
    if args.operator_capability:
        with bus.connection() as database:
            bus.operator(database, Path(args.operator_capability))
        principal=Principal('local-operator','operator')
    elif args.actor_capability:
        actor=invoking_actor(bus,Path(args.actor_capability),endpoint=args.app_server)
        with bus.connection() as database:
            bus.validate_actor(database,actor)
        principal=Principal(actor.thread_id)
    else:
        raise PermissionDenied('permission_identity_unverified')
    return principal


def command(args,root):
    principal=verified_cli_principal(args)
    store=PermissionStore(root)
    if args.permission_command=='show':
        subject=args.subject or principal.subject
        if subject!=principal.subject and principal.role!='operator':
            raise PermissionDenied('permission_inspection_denied')
        result=store.evaluate(args.action,Principal(subject,principal.role),target=args.target)
    else:
        from .wake_policy import _read
        data=_read(args.file)
        result=(store.configure(data,principal,expected_revision=args.expected_revision)
                if args.permission_command=='configure' else store.change_session(
                    args.subject,data,principal,expected_revision=args.expected_revision))
    print(json.dumps(result,sort_keys=True))
    return 0
