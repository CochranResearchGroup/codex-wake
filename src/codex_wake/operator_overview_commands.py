"""Terminal overview callers; models receive read projections only."""
import json
from pathlib import Path

from .operator_overview import OperatorOverview, OverviewError
from .records import WakeError
from .session_permissions import Principal


def execute(action, arguments, root, *, owner=None):
    if set(arguments) - {'managed_agent_id', 'limit', 'timeout', 'freshness'}:
        raise OverviewError('unsupported overview argument')
    owner = owner or OperatorOverview(root)
    if action == 'overview':
        return owner.snapshot(**arguments)
    if action == 'navigation_plan':
        return owner.navigation_plan(**arguments)
    raise OverviewError('model navigation effects unsupported')


def register_parser(commands):
    for verb in ('overview','focus'):
        parser=commands.add_parser(verb,help='inspect agents' if verb=='overview' else 'focus one existing terminal attachment')
        parser.add_argument('--timeout',type=float,default=10)
        parser.add_argument('--json',dest='as_json',action='store_true')
        parser.add_argument('--app-server',default='unix://')
        parser.add_argument('--tmux-socket')
        if verb=='overview':
            parser.add_argument('--limit',type=int,default=50)
            parser.add_argument('--freshness',type=float,default=30)
        else:
            parser.add_argument('--managed-agent-id',required=True)
            parser.add_argument('--bus-root',type=Path,required=True)
            parser.add_argument('--operator-capability',type=Path,required=True)


def run(args,root):
    try:
        owner=OperatorOverview(root, socket_path=args.tmux_socket,endpoint=args.app_server)
        if args.agents_command=='focus':
            from .a2a_bus import BusStore
            bus=BusStore(args.bus_root)
            with bus.connection() as database:
                bus.operator(database,args.operator_capability)
            value=owner.focus(args.managed_agent_id,principal=Principal('operator:'+bus.bus_id,'operator'),
                              timeout=args.timeout)
        else:
            value=owner.snapshot(limit=args.limit,timeout=args.timeout,freshness=args.freshness)
        if args.as_json or value['status']!='overview':
            print(json.dumps(value,sort_keys=True))
        else:
            print('AGENT\tRUNTIME\tSTATE\tFRESH\tBINDING\tTASK\tWORKSPACE\tREPOSITORY\tOBSERVED\tEVIDENCE\tREASON\tCAPABILITIES')
            for row in value['agents']:
                print('\t'.join(str(x) for x in (row['managed_agent_id'],row['runtime'],
                    row['semantic']['state'],row['semantic']['fresh'],row['binding']['state'],row['task_id'] or 'unassigned',
                    row['workspace'],'uninspected',row['semantic'].get('observed_at'),
                    row['semantic'].get('evidence_kind','unavailable'),row['semantic']['reason'],
                    json.dumps(row['semantic']['capabilities'],sort_keys=True))))
            print('managed-only inventory; complete='+str(value['complete'])+'; truncated='+str(value['truncated']))
        return 0 if value.get('complete',True) else 3
    except (WakeError,ValueError,TypeError,KeyError,OSError):
        print(json.dumps(dict(status='held',reason='overview_or_navigation_unavailable')))
        return 2
