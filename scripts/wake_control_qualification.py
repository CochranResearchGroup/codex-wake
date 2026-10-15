import asyncio,contextlib,hashlib,json,os,subprocess,tempfile
from pathlib import Path
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client
from codex_wake.records import build_record,write_record
from codex_wake import __version__
import codex_wake
import argparse
parser=argparse.ArgumentParser(description='Isolated installed wake-control CLI/MCP qualification; zero native model turns.')
parser.add_argument('--prefix',type=Path,required=True)
parser.add_argument('--source-root',type=Path,default=Path(__file__).resolve().parents[1])
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
prefix=args.prefix.resolve();cli=str(prefix/'bin/codex-wake');mcp=str(prefix/'bin/codex-wake-mcp')
repo=args.source_root.resolve()
source=repo/'src/codex_wake';installed=Path(codex_wake.__file__).parent
matched=[]
for p in source.rglob('*.py'):
 assert p.read_bytes()==(installed/p.relative_to(source)).read_bytes(),p
 matched.append(str(p.relative_to(source)))
env=dict(os.environ);env.pop('PYTHONPATH',None);env['CODEX_WAKE_STABLE_TIME_CONFIG']=''
with tempfile.TemporaryDirectory(prefix='codex-wake-p164-qualification-') as tmp:
 base=Path(tmp);env['XDG_STATE_HOME']=str(base/'state');a=base/'a';b=base/'b';registry=base/'registry';registry.mkdir()
 for i,root in enumerate((a,b)):
  record=build_record(predicate={'type':'not_before','due_at':'2020-01-01T00:00:00Z'},prompt='fixture only',cwd=root,
     target={'transport':'tmux','socket_path':str(base/'nonexistent.sock'),'session_id':'fixture','pane_id':'%999999'})
  record['next_attempt_at']='2020-01-01T00:00:00Z';write_record(root,record)
  (registry/(str(i)+'.json')).write_text(json.dumps(dict(schema_version=1,wake_root=str(root),enabled=False)))
 def invoke(*args):
  result=subprocess.run([cli,'--wake-root',str(a),*args],capture_output=True,text=True,env=env,timeout=15)
  assert result.returncode==0,(args,result.stdout,result.stderr)
  return json.loads(result.stdout)
 invoke('pause','--all-roots','--registry-dir',str(registry),'--json')
 polled=subprocess.run([str(prefix/'bin/codex-waked'),'--once','--wake-root',str(a)],capture_output=True,text=True,env=env,timeout=15)
 assert polled.returncode==0,(polled.stdout,polled.stderr)
 status=invoke('list','--all-roots','--registry-dir',str(registry),'--json')
 assert len(status['roots'])==2 and all(r['paused'] for r in status['roots'])
 assert len(list((a/'firing').glob('*.json')))==1 and not list((a/'submitted').glob('*.json'))
 caller='00000000-0000-7000-8000-000000000011';grants=base/'grants.json'
 actions=['list','cancel','pause','pause-status','interrupt','resume']
 grants.write_text(json.dumps(dict(version=1,callers={caller:dict(roots=[str(a),str(b)],actions=actions)})))
 calls=[]
 async def qualify():
  params=StdioServerParameters(command=mcp,args=['--wake-root',str(a),'--wake-control-config',str(grants),'--wake-registry',str(registry)],env=env)
  async with stdio_client(params) as streams:
   async with ClientSession(*streams) as session:
    await session.initialize();catalog=await session.list_tools();assert len(catalog.tools)==25
    for name in ['wake_list','wake_pause','wake_pause_status','wake_interrupt','wake_cancel','wake_resume']:
     args=dict(caller_thread_id=caller,all_roots=True)
     if name=='wake_cancel':args['all']=True
     reply=await session.call_tool(name,args);value=json.loads(reply.content[0].text)
     assert not reply.is_error,(name,value)
     assert len(value['roots'])==2
     calls.append(name)
    grants.write_text(json.dumps(dict(version=1,callers={caller:dict(roots=[str(a)],actions=actions)})))
    denied=await session.call_tool('wake_pause',dict(caller_thread_id=caller,all_roots=True))
    assert denied.is_error
    assert json.loads(denied.content[0].text)['error']['code']=='policy_denied'
  return dict(tools=25,calls=calls,ungranted_root_denied=True)
 mcp_result=asyncio.run(qualify())
 assert len(list((a/'cancelled').glob('*.json')))==1
 assert len(list((b/'cancelled').glob('*.json')))==1
 assert not invoke('pause-status','--json')['roots'][0]['paused']
 report=dict(version=__version__,source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip(),python_files_matched=len(matched),cli_pause_blocks_actual_daemon=True,
   cross_root_cancellation=True,explicit_resume=True,mcp=mcp_result,native_model_turns=0,operator_wakes_changed=0,service_restarts=0,temporary_roots_removed='context-managed')
args.output.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
