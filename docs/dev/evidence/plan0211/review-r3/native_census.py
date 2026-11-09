import json,subprocess
from pathlib import Path
base=Path('docs/dev/evidence/plan0211/review-r3')
receipts=[json.loads(p.read_text()) for p in base.glob('native*.json')]
names=sorted({r['namespace'] for r in receipts if 'namespace' in r})
parents={i['pid'] for r in receipts for i in r.get('owned_servers',[])}
code='''import json,subprocess,sys
v=json.loads(sys.stdin.read())
s="Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId,Name,CommandLine,CreationDate | ConvertTo-Json -Compress"
r=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',s],capture_output=True,text=True,check=True)
rows=json.loads(r.stdout);owned=[p for p in rows if any(n in (p.get('CommandLine') or '') for n in v['namespaces'])]
root=set(v['server_pids'])|{p['ProcessId'] for p in owned}
while True:
 extra=[p for p in rows if p['ParentProcessId'] in root and p['ProcessId'] not in root]
 if not extra:break
 owned+=extra;root.update(p['ProcessId'] for p in extra)
import ctypes
from ctypes import wintypes as w
k=ctypes.WinDLL('kernel32',use_last_error=True)
k.OpenProcess.argtypes=[w.DWORD,w.BOOL,w.DWORD];k.OpenProcess.restype=w.HANDLE
k.GetExitCodeProcess.argtypes=[w.HANDLE,ctypes.POINTER(w.DWORD)];k.CloseHandle.argtypes=[w.HANDLE]
def observe(p):
 result={k:p[k] for k in ('ProcessId','ParentProcessId','Name','CreationDate')}
 h=k.OpenProcess(0x1000,False,p['ProcessId'])
 if not h:return dict(result,winerror=ctypes.get_last_error())
 try:
  out=w.DWORD();assert k.GetExitCodeProcess(h,ctypes.byref(out));return dict(result,exit_code=out.value)
 finally:k.CloseHandle(h)
print(json.dumps(dict(namespaces=v['namespaces'],matching_processes=[observe(p) for p in owned])))
'''
py='/mnt/c/Users/ecoch/AppData/Local/codex-wake-test/controller405-20261030/venv/Scripts/python.exe'
r=subprocess.run([py,'-c',code],input=json.dumps(dict(namespaces=names,server_pids=sorted(parents))),text=True,capture_output=True,check=True,timeout=30)
result=json.loads(r.stdout)
assert all(p.get('exit_code')!=259 for p in result['matching_processes']),result
(base/'cleanup-census.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
