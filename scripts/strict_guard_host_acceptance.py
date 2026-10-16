"""Opt-in disposable guard/cgroup proof. All token telemetry is injected.

No Codex/provider calls, shared roots, or production processes. Run explicitly.
"""
import argparse
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from uuid import uuid4
from codex_wake.host_execution import SystemdExecution
from codex_wake.objective_ledger import ObjectiveLedger
from codex_wake.process import process_identity,boot_id_value


def write(path,value):
    path.write_text(json.dumps(value));path.chmod(0o600)


def execute(output):
    results=[];host=SystemdExecution();source=str(Path(__file__).resolve().parents[1]/'src')
    sentinel=subprocess.Popen(['/bin/sleep','60'])
    try:
        for case in ('deadline','controller_death','accounting_loss','injected_token_exhaustion'):
            with tempfile.TemporaryDirectory(prefix='cw166g-') as tmp:
                root=Path(tmp);home=root/'home';home.mkdir(mode=0o700);(home/'sessions').mkdir()
                lifecycle=root/'lifecycle';lifecycle.mkdir(mode=0o700)
                now=time.time();boot=time.clock_gettime(time.CLOCK_BOOTTIME)
                limits=dict(memory_max_bytes=134217728,memory_swap_max_bytes=0,cpu_quota_percent=50,
                    tasks_max=32,stop_grace_seconds=.3,checkpoint_grace_seconds=.2,
                    poll_seconds=.05,accounting_max_age_seconds=8)
                cfg=dict(revision='fixture',objective_token_limit=200,objective_time_limit_seconds=20,
                    session_token_limit=100,session_time_limit_seconds=15,max_correction_cycles=1,
                    started_at=now,objective_deadline=now+20,strict_execution=dict(limits=limits))
                ledger=ObjectiveLedger(root,'fixture');ledger.configure(cfg,'disposable-fixture',now=now)
                ledger.reserve('worker',100,15,now=now)
                controller=subprocess.Popen(['/bin/sleep','30'])
                identity=None;unit='codex-wake-objective-'+uuid4().hex+'.service'
                try:
                    write(lifecycle/'supervision.json',dict(active=True,pid=controller.pid,
                        identity=process_identity(controller.pid),observed_at=now,interval=.05))
                    write(lifecycle/'spawn.json',dict(thread_id='fixture-thread',budget_actor='worker',
                        intent=dict(operation='spawn',configuration=cfg,continuation=dict(objective_id='fixture'),
                            launch=dict(app_server='unix:///fixture.sock',codex_home=str(home)))))
                    rollout=home/'sessions'/'fixture.jsonl'
                    rows=[dict(type='session_meta',payload=dict(id='fixture-thread')),
                        dict(type='event_msg',timestamp=datetime.fromtimestamp(now,timezone.utc).isoformat(),
                            payload=dict(type='token_count',info=dict(total_token_usage=dict(total_tokens=20))))]
                    rollout.write_text('\n'.join(json.dumps(r) for r in rows)+'\n');rollout.chmod(0o600)
                    proof=root/'child.json'
                    child_code='import os,signal,subprocess,time,json,pathlib;signal.signal(signal.SIGTERM,signal.SIG_IGN);p=subprocess.Popen(["/bin/sleep","30"]);pathlib.Path('+repr(str(proof))+').write_text(json.dumps({"parent":os.getpid(),"child":p.pid}));time.sleep(30)'
                    config=dict(wake_root=str(root),objective_id='fixture',endpoint='unix:///fixture.sock',
                        codex_home=str(home),cwd=str(root),argv=[sys.executable,'-c',child_code],
                        configuration=cfg,started_upper=now,started_boottime=boot,boot_id=boot_id_value(),
                        deadline=now+3 if case=='deadline' else now+20,status_path=str(root/'status.json'),generation=unit)
                    write(root/'guard.json',config)
                    start=time.monotonic()
                    identity=host.launch(unit,[sys.executable,'-m','codex_wake.strict_executor',str(root/'guard.json')],
                        cwd=str(root),environment=dict(PYTHONPATH=source),
                        limits={k:limits[k] for k in ('memory_max_bytes','memory_swap_max_bytes','cpu_quota_percent','tasks_max','stop_grace_seconds')},runtime_seconds=8)
                    until=start+3
                    while not proof.exists() and time.monotonic()<until:time.sleep(.02)
                    if not proof.exists():raise RuntimeError('guard did not launch fixture child')
                    before=host.inspect(identity);pids=json.loads(proof.read_text())
                    assert set(pids.values())<=set(before['members'])
                    if case=='controller_death':controller.kill();controller.wait()
                    elif case=='accounting_loss':rollout.write_text('malformed\n')
                    elif case=='injected_token_exhaustion':
                        rows[1]['payload']['info']['total_token_usage']['total_tokens']=101
                        rollout.write_text('\n'.join(json.dumps(r) for r in rows)+'\n')
                    triggered=time.monotonic()
                    until=start+10
                    while time.monotonic()<until:
                        after=host.inspect(identity)
                        if not after['populated']:break
                        time.sleep(.02)
                    status=json.loads((root/'status.json').read_text())
                    assert not after['populated'] and not after['members'],after
                    assert sentinel.poll() is None
                    results.append(dict(case=case,telemetry='injected_fixture',identity=identity,
                        kernel_limits=before['kernel_limits'],status=status,after=after,
                        elapsed_seconds=time.monotonic()-start,trigger_to_empty_seconds=time.monotonic()-triggered,
                        sentinel_survived=True))
                finally:
                    if identity:host.stop(identity)
                    subprocess.run(['systemctl','--user','reset-failed',unit],capture_output=True)
                    if controller.poll() is None:controller.terminate();controller.wait()
    finally:
        sentinel.terminate();sentinel.wait()
        output.write_text(json.dumps(results,indent=2)+'\n')
    assert len(results)==4
    print(json.dumps([dict(case=r['case'],reason=r['status']['reason'],seconds=r['elapsed_seconds']) for r in results]))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--execute',action='store_true',required=True)
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();execute(args.output)
