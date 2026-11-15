#!/usr/bin/env python3
"""Opt-in deployed connector visible restoration probe on one disposable thread.

This diagnostic does not certify ticket acceptance; correlate final native result
and restored harness/cwd separately before claiming completion.

Run with the installed connector Python. Secrets stay in process memory; only a
credential-free receipt is retained. No operator conversation is addressed.
"""
import argparse
import os
import asyncio
import base64
import hashlib
import json
from pathlib import Path
import secrets
import tempfile
import time
import subprocess
import shlex
from datetime import datetime, timezone, timedelta

import httpx2 as httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from codex_wake.controller_auth import OAuthAuthority
from codex_wake.local_sessions import discover
from codex_wake.native_protocol import native_request
from codex_wake.shared_app_server import locate_shared_endpoint


def decode(result):
    if getattr(result,'structured_content',None) is not None:return result.structured_content
    return json.loads(next(c.text for c in result.content if c.type=='text'))


async def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-live',action='store_true',required=True)
    parser.add_argument('--receipt',type=Path,required=True)
    args=parser.parse_args()
    os.umask(0o077)
    config=json.loads((Path.home()/'.config/codex-wake/external-connector.json').read_text())
    root=Path(config['wake_root']);issuer=config['issuer'];endpoint=locate_shared_endpoint(timeout=10)
    authority=OAuthAuthority(root/'external-oauth/authority.sqlite',issuer=issuer,resource=issuer+'/mcp')
    output=args.receipt
    assert not output.exists(), 'Receipt already exists; preserve previous evidence'
    tmux_name='cw668-visible-'+secrets.token_hex(4)
    owned_session=False
    grant=None;thread=None;receipt=dict(ticket=668,status='running',boundary='deployed HTTPS OAuth/MCP')
    def native(method,args):return native_request(endpoint,['codex'],method,args,60)
    try:
        scratch=Path(__file__).resolve().parents[1]/'.scratch'
        scratch.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='cw668-',dir=scratch) as cwd:
            receipt['stage']='native setup'
            thread=native('thread/start',dict(cwd=cwd,approvalPolicy='never',sandbox='read-only'))['thread']['id']
            receipt.update(thread_id=thread,cwd=cwd)
            native('turn/start',dict(threadId=thread,input=[dict(type='text',text='Reply exactly setup-ready. Do not use tools.')]))
            deadline=time.monotonic()+120
            from codex_wake.shared_app_server import SharedAppServerReader
            while time.monotonic()<deadline:
                metadata=native('thread/read',dict(threadId=thread,includeTurns=False))['thread']
                if metadata.get('status',{}).get('type')=='idle':break
                await asyncio.sleep(1)
            assert metadata.get('status',{}).get('type')=='idle','setup turn did not finish'
            receipt['setup_turn']='completed separate native preparation'
            selected=discover(root,endpoint,thread_id=thread)['sessions']
            assert len(selected)==1, 'exact disposable thread discovery required'
            target=selected[0]['target']
            receipt['stage']='native visible attachment'
            receipt['sessions_before']=subprocess.check_output(['tmux','list-sessions','-F','#{session_id}:#{session_name}'],text=True).splitlines()
            command=shlex.join(['env','-u','CODEX_THREAD_ID','-u','CODEX_SESSION_ID','-u','TMUX_PANE',target['executable'],'resume','--remote',endpoint,'--no-alt-screen','-C',cwd,thread])
            subprocess.run(['tmux','new-session','-d','-s',tmux_name,'-x','120','-y','35',command],check=True)
            owned_session=True
            receipt['owned_session']=tmux_name
            from codex_wake.sessions import observe
            deadline=time.monotonic()+90
            while time.monotonic()<deadline:
                snap=observe(endpoint=endpoint,timeout=10)
                rows=[r for r in snap['sessions'] if r.get('thread_id')==thread and r.get('attachments')]
                if len(rows)==1:break
                await asyncio.sleep(1)
            assert len(rows)==1,'native attachment missing'
            receipt['attachment']=rows[0]['attachments'][0]

            receipt['stage']='public OAuth/MCP'
            verifier=secrets.token_urlsafe(48);challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
            redirect=config['redirect_uris'][0]
            async with httpx.AsyncClient(timeout=70) as http:
                reg=await http.post(issuer+'/register',json=dict(client_name='cw668-visible-wake',redirect_uris=[redirect]));reg.raise_for_status();client=reg.json()['client_id']
                code=authority.authorize(subject=config['owner'],principal_kind='owner',client_id=client,redirect_uri=redirect,resource=issuer+'/mcp',scopes=['observe','content.observe','control'],targets=[dict(host=config['host'],environment=config['environment'],conversation_id=thread)],code_challenge=challenge)
                response=await http.post(issuer+'/token',data=dict(grant_type='authorization_code',client_id=client,code=code,redirect_uri=redirect,code_verifier=verifier,resource=issuer+'/mcp'));response.raise_for_status();token=response.json()['access_token'];grant=authority.authenticate(token).grant_id
                async with httpx.AsyncClient(headers={'Authorization':'Bearer '+token},timeout=70) as transport:
                    async with streamable_http_client(issuer+'/mcp',http_client=transport) as streams:
                        async with ClientSession(streams[0],streams[1]) as session:
                            await session.initialize()
                            request=dict(idempotency_key='cw668-'+secrets.token_hex(8),thread_id=thread,prompt='Reply exactly CW668_VISIBLE_RESTORATION. Do not use tools.',session_mode='reopen_live',cadence=dict(kind='interval',seconds=30,start_at=(datetime.now(timezone.utc)+timedelta(seconds=45)).isoformat()),end=dict(kind='count',count=1),missed=dict(policy='skip',max_lateness_seconds=15),overlap=dict(policy='skip'),delivery_window_seconds=15)
                            receipt['thread_id']=thread;receipt['request']=request
                            missing=dict(request);missing.pop('session_mode')
                            refused=decode(await session.call_tool('wake_wakes_schedules_register',dict(request=missing)))
                            assert 'explicit_schedule_fields_required' in json.dumps(refused),refused
                            receipt['missing_mode']='refused'
                            receipt['stage']='schedule registration'
                            registered=decode(await session.call_tool('wake_wakes_schedules_register',dict(request=request)))
                            schedule=None
                            try:
                                receipt['registration']=registered
                                assert registered.get('status')=='completed',registered
                                schedule=registered['result'];receipt['schedule_id']=schedule['id']
                                assert schedule['armed'],schedule
                                # The exact owned recipient is genuinely closed before due time.
                                subprocess.run(['tmux','kill-session','-t',tmux_name],check=True)
                                receipt['closed_before_due']=True
                                receipt['stage']='closed recipient due wake'
                                deadline=time.monotonic()+100
                                while time.monotonic()<deadline:
                                    shown=decode(await session.call_tool('wake_wakes_schedules_show',dict(schedule_id=schedule['id'])))['result']
                                    receipt['after_due']=shown
                                    if shown.get('occurrences') and all(o.get('status') not in ('pending','dispatching','active') for o in shown['occurrences']):break
                                    await asyncio.sleep(1)
                                observed=native('thread/read',dict(threadId=thread,includeTurns=True))['thread']
                                messages=[i for t in observed['turns'] for i in t.get('items',[]) if i.get('type')=='userMessage']
                                receipt['native_inputs_after_closure']=len(messages)-1
                                receipt['restoration_attachments']=[r['attachments'] for r in observe(endpoint=endpoint,timeout=10)['sessions'] if r.get('thread_id')==thread]
                                # This probe never certifies success from message count alone.
                                # A completing run also needs the correlated final result and
                                # verified restored harness/cwd before ticket acceptance.
                                receipt['status']='incomplete'
                                receipt['unqualified_criteria']=['correlated final result','restored harness and cwd']
                            finally:
                                if schedule is not None:
                                    current=decode(await session.call_tool('wake_wakes_schedules_show',dict(schedule_id=schedule['id'])))['result']
                                    receipt['schedule_cleanup']=decode(await session.call_tool('wake_wakes_schedules_cancel',dict(schedule_id=schedule['id'],expected_revision=current['revision'])))

    except Exception as error:
        receipt['failure_type']=type(error).__name__
        raise
    finally:
        if owned_session:subprocess.run(['tmux','kill-session','-t',tmux_name],capture_output=True)
        listed=subprocess.run(['tmux','list-sessions','-F','#{session_name}'],capture_output=True,text=True)
        receipt['owned_session_absent']=tmux_name not in listed.stdout.splitlines()
        receipt['memory_disposition']='forbidden'
        receipt['memory_reason']='No explicit memory write request'
        try:
            if thread is not None:
                native('thread/archive',dict(threadId=thread));receipt['disposable_thread']='archived'
        finally:
            try:
                if grant is not None:
                    authority.revoke_grant(grant);receipt['temporary_grant']='revoked'
            finally:
                output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(receipt,indent=2));output.chmod(0o600)
                if receipt['status']=='running':receipt['status']='failed'
                output.write_text(json.dumps(receipt,indent=2))
                print(json.dumps(receipt))



if __name__=='__main__':asyncio.run(main())
