"""Automatic same-user binding for voluntary limits, preserving explicit host policy."""
import hashlib
import os
from pathlib import Path

from .local_sessions import resolve
from .shortcut_store import locked,write,read
from .self_limits import local_execute


def execute(root,verb,arguments,*,selector=None,endpoint='unix://',policy=None):
    selector=selector or ('thread:'+os.environ['CODEX_THREAD_ID'] if os.environ.get('CODEX_THREAD_ID') else None)
    if selector is None:raise ValueError('choose your session selector, or run inside a session with CODEX_THREAD_ID')
    row=resolve(root,selector,endpoint=endpoint)
    if policy is None:
        # The resolved owned endpoint supplies the envelope. This is a private
        # voluntary policy, not an override of any configured external policy.
        directory=Path(root)/'self-limit-policies'
        key=hashlib.sha256((row['target']['home']+'\0'+row['endpoint']).encode()).hexdigest()
        policy=directory/(key+'.json')
        value=dict(version=2,native_caller_binding=True,allocations={},self_enrollment=dict(app_server=row['endpoint'],codex_path=row['target']['executable'],codex_home=row['target']['home'],max_tokens=2**53-1,max_seconds=315360000,rpc_timeout=5))
        with locked(directory):
            if policy.exists():
                if read(policy)!=value:raise ValueError('retained voluntary limit binding changed; inspect existing policy')
            else:write(policy,value)
    return local_execute(root,policy,verb,arguments,thread_id=row['thread_id'])


def register_parser(subparsers):
    parser=subparsers.add_parser('self-limits',help='inspect or enforce voluntary limits on your own session')
    verbs=parser.add_subparsers(dest='self_limits_verb',required=True)
    for verb in ('show','set'):
        command=verbs.add_parser(verb)
        command.add_argument('selector',nargs='?',help='owned session selector; defaults to CODEX_THREAD_ID')
        command.add_argument('--endpoint',default='unix://')
        command.add_argument('--policy',type=Path,help='optional existing host policy; never modified')
        if verb=='set':
            command.add_argument('--token-limit',type=int,required=True)
            command.add_argument('--time-limit-seconds',type=int,required=True)


def command(args,root):
    import json
    try:
        arguments={} if args.self_limits_verb=='show' else dict(token_limit=args.token_limit,time_limit_seconds=args.time_limit_seconds)
        value=execute(root,args.self_limits_verb,arguments,selector=args.selector,endpoint=args.endpoint,policy=args.policy)
        print(json.dumps(value,sort_keys=True));return 0 if args.self_limits_verb=='show' or value.get('engagement',{}).get('engaged') or value.get('state')=='stopped' else 2
    except (ValueError,OSError) as error:
        print(json.dumps({'status':'failed','error':{'code':getattr(error,'code','self_limits_unavailable'),'message':str(error)}}));return 2
