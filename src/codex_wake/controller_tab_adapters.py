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
