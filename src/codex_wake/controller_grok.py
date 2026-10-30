"""Negotiated Grok ACPv1 control on an existing host-approved structured owner.

No terminal adapter, native credential discovery, fallback executor or native
result-query extension is used. Original JSON-RPC final replies and correlated
assistant updates are retained by ControllerRuntime before caller delivery.
A lost native connection remains uncertain and is never resubmitted.
"""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
from urllib.parse import urlsplit

from .controller_auth import AuthError
from .controller_health import _image_hash,_process_matches
from .controller_runtime import ControllerRuntime,encoded,bounded_id
from .managed_inventory import InventoryError

BASE_FIELDS=frozenset(('host','environment','runtime','provider','account','home','namespace','build_sha256',
    'backend_id','channel','connection_generation','process_pid','process_start_ticks','process_boot_id','configuration_revision'))


class ControllerGrok:
    def __init__(self,root,*,request=None):
        self.root,self.request=Path(root),request
        self.runtime=ControllerRuntime(root,adapter=self)

    def profile(self,name):
        bounded_id(name);path=self.root/'controller-grok.json'
        if path.is_symlink() or not path.is_file() or path.stat().st_uid!=os.geteuid() or path.stat().st_mode&0o077 or path.stat().st_size>1048576:
            raise InventoryError('configuration_unavailable','private bounded Grok structured profiles required')
        try:value=json.loads(path.read_text())
        except (ValueError,OSError):raise InventoryError('configuration_unavailable','Grok profile registry unavailable') from None
        if value.get('version')!=1 or not isinstance(value.get('profiles'),dict) or len(value['profiles'])>256:raise InventoryError('configuration_unavailable','unsupported Grok registry version/capacity')
        profile=value['profiles'].get(name)
        if not isinstance(profile,dict) or set(profile)!={'target','endpoint','secret_file','cwd','agent_version','timeout'}:
            raise InventoryError('unsupported_target','Grok structured profile unavailable')
        target=profile['target']
        if not isinstance(target,dict) or not BASE_FIELDS<=target.keys() or any(not isinstance(v,str) or not v or len(v)>4096 for v in target.values()) or target['runtime']!='grok' or target['provider']!='grok' or target['channel']!='acp-websocket':
            raise InventoryError('configuration_unavailable','complete host-approved Grok identity required')
        url=urlsplit(profile['endpoint'])
        if url.scheme!='ws' or url.hostname!='127.0.0.1' or url.path!='/ws' or url.query or url.fragment or url.username or not url.port:
            raise InventoryError('unsupported_operation','existing local native ACP WebSocket endpoint required')
        if not Path(profile['cwd']).is_absolute() or not Path(profile['cwd']).is_dir() or type(profile['timeout']) not in (int,float) or not 0<profile['timeout']<=30:
            raise InventoryError('configuration_unavailable','bounded existing native working-directory/RPC profile required')
        return dict(profile,_sha256=hashlib.sha256(encoded(profile).encode()).hexdigest())

    def _pin(self,profile):
        target=profile['target']
        try:pid=int(target['process_pid'])
        except (ValueError,TypeError):raise InventoryError('stale_target','native process identity unavailable') from None
        raw=dict(process=dict(pid=pid,start_ticks=target['process_start_ticks'],boot_id=target['process_boot_id']))
        if not _process_matches(raw) or (Path('/proc')/str(pid)).stat().st_uid!=os.geteuid() or _image_hash(pid)!=target['build_sha256']:
            raise InventoryError('stale_target','Grok native process generation or immutable image changed')

    def _context(self,actor,args,capability,authorize,*,conversation=False):
        profile=self.profile(args.get('profile'));target=args.get('expected_target')
        expected=dict(profile['target'])
        if conversation:
            if not isinstance(target,dict):raise InventoryError('invalid_argument','pinned native conversation required')
            bounded_id(target.get('conversation_id'));expected['conversation_id']=target['conversation_id']
        if target!=expected:raise InventoryError('stale_target','exact Grok account/build/process/agent-instance target required')
        if not any(BASE_FIELDS<=scope.keys() and all(target.get(k)==v for k,v in scope.items()) for scope in actor.targets):raise AuthError('insufficient_scope')
        self.runtime.check_authority(actor,target,capability,authorize=authorize)
        self._pin(profile)
        return profile

    @contextmanager
    def _connection(self,profile,guard):
        if self.request is not None:
            class Connection:
                def call(unused,method,params,identifier):
                    guard();value=self.request(profile,method,params,identifier,guard);guard();return value
            yield Connection()
        else:
            from .grok_acp import GrokACPConnection
            with GrokACPConnection(profile,guard=guard) as connection:yield connection

    @staticmethod
    def _negotiation(connection,profile):
        value=connection.call('initialize',dict(protocolVersion=1,clientCapabilities={},clientInfo=dict(name='codex_wake_controller',version='0.22.0.dev2')),'wake_initialize')
        meta=value.get('_meta',{})
        if value.get('protocolVersion')!=1 or not isinstance(value.get('agentCapabilities'),dict):raise InventoryError('unsupported_operation','Grok ACPv1 was not negotiated')
        target=profile['target']
        if meta.get('agentVersion')!=profile['agent_version'] or meta.get('agentId')!=target['backend_id'] or meta.get('agentInstanceId')!=target['connection_generation'] or meta.get('currentWorkingDirectory')!=profile['cwd']:
            raise InventoryError('stale_target','Grok native agent/instance/version/workspace changed')
        return value

    @staticmethod
    def _capabilities(value):
        agent=value['agentCapabilities']
        supported=lambda reason:dict(status='supported',reason=reason)
        unsupported=lambda reason:dict(status='unsupported',reason=reason)
        return dict(protocol_version=1,capabilities=dict(create=supported('ACPv1 session/new'),prompt=supported('bounded synchronous ACPv1 session/prompt'),
            load=supported('negotiated loadSession') if agent.get('loadSession') is True else unsupported('loadSession not negotiated'),
            cancellation=dict(status='requested_only',reason='ACPv1 notification; confirmation requires original cancelled final reply'),
            retained_results=supported('original controller-recorded final reply only'),
            native_result_lookup=unsupported('ACPv1 exposes no negotiated original-request result query'),
            fork=unsupported('no qualified common-prefix fork contract negotiated'),checkpoint=unsupported('no qualified immutable checkpoint contract negotiated'),
            exact_tui_health=unsupported('Grok ACP metadata is not exact controlling TUI-loop evidence'),
            exact_metering=unsupported('no qualified exact token/time enforcement'),observation_tool_isolation=unsupported('not negotiated'),parallel_sessions=unsupported('not qualified')),
            authority=dict(account_identity='host-approved process/home binding; native account ownership unverified',provider_credentials='native_store_only',client_capabilities='none'))

    def execute(self,actor,operation,args,*,authorize):
        allowed={**{'grok.'+verb:{'profile','expected_target'} for verb in ('capabilities','health','checkpoint')},
            **{'grok.'+verb:{'profile','expected_target','_request'} for verb in ('create','load','fork')},
            'grok.prompt':{'profile','expected_target','_request','prompt'},'grok.wait':{'operation_id','timeout'},'grok.cancel':{'operation_id'}}
        if operation not in allowed or not isinstance(args,dict) or set(args)-allowed[operation]:raise InventoryError('invalid_argument','unsupported Grok controller operation/arguments')
        if operation in ('grok.wait','grok.cancel'):
            return self.runtime.operation(actor,'operations.wait' if operation=='grok.wait' else 'operations.cancel',args,authorize=authorize,expected_operation='grok.prompt')
        capability='observe' if operation in ('grok.capabilities','grok.health','grok.checkpoint') else 'control'
        profile=self._context(actor,args,capability,authorize,conversation=operation in ('grok.prompt','grok.load','grok.fork','grok.checkpoint') or operation in ('grok.capabilities','grok.health') and isinstance(args.get('expected_target'),dict) and 'conversation_id' in args['expected_target'])
        def guard():
            current=self._context(actor,args,capability,authorize,conversation=operation in ('grok.prompt','grok.load','grok.fork','grok.checkpoint') or operation in ('grok.capabilities','grok.health') and isinstance(args.get('expected_target'),dict) and 'conversation_id' in args['expected_target'])
            if current['_sha256']!=profile['_sha256']:raise InventoryError('stale_target','Grok host profile changed before native I/O')
            return actor
        with self._connection(profile,guard) as connection:
            negotiation=self._negotiation(connection,profile)
            if operation=='grok.capabilities':return dict(schema_version=1,operation=operation,status='completed',result=self._capabilities(negotiation))
            if operation=='grok.health':return dict(schema_version=1,operation=operation,status='completed',result=dict(status='unsupported',responsive=False,reason='structured ACP metadata cannot establish exact controlling TUI-loop health',grants_recovery=False))
            if operation in ('grok.fork','grok.checkpoint'):raise InventoryError('unsupported_operation','Grok immutable common-prefix fork/checkpoint capability is not qualified')
            if operation=='grok.load' and negotiation['agentCapabilities'].get('loadSession') is not True:raise InventoryError('unsupported_operation','Grok loadSession capability was not negotiated')
            if operation=='grok.prompt' and (not isinstance(args.get('prompt'),str) or not 0<len(args['prompt'].encode())<=32768):raise InventoryError('invalid_argument','bounded text prompt required')
            prepared=dict(args,_profile_sha256=profile['_sha256'])
            def dispatch(unused,payload):
                guard();identifier=args['_request']['operation_id']
                if operation=='grok.create':
                    value=connection.call('session/new',dict(cwd=profile['cwd'],mcpServers=[]),identifier)
                    bounded_id(value.get('sessionId'))
                    return dict(session_id=value['sessionId'],target=dict(profile['target'],conversation_id=value['sessionId']),native_result=value,allocation_created=False,authority='inherited')
                session=args['expected_target']['conversation_id']
                if operation=='grok.load':
                    value=connection.call('session/load',dict(sessionId=session,cwd=profile['cwd'],mcpServers=[]),identifier)
                    return dict(session_id=session,native_result=value,history_replay='native ACP only')
                value=connection.call('session/prompt',dict(sessionId=session,prompt=[dict(type='text',text=args['prompt'])]),identifier)
                text=[];size=0;truncated=False
                for item in value.pop('_wake_updates',[]):
                    if item.get('sessionId')!=session:continue
                    update=item.get('update',{});content=update.get('content',{})
                    if update.get('sessionUpdate')!='agent_message_chunk' or content.get('type')!='text' or not isinstance(content.get('text'),str):continue
                    raw=content['text'].encode();remaining=32768-size
                    if len(raw)>remaining:truncated=True
                    chunk=raw[:max(0,remaining)].decode(errors='ignore');text.append(chunk);size+=len(chunk.encode())
                stop=value.get('stopReason')
                if stop not in ('end_turn','max_tokens','max_turn_requests','refusal','cancelled'):raise InventoryError('effect_uncertain','native prompt final stop reason is not qualified')
                return dict(session_id=session,text=''.join(text),stop_reason=stop,native_result=value,output_truncated=truncated,
                    native_request_id=identifier,peer_content_trust='untrusted',allocation_created=False,authority='inherited',execution='cancelled' if stop=='cancelled' else 'completed')
            return self.runtime.execute(actor,operation,prepared,authorize=authorize,dispatch=dispatch)

    def observe_native_owned(self,record):
        # ACP has no negotiated original-request result query. The submitting
        # connection alone may retain its original final reply in the journal.
        return record

    def cancel_native_owned(self,record):
        if record.get('operation')!='grok.prompt':raise InventoryError('unsupported_operation','original operation belongs to another owner')
        payload=record['payload'];profile=self.profile(payload['profile'])
        if payload.get('_profile_sha256')!=profile['_sha256'] or record['target']!=payload['expected_target'] or {k:v for k,v in record['target'].items() if k!='conversation_id'}!=profile['target']:
            raise InventoryError('stale_target','original Grok prompt profile/target changed')
        def guard():
            current=self.profile(payload['profile'])
            if current['_sha256']!=profile['_sha256']:raise InventoryError('stale_target','original Grok profile changed')
            self._pin(current)
        with self._connection(profile,guard) as connection:
            self._negotiation(connection,profile)
            connection.call('session/cancel',dict(sessionId=record['target']['conversation_id']),'wake_cancel_original')
        original=self.runtime._load(record['operation_id'])
        if original['phase']=='terminal' and (original.get('result') or {}).get('stop_reason')=='cancelled':return 'confirmed'
        return 'requested'
