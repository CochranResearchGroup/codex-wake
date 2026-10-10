"""Exact opt-in owning-client delivery for journal-fenced mailbox notifications.

Bindings explicitly select either the opt-in owning client or the existing tmux
wake transport. An explicitly authorized original notification may use native
delivery for the same saved recipient after its bound Byobu client is closed.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from contextlib import nullcontext
import os
from pathlib import Path
import socket
import stat
import struct
import time

from .a2a_bus import private_path
from .a2a_identity import BusError, RuntimeIdentity
from .a2a_mailbox import encoded
from .a2a_scheduler import MailScheduler
from .process import process_start_time_ticks, boot_id_value

MAX_FRAME = 8192


@dataclass(frozen=True)
class ClientBinding:
    namespace: str
    thread_id: str
    root: str
    socket_path: str
    pid: int
    process_start_ticks: int
    boot_id: str
    generation: str

    transport = "owning_client_v1"

    @property
    def key(self):
        return encoded([self.namespace, self.thread_id])

    def validate(self):
        if (type(self.pid) is not int or self.pid <= 0
                or type(self.process_start_ticks) is not int or self.process_start_ticks <= 0
                or not all(type(x) is str and x for x in
                    (self.namespace, self.thread_id, self.root, self.socket_path, self.boot_id, self.generation))
                or len(encoded(asdict(self)).encode()) > MAX_FRAME):
            raise BusError('binding_invalid', 'invalid exact client binding')
        for value in (self.root, self.socket_path):
            path = Path(value)
            if not path.is_absolute() or path != path.resolve():
                raise BusError('binding_invalid', 'client paths must be absolute and canonical')
        if self.boot_id != boot_id_value() or self.process_start_ticks != process_start_time_ticks(self.pid):
            raise BusError('client_offline', 'bound client process generation is no longer live')
        _socket_path(Path(self.socket_path))

    def request(self, request, *, effect=False):
        entered_io = False
        try:
            self.validate()
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as stream:
                stream.settimeout(18)
                stream.connect(self.socket_path)
                pid, uid, _ = struct.unpack('3i', stream.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
                if pid != self.pid or uid != os.geteuid():
                    raise BusError('binding_invalid', 'client socket peer is not the bound process')
                # Recheck PID generation after connection, before any effectful bytes.
                self.validate()
                raw = (encoded(request) + '\n').encode()
                if len(raw) > MAX_FRAME:
                    raise BusError('binding_invalid', 'notification exceeds protocol bound')
                entered_io = True
                stream.sendall(raw)
                reply = bytearray()
                while b'\n' not in reply and len(reply) <= MAX_FRAME:
                    part = stream.recv(min(1024, MAX_FRAME + 1 - len(reply)))
                    if not part:
                        raise ValueError('incomplete client response')
                    reply.extend(part)
                if len(reply) > MAX_FRAME or not reply.endswith(b'\n'):
                    raise ValueError('invalid client response framing')
                result = json.loads(reply, object_pairs_hook=_unique)
                if (type(result) is not dict or result.get('protocol') != 1
                        or result.get('pid') != self.pid or result.get('generation') != self.generation):
                    raise ValueError('client response generation mismatch')
                return result
        except (OSError, ValueError, TypeError, BusError):
            if effect:
                return dict(status='uncertain' if entered_io else 'unsent',
                            reason='client_response_unqualified' if entered_io else 'pre_io_failure')
            raise BusError('client_offline', 'bound client response is unavailable') from None

    def probe(self):
        result = self.request(dict(action='probe'))
        if result.get('identity') != dict(thread_id=self.thread_id, root=self.root, namespace=self.namespace):
            return dict(status='deferred', reason='identity_changed')
        if result.get('idle_only_method') != 'turn/startIfIdle':
            return dict(status='deferred', reason='capability_unavailable')
        if result.get('status') not in ('ready', 'deferred'):
            raise BusError('binding_invalid', 'invalid client eligibility response')
        return result

    def deliver(self, claim, job, bus_root):
        result = self.request(dict(action='deliver', request_id=claim['attempt_id'],
            generation=self.generation, thread_id=self.thread_id, root=self.root, namespace=self.namespace,
            bus_root=str(bus_root), message_id=job['message_id'], expires_at=job['expires_at']), effect=True)
        if result.get('status') in ('submitted', 'unsent') and result.get('reason') != 'pre_io_failure':
            if result.get('identity') != dict(thread_id=self.thread_id, root=self.root, namespace=self.namespace):
                return dict(status='uncertain', reason='client_identity_mismatch')
        if result.get('status') == 'submitted' and (
                result.get('request_id') != claim['attempt_id']
                or type(result.get('receipt_id')) is not str or not result['receipt_id']):
            return dict(status='uncertain', reason='missing_exact_transport_receipt')
        return result


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate protocol member')
        result[key] = value
    return result


def _socket_path(path):
    private_path(path.parent, directory=True)
    info = path.lstat()
    if (not stat.S_ISSOCK(info.st_mode) or info.st_uid != os.geteuid()
            or stat.S_IMODE(info.st_mode) != 0o600):
        raise BusError('binding_invalid', 'client socket must be owned and private')


def load_bindings(path):
    path = Path(path)
    if path != path.resolve():
        raise BusError('binding_invalid', 'binding configuration must be canonical')
    private_path(path)
    with path.open('rb') as stream:
        raw = stream.read(65537)
    try:
        value = json.loads(raw, object_pairs_hook=_unique)
        if (len(raw) > 65536 or type(value) is not dict or set(value) != {'schema_version', 'bindings'}
                or type(value['schema_version']) is not int or value['schema_version'] != 1 or type(value['bindings']) is not list
                or not 1 <= len(value['bindings']) <= 100):
            raise ValueError('invalid configuration')
        bindings = []
        for row in value['bindings']:
            row = dict(row)
            transport = row.pop('transport', 'owning_client_v1')
            if transport == 'tmux_notification_v1':
                from .a2a_tmux_delivery import TmuxBinding
                bindings.append(TmuxBinding(**row))
            elif transport == 'owning_client_v1':
                bindings.append(ClientBinding(**row))
            else:
                raise ValueError('unsupported binding transport')
        keys = [row.key for row in bindings]
        sockets = [getattr(row, "socket_path", None) or (row.tmux_socket, row.pid, row.process_start_ticks) for row in bindings]
        if len(set(keys)) != len(keys) or len(set(sockets)) != len(sockets):
            raise ValueError('ambiguous binding')
        return {row.key: row for row in bindings}
    except (ValueError, TypeError, KeyError):
        raise BusError('binding_invalid', 'invalid or ambiguous binding configuration') from None


def bind_client(path, socket_path, identity: RuntimeIdentity):
    """Bind one current client, without enrollment, turn start or automatic discovery."""
    path, socket_path = Path(path), Path(socket_path)
    if not path.is_absolute() or path != path.resolve() or socket_path != socket_path.resolve():
        raise BusError('binding_invalid', 'binding paths must be canonical and absolute')
    private_path(path.parent, directory=True)
    _socket_path(socket_path)
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as stream:
        stream.settimeout(5)
        stream.connect(str(socket_path))
        pid, uid, _ = struct.unpack('3i', stream.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
        if uid != os.geteuid():
            raise BusError('binding_invalid', 'client belongs to another user')
        stream.sendall(b'{"action":"probe"}\n')
        with stream.makefile('rb') as reader:
            raw = reader.readline(MAX_FRAME + 1)
    try:
        reply = json.loads(raw, object_pairs_hook=_unique)
        if (len(raw) > MAX_FRAME or not raw.endswith(b'\n') or reply.get('pid') != pid
                or reply.get('protocol') != 1 or reply.get('idle_only_method') != 'turn/startIfIdle'
                or reply.get('identity') != dict(thread_id=identity.thread_id, root=identity.cwd, namespace=identity.namespace)
                or reply.get('status') not in ('ready', 'deferred')):
            raise ValueError('client identity mismatch')
        binding = ClientBinding(identity.namespace, identity.thread_id, identity.cwd,
            str(socket_path), pid, process_start_time_ticks(pid), boot_id_value(), reply['generation'])
        binding.validate()
    except (ValueError, TypeError, KeyError):
        raise BusError('binding_invalid', 'client did not attest exact runtime identity') from None
    bindings = load_bindings(path) if path.exists() or path.is_symlink() else {}
    if any(getattr(row, "socket_path", None) == str(socket_path) and row.key != binding.key for row in bindings.values()):
        raise BusError('binding_invalid', 'client socket already belongs to another thread')
    if binding.key not in bindings and len(bindings) >= 100:
        raise BusError('binding_invalid', 'client binding population bound reached')
    bindings[binding.key] = binding
    temporary = path.with_name('.' + path.name + '.tmp-' + str(os.getpid()))
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, 'w') as stream:
            stream.write(encoded(dict(schema_version=1, bindings=[binding_dict(row) for row in bindings.values()])) + '\n')
            stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        temporary.unlink(missing_ok=True)
    return asdict(binding)


class NotificationDispatcher:
    def __init__(self, scheduler: MailScheduler, bindings_file, *, receipt_gate=None):
        self.scheduler, self.bindings_file = scheduler, Path(bindings_file)
        self.receipt_gate = receipt_gate

    def tick(self, *, limit=10):
        if self.receipt_gate is not None:
            self.receipt_gate.tick()
        bindings = load_bindings(self.bindings_file)  # revocation/rebinding is observed every tick
        scheduler = self.scheduler
        dispatcher = scheduler.acquire()
        if dispatcher is None:
            return dict(status='busy', submitted=0, results=[])
        results = []
        try:
            recovered = scheduler.recover(dispatcher)
            with scheduler.mailbox.transaction() as database:
                scheduler._operator(database)
                paused = scheduler.mailbox.bus.meta(database, 'paused')
                database.execute('ROLLBACK')
            if paused:
                return dict(status='paused', submitted=0, results=[], recovered=recovered)
            for job in scheduler.jobs(dispatcher, limit=limit):
                with (self.receipt_gate.guard(job) if self.receipt_gate is not None else nullcontext(None)) as receipt:
                    if receipt is False:
                        scheduler.defer(dispatcher, job['job_id'], 'capability_unavailable')
                        results.append(dict(message_id=job['message_id'], status='deferred', reason='reply_arm_unavailable'))
                        continue
                    dispatcher = scheduler.acquire()
                    if dispatcher is None:
                        raise BusError('stale_lease', 'dispatcher ownership changed')
                    binding = bindings.get(job['recipient_key'])
                    try:
                        probe = binding.probe() if binding else dict(status='deferred', reason='capability_unavailable')
                    except (BusError, OSError):
                        probe = dict(status='deferred', reason='offline')
                    if binding is not None and probe.get('reason') == 'offline':
                        from .a2a_saved_delivery import SavedRecipientBinding
                        saved = SavedRecipientBinding(binding, scheduler, job, reply_authorized=receipt is not None)
                        saved_probe = saved.probe()
                        if saved_probe.get('reason') != 'reopening_not_authorized':
                            binding, probe = saved, saved_probe
                    if probe.get('status') != 'ready':
                        reason = probe.get('reason', 'capability_unavailable')
                        scheduler.defer(dispatcher, job['job_id'], reason if reason in
                            ('busy', 'offline', 'capability_unavailable', 'authorization_denied',
                             'identity_changed', 'composer_protected', 'runtime_unavailable',
                             'client_offline', 'reply_arm_unavailable') else 'capability_unavailable')
                        results.append(dict(message_id=job['message_id'], status='deferred', reason=reason))
                        continue
                    dispatcher = scheduler.acquire()
                    if dispatcher is None:
                        raise BusError('stale_lease', 'dispatcher ownership changed')
                    recipient = scheduler.acquire('recipient:' + job['recipient_key'])
                    if recipient is None:
                        results.append(dict(message_id=job['message_id'], status='deferred', reason='busy'))
                        continue
                    try:
                        try:
                            claim = scheduler.claim(dispatcher, recipient, [job['job_id']])
                        except BusError as error:
                            results.append(dict(message_id=job['message_id'], status='denied', reason=error.code))
                            continue
                        from .a2a_tmux_delivery import TmuxBinding
                        if isinstance(binding, TmuxBinding):
                            result = binding.deliver(claim, job, scheduler.mailbox.bus.root, scheduler=scheduler)
                        else:
                            result = binding.deliver(claim, job, scheduler.mailbox.bus.root)
                        outcome = result.get('status')
                        evidence = dict(transport=getattr(binding, 'delivery_transport', binding.transport), exact_thread_id=binding.thread_id,
                                        daemon_generation=binding.generation)
                        if outcome == 'submitted':
                            evidence['receipt_id'] = result['receipt_id']
                        elif outcome == 'unsent':
                            evidence['reason'] = 'pre_io_failure' if result.get('reason') == 'pre_io_failure' else 'explicit_not_sent'
                        else:
                            outcome = 'uncertain'
                            evidence['reason'] = 'client_response_unqualified'
                        scheduler.finish(dispatcher, recipient, claim['attempt_id'], outcome=outcome, evidence=evidence)
                        results.append(dict(message_id=job['message_id'], attempt_id=claim['attempt_id'],
                            status=outcome, reason=result.get('reason'), receipt_id=result.get('receipt_id')))
                        if outcome == 'submitted' and self.receipt_gate is not None:
                            self.receipt_gate.submitted(receipt, job, claim['attempt_id'], result['receipt_id'], transport=evidence['transport'])
                        if outcome == 'uncertain':
                            break
                    finally:
                        scheduler.release(recipient)
            return dict(status='processed', submitted=sum(row['status'] == 'submitted' for row in results),
                        results=results, recovered=recovered)
        finally:
            scheduler.release(dispatcher)


def binding_dict(binding):
    value = asdict(binding)
    if binding.transport != 'owning_client_v1':
        value['transport'] = binding.transport
    return value
