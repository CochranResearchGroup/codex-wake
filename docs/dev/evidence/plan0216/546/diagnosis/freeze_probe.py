"""One disposable causal probe: freeze a real monitor while it owns the lock."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from test_tab_format_cli_status import FormattingCLIStatusTests

fixture=FormattingCLIStatusTests('test_unqualified_running_monitor_is_partial_exit_without_restarting_it')
fixture.setUp()
pid=None
try:
    started=fixture.monitor.execute('tabs.monitor.start',dict(interval=.2))
    pid=started['monitor']['process']['pid']
    lock=fixture.root/'tab-formatting'/'lock'
    def held():
        if not lock.exists():return False
        inode=lock.stat().st_ino
        return any(parts[4]==str(pid) and parts[5].endswith(':'+str(inode))
                   for line in Path('/proc/locks').read_text().splitlines()
                   if len(parts:=line.split())>=6)
    deadline=time.monotonic()+5
    while time.monotonic()<deadline:
        if held():
            os.kill(pid,signal.SIGSTOP)
            if held():break
            os.kill(pid,signal.SIGCONT)
        time.sleep(.001)
    else:raise AssertionError('could not freeze owned formatting lock within bound')
    path=fixture.root/'tab-monitor'/'owner.json'
    record=json.loads(path.read_text());record['capabilities']=[];path.write_text(json.dumps(record))
    result=subprocess.run([sys.executable,'-m','codex_wake.entrypoint','--wake-root',str(fixture.root),
        'tabs','format','enable','--workspace','work'],capture_output=True,text=True,timeout=15)
    print(json.dumps(dict(lock_held_while_stopped=held(),returncode=result.returncode,
                         stdout=result.stdout,stderr=result.stderr),indent=2))
finally:
    if pid is not None:os.kill(pid,signal.SIGCONT)
    fixture.doCleanups()
