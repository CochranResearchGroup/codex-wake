"""R3 namespace census/cleanup, with persisted birth/hash pins for owned fixtures."""
import argparse
import json
from pathlib import Path
import subprocess

WINDOWS = r'''
import ctypes,hashlib,json,re,subprocess,sys,time
from ctypes import wintypes as w
v=json.loads(sys.stdin.read());k=ctypes.WinDLL('kernel32',use_last_error=True)
k.OpenProcess.argtypes=[w.DWORD,w.BOOL,w.DWORD];k.OpenProcess.restype=w.HANDLE
k.GetProcessTimes.argtypes=[w.HANDLE,*([ctypes.POINTER(w.FILETIME)]*4)];k.GetProcessTimes.restype=w.BOOL
k.GetExitCodeProcess.argtypes=[w.HANDLE,ctypes.POINTER(w.DWORD)];k.GetExitCodeProcess.restype=w.BOOL
k.QueryFullProcessImageNameW.argtypes=[w.HANDLE,w.DWORD,w.LPWSTR,ctypes.POINTER(w.DWORD)];k.QueryFullProcessImageNameW.restype=w.BOOL
k.TerminateProcess.argtypes=[w.HANDLE,w.UINT];k.TerminateProcess.restype=w.BOOL
k.CloseHandle.argtypes=[w.HANDLE]
expected='bbe825a30f7cddc91b043084049143a381aba5f7e9e36e4d0bb587e296d262ca'
def inspect(h):
 t=[w.FILETIME() for _ in range(4)];out=w.DWORD();buf=ctypes.create_unicode_buffer(32768);length=w.DWORD(len(buf))
 assert k.GetProcessTimes(h,*[ctypes.byref(x) for x in t]) and k.GetExitCodeProcess(h,ctypes.byref(out))
 assert k.QueryFullProcessImageNameW(h,0,buf,ctypes.byref(length))
 return dict(birth=(t[0].dwHighDateTime<<32)|t[0].dwLowDateTime,exit_code=out.value,executable_sha256=hashlib.sha256(open(buf.value,'rb').read()).hexdigest())
if v['action']=='census':
 raw=subprocess.check_output(['powershell.exe','-NoProfile','-NonInteractive','-Command','Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId,Name,CommandLine,@{Name="CreationFiletime";Expression={$_.CreationDate.ToFileTimeUtc()}} | ConvertTo-Json -Compress'],text=True)
 rows=json.loads(raw);roots=[]
 for p in rows:
  if p['Name'].lower()!='psmux.exe':continue
  matches=[n for n in v['namespaces'] if re.search(r'(?:^| )-L '+re.escape(n)+r'(?: |$)',p.get('CommandLine') or '')]
  if matches:p=dict(p,namespace=matches[0]);roots.append(p)
 owned=list(roots);ids={p['ProcessId'] for p in roots};root_ids=set(ids)
 while True:
  extra=[p for p in rows if p['ParentProcessId'] in ids and p['ProcessId'] not in ids]
  if not extra:break
  owned+=extra;ids.update(p['ProcessId'] for p in extra)
 result=[]
 for p in owned:
  h=k.OpenProcess(0x1000,False,p['ProcessId'])
  if not h:
   result.append(dict(pid=p['ProcessId'],parent=p['ParentProcessId'],name=p['Name'],winerror=ctypes.get_last_error()));continue
  try:
   observed=inspect(h)
   assert abs(observed['birth']-p['CreationFiletime'])<10,('census PID reused',p['ProcessId'])
   if p['ProcessId'] in root_ids:assert observed['executable_sha256']==expected
   result.append(dict(pid=p['ProcessId'],parent=p['ParentProcessId'],name=p['Name'],root=p['ProcessId'] in root_ids,namespace=p.get('namespace'),**observed))
  finally:k.CloseHandle(h)
 pins=[]
 for pin in v.get('pins',[]):
  h=k.OpenProcess(0x1000,False,pin['pid'])
  if not h:
   error=ctypes.get_last_error();assert error==87,('unknown pinned process',pin['pid'],error)
   pins.append(dict(pid=pin['pid'],winerror=error));continue
  try:
   t=[w.FILETIME() for _ in range(4)];out=w.DWORD()
   assert k.GetProcessTimes(h,*[ctypes.byref(x) for x in t]) and k.GetExitCodeProcess(h,ctypes.byref(out))
   birth=(t[0].dwHighDateTime<<32)|t[0].dwLowDateTime
   pins.append(dict(pid=pin['pid'],birth=birth,replaced=birth!=pin['birth'],exit_code=out.value))
  finally:k.CloseHandle(h)
 print(json.dumps(dict(namespaces=v['namespaces'],matching_processes=result,active_count=sum(p.get('exit_code')==259 for p in result),pinned_processes=pins,pinned_active_count=sum(not p.get('replaced') and p.get('exit_code')==259 for p in pins))))
else:
 # Open all known handles before any effect; birth and image must equal the
 # prior namespace-qualified census, preventing PID reuse from gaining custody.
 handles=[];result=[]
 try:
  for p in v['matching_processes']:
   if p.get('exit_code')!=259:continue
   h=k.OpenProcess(0x1001,False,p['pid'])
   if not h:
    error=ctypes.get_last_error();assert error==87,('unknown handle failure',p['pid'],error)
    result.append(dict(pid=p['pid'],already_absent=True));continue
   observed=inspect(h)
   if observed['birth']!=p['birth']:
    k.CloseHandle(h);result.append(dict(pid=p['pid'],replaced=True));continue
   assert observed['executable_sha256']==p['executable_sha256']
   if p.get('root'):assert observed['executable_sha256']==expected
   handles.append((p,h))
  for p,h in reversed(handles):
   observed=inspect(h);assert observed['birth']==p['birth']
   if observed['exit_code']==259:assert k.TerminateProcess(h,0),ctypes.get_last_error()
   until=time.monotonic()+5
   while True:
    out=w.DWORD();assert k.GetExitCodeProcess(h,ctypes.byref(out))
    if out.value!=259 or time.monotonic()>until:break
    time.sleep(.05)
   assert out.value!=259
   result.append(dict(pid=p['pid'],parent=p['parent'],name=p['name'],birth=p['birth'],executable_sha256=p['executable_sha256'],after_exit_code=out.value))
  print(json.dumps(dict(namespaces=v['namespaces'],terminated_owned_processes=result)))
 finally:
  for _,h in handles:k.CloseHandle(h)
'''

if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['census','cleanup']);p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    value=json.loads(a.input.read_text());value['action']=a.action
    python='/mnt/c/Users/ecoch/AppData/Local/codex-wake-test/controller405-20261030/venv/Scripts/python.exe'
    r=subprocess.run([python,'-c',WINDOWS],input=json.dumps(value),text=True,capture_output=True,timeout=60)
    if r.returncode:raise RuntimeError(r.stderr)
    a.output.write_text(json.dumps(json.loads(r.stdout),indent=2)+'\n');print(json.dumps(dict(action=a.action,output=str(a.output),**{k:v for k,v in json.loads(r.stdout).items() if k in ['active_count']})))
