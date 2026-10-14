"""Owned Plan0162 startup proof; zero model turns, no production peer effects."""
import asyncio
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import signal
import subprocess
import time
from mcp import Client,StdioServerParameters

root=Path('/tmp/codex-wake-p162-live-04');root.mkdir(mode=0o700,exist_ok=False)
workspace=root/'workspace';workspace.mkdir()
home=root/'codex-home';home.mkdir(mode=0o700)
(home/'config.toml').write_text('approval_policy="never"\nsandbox_mode="workspace-write"\n'+
    '[projects.'+json.dumps(str(workspace))+']\ntrust_level="trusted"\n')
(home/'auth.json').symlink_to(Path.home()/'.codex/auth.json')
prefix=Path('/tmp/codex-wake-p162-install')
codex=Path(subprocess.check_output(['which','codex'],text=True).strip()).resolve()
env=dict(os.environ,CODEX_HOME=str(home))
for key in ('PYTHONPATH','CODEX_THREAD_ID','TMUX','TMUX_PANE','CODEX_WAKE_A2A_CAPABILITY',
            'CODEX_WAKE_A2A_BUS_ROOT','CODEX_WAKE_SENDER_RECEIPT_AUTHORITY'):env.pop(key,None)
socket=root/'tmux.sock';endpoint=root/'native.sock';session='p162-owned'
caller='00000000-0000-7000-8000-000000000162'
receipt=dict(state='preparing',root=str(root),prefix=str(prefix),model_turns=0,
             scope='operator issue262 implementation; owned startup only')
server=None

def write():
    (root/'receipt.json').write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')

def tmux(*args):
    return subprocess.check_output(['tmux','-S',str(socket),*args],text=True,env=env,timeout=10).strip()

async def exercise():
    from codex_wake.native_clock import snapshot
    bounds=snapshot().get('utc')
    if not bounds:raise RuntimeError('trusted time unavailable')
    expiry=datetime.fromtimestamp(bounds['upper']+180,timezone.utc).isoformat()
    profiles=root/'profiles.json'
    profiles.write_text(json.dumps(dict(version=1,callers={caller:['worker']},profiles={'worker':dict(
        cwd=str(workspace),codex_home=str(home),codex_path=str(codex),app_server='unix://'+str(endpoint),
        tmux_session=session,tmux_socket=str(socket),timeout=5)})))
    params=StdioServerParameters(command=str(prefix/'bin/codex-wake-mcp'),args=[
        '--wake-root',str(root/'wake'),'--lifecycle-profiles',str(profiles),
        '--app-server','unix://'+str(endpoint),'--tmux-socket',str(socket),'--tmux-session',session],env=env)
    async with Client(params,mode='legacy') as client:
        tools={t.name for t in (await client.list_tools()).tools}
        receipt['tool_discovered']='wake_sessions_target' in tools
        async def call(selector,**options):
            result=await client.call_tool('wake_sessions_target',dict(selector=selector,caller_thread_id=caller,**options))
            return json.loads(result.content[0].text)
        receipt['before']=await call('tab 18')
        receipt['tab_only']=await call('new-shell',on_missing='tab_only',profile='worker',intent='shell',expires_at=expiry)
        write()
        for n in range(20):
            result=await call('poicys',on_inactive='fresh',profile='worker',intent='fresh',expires_at=expiry)
            receipt['fresh']=result;receipt['fresh_observations']=n+1;write()
            if result['status']!='starting':break
            await asyncio.sleep(.5)
        if result['status']!='resolved':
            raise RuntimeError('fresh target not ready: '+result['status'])
        thread=result['thread_id'];pane=result['session']['selected_attachment']['pane_id']
        tmux('kill-pane','-t',pane)
        for n in range(20):
            result=await call('tab 18',on_inactive='resume',profile='worker',intent='resume',expires_at=expiry,
                              resume_thread_id=thread)
            receipt['resume']=result;receipt['resume_observations']=n+1;write()
            if result['status']!='starting':break
            await asyncio.sleep(.5)
        receipt['state']='passed' if result['status']=='resolved' and result['thread_id']==thread else 'partial'
        write()

log=(root/'server.log').open('w')
try:
    server=subprocess.Popen([str(codex),'app-server','--listen','unix://'+str(endpoint)],env=env,
        stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    receipt['server_pid']=server.pid
    end=time.monotonic()+15
    while not endpoint.exists() and server.poll() is None and time.monotonic()<end:time.sleep(.1)
    if not endpoint.exists():raise RuntimeError('owned server unavailable')
    endpoint=endpoint.resolve()
    tmux('new-session','-d','-s',session,'-n','controller','-c',str(workspace))
    tmux('new-window','-d','-t',session+':18','-n','policies','-c',str(workspace))
    asyncio.run(exercise())
except Exception as exc:
    receipt.update(state='failed',reason=str(exc));write()
finally:
    try:tmux('kill-server')
    except Exception:pass
    if server and server.poll() is None:
        os.killpg(server.pid,signal.SIGTERM)
        try:server.wait(timeout=5)
        except subprocess.TimeoutExpired:os.killpg(server.pid,signal.SIGKILL);server.wait(timeout=5)
    log.close()
    time.sleep(.2)
    processes=subprocess.check_output(['ps','-eo','pid,ppid,args'],text=True).splitlines()
    residue=[line for line in processes if str(root) in line and int(line.split()[0])!=os.getpid()]
    receipt['fresh_os_residue']=residue
    receipt['server_returncode']=server.returncode if server else None
    write()
print(json.dumps({k:receipt.get(k) for k in ('state','reason','model_turns','fresh_os_residue')}))
