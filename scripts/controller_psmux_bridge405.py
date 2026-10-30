#!/usr/bin/env python3
"""Finite actual Windows psmux test bridge; fixed namespace and birth-pinned server."""
import argparse
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys


def birth(pid):
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];kernel.OpenProcess.restype=wintypes.HANDLE
    kernel.GetProcessTimes.argtypes=[wintypes.HANDLE,*([ctypes.POINTER(wintypes.FILETIME)]*4)];kernel.GetProcessTimes.restype=wintypes.BOOL
    kernel.CloseHandle.argtypes=[wintypes.HANDLE]
    handle=kernel.OpenProcess(0x1000,False,pid)
    if not handle:raise OSError('server process unavailable')
    try:
        values=[wintypes.FILETIME() for _ in range(4)]
        if not kernel.GetProcessTimes(handle,*[ctypes.byref(value) for value in values]):raise OSError('server birth unavailable')
        return (values[0].dwHighDateTime<<32)|values[0].dwLowDateTime
    finally:kernel.CloseHandle(handle)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--namespace',required=True);parser.add_argument('--session',required=True)
    parser.add_argument('--server-pid',type=int);parser.add_argument('--server-birth',type=int);parser.add_argument('--describe',action='store_true')
    args=parser.parse_args();assert os.name=='nt' and re.fullmatch(r'controller405-[A-Za-z0-9-]+',args.namespace)
    binary=Path(os.environ['LOCALAPPDATA'])/'Microsoft/WinGet/Links/psmux.exe'
    def command(*argv):
        answer=subprocess.run([str(binary),'-L',args.namespace,*argv],text=True,capture_output=True,timeout=4,check=True)
        if len(answer.stdout)>1048576:raise ValueError('bounded presentation required')
        return answer.stdout
    pid=int(command('display-message','-p','#{pid}').strip());created=birth(pid)
    if args.server_pid is not None:assert pid==args.server_pid and created==args.server_birth,'psmux server generation changed'
    identity=dict(platform='windows',namespace=args.namespace,pid=pid,creation_filetime=created,executable_sha256=hashlib.sha256(binary.read_bytes()).hexdigest())
    generation=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()
    if args.describe:print(json.dumps(dict(generation=generation,identity=identity)));return
    request=json.loads(sys.stdin.buffer.read(65537));action=request['action'];arguments=request['arguments']
    fields=('session_id','window_id','window_index','window_name','window_active','pane_id','pane_pid','pane_current_path')
    rows=[dict(zip(fields,line.split('|'))) for line in command('list-panes','-a','-F','|'.join('#{'+field+'}' for field in fields)).splitlines()]
    assert rows and all(len(row)==len(fields) for row in rows)
    sessions={row['session_id'] for row in rows};assert len(sessions)==1,'dedicated namespace must contain one test session'
    windows={}
    for row in rows:
        assert re.fullmatch(r'@[0-9]+',row['window_id']) and re.fullmatch(r'%[0-9]+',row['pane_id'])
        window=windows.setdefault(row['window_id'],dict(window_id=row['window_id'],index=int(row['window_index']),name=row['window_name'],focused=row['window_active']=='1',linked=False,panes=[]))
        window['panes'].append(dict(pane_id=row['pane_id'],pid=int(row['pane_pid']),windows_creation_filetime=birth(int(row['pane_pid']))))
    if action=='snapshot':
        assert not arguments
        result=dict(server=str(pid),session_id=next(iter(sessions)),socket_identity=[pid,created],windows=sorted(windows.values(),key=lambda row:row['index']),windows_server=identity)
    elif action=='capture':
        assert set(arguments)=={'pane','lines'} and arguments['pane'] in {row['pane_id'] for row in rows} and type(arguments['lines']) is int and 1<=arguments['lines']<=2000
        result=command('capture-pane','-p','-t',arguments['pane'],'-S','-'+str(arguments['lines']))
    elif action=='swap':
        assert set(arguments)=={'first','second'} and arguments['first'] in windows and arguments['second'] in windows
        focused=next(row['window_id'] for row in windows.values() if row['focused'])
        command('swap-window','-d','-s',arguments['first'],'-t',arguments['second']);command('select-window','-t',focused);result={}
    else:raise ValueError('unsupported finite bridge action')
    assert birth(pid)==created,'psmux server generation changed during operation'
    print(json.dumps(dict(generation=generation,result=result)))


if __name__=='__main__':main()
