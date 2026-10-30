"""Host presentation adapters and exclusive use of an existing stdio owner."""
import threading
import uuid

from .managed_inventory import InventoryError
from .tab_organization import TmuxTransport


class TmuxAttachmentTransport(TmuxTransport):
    def capture(self, pane, lines, deadline):
        return self.command(deadline, 'capture-pane', '-p', '-t', pane, '-S', '-' + str(lines))


class PsmuxAttachmentTransport:
    """Finite host broker protocol, also used for Windows qualification fixtures.

    The host bridge owns psmux process/Windows identity. A protocol fixture is
    not Windows runtime qualification. No shell/path/argv comes from a caller.
    """
    def __init__(self, bridge, *, generation):
        self.bridge, self.generation = bridge, generation

    def request(self, action, arguments, deadline):
        reply = self.bridge(action, arguments, deadline)
        if not isinstance(reply, dict) or reply.get('generation') != self.generation:
            raise InventoryError('stale_target', 'psmux bridge generation changed')
        return reply['result']

    def snapshot(self, deadline):
        return dict(self.request('snapshot', {}, deadline), bridge_generation=self.generation)

    def swap(self, first, second, deadline):
        return self.request('swap', dict(first=first, second=second), deadline)

    def capture(self, pane, lines, deadline):
        return self.request('capture', dict(pane=pane, lines=lines), deadline)


class OwnedStdioBroker:
    """Serialize the already-owned app-server client; never open another stdin.

    Host installs this object at the connection owner and shares this broker,
    rather than creating a competing reader/writer on the process pipes.
    """
    def __init__(self, client, *, bindings, owner_id):
        self.client, self.bindings = client, dict(bindings)
        self.custody = dict(available=True, transport='structured', owner_id=owner_id,
                            generation=uuid.uuid4().hex)
        self.lock = threading.Lock()
        self.closed = False

    def inspect(self):
        return dict(self.custody, available=not self.closed)

    def send(self, pane, text, *, expected_custody):
        with self.lock:
            if self.closed or expected_custody != self.inspect() or pane not in self.bindings:
                raise InventoryError('input_custody_required', 'structured connection ownership changed')
            # Existing owner translates typed input into structured turn/start.
            # An exception remains uncertain under ControllerRuntime; no fallback.
            return self.client.start_turn(self.bindings[pane], text)

    def relinquish(self):
        with self.lock:
            self.closed = True


class OwnedTerminalBroker:
    """Explicit literal-line fallback, installed only after host input custody.

    Caller must still pass privacy admission, exact pane generation and control
    grant. Never selected as recovery for failed structured submission.
    """
    def __init__(self, transport, *, panes, owner_id):
        self.transport, self.panes = transport, frozenset(panes)
        self.custody = dict(available=True,transport='terminal',owner_id=owner_id,generation=uuid.uuid4().hex)
        self.lock = threading.Lock()

    def inspect(self):
        return dict(self.custody)

    def send(self, pane, text, *, expected_custody):
        import time
        with self.lock:
            if expected_custody != self.custody or pane not in self.panes:
                raise InventoryError('input_custody_required', 'terminal custody changed')
            deadline = time.monotonic() + 5
            self.transport.command(deadline,'send-keys','-t',pane,'-l','--',text)
            self.transport.command(deadline,'send-keys','-t',pane,'Enter')
            return dict(status='submitted',acceptance='unverified',transport='terminal')


class ConfiguredBridge:
    """Host-fixed finite subprocess protocol; no command selection in requests."""
    def __init__(self, command):
        if not isinstance(command,list) or not command or any(not isinstance(x,str) for x in command):
            raise ValueError('host bridge command must be argv')
        self.command = command

    def __call__(self, action, arguments, deadline):
        import json
        import subprocess
        import time
        result = subprocess.run(self.command,input=json.dumps(dict(action=action,arguments=arguments)),
            text=True,capture_output=True,check=True,timeout=max(.001,min(5,deadline-time.monotonic())))
        if len(result.stdout)>1048576: raise ValueError('bridge reply exceeds bounded capacity')
        return json.loads(result.stdout)


class UnixInputBroker:
    """Proxy the existing host stdin custodian, never attach to its pipes."""
    def __init__(self, path):
        from pathlib import Path
        import os
        import stat
        self.path = Path(path)
        info = self.path.lstat()
        if (not self.path.is_absolute() or self.path != self.path.resolve() or
            not stat.S_ISSOCK(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077):
            raise ValueError('input broker requires private user-owned socket')
        self.identity = (info.st_dev,info.st_ino)

    def request(self, action, arguments):
        import json
        import socket
        info = self.path.lstat()
        if (info.st_dev,info.st_ino) != self.identity:
            raise InventoryError('input_custody_required','broker socket generation changed')
        with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as stream:
            stream.settimeout(5)
            stream.connect(str(self.path))
            stream.sendall(json.dumps(dict(action=action,arguments=arguments)).encode()+b'\n')
            data = b''
            while b'\n' not in data:
                chunk = stream.recv(65536)
                if not chunk: raise InventoryError('input_custody_required','broker disconnected')
                data += chunk
                if len(data)>262144: raise ValueError('broker reply exceeds bound')
            result = json.loads(data.split(b'\n',1)[0])
            if not isinstance(result,dict): raise ValueError('invalid broker response')
            return result

    def inspect(self):
        return self.request('inspect',{})

    def send(self,pane,text,*,expected_custody):
        return self.request('send',dict(pane=pane,input=text,expected_custody=expected_custody))
