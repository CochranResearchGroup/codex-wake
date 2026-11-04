"""CLI frame transport: presentation changes neither ownership nor operation identity."""
import json
import math
import sys
import time
from uuid import uuid4
from urllib.request import Request,build_opener,ProxyHandler

from .local_control_commands import output_exit_code,operation_exit_code,receipt_output,operation_schemas
from .local_control_routing import LocalSessionRouter


def _parsed(arguments):
    from .cli import build_parser
    from .command_contract import parser_paths
    arguments=list(arguments)
    if not arguments or arguments[0] not in ('control','self-limits'):arguments.insert(0,'control')
    parser=build_parser()
    if '--help' in arguments or '-h' in arguments:
        paths=dict(parser_paths(parser));path=[]
        for token in arguments:
            if token in ('--help','-h'):break
            if tuple(path+[token]) in paths:path.append(token)
            else:break
        return None,paths.get(tuple(path),parser).format_help()
    def error(message):raise ValueError(message)
    for path,child in parser_paths(parser):child.error=error
    return parser.parse_args(arguments),None


def _receipt_frames(value,mode,cursor=0):
    from .local_control_commands import receipt_exit_code
    output=receipt_output(value,mode,cursor=cursor)
    if mode in ('stream','final'):yield {'stdout':output['text']}
    elif mode=='transcript':yield {'stdout':json.dumps(output,sort_keys=True)+'\n'}
    code=receipt_exit_code(output)
    if code:yield {'stderr':json.dumps(dict(operation_id=output['operation_id'],execution=output['execution'],reason=output['reason'] or 'interaction_or_failure',result=value['result']['operation'].get('result')))+'\n'}
    yield {'exit_code':code}


def cli_frames(owner,arguments):
    try:
        args,help_text=_parsed(arguments)
        if help_text is not None:yield {'stdout':help_text};yield {'exit_code':0};return
        if args.command=='self-limits':
            values={k:v for k,v in vars(args).items() if k in ('selector','endpoint','token_limit','time_limit_seconds') and v is not None}
            value=owner.execute('local.self_limits.'+args.self_limits_verb,values)
            yield {'stdout':json.dumps(value,sort_keys=True)+'\n'};yield {'exit_code':0 if args.self_limits_verb=='show' or value.get('engagement',{}).get('engaged') or value.get('state')=='stopped' else 2};return
        if args.command!='control':raise ValueError('only local session control commands are available over this transport')
        verb=args.control_verb
        if verb=='slash':
            from .local_slash_commands import tool_specs
            schema=tool_specs()['wake_control_slash_'+args.slash_verb]
            values={k:v for k,v in vars(args).items() if k in schema[3] and k not in ('command','mode','cursor') and v is not None}
            if args.slash_verb=='run':values['command']=args.slash_command
            value=owner.execute('local.slash.'+args.slash_verb,values)
            if args.slash_verb=='list':yield {'stdout':json.dumps(value,sort_keys=True)+'\n'};yield {'exit_code':0}
            else:yield from _receipt_frames(value,args.mode,getattr(args,'cursor',0))
            return
        if verb in ('list','resolve','health','create'):
            schema=owner.definitions['local.'+verb][2]
            values={k:v for k,v in vars(args).items() if k in schema['properties'] and v is not None}
            value=owner.execute('local.'+verb,values);yield {'stdout':json.dumps(value,sort_keys=True)+'\n'};yield {'exit_code':operation_exit_code(value)};return
        if verb not in ('prompt','output','result','cancel'):raise ValueError('this command is managed locally, not through a client connection')
        schema=operation_schemas()['local.'+verb]
        values={k:v for k,v in vars(args).items() if k in schema['properties'] and v is not None}
        mode=values.pop('mode',None)
        timeout=values.pop('timeout',0)
        if not math.isfinite(timeout) or not 0<=timeout<=3600:raise ValueError('CLI wait timeout must be finite and0..3600seconds')
        if not mode:
            value=owner.execute('local.'+verb,dict(values,**({'timeout':min(30,timeout)} if 'timeout' in schema['properties'] else {})))
            yield {'stdout':json.dumps(value,sort_keys=True)+'\n'}
            yield {'exit_code':operation_exit_code(value)};return
        if verb=='prompt':
            submitted=owner.execute('local.prompt',dict(values,timeout=0));identifier=submitted['result']['operation']['operation_id']
        else:identifier=values['operation_id']
        yield from output_frames(owner,identifier,mode,timeout,values.get('cursor',0),values.get('limit',100))
    except (ValueError,OSError,TypeError,KeyError) as error:
        yield {'stderr':json.dumps(dict(status='failed',error=dict(code=getattr(error,'code','invalid_argument'),message=str(error))))+'\n'}
        yield {'exit_code':2}


def remote(root,arguments):
    from .local_control_server import connection_info
    info=connection_info(root)
    arguments=list(arguments)
    command=arguments if arguments[:1]==['control'] else ['control',*arguments]
    retry_key=None
    if len(command)>1 and command[0]=='control' and command[1] in ('prompt','create'):
        for index,argument in enumerate(arguments):
            if argument.startswith('--idempotency-key='):retry_key=argument.split('=',1)[1]
            elif argument=='--idempotency-key' and index+1<len(arguments):retry_key=arguments[index+1]
        if retry_key is None:
            retry_key=uuid4().hex;arguments.extend(['--idempotency-key',retry_key])
    request=Request(info['url']+'/cli',json.dumps({'arguments':arguments}).encode(),headers={'Content-Type':'application/json','Authorization':'Bearer '+info['token']})
    try:
        with build_opener(ProxyHandler({})).open(request,timeout=3700) as response:
            for raw in response:
                value=json.loads(raw)
                if 'stdout' in value:sys.stdout.write(value['stdout']);sys.stdout.flush()
                if 'stderr' in value:sys.stderr.write(value['stderr']);sys.stderr.flush()
                if 'exit_code' in value:return value['exit_code']
    except (OSError,ValueError) as error:
        if retry_key:
            raise ValueError('controller transport failed; retain the original intent and retry only with idempotency key '+retry_key) from error
        raise
    raise ValueError('controller connection ended without an exit receipt; retry only with the original idempotency key '+str(retry_key))


def output_frames(owner,identifier,mode,timeout,cursor=0,limit=100):
    yield {'operation_id':identifier}
    session=LocalSessionRouter(owner.root);deadline=time.monotonic()+timeout
    while True:
        output=session.output(identifier,mode=mode,cursor=cursor,limit=limit,timeout=max(0,min(30,deadline-time.monotonic())))
        yield {'output':output}
        if mode=='stream' and output.get('text'):yield {'stdout':output['text']}
        elif mode=='transcript':yield {'stdout':json.dumps(output,sort_keys=True)+'\n'}
        elif mode=='final' and output['terminal']:yield {'stdout':output.get('text','')}
        cursor=output['next_cursor']
        if mode in ('stream','transcript') and cursor<output['latest_cursor']:continue
        if output['terminal'] or output['phase']=='uncertain' or time.monotonic()>=deadline:
            code=output_exit_code(output)
            if code:yield {'stderr':json.dumps(dict(operation_id=identifier,reason=output['reason'] or ('output_incomplete' if output['terminal'] else 'wait_timeout'),next_cursor=cursor,retention=output['retention']))+'\n'}
            yield {'exit_code':code};return


def operation_frames(owner,operation,arguments):
    """NDJSON representation of the same typed operation, without CLI parsing."""
    try:
        arguments=owner.validated_arguments(operation,arguments)
        mode=arguments.pop('mode','stream')
        timeout=arguments.pop('timeout',0);cursor=arguments.pop('cursor',0);limit=arguments.pop('limit',100)
        if operation=='local.prompt':
            value=owner.execute(operation,arguments)
            identifier=value['result']['operation']['operation_id']
        elif operation in ('local.output','local.result'):identifier=arguments['operation_id']
        elif operation.startswith('local.slash.') and operation!='local.slash.list':
            yield from _receipt_frames(owner.execute(operation,arguments),mode,cursor);return
        else:
            value=owner.execute(operation,arguments)
            yield {'result':value};yield {'exit_code':operation_exit_code(value)};return
        yield from output_frames(owner,identifier,mode,timeout,cursor,limit)
    except (ValueError,OSError,TypeError,KeyError) as error:
        yield {'error':dict(code=getattr(error,'code','invalid_argument'),message=str(error))}
        yield {'exit_code':2}


def mcp_stdio(root):
    """A local MCP client needs only a command, never a copied bearer or OAuth grant."""
    from .local_control_server import connection_info
    for raw in sys.stdin:
        if len(raw.encode())>1048576:raise ValueError('MCP request exceeds local frame limit')
        request=json.loads(raw)
        info=connection_info(root)
        body=Request(info['url']+'/mcp',json.dumps(request).encode(),headers={'Content-Type':'application/json','Authorization':'Bearer '+info['token']})
        try:
            with build_opener(ProxyHandler({})).open(body,timeout=35) as response:
                value=response.read(4194305)
                if len(value)>4194304:raise ValueError('MCP result exceeds local frame limit')
                if 'id' in request:sys.stdout.write(value.decode()+'\n');sys.stdout.flush()
        except OSError:
            if 'id' in request:
                print(json.dumps(dict(jsonrpc='2.0',id=request['id'],error=dict(code=-32000,message='Local controller unavailable; retain the original intent and reconnect.'))),flush=True)
    return 0
