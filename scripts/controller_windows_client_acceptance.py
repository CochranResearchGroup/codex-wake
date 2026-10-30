#!/usr/bin/env python3
"""Actual Windows published-client and token DACL acceptance; no native owner."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();assert os.name=='nt','Windows acceptance requires native Windows Python'
    from codex_wake.controller_client import ClientError,private_token
    executable=Path(sys.executable).parent/'codex-wake.exe';assert executable.is_file()
    args.root.mkdir(parents=True,exist_ok=True)
    token=args.root/'client-acl.token';token.touch()
    powershell=Path(os.environ['SystemRoot'])/'System32/WindowsPowerShell/v1.0/powershell.exe'
    sid=subprocess.check_output([str(powershell),'-NoProfile','-NonInteractive','-Command','[System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value'],text=True,timeout=10).strip()
    assert sid.startswith('S-1-')
    icacls=Path(os.environ['SystemRoot'])/'System32/icacls.exe'
    subprocess.run([str(icacls),str(token),'/inheritance:r','/grant:r','*'+sid+':(F)','*S-1-5-18:(F)','*S-1-5-32-544:(F)'],text=True,capture_output=True,check=True,timeout=10)
    token.write_text('synthetic-controller405-token',encoding='utf-8')
    calls=[]
    envelope=dict(schema_version=1,operation='inventory.list',status='completed',result={'resources':[]})
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_POST(self):
            body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            assert self.headers['Authorization']=='Bearer synthetic-controller405-token'
            calls.append((self.path,body))
            result=envelope if self.path=='/operations' else dict(jsonrpc='2.0',id=1,result={'structuredContent':envelope})
            data=json.dumps(result).encode();self.send_response(200);self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        assert private_token(token)=='synthetic-controller405-token'
        for transport in ('api','mcp'):
            process=subprocess.run([str(executable),'controller','remote','--endpoint','http://127.0.0.1:'+str(server.server_port),
                '--token-file',str(token),'--transport',transport,'inventory.list'],text=True,capture_output=True,timeout=20)
            assert process.returncode==0,(process.returncode,process.stdout,process.stderr)
            assert json.loads(process.stdout)==envelope
        icacls=Path(os.environ['SystemRoot'])/'System32/icacls.exe'
        modified=False
        try:
            process=subprocess.run([str(icacls),str(token),'/grant','*S-1-1-0:(R)'],text=True,capture_output=True,check=True,timeout=10);modified=True
            try:private_token(token)
            except ClientError as error:assert error.code=='token_file_not_private'
            else:raise AssertionError('Everyone read grant admitted')
        finally:
            if modified:subprocess.run([str(icacls),str(token),'/remove:g','*S-1-1-0'],text=True,capture_output=True,check=True,timeout=10)
        assert private_token(token)=='synthetic-controller405-token'
        unsupported=subprocess.run([str(executable),'controller','serve'],text=True,capture_output=True,timeout=10)
        assert unsupported.returncode==2 and json.loads(unsupported.stdout)['error']['code']=='unsupported_native_windows_owner'
        assert [row[0] for row in calls]==['/operations','/mcp']
        import codex_wake
        result=dict(status='passed',platform=sys.platform,python=sys.version,package=codex_wake.__file__,
            published_cli=str(executable),api_and_oauth_mcp=True,current_owner_private_dacl_accepted=True,everyone_read_refused=True,
            native_windows_owner='unsupported_explicit',provider_calls=0)
        args.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
    finally:server.shutdown();server.server_close();thread.join(timeout=2);token.unlink(missing_ok=True)


if __name__=='__main__':main()
