"""Local same-user controller CLI; remote transports share the operation owner."""
import json
from pathlib import Path


def register_parser(subparsers):
    parser=subparsers.add_parser('control',help='control existing same-user sessions without manual profiles')
    verbs=parser.add_subparsers(dest='control_verb',required=True)
    for verb in ('list','resolve'):
        item=verbs.add_parser(verb)
        item.add_argument('--endpoint',default='unix://',help='existing native Unix endpoint; default discovers running local daemons')
        if verb=='resolve':
            item.add_argument('selector');item.add_argument('--expected-target',type=json.loads)


def command(args,root):
    from .local_sessions import discover,resolve
    try:
        value=discover(root,args.endpoint) if args.control_verb=='list' else resolve(root,args.selector,args.expected_target,endpoint=args.endpoint)
        print(json.dumps(value,sort_keys=True));return 0
    except (ValueError,OSError) as error:
        print(json.dumps({'status':'failed','error':{'code':getattr(error,'code','control_unavailable'),'message':str(error)}}));return 2
