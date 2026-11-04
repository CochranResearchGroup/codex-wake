"""Presentation adapter for exact native slash actions."""
import json
import sys
from .local_slash_commands import tool_specs
from .local_control_commands import present_receipt


def command(args,root):
    try:
        schema=tool_specs()['wake_control_slash_'+args.slash_verb]
        arguments={key:value for key,value in vars(args).items() if key in schema[3] and key not in ('command','mode','cursor') and value is not None}
        if args.slash_verb=='run':arguments['command']=args.slash_command
        from .local_control_service import LocalOperations
        value=LocalOperations(root).execute('local.slash.'+args.slash_verb,arguments)
        if args.slash_verb=='list':print(json.dumps(value,sort_keys=True));return 0
        return present_receipt(value,args.mode,cursor=getattr(args,'cursor',0))
    except (ValueError,OSError) as error:
        print(json.dumps({'status':'failed','error':{'code':getattr(error,'code','slash_unavailable'),'message':str(error)}}),file=sys.stderr);return 2
