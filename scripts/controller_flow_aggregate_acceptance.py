#!/usr/bin/env python3
"""Provider-free installed flow matrix, including real evaluator process loss.

This runner exercises existing owners and all five public surfaces in isolated
fixtures. Native packaged fork qualification remains its separate pinned receipt;
fixture protocol results never imply platform or production acceptance.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    import codex_wake
    installed=Path(codex_wake.__file__).resolve().parent
    source=Path(__file__).resolve().parent.parent
    assert source/'src' not in installed.parents,'run with an installed package and PYTHONPATH unset'
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()
    env={key:value for key,value in os.environ.items() if key!='PYTHONPATH'}
    env['WAKE_ACCEPTANCE_SOURCE_SHA']=commit
    matrix=[('versioned_wait_and_late_result',['controller_flow_acceptance.py']),
            ('new_session_and_sequential_foreach',['controller_foreach_acceptance.py']),
            ('join_retry_cancel_revocation',['controller_foreach_acceptance.py','--join-and-retry']),
            ('common_prefix_fork_protocol',['controller_fork_acceptance.py']),
            ('typed_composed_semantic_conditions',['controller_conditions_acceptance.py']),
            ('original_semantic_limit_cleanup',['controller_conditions_acceptance.py','--limit-stop']),
            ('process_loss_and_transport_recovery',['controller_flow_recovery_acceptance.py'])]
    checks=[]
    for name,arguments in matrix:
        command=[sys.executable,str(source/'scripts'/arguments[0]),*arguments[1:]]
        began=time.monotonic()
        process=subprocess.run(command,env=env,cwd=source,text=True,capture_output=True,timeout=180)
        if process.returncode:
            raise RuntimeError((name,process.returncode,process.stdout[-8000:],process.stderr[-8000:]))
        result=json.loads(process.stdout.strip().splitlines()[-1])
        assert result['status']=='passed',(name,result)
        checks.append(dict(name=name,command=command,exit_code=0,elapsed_seconds=round(time.monotonic()-began,3),
                           result=result,stderr_sha256=hashlib.sha256(process.stderr.encode()).hexdigest()))
    modules=['controller_flows.py','controller_conditions.py','controller_condition_native.py','controller_flow_foreach.py',
             'controller_flow_sessions.py','controller_flow_fork.py','controller_flow_retry.py']
    hashes={name:hashlib.sha256((installed/name).read_bytes()).hexdigest() for name in modules}
    assert all(value==hashlib.sha256((source/'src/codex_wake'/name).read_bytes()).hexdigest() for name,value in hashes.items())
    evidence=dict(schema_version=1,ticket=411,status='passed',source_commit=commit,python=sys.version,
        platform=platform.platform(),installed_package=str(installed),installed_source_sha256=hashes,checks=checks,
        hosted_ci='not run: operator requires local validation; no GitHub Actions capacity requested',
        hosted_environment_differences='local Linux/WSL Python3.12 only; deterministic Unix fixtures; no hosted OS matrix, native build, provider turn or production activation',
        retained_native_boundary='docs/dev/evidence/plan0190/fork408-native-correction.json retains actual packaged native lastTurnId proof; this aggregate reruns the protocol fixture only',
        authorities=dict(resource_mode='manual',resource_renewals=0,governor_enrollments=0,shared_restarts=0,provider_experiments=0))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(evidence,indent=2,sort_keys=True)+'\n')
    print(json.dumps(dict(status='passed',output=str(args.output),checks=len(checks),source_commit=commit)))


if __name__=='__main__':main()
