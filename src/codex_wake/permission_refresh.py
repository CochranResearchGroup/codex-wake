"""Bounded private refresh RPC after host identity attestation (#318/#320)."""
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

from .records import WakeError
from .session_permissions import Principal, PermissionStore, check_operation, PermissionDenied


def owned_client(profile, thread):
    from .sessions import observe, revalidate_attachment
    snapshot=observe(endpoint=profile['app_server'],socket_path=profile.get('tmux_socket'),timeout=profile['timeout'])
    rows=[r for r in snapshot['sessions'] if r['thread_id']==thread]
    attachments=[a for r in rows for a in r['attachments']]
    if (not snapshot['complete'] or len(rows)!=1 or len(attachments)!=1
            or rows[0]['cwd']!=str(Path(profile['cwd']).resolve())
            or attachments[0]['session_name']!=profile.get('tmux_session')
            or not revalidate_attachment(attachments[0])):
        raise PermissionDenied('refresh_ownership_unavailable')
    return attachments[0]


def revalidate(root, context):
    return check_operation(root,context['action'],Principal(context['subject']),
        target=context['target'],relationship=context['relationship'],launch_profile=context.get('launch_profile'))


def request(packet):
    from .goal_supervision import _private
    from .shared_refresh import configuration, command
    from .wake_control import delivery_guard
    try:
        args=dict(packet['arguments']);binding=packet['binding'];root=Path(packet['root']).absolute()
        if (set(binding)!={'thread_id','turn_id','call_id'}
                or any(not isinstance(x,str) or not x for x in binding.values())
                or args['thread_id']!=args['caller_thread_id'] or args['thread_id']!=binding['thread_id']):
            raise PermissionDenied('permission_identity_unverified')
        if root!=root.resolve():raise PermissionDenied('permission_root_not_canonical')
        policy=Path(packet['profiles']).absolute();_private(policy)
        if policy!=policy.resolve():raise PermissionDenied('permission_profile_not_canonical')
        config=json.loads(policy.read_text());profile=config['profiles'][args['profile']]
        from .permission_migration import profile_ceiling
        profile_ceiling(config,args['profile'],binding['thread_id'])
        mode=profile.get('refresh_mode')
        if mode not in ('shared_mcp_idle','client_idle','thread_mcp_idle'):
            raise PermissionDenied('refresh_capability_unsupported')
        actual={'client_idle':'single_client','shared_mcp_idle':'shared_server','thread_mcp_idle':'current_connection'}[mode]
        selected=args.pop('scope',actual)
        action={'current_connection':'refresh.connection','single_client':'refresh.self','shared_server':'refresh.shared'}[selected]
        context=dict(action=action,subject=binding['thread_id'],target=(binding['thread_id'] if selected!='shared_server' else 'shared-server'),relationship=('shared' if selected=='shared_server' else 'self'),launch_profile=args['profile'])
        store=PermissionStore(root)
        decision=store.evaluate(action,Principal(context['subject']),target=context['target'],relationship=context['relationship'],launch_profile=context.get('launch_profile'))
        # Inspection reports permission separately even when denied/unsupported.
        info=configuration(config,args['profile'],args['thread_id'],args['caller_thread_id'],_permission_checked=True)
        supported=selected==actual and (selected!='current_connection' or info.get('capability')=='supported')
        if packet['verb']=='configuration':
            return dict(info,effective_permission=decision,requested_scope=selected,
                        capability='supported' if supported else 'unsupported',readiness=info.get('readiness','not_observed')),False
        if not supported:raise PermissionDenied('refresh_scope_unsupported',decision)
        revalidate(root,context)
        if mode=='client_idle':owned_client(profile,args['thread_id'])
        workspace=Path(profile['cwd']).resolve(strict=True)
        checkpoint=(workspace/args['checkpoint']).resolve(strict=True);checkpoint.relative_to(workspace)
        if not checkpoint.is_file() or checkpoint.stat().st_size>262144:
            raise PermissionDenied('refresh_checkpoint_invalid')
        content=checkpoint.read_bytes()
        if hashlib.sha256(content).hexdigest()!=args['checkpoint_sha256']:
            raise PermissionDenied('refresh_checkpoint_changed')
        args['resource']=args.pop('resources');args.update(profiles=str(policy),as_json=True)
        args.setdefault('rollback',False)
        root.mkdir(parents=True,exist_ok=True,mode=0o700);_private(root,True)
        output=[]
        with delivery_guard(root):
            revalidate(root,context)
            status=command(SimpleNamespace(**args),root,config,profile,checkpoint,content,
                permission_context=context,emit_result=lambda value,_json:output.append(value))
        return output[-1],status!=0
    except (OSError,ValueError,TypeError,KeyError,AttributeError,WakeError) as exc:
        return dict(error=dict(code=getattr(exc,'code','refresh_unavailable'),message=str(exc)),
                    effective_permission=getattr(exc,'decision',None)),True


def main():
    import sys
    try:
        raw=sys.stdin.buffer.read(65537)
        if len(raw)>65536:raise ValueError('private refresh packet exceeds limit')
        packet=json.loads(raw)
        value,failed=request(packet)
    except (ValueError,TypeError) as exc:
        value,failed=dict(error=dict(code='invalid_argument',message=str(exc))),True
    print(json.dumps(value))
    return 2 if failed else 0


if __name__=='__main__':raise SystemExit(main())


def cli_request(args,root,verb):
    from .permission_commands import verified_cli_principal
    principal=verified_cli_principal(args)
    if principal.role!='operator' and principal.subject!=args.thread_id:
        raise PermissionDenied('permission_identity_unverified')
    arguments={name:getattr(args,name) for name in (
        'thread_id','profile','caller_thread_id','scope') if getattr(args,name,None) is not None}
    arguments['caller_thread_id']=args.thread_id
    if verb=='refresh':
        for name in ('intent','checkpoint','checkpoint_sha256','expires_at','rollback'):
            arguments[name]=getattr(args,name)
        arguments['resources']=args.resource
    value,failed=request(dict(verb=verb,arguments=arguments,root=str(root),profiles=args.profiles,
        binding=dict(thread_id=args.thread_id,turn_id='operator-cli',call_id=getattr(args,'intent','inspect'))))
    print(json.dumps(value))
    return 2 if failed else 0
