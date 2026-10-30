"""CLI and MCP adapter for Wake build operations; no caller-supplied host paths."""
import json


def execute(owner, operation, arguments):
    return owner.execute('builds.' + operation, arguments)


def register_parser(subparsers):
    parser = subparsers.add_parser('builds')
    commands = parser.add_subparsers(dest='build_command', required=True)
    for verb in ('list', 'launch', 'stage', 'rollback'):
        item = commands.add_parser(verb)
        item.add_argument('--arguments', type=json.loads, default={})
    return parser


def command(args, owner):
    print(json.dumps(execute(owner, args.build_command, args.arguments), sort_keys=True))
    return 0
