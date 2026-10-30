#!/usr/bin/env python3
"""Provider-free native Grok ACP metadata proof; never creates a session/turn."""
import argparse,hashlib,json,os,signal,socket,subprocess,time
from pathlib import Path
from urllib.parse import quote


def main():
    from websockets.sync.client import connect
    parser=argparse.ArgumentParser(__doc__);parser.add_argument('--binary',type=Path,required=True);parser.add_argument('--artifacts',type=Path,required=True);parser.add_argument('--leader-mode',action='store_true');args=parser.parse_args()
    root=args.artifacts.resolve();root.mkdir(mode=0o700,parents=True,exist_ok=False)
    home=root/'home';home.mkdir();work=root/'work';work.mkdir();secret='fixture-grok412-native-transport-only'
    key=root/'transport.secret';key.write_text(secret);key.chmod(0o600)
    sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1];sock.close()
    env={k:os.environ[k] for k in ('PATH','LANG') if k in os.environ}
    env.update(HOME=str(home),GROK_HOME=str(home/'.grok'),XDG_CONFIG_HOME=str(root/'config'),XDG_STATE_HOME=str(root/'state'),XDG_CACHE_HOME=str(root/'cache'),HTTP_PROXY='http://127.0.0.1:9',HTTPS_PROXY='http://127.0.0.1:9',ALL_PROXY='http://127.0.0.1:9',NO_PROXY='',GROK_AGENT_SECRET=secret,GROK_SUBAGENTS='0')
    binary=args.binary.resolve();log=(root/'native.log').open('wb')
    leader=None
    if args.leader_mode:
        leader_command=['grok','agent','--grok-ws-url','ws://127.0.0.1:9','--grok-ws-origin','http://127.0.0.1:9','--xai-api-base-url','http://127.0.0.1:9','--cli-chat-proxy-base-url','http://127.0.0.1:9','leader','--relay-on-demand','--no-auto-update','--leader-socket',str(root/'leader.sock')]
        leader=subprocess.Popen(leader_command,executable=str(binary),env=env,cwd=work,stdin=subprocess.PIPE,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        until=time.monotonic()+10
        while not (root/'leader.sock').exists() and leader.poll() is None and time.monotonic()<until:time.sleep(.1)
    command=['grok','agent','--leader' if args.leader_mode else '--no-leader','--xai-api-base-url','http://127.0.0.1:9','--cli-chat-proxy-base-url','http://127.0.0.1:9','serve','--bind','127.0.0.1:'+str(port),'--leader-socket',str(root/'leader.sock')]
    process=subprocess.Popen(command,executable=str(binary),env=env,cwd=work,stdin=subprocess.PIPE,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    receipt=dict(binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),no_session=True,no_prompt=True,private_home=True,provider_endpoints_loopback_only=True)
    try:
        deadline=time.monotonic()+30
        while True:
            try:
                with connect(f'ws://127.0.0.1:{port}/ws?server-key='+quote(secret),open_timeout=1,close_timeout=1,proxy=None) as ws:
                    frame=dict(jsonrpc='2.0',id=1,method='initialize',params=dict(protocolVersion=1,clientCapabilities={},clientInfo=dict(name='wake-provider-free',version='0.22.0.dev2')))
                    ws.send(json.dumps(frame));response=json.loads(ws.recv(timeout=5));assert response['id']==1
                    (root/'initialize.json').write_text(json.dumps(response,indent=2)+'\n')
                    value=response['result'];meta=value['_meta']
                    receipt.update(protocol_version=value['protocolVersion'],agent_version=meta['agentVersion'],agent_id=meta['agentId'],agent_instance_id=meta['agentInstanceId'],cwd_matches=meta['currentWorkingDirectory']==str(work),agent_capabilities=value['agentCapabilities'],transport='native WebSocket /ws with fixed host transport secret')
                    break
            except OSError:
                assert process.poll() is None and time.monotonic()<deadline,'native metadata readiness unavailable';time.sleep(.1)
        try:
            with connect(f'ws://127.0.0.1:{port}/ws',open_timeout=1,close_timeout=1,proxy=None):pass
        except Exception:receipt['anonymous_denied']=True
    finally:
        for owned in (process,leader):
            if owned is None:continue
            try:os.killpg(owned.pid,signal.SIGTERM)
            except ProcessLookupError:pass
            try:owned.wait(timeout=3)
            except subprocess.TimeoutExpired:os.killpg(owned.pid,signal.SIGKILL);owned.wait(timeout=3)
        log.close();receipt['owned_exit_code']=process.returncode
        (root/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt,sort_keys=True))


if __name__=='__main__':main()
