"""Guarded target preparation sharing the lifecycle journal and effect gates."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace

from .agent_lifecycle import before_effect, save
from .native_protocol import native_request
from .records import WakeError
from .session_lifecycle import tmux_command
from .sessions import observe
from .shared_app_server import SharedAppServerReader
from .tab_targets import canonical


def saved_history(endpoint, cwd, timeout):
    with SharedAppServerReader(endpoint, timeout=timeout) as reader:
        return reader.saved_threads(cwd)


def approved_profile(args):
    config = json.loads(Path(args.profiles).read_text())
    profile = config['profiles'][args.profile]
    required = {'cwd', 'app_server', 'codex_path', 'tmux_session', 'timeout'}
    if (config.get('version') != 1 or not isinstance(profile, dict) or not required <= profile.keys()
            or profile.keys() - required - {'tmux_socket', 'codex_home', 'resources'}
            or any(not isinstance(profile[k], str) or not profile[k] or '\x00' in profile[k]
                   for k in required - {'timeout'})
            or type(profile['timeout']) not in (int, float) or not 0 < profile['timeout'] <= 60
            or not Path(profile['cwd']).is_dir()):
        raise ValueError('approved launch profile is incomplete')
    # Preparation does not copy credentials, enroll actors, assign work or start a goal.
    caller = args.caller_thread_id or os.environ.get('CODEX_THREAD_ID')
    if not caller or args.profile not in config.get('callers', {}).get(caller, []):
        raise ValueError('host caller grant does not authorize this launch profile')
    from .shared_app_server import locate_shared_endpoint
    endpoint=locate_shared_endpoint() if args.app_server=='unix://' else args.app_server
    socket=args.tmux_socket or (os.environ.get('TMUX','').split(',')[0] or None)
    if endpoint != profile['app_server'] or socket != profile.get('tmux_socket'):
        raise ValueError('discovery and launch profile must use the same host runtime')
    if args.tmux_session and args.tmux_session != profile['tmux_session']:
        raise ValueError('tmux session differs from approved launch profile')
    return profile, caller


def prepare(args, root, value):
    try:
        profile, caller = approved_profile(args)
        cwd = canonical(value.get('cwd') or args.cwd or profile['cwd'])
        if cwd != canonical(profile['cwd']) or (args.cwd and canonical(args.cwd) != cwd):
            value.update(status='cwd_mismatch', message='CWD differs from observed tab or approved profile')
            return value
        if args.expected_cwd and canonical(args.expected_cwd) != cwd:
            value.update(status='cwd_mismatch')
            return value
        value['cwd'] = cwd
        if value['status']=='tab_not_found' and args.selector.startswith(('thread:','pane:','window:')):
            value.update(status='policy_denied',message='exact runtime identities cannot be recreated from a missing selector')
            return value
        row = value.get('session')
        attachment = row.get('selected_attachment') if row else None
        if attachment and profile['tmux_session'] not in (attachment['session_id'],attachment['session_name']):
            value.update(status='policy_denied',message='observed tab is outside approved tmux session')
            return value
        if attachment and attachment.get('pane_current_command') not in ('bash','zsh','fish','sh','dash'):
            value.update(status='target_busy', message='existing pane is not an observed shell')
            return value
        selected = None
        if value['applied_policy'] == 'resume':
            if args.resume_thread_id:
                # Exact metadata is authoritative even when thread/list omits a
                # newly materialized conversation with no user turns yet.
                thread=native_request(profile['app_server'],profile['codex_path'],'thread/read',
                    dict(threadId=args.resume_thread_id,includeTurns=False),profile['timeout'])['thread']
                if thread.get('id')!=args.resume_thread_id or canonical(thread['cwd'])!=cwd:
                    value.update(status='cwd_mismatch',message='exact saved thread differs from selected CWD')
                    return value
                if isinstance(thread.get('source'),dict) or thread.get('source') not in (None,'cli','vscode','appServer'):
                    value.update(status='policy_denied',message='exact saved thread is not an interactive session')
                    return value
                rows=[{k:thread[k] for k in ('id','cwd','name','updatedAt','source','status') if k in thread}]
            else:
                rows = saved_history(profile['app_server'], cwd, profile['timeout'])
            value['candidates'] = rows[:10]
            value['candidate_count'] = len(rows)
            if len(rows) != 1:
                value.update(status='resume_not_found' if not rows else 'resume_ambiguous',
                             next_actions=['select_exact_resume_thread'] if rows else ['fresh','error'])
                return value
            selected = rows[0]['id']
        return journaled_prepare(args, root, value, profile, caller, selected, attachment)
    except (WakeError, OSError, ValueError, KeyError, TypeError) as exc:
        value.update(status='inventory_unavailable' if isinstance(exc, WakeError) else 'policy_denied',
                     message=str(exc))
        return value


def receipt_path(root, intent):
    return Path(root) / 'lifecycle' / ('target-' + hashlib.sha256(intent.encode()).hexdigest() + '.json')


def binding(args, profile, caller):
    return dict(operation='target', profile=args.profile, launch=profile, caller=caller,
        selector=args.selector, on_missing=args.on_missing, on_inactive=args.on_inactive,
        expected_cwd=args.expected_cwd, cwd=args.cwd, resume_thread_id=args.resume_thread_id,
        expires_at=args.expires_at, assignment_digest=getattr(args,'assignment_digest',None))


def replay(args, root):
    path = receipt_path(root, args.intent)
    if not path.exists():
        return None
    try:
        profile, caller = approved_profile(args)
        return journaled_prepare(args, root, None, profile, caller, None, None)
    except (ValueError, KeyError, TypeError, OSError, WakeError):
        return dict(status='policy_denied', effects=[], message='existing intent host scope changed')


def journaled_prepare(args, root, value, profile, caller, selected, attachment):
    intent = binding(args, profile, caller)
    fingerprint = hashlib.sha256(json.dumps(intent, sort_keys=True).encode()).hexdigest()
    path = receipt_path(root, args.intent)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with path.with_suffix('.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if path.exists():
            receipt = json.loads(path.read_text())
            if receipt['fingerprint'] != fingerprint:
                return dict(status='policy_denied', effects=[], message='intent key binds different target options')
        else:
            receipt = dict(version=1, intent_key=args.intent, fingerprint=fingerprint, intent=intent,
                state='prepared', thread_id=selected, report=value, original_attachment=attachment)
            save(path, receipt)
        advance(path, receipt, profile)
        return receipt['report']


def same_attachment(old, new):
    fields = ('socket','session_id','window_id','window_index','window_name','pane_id',
              'pane_current_path','pane_title','client_pid','client_start_time_ticks','pane_pid')
    return all(old.get(k) == new.get(k) for k in fields)


def original_unchanged(receipt, profile):
    from .tab_targets import inspect_target
    snapshot = observe(endpoint=profile['app_server'], socket_path=profile.get('tmux_socket'), timeout=profile['timeout'], shell_metadata=True)
    if not snapshot['complete']:
        return False
    old = receipt['original_attachment']
    if old:
        panes = [p for r in snapshot['sessions'] for p in r['attachments'] if p['pane_id'] == old['pane_id']]
        return len(panes) == 1 and same_attachment(old, panes[0]) and panes[0].get('pane_current_command') in ('bash','zsh','fish','sh','dash')
    current = inspect_target(snapshot, receipt['intent']['selector'], session=profile['tmux_session'])
    return current['status'] == 'tab_not_found'


def mark(path, receipt, status, **details):
    receipt['report'].update(status=status, **details)
    save(path, receipt)


def gate(path, receipt):
    if before_effect(path, receipt):
        return True
    mark(path, receipt, 'policy_denied', message=receipt.get('reason'))
    return False


def advance(path, receipt, profile):
    import shlex
    value = receipt['report']
    runtime = SimpleNamespace(**(dict(tmux_socket=None) | profile))
    if receipt['state'] in ('starting','uncertain'):
        effect=receipt.get('uncertain_effect')
        matches=[]
        if effect in ('tmux/new-window','tmux/split-window') and receipt['thread_id']:
            observed=observe(endpoint=profile['app_server'],socket_path=profile.get('tmux_socket'),
                             timeout=profile['timeout'],shell_metadata=True)
            old=receipt['original_attachment']
            if observed['complete']:
                matches=[(r,p) for r in observed['sessions'] for p in r['attachments']
                    if r['thread_id']==receipt['thread_id'] and canonical(r['cwd'])==value['cwd']
                    and profile['tmux_session'] in (p['session_id'],p['session_name'])
                    and (p['window_id']==old['window_id'] if old else
                         p['window_name']==receipt.get('created_name'))]
        if len(matches)!=1:
            receipt['state']='uncertain'
            mark(path,receipt,'effect_uncertain',uncertain_effect=effect,
                 reconciliation_required=True,next_actions=['reconcile_same_intent'])
            return
        row,pane=matches[0]
        receipt.update(pane_id=pane['pane_id'],window_id=pane['window_id'],state='awaiting_preflight')
        receipt.pop('uncertain_effect',None)
        value.pop('uncertain_effect',None)
        value['reconciliation_required']=False
        value['effects'].append(dict(operation=effect,pane_id=pane['pane_id'],window_id=pane['window_id'],
                                     recovered_from='exact_native_binding'))
        save(path,receipt)
    if receipt['state'] == 'completed':
        if value.get('session') and value.get('thread_id'):
            from .tab_targets import revalidate_target
            options=SimpleNamespace(app_server=profile['app_server'],tmux_socket=profile.get('tmux_socket'),timeout=profile['timeout'], shell_metadata=True)
            receipt['report']=revalidate_target(value,options)
            save(path,receipt)
        return
    if receipt.get('pane_id'):
        current = observe(endpoint=profile['app_server'], socket_path=profile.get('tmux_socket'), timeout=profile['timeout'], shell_metadata=True)
        matches = [(r,p) for r in current['sessions'] for p in r['attachments']
                   if p['pane_id'] == receipt['pane_id'] and p['window_id'] == receipt['window_id']]
        if not current['complete']:
            mark(path,receipt,'inventory_unavailable');return
        if len(matches) == 1:
            row, pane = matches[0]
            if row['thread_id'] == receipt['thread_id'] and canonical(row['cwd']) == value['cwd']:
                if row['runtime_state'] == 'idle' and not row.get('active_flags'):
                    receipt['state'] = 'completed'
                    value.update(session=dict(row, selected_attachment=pane), thread_id=row['thread_id'])
                    mark(path,receipt,'resolved',next_actions=['send']);return
                mark(path,receipt,'target_busy');return
            if row['thread_id'] or pane.get('client_pid'):
                mark(path,receipt,'target_changed');return
            # A shell may still be launching. Never launch a replacement.
            mark(path,receipt,'starting',next_actions=['retry_same_intent']);return
        mark(path,receipt,'target_changed');return
    if not original_unchanged(receipt,profile):
        mark(path,receipt,'target_changed');return
    policy = value['applied_policy']
    old = receipt['original_attachment']
    if policy == 'tab_only' and old:
        receipt['state']='completed'
        mark(path,receipt,'tab_ready',next_actions=['fresh','resume']);return
    try:
        if policy != 'tab_only' and receipt['thread_id'] is None:
            if not gate(path,receipt):return
            receipt.update(state='starting',uncertain_effect='thread/start')
            save(path,receipt)
            thread=native_request(profile['app_server'],profile['codex_path'],'thread/start',
                dict(cwd=value['cwd'],ephemeral=False),profile['timeout'])['thread']
            if not isinstance(thread.get('id'),str) or not thread['id']:
                raise WakeError('native thread identity unavailable')
            receipt.update(thread_id=thread['id'],state='prepared')
            receipt.pop('uncertain_effect',None)
            value.update(thread_id=thread['id'])
            value['effects'].append(dict(operation='thread/start',thread_id=thread['id']))
            save(path,receipt)
        if policy != 'tab_only':
            thread=native_request(profile['app_server'],profile['codex_path'],'thread/read',
                dict(threadId=receipt['thread_id'],includeTurns=False),profile['timeout'])['thread'] if policy == 'resume' else None
            if thread and (thread.get('id') != receipt['thread_id'] or canonical(thread['cwd']) != value['cwd']):
                mark(path,receipt,'target_changed');return
            if thread and (thread.get('status',{}).get('type') not in ('idle','notLoaded') or thread.get('status',{}).get('activeFlags')):
                mark(path,receipt,'target_busy');return
            if policy == 'resume':
                live=observe(endpoint=profile['app_server'],socket_path=profile.get('tmux_socket'),timeout=profile['timeout'], shell_metadata=True)
                if not live['complete']:
                    mark(path,receipt,'inventory_unavailable');return
                if any(r['thread_id']==receipt['thread_id'] and r['attachments'] for r in live['sessions']):
                    mark(path,receipt,'target_busy',message='saved thread already has a live attachment');return
            if not gate(path,receipt):return
            if policy == 'fresh':
                native_request(profile['app_server'],profile['codex_path'],'thread/name/set',
                    dict(threadId=receipt['thread_id'],name='Wake target '+receipt['fingerprint'][:12]),profile['timeout'])
            if not original_unchanged(receipt,profile):
                mark(path,receipt,'target_changed');return
            removed = ('CODEX_THREAD_ID','TMUX_PANE','CODEX_WAKE_A2A_CAPABILITY',
                       'CODEX_WAKE_A2A_BUS_ROOT','CODEX_WAKE_SENDER_RECEIPT_AUTHORITY')
            home=['CODEX_HOME='+profile['codex_home']] if profile.get('codex_home') else []
            command=shlex.join(['env',*[part for key in removed for part in ('-u',key)],*home,
                profile['codex_path'],'resume','--no-alt-screen','-C',value['cwd'],receipt['thread_id'],
                '--remote',profile['app_server']])
        else:
            command=None
        if not gate(path,receipt):return
        effect='split-window' if old else 'new-window'
        receipt.update(state='starting',uncertain_effect='tmux/'+effect)
        save(path,receipt)
        flags=['-d','-P','-F','#{window_id}\t#{pane_id}']
        if old:
            flags+=['-t',old['pane_id'],'-c',value['cwd']]
        else:
            # A missing descriptor supplies a display name, never tmux target syntax.
            import re
            name=value.get('normalized_selector') or receipt['intent']['selector']
            name=re.sub(r'^tab\s+', '', name)
            if name.startswith('tab:'):name=name[4:]
            parsed=re.fullmatch(r'(\d+)(?::(.+))?',name)
            index=''
            if parsed:
                index,name=parsed.groups()
                name=name or 'codex'
            receipt['created_name']=name
            save(path,receipt)
            flags+=['-t',profile['tmux_session']+':'+index,'-n',name,'-c',value['cwd']]
        if command:flags.append(command)
        window,pane=tmux_command(runtime,effect,*flags).split('\t')
        receipt.update(window_id=window,pane_id=pane,state='completed' if policy=='tab_only' else 'awaiting_preflight')
        receipt.pop('uncertain_effect',None)
        value['effects'].append(dict(operation='tmux/'+effect,window_id=window,pane_id=pane,
                                     preserved_pane_id=old['pane_id'] if old else None))
        value['thread_id']=receipt['thread_id']
        mark(path,receipt,'tab_created' if policy=='tab_only' else 'starting',next_actions=['retry_same_intent'])
    except Exception as exc:
        receipt['state']='uncertain' if receipt.get('uncertain_effect') else 'blocked'
        mark(path,receipt,'effect_uncertain' if receipt.get('uncertain_effect') else 'inventory_unavailable',
             reconciliation_required=bool(receipt.get('uncertain_effect')),
             uncertain_effect=receipt.get('uncertain_effect'),next_actions=['reconcile_same_intent'],
             message=type(exc).__name__)
