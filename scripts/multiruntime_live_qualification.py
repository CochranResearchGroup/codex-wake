#!/usr/bin/env python3
"""Opt-in isolated installed Codex/Grok TUI acceptance. No production grant changes.

Per run: one owner, one recipient per runtime, <=6 original synthetic prompts, <=300s.
A refusal or uncertain outcome stops the run; no replay, draft clearing or retry.
Run only with explicit current authority for this bounded live acceptance.
Each diagnostic rerun uses new sessions and intents; uncertain work is never replayed.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import re
import signal
import stat
import subprocess
import tempfile
import time
import tomllib
import uuid
import zipfile


def census():
    found={}
    for proc in Path('/proc').glob('[0-9]*'):
        try:
            if proc.stat().st_uid!=os.getuid():continue
            data=proc.joinpath('stat').read_text().rsplit(') ',1)[1].split()
            exe=proc.joinpath('exe').resolve(strict=True)
            if exe.name not in ('grok','codex') and 'tmux' not in exe.name:continue
            found[int(proc.name)]=dict(start_ticks=int(data[19]),exe=str(exe))
        except (OSError,ValueError,IndexError):pass
    return found


def prepare_tmux(tmux,workspace,codex_argv):
    """Retain startup errors even when a TUI exits immediately (zero providers)."""
    tmux('-f','/dev/null','new-session','-d','-s','mr06','-n','codex',
         '-x','180','-y','50','-c',workspace,'exec sleep 300')
    tmux('set-option','-g','remain-on-exit','on')
    tmux('respawn-pane','-k','-t','mr06:codex','-c',workspace,'exec '+shlex.join(codex_argv))
    return tmux('display-message','-p','-t','mr06:codex','#{pane_id}').strip()


def notification_outcome(receipt):
    rows=receipt['dispatch']['results']
    return (any(row.get('attempt_id') for row in rows),
            any(row.get('status')=='submitted' for row in rows),
            any(row.get('status')=='uncertain' for row in rows))


HELPER=r'''
import json,os,subprocess,sys,time
from pathlib import Path
root=Path(__file__).parent
cfg=json.loads((root/'actor-config.json').read_text())
role,step=sys.argv[1:]
result_file=root/(role+'-'+step+'.json')
if result_file.exists():
 print('Already attempted; do not retry.');sys.exit(42)
result_file.write_text(json.dumps({'status':'started','role':role,'step':step}))
result={'status':'failed','role':role,'step':step,'calls':[]}
def invoke(*args):
 cmd=[cfg['cli'],'messages',*args,'--bus-root',cfg['bus'],'--capability',cfg[role+'_cap'],'--json']
 if role=='grok':cmd+=['--actor-runtime','grok']
 else:cmd+=['--app-server',cfg['endpoint']]
 p=subprocess.run(cmd,capture_output=True,text=True,timeout=45)
 try:value=json.loads(p.stdout)
 except ValueError:value={'error':{'code':'unstructured_cli_response'}}
 result['calls'].append({'verb':args[0],'exit_code':p.returncode,'result':value})
 if p.returncode:raise RuntimeError('actor_cli_refused:'+str(value.get('error',{}).get('code')))
 return value
try:
 expected=cfg['grok_session'] if role=='grok' else cfg['codex_thread']
 actual=os.environ.get('GROK_SESSION_ID' if role=='grok' else 'CODEX_THREAD_ID')
 result['inherited_session_present']=actual is not None
 result['inherited_session_matches']=actual==expected
 if actual!=expected:raise RuntimeError('native_inherited_session_context_unavailable')
 if role=='grok' and step=='probe':
  ancestry=[];pid=os.getpid()
  for _ in range(16):
   try:
    proc=Path('/proc')/str(pid);s=(proc/'stat').read_text().rsplit(') ',1)[1].split()
    ancestry.append({'pid':pid,'parent':int(s[1]),'executable':str((proc/'exe').resolve()),'start_ticks':int(s[19])});pid=int(s[1])
    if pid<=1:break
   except OSError:break
  result['ancestry']=ancestry
  invoke('inbox')
 elif role=='codex' and step=='send':
  sent=invoke('send','--to','grok:'+cfg['binding_id'],'--runtime-root',cfg['wake'],
      '--body-file',str(root/'request.txt'),'--idempotency-key',cfg['nonce']+'-forward','--delivery','notify','--ttl','4m')
  result['message_id']=sent['message']['message_id']
 elif role=='grok' and step=='work':
  first=json.loads((root/'codex-send.json').read_text())['message_id']
  invoke('read',first)
  claim=invoke('ack',first,'--outcome','accepted')
  if claim.get('claimed') is not True:raise RuntimeError('not_a_new_work_claim')
  result['claimed']=claim['claimed']
  reply=invoke('reply',first,'--body-file',str(root/'result.txt'),
      '--idempotency-key',cfg['nonce']+'-forward-reply','--delivery','inbox','--outcome','completed','--evidence',str(root/'result.txt'))
  reverse=invoke('send','--to','thread:'+cfg['codex_thread'],'--app-server',cfg['endpoint'],
      '--body-file',str(root/'request.txt'),'--idempotency-key',cfg['nonce']+'-reverse','--delivery','inbox','--ttl','3m')
  result.update(message_id=reverse['message']['message_id'],forward_reply=reply['message']['message_id'])
  (root/'reverse-message.json').write_text(json.dumps({'message_id':result['message_id']}))
  (root/'reverse.ready').touch()
  waited=invoke('wait',result['message_id'],'--for','reply','--timeout','45s','--interval','1')
  result['reverse_replies']=[r['message_id'] for r in waited['replies']]
 elif role=='codex' and step=='receive':
  first=json.loads((root/'reverse-message.json').read_text())['message_id']
  invoke('read',first)
  claim=invoke('ack',first,'--outcome','accepted')
  if claim.get('claimed') is not True:raise RuntimeError('not_a_new_work_claim')
  result['claimed']=claim['claimed']
  reply=invoke('reply',first,'--body-file',str(root/'result.txt'),
      '--idempotency-key',cfg['nonce']+'-reverse-reply','--delivery','inbox','--outcome','completed','--evidence',str(root/'result.txt'))
  result.update(message_id=first,reply_id=reply['message']['message_id'])
 else:raise RuntimeError('unknown_step')
 result['status']='passed'
except Exception as exc:result['reason']=str(exc)
result_file.write_text(json.dumps(result,indent=2))
print(json.dumps({k:v for k,v in result.items() if k not in ('calls','ancestry')}))
'''


def qualify(args):
    prefix=Path(args.prefix).resolve();cli=prefix/'bin/codex-wake';daemon=prefix/'bin/codex-waked'
    import codex_wake
    if not Path(codex_wake.__file__).resolve().is_relative_to(prefix):raise RuntimeError('non_editable_candidate_required')
    wheel=Path(args.wheel).resolve()
    if hashlib.sha256(wheel.read_bytes()).hexdigest()!=args.wheel_sha256:
        raise RuntimeError('qualified_wheel_digest_mismatch')
    module_hashes={}
    with zipfile.ZipFile(wheel) as archive:
        for module in sorted(Path(codex_wake.__file__).parent.glob('*.py')):
            data=module.read_bytes()
            if data!=archive.read('codex_wake/'+module.name):
                raise RuntimeError('installed_module_differs_from_qualified_wheel')
            module_hashes[module.name]=hashlib.sha256(data).hexdigest()
    work=Path(tempfile.mkdtemp(prefix='cw-mr06-'));work.chmod(0o700)
    workspace=work/'workspace';workspace.mkdir(mode=0o700)
    wake=work/'wake';bus=work/'bus';bindings=work/'bindings.json'
    socket=work/'tmux.sock';leader=work/'leader.sock';alias=work/'codex.sock'
    nonce=uuid.uuid4().hex;session=str(uuid.uuid4());before=census();native=None;thread=None
    result=dict(verdict='INCOMPLETE',work=str(work),grok_session=session,prompt_limit=6,wall_limit_seconds=args.wall_budget_seconds,
                prompts_submitted=0,phases=[],runtime_versions={},source_commit=args.source_commit)
    def save(name,value):
        (work/name).write_text(value if isinstance(value,str) else json.dumps(value,indent=2))
    save('processes-before.json',before)
    save('launcher-source.py',Path(__file__).read_text())
    save('installed-module-hashes.json',module_hashes)
    result.update(wheel_sha256=args.wheel_sha256,installed_module_count=len(module_hashes),
        launcher_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    # Prepare local synthetic files before starting either runtime.
    (workspace/'actor_step.py').write_text(HELPER)
    (workspace/'request.txt').write_text('Synthetic bounded work: produce the fixed fixture result, then stop. No other task or permission is granted.')
    (workspace/'result.txt').write_text('CW_MR06_SYNTHETIC_RESULT_'+nonce)
    started=time.monotonic();deadline=started+args.wall_budget_seconds-30
    def run(argv,**kw):
        p=subprocess.run([str(x) for x in argv],capture_output=True,text=True,
                         timeout=min(20,max(1,deadline-time.monotonic())),**kw)
        if p.returncode:raise RuntimeError('command_refused:'+str(argv[0])+':'+p.stderr[:200])
        return p.stdout
    def tmux(*argv):return run(['tmux','-S',socket,*argv])
    def frame(pane):return tmux('capture-pane','-p','-J','-S','-2000','-t',pane)
    endpoint=None
    try:
        result['runtime_versions']={'codex':run([args.codex,'--version']).strip(),'grok':run([args.grok,'--version']).strip(),
                                    'wake':run([cli,'--version']).strip()}
        if result['runtime_versions']['grok']!='grok 1.0.40 (eb1a2256660d) [stable]':raise RuntimeError('unqualified_grok_version')
        # Private app-server; reuse the user's normal auth coordination without
        # copying tokens or touching any existing thread. Disable configured MCPs.
        env=dict(os.environ);env.pop('CODEX_THREAD_ID',None);env.pop('PYTHONPATH',None)
        config_path=Path(os.environ.get('CODEX_HOME',str(Path.home()/'.codex')))/'config.toml'
        config=tomllib.loads(config_path.read_text()) if config_path.exists() else {}
        overrides=[]
        for name in config.get('mcp_servers',{}):
            if not all(c.isalnum() or c in '_-' for c in name):raise RuntimeError('unsupported_mcp_config_key')
            overrides+=['-c','mcp_servers.'+name+'.enabled=false']
        overrides+=['-c','approval_policy="never"','-c','sandbox_mode="danger-full-access"']
        overrides+=['-c','projects.'+json.dumps(str(workspace))+'.trust_level="trusted"']
        log=(work/'codex-native.log').open('w')
        native=subprocess.Popen([args.codex,'app-server',*overrides,'--listen','unix://'+str(alias)],
                                env=env,cwd=workspace,stdout=log,stderr=log,start_new_session=True)
        result['native_pid']=native.pid
        until=min(deadline-80,time.monotonic()+25)
        while not alias.exists():
            if native.poll() is not None or time.monotonic()>until:raise RuntimeError('private_native_startup_unavailable')
            time.sleep(.1)
        endpoint='unix://'+str(alias.resolve(strict=True))
        from codex_wake.native_protocol import native_request
        def rpc(method,params):return native_request(endpoint,args.codex,method,params,4)
        # Remote resume rejects permission overrides; a new empty RPC thread has
        # no persisted rollout to resume. Let the real TUI create its thread.
        codex_argv=[args.codex,'--remote',endpoint,'--no-alt-screen']
        codex_pane=prepare_tmux(tmux,workspace,codex_argv)
        until=min(deadline-80,time.monotonic()+20)
        while time.monotonic()<until:
            loaded=rpc('thread/loaded/list',{})['data']
            if len(loaded)==1 and 'Ask Codex to do anything' in frame(codex_pane):
                thread=loaded[0];break
            if tmux('display-message','-p','-t',codex_pane,'#{pane_dead}').strip()=='1':
                save('codex-before.txt',frame(codex_pane))
                raise RuntimeError('codex_tui_exited_before_admission')
            time.sleep(.1)
        else:raise RuntimeError('unique_owned_codex_tui_thread_not_ready')
        result['codex_thread']=thread
        rules=('Disposable synthetic acceptance. Never spawn agents, search, edit files or run other commands. '
               'On the first wake run exactly '+str(prefix/'bin/python')+' '+str(workspace/'actor_step.py')+' grok probe. '
               'On a mailbox notification run exactly '+str(prefix/'bin/python')+' '+str(workspace/'actor_step.py')+' grok work. '
               'A refused/failed command means stop, never repair/retry/bypass. Then answer CW_MR06_DONE only.')
        grok_argv=['env','GROK_DISABLE_AUTOUPDATER=1','GROK_CONFIG='+json.dumps({'cli':{'use_leader':True,'auto_update':False}}),
                   args.grok,'--leader-socket',str(leader),'--cwd',str(workspace),'--session-id',session,
                   '--tools','Bash','--allow','Bash('+str(prefix/'bin/python')+' '+str(workspace/'actor_step.py')+' grok probe)',
                   '--allow','Bash('+str(prefix/'bin/python')+' '+str(workspace/'actor_step.py')+' grok work)',
                   '--permission-mode','dontAsk','--no-subagents','--disable-web-search','--max-turns','4','--no-alt-screen','--rules',rules]
        tmux('new-window','-d','-t','mr06','-n','grok','-c',workspace,'exec '+shlex.join(grok_argv))
        grok_pane=tmux('display-message','-p','-t','mr06:grok','#{pane_id}').strip()
        grok_pid=int(tmux('display-message','-p','-t',grok_pane,'#{pane_pid}').strip());result['grok_pid']=grok_pid
        result['phases'].append('two_owned_tuis_started')
        stable=None;until=min(deadline-90,time.monotonic()+160)
        while time.monotonic()<until:
            f=tmux('capture-pane','-p','-J','-t',grok_pane);lines=[x.rstrip() for x in f.splitlines() if x.strip()]
            idle=len(lines)>2 and lines[-2]=='❯' and 'ctrl+o transcript' in lines[-1] and 'Starting session' not in f
            if idle:
                if stable is None:stable=time.monotonic()
                if time.monotonic()-stable>2:break
            else:stable=None
            time.sleep(.2)
        else:raise RuntimeError('grok_startup_identity_not_ready')
        tmux('send-keys','-l','-t',grok_pane,'/session-info');time.sleep(.15)
        if '❯ /session-info' not in frame(grok_pane):raise RuntimeError('local_identity_control_not_visible')
        tmux('send-keys','-t',grok_pane,'Enter')
        until=min(deadline-75,time.monotonic()+10)
        while time.monotonic()<until:
            if 'Session ID: '+session in frame(grok_pane):break
            time.sleep(.2)
        else:raise RuntimeError('active_grok_session_not_established')
        save('grok-before.txt',frame(grok_pane));save('codex-before.txt',frame(codex_pane))
        if tmux('display-message','-p','-t',codex_pane,'#{pane_dead}').strip()=='1':
            raise RuntimeError('codex_tui_exited_before_admission; retained codex-before.txt')
        binding=json.loads(run([cli,'--wake-root',wake,'grok','bind','--socket',socket,'--pane',grok_pane,
            '--pid',grok_pid,'--session-id',session,'--executable',args.grok,'--allow-terminal-input','--allow-terminal-fallback','--json']))
        result['binding_id']=binding['binding_id'];save('grok-binding-receipt.json',binding)
        def operator(*parts):return json.loads(run([cli,'a2a',*parts,'--bus-root',bus,'--json'],cwd=workspace))
        configured=operator('configure');op=configured['operator_capability_file']
        save('network-time-policy.json',operator('network-time','--accept-unauthenticated-ntp','--operator-capability',op))
        result['mailbox_time_policy']='network-first-v1; plain NTP explicitly opted in for isolated test bus'
        codex_actor=operator('enroll',workspace,'--thread','thread:'+thread,'--app-server',endpoint,'--tmux-socket',socket,'--operator-capability',op,'--notify')
        grok_actor=operator('enroll',workspace,'--thread','grok:'+binding['binding_id'],'--runtime-root',wake,'--operator-capability',op,'--notify')
        operator('bind-grok','--runtime-root',wake,'--binding-id',binding['binding_id'],'--bindings-file',bindings,'--operator-capability',op)
        operator('resume','--operator-capability',op)
        cfg=dict(cli=str(cli),wake=str(wake),bus=str(bus),endpoint=endpoint,nonce=nonce,binding_id=binding['binding_id'],
                 codex_thread=thread,grok_session=session,codex_cap=codex_actor['actor_capability_file'],grok_cap=grok_actor['actor_capability_file'])
        (workspace/'actor-config.json').write_text(json.dumps(cfg));(workspace/'actor-config.json').chmod(0o600)
        def arm(runtime,key,trigger,prompt):
            argv=[cli,'--wake-root',wake,runtime,'file','--json','--ttl','3m','--idempotency-key',nonce+'-'+key]
            if runtime=='native':argv+=['--endpoint',endpoint,'--codex-path',args.codex,thread]
            else:argv+=[binding['binding_id']]
            value=json.loads(run([*argv,trigger,'--',prompt],cwd=workspace));save('arm-'+key+'.json',value);return value
        helper=str(prefix/'bin/python')+' '+str(workspace/'actor_step.py')
        first=arm('native','codex-initial',workspace/'begin.ready',
                  'Synthetic acceptance. Run only '+helper+' codex send. Do not use any other tools/commands or edit files. Stop on refusal; never retry. Then reply CW_MR06_DONE.')
        probe=arm('grok','grok-probe',workspace/'begin.ready',
                  'Synthetic acceptance wake: run the exact grok probe helper in your extra rules once. Stop on any refusal, do not retry. Then reply CW_MR06_DONE.')
        reverse=arm('native','codex-reverse',workspace/'reverse.ready',
                  'Synthetic acceptance. Run only '+helper+' codex receive. Require claimed=true before returning the fixture result. No other tools/commands, edits or retry. Then reply CW_MR06_DONE.')
        (workspace/'begin.ready').touch();result['phases'].append('installed_durable_intents_registered')
        notification_attempted=False;notification_submitted=False;dispatch_count=0
        while time.monotonic()<deadline:
            save('daemon-last.txt',run([daemon,'--once','--wake-root',wake],cwd=workspace))
            from codex_wake.records import all_records
            records=[item.record for item in all_records(wake)]
            durable_attempts=sum(r.get('attempts',0) for r in records)
            if any(r.get('attempts',0)>1 for r in records):raise RuntimeError('original_intent_attempt_budget_exceeded')
            result['prompts_submitted']=durable_attempts+(1 if notification_attempted else 0)
            if result['prompts_submitted']>6:raise RuntimeError('synthetic_prompt_budget_exceeded')
            steps={}
            for name in ('codex-send','grok-probe','grok-work','codex-receive'):
                file=workspace/(name+'.json')
                if file.exists():
                    value=json.loads(file.read_text());steps[name]=value
                    if value['status']=='failed':raise RuntimeError(name+':'+value.get('reason','failed'))
            result['actor_steps']={k:v['status'] for k,v in steps.items()}
            if steps.get('codex-send',{}).get('status')=='passed' and steps.get('grok-probe',{}).get('status')=='passed' and not notification_attempted:
                # Wait for the real empty composer; never paste over the probe turn.
                from codex_wake.grok_runtime import GrokRuntimeAdapter
                from codex_wake.grok_terminal import GrokTerminalHost
                adapter=GrokRuntimeAdapter(GrokTerminalHost(wake));recipient=adapter.resolve(dict(transport='runtime',version=1,runtime='grok',
                    method='terminal_observation',session_id=session,binding_id=binding['binding_id'],binding_sha256=binding['binding_sha256']))
                if adapter.observe(recipient).state=='ready':
                    notification=operator('dispatch','--bindings-file',bindings,'--operator-capability',op)
                    dispatch_count+=1;save('notification-dispatch-'+str(dispatch_count)+'.json',notification)
                    notification_attempted,notification_submitted,uncertain=notification_outcome(notification)
                    if uncertain:raise RuntimeError('notification_uncertain_no_replay')
            if (len(steps)==4 and all(v['status']=='passed' for v in steps.values())
                    and len(records)==3 and all(r.get('status')=='submitted' for r in records)
                    and notification_submitted):
                visible={label:len(re.findall(r'(?m)^\s*[•●]?\s*CW_MR06_DONE\s*$',frame(pane)))
                         for label,pane in [('codex',codex_pane),('grok',grok_pane)]}
                if all(count>=2 for count in visible.values()):
                    result.update(verdict='PASS',visible_synthetic_responses=visible)
                    result['phases'].append('both_directions_credentialed_claim_and_correlated_reply');break
            if any(r.get('status')=='failed' for r in records):raise RuntimeError('durable_wake_failed')
            time.sleep(.3)
        else:raise RuntimeError('bounded_live_deadline_reached')
        save('final-records.json',records)
    except Exception as exc:
        result.update(verdict='FAIL',reason=str(exc))
    finally:
        # Count persisted attempts even if a CLI response was lost. This is a
        # conservative possible-input count, never proof that no bytes were sent.
        try:
            from codex_wake.records import all_records
            final_records=[item.record for item in all_records(wake)] if wake.exists() else []
            save('final-records.json',final_records)
            possible=sum(r.get('attempts',0) for r in final_records)
            if (bus/'mailbox.sqlite').exists():
                import sqlite3
                with sqlite3.connect((bus/'mailbox.sqlite').as_uri()+'?mode=ro',uri=True) as db:
                    possible+=db.execute('SELECT count(*) FROM mail_attempts').fetchone()[0]
            result['possible_prompt_attempts']=possible
            result['prompts_submitted']=max(result['prompts_submitted'],possible)
            if possible>6:result.update(verdict='FAIL',prompt_budget_exceeded=True)
        except Exception:
            result.update(possible_prompt_attempts=None,verdict='FAIL',attempt_count_unavailable=True)
        for label in ('grok','codex'):
            pane=locals().get(label+'_pane')
            if pane:
                try:save(label+'-final.txt',frame(pane))
                except Exception:pass
        if endpoint and thread:
            try:
                from codex_wake.native_protocol import native_request
                data=native_request(endpoint,args.codex,'thread/read',dict(threadId=thread,includeTurns=True),3)['thread']
                save('codex-owned-thread.json',data)
                for turn in data.get('turns',[]):
                    if turn.get('status')=='inProgress':
                        native_request(endpoint,args.codex,'turn/interrupt',dict(threadId=thread,turnId=turn['id']),3)
            except Exception:pass
        try:subprocess.run(['tmux','-S',str(socket),'kill-server'],capture_output=True,timeout=3)
        except Exception:pass
        if native is not None:
            try:
                os.killpg(native.pid,signal.SIGTERM);native.wait(timeout=4)
            except (OSError,subprocess.TimeoutExpired):
                try:os.killpg(native.pid,signal.SIGKILL)
                except OSError:pass
        # Retire only introduced Grok generations naming this exact private peer.
        for proc in Path('/proc').glob('[0-9]*'):
            try:
                pid=int(proc.name)
                if pid in before:continue
                argv=proc.joinpath('cmdline').read_bytes().decode(errors='replace').split('\0')
                if str(leader) in argv and proc.joinpath('exe').resolve(strict=True).name=='grok':os.kill(pid,signal.SIGTERM)
            except (OSError,ValueError):pass
        # Owned leaders may retire asynchronously after their client exits.
        # Bounded fresh readbacks replace an arbitrary fixed cleanup delay.
        cleanup_deadline=time.monotonic()+5
        while True:
            after=census()
            owned_remaining=[]
            newly_observed=[pid for pid in after if pid not in before]
            for pid in after:
                if pid in before:continue
                try:
                    argv=(Path('/proc')/str(pid)/'cmdline').read_bytes().decode(errors='replace')
                    if str(work) in argv:owned_remaining.append(pid)
                except OSError:pass
            if not newly_observed or time.monotonic()>=cleanup_deadline:break
            time.sleep(.1)
        save('processes-after.json',after)
        introduced=owned_remaining
        changed=[pid for pid,value in before.items() if after.get(pid)!=value]
        result.update(elapsed_seconds=round(time.monotonic()-started,3),cleanup=dict(
            introduced_remaining=introduced,unattributed_new_processes=[p for p in newly_observed if p not in introduced],
            preexisting_changed=changed))
        if newly_observed:result.update(verdict='FAIL',cleanup_incomplete=True)
        result['cleanup']['preexisting_changes_attribution']='unattributed; no pre-existing PID was targeted'
        if result['elapsed_seconds']>args.wall_budget_seconds:result.update(verdict='FAIL',budget_exceeded=True)
        save('result.json',result);print(json.dumps(result),flush=True)
    return 0 if result['verdict']=='PASS' else 1


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-live',action='store_true',required=True)
    parser.add_argument('--prefix',required=True)
    parser.add_argument('--wheel',required=True)
    parser.add_argument('--wheel-sha256',required=True)
    parser.add_argument('--codex',required=True)
    parser.add_argument('--grok',required=True)
    parser.add_argument('--source-commit',required=True)
    parser.add_argument('--wall-budget-seconds',type=int,default=300,choices=range(45,301),metavar='45..300')
    return qualify(parser.parse_args())

if __name__=='__main__':raise SystemExit(main())
