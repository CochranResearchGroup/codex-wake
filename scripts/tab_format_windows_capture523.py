"""Capture one owned native psmux console window, then reap its exact client.

Stdlib only. No desktop-wide screenshots or discovery of other windows. The
wrapper opens CONIN$/CONOUT$ explicitly because inherited WSL pipe handles make
psmux's documented non-TTY guard print its version and exit without rendering.
"""
import argparse
import ctypes
from ctypes import wintypes as W
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time


class COORD(ctypes.Structure):
    _fields_=[('X',ctypes.c_short),('Y',ctypes.c_short)]


class RECT(ctypes.Structure):
    _fields_=[('Left',ctypes.c_short),('Top',ctypes.c_short),('Right',ctypes.c_short),('Bottom',ctypes.c_short)]


class SCREEN_INFO(ctypes.Structure):
    _fields_=[('size',COORD),('cursor',COORD),('attributes',W.WORD),('window',RECT),('maximum',COORD)]


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--namespace',required=True);parser.add_argument('--session',required=True);parser.add_argument('--matrix',type=Path,required=True);args=parser.parse_args()
    if not args.namespace.startswith('wake523-'):raise RuntimeError('Explicit owned test namespace required.')
    directory=Path(__file__).resolve().parent
    spec=importlib.util.spec_from_file_location('owned_bridge',directory/'bridge.py');bridge=importlib.util.module_from_spec(spec);spec.loader.exec_module(bridge)
    binary=str(Path(os.environ['LOCALAPPDATA'])/'Microsoft/WinGet/Links/psmux.exe')
    wrapper=directory/'console_wrapper.py';metadata=directory/'client.json'
    wrapper.write_text('''import ctypes,json,subprocess,sys
from pathlib import Path
ctypes.windll.kernel32.SetConsoleTitleW(sys.argv[2])
with open('CONIN$','r') as cin,open('CONOUT$','w',encoding='utf-8') as cout:
 process=subprocess.Popen([sys.argv[1],'-L',sys.argv[2],'attach-session','-t',sys.argv[3]],stdin=cin,stdout=cout,stderr=cout)
 Path(sys.argv[4]).write_text(json.dumps(dict(pid=process.pid)))
 process.wait()
''')
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.CreateFileW.argtypes=[W.LPCWSTR,W.DWORD,W.DWORD,ctypes.c_void_p,W.DWORD,W.DWORD,W.HANDLE];kernel.CreateFileW.restype=W.HANDLE
    kernel.AttachConsole.argtypes=[W.DWORD];kernel.AttachConsole.restype=W.BOOL
    kernel.GetConsoleScreenBufferInfo.argtypes=[W.HANDLE,ctypes.POINTER(SCREEN_INFO)]
    kernel.ReadConsoleOutputCharacterW.argtypes=[W.HANDLE,W.LPWSTR,W.DWORD,COORD,ctypes.POINTER(W.DWORD)]
    kernel.ReadConsoleOutputAttribute.argtypes=[W.HANDLE,ctypes.POINTER(W.WORD),W.DWORD,COORD,ctypes.POINTER(W.DWORD)]
    kernel.OpenProcess.argtypes=[W.DWORD,W.BOOL,W.DWORD];kernel.OpenProcess.restype=W.HANDLE
    kernel.TerminateProcess.argtypes=[W.HANDLE,W.UINT];kernel.WaitForSingleObject.argtypes=[W.HANDLE,W.DWORD]
    kernel.CloseHandle.argtypes=[W.HANDLE]
    process=subprocess.Popen([sys.executable,str(wrapper),binary,args.namespace,args.session,str(metadata)],creationflags=subprocess.CREATE_NEW_CONSOLE)
    child=None;birth=None;console=None;report=None
    try:
        until=time.monotonic()+5
        while not metadata.exists():
            if process.poll() is not None or time.monotonic()>=until:raise RuntimeError('Owned console client did not start.')
            time.sleep(.02)
        child=json.loads(metadata.read_text())['pid'];birth=bridge.process_birth(child)
        kernel.FreeConsole()
        if not kernel.AttachConsole(process.pid):raise ctypes.WinError(ctypes.get_last_error())
        console=kernel.CreateFileW('CONOUT$',0x80000000,3,None,3,0,None)
        if console==ctypes.c_void_p(-1).value:raise ctypes.WinError(ctypes.get_last_error())
        def screen():
            info=SCREEN_INFO()
            if not kernel.GetConsoleScreenBufferInfo(console,ctypes.byref(info)):raise ctypes.WinError(ctypes.get_last_error())
            width=info.size.X;height=info.window.Bottom-info.window.Top+1
            count=min(width*height,32768);buffer=ctypes.create_unicode_buffer(count);read=W.DWORD()
            origin=COORD(0,info.window.Top)
            if not kernel.ReadConsoleOutputCharacterW(console,buffer,count,origin,ctypes.byref(read)):raise ctypes.WinError(ctypes.get_last_error())
            attributes=(W.WORD*width)();seen=W.DWORD()
            kernel.ReadConsoleOutputAttribute(console,attributes,width,COORD(0,info.window.Bottom),ctypes.byref(seen))
            return dict(width=width,height=height,text=buffer[:read.value],status_attributes=list(attributes)[:seen.value])
        matrix=json.loads(args.matrix.read_text())
        host=bridge.PsmuxHost(namespace=args.namespace,session=args.session,
            server_pid=matrix['identity']['pid'],server_birth=matrix['identity']['creation_filetime'])
        cases={}
        for case in matrix['cases']:
            host.execute(dict(action='formatting_batch',arguments=dict(requests=case['requests'])))
            subprocess.run([binary,'-L',args.namespace,'select-window','-t',args.session+':0'],text=True,encoding='utf-8',capture_output=True,check=True,timeout=5)
            subprocess.run([binary,'-L',args.namespace,'refresh-client','-S'],text=True,encoding='utf-8',capture_output=True,check=True,timeout=5)
            until=time.monotonic()+4
            while True:
                initial=screen()
                if 'CX+' in initial['text'] and 'GK' in initial['text'] and '[0' in initial['text']:break
                if time.monotonic()>=until:raise RuntimeError('Native console did not display selected Wake status labels: '+repr(initial['text'][-500:]))
                time.sleep(.03)
            subprocess.run([binary,'-L',args.namespace,'select-window','-t',args.session+':1'],text=True,encoding='utf-8',capture_output=True,check=True,timeout=5)
            subprocess.run([binary,'-L',args.namespace,'refresh-client','-S'],text=True,encoding='utf-8',capture_output=True,check=True,timeout=5)
            until=time.monotonic()+3
            while True:
                changed=screen()
                if '[1' in changed['text']:break
                if time.monotonic()>=until:raise RuntimeError('Native selected-tab update not observed.')
                time.sleep(.03)
            cases[case['mode']]=dict(initial=initial,changed=changed)
        report=dict(status='passed',client_pid=child,client_birth=birth,wrapper_pid=process.pid,
                    modes=cases,native_console=True)
    finally:
        if console is not None and console!=ctypes.c_void_p(-1).value:kernel.CloseHandle(console)
        kernel.FreeConsole()
        if child is not None:
            if bridge.process_birth(child)!=birth:raise RuntimeError('Owned client identity changed before cleanup.')
            handle=kernel.OpenProcess(0x100000|0x1000|1,False,child)
            if not handle:raise ctypes.WinError(ctypes.get_last_error())
            try:
                if not kernel.TerminateProcess(handle,0):raise ctypes.WinError(ctypes.get_last_error())
                if kernel.WaitForSingleObject(handle,5000)!=0:raise RuntimeError('Owned client did not stop.')
            finally:kernel.CloseHandle(handle)
        try:process.wait(timeout=5)
        except subprocess.TimeoutExpired:process.terminate();process.wait(timeout=5)
    report['client_terminated_and_reaped']=True
    print(json.dumps(report))


if __name__=='__main__':main()
