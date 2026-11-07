"""Explicit MCP configuration reload through the selected native daemon owner."""
import os
import socket
import struct
import tomllib

from .controller_builds import ControllerBuilds
from .controller_daemons import ControllerDaemons
from .managed_inventory import InventoryError
from .native_protocol import NativeCapabilityUnavailable, native_request


def selected_reload(accounts, destination, *, categories, guard=lambda: None):
    """Never launch/restart a daemon or redirect a reload to stock or a peer."""
    guard()
    if 'mcp' not in categories:
        return 'unsupported; use next launch for selected categories; native reload supports MCP definitions only'
    manifest = tomllib.loads(accounts.path.read_text()).get('builds', {}).get('manifest')
    if not manifest or destination['kind'] != 'profile':
        return 'unsupported; use next launch or register a supported selected-profile daemon'
    owner = ControllerDaemons(ControllerBuilds(manifest, accounts))
    selector = destination['selector']
    observed = owner.execute('daemons.status', dict(account=selector, channel='modded'))['daemon']
    if observed['state'] != 'running' or not observed.get('selected_build_running'):
        return 'unsupported; use next launch or start the selected registered profile build'
    target = observed['target']
    if target['home'] != destination['home'] or target['home_generation'] != destination['home_generation']:
        raise InventoryError('stale_target', 'selected sync destination changed before reload')

    def verify(connection, metadata):
        guard()
        pid, uid, _ = struct.unpack('3i', connection.socket.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
        current = owner.execute('daemons.status', dict(account=selector, channel='modded'))['daemon']
        if (uid != os.geteuid() or pid != target['process']['pid'] or metadata.get('codexHome') != destination['home']
                or current['target'] != target):
            raise InventoryError('stale_target', 'selected native reload peer changed')

    def request(method, params):
        guard()
        value = native_request(observed['endpoint'], target['executable'], method, params, 8, verify_connection=verify)
        guard()
        return value

    try:
        loaded = request('thread/loaded/list', {})['data']
        for thread in loaded:
            row = request('thread/read', dict(threadId=thread, includeTurns=False))['thread']
            if row['status']['type'] != 'idle' or row['status'].get('activeFlags'):
                return 'pending; selected profile has active turns; use next launch or retry a new sync after idle'
        # This native method queues configuration reload in this exact daemon;
        # it never replaces a client or a conversation and leaves goals intact.
        acknowledgement = request('config/mcpServer/reload', None)
        if acknowledgement != {}:
            raise InventoryError('outcome_unknown', 'selected profile reload acknowledgement is unrecognized; reconcile before retry')
    except NativeCapabilityUnavailable:
        return 'unsupported; selected native build lacks configuration reload; use next launch'
    return 'requested_selected_profile'
