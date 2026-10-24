"""Pin human message destinations before admission, including interrupted attempts."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace

from .agent_lifecycle import save
from .a2a_identity import BusError
from .tab_targets import prepare_target, revalidate_target


def routed_send(args, bus, mailbox, actor, body, key, resolve_identity):
    # An authenticated identity alone is not a current send grant.
    with bus.connection() as database:
        bus.validate_actor(database, actor, permission='send')
    root = args.wake_root or bus.root
    options = dict(selector=args.to, on_missing=args.on_missing, on_inactive=args.on_inactive,
        cwd=args.cwd, expected_cwd=args.expected_cwd, resume_thread_id=args.resume_thread_id,
        profile=args.profile, expires_at=args.expires_at, body_sha256=hashlib.sha256(body.encode()).hexdigest(),
        delivery=args.delivery, kind=args.kind, ttl=args.ttl, subject=args.subject,
        correlation=args.correlation, resume_missing=args.resume_missing,
        runtime=[args.app_server,args.tmux_socket,args.tmux_session],caller=actor.key)
    if getattr(args,'task_id',None) is not None:options['task_id']=args.task_id
    fingerprint = hashlib.sha256(json.dumps(options,sort_keys=True).encode()).hexdigest()
    route_key = hashlib.sha256(json.dumps([actor.key,key]).encode()).hexdigest()
    path = Path(root)/'lifecycle'/('route-'+route_key+'.json')
    path.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
    with path.with_suffix('.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        if path.exists():
            receipt=json.loads(path.read_text())
            if receipt['fingerprint'] != fingerprint:
                raise BusError('idempotency_conflict','intent binds different target/message options')
        else:
            receipt=dict(version=1,state='prepared',fingerprint=fingerprint,report=None)
            save(path,receipt)
        target_args=SimpleNamespace(**vars(args))
        target_args.selector=args.to
        target_args.intent='send-'+route_key
        target_args.caller_thread_id=os.environ.get('CODEX_THREAD_ID')
        target_args.assignment_digest=fingerprint
        target_args.timeout=10
        if receipt['report'] is None or receipt['report']['status'] in ('starting','effect_uncertain','inventory_unavailable'):
            report=prepare_target(target_args,root)
            receipt['report']=report
            save(path,receipt)
        else:
            report=receipt['report']
        if report['status'] not in ('resolved','target_busy') or not report.get('thread_id'):
            return dict(target=report,idempotency_key=key,admitted=False), False
        report=revalidate_target(report,target_args)
        if report['status'] != 'resolved':
            return dict(target=report,idempotency_key=key,admitted=False), False
        thread=report['session']['thread_id']
        recipient=resolve_identity('thread:'+thread,endpoint=args.app_server,allow_offline=True)
        if recipient.thread_id != thread or recipient.cwd != report['cwd']:
            report=dict(report,status='target_changed')
            return dict(target=report,idempotency_key=key,admitted=False),False
        # Identity metadata and live pane generation both remain pinned just before admission.
        report=revalidate_target(report,target_args)
        if report['status'] != 'resolved':
            return dict(target=report,idempotency_key=key,admitted=False),False
        from .records import parse_duration
        value=mailbox.send(actor,recipient,body=body,idempotency_key=key,kind=args.kind,
            ttl=parse_duration(args.ttl).total_seconds(),delivery=args.delivery,subject=args.subject,
            selector=dict(selector=args.to,identity=thread),correlation=args.correlation,
            resume_missing=args.resume_missing,task_id=getattr(args,'task_id',None))
        return dict(value,target=report),True
