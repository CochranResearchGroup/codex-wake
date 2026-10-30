"""Prepare an explicit cross-account context fork without authorizing work."""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import select
import signal
import subprocess
import sys
import tempfile
import time
from uuid import UUID

from .build_channels import _home_ownership, _pinned_executable, load_build, validate_history
from .config import account_environment, load_settings
from .history import HistoryError, select_session, selected_profiles


class ContinuationError(ValueError):
    pass


def _save(path: Path, value: dict) -> None:
    descriptor, temporary = tempfile.mkstemp(prefix='.continuation-', dir=path.parent)
    try:
        with os.fdopen(descriptor, 'w') as stream:
            json.dump(value, stream, indent=2)
            stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try: os.fsync(directory)
        finally: os.close(directory)
    finally:
        if os.path.exists(temporary): os.unlink(temporary)


class NativeFork:
    """One owned stdio backend, pinned to a selected target account/build."""
    def __init__(self, build, home: Path, timeout: float = 15):
        self.build, self.home, self.timeout = build, home, timeout

    def __enter__(self):
        validate_history(self.build, self.home)
        self.stack = ExitStack()
        executable = self.stack.enter_context(_pinned_executable(self.build))
        env = account_environment(self.home, self.home.name)
        env.pop('CODEX_THREAD_ID', None)
        self.process = subprocess.Popen([f'/proc/self/fd/{executable}', 'app-server'],
            env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            pass_fds=(executable,), start_new_session=True)
        self.pending = b''; self.sequence = 0
        try:
            result = self.request('initialize', {'clientInfo': {'name':'codex-profiles-continuation','version':'0.2.1'}, 'capabilities':{'experimentalApi':True}})
            if result.get('codexHome') != str(self.home):
                raise ContinuationError('native target account namespace mismatch')
            self.process.stdin.write(b'{"method":"initialized"}\n');self.process.stdin.flush()
        except BaseException:
            self.__exit__(None, None, None)
            raise
        return self

    def request(self, method: str, params: dict) -> dict:
        self.sequence += 1; expected = self.sequence
        self.process.stdin.write((json.dumps({'id':expected,'method':method,'params':params})+'\n').encode())
        self.process.stdin.flush(); deadline = time.monotonic()+self.timeout
        while time.monotonic() < deadline:
            while b'\n' in self.pending:
                line, self.pending = self.pending.split(b'\n',1)
                try: response=json.loads(line)
                except ValueError: continue
                if response.get('id') != expected: continue
                if 'error' in response: raise ContinuationError('native fork request rejected; inspect operation before retry')
                return response.get('result', {})
            ready,_,_=select.select([self.process.stdout],[],[],max(0,deadline-time.monotonic()))
            if not ready: break
            chunk=os.read(self.process.stdout.fileno(),65536)
            if not chunk: break
            self.pending += chunk
            if len(self.pending)>32*1024*1024: raise ContinuationError('native response exceeds bounded context metadata limit')
        raise ContinuationError('native response unavailable; operation requires reconciliation')

    def __exit__(self, *unused):
        if hasattr(self, 'process'):
            self.process.stdin.close()
            try: self.process.wait(timeout=1)
            except subprocess.TimeoutExpired: pass
            try: os.killpg(self.process.pid, signal.SIGKILL)
            except ProcessLookupError: pass
            self.process.wait(); self.process.stdout.close()
        self.stack.close()


def _accounting_reference(wake_root: Path | None, objective_id: str | None, source_id: str) -> dict:
    """Read the existing accounting owner; a reference never creates a binding."""
    result={'status':'unqualified','reason':'no validated successor accounting binding'}
    if not wake_root or not objective_id: return result
    path=wake_root/'objective-ledgers'/(hashlib.sha256(objective_id.encode()).hexdigest()+'.json')
    if not path.is_file(): return dict(result, reason='existing objective allocation unavailable')
    try:
        from codex_wake.objective_ledger import ObjectiveLedger
        view=ObjectiveLedger(wake_root,objective_id).inspect(now=time.time())
        linked=source_id in view.get('request_sessions',{}) or any(k.startswith('goal:'+source_id+':') for k in view.get('goal_aliases',{})) or any(k.startswith('goal:'+source_id+':') for k in view.get('actors',{}))
        if not linked: return dict(result, reason='source not bound to existing objective allocation')
        return {'status':'reference_only','objective_id':objective_id,'wake_root':str(wake_root),
                'source_thread_id':source_id,'original_deadline':view.get('original_deadline'),
                'remaining_tokens':view.get('remaining_tokens'),'remaining_seconds':view.get('remaining_seconds'),
                'tokens_used':view.get('tokens_used'),'reason':'successor binding must be validated by existing accounting owner'}
    except (ImportError, ValueError, OSError, KeyError):
        return dict(result,reason='existing accounting owner could not qualify continuity')


def _history_snapshot(source_bytes: bytes, source_home: Path) -> tuple[bytes, str, list[dict]]:
    """Detach bounded native JSONL lineage at its immutable byte/ordinal cutoffs.

    Native HistoryPosition excludes end_ordinal_exclusive, and the child's
    session metadata occupies that ordinal. Only the snapshot becomes legacy;
    source records and every response/event payload remain unchanged.
    """
    lines=source_bytes.splitlines()
    first=json.loads(lines[0])
    metadata=first['payload']
    if metadata.get('history_mode')!='paginated':
        if metadata.get('history_base'):
            raise ContinuationError('unknown legacy history reference; no partial history was copied')
        return source_bytes, 'native_full_available', []
    evidence=[];seen=set();total=len(source_bytes)
    def items(raw, depth=0):
        nonlocal total
        rows=[json.loads(line) for line in raw.splitlines()]
        meta=rows[0]
        if meta.get('type')!='session_meta' or meta['payload'].get('history_mode')!='paginated':
            raise ContinuationError('incompatible paginated lineage metadata')
        base=meta['payload'].get('history_base')
        inherited=[]
        if base:
            if depth>=64:raise ContinuationError('paginated lineage exceeds bounded snapshot depth')
            parent_id=str(UUID(base['thread_id']))
            if parent_id in seen:raise ContinuationError('paginated lineage cycle')
            seen.add(parent_id)
            matches=[]
            for folder in ('sessions','archived_sessions'):
                for candidate in (source_home/folder).rglob('*'+parent_id+'.jsonl'):
                    resolved=candidate.resolve()
                    if not resolved.is_relative_to(source_home.resolve()) or candidate.is_symlink():
                        raise ContinuationError('paginated lineage escapes source tenant')
                    matches.append(resolved)
            if len(set(matches))!=1:raise ContinuationError('missing or ambiguous paginated source rollout')
            parent=matches[0]
            size=parent.stat().st_size;total+=size
            if total>128*1024*1024:raise ContinuationError('source exceeds bounded history snapshot; no history was truncated')
            data=parent.read_bytes()
            offset=base['end_byte_offset'];end=base['end_ordinal_exclusive']
            if (type(offset) is not int or type(end) is not int or end<1
                    or offset<1 or offset>len(data) or data[offset-1:offset]!=b'\n'):
                raise ContinuationError('invalid paginated lineage byte cutoff')
            prefix=data[:offset]
            prefix_rows=[json.loads(line) for line in prefix.splitlines()]
            ordinals=[row.get('ordinal') for row in prefix_rows]
            if (any(type(n) is not int for n in ordinals) or ordinals[-1]!=end-1
                    or any(n>=end for n in ordinals) or meta.get('ordinal')!=end):
                raise ContinuationError('invalid paginated lineage ordinal cutoff')
            evidence.append({'path':str(parent),'sha256':hashlib.sha256(data).hexdigest(),
                             'end_byte_offset':offset,'end_ordinal_exclusive':end})
            inherited=items(prefix,depth+1)
        return inherited+rows[1:]
    body=items(source_bytes)
    metadata['history_mode']='legacy'
    metadata.pop('history_base',None)
    first.pop('ordinal',None)
    result=[first]
    for item in body:
        item.pop('ordinal',None)
        result.append(item)
    return b''.join((json.dumps(item)+'\n').encode() for item in result), 'materialized_paginated', evidence


def _bind_accounting(receipt: dict) -> None:
    reference=receipt['accounting']
    if reference.get('status')!='reference_only':return
    try:
        from codex_wake.objective_ledger import ObjectiveLedger
        ledger=ObjectiveLedger(Path(reference['wake_root']),reference['objective_id'])
        view=ledger.continue_request_thread(receipt['successor_thread_id'],receipt['source']['thread_id'],
            {'intent':receipt['intent'],'fingerprint':receipt['fingerprint'],
             'source_namespace':receipt['source']['namespace'],'target_namespace':receipt['target']['namespace']},now=time.time())
        reference.update(status='bound',successor_thread_id=receipt['successor_thread_id'],
            original_deadline=view['original_deadline'],tokens_used=view['tokens_used'],
            remaining_tokens=view['remaining_tokens'],remaining_seconds=view['remaining_seconds'],
            session_deadline=view['request_sessions'][receipt['successor_thread_id']]['deadline'],
            reason='existing request accounting owner retains cumulative session spending and deadline')
    except (ImportError, AttributeError, ValueError, OSError, KeyError) as exc:
        reference.update(status='held',reason='existing accounting owner could not bind successor: '+str(exc))


def continue_account(settings, source_id: str, owner: str, target: str, intent: str,
                     manifest: Path, *, channel: str='modded', wake_root: Path | None=None,
                     objective_id: str | None=None, reconcile: str | None=None) -> dict:
    if not re.fullmatch(r'[A-Za-z0-9_.-]{1,128}',intent):
        raise ContinuationError('intent must be a stable simple identifier')
    source_id=str(UUID(source_id))
    source_profile=selected_profiles(settings,[owner])[0]
    source_home=settings.account_root(source_profile).resolve()
    target_profile=selected_profiles(settings,[target])[0]
    target_home=settings.account_root(target_profile).absolute()
    if target_home.resolve()==source_home:
        raise ContinuationError('cross-account continuation requires a different target tenant')
    root=settings.shared_root/'continuations';root.mkdir(parents=True,exist_ok=True,mode=0o700)
    fingerprint=hashlib.sha256(json.dumps([str(source_home),source_id,str(target_home),channel,intent]).encode()).hexdigest()
    path=root/(fingerprint+'.json')
    with (root/(fingerprint+'.lock')).open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        if path.exists():
            receipt=json.loads(path.read_text())
            if reconcile and receipt['state'] in ('creating','uncertain'):
                successor=str(UUID(reconcile))
                with _home_ownership(target_home), NativeFork(load_build(manifest,channel,target_home),target_home) as native:
                    response=native.request('thread/read',{'threadId':successor,'includeTurns':False})
                    thread=response['thread']; saved=Path(thread['path']).resolve()
                    if (thread.get('id')!=successor or thread.get('forkedFromId')!=source_id
                            or not saved.is_file() or not saved.is_relative_to(target_home.resolve())):
                        raise ContinuationError('successor provenance does not match uncertain operation')
                    with saved.open() as stream: first=json.loads(stream.readline(131072))
                    metadata=first.get('payload',{})
                    if metadata.get('id')!=successor or metadata.get('forked_from_id')!=source_id:
                        raise ContinuationError('persisted successor provenance does not match source')
                    receipt.update(state='prepared_context',successor_thread_id=successor,
                                   successor_path=str(saved),reconciled=True)
                    _bind_accounting(receipt)
                    _save(path,receipt)
            return receipt
        source=select_session(settings,source_id,owner)
        if not target_home.is_dir() or target_home.is_symlink():
            raise ContinuationError('target account must already be provisioned')
        with ExitStack() as stack:
            for home in sorted({Path(source['namespace']),target_home}):stack.enter_context(_home_ownership(home))
            source_bytes=Path(source['rollout_path']).read_bytes()
            if len(source_bytes)>128*1024*1024: raise ContinuationError('source exceeds bounded history snapshot; no history was truncated')
            lines=source_bytes.splitlines()
            first=json.loads(lines[0]) if lines else {}
            metadata=first.get('payload',{})
            if first.get('type')!='session_meta' or metadata.get('id')!=source_id:
                raise ContinuationError('saved conversation identity does not match selected source')
            snapshot_bytes,history_kind,lineage=_history_snapshot(source_bytes,source_home)
            snapshot=root/(fingerprint+'.source.jsonl')
            with snapshot.open('xb') as stream:stream.write(snapshot_bytes)
            snapshot.chmod(0o600)
            receipt={'schema_version':1,'intent':intent,'fingerprint':fingerprint,'source':source,
                     'source_sha256':hashlib.sha256(source_bytes).hexdigest(),
                     'source_lineage':lineage,
                     'target':{'profile':target_profile,'namespace':str(target_home),'channel':channel},
                     'state':'prepared','history':history_kind,'work_authorized':False,
                     'accounting':_accounting_reference(wake_root,objective_id,source_id),
                     'goal_continuation':'deferred','pending_actions':'not_replayed','created_at':time.time()}
            _save(path,receipt)
            try:
                with NativeFork(load_build(manifest,channel,target_home),target_home) as native:
                    receipt['state']='creating';_save(path,receipt)
                    result=native.request('thread/fork',{'threadId':source_id,'path':str(snapshot),
                        'cwd':source['cwd'],'excludeTurns':True,'deferGoalContinuation':True})
                    thread=result['thread']; successor=str(UUID(thread['id']))
                    if successor==source_id: raise ContinuationError('native fork did not create a distinct successor')
                    saved=Path(thread['path']).resolve()
                    if not saved.is_file() or not saved.is_relative_to(target_home.resolve()):
                        raise ContinuationError('native successor was not persisted in target namespace')
                    if hashlib.sha256(Path(source['rollout_path']).read_bytes()).hexdigest()!=receipt['source_sha256']:
                        raise ContinuationError('source history changed during preparation')
                    if any(hashlib.sha256(Path(row['path']).read_bytes()).hexdigest()!=row['sha256'] for row in lineage):
                        raise ContinuationError('source lineage changed during preparation')
                    receipt.update(state='prepared_context',successor_thread_id=successor,successor_path=str(saved))
                    _bind_accounting(receipt)
            except (ValueError, OSError, KeyError, BrokenPipeError) as exc:
                receipt.update(state='uncertain' if receipt['state']=='creating' else 'held',reason=str(exc))
            _save(path,receipt)
            return receipt


def main(argv=None) -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,default=Path(os.environ.get('CODEX_PROFILES_CONFIG','profiles.toml')))
    parser.add_argument('--source',required=True);parser.add_argument('--owner',required=True)
    parser.add_argument('--target',required=True);parser.add_argument('--intent',required=True)
    parser.add_argument('--manifest',type=Path,required=True)
    parser.add_argument('--channel',choices=('stock','modded'),default='modded')
    parser.add_argument('--wake-root',type=Path);parser.add_argument('--objective-id')
    parser.add_argument('--reconcile',help='Exact persisted successor ID to reconcile; never retries the fork.')
    args=parser.parse_args(argv)
    try:
        result=continue_account(load_settings(args.config),args.source,args.owner,args.target,args.intent,args.manifest,
                                channel=args.channel,wake_root=args.wake_root,objective_id=args.objective_id,reconcile=args.reconcile)
        print(json.dumps(result,indent=2));return 0 if result['state']=='prepared_context' else 2
    except (ContinuationError,HistoryError,OSError,ValueError) as exc:
        print(json.dumps({'state':'held','reason':str(exc),'work_authorized':False}));return 2


if __name__=='__main__':raise SystemExit(main())
