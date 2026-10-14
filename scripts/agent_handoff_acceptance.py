"""Opt-in isolated installed handoff/preflight/goal probe; never shared services."""
from __future__ import annotations
import argparse
from datetime import UTC,datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time
import tomllib

from codex_wake.lifecycle_configuration import effective_configuration
from codex_wake.lifecycle_review import instruction_read
from codex_wake.native_clock import snapshot
from codex_wake.native_protocol import native_request


class SetupQualified(Exception):
    """Exit the qualification-only path through common owned cleanup."""


class CorrectionStopped(Exception):
    """Qualified rejected work reached the original two-cycle boundary."""
from agent_handoff_writer_acceptance import write


def wait_for_preflight(invoke, intent, deadline, observe):
    """Observe one existing intent; clock uncertainty never authorizes replacement."""
    while True:
        code, state = invoke(intent)
        observe(state)
        if state['state'] == 'awaiting_activation':
            return state
        clock_hold = (state['state'] == 'blocked'
                      and state.get('reason') == 'admissible_time_unavailable')
        if ((state['state'] in ('blocked', 'expired') and not clock_hold)
                or time.monotonic() > deadline
                or (state['state'] == 'uncertain' and not (
                    state.get('successor_thread_id')
                    and state.get('successor', {}).get('submission_id')))):
            raise RuntimeError('handoff held: ' + state.get('reason', state['state']))
        time.sleep(.5)


def observe_native_preflight(request, source, target, guide, cwd):
    """Host-side reads; the sandbox never gains access to the daemon socket."""
    source_goal=request('thread/goal/get',dict(threadId=source))['goal']
    if not source_goal or source_goal['threadId']!=source or source_goal['status']!='paused':
        raise RuntimeError('source goal is not the paused preflight owner')
    skills=request('skills/list',dict(cwds=[str(cwd)],forceReload=True))
    if not any(s['path']==str(guide) and s.get('enabled') is True
               for d in skills['data'] for s in d['skills']):
        raise RuntimeError('actual native skill catalog did not load selected guide')
    resource=request('mcpServer/tool/call',dict(threadId=target,server='codex-wake',
        tool='wake_sessions_show',arguments={'selector':'thread:'+source}))
    if resource.get('isError',False):raise RuntimeError('native resource tool failed')
    observed=json.loads(resource['content'][0]['text'])
    if observed['session']['thread_id']!=source or observed['complete'] is not True:
        raise RuntimeError('native resource source identity/readiness mismatch')
    return dict(state='passed',source_thread_id=source,successor_thread_id=target,
        guide=str(guide),source_goal=source_goal,
        native_resource=dict(state='passed',tool='wake_sessions_show',source_thread_id=source,
            content_sha256=hashlib.sha256(json.dumps(resource,sort_keys=True).encode()).hexdigest()))


def call_source_mcp(request,source,saved_goal,tool,arguments):
    """Load the original paused caller without assigning work or changing its goal."""
    before=request('thread/goal/get',dict(threadId=source))['goal']
    identity=('threadId','objective','tokenBudget','createdAt')
    if (not before or before.get('status')!='paused' or before.get('threadId')!=source
            or any(before.get(k)!=saved_goal.get(k) for k in identity)):
        raise RuntimeError('source MCP caller goal authority changed')
    native=request('thread/resume',dict(threadId=source))['thread']
    if native.get('id')!=source or any(t.get('status')=='inProgress' for t in native['turns']):
        raise RuntimeError('source MCP caller is not the idle original context')
    after=request('thread/goal/get',dict(threadId=source))['goal']
    if after!=before:
        raise RuntimeError('source MCP caller resume changed its paused goal')
    return request('mcpServer/tool/call',dict(threadId=source,server='codex-wake',tool=tool,arguments=arguments))


def qualify_lifecycle_mcp(request,thread,profile,expiry):
    def call(tool,arguments):
        return request('mcpServer/tool/call',dict(threadId=thread,server='codex-wake',tool=tool,arguments=arguments))
    result=call('wake_sessions_configuration',dict(thread_id=thread,profile=profile,caller_thread_id=thread))
    if result.get('isError'):raise RuntimeError('native configuration readback rejected')
    configuration=json.loads(result['content'][0]['text'])
    if configuration['source_thread_id']!=thread:raise RuntimeError('native configuration identity changed')
    held=call('wake_sessions_handoff',dict(thread_id=thread,profile=profile,caller_thread_id=thread,
        intent='qualification-missing-checkpoint',checkpoint='missing-checkpoint.json',checkpoint_sha256='a'*64,
        expires_at=expiry,mode='new-tab'))
    error=json.loads(held['content'][0]['text'])
    if held.get('isError') is not True or not error.get('error',{}).get('code'):
        raise RuntimeError('native negative handoff case did not return a structured error')
    # A transport error alone proves no effect boundary. The caller must also
    # inspect native turns/goals and the private lifecycle journal.
    return dict(configuration_revision=configuration['revision'],handoff_negative_case_rejected=True,
                negative_error=error)


def settle_owned_successor(request, handoff):
    target=handoff['successor_thread_id']
    goal=request('thread/goal/get',dict(threadId=target))['goal']
    saved=handoff.get('successor_goal')
    owned_goal=bool(goal and saved and all(goal.get(k)==saved.get(k)
        for k in ('threadId','objective','tokenBudget','createdAt')))
    if goal and not owned_goal:raise RuntimeError('cleanup successor goal authority changed')
    if owned_goal and goal['status']=='active':
        goal=request('thread/goal/set',dict(threadId=target,status='paused',origin='automatic'))['goal']
        if goal['status']!='paused':raise RuntimeError('cleanup pause not observed')
    native=request('thread/read',dict(threadId=target,includeTurns=True))['thread']
    if native.get('id')!=target:raise RuntimeError('cleanup successor identity changed')
    running=[t for t in native['turns'] if t.get('status')=='inProgress']
    if len(running)>1:raise RuntimeError('cleanup active turn ambiguous')
    for turn in running:
        if not owned_goal and not any(i.get('type')=='userMessage' and
            i.get('clientId')==handoff['successor']['submission_id'] for i in turn['items']):
            raise RuntimeError('cleanup turn not owned')
        request('turn/interrupt',dict(threadId=target,turnId=turn['id']))
    final=request('thread/read',dict(threadId=target,includeTurns=True))['thread']
    if any(t.get('status')=='inProgress' for t in final['turns']):raise RuntimeError('cleanup turn not settled')
    return dict(thread_id=target,goal=goal,interrupted_turn_ids=[t['id'] for t in running],settled=True)


def preflight_program(constants):
    program='C='+repr(constants)+'\n'+'''import os,sys,json,pathlib,hashlib,subprocess,time
from codex_wake.lifecycle_review import validate_work_review
cid=os.environ['CODEX_THREAD_ID']
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def host_read(key):
    deadline=time.monotonic()+10
    while not pathlib.Path(C[key]).is_file():
        assert time.monotonic()<deadline,'host native observation unavailable'
        time.sleep(.1)
    return json.loads(pathlib.Path(C[key]).read_text())
if sys.argv[1:1+1] in (['--instructions'],['--correction-instructions']):
    correction_read=sys.argv[1]=='--correction-instructions'
    for kind in ('reviewer','workflow'):
        print('SELECTED_INSTRUCTIONS:'+kind+':'+sha(C[kind]))
        print(pathlib.Path(C[kind]).read_text())
    for p in (C['repo']+'/docs/dev/plans/0156-2026-10-12-agent-lifecycle-delivery.md',
              C['repo']+'/docs/dev/plans/0159-2026-10-12-agent-handoff.md','checkpoint.json','host-validation.json'):
        print('PREFLIGHT_SOURCE:'+p+':'+sha(p))
        content=pathlib.Path(p).read_text()
        if correction_read:
            assert sha(p)==C['original_source_hashes'][p],'previously read canonical evidence changed'
            continue
        if p.endswith('0156-2026-10-12-agent-lifecycle-delivery.md'):
            start=content.index('## Operator requirements revision')
            end=content.index('\\n## Problem Statement',start)
            print(content[:content.index('## Current State')])
            print(content[start:end])
            print('Canonical operator revision shown in full; wider plan remains OPEN. Other sections are retained in the hashed source.')
        elif p.endswith('0159-2026-10-12-agent-handoff.md'):
            print(content[content.index('## Scope'):])
        else:print(content)
    own=pathlib.Path(__file__).resolve()
    print('APPROVED_HELPER_SOURCE:'+str(own)+':'+sha(own))
    if not correction_read:print(own.read_text())
    if C.get('correction'):
        print('REPAIR_EVIDENCE:'+sha('repair.txt'))
        print(pathlib.Path('repair.txt').read_text())
    raise SystemExit(0)
if sys.argv[1:]==['--continue']:
    proof=json.loads(pathlib.Path('preflight.json').read_text())
    assert proof['successor_thread_id']==cid and proof['state']=='passed'
    assert not pathlib.Path('continued.json').exists(),'continuation already executed'
    p=subprocess.run([C['prefix']+'/bin/codex-wake','--version'],capture_output=True,text=True,check=True)
    goal=host_read('continuation_authority')['goal']
    checkpoint=json.loads(pathlib.Path('checkpoint.json').read_text())
    assert goal['threadId']==cid and goal['objective']==checkpoint['objective'] and goal['status']=='active'
    pathlib.Path('continued.json').write_text(json.dumps(dict(state='passed',thread_id=cid,checkpoint_sha256=proof['checkpoint_sha256'],version=p.stdout.strip())))
    print(pathlib.Path('continued.json').read_text())
    print('CONTINUATION_CHECK:'+cid+':'+proof['checkpoint_sha256'])
    raise SystemExit(0)
source,nonce,digest=sys.argv[1:]
assert sha('checkpoint.json')==digest
body=json.loads(pathlib.Path('checkpoint.json').read_text());assert body['source_thread_id']==source
assert subprocess.check_output(['git','-C',C['repo'],'rev-parse','HEAD'],text=True).strip()==C['head']
assert not subprocess.check_output(['git','-C',C['repo'],'status','--porcelain'],text=True).strip()
checks={}
for name in ('canonical_sources','selected_skill','selected_workflow'):
    paths=([C['repo']+'/docs/dev/plans/0156-2026-10-12-agent-lifecycle-delivery.md',C['repo']+'/docs/dev/plans/0159-2026-10-12-agent-handoff.md'] if name=='canonical_sources' else [C['guide']] if name=='selected_skill' else [C['workflow']])
    checks[name]=dict(state='passed',sources=[dict(path=p,sha256=sha(p)) for p in paths])
observed=host_read('native_observations')
assert observed['state']=='passed' and observed['source_thread_id']==source and observed['successor_thread_id']==cid
assert observed['checkpoint_sha256']==digest and observed['intent_fingerprint']==nonce and observed['guide']==C['guide']
checks['native_resource']=observed['native_resource']
version=subprocess.check_output([C['prefix']+'/bin/codex-wake','--version'],text=True).strip()
checks['installed_cli']=dict(state='passed',version=version)
ref=observed['host_validation']['verified_ref']
assert ref==C['head']
checks['focused_validation']=observed['host_validation']['focused_validation']
assert checks['focused_validation']['state']=='passed' and checks['focused_validation']['exit_code']==0
validation=checks['focused_validation']['command']
# The reviewer, not this verifier, authors the semantic verdict and packet.
review_path=pathlib.Path('work-review.json')
review=json.loads(review_path.read_text())
authority=host_read('review_authority')
assert review['configuration_revision']==authority['configuration_revision']
assert review['source_thread_id']==source and review['successor_thread_id']==cid
assert review['checkpoint_sha256']==digest and review['intent_fingerprint']==nonce
assert review['work_review']['verdict'] in ('accept','correct','blocked')
assert review['work_review']['selected_review']=='github-handoff'
if review['work_review']['verdict']=='accept':
    assert validate_work_review(review['work_review'],authority['policy'],pathlib.Path.cwd(),body)
    if C.get('correction'):assert pathlib.Path('repair.txt').read_text()=='accepted correction\\n'
elif C.get('correction') and review['work_review']['verdict']=='correct':
    packet=review['work_review']['correction_packet']
    assert packet['criterion']=='repair fixture matches accepted correction' and packet['paths']==['repair.txt']
    assert packet['evidence']==[dict(path='repair.txt',sha256=sha('repair.txt'))]
    assert packet['instructions']==C['repair_instructions']
    assert pathlib.Path('repair.txt').read_text()!='accepted correction\\n'
else:assert validate_work_review(review['work_review'],authority['policy'],pathlib.Path.cwd(),body)
packet=pathlib.Path('successor-handoff.md').read_text()
assert packet.strip(),'reviewer handoff packet missing'
checks['selected_workflow'].update(packet='successor-handoff.md',packet_sha256=sha('successor-handoff.md'),verified_ref=ref,
    review_artifact='work-review.json',review_artifact_sha256=sha(review_path))
pathlib.Path('preflight.json').write_text(json.dumps(dict(version=1,state='passed',source_thread_id=source,successor_thread_id=cid,checkpoint_sha256=digest,intent_fingerprint=nonce,selected_workflow='github-ask-matt',configuration_revision=authority['configuration_revision'],runtime_readiness=dict(state='passed',checks=checks),work_review=review['work_review'],checks=checks)))
# The host reads the authored artifacts and verifies their hashes. Avoid replaying
# those complete artifacts into the next model context after semantic verification.
print('preflight:'+cid+':'+nonce+':'+digest)
'''
    compile(program, '<generated preflight>', 'exec')
    return program


def excluded_skill_paths(catalog, selected_paths):
    selected=set(map(str,selected_paths))
    enabled={entry['path'] for group in catalog['data'] for entry in group['skills']
             if entry.get('enabled') is True}
    if not selected <= enabled:
        raise RuntimeError('actual native skill catalog did not load exact selected instructions')
    return sorted(enabled-selected)


def checkpoint_program(contract,objective):
    program=f"""import os,json,hashlib,pathlib
p=pathlib.Path('checkpoint.json')
p.write_text(json.dumps(dict(**{contract!r},source_thread_id=os.environ['CODEX_THREAD_ID'],objective={objective!r},authority='operator execute Plan0156; fixed bounded disposable continuation',next_packet='Read selected skill instructions and run host preflight before authorized bounded continuation',pending_obligations=[]),sort_keys=True)+{chr(10)!r})
print('checkpoint:'+os.environ['CODEX_THREAD_ID']+':'+hashlib.sha256(p.read_bytes()).hexdigest())
"""
    compile(program,'<generated checkpoint>','exec')
    return program


def start_owned_monitor(prefix,root,env,log):
    """Qualify the same resident supervision used before source model admission."""
    from codex_wake.process import process_identity
    process=subprocess.Popen([str(prefix/'bin/codex-waked'),'--wake-root',str(root/'wake'),
        '--no-dispatch','--interval','1'],env=env,stdout=log,stderr=log,start_new_session=True)
    deadline=time.monotonic()+15
    try:
        while process.poll() is None and time.monotonic()<deadline:
            proof=root/'wake/lifecycle/supervision.json'
            if proof.exists():
                observed=json.loads(proof.read_text())
                if (observed.get('active') and observed.get('pid')==process.pid
                        and observed.get('identity')==process_identity(process.pid)
                        and type(observed.get('observed_at')) in (int,float)):
                    return process,observed
            time.sleep(.1)
        raise RuntimeError('source supervisor not ready')
    except Exception:
        if process.poll() is None:
            os.killpg(process.pid,signal.SIGINT);process.wait(timeout=30)
        raise


def execute(root,prefix,repo,parent_deadline,resume_setup=False,mode='new-tab',rollback=False,qualify_only=False,correction=None):
    original=None
    if resume_setup:
        original=json.loads((root/'state.json').read_text())
        if (original.get('state')!='failed' or original.get('source') or original.get('handoff')
                or 'launch profile requires an existing owned Unix socket' not in original.get('error','')
                or list((root/'wake/lifecycle').glob('*.json')) or list((root/'codex-home/sessions').rglob('*.jsonl'))
                or original.get('cleanup',{}).get('private_readable_environment_matches')!=[]):
            raise RuntimeError('setup resume requires proved pre-creation rejection and clean owned runtime')
        write(root/'setup-failure-01.json',original)
    root.mkdir(mode=0o700,parents=True,exist_ok=resume_setup)
    workspace=root/'workspace';workspace.mkdir(exist_ok=resume_setup);home=root/'codex-home';home.mkdir(mode=0o700,exist_ok=resume_setup)
    codex=Path(subprocess.check_output(['which','codex'],text=True).strip()).resolve()
    config=tomllib.loads((Path.home()/'.codex/config.toml').read_text())
    selected={k:config[k] for k in ('model','model_reasoning_effort','model_provider') if k in config}
    lines=[f'{k} = {json.dumps(v)}' for k,v in selected.items()]
    lines+=['approval_policy = "never"','sandbox_mode = "workspace-write"',f'[projects.{json.dumps(str(workspace))}]','trust_level = "trusted"']
    (home/'config.toml').write_text('\n'.join(lines)+'\n')
    if not (home/'auth.json').is_symlink():(home/'auth.json').symlink_to(Path.home()/'.codex/auth.json')
    skill=home/'skills/codex-wake';shutil.copytree(repo/'skills/codex-wake',skill,dirs_exist_ok=resume_setup)
    workflow_source=Path.home()/'.codex/plugins/cache/created-by-me-remote/chatgpt-github-engineering/0.1.0/skills/github-handoff/SKILL.md'
    reviewer_source=workflow_source.parent.parent/'github-ask-matt/SKILL.md'
    # Exact catalog selections: unreadable paths hold before any runtime effects.
    for selected_path in (workflow_source, reviewer_source):
        if not selected_path.is_file() or not selected_path.read_text().strip():
            raise RuntimeError('selected instructions unavailable; no substitution permitted')
    # Explicit byte-preserving installation: isolated homes cannot discover the
    # main home's plugin cache merely from skills.config enablement entries.
    mirrors=[]
    for selected_path in (workflow_source, reviewer_source):
        installed=home/'skills'/selected_path.parent.name
        shutil.copytree(selected_path.parent,installed,dirs_exist_ok=resume_setup)
        destination=installed/'SKILL.md'
        digest=hashlib.sha256(selected_path.read_bytes()).hexdigest()
        if hashlib.sha256(destination.read_bytes()).hexdigest()!=digest:
            raise RuntimeError('selected instruction mirror bytes changed')
        mirrors.append(dict(source=str(selected_path),installed=str(destination),sha256=digest))
    workflow=Path(mirrors[0]['installed']);reviewer=Path(mirrors[1]['installed'])
    token_cap=400000 if correction=='reject' else 300000 if correction else 250000
    session_cap=350000 if correction=='reject' else 250000 if correction else 150000
    source_cap=50000 if correction else 100000
    if correction:(workspace/'repair.txt').write_text('unaccepted fixture\n')
    guide=skill/'SKILL.md';helper=root/'preflight.py';profiles=root/'profiles.json'
    head=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()
    receipt=dict(state='preparing',root=str(root),prefix=str(prefix),source_commit=head,
        selected_model=selected,authority='operator execute Plan0156; isolated bounded continuation fixture',
        token_cap=token_cap,time_cap_seconds=600,manual_assignment_limit=0 if qualify_only else 4 if correction else 2,mode=mode,rollback_requested=rollback,correction_case=correction,
        selected_instruction_mirrors=mirrors,
        root_window=dict(start=datetime.fromtimestamp(parent_deadline-21600,UTC).isoformat(),
            deadline=datetime.fromtimestamp(parent_deadline,UTC).isoformat(),token_cap=2000000),
        adaptation_lane=dict(token_cap=100000,time_cap_seconds=900,goal_counter='unknown'))
    env=dict(os.environ,CODEX_HOME=str(home),XDG_STATE_HOME=str(root/'state'))
    for k in ('CODEX_THREAD_ID','TMUX','TMUX_PANE','CODEX_WAKE_A2A_CAPABILITY','CODEX_WAKE_A2A_BUS_ROOT','CODEX_WAKE_SENDER_RECEIPT_AUTHORITY','PYTHONPATH'):env.pop(k,None)
    socket=root/'tmux.sock';session='owned-handoff';locator=root/'native.sock';server=None;monitor=None;created=False
    log=(root/'server.log').open('a' if resume_setup else 'w');mlog=(root/'monitor.log').open('a' if resume_setup else 'w')
    def launch_server():
        proc=subprocess.Popen([str(codex),'app-server','--listen','unix://'+str(locator)],env=env,stdout=log,stderr=log,start_new_session=True)
        deadline=time.monotonic()+20
        while proc.poll() is None and time.monotonic()<deadline:
            try:
                endpoint=locator.resolve(strict=True)
                ready=native_request('unix://'+str(endpoint),str(codex),'thread/loaded/list',{},2)
                if ready.get('data')==[] and ready.get('nextCursor') is None:return proc
                raise RuntimeError('unexpected existing native threads in setup')
            except (OSError,ValueError,RuntimeError):time.sleep(.1)
        if proc.poll() is None:
            os.killpg(proc.pid,signal.SIGTERM);proc.wait(timeout=10)
        raise RuntimeError('owned native socket did not answer readiness')
    def invoke(args):
        p=subprocess.run([str(prefix/'bin/codex-wake'),'--wake-root',str(root/'wake'),*args],env=env,text=True,capture_output=True,timeout=40)
        if not p.stdout:raise RuntimeError('installed CLI empty response '+p.stderr[-300:])
        return p.returncode,json.loads(p.stdout)
    def usage(thread):
        native=request('thread/read',dict(threadId=thread,includeTurns=True))['thread']
        path=Path(native['path']).resolve();path.relative_to(home/'sessions')
        values=[]
        for line in path.read_text().splitlines():
            e=json.loads(line);p=e.get('payload',{});i=p.get('info') or {}
            if e.get('type')=='event_msg' and p.get('type')=='token_count' and i.get('total_token_usage'):values.append(i['total_token_usage'])
        if not values:raise RuntimeError('native cumulative usage unavailable')
        return native,values[-1]
    try:
        bounds=snapshot().get('utc')
        if not bounds:raise RuntimeError('admissible UTC unavailable')
        started=original['started_at'] if original else bounds['upper']
        end=min(original['deadline'] if original else started+600,parent_deadline-60)
        if end-bounds['upper']<(240 if original else 480):raise RuntimeError('original/parent deadline leaves insufficient fixed fixture window')
        expiry=datetime.fromtimestamp(end,UTC).isoformat();receipt.update(started_at=started,deadline=end)
        # Resolve the owned listener before configuring MCP, without creating a thread.
        server=launch_server();endpoint=locator.resolve(strict=True)
        os.killpg(server.pid,signal.SIGTERM);server.wait(timeout=15)
        for selected_path in (workflow,reviewer):
            lines+=['[[skills.config]]',f'path = {json.dumps(str(selected_path))}','enabled = true']
        lines+=['[mcp_servers.codex-wake]',f'command = {json.dumps(str(prefix/"bin/codex-wake-mcp"))}',
            'args = '+json.dumps(['--wake-root',str(root/'wake'),'--lifecycle-profiles',str(profiles),
                '--app-server','unix://'+str(endpoint),'--tmux-socket',str(socket),'--tmux-session',session]),
            'enabled_tools = ["wake_sessions_show", "wake_sessions_configuration", "wake_sessions_handoff"]',
            'startup_timeout_sec = 20','tool_timeout_sec = 20']
        (home/'config.toml').write_text('\n'.join(lines)+'\n');server=launch_server()
        if locator.resolve()!=endpoint:raise RuntimeError('owned endpoint changed')
        def request(method,params):return native_request('unix://'+str(endpoint),str(codex),method,params,10)
        catalog=request('skills/list',dict(cwds=[str(workspace)],forceReload=True))
        exclusions=excluded_skill_paths(catalog,(workflow,reviewer,guide))
        if exclusions:
            # Keep the paid fixture's catalog bounded to its exact three resources.
            # Global skill files and every unrelated service remain unchanged.
            for excluded in exclusions:
                lines+=['[[skills.config]]',f'path = {json.dumps(excluded)}','enabled = false']
            (home/'config.toml').write_text('\n'.join(lines)+'\n')
            os.killpg(server.pid,signal.SIGTERM);server.wait(timeout=15)
            server=launch_server()
            catalog=request('skills/list',dict(cwds=[str(workspace)],forceReload=True))
            if excluded_skill_paths(catalog,(workflow,reviewer,guide)):
                raise RuntimeError('owned fixture skill catalog filtering did not take effect')
        receipt['skill_catalog_scope']=dict(selected=[str(workflow),str(reviewer),str(guide)],
            excluded_count=len(exclusions),verified_enabled_count=3)
        receipt['selected_instruction_catalog']=dict(writer=str(workflow),reviewer=str(reviewer))
        empty=request('thread/list',{'limit':100})
        if empty.get('data')!=[] or empty.get('nextCursor') is not None:raise RuntimeError('existing conversations hold setup resume')
        receipt['setup_readiness']=dict(loaded_threads=[],persisted_threads=[],original_window_retained=bool(original))
        subprocess.run(['tmux','-S',str(socket),'new-session','-d','-s',session,'-x','160','-y','40','sleep 700'],env=env,check=True,capture_output=True,timeout=10);created=True
        profile=dict(cwd=str(workspace),codex_home=str(home),codex_path=str(codex),app_server='unix://'+str(endpoint),tmux_socket=str(socket),tmux_session=session,timeout=10)
        defaults=dict(handoff_writer=dict(name='github-handoff',path=str(workflow)),
            preflight_reviewer=dict(name='github-ask-matt',path=str(reviewer)),
            session_token_limit=session_cap,session_time_limit_seconds=int(end-started),
            objective_token_limit=token_cap,objective_time_limit_seconds=int(end-started),max_correction_cycles=2 if correction else 0)
        objective=f'Operator-approved Plan0156 disposable continuation: execute {prefix}/bin/python {helper} --continue exactly once and report its actual result. The external controller completes this goal after verifying the command; do not invoke goal tools or change any goal. No other work, actors, resource renewal or goal budget change.'
        if correction:
            objective=f'Operator-approved Plan0156 disposable correction proof: review and repair only repair.txt under the frozen host packet, at most two corrective cycles. Execute {prefix}/bin/python {helper} --continue exactly once only after acceptance and report its actual result. The external controller completes an accepted goal after verification. Do not invoke goal tools or change goals, scope, actors or resources; rejected work cannot continue.'
        bootstrap=dict(objective=objective,approval=receipt['authority'],spawn_token_limit=source_cap,
            started_at=datetime.fromtimestamp(started,UTC).isoformat())
        write(profiles,dict(version=1,profiles={'worker':profile},lifecycle_defaults=defaults,
            continuations={'bootstrap':bootstrap}))
        constants=dict(repo=str(repo),head=head,guide=str(guide),workflow=str(workflow),reviewer=str(reviewer),prefix=str(prefix),
            review_authority=str(root/'review-authority.json'),
            native_observations=str(root/'native-observations.json'),continuation_authority=str(root/'continuation-authority.json'))
        if correction:
            repair_value='accepted correction\n' if correction=='accept' else 'attempted correction\n'
            constants.update(correction=correction,original_source_hashes={},repair_instructions=
                'Write repair.txt with exactly '+repr(repair_value)+'. No other repair changes. Then read full selected instructions and current repair evidence using the approved helper --correction-instructions, author a fresh work-review.json and successor-handoff.md, and run the original exact host verifier. The ineffective value in the rejection fixture is intentional; report its unmet criterion without substituting another repair outside this frozen packet.')
        helper.write_text(preflight_program(constants))
        bootstrap_effective=effective_configuration(json.loads(profiles.read_text()),'bootstrap','worker')
        receipt['bootstrap_configuration']=dict(revision=bootstrap_effective['revision'],
            objective_deadline=bootstrap_effective['objective_deadline'],spawn_token_limit=bootstrap['spawn_token_limit'],
            session_token_limit=bootstrap_effective['session_token_limit'],objective_token_limit=bootstrap_effective['objective_token_limit'])
        monitor,receipt['source_supervision']=start_owned_monitor(prefix,root,env,mlog)
        if qualify_only:
            probe=request('thread/start',dict(cwd=str(workspace),ephemeral=False))['thread']['id']
            registry=json.loads(profiles.read_text());registry['continuations'][probe]=bootstrap
            registry['callers']={probe:['worker']};write(profiles,registry)
            receipt['native_mcp_setup']=qualify_lifecycle_mcp(request,probe,'worker',expiry)
            observed=request('thread/read',dict(threadId=probe,includeTurns=False))['thread']
            if observed['status']['type']!='idle' or request('thread/goal/get',dict(threadId=probe))['goal'] is not None:
                raise RuntimeError('setup probe admitted unexpected native work')
            if set(p.name for p in (root/'wake/lifecycle').glob('*.json'))!={'supervision.json'}:
                raise RuntimeError('missing checkpoint made a lifecycle effect')
            receipt['native_mcp_setup'].update(thread_id=probe,turns=0,goal=None,lifecycle_effects=0,missing_checkpoint_held=True)
            receipt['generated_helper_syntax']='passed'
            raise SetupQualified
        ref=subprocess.check_output(['git','-C',str(repo),'ls-remote','--exit-code','origin','refs/heads/feat/agent-lifecycle'],text=True,timeout=15).split()[0]
        if ref!=head:raise RuntimeError('published candidate differs before native assignments')
        validation=[str(prefix/'bin/python'),'-m','unittest','discover','-s',str(repo/'tests'),'-p','test_agent_handoff.py','-q']
        checked=subprocess.run(validation,cwd=repo,env=dict(env,CODEX_WAKE_STABLE_TIME_CONFIG='',PYTHONWARNINGS='ignore'),capture_output=True,text=True,timeout=30)
        if checked.returncode!=0:raise RuntimeError('host installed public validation failed')
        host_validation=dict(verified_ref=ref,focused_validation=dict(state='passed',command=validation,
            exit_code=checked.returncode,result=checked.stderr[-500:],performed_by='host_controller'))
        write(root/'host-validation.json',host_validation)
        (workspace/'AGENTS.md').write_text(f"For reviewer preflight, first run {prefix}/bin/python {helper} --instructions {reviewer} {workflow} using functions.exec with first-line // @exec: {{\"max_output_tokens\": 20000}} and tools.exec_command max_output_tokens=20000; emit text(result.output) directly, not text(result). Read both selected Matt instruction files in full, the complete canonical operator revision and child scope/acceptance, checkpoint and immutable approved helper from this bounded output. The product guide is a separate host-qualified native catalog/resource check, not a selected review instruction. Apply github-ask-matt to this continuation request: select and apply github-handoff. Check actual supplied source and host-approved evidence, then author successor-handoff.md and work-review.json and immediately run the exact host verifier in that same shell command. The review artifact must bind configuration_revision, source_thread_id, successor_thread_id, checkpoint_sha256 and intent_fingerprint from PREFLIGHT_CONTRACT; work_review must contain verdict (accept/correct/blocked), actual selected_review, changes, acceptance_progress (host-approved criterion, change, workspace-relative path/SHA256 evidence), scope_deviations, unsupported_claims, unfinished_work and exact checkpoint next_packet. Report actual gaps; do not fabricate acceptance or infer progress from counts. Evidence available in checkpoint.json and host-validation.json; inspect their actual content. Exactly two reviewer shell commands: selected instruction/source read, then artifact authoring followed by host verification in the same command. Both selected instruction files remain complete; do not accept truncated output. No retries, extra source reads, goal changes, protected native socket access, A2A effects or resource renewal. The host supplies identity-bound native observations and validation; do not claim GitHub connector health. Outgoing writer: first read the exact selected github-handoff instructions using a command containing its absolute path and print all bytes, apply them to the supplied fixture evidence, then run its supplied checkpoint script. No other work.\n")
        shutil.copyfile(root/'host-validation.json',workspace/'host-validation.json')
        checkpoint_contract=dict(repo=str(repo),worktree=str(workspace),commit=head,dirty_work='clean frozen candidate',
            acceptance_remaining=['selected preflight','native bounded continuation','owned rollback'],
            evidence=[str(root/'host-validation.json')],pending_wakes=[],pending_messages=[],claim_holders=[],
            reply_route='root controller via native result and '+str(root/'state.json'),hard_stops=['original token and time caps; no renewal'],
            expires_at=expiry,resources=dict(token_cap=token_cap,time_cap_seconds=int(end-started),tokens_before_source=0,
                seconds_before_source=0,started_at=datetime.fromtimestamp(started,UTC).isoformat()))
        if correction:
            (workspace/'AGENTS.md').write_text((workspace/'AGENTS.md').read_text()+'\nDedicated correction fixture: compare actual repair.txt against accepted correction followed by newline. Until it matches, report correct with a correction_packet: criterion=repair fixture matches accepted correction; paths=[repair.txt]; actual repair path/hash evidence; instructions copied exactly from C[repair_instructions] in the approved helper. Do not repair before an assigned correction. During correction, execute only that frozen repair and use --correction-instructions for the first read command; it prints full selected instructions and current repair evidence, and verifies unchanged hashes for canonical sources already fully read in this same context. The ineffective rejection packet is deliberate fault injection: obey it and report correct again rather than inventing a different repair or claiming acceptance. Author fresh review and handoff artifacts, then run the original verifier in the second command. The source writer emits only its checkpoint. No goal or ordinary continuation before accepted repair.\n')
            with (workspace/'AGENTS.md').open('a') as instructions:
                instructions.write('Native proof requires the absolute approved helper path literally in the second command transcript. After artifact writing, invoke '+str(prefix/'bin/python')+' '+str(helper)+' followed by the exact source, fingerprint and checkpoint hash arguments from PREFLIGHT_CONTRACT. Do not construct the executable or helper path from root variables or string concatenation. This also applies to every corrective review.\n')
            constants['original_source_hashes']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in
                (repo/'docs/dev/plans/0156-2026-10-12-agent-lifecycle-delivery.md',repo/'docs/dev/plans/0159-2026-10-12-agent-handoff.md',workspace/'host-validation.json')}
            # checkpoint is authored below; fill its immutable hash before receiver admission.
        script=checkpoint_program(checkpoint_contract,objective)
        task='First read and print the complete selected writer instructions at '+str(workflow)+' using a command containing that absolute path. Apply them to the supplied bounded fixture checkpoint. Then execute only this Python script to write your own outgoing checkpoint, then report checkpoint ready. Do not change any goal.\n```python\n'+script+'```'
        spawn=['sessions','spawn','--profiles',str(profiles),'--profile','worker','--objective-ref','bootstrap','--intent','source-1','--name','checkpoint-source','--task',task,'--expires-at',expiry,'--json']
        deadline=time.monotonic()+180
        while True:
            code,state=invoke(spawn);receipt['source']=state;write(root/'state.json',receipt)
            if state['state']=='completed':break
            if state['state'] in ('blocked','expired') or time.monotonic()>deadline or (state['state']=='uncertain' and not(state.get('thread_id') and state.get('submission_id'))):raise RuntimeError('source held: '+state['state'])
            time.sleep(.5)
        source=state['thread_id'];native,spent=usage(source);receipt['source_usage']=spent;write(root/'native-source.json',native)
        writer_selection=dict(path=str(workflow),instructions=workflow.read_text())
        if not instruction_read(native,writer_selection,workspace):
            raise RuntimeError('selected writer instruction bytes not observed')
        if spent['total_tokens']>=source_cap:raise RuntimeError('source exceeded fixture suballowance')
        os.killpg(monitor.pid,signal.SIGINT);monitor.wait(timeout=30)
        receipt['source_supervisor_exit']=monitor.returncode;monitor=None
        receipt['source_goal']=request('thread/goal/set',dict(threadId=source,objective=objective,tokenBudget=token_cap-spent['total_tokens'],status='paused',origin='automatic'))['goal']
        # Qualify the host route on the settled source before buying a successor turn.
        receipt['host_source_preflight']=observe_native_preflight(request,source,source,guide,workspace)
        write(root/'state.json',receipt)
        policy=dict(objective=objective,approval=receipt['authority'],token_cap=token_cap,time_cap_seconds=int(end-started),tokens_before_source=spent['total_tokens'],seconds_before_source=0,started_at=datetime.fromtimestamp(started,UTC).isoformat(),preflight=dict(script=str(helper),sha256=hashlib.sha256(helper.read_bytes()).hexdigest(),receipt='preflight.json',workflow='github-ask-matt',required_checks=['canonical_sources','selected_skill','selected_workflow','native_resource','installed_cli','focused_validation'],token_allowance=session_cap),activation=dict(approved=True,max_poll_seconds=1,deadline_margin_seconds=45))
        policy['acceptance_criteria']=['restart-safe fixture checkpoint matches the approved objective, authority and next packet',
            'host-qualified installed candidate evidence is attributable and does not close wider Plan0156 acceptance']
        if correction:
            policy['correction_scope']=['repair.txt']
            policy['acceptance_criteria'].append('repair fixture matches accepted correction')
            constants['original_source_hashes']['checkpoint.json']=hashlib.sha256((workspace/'checkpoint.json').read_bytes()).hexdigest()
            constants['original_source_hashes']['host-validation.json']=hashlib.sha256((workspace/'host-validation.json').read_bytes()).hexdigest()
            helper.write_text(preflight_program(constants))
            policy['preflight']['sha256']=hashlib.sha256(helper.read_bytes()).hexdigest()
        configured=dict(version=1,profiles={'worker':profile},lifecycle_defaults=defaults,continuations={source:policy},callers={source:['worker']})
        effective=effective_configuration(configured,source,'worker')
        receipt['configuration_revision']=effective['revision']
        write(root/'review-authority.json',dict(configuration_revision=effective['revision'],policy=policy))
        write(profiles,configured)
        checkpoint=workspace/'checkpoint.json';digest=hashlib.sha256(checkpoint.read_bytes()).hexdigest()
        handoff=['sessions','handoff','--profiles',str(profiles),'--profile','worker','--intent','handoff-1','--thread-id',source,'--checkpoint','checkpoint.json','--checkpoint-sha256',digest,'--expires-at',expiry,'--mode',mode,'--json']
        deadline=time.monotonic()+min(480 if correction else 240,max(0,end-snapshot()['utc']['upper']-50))
        def observe_handoff(state):
            receipt['handoff']=state;write(root/'state.json',receipt)
            if state.get('successor_thread_id') and not (root/'native-observations.json').exists():
                observed=observe_native_preflight(request,source,state['successor_thread_id'],guide,workspace)
                observed.update(checkpoint_sha256=digest,intent_fingerprint=state['fingerprint'],host_validation=host_validation)
                write(root/'native-observations.json',observed)
            if correction=='reject' and state.get('terminal_review') and state.get('reason')=='correction_cycles_exhausted':
                if state['objective_budget']['correction_cycles']!=2 or len(state['review_history'])!=2:
                    raise RuntimeError('rejection did not retain exactly two corrective cycles')
                if request('thread/goal/get',dict(threadId=state['successor_thread_id']))['goal'] is not None:
                    raise RuntimeError('rejected work prepared an unauthorized goal')
                native,spent=usage(state['successor_thread_id'])
                if len(native['turns'])!=3 or any(t['status']!='completed' for t in native['turns']):
                    raise RuntimeError('rejection did not stop at three completed native review turns')
                if spent['total_tokens']>session_cap or receipt['source_usage']['total_tokens']+spent['total_tokens']>token_cap:
                    raise RuntimeError('rejection proof exceeded its fixed resource contract')
                receipt.update(successor_usage=spent,rejection_goal=None,correction_cycles=2,
                    review_history=state['review_history'],rejection_native_turns=3)
                raise CorrectionStopped

        state=wait_for_preflight(invoke,handoff,deadline,observe_handoff)
        target=state['successor_thread_id'];native,spent=usage(target);receipt['preflight_usage']=spent;write(root/'native-preflight.json',native)
        instructions=[i for t in native['turns'] for i in t['items'] if i['type']=='commandExecution' and ('--instructions' in i.get('command','') or '--correction-instructions' in i.get('command','')) and i.get('exitCode')==0]
        expected_reviews=1+state.get('objective_budget',{}).get('correction_cycles',0)
        if len(instructions)!=expected_reviews or not all(all('SELECTED_INSTRUCTIONS:'+k+':' in item.get('aggregatedOutput','') for k in ('reviewer','workflow')) for item in instructions):raise RuntimeError('actual selected instruction read unverified')
        if not instruction_read(native,effective['preflight_reviewer'],workspace):
            raise RuntimeError('selected reviewer instruction bytes not observed')
        if not instruction_read(native,effective['handoff_writer'],workspace):
            raise RuntimeError('downstream handoff workflow instruction bytes not observed')
        authored=[i for t in native['turns'] if t.get('status')=='completed' for i in t['items']
            if i.get('type')=='commandExecution' and i.get('status')=='completed'
            and i.get('exitCode')==0 and 'work-review.json' in i.get('command','')]
        if len(authored)!=expected_reviews:
            raise RuntimeError('reviewer-authored work review native evidence unverified')
        receipt['work_review_artifact']=dict(path=str(workspace/'work-review.json'),
            sha256=hashlib.sha256((workspace/'work-review.json').read_bytes()).hexdigest(),
            native_item_id=authored[-1]['id'])
        if correction:
            if expected_reviews!=2 or len(state['review_history'])!=1:
                raise RuntimeError('accepted repair did not consume exactly one correction')
            receipt.update(correction_cycles=1,review_history=state['review_history'])
        receipt['instruction_read_item']=instructions[0]['id']
        mcp_args=dict(profile='worker',intent='handoff-1',thread_id=source,checkpoint='checkpoint.json',checkpoint_sha256=digest,expires_at=expiry,mode=mode,caller_thread_id=source)
        receipt['native_handoff_mcp_prepared']=call_source_mcp(
            lambda method,params:native_request('unix://'+str(endpoint),str(codex),method,params,70),
            source,receipt['source_goal'],'wake_sessions_handoff',mcp_args)
        if correction:
            # Repair acceptance is its own axis. Both-mode continuation and
            # rollback already have native proof; do not purchase a duplicate.
            receipt.update(state='passed_correction_acceptance_axis',successor_usage=spent,
                accepted_repair_sha256=hashlib.sha256((workspace/'repair.txt').read_bytes()).hexdigest(),
                final_source_goal=request('thread/goal/get',dict(threadId=source))['goal'],
                final_successor_goal=request('thread/goal/get',dict(threadId=target))['goal'])
            raise SetupQualified
        monitor=subprocess.Popen([str(prefix/'bin/codex-waked'),'--wake-root',str(root/'wake'),'--no-dispatch','--interval','1'],env=env,stdout=mlog,stderr=mlog,start_new_session=True)
        deadline=time.monotonic()+min(180,max(0,end-snapshot()['utc']['upper']-50))
        while time.monotonic()<deadline and monitor.poll() is None:
            code,state=invoke(handoff);receipt['continuation']=state;write(root/'state.json',receipt)
            if not (root/'continuation-authority.json').exists():
                goal=request('thread/goal/get',dict(threadId=target))['goal']
                if goal and goal['status']=='active':write(root/'continuation-authority.json',dict(goal=goal))
            if (workspace/'continued.json').exists():break
            if state['state'] in ('expired','blocked'):raise RuntimeError('continuation held: '+state['reason'])
            time.sleep(1)
        if not (workspace/'continued.json').exists():raise RuntimeError('actual goal continuation command not observed')
        # Verify real command completion before ending goal dispatch.
        deadline=time.monotonic()+20
        while True:
            native,spent=usage(target)
            matching=[t for t in native['turns'] if any(i.get('type')=='commandExecution' and 'CONTINUATION_CHECK:'+target+':'+digest in (i.get('aggregatedOutput') or '') and i.get('exitCode')==0 for i in t['items'])]
            executed=[i for t in matching for i in t['items'] if i.get('type')=='commandExecution' and i.get('status')=='completed' and i.get('exitCode')==0 and str(helper) in i.get('command','') and '--continue' in i.get('command','') and 'CONTINUATION_CHECK:'+target+':'+digest in (i.get('aggregatedOutput') or '')]
            if len(matching)==1 and len(executed)==1:break
            if time.monotonic()>deadline:raise RuntimeError('native continuation completion unverified')
            time.sleep(.5)
        goal=request('thread/goal/get',dict(threadId=target))['goal']
        if not goal or goal['status'] not in ('active','complete') or any(goal.get(k)!=state['successor_goal'].get(k) for k in ('threadId','objective','tokenBudget','createdAt')):
            raise RuntimeError('exact active continuation owner not observed before completion')
        done=goal if goal['status']=='complete' else request('thread/goal/set',dict(threadId=target,status='complete',origin='automatic'))['goal']
        if done['status']!='complete' or done['tokenBudget']!=goal['tokenBudget']:
            raise RuntimeError('native continuation completion did not conserve budget')
        deadline=time.monotonic()+20
        while True:
            native,spent=usage(target)
            final_turn=[t for t in native['turns'] if t['id']==matching[0]['id']]
            if len(final_turn)==1 and final_turn[0]['status']=='completed':break
            if time.monotonic()>deadline:raise RuntimeError('native continuation turn completion unverified')
            time.sleep(.5)
        if receipt['source_usage']['total_tokens']+spent['total_tokens']>receipt['token_cap']:
            raise RuntimeError('reported native fixture usage exceeded total cap')
        if spent['total_tokens']>defaults['session_token_limit']:
            raise RuntimeError('actual successor rollout exceeded configured session cap')
        final_goal=request('thread/goal/get',dict(threadId=target))['goal']
        if (not final_goal or final_goal['status']!='complete'
                or any(final_goal.get(k)!=done.get(k) for k in ('threadId','objective','tokenBudget','createdAt'))
                or final_goal['tokensUsed']>final_goal['tokenBudget']):
            raise RuntimeError('final native goal completion/accounting unverified')
        done=final_goal
        receipt.update(state='passed_continuation_axis',successor_usage=spent,continuation_turn_id=matching[0]['id'],final_source_goal=request('thread/goal/get',dict(threadId=source))['goal'],final_successor_goal=done)
        receipt['native_handoff_mcp_result']=call_source_mcp(
            lambda method,params:native_request('unix://'+str(endpoint),str(codex),method,params,70),
            source,receipt['final_source_goal'],'wake_sessions_handoff',mcp_args)
        write(root/'native-continuation.json',native)
        if mode=='same-tab':
            old=receipt['handoff']['source_attachment'];fresh=receipt['handoff']['successor']['attachment']
            if old['pane_id']!=fresh['pane_id'] or old['window_id']!=fresh['window_id'] or old['client_pid']==fresh['client_pid']:
                raise RuntimeError('same-tab identity/generation proof failed')
            receipt['same_tab_identity']=dict(original=old,successor=fresh)
        if rollback:
            deadline=time.monotonic()+30
            while True:
                code,restored=invoke(handoff+['--rollback']);receipt['rollback']=restored;write(root/'state.json',receipt)
                if restored.get('rollback',{}).get('state')=='completed':break
                if time.monotonic()>deadline:raise RuntimeError('installed rollback did not settle')
                time.sleep(.5)
            returned=restored['rollback'];before=receipt['source_goal'];after=returned['source_goal_after']
            if (after['status']!='paused' or any(after.get(k)!=before.get(k) for k in ('threadId','objective','createdAt'))
                    or any(after[k]<before[k] for k in ('tokensUsed','timeUsedSeconds'))):
                raise RuntimeError('rollback source identity/counters not conserved')
            receipt['native_rollback_mcp_result']=call_source_mcp(
                lambda method,params:native_request('unix://'+str(endpoint),str(codex),method,params,70),
                source,after,'wake_sessions_handoff',dict(mcp_args,rollback=True))
            receipt['rollback_source_goal']=request('thread/goal/get',dict(threadId=source))['goal']
    except SetupQualified:
        if receipt['state']!='passed_correction_acceptance_axis':receipt.update(state='qualified_setup')
    except CorrectionStopped:receipt.update(state='passed_bounded_rejection_axis')
    except Exception as exc:receipt.update(state='failed',error=str(exc))
    finally:
        if monitor is not None and monitor.poll() is None:
            os.killpg(monitor.pid,signal.SIGINT)
            try:monitor.wait(timeout=30)
            except subprocess.TimeoutExpired:receipt['monitor_shutdown']='timed_out'
        receipt['monitor_exit']=monitor.poll() if monitor else None
        cleanup_source=receipt.get('source',{}).get('thread_id')
        if cleanup_source:
            try:
                receipt['owned_source_settlement']=settle_owned_successor(request,dict(
                    successor_thread_id=cleanup_source,successor=receipt['source'],
                    successor_goal=receipt.get('source_goal')))
                _,receipt['source_usage']=usage(cleanup_source)
            except Exception as exc:receipt['source_final_readback_error']=type(exc).__name__
        cleanup_target=receipt.get('handoff',{}).get('successor_thread_id')
        if cleanup_target:
            try:
                receipt['owned_successor_settlement']=settle_owned_successor(request,receipt['handoff'])
                _,receipt['successor_usage']=usage(cleanup_target)
                receipt['cleanup_successor_goal']=request('thread/goal/get',dict(threadId=cleanup_target))['goal']
            except Exception as exc:receipt['final_readback_error']=type(exc).__name__
        if created:subprocess.run(['tmux','-S',str(socket),'kill-session','-t',session],env=env,capture_output=True,timeout=10)
        if server is not None and server.poll() is None:
            os.killpg(server.pid,signal.SIGTERM)
            try:server.wait(timeout=20)
            except subprocess.TimeoutExpired:
                receipt['server_shutdown']='forced_after_owned_settlement_attempt'
                os.killpg(server.pid,signal.SIGKILL);server.wait(timeout=10)
        log.close();mlog.close();receipt['server_exit']=server.poll() if server else None
        matches=[];denied=[]
        for p in Path('/proc').iterdir():
            if not p.name.isdigit():continue
            try:
                if p.stat().st_uid==os.getuid() and ('CODEX_HOME='+str(home)).encode() in (p/'environ').read_bytes().split(b'\0'):matches.append(int(p.name))
            except PermissionError:denied.append(int(p.name))
            except (FileNotFoundError,ProcessLookupError):pass
        receipt['cleanup']=dict(private_readable_environment_matches=matches,denied_environment_pids=denied)
        if matches or receipt['server_exit'] is None or receipt.get('monitor_shutdown'):receipt.update(state='failed',cleanup_error='owned processes remain or shutdown unverified')
        write(root/'state.json',receipt)
    print(json.dumps({k:receipt.get(k) for k in ('state','error','root','source_usage','successor_usage','cleanup')}))
    return 0 if receipt['state'] in ('passed_continuation_axis','qualified_setup','passed_bounded_rejection_axis','passed_correction_acceptance_axis') else 1


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execute',action='store_true');p.add_argument('--resume-setup',action='store_true');p.add_argument('--root',type=Path,required=True);p.add_argument('--prefix',type=Path,required=True);p.add_argument('--repo',type=Path,required=True);p.add_argument('--parent-deadline',type=float,required=True)
    p.add_argument('--mode',choices=['new-tab','same-tab'],default='new-tab');p.add_argument('--rollback',action='store_true')
    p.add_argument('--qualify-only',action='store_true',help='verify isolated catalog/helper and cleanup without any model assignment')
    p.add_argument('--correction',choices=['accept','reject'],help='dedicated bounded correction proof, at most two corrective assignments')
    args=p.parse_args()
    if not args.execute:p.error('--execute required for two owned assignments and bounded native goal effects')
    return execute(args.root.resolve(),args.prefix.resolve(),args.repo.resolve(),args.parent_deadline,args.resume_setup,args.mode,args.rollback,args.qualify_only,args.correction)
if __name__=='__main__':raise SystemExit(main())
