"""CLI/MCP resume callers authenticate before the shared effect owner."""
import json
from pathlib import Path

from .agent_resume import AgentResume, ResumeError
from .goal_supervision import _private, verified_native_caller
from .session_permissions import Principal, PermissionStore
from .records import WakeError


def load_profiles(path):
    path=Path(path).absolute()
    if path!=path.resolve():raise ResumeError('resume_profile_not_canonical')
    _private(path)
    if path.stat().st_size>262144:raise ResumeError('resume_profile_too_large')
    return json.loads(path.read_text())


def execute(arguments, root, profiles, principal, *, runtime=None, now=None):
    try:
        owner=AgentResume(root,load_profiles(profiles),runtime=runtime,now=now,
                          config_loader=lambda:load_profiles(profiles))
        return owner.resume(arguments,principal)
    except (WakeError,ValueError,TypeError,KeyError,OSError):
        # Detailed local paths and protocol errors never enter public projections.
        import sys
        error=sys.exception()
        return {'status':'held','error':{'code':getattr(error,'code','resume_unavailable'),
                                       'message':'Exact saved conversation could not be resumed.'}}


def register_parser(commands):
    p=commands.add_parser('resume',help='resume one exact managed saved conversation')
    for name in ('managed-agent-id','profile','intent','expires-at','profiles','bus-root'):
        p.add_argument('--'+name,required=True)
    p.add_argument('--operator-capability')
    p.add_argument('--actor-capability')
    p.add_argument('--app-server',default='unix://')
    p.add_argument('--record-sha256')
    p.add_argument('--assignment-id')
    p.add_argument('--json',dest='as_json',action='store_true')


def run(args,root, *, runtime=None, now=None):
    from .permission_commands import verified_cli_principal
    try:
        principal=verified_cli_principal(args)
        if principal.role != 'operator':
            from .managed_inventory import ManagedInventory
            from .permission_enforcement import verified_tasks
            agent=ManagedInventory(root).inspect(args.managed_agent_id)['agent']
            tasks=verified_tasks(root,principal.subject,agent.get('task_id'),args.assignment_id,
                                 actor_id=getattr(args,'permission_actor_id',None))
            principal=Principal(principal.subject,principal.role,tasks=tasks)
        value=execute(vars(args),root,args.profiles,principal,runtime=runtime,now=now)
    except (WakeError,ValueError,TypeError,KeyError,OSError) as error:
        value={'status':'held','error':{'code':getattr(error,'code','resume_identity_unverified')}}
    print(json.dumps(value,sort_keys=True))
    return 0 if value.get('status')=='resumed' else 2


def tool_specs():
    text={'type':'string','minLength':1,'maxLength':256}
    names=('managed_agent_id','profile','intent','expires_at','caller_thread_id')
    return {'wake_agents_resume':('agents','resume',
        'Resume the exact managed saved conversation with a host-approved named profile. '
        'Fresh binding is required; uncertainty never starts another conversation or renews allowance.',
        {**{name:text for name in names},'record_sha256':text,'assignment_id':text},list(names),False)}


def mcp_call(runner,arguments,native_context, *, runtime=None, now=None):
    try:
        caller=arguments['caller_thread_id']
        verified_native_caller(native_context,caller)
        if runner.wake_root is None or runner.lifecycle_profiles is None:
            raise ResumeError('resume_host_configuration_required')
        store=PermissionStore(runner.wake_root)
        delegated=caller in store._read()['policy'].get('delegations',{})
        from .managed_inventory import ManagedInventory
        from .permission_enforcement import verified_tasks
        from .harness_mcp import controller_tasks
        agent=ManagedInventory(runner.wake_root).inspect(arguments['managed_agent_id'])['agent']
        tasks=verified_tasks(runner.wake_root,caller,agent.get('task_id'),arguments.get('assignment_id'),
                             controller_tasks=controller_tasks(runner,caller) if agent.get('task_id') else ())
        principal=Principal(caller,'controller' if delegated else 'session',tasks=tasks)
        return execute(arguments,runner.wake_root,runner.lifecycle_profiles,principal,runtime=runtime,now=now)
    except (WakeError,ValueError,TypeError,KeyError,OSError) as error:
        return {'status':'held','error':{'code':getattr(error,'code','resume_identity_unverified')}}
