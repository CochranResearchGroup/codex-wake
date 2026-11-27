"""Bind one Linux stock Codex background recipient to its owning profile."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import struct
import subprocess
import sys
from uuid import UUID

from .codex_runtime import CodexRuntimeAdapter, submission_failure
from .message_delivery import Message
from .message_handoff import MessageHandoff
from .message_owner import _object, _private
from .native_clock import snapshot
from .native_protocol import native_request
from .process import process_identity
from .records import WakeError
from .runtime_delivery import RuntimeTargetError
from .wake_live_restore import _home_generation, _provider_account_fingerprint
from .wake_mode_runtime import observe_mode_presence, submit_background_turn


_FIELDS = {'peer_id', 'thread', 'cwd', 'home', 'codex', 'app_socket', 'tmux_socket'}


def _digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def _physical(value):
    path = Path(value)
    if not path.is_absolute() or path != path.resolve(strict=True):
        raise ValueError('expected a canonical absolute owner path')
    return path


def _spec(value):
    if (set(value) != _FIELDS or str(UUID(value['thread'])) != value['thread']
            or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}', value['peer_id'])):
        raise ValueError('expected one exact Codex conversation')
    if not _physical(value['cwd']).is_dir() or not _physical(value['codex']).is_file():
        raise ValueError('expected an owner workspace and versioned Codex executable')
    _private(value['home'], directory=True)
    for key in ('app_socket', 'tmux_socket'):
        path = Path(value[key])
        if not path.is_absolute() or '..' in path.parts:
            raise ValueError('expected an explicit absolute socket')
        _private(path.parent, directory=True)
    return value


class Recipient:
    def __init__(self, spec):
        self.spec = _spec(spec)
        self.executable = Path(spec['codex'])
        self.app_socket = Path(spec['app_socket']).resolve(strict=True)
        _private(self.app_socket.parent, directory=True)
        self.image = _digest(self.executable)
        self.home_generation = _home_generation(spec['home'])
        self.generation = None
        self.effect_entered = False
        self.message = None
        self.deadline_state = None
        self.target = dict(transport='native', runtime='codex', thread_id=spec['thread'],
            endpoint='unix://' + str(self.app_socket), codex_cmd=spec['codex'],
            tmux_socket=spec['tmux_socket'], resume_policy='same_thread', startup_policy='background_saved')

    def _connection(self, ws, metadata, *, effect):
        pid, uid, _ = struct.unpack('3i', ws.socket.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
        process = process_identity(pid)
        executable = Path('/proc') / str(pid) / 'exe'
        if (uid != os.geteuid() or not process or metadata.get('codexHome') != self.spec['home']
                or executable.resolve(strict=True) != self.executable
                or _home_generation(self.spec['home']) != self.home_generation):
            return False
        if self.generation is None:
            if _digest(executable) != self.image:
                return False
            self.generation = (pid, process)
        elif (pid, process) != self.generation:
            return False
        if effect:
            self.deadline_state = MessageHandoff._window(self.message, snapshot())
            if self.deadline_state != 'eligible':
                return False
            self.effect_entered = True
        return True

    def request(self, endpoint, codex, method, params, timeout):
        if (endpoint, codex) != (self.target['endpoint'], self.target['codex_cmd']):
            raise ValueError('native endpoint changed')
        reply = native_request(endpoint, codex, method, params, min(timeout, 3),
            verify_connection=lambda ws, metadata: self._connection(ws, metadata, effect=method == 'turn/start'))
        if reply is None:
            raise ValueError('native ownership or deadline changed')
        return reply

    def call(self, method, params):
        return self.request(self.target['endpoint'], self.target['codex_cmd'], method, params, 3)

    def thread(self, target=None):
        selected = self.call('thread/read', {'threadId': self.spec['thread'], 'includeTurns': False})['thread']
        if (selected.get('id'), selected.get('cwd')) != (self.spec['thread'], self.spec['cwd']):
            raise ValueError('saved conversation changed')
        return selected

    def identity(self):
        selected = self.thread()
        provider = selected.get('modelProvider')
        if not provider:
            raise ValueError('original provider is unavailable')
        identity = dict(image=self.image, home_generation=self.home_generation, provider=provider)
        account = self.call('account/read', {'refreshToken': False}).get('account')
        identity['account'] = hashlib.sha256(
            json.dumps(account, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        if provider == 'openai':
            identity['provider_account'] = _provider_account_fingerprint(
                dict(codex_home=self.spec['home'], home_generation=self.home_generation))
        config = Path(self.spec['home']) / 'config.toml'
        if config.exists():
            identity['profile'] = _digest(_private(config))
        return identity, selected['status']['type']

    def run(self, message, identity):
        self.message = message
        if self.identity()[0] != identity:
            return {'status': 'unsent', 'reason': 'offline'}
        window = MessageHandoff._window(message, snapshot())
        if window != 'eligible':
            return {'status': 'unsent', 'reason': 'expired' if window == 'expired' else 'offline'}
        if observe_mode_presence(self.target) != 'background':
            return {'status': 'unsent', 'reason': 'busy'}
        adapter = CodexRuntimeAdapter(read_thread=self.thread, request=self.request,
            run=subprocess.run, project_failure=submission_failure)
        recipient = adapter.resolve(self.target)
        if adapter.observe(recipient).state != 'ready':
            return {'status': 'unsent', 'reason': 'busy'}
        identity_after, state = self.identity()
        if identity_after != identity or state != 'idle' or observe_mode_presence(
                self.target, resumed=True) != 'background':
            return {'status': 'unsent', 'reason': 'offline'}
        result = submit_background_turn(self.request, recipient, message.payload)
        if result.state == 'accepted' and result.receipt_id:
            return {'status': 'submitted', 'receipt_id': result.receipt_id}
        if not self.effect_entered:
            return {'status': 'unsent', 'reason': 'expired' if self.deadline_state == 'expired' else 'offline'}
        return {'status': 'uncertain', 'reason': 'owner_transport_outcome_unverified'}


def _deliver(path, message):
    receipt = dict(id=message.identifier, recipient=message.recipient, expires_at_micros=message.expires_at_micros)
    runtime = None
    try:
        saved = _object(_private(path))
        if (set(saved) != {'version', 'spec', 'identity'} or saved['version'] != 1
                or message.recipient != saved['spec']['thread'] or message.source != 'direct'
                or message.scope != 'peer:' + saved['spec']['peer_id']):
            raise ValueError('message recipient does not match its binding')
        runtime = Recipient(saved['spec'])
        return dict(receipt, **runtime.run(message, saved['identity']))
    except Exception:
        if runtime is not None and runtime.effect_entered:
            return dict(receipt, status='uncertain', reason='owner_transport_outcome_unverified')
        return dict(receipt, status='unsent', reason='offline')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binding', type=Path, required=True)
    verbs = parser.add_subparsers(dest='verb', required=True)
    enroll = verbs.add_parser('enroll')
    enroll.add_argument('--request', type=Path, required=True)
    verbs.add_parser('deliver')
    args = parser.parse_args(argv)
    try:
        if sys.platform != 'linux':
            raise ValueError('native Linux scope required')
        if args.verb == 'enroll':
            _private(args.binding.parent, directory=True)
            runtime = Recipient(_object(_private(args.request)))
            identity, state = runtime.identity()
            if state not in {'idle', 'notLoaded'} or observe_mode_presence(runtime.target) != 'background':
                raise ValueError('idle saved background conversation required')
            fd = os.open(args.binding, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, 'w') as stream:
                json.dump(dict(version=1, spec=runtime.spec, identity=identity), stream, sort_keys=True)
                stream.flush()
                os.fsync(stream.fileno())
            result = dict(status='bound', thread=runtime.spec['thread'])
        else:
            raw = sys.stdin.buffer.read(400001)
            if len(raw) > 400000:
                raise ValueError('message exceeds the owner frame')
            result = _deliver(args.binding, Message(**json.loads(raw)))
        print(json.dumps(result, sort_keys=True))
        return 0
    except (WakeError, RuntimeTargetError, OSError, TypeError, ValueError, KeyError):
        print(json.dumps(dict(status='held', reason='linux_network_binding_unverified')))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
