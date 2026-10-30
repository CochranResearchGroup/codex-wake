"""Pinned session actions over the existing native owner and operation journal.

The host supplies private profiles. No command, endpoint, home, account, authority
or allowance can be supplied by a flow author. Native thread/turn state remains
native; ControllerRuntime retains admission and uncertain effects.
"""
import hashlib
import json
from pathlib import Path
import time

from .a2a_bus import private_path
from .a2a_identity import RuntimeIdentity
from .controller_auth import AuthError
from .controller_runtime import ControllerRuntime
from .managed_inventory import InventoryError
from .native_protocol import native_request
from .process import process_identity

_ACCOUNT_FIELDS = {'host','environment','provider','account','home','home_generation',
    'configuration_revision','build_channel','build_sha256','build_revision','executable'}


class ControllerFlowSessions:
    def __init__(self, root, *, resolve_build=None, request=native_request, metadata=None):
        self.root = Path(root)
        self.runtime = ControllerRuntime(root)
        self.resolve_build = resolve_build or self._build
        self.request = request
        self.metadata = metadata or self._metadata

    def _build(self, target):
        from .build_commands import owner_from_root
        rows = owner_from_root(self.root).execute('builds.list', {'account': target['account']})['builds']
        matches = [row['target'] for row in rows if row['name'] == target['build_channel'] and 'status' not in row]
        if len(matches) != 1:
            raise InventoryError('stale_target', 'profile immutable account build is unavailable')
        return matches[0]

    @staticmethod
    def _metadata(profile):
        from .shared_app_server import SharedAppServerReader
        with SharedAppServerReader(profile['endpoint'], timeout=5) as reader:
            import socket
            import struct
            peer = reader.connection.socket.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize('3i'))
            pid, uid, gid = struct.unpack('3i', peer)
            return dict(reader.server_metadata, peer_pid=pid)

    def profile(self, name):
        path = self.root / 'controller-flow-sessions.json'
        private_path(path)
        if path.stat().st_size > 1048576:
            raise InventoryError('configuration_unavailable', 'bounded private session profiles required')
        try:
            config = json.loads(path.read_text())
            profile = config['profiles'][name]
            if config['version'] != 1 or not isinstance(profile, dict):
                raise ValueError()
            required = {'target','endpoint','process','modes','cwd','methods','native_provider'}
            if set(profile) != required or not _ACCOUNT_FIELDS <= profile['target'].keys():
                raise ValueError()
            if not profile['endpoint'].startswith('unix:///') or not Path(profile['cwd']).is_dir():
                raise ValueError()
            if not isinstance(profile['modes'], list) or set(profile['modes']) - {'new_session','sequential'}:
                raise ValueError()
            if not {'thread/start','turn/start','thread/read','turn/interrupt'} <= set(profile['methods']):
                raise ValueError()
            observed = self.resolve_build(profile['target'])
            if observed != profile['target']:
                raise InventoryError('stale_target', 'profile account/build generation changed')
            expected = profile['process']
            observed_process = process_identity(expected['pid'])
            if not observed_process or (observed_process['start_time_ticks'],observed_process['boot_id']) != (expected['start_ticks'],expected['boot_id']):
                raise InventoryError('stale_target', 'native process birth changed')
            from .controller_health import _image_hash
            if _image_hash(expected['pid']) != observed['build_sha256']:
                raise InventoryError('stale_target', 'native process image differs from pinned build')
            profile = dict(profile)
            profile['revision'] = hashlib.sha256(json.dumps(config['profiles'][name],sort_keys=True).encode()).hexdigest()
            return profile
        except InventoryError:
            raise
        except (OSError,ValueError,TypeError,KeyError):
            raise InventoryError('configuration_unavailable', 'qualified private native session profile required') from None

    def target(self, name):
        profile = self.profile(name)
        namespace = RuntimeIdentity.from_metadata(dict(id='profile',cwd=profile['cwd'],modelProvider=profile['native_provider']),
            dict(codexHome=profile['target']['home'])).namespace
        return dict(profile['target'], runtime='codex', namespace=namespace, generation=profile['revision'], process=profile['process'])

    def _context(self, actor, name, target, authorize, capability):
        profile = self.profile(name)
        base = self.target(name)
        if {key:value for key,value in target.items() if key != 'conversation_id'} != base:
            raise InventoryError('stale_target', 'exact account/build/profile/process target required')
        if not any(_ACCOUNT_FIELDS <= scope.keys() and all(target.get(key) == value for key,value in scope.items()) for scope in actor.targets):
            raise AuthError('insufficient_scope')
        self.runtime.check_authority(actor,target,capability,authorize=authorize)
        metadata = self.metadata(profile)
        if metadata.get('codexHome') != profile['target']['home'] or metadata.get('peer_pid') != profile['process']['pid']:
            raise InventoryError('stale_target', 'native endpoint belongs to another account home')
        return profile

    def _identity(self, profile, thread):
        if not isinstance(thread,dict) or thread.get('cwd') != profile['cwd'] or thread.get('modelProvider') != profile['native_provider']:
            raise InventoryError('native_identity_unavailable', 'native conversation provenance did not match the profile')
        return RuntimeIdentity.from_metadata(thread,dict(codexHome=profile['target']['home']))

    def execute(self, actor, operation, arguments, *, authorize):
        if operation in ('sessions.wait','sessions.cancel'):
            return self._existing(actor,operation,arguments,authorize)
        fields = {'sessions.create':{'profile','expected_target','_request'},
            'sessions.prompt':{'profile','expected_target','prompt','_request'},
            'sessions.capabilities':{'profile','expected_target'}}
        if operation not in fields or not isinstance(arguments,dict) or set(arguments) != fields[operation]:
            raise InventoryError('invalid_argument','exact structured session arguments required')
        name,target = arguments['profile'],arguments['expected_target']
        if not isinstance(target,dict):
            raise InventoryError('invalid_argument','pinned session target required')
        capability = 'observe' if operation == 'sessions.capabilities' else 'control'
        profile = self._context(actor,name,target,authorize,capability)
        if operation == 'sessions.capabilities':
            return dict(schema_version=1,operation=operation,status='completed',result=dict(target=target,modes=profile['modes']))
        if operation == 'sessions.create' and ('new_session' not in profile['modes'] or 'conversation_id' in target):
            raise InventoryError('unsupported_session_mode','new sessions unavailable for this profile')
        if operation == 'sessions.prompt' and (not target.get('conversation_id') or not isinstance(arguments['prompt'],str)
                or not 0 < len(arguments['prompt'].encode()) <= 32768):
            raise InventoryError('invalid_argument','existing exact conversation and bounded prompt required')
        def guard():
            self._context(actor,name,target,authorize,'control')
            return authorize()
        def dispatch(unused,payload):
            guard()
            if operation == 'sessions.create':
                thread = self.request(profile['endpoint'],profile['target']['executable'],'thread/start',
                    dict(cwd=profile['cwd'],ephemeral=False),5)['thread']
                native = self._identity(profile,thread)
                return dict(target=dict(target,conversation_id=native.thread_id),account_identity='unverified',
                    authority='inherited',allocation_created=False)
            thread = self.request(profile['endpoint'],profile['target']['executable'],'thread/read',
                dict(threadId=target['conversation_id'],includeTurns=False),5)['thread']
            self._identity(profile,thread)
            guard()
            turn = self.request(profile['endpoint'],profile['target']['executable'],'turn/start',
                dict(threadId=target['conversation_id'],input=[dict(type='text',text=payload['prompt'])],cwd=profile['cwd']),5)['turn']
            if not isinstance(turn.get('id'),str) or not turn['id']:
                raise InventoryError('uncertain_effect','native turn ID unavailable after submission')
            return dict(target=target,turn_id=turn['id'],profile=name,profile_revision=profile['revision'],
                status='submitted',answer=None,allocation_created=False)
        from .wake_control import delivery_guard
        with delivery_guard(self.root):
            return self.runtime.execute(actor,operation,arguments,authorize=guard,dispatch=dispatch)

    def _existing(self,actor,operation,arguments,authorize):
        allowed = {'operation_id','timeout'} if operation == 'sessions.wait' else {'operation_id'}
        if not isinstance(arguments,dict) or set(arguments)-allowed or 'operation_id' not in arguments:
            raise InventoryError('invalid_argument','owned native operation handle required')
        record = self.runtime.operation(actor,'operations.result',dict(operation_id=arguments['operation_id']),authorize=authorize)['result']['operation']
        if record['operation'] != 'sessions.prompt' or not isinstance(record.get('result'),dict):
            raise InventoryError('unsupported_operation','retained session prompt required')
        result = record['result']
        target,name = result['target'],result['profile']
        profile = self._context(actor,name,target,authorize,'control' if operation == 'sessions.cancel' else 'observe')
        if operation == 'sessions.cancel':
            self.request(profile['endpoint'],profile['target']['executable'],'turn/interrupt',
                dict(threadId=target['conversation_id'],turnId=result['turn_id']),5)
            record.update(cancellation='requested')
            return self.runtime.envelope(operation,record)
        timeout = arguments.get('timeout',0)
        if type(timeout) not in (int,float) or not 0 <= timeout <= 30:
            raise InventoryError('invalid_argument','bounded wait timeout required')
        deadline = time.monotonic()+timeout
        while True:
            self._context(actor,name,target,authorize,'observe')
            thread = self.request(profile['endpoint'],profile['target']['executable'],'thread/read',
                dict(threadId=target['conversation_id'],includeTurns=True),5)['thread']
            self._identity(profile,thread)
            turns = [turn for turn in thread.get('turns',[]) if turn.get('id') == result['turn_id']]
            if len(turns) == 1 and turns[0].get('status') in ('completed','failed','interrupted'):
                turn = turns[0]
                texts = [item['text'] for item in turn.get('items',[]) if item.get('type') == 'agentMessage' and isinstance(item.get('text'),str)]
                record.update(execution='completed' if turn['status']=='completed' else 'cancelled' if turn['status']=='interrupted' else 'failed',
                    answer=dict(text='\n'.join(texts),source='native_turn',turn_id=result['turn_id']),phase='terminal')
                return self.runtime.envelope(operation,record,wait=dict(status='completed',ends_work=False))
            if time.monotonic() >= deadline:
                record.update(execution='running',phase='pending',answer=None)
                return self.runtime.envelope(operation,record,wait=dict(status='timeout',ends_work=False))
            time.sleep(min(.05,max(0,deadline-time.monotonic())))
