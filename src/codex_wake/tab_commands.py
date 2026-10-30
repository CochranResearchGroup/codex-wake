"""Controller attachment CLI adapter over the host-owned operation service."""
import json


def register_parser(subparsers):
    parser = subparsers.add_parser('tabs')
    commands = parser.add_subparsers(dest='tab_command', required=True)
    for verb in ('list','show','preview','apply','undo','capture','input'):
        item = commands.add_parser(verb)
        item.add_argument('--arguments', type=json.loads, default={})
    return parser


def command(args, owner):
    print(json.dumps(owner.execute('tabs.' + args.tab_command, args.arguments), sort_keys=True))
    return 0
