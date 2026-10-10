"""Bounded native lifecycle and explicit delivery-recovery protocol access."""
from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import time

from . import __version__
from .records import WakeError


def native_request(endpoint, codex, method, params, timeout):
    from .shared_app_server import locate_shared_endpoint
    from websockets.sync.client import unix_connect
    deadline = time.monotonic() + timeout
    if endpoint == 'unix://':
        endpoint = locate_shared_endpoint(codex_cmd=codex, timeout=timeout)
    if not endpoint.startswith('unix://') or not Path(endpoint[7:]).is_absolute():
        raise WakeError('session lifecycle requires an existing local Unix endpoint')
    try:
        info = Path(endpoint[7:]).lstat()
    except OSError:
        raise WakeError('native lifecycle endpoint is unavailable') from None
    if not stat.S_ISSOCK(info.st_mode) or info.st_uid != os.geteuid():
        raise WakeError('native lifecycle endpoint must be an owned Unix socket')
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise WakeError('native lifecycle endpoint observation timed out')
    # Long-lived threads can exceed the WebSocket library's 1 MiB default.
    # Retain a finite response cap and the existing absolute request deadline.
    with unix_connect(endpoint[7:], open_timeout=remaining, close_timeout=1,
                      compression=None, max_size=32 * 1024 * 1024) as ws:
        def request(identifier, name, body):
            ws.send(json.dumps({'id': identifier, 'method': name, 'params': body}))
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise WakeError('native lifecycle request timed out; inspect state before retry')
                result = json.loads(ws.recv(timeout=remaining))
                if result.get('id') != identifier:
                    continue
                if 'error' in result:
                    raise WakeError('native lifecycle request rejected: ' + name)
                return result['result']
        request(1, 'initialize', {'clientInfo': {'name': 'codex_wake_lifecycle', 'version': __version__},
                                  'capabilities': {'experimentalApi': True}})
        ws.send(json.dumps({'method': 'initialized'}))
        return request(2, method, params)


