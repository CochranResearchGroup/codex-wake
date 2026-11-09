import json,subprocess
from pathlib import Path
base=Path('docs/dev/evidence/plan0211/review-r3');v=json.loads((base/'cleanup-firstfailure.json').read_text())
code=r'''import ctypes,json,subprocess,sys,re,time,hashlib
from ctypes import wintypes as w
v=json.loads(sys.stdin.read());raw=subprocess.check_output(['powershell.exe','-NoProfile','-NonInteractive','-Command','Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId,Name,CommandLine | ConvertTo-Json -Compress'],text=True);rows=json.loads(raw)
roots=[p for p in rows if p['Name'].lower()=='psmux.exe' and any(re.search(r'(?:^| )-L '+re.escape(n)+r'(?: |$)',p.get('CommandLine') or '') for n in v['namespaces'])]
owned=list(roots);ids={p['ProcessId'] for p in owned}
while True:
 extra=[p for p in rows if p['ParentProcessId'] in ids and p['ProcessId'] not in ids]
 if not extra:break
 owned+=extra;ids.update(p['ProcessId'] for p in extra)
k=ctypes.WinDLL('kernel32',use_last_error=True)
k.OpenProcess.argtypes=[w.DWORD,w.BOOL,w.DWORD];k.OpenProcess.restype=w.HANDLE
k.GetExitCodeProcess.argtypes=[w.HANDLE,ctypes.POINTER(w.DWORD)];k.CloseHandle.argtypes=[w.HANDLE];k.TerminateProcess.argtypes=[w.HANDLE,w.UINT]
k.GetProcessTimes.argtypes=[w.HANDLE,*([ctypes.POINTER(w.FILETIME)]*4)]
k.QueryFullProcessImageNameW.argtypes=[w.HANDLE,w.DWORD,w.LPWSTR,ctypes.POINTER(w.DWORD)]
handles=[];result=[]
try:
 for p in owned:
  h=k.OpenProcess(0x1001,False,p['ProcessId'])
  if not h:continue
  t=[w.FILETIME() for _ in range(4)];assert k.GetProcessTimes(h,*[ctypes.byref(x) for x in t]);birth=(t[0].dwHighDateTime<<32)|t[0].dwLowDateTime
  if p in roots:
   buf=ctypes.create_unicode_buffer(32768);length=w.DWORD(len(buf));assert k.QueryFullProcessImageNameW(h,0,buf,ctypes.byref(length));assert hashlib.sha256(open(buf.value,'rb').read()).hexdigest()=='bbe825a30f7cddc91b043084049143a381aba5f7e9e36e4d0bb587e296d262ca'
  handles.append((p,h,birth))
 for p,h,birth in reversed(handles):
  out=w.DWORD();assert k.GetExitCodeProcess(h,ctypes.byref(out));before=out.value
  if before==259:assert k.TerminateProcess(h,0)
  until=time.monotonic()+5
  while True:
   assert k.GetExitCodeProcess(h,ctypes.byref(out))
   if out.value!=259 or time.monotonic()>until:break
   time.sleep(.05)
  result.append(dict(pid=p['ProcessId'],parent=p['ParentProcessId'],name=p['Name'],birth=birth,before_exit_code=before,after_exit_code=out.value))
 assert all(p['after_exit_code']!=259 for p in result)
 print(json.dumps(dict(namespaces=v['namespaces'],terminated_owned_processes=result)))
finally:
 for _,h,_ in handles:k.CloseHandle(h)
'''
py='/mnt/c/Users/ecoch/AppData/Local/codex-wake-test/controller405-20261030/venv/Scripts/python.exe'
r=subprocess.run([py,'-c',code],input=json.dumps(v),text=True,capture_output=True,check=True,timeout=45)
(base/'cleanup-termination.json').write_text(r.stdout);print('Terminated exact owned processes:',len(json.loads(r.stdout)['terminated_owned_processes']))
