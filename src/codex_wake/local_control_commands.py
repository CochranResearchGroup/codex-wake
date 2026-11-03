"""Local same-user controller CLI; remote transports share the operation owner."""
import json
from pathlib import Path


def register_parser(subparsers):
    parser=subparsers.add_parser('control',help='control existing same-user sessions without manual profiles')
    verbs=parser.add_subparsers(dest='control_verb',required=True)
    for verb in ('list','resolve','prompt','result','cancel'):
        item=verbs.add_parser(verb)
        item.add_argument('--endpoint',default='unix://',help='existing native Unix endpoint; default discovers running local daemons')
        if verb in ('resolve','prompt'):
            item.add_argument('selector');item.add_argument('--expected-target',type=json.loads)
        if verb=='prompt':
            item.add_argument('prompt');item.add_argument('--idempotency-key',required=True)
        if verb in ('result','cancel'):item.add_argument('operation_id')
        if verb=='result':item.add_argument('--timeout',type=float,default=0)


def command(args,root):
    from .local_sessions import discover,resolve
    try:
        from .local_session_operations import LocalSessionControl
        owner=LocalSessionControl(root) if args.control_verb not in ('list','resolve') else None
        if args.control_verb=='list':value=discover(root,args.endpoint)
        elif args.control_verb=='resolve':value=resolve(root,args.selector,args.expected_target,endpoint=args.endpoint)
        elif args.control_verb=='prompt':value=owner.prompt(args.selector,args.prompt,args.idempotency_key,endpoint=args.endpoint,expected_target=args.expected_target)
        elif args.control_verb=='result':value=owner.result(args.operation_id,args.timeout)
        else:value=owner.cancel(args.operation_id)
        print(json.dumps(value,sort_keys=True));return 0
    except (ValueError,OSError) as error:
        print(json.dumps({'status':'failed','error':{'code':getattr(error,'code','control_unavailable'),'message':str(error)}}));return 2
