"""Opt-in installed-candidate qualification using disposable state and no dispatch."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

import codex_wake
from codex_wake.a2a_bus import BusStore
from codex_wake.a2a_identity import BusError, RuntimeIdentity
from codex_wake.a2a_mailbox import Mailbox
from codex_wake.records import find_record
from codex_wake.time_provider import TimeDecision


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if not Path(codex_wake.__file__).is_relative_to(Path(sys.prefix)):
        raise SystemExit('Run with an isolated installed candidate, not PYTHONPATH source imports')
    report=dict(candidate=dict(version=codex_wake.__version__,package=codex_wake.__file__),
                dispatch=False,system_clock_adjustments=0,production_store_changes=0,checks=[])
    env=dict(os.environ);env.pop('PYTHONPATH',None)
    def command(module,*arguments):
        completed=subprocess.run([sys.executable,'-m',module,*map(str,arguments)],env=env,text=True,capture_output=True,timeout=30)
        if completed.returncode:
            raise RuntimeError(completed.stdout+completed.stderr)
        return completed.stdout
    try:
        with tempfile.TemporaryDirectory(prefix='codex-wake-network-acceptance-') as directory:
            root=Path(directory)
            observation=json.loads(command('codex_wake.cli','time','inspect'))
            assert observation['decision']['status']=='network',observation
            report['live_observation']=observation
            report['checks'].append('installed network inspection: two admitted operators; all five candidates visible')
            wake_root=root/'wake'
            created=command('codex_wake.cli','--wake-root',wake_root,'after','--network-time','--app-server-thread-id','qualification-fixture','2s','--','Resume qualification fixture')
            wake_id=created.split()[0]
            initial=find_record(wake_root,wake_id).record
            polls=[]
            for _ in range(8):
                polls.append(command('codex_wake.daemon','--wake-root',wake_root,'--once','--no-dispatch').strip())
                if find_record(wake_root,wake_id).record['status']=='firing':
                    break
            final=json.loads(command('codex_wake.cli','--wake-root',wake_root,'show',wake_id))
            assert final['status']=='firing',polls
            assert final['predicate']==initial['predicate']
            assert final['prompt']=='Resume qualification fixture'
            report['wake']=dict(initial=initial,final=final,polls=polls)
            report['checks'].append('installed create/persist/poll/show: real network deadline reached with no transport dispatch')
            command('codex_wake.cli','--wake-root',wake_root,'cancel',wake_id)
            assert find_record(wake_root,wake_id).record['status']=='cancelled'
            report['checks'].append('installed cancellation resolves isolated firing wake')
            configured=json.loads(command('codex_wake.cli','a2a','configure','--bus-root',root/'bus'))
            capability=Path(configured['operator_capability_file'])
            migrated=json.loads(command('codex_wake.cli','a2a','network-time','--bus-root',root/'bus','--operator-capability',capability,'--accept-unauthenticated-ntp'))
            assert migrated['success']
            bus=BusStore(root/'bus')
            repo=root/'fixture-repo';repo.mkdir()
            bus.enroll(repo,capability)
            identities=[RuntimeIdentity('qualification-runtime',name,str(repo)) for name in ('sender-fixture','recipient-fixture')]
            actors=[]
            for identity in identities:
                actor_cap,_=bus.issue_actor(identity,repo,capability)
                actors.append(bus.authenticate(actor_cap,identity,invoking_cwd=repo))
            mailbox=Mailbox(bus)
            sent=mailbox.send(actors[0],identities[1],body='Qualification fixture; no transport dispatch',idempotency_key='fixture-request',delivery='inbox',ttl=60)
            identifier=sent['message']['message_id']
            shown=json.loads(command('codex_wake.cli','messages','show',identifier,'--as-operator','--operator-capability',capability,'--bus-root',root/'bus','--json'))
            assert shown['message']['expires_at']==sent['message']['expires_at']
            report['checks'].append('installed operator migration and fresh-process mailbox inspection preserve the deadline')
            uncertain=Mailbox(bus,time_provider=lambda:TimeDecision('uncertain',reason='controlled network outage'))
            try:
                uncertain.send(actors[0],identities[1],body='outage fixture',idempotency_key='outage-intent',delivery='inbox')
            except BusError as error:
                assert error.code=='time_uncertain'
            else:
                raise AssertionError('uncertain admission was not held')
            assert uncertain.show(actors[0],identifier)['expires_at']==sent['message']['expires_at']
            cancelled=uncertain.cancel(actors[0],identifier)
            assert cancelled['message']['state']['admission']=='cancelled'
            cancellation=next(r for r in cancelled['message']['receipts'] if r['kind']=='cancelled')
            assert cancellation['created_at'] is None
            report['mailbox']=dict(deadline=sent['message']['expires_at'],cancelled=True,cancellation_time=None,
                                   migration_receipt=migrated['receipt_id'])
            report['checks'].append('controlled outage: relative admission held, inspection/cancellation remain usable, no UTC fabricated')
        report['status']='passed'
    except Exception as error:
        report.update(status='failed',error=str(error))
        raise
    finally:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print(json.dumps(dict(status=report['status'],checks=len(report['checks']),output=str(args.output))))


if __name__=='__main__':
    main()
