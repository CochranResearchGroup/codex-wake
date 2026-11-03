"""Local-only server startup and client bootstrap, never exposed as remote actions."""
import json
import os
from pathlib import Path
import signal
import sys


def root_for(args):
    if args.wake_root is not None:return args.wake_root.expanduser().absolute()
    from .shortcut_store import preference_path,default_root
    if preference_path().exists():return default_root()
    return Path(os.environ.get('XDG_STATE_HOME',str(Path.home()/'.local/state')))/'codex-wake/controller'


def register(subparsers):
    item=subparsers.add_parser('server',help='start and inspect the same-user local controller')
    verbs=item.add_subparsers(dest='local_server_verb',required=True)
    for verb in ('start','run','status','stop'):
        command=verbs.add_parser(verb)
        if verb in ('start','run'):
            command.add_argument('--port',type=int,default=0)
            command.add_argument('--native-endpoint',default='unix://')
    subparsers.add_parser('mcp',help='local MCP stdio client with automatic private connection bootstrap')
    subparsers.add_parser('connection',help='private pipe-only client connection bootstrap')
    client=subparsers.add_parser('remote',help='run control arguments through the local server')
    import argparse
    client.add_argument('remote_arguments',nargs=argparse.REMAINDER)
    powershell=subparsers.add_parser('powershell',help='render the native Windows PowerShell client')
    powershell.add_argument('--distro',help='explicit WSL distribution; normally discovered automatically')


def command(args,root):
    from .local_control_server import connection_info,start,LocalControllerServer
    try:
        if args.control_verb=='powershell':
            from .powershell_client import render
            print(render(root,distro=args.distro));return 0
        if args.control_verb=='mcp':
            from .local_control_client import mcp_stdio
            return mcp_stdio(root)
        if args.control_verb=='remote':
            from .local_control_client import remote
            return remote(root,args.remote_arguments)
        if args.control_verb=='connection':
            if sys.stdout.isatty():raise ValueError('connection bootstrap is private; use it only through a captured pipe')
            print(json.dumps(connection_info(root)));return 0
        verb=args.local_server_verb
        if verb=='start':value=start(root,port=args.port,native_endpoint=args.native_endpoint)
        elif verb=='run':
            with LocalControllerServer(root,port=args.port,native_endpoint=args.native_endpoint) as server:server.serve_forever()
            return 0
        else:
            value=connection_info(root)
            if verb=='stop':os.kill(value['pid'],signal.SIGTERM);value=dict(status='stop_requested',pid=value['pid'])
        print(json.dumps({k:v for k,v in value.items() if k!='token'}));return 0
    except (ValueError,OSError,KeyError) as error:
        print(json.dumps(dict(status='failed',error=dict(code=getattr(error,'code','controller_unavailable'),message=str(error)))),file=sys.stderr);return 2
