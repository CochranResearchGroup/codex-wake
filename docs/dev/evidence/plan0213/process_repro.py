import json,sys,tempfile,time,subprocess
from pathlib import Path
from codex_wake.controller_tab_adapters import TmuxAttachmentTransport
from codex_wake.controller_tabs import ControllerTabs
with tempfile.TemporaryDirectory(prefix='wake-format-perf-') as td:
 root=Path(td);sock=str(root/'tmux.sock')
 def tmux(*a):return subprocess.run(['tmux','-S',sock,*a],capture_output=True,text=True,timeout=5,check=True).stdout
 tmux('new-session','-d','-s','fixture','exec sleep 120')
 try:
  for i in range(int(sys.argv[1]) if len(sys.argv)>1 else 41):tmux('new-window','-d','-t','fixture:','exec sleep 120')
  tabs=ControllerTabs(root,workspaces={'work':dict(kind='tmux',transport=TmuxAttachmentTransport(sock,'$0'))},host='fixture',environment='local')
  timings=[]
  from unittest.mock import patch
  original=subprocess.run;calls=[]
  def counted(*a,**k):
   calls.append(a[0]);return original(*a,**k)
  scope=patch('subprocess.run',side_effect=counted);scope.start()
  for verb in ['enable','rollback']:
   start=time.monotonic();r=tabs.execute('tabs.format.'+verb,dict(workspace='work'));elapsed=time.monotonic()-start
   timings.append(dict(verb=verb,seconds=round(elapsed,3),status=r.get('status'),failures=len(r.get('failures',[]))))
  scope.stop();print('tmux process launches:',len(calls));assert len(calls)<500,'Excessive per-option tmux process launches';print(json.dumps(timings));assert all(x['status'] in ('applied','rolled_back') for x in timings),'Formatting/rollback exceeds workspace deadline'
 finally:tmux('kill-server')
