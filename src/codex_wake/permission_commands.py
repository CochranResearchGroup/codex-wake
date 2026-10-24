"""Public policy callers; roles are verified from host metadata/capabilities."""
import json
from pathlib import Path
from .session_permissions import PermissionStore, Principal, PermissionDenied


def tool_specs():
    from .harness_mcp import CALLER, TEXT
    result={'wake_permissions_show': ('permissions', 'show',
        'Explain effective action permission separately from runtime capability/readiness. Native identity is host verified; arguments cannot assign roles.',
        dict(caller_thread_id=CALLER, action=TEXT, target=TEXT,launch_profile=TEXT),
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
        Principal(arguments['caller_thread_id']), target=arguments.get('target'),launch_profile=arguments.get('launch_profile'))


def register_parser(subparsers):
    group=subparsers.add_parser('permissions',help='configure and explain common session action permissions')
    verbs=group.add_subparsers(dest='permission_command',required=True)
    for verb in ('configure','show','restrict','bind-domain','adoption-plan','adopt'):
        p=verbs.add_parser(verb)
        p.add_argument('--bus-root',type=Path,required=True)
        p.add_argument('--operator-capability',type=Path)
        p.add_argument('--actor-capability',type=Path)
        p.add_argument('--app-server',default='unix://')
        p.add_argument('--json',action='store_true')
        if verb in ('configure','restrict','adoption-plan','adopt'):
            p.add_argument('--file',type=Path,required=True)
            if verb!='adoption-plan':p.add_argument('--expected-revision',type=int,required=True)
        if verb in ('adoption-plan','adopt'):
            p.add_argument('--legacy-profiles',type=Path)
            p.add_argument('--hold-legacy-pending',action='store_true')
        if verb=='restrict':p.add_argument('--subject',required=True)
        if verb=='bind-domain':p.add_argument('--domain-root',type=Path,required=True)
        if verb=='show':
            p.add_argument('--action',required=True)
            p.add_argument('--target')
            p.add_argument('--subject')
            p.add_argument('--launch-profile')


def verified_cli_principal(args):
    from .a2a_bus import BusStore
    from .a2a_cli import invoking_actor
    if not args.bus_root or bool(args.operator_capability)==bool(args.actor_capability):
        raise PermissionDenied('permission_identity_unverified')
    bus=BusStore(args.bus_root)
    if args.operator_capability:
        with bus.connection() as database:
            bus.operator(database, Path(args.operator_capability))
        principal=Principal('local-operator','operator')
    elif args.actor_capability:
        if getattr(args,'actor_runtime','codex')=='grok':
            from .runtime_a2a import GrokMailboxRuntime
            runtime=GrokMailboxRuntime.from_actor(bus,Path(args.actor_capability))
            actor=runtime.authenticate(bus,Path(args.actor_capability))
        else:
            actor=invoking_actor(bus,Path(args.actor_capability),endpoint=args.app_server)
        with bus.connection() as database:
            bus.validate_actor(database,actor)
        principal=Principal(actor.thread_id)
    else:
        raise PermissionDenied('permission_identity_unverified')
    return principal


def _command(args,root):
    principal=verified_cli_principal(args)
    store=PermissionStore(root)
    if args.permission_command in ('configure','adopt','adoption-plan','bind-domain') and principal.role!='operator':
        raise PermissionDenied('permission_operator_required')
    if args.permission_command in ('configure','adopt'):
        from .a2a_bus import BusStore
        from .permission_a2a import binding
        bus=BusStore(args.bus_root)
        with bus.connection() as database:
            current=binding(bus,database)
        if current is not None and PermissionStore(current['root']).root!=store.root:
            raise PermissionDenied('permission_root_binding_conflict')
    if args.permission_command=='bind-domain':
        result=store.bind_domain(args.domain_root,principal)
    elif args.permission_command=='show':
        subject=args.subject or principal.subject
        if subject!=principal.subject and principal.role!='operator':
            raise PermissionDenied('permission_inspection_denied')
        result=store.evaluate(args.action,Principal(subject,principal.role),target=args.target,launch_profile=args.launch_profile)
    else:
        from .wake_policy import _read
        data=_read(args.file)
        if args.permission_command in ('adoption-plan','adopt'):
            from .permission_migration import plan,adopt
            if principal.role!='operator':raise PermissionDenied('permission_operator_required')
            result=(plan(root,data,legacy_profiles=args.legacy_profiles) if args.permission_command=='adoption-plan' else
                adopt(store,data,principal,expected_revision=args.expected_revision,legacy_profiles=args.legacy_profiles,hold_legacy_pending=args.hold_legacy_pending))
        else:
            if args.permission_command=='configure' and not store.active():
                from .permission_migration import plan
                proposal=plan(root,data)
                if not proposal['can_adopt']:raise PermissionDenied('permission_adoption_needs_resolution',proposal)
            result=(store.configure(data,principal,expected_revision=args.expected_revision)
                if args.permission_command=='configure' else store.change_session(
                    args.subject,data,principal,expected_revision=args.expected_revision))
    if args.permission_command in ('configure','adopt'):
        from .a2a_bus import BusStore
        binding=BusStore(args.bus_root).bind_permissions(store.root,Path(args.operator_capability))
        result['bus_binding']=binding
    print(json.dumps(result,sort_keys=True))
    return 0


def command(args,root):
    from .records import WakeError
    try:return _command(args,root)
    except (WakeError,OSError,ValueError,TypeError,KeyError) as exc:
        print(json.dumps({'error':{'code':getattr(exc,'code','permission_unavailable'),
            'message':str(exc)},'details':getattr(exc,'decision',None)}))
        return 2


def main():
    import sys
    from types import SimpleNamespace
    from .records import WakeError
    try:
        raw=sys.stdin.buffer.read(65537)
        if len(raw)>65536:raise ValueError('private permission packet exceeds limit')
        packet=json.loads(raw)
        result=mcp_call(SimpleNamespace(wake_root=Path(packet['root'])),packet['arguments'],
            packet['native_context'],packet['verb'])
        failed=False
    except (ValueError,OSError,TypeError,KeyError,WakeError) as exc:
        result={'error':{'code':getattr(exc,'code','permission_unavailable'),'message':str(exc)}}
        failed=True
    print(json.dumps(result))
    return 2 if failed else 0


if __name__=='__main__':raise SystemExit(main())
