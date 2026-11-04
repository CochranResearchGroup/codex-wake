"""Private same-user WSL controller transport; external OAuth ingress is separate."""
import argparse
import hmac
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
import os
from pathlib import Path
import secrets
import re
from urllib.parse import urlsplit
import signal
import subprocess
import sys
import time
from urllib.request import Request,build_opener,ProxyHandler

from .local_control_service import LocalOperations
from .managed_inventory import InventoryError
from .process import process_identity
from .shortcut_store import private_directory,read,write,locked


def connection_info(root):
    value=read(Path(root)/'local-controller'/'connection.json')
    if value.get('version')!=1 or value.get('uid')!=os.getuid() or process_identity(value['pid'])!=value['process']:
        raise InventoryError('controller_unavailable','local controller identity is stale; start it again')
    url=urlsplit(value.get('url',''))
    if url.scheme!='http' or url.hostname not in ('127.0.0.1','localhost','::1') or url.username or url.password or url.query or url.fragment or url.path:
        raise ValueError('local controller connection must use a loopback endpoint')
    if not isinstance(value.get('token'),str) or not re.fullmatch('[A-Za-z0-9_-]{32,128}',value['token']):
        raise ValueError('local connection credential is malformed; restart the controller')
    return value


class LocalControllerServer(ThreadingHTTPServer):
    daemon_threads=True
    def __init__(self,root,*,port=0,native_endpoint='unix://'):
        self.root=Path(root).absolute();self.directory=private_directory(self.root/'local-controller')
        self.owner=LocalOperations(self.root,native_endpoint=native_endpoint)
        self.token=secrets.token_urlsafe(32)
        super().__init__(('127.0.0.1',port),LocalHandler)
        write(self.directory/'connection.json',dict(version=1,url='http://127.0.0.1:'+str(self.server_port),token=self.token,uid=os.getuid(),pid=os.getpid(),process=process_identity(os.getpid())))


class LocalHandler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def setup(self):
        super().setup();self.connection.settimeout(10)
    def authorized(self):
        value=self.headers.get('Authorization','')
        if not value.startswith('Bearer ') or not hmac.compare_digest(value[7:],self.server.token):
            self.reply(401,dict(status='failed',error=dict(code='invalid_token')));return False
        if self.headers.get('Origin'):
            self.reply(403,dict(status='failed',error=dict(code='invalid_origin')));return False
        return True
    def reply(self,status,value):
        data=json.dumps(value).encode();self.send_response(status)
        self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(data)
    def do_GET(self):
        if not self.authorized():return
        if self.path!='/status':return self.reply(404,{'status':'not_found'})
        self.reply(200,dict(status='ready',pid=os.getpid(),uid=os.getuid()))
    def stream(self,frames):
        self.send_response(200);self.send_header('Content-Type','application/x-ndjson; charset=utf-8');self.send_header('Cache-Control','no-store');self.end_headers()
        for frame in frames:self.wfile.write((json.dumps(frame)+'\n').encode());self.wfile.flush()
    def do_POST(self):
        if not self.authorized():return
        try:
            length=int(self.headers.get('Content-Length','0'))
            if not 0<length<=1048576 or self.headers.get('Content-Type','').split(';')[0]!='application/json':raise ValueError('bounded JSON body required')
            body=json.loads(self.rfile.read(length))
            if not isinstance(body,dict):raise ValueError('object request required')
            if self.path=='/operations':
                if set(body)!={'operation','arguments'}:raise ValueError('operation and arguments required')
                if 'application/x-ndjson' in self.headers.get('Accept',''):
                    from .local_control_client import operation_frames
                    return self.stream(operation_frames(self.server.owner,body['operation'],body['arguments']))
                return self.reply(200,self.server.owner.execute(body['operation'],body['arguments']))
            if self.path=='/mcp':
                identifier=body.get('id');method=body.get('method')
                if method=='initialize':result=dict(protocolVersion=body.get('params',{}).get('protocolVersion','2025-06-18'),capabilities={'tools':{}},serverInfo={'name':'codex-wake-local','version':'1'})
                elif method=='notifications/initialized':return self.reply(202,{})
                elif method=='tools/list':result=dict(tools=self.server.owner.tools())
                elif method=='tools/call':
                    params=body.get('params',{})
                    if not isinstance(params,dict):raise ValueError('MCP params must be an object')
                    try:
                        value=self.server.owner.call_tool(params.get('name'),params.get('arguments',{}))
                    except (ValueError,OSError,TypeError,KeyError) as error:
                        value=dict(status='failed',error=dict(code=getattr(error,'code','invalid_argument'),message=str(error)))
                    result=dict(content=[dict(type='text',text=json.dumps(value))],structuredContent=value,isError=value.get('status')=='failed')
                else:raise InventoryError('unsupported_operation','unsupported MCP method')
                return self.reply(200,dict(jsonrpc='2.0',id=identifier,result=result))
            if self.path=='/cli':
                from .local_control_client import cli_frames
                if set(body)!={'arguments'} or not isinstance(body['arguments'],list) or len(body['arguments'])>128 or any(not isinstance(x,str) or len(x)>65536 for x in body['arguments']):raise ValueError('bounded CLI argument array required')
                return self.stream(cli_frames(self.server.owner,body['arguments']))
            self.reply(404,{'status':'not_found'})
        except (BrokenPipeError,ConnectionResetError,TimeoutError):pass # Caller disconnect never cancels native work.
        except (ValueError,OSError,TypeError,KeyError) as error:
            self.reply(400,dict(status='failed',error=dict(code=getattr(error,'code','invalid_argument'),message=str(error))))


def start(root,*,port=0,native_endpoint='unix://'):
    directory=private_directory(Path(root)/'local-controller')
    with locked(directory):
        try:
            info=connection_info(root)
            opener=build_opener(ProxyHandler({}))
            with opener.open(Request(info['url']+'/status',headers={'Authorization':'Bearer '+info['token']}),timeout=2) as response:
                if json.loads(response.read())['pid']==info['pid']:return {k:v for k,v in info.items() if k!='token'}
        except (ValueError,OSError,KeyError):pass
        log=(directory/'server.log').open('ab')
        env=dict(os.environ,PYTHONPATH=os.pathsep.join(str(Path(p).absolute()) for p in sys.path if p))
        process=subprocess.Popen([sys.executable,'-m','codex_wake.local_control_server','--root',str(Path(root).absolute()),'--port',str(port),'--native-endpoint',native_endpoint],stdin=subprocess.DEVNULL,stdout=log,stderr=log,env=env,cwd=directory,start_new_session=True)
        log.close();deadline=time.monotonic()+10
        while time.monotonic()<deadline:
            try:
                info=connection_info(root)
                if info['pid']==process.pid:return {k:v for k,v in info.items() if k!='token'}
            except (ValueError,OSError,KeyError):pass
            if process.poll() is not None:break
            time.sleep(.05)
        raise InventoryError('controller_start_unverified','local server did not publish readiness; inspect its private server.log')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True);parser.add_argument('--port',type=int,default=0);parser.add_argument('--native-endpoint',default='unix://');args=parser.parse_args()
    with LocalControllerServer(args.root,port=args.port,native_endpoint=args.native_endpoint) as server:server.serve_forever()


if __name__=='__main__':main()
