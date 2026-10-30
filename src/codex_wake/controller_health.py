"""Read-only exact-TUI-loop challenges over Wake's existing native RPC bridge.

Listener/daemon metadata is never positive evidence. Only the native TUI event
loop can originate the acknowledged frame qualified here; immutable package and
process generation checks bind it to the host-approved controlling TUI.
"""
from __future__ import annotations

from collections import OrderedDict
import hashlib
import json
import os
from pathlib import Path
import threading
import sys
import time
from uuid import uuid4
from websockets.exceptions import WebSocketException

from .native_protocol import native_request, NativeCapabilityUnavailable
from .process import process_identity
from .managed_inventory import InventoryError
from .records import WakeError

_NATIVE_FIELDS = {'conversation_id','home','provider','backend_id','channel','process','connection_generation'}
_TARGET_FIELDS = _NATIVE_FIELDS | {'host','environment','runtime','namespace','build_sha256'}
_SLOTS = threading.BoundedSemaphore(8)
_HASHES = OrderedDict()
_HASH_LOCK = threading.Lock()


def _image_hash(pid):
    path = Path('/proc') / str(pid) / 'exe'
    info = path.stat()
    key = (info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns,info.st_ctime_ns)
    with _HASH_LOCK:
        if key in _HASHES:
            _HASHES.move_to_end(key)
            return _HASHES[key]
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):digest.update(block)
    with _HASH_LOCK:
        _HASHES[key] = digest.hexdigest()
        while len(_HASHES)>64:_HASHES.popitem(last=False)
    return digest.hexdigest()


def _process_matches(target):
    expected=target.get('process')
    if not isinstance(expected,dict) or set(expected)!={'pid','start_ticks','boot_id'} or type(expected['pid']) is not int or expected['pid']<=0:return False
    observed=process_identity(expected['pid'])
    return bool(observed and str(observed.get('start_time_ticks'))==str(expected['start_ticks']) and observed.get('boot_id')==expected['boot_id'])


class ControllerHealth:
    def __init__(self,root,*,request=native_request):
        self.root,self.request=Path(root),request

    def bindings(self):
        path=self.root/'controller-health.json'
        if path.is_symlink() or not path.is_file() or path.stat().st_uid != os.geteuid() or path.stat().st_mode & 0o077 or path.stat().st_size > 1048576:
            raise InventoryError('configuration_unavailable','private host health bindings required')
        try:value=json.loads(path.read_text())
        except (OSError,ValueError):raise InventoryError('configuration_unavailable','invalid private health registry') from None
        if value.get('version')!=1 or not isinstance(value.get('bindings'),list) or len(value['bindings'])>256:
            raise InventoryError('configuration_unavailable','unsupported bounded health binding registry')
        if any(not isinstance(row,dict) or not isinstance(row.get('target'),dict) for row in value['bindings']):
            raise InventoryError('configuration_unavailable','invalid private health bindings')
        return value['bindings']

    def execute(self,operation,arguments):
        if operation!='health.observe':raise InventoryError('unsupported_operation','unsupported health operation')
        if not isinstance(arguments,dict) or set(arguments)-{'expected_target','timeout'}:
            raise InventoryError('invalid_argument','health observation requires an exact pinned target and bounded timeout')
        target,timeout=arguments.get('expected_target'),arguments.get('timeout',1)
        if not isinstance(target,dict) or set(target)!=_TARGET_FIELDS or type(timeout) not in (int,float) or not .05<=timeout<=5:
            raise InventoryError('invalid_argument','complete native health identity and timeout0.05..5 seconds required')
        if any(not isinstance(target[key],str) or not target[key] or len(target[key])>4096 for key in _TARGET_FIELDS-{'process'}):
            raise InventoryError('invalid_argument','health identity fields must be bounded nonempty strings')
        observation=dict(status='unknown',responsive=False,evidence='none',observed_at=time.time(),reason='unqualified')
        result=dict(target=target,observation=observation,grants_recovery=False,application_effects=False)
        def unknown(reason,status='unknown'):
            observation.update(reason=reason,status=status)
            return result
        matches=[row for row in self.bindings() if row.get('target')==target]
        if len(matches)!=1:return unknown('stale_or_ambiguous_binding')
        binding=matches[0]
        if target['runtime']!='codex' or sys.platform!='linux':return unknown('native_health_unsupported','unsupported')
        endpoint,command=binding.get('endpoint'),binding.get('codex_cmd')
        if not isinstance(endpoint,str) or not endpoint.startswith('unix:///') or not isinstance(command,list) or not command or any(not isinstance(arg,str) for arg in command):
            return unknown('native_health_binding_unavailable','unsupported')
        if not _SLOTS.acquire(blocking=False):return unknown('health_request_capacity')
        started=time.monotonic();deadline=started+timeout
        try:
            if not _process_matches(target):return unknown('stale_process_generation')
            if _image_hash(target['process']['pid'])!=target['build_sha256']:return unknown('native_build_mismatch')
            challenge=uuid4().hex+uuid4().hex
            remaining=deadline-time.monotonic()
            if remaining<=0:return unknown('challenge_deadline')
            native_binding=dict(home=target['home'],provider=target['provider'],backendId=target['backend_id'],channel=target['channel'],pid=target['process']['pid'],startTicks=str(target['process']['start_ticks']),bootId=target['process']['boot_id'],connectionGeneration=target['connection_generation'])
            frame=self.request(endpoint,command,'tui/health/probe',dict(binding=native_binding,threadId=target['conversation_id'],challenge=challenge,timeoutMs=max(50,int(remaining*1000))),remaining)
            if time.monotonic()>deadline:return unknown('challenge_deadline')
            if not isinstance(frame,dict):return unknown('invalid_native_frame')
            body=frame
            if not isinstance(body,dict) or len(json.dumps(body).encode())>16384:return unknown('incomplete_native_evidence')
            if body.get('state')!='responsive':return unknown(body.get('reason','native_loop_unobserved'))
            if body.get('evidence')!='tui_main_loop_ack' or body.get('challenge')!=challenge:
                return unknown('not_exact_tui_loop_evidence')
            if body.get('binding')!=native_binding or body.get('threadId')!=target['conversation_id']:return unknown('wrong_native_target')
            namespace=hashlib.sha256(json.dumps([str(Path(target['home']).resolve()),target['provider']],separators=(',',':')).encode()).hexdigest()
            if target['namespace']!='codex:'+namespace:return unknown('wrong_native_account_namespace')
            tid=body.get('loopTid')
            if type(tid) is not int or tid<=0 or not (Path('/proc')/str(target['process']['pid'])/'task'/str(tid)).is_dir():return unknown('wrong_native_loop_thread')
            if not _process_matches(target):return unknown('replaced_process_during_challenge')
            observation.update(status='responsive',responsive=True,evidence='tui_main_loop_ack',reason=None,
                challenge=challenge,latency_seconds=time.monotonic()-started,loop_tid=tid)
            return result
        except NativeCapabilityUnavailable:return unknown('native_health_capability_unavailable','unsupported')
        except (ValueError,OSError,TimeoutError,WakeError,WebSocketException):return unknown('native_loop_unobserved')
        finally:_SLOTS.release()
