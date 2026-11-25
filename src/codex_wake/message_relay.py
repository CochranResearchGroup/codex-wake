"""Pinned SSH transport for one cross-server Message admission or readback."""
from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
from uuid import UUID


FRAME_LIMIT = 400_000
WAITING = {'owner_admitted', 'held_dnd', 'held_policy', 'held_recipient', 'waiting_for_time'}


def _outcome(value):
    if not isinstance(value, dict):
        return None
    status = value.get('status')
    if status in WAITING | {'expired'}:
        if (set(value) == {'status'} or
                status == 'held_recipient' and set(value) == {'status', 'reason'}
                and isinstance(value['reason'], str) and len(value['reason']) <= 256):
            return value
    if status not in ('submitted', 'uncertain'):
        return None
    if set(value) - {'status', 'attempt_id', 'receipt_id', 'reason', 'evidence_kind', 'execution', 'acknowledgment'}:
        return None
    if not all(isinstance(item, str) and 0 < len(item) <= 256 for item in value.values()):
        return None
    if str(UUID(value['attempt_id'])) != value['attempt_id']:
        return None
    if status == 'submitted' and not value.get('receipt_id'):
        return None
    return value


def forwarded_outcome(frame, response):
    if not isinstance(response, dict):
        return None
    message = frame['request']['message']
    expected = dict(id=message['identifier'], recipient=message['recipient'],
                    source=frame['destination'], destination=frame['source'],
                    expires_at_micros=message['expires_at_micros'],
                    not_before_micros=message['not_before_micros'],
                    in_reply_to=message['in_reply_to'])
    if set(response) != set(expected) | {'outcome'} or any(response[key] != item for key, item in expected.items()):
        return None
    try:
        return _outcome(response['outcome'])
    except (KeyError, ValueError, TypeError):
        return None


def ssh_relay(config, record, private):
    if not isinstance(config, dict) or not {'identity_file', 'known_hosts'} <= set(config) <= {
            'identity_file', 'known_hosts', 'port'}:
        raise ValueError('cross-server SSH requires an identity file and pinned known hosts')
    transport = record['transport']
    executable = Path(transport['executable'])
    destination = transport['destination']
    port = config.get('port', 22)
    if (not executable.is_absolute() or type(port) is not int or not 0 < port <= 65535
            or not re.fullmatch(r'(?:[A-Za-z0-9_][A-Za-z0-9_.-]*@)?(?:[A-Za-z0-9][A-Za-z0-9.-]*|\[[0-9a-fA-F:]+\])',
                                destination)):
        raise ValueError('cross-server SSH requires an explicit SSH executable and host')
    identity = private(config['identity_file'])
    known_hosts = private(config['known_hosts'])
    argv = [str(executable), '-F', 'none', '-T', '-p', str(port),
            '-i', str(identity), '-o', f'UserKnownHostsFile="{known_hosts}"',
            '-o', 'GlobalKnownHostsFile=none', '-o', 'StrictHostKeyChecking=yes',
            '-o', 'BatchMode=yes', '-o', 'IdentitiesOnly=yes', '-o', 'IdentityAgent=none',
            '-o', 'ConnectTimeout=3', '-o', 'ClearAllForwardings=yes',
            '--', destination, 'codex-wake-message-relay-v1']

    def forward(frame):
        payload = json.dumps(frame, ensure_ascii=False).encode()
        if len(payload) > FRAME_LIMIT:
            raise ValueError('cross-server message frame exceeds protocol limit')
        try:
            result = subprocess.run(argv, input=payload, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                    timeout=8, check=False)
            if result.returncode or len(result.stdout) > 4096:
                return None
            return forwarded_outcome(frame, json.loads(result.stdout))
        except (OSError, ValueError, subprocess.SubprocessError):
            return None

    return forward


def read_forward(stream):
    raw = stream.read(FRAME_LIMIT + 1)
    if not raw or len(raw) > FRAME_LIMIT:
        raise ValueError('invalid cross-server message frame size')
    frame = json.loads(raw)
    if not isinstance(frame, dict):
        raise ValueError('cross-server message frame must be an object')
    return frame
