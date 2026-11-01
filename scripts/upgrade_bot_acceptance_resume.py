#!/usr/bin/env python3
"""Explicit verification-only continuation of one already held disposable job.

Original admission, counters and clock remain authoritative. This command never
creates/enables a job and never dispatches a new semantic coding attempt.
"""
import argparse
import hashlib
import json
from pathlib import Path
import time

from codex_profiles.upgrades import _atomic
from codex_wake.operation_commands import local_actor
from codex_wake.upgrade_jobs import TERMINAL, UpgradeJobs


def run(root,identifier,deadline,attempts,evidence):
    root=Path(root).resolve(strict=True);evidence=Path(evidence).resolve()
    evidence.mkdir(mode=0o700,parents=True,exist_ok=False)
    config=json.loads((root/'upgrade-bot.json').read_text());target=config['target']
    if target.get('environment')!='test':raise ValueError('explicit disposable test target required')
    receipt=dict(schema_version=1,started_at=time.time(),root=str(root),job_id=identifier,
        original_deadline=deadline,original_attempts=attempts,phases=[],
        launcher_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    def call(verb,**arguments):
        actor=local_actor(root)
        result=UpgradeJobs(root).execute(actor,'upgrades.'+verb,
            dict(expected_target=target,job_id=identifier,**arguments),authorize=lambda:local_actor(root))
        receipt['phases'].append(dict(operation=verb,at=time.time(),result=result))
        _atomic(evidence/'checkpoint.json',receipt)
        job=result['result']['job']
        if job['id']!=identifier or job['deadline']!=deadline or job['repair_attempts']!=attempts:
            raise ValueError('original accounting changed; continuation refused')
        return job
    try:
        original=call('show')
        if original['state']!='held':raise ValueError('explicit held-job readmission required')
        job=call('reconcile',mode='verify_only')
        for unused in range(3):
            if job['state'] in TERMINAL:break
            job=call('advance')
        job=call('show')
        receipt.update(status=job['state'],reason=job.get('reason'),job=job,
            exit_code=0 if job['state']=='succeeded' else 1)
    except BaseException as error:
        receipt.update(status='continuation_failed',reason=type(error).__name__+': '+str(error),exit_code=1)
        if isinstance(error,(KeyboardInterrupt,SystemExit)):raise
    finally:
        receipt['finished_at']=time.time();_atomic(evidence/'completion.json',receipt)
    return receipt


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--job-id',required=True)
    parser.add_argument('--original-deadline',type=float,required=True)
    parser.add_argument('--original-attempts',type=int,required=True)
    parser.add_argument('--evidence',type=Path,required=True)
    args=parser.parse_args()
    receipt=run(args.root,args.job_id,args.original_deadline,args.original_attempts,args.evidence)
    print(json.dumps({k:receipt.get(k) for k in ('status','reason','job_id','exit_code')}))
    return receipt['exit_code']


if __name__=='__main__':raise SystemExit(main())
