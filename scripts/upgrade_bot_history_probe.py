"""Fresh disposable failed-start/history/rollback proof for one exact package.

Runs the existing managed journey inside an isolated loopback-only namespace.
Does not select a working-account package, import credentials or call a provider.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import pwd
import signal
import subprocess
import sys
import time
import uuid


def file_hash(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def owned_processes(root):
    result=[]
    for item in Path('/proc').iterdir():
        if not item.name.isdigit() or int(item.name)==os.getpid():continue
        try:
            if item.stat().st_uid!=os.getuid():continue
            fields=(item/'stat').read_text().rsplit(')',1)[1].split()
            if fields[0]=='Z':continue
            env=(item/'environ').read_bytes().split(b'\0')
            home=next((entry.split(b'=',1)[1].decode() for entry in env if entry.startswith(b'CODEX_HOME=')),None)
            cwd=(item/'cwd').resolve(strict=True)
            if (home and Path(home).is_relative_to(root)) or cwd.is_relative_to(root):
                result.append(dict(pid=int(item.name),start=fields[19]))
        except (OSError,ValueError,IndexError):continue
    return result


def cleanup(root):
    for sig in (signal.SIGTERM,signal.SIGKILL):
        for proc in owned_processes(root):
            try:
                stat=Path('/proc',str(proc['pid']),'stat').read_text().rsplit(')',1)[1].split()
                if stat[19]==proc['start']:os.kill(proc['pid'],sig)
            except (OSError,IndexError):pass
        if sig==signal.SIGTERM:time.sleep(.25)
    return owned_processes(root)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('package','baseline','root','wake-prefix'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--timeout',type=int,default=300)
    args=parser.parse_args(argv)
    if os.getuid()!=1000 or os.environ.get('WSL_DISTRO_NAME')!='wsl-test':
        parser.error('run inside disposable wsl-test as ubuntu')
    root=args.root.resolve();lab=Path('/home/ubuntu/codex-profile-lab')
    if not root.is_relative_to(lab) or root==lab:parser.error('owned disposable child root required')
    root.mkdir(parents=True,exist_ok=True,mode=0o700)
    if root.is_symlink() or root.stat().st_uid!=os.getuid() or root.stat().st_mode&0o022:parser.error('private owned fixture root required')
    if (root/'receipt.json').exists():parser.error('use a fresh root; previous evidence is retained')
    if not 1<=args.timeout<=600:parser.error('timeout must be1–600 seconds')
    executable=(args.package/'bin/codex').resolve(strict=True)
    baseline=(args.baseline/'bin/codex').resolve(strict=True)
    marker=args.package/'codex-resources/upgrade-qualification.txt'
    if not marker.is_file():parser.error('candidate must contain its build-time qualification marker')
    harness=Path(__file__).with_name('native_daemon_upgrade_resume_acceptance.py').resolve(strict=True)
    case='upgrade453-'+uuid.uuid4().hex[:12]
    report=dict(schema_version=1,status='failed',native_sha256=file_hash(executable),baseline_sha256=file_hash(baseline),
        checks={},model_requests=0,external_provider_requests=0,scripted_provider_requests=0,
        harness_sha256=file_hash(harness),root=str(root),owned_processes_remaining=[],started_at=time.time())
    isolated_home=root/'operator-home';isolated_home.mkdir(mode=0o700)
    env={key:value for key,value in os.environ.items() if key in ('PATH','LANG','LC_ALL')}
    declarations=dict(HOME=str(isolated_home),USER='ubuntu',LOGNAME='ubuntu',WSL_DISTRO_NAME='wsl-test',
        XDG_CONFIG_HOME=str(root/'xdg-config'),XDG_STATE_HOME=str(root/'xdg-state'),
        CODEX_QUALIFICATION_TEST_ROOT=str(root),CODEX_QUALIFICATION_WAKE_PREFIX=str(args.wake_prefix),
        CODEX_QUALIFICATION_BASELINE=str(baseline),CODEX_QUALIFICATION_TARGET=str(executable),
        CODEX_QUALIFICATION_ROLLBACK=str(baseline),CODEX_QUALIFICATION_MODE='startup-fail',CODEX_QUALIFICATION_HEALTH='1')
    command=['sudo','-n','unshare','--net','--','/bin/sh','-c','ip link set lo up; exec "$@"','history-netns',
        'sudo','-u',pwd.getpwuid(os.getuid()).pw_name,'env',*[key+'='+value for key,value in dict(env,**declarations).items()],
        sys.executable,str(harness),case]
    process=None
    previous=signal.signal(signal.SIGTERM,lambda *_:(_ for _ in ()).throw(InterruptedError('owned history probe stopped')))
    try:
        with (root/'journey.log').open('wb') as log:
            process=subprocess.Popen(command,env=env,stdout=log,stderr=log,start_new_session=True)
            process.wait(timeout=args.timeout)
        receipt=root/('resume-journey-'+case)/'receipt.json'
        data=json.loads(receipt.read_text())
        assert process.returncode==0 and data['state']=='passed',data.get('error','journey failed')
        assert data['target_sha256']==report['native_sha256'] and data['baseline_sha256']==report['baseline_sha256'],'package identity changed'
        assert data['rollback_expected_sha256']==report['baseline_sha256'],'rollback differs from qualified baseline'
        assert data.get('failed_start_injection') and data.get('failed_start_no_work_before_repair') is True,'failed start not established'
        assert data.get('counters_and_limits_preserved') is True and data.get('rollback_preserves_handoffs') is True,'continuity not established'
        assert data.get('all_tabs_notified') is True and data.get('ui_after_rollback') and data.get('resumed_output_in_original_tabs'),'actual tab/history proof missing'
        assert data.get('external_model_calls')==0 and data.get('external_provider_calls')==0,'external effect boundary violated'
        report.update(status='passed',checks=dict(history_visibility=True,failed_start_recovery=True,compatible_rollback=True),
            scripted_provider_requests=len(data['calls']),journey_receipt=str(receipt),journey_receipt_sha256=file_hash(receipt))
    except (OSError,ValueError,KeyError,AssertionError,subprocess.SubprocessError,InterruptedError) as error:
        report.update(status='failed',reason=str(error))
    finally:
        if process is not None and process.poll() is None:
            try:os.killpg(process.pid,signal.SIGTERM)
            except (OSError,PermissionError):pass
            try:process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                try:os.killpg(process.pid,signal.SIGKILL)
                except (OSError,PermissionError):pass
        report['owned_processes_remaining']=cleanup(root)
        signal.signal(signal.SIGTERM,previous)
    if report['owned_processes_remaining']:report.update(status='failed',reason='owned processes remain')
    report['finished_at']=time.time()
    (root/'receipt.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,sort_keys=True))
    return 0 if report['status']=='passed' else 1


if __name__=='__main__':raise SystemExit(main())
