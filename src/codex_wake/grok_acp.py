"""Bounded ACPv1 JSON-RPC framing on Grok's native local WebSocket server.

The host approves endpoint and transport-secret file. Provider credentials are
never discovered/read. Only existing structured ownership is used; no daemon,
leader, terminal connection, permission grant or alternative route is started.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import time
from urllib.parse import quote,urlsplit

from .managed_inventory import InventoryError


class ACPRefusal(InventoryError):
    """A definitive native JSON-RPC rejection, distinct from lost response."""
    def __init__(self,code,message,native_code=None):
        super().__init__(code,message);self.native_code=native_code


def owned_listener(profile):
    target=profile['target'];pid=int(target['process_pid']);port=urlsplit(profile['endpoint']).port
    directory=Path('/proc')/str(pid)
    inodes=set()
    for path in (directory/'fd').iterdir():
        try:link=os.readlink(path)
        except OSError:continue
        if link.startswith('socket:['):inodes.add(link[8:-1])
    for line in (directory/'net/tcp').read_text().splitlines()[1:]:
        fields=line.split()
        if len(fields)>9 and fields[1]=='0100007F:'+format(port,'04X') and fields[3]=='0A' and fields[9] in inodes:return
    raise InventoryError('stale_target','native ACP listener is not owned by the pinned Grok process')


class GrokACPConnection:
    def __init__(self,profile,*,guard):
        self.profile,self.guard=profile,guard
        self.connection=None;self.deadline=0

    def __enter__(self):
        from websockets.sync.client import connect
        self.guard();owned_listener(self.profile)
        path=Path(self.profile['secret_file'])
        if path.is_symlink() or not path.is_file() or path.stat().st_uid!=os.geteuid() or path.stat().st_mode&0o077 or not 0<path.stat().st_size<=4096:
            raise InventoryError('configuration_unavailable','private Grok transport-secret file required; provider keys are never selected')
        token=path.read_text().strip()
        if not token or any(ord(c)<32 for c in token):raise InventoryError('configuration_unavailable','invalid native transport secret')
        self.deadline=time.monotonic()+self.profile['timeout']
        try:
            self.connection=connect(self.profile['endpoint']+'?server-key='+quote(token,safe=''),proxy=None,
                open_timeout=min(5,self.profile['timeout']),close_timeout=1,compression=None,max_size=1048576)
        except Exception:
            raise InventoryError('native_unavailable','fixed native Grok ACP connection unavailable') from None
        self.guard();owned_listener(self.profile)
        return self

    def __exit__(self,*unused):
        if self.connection is not None:
            try:self.connection.close()
            except Exception:pass

    def call(self,method,params,identifier):
        self.guard()
        if time.monotonic()>=self.deadline:raise TimeoutError('original Grok RPC deadline elapsed')
        message=dict(jsonrpc='2.0',method=method,params=params)
        if method!='session/cancel':message['id']=identifier
        self.connection.send(json.dumps(message,allow_nan=False))
        if method=='session/cancel':return dict(status='requested')
        updates=[];retained_bytes=0;wire_bytes=0;progress_seen=False;truncated=False
        for unused in range(2048):
            remaining=self.deadline-time.monotonic()
            if remaining<=0:raise TimeoutError('original native reply deadline elapsed; no replay')
            raw=self.connection.recv(timeout=remaining);wire_bytes+=len(raw.encode() if isinstance(raw,str) else raw)
            if wire_bytes>4194304:raise InventoryError('capacity','native ACP response exceeds bounded wire capacity')
            value=json.loads(raw)
            if not isinstance(value,dict) or value.get('jsonrpc')!='2.0':raise InventoryError('effect_uncertain','invalid native ACP frame')
            if value.get('id')==identifier and 'method' not in value:
                if 'error' in value:
                    code=(value.get('error') or {}).get('code')
                    if progress_seen:raise InventoryError('effect_uncertain','native error followed correlated progress; prior effects are uncertain')
                    if code==-32000:raise ACPRefusal('native_auth_required','native Grok authentication required; no authentication or provider experiment attempted',code)
                    if code in (-32601,-32602):raise ACPRefusal('unsupported_operation' if code==-32601 else 'invalid_native_argument','native ACP definitively refused the requested method/parameters',code)
                    raise InventoryError('effect_uncertain','native ACP returned an unqualified error; original effect is uncertain')
                result=value.get('result')
                if not isinstance(result,dict):raise InventoryError('effect_uncertain','native ACP reply is not an object')
                if len(json.dumps(result).encode())>65536:raise InventoryError('capacity','original native final reply exceeds retained bound')
                if method=='session/prompt':result=dict(result,_wake_updates=updates,_wake_truncated=truncated)
                return result
            if value.get('method')=='session/update' and method=='session/prompt':
                event=value.get('params',{})
                if event.get('sessionId')==params.get('sessionId'):
                    progress_seen=True
                    update=event.get('update',{})
                    if update.get('sessionUpdate')=='agent_message_chunk':
                        content=update.get('content',{})
                        if content.get('type')=='text' and isinstance(content.get('text'),str):
                            raw_text=content['text'].encode()
                            if len(raw_text)>32768-retained_bytes:truncated=True
                            text=raw_text[:max(0,32768-retained_bytes)].decode(errors='ignore');retained_bytes+=len(text.encode())
                            updates.append(dict(sessionId=event['sessionId'],update=dict(sessionUpdate='agent_message_chunk',content=dict(type='text',text=text))))
            elif 'id' in value and 'method' in value:
                progress_seen=True
                # No client FS/terminal/tool capabilities were advertised. Native
                # approval requests receive cancellation, never an invented grant.
                if value['method']=='session/request_permission':reply=dict(result=dict(outcome=dict(outcome='cancelled')))
                else:reply=dict(error=dict(code=-32601,message='Client capability was not negotiated.'))
                self.connection.send(json.dumps(dict(jsonrpc='2.0',id=value['id'],**reply)))
        raise InventoryError('capacity','native ACP frame-count bound reached')
