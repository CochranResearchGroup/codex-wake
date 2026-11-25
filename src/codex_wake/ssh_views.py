"""Restore a source SSH presentation while retaining destination execution custody."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import sqlite3
import subprocess
import sys
from tempfile import NamedTemporaryFile, TemporaryDirectory
from urllib.parse import urlsplit

from .message_owner import _object, _private
from .message_owner_registry import environment_record, resolve_owner_pair
from .runtime_identity_key import codex_identity


class ViewError(ValueError):
    pass


_TOKEN = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,95}\Z')
_LIVE = ('idle', 'active')
_TOKEN_ENV = 'CODEX_WAKE_SSH_VIEW_NATIVE_TOKEN'
_FORMAT = '#{window_id}\t#{window_index}\t#{window_name}\t#{pane_id}\t#{pane_pid}'


def _token(value):
    if not isinstance(value, str) or not _TOKEN.fullmatch(value):
        raise ViewError('invalid_view_identifier')
    return value


def _argv(value):
    if (not isinstance(value, list) or not 1 <= len(value) <= 12
            or any(not isinstance(arg, str) or not arg or len(arg) > 4096 or any(ord(c) < 32 for c in arg)
                   for arg in value)):
        raise ViewError('invalid_ssh_view_command')
    return value


def _executable(value):
    executable = Path(value)
    if (not executable.is_absolute() or not executable.is_file()
            or executable.suffix.lower() in ('.bat', '.cmd', '.ps1')):
        raise ViewError('view_executable_unavailable')
    return str(executable)


def _config(path, role):
    path = _private(Path(path))
    config = _object(path)
    if config.get('version') != 1 or config.get('role') != role:
        raise ViewError('invalid_ssh_view_configuration')
    source, destination = config['source'], config['destination']
    registry = _private(Path(config['registry']))
    source_kind, destination_kind = resolve_owner_pair(registry, source, destination)
    if {source_kind, destination_kind} != {'windows', 'wsl'}:
        raise ViewError('ssh_view_normal_windows_wsl_scope_required')
    with sqlite3.connect(registry.as_uri() + '?mode=ro', uri=True) as db:
        registered = environment_record(db, destination['host'], destination['environment'])
    identity = config['conversation']
    if (not isinstance(identity, dict) or set(identity) != {'namespace', 'thread_id', 'cwd'}
            or any(not isinstance(v, str) or not 0 < len(v) <= 4096 for v in identity.values())):
        raise ViewError('invalid_exact_conversation')
    _token(config['view'])
    return path, config, registered, (source_kind, destination_kind)


def _clean_environment(codex_home):
    env = dict(os.environ)
    for name in ('TMUX', 'TMUX_PANE', 'STY', 'BYOBU_BACKEND', 'PSMUX', 'PSMUX_PANE', 'CODEX_THREAD_ID',
                 'CODEX_WAKE_OWNER_DB_DSN', 'CODEX_WAKE_MESSAGE_DB_DSN', 'CODEX_WAKE_CUTOVER_DB_DSN', _TOKEN_ENV):
        env.pop(name, None)
    env['CODEX_HOME'] = codex_home
    return env


def _thread(endpoint, thread_id, token=None):
    if endpoint.startswith('unix:///'):
        if token is not None:
            raise ViewError('native_bearer_requires_loopback_websocket')
        from .shared_app_server import SharedAppServerReader
        with SharedAppServerReader(endpoint, timeout=5) as reader:
            thread = reader.read_thread(thread_id)
            return thread, reader.server_metadata
    url = urlsplit(endpoint)
    if (url.scheme != 'ws' or url.hostname not in ('127.0.0.1', '::1') or not url.port
            or url.username or url.password or url.path not in ('', '/') or url.query or url.fragment):
        raise ViewError('local_native_endpoint_required')
    from websockets.sync.client import connect
    headers = {'Authorization': 'Bearer ' + token} if token is not None else None
    with connect(endpoint, proxy=None, additional_headers=headers,
                 open_timeout=4, close_timeout=1, max_size=4 * 1024 * 1024) as connection:
        def exchange(ident, method, **params):
            from time import monotonic
            until = monotonic() + 4
            connection.send(json.dumps(dict(id=ident, method=method, params=params)))
            for _ in range(128):
                reply = json.loads(connection.recv(timeout=max(0, until - monotonic())))
                if reply.get('id') == ident:
                    return reply['result']
            raise ViewError('native_observation_capacity')
        server = exchange(1, 'initialize', clientInfo=dict(name='wake-ssh-view', version='1'),
                          capabilities=dict(experimentalApi=True))
        connection.send(json.dumps(dict(method='initialized')))
        return exchange(2, 'thread/read', threadId=thread_id, includeTurns=False)['thread'], server


def _receiver(config, *, resume):
    profile = config['harness']
    cwd = Path(profile['cwd'])
    home = Path(profile['codex_home'])
    if (not home.is_absolute() or not home.is_dir() or home != home.resolve()
            or os.name != 'nt' and home.stat().st_uid != os.geteuid()):
        raise ViewError('destination_home_changed')
    codex = _executable(profile['codex'])
    exact = config['conversation']
    if not cwd.is_absolute() or not cwd.is_dir() or cwd != cwd.resolve() or str(cwd) != exact['cwd']:
        raise ViewError('destination_workspace_changed')
    endpoint = profile['endpoint']
    token = None
    if profile.get('token_file') is not None:
        with _private(Path(profile['token_file'])).open(encoding='utf-8') as stream:
            token = stream.read(258).strip()
        if not re.fullmatch(r'[A-Za-z0-9._~-]{32,256}', token):
            raise ViewError('native_bearer_invalid')
    thread, metadata = _thread(endpoint, exact['thread_id'], token)
    namespace, identifier, saved_cwd = codex_identity(thread, metadata)
    if (dict(namespace=namespace, thread_id=identifier, cwd=saved_cwd) != exact
            or Path(metadata['codexHome']).resolve() != home):
        raise ViewError('destination_conversation_changed')
    state = thread.get('status', {}).get('type')
    if state not in (*_LIVE, 'notLoaded'):
        raise ViewError('destination_harness_state_unavailable')
    allowed = state in _LIVE or resume and config.get('allow_saved_resume') is True
    env = _clean_environment(str(home))
    command = [codex, '--remote', endpoint]
    if token is not None:
        env[_TOKEN_ENV] = token
        command.extend(('--remote-auth-token-env', _TOKEN_ENV))
    command.extend(('resume', '--no-alt-screen', '-C', str(cwd), identifier))
    return dict(view=config['view'], owner=config['destination'], conversation=exact,
                state=state, allowed=allowed), command, cwd, env


def _windows_normal():
    if os.name == 'nt':
        import ctypes
        if ctypes.windll.shell32.IsUserAnAdmin():
            raise ViewError('separately_registered_elevated_owner_required')


def _ssh(config, registered, destination_kind, verb, mode):
    transport = registered['transport']
    args = [transport['executable']]
    if config.get('ssh_config') is not None:
        args.extend(('-F', str(_private(Path(config['ssh_config'])))))
    args.extend(('-S', 'none', '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes', '-o', 'ConnectTimeout=5'))
    args.extend(('-tt',) if verb == 'present' else ('-n', '-T'))
    args.extend(('--', transport['destination']))
    remote = [*_argv(config['receiver_argv']), verb, mode]
    if destination_kind == 'windows':
        if any(any(c in arg for c in '"&|<>^%!()') for arg in remote):
            raise ViewError('unqualified_windows_receiver_argv')
        command = subprocess.list2cmdline(remote)
    else:
        command = shlex.join(remote)
    return [*args, command]



def _capture(argv, *, timeout, limit):
    # Native Windows OpenSSH can keep inherited pipe handles open after the
    # command exits. Use a private file and bound the result we read.
    with TemporaryDirectory(prefix='wake-ssh-view-') as directory:
        path = Path(directory) / 'stdout'
        with path.open('wb') as output:
            subprocess.run(argv, stdin=subprocess.DEVNULL, stdout=output, stderr=output,
                           timeout=timeout, check=True)
        with path.open('rb') as output:
            data = output.read(limit + 1)
    if len(data) > limit:
        raise ViewError('ssh_view_response_capacity')
    return data.decode('utf-8')

def _terminal(config, *args):
    terminal = config['terminal']
    executable = _executable(terminal['executable'])
    if os.name == 'nt':
        prefix = [executable, '-L', _token(terminal['namespace'])]
    else:
        socket = Path(terminal['socket'])
        if not socket.is_absolute() or socket.is_symlink() or not socket.is_socket() or socket.stat().st_uid != os.geteuid():
            raise ViewError('source_terminal_unavailable')
        prefix = [executable, '-S', str(socket)]
    return _capture([*prefix, *args], timeout=6, limit=1024 * 1024).strip('\r\n')


def _placement(config):
    terminal = config['terminal']
    session, name = _token(terminal['session']), _token(terminal['name'])
    index = terminal['index']
    if type(index) is not int or not 0 <= index <= 9999:
        raise ViewError('invalid_source_window_index')
    rows = _terminal(config, 'list-panes', '-s', '-t', session, '-F', _FORMAT)
    panes = []
    for line in rows.splitlines():
        window, position, label, pane, pid = line.split('\t')
        panes.append(dict(window_id=window, index=int(position), name=label, pane_id=pane, pid=int(pid)))
    return session, name, index, panes


def _marker(config):
    return hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()


def _birth(pid):
    if os.name == 'nt':
        from .tab_psmux_bridge import BridgeError, process_birth
        try:
            return process_birth(pid)
        except BridgeError:
            return None
    from .process import process_identity
    return process_identity(pid)


def _current_view(receipt, config, panes):
    try:
        prior = _object(_private(receipt))
    except FileNotFoundError:
        return None
    if prior['binding'] != _marker(config):
        return None
    process = prior['pane']
    rows = [pane for pane in panes
            if all(pane[key] == process[key] for key in ('window_id', 'pane_id', 'pid'))]
    if len(rows) == 1 and prior['birth'] is not None and prior['birth'] == _birth(process['pid']):
        return rows[0]
    return None


def _record_view(receipt, config, pane):
    birth = _birth(pane['pid'])
    if birth is None:
        raise ViewError('source_window_outcome_unverified')
    with NamedTemporaryFile(dir=receipt.parent, mode='w', encoding='utf-8', delete=False) as stream:
        temporary = Path(stream.name)
        try:
            json.dump(dict(binding=_marker(config), pane=pane, birth=birth), stream)
            stream.flush()
            os.fsync(stream.fileno())
        except BaseException:
            stream.close()
            temporary.unlink(missing_ok=True)
            raise
    try:
        temporary.replace(receipt)
    finally:
        temporary.unlink(missing_ok=True)


def _source(path, config, registered, destination_kind, verb, mode):
    receipt = path.with_suffix('.ssh-view.json')
    session, name, index, panes = _placement(config)
    existing = _current_view(receipt, config, panes)
    if existing is not None:
        return dict(view=config['view'], status='present', owner=config['destination'],
                    conversation=config['conversation'], placement=existing)
    if any(pane['index'] == index or pane['name'] == name for pane in panes):
        raise ViewError('source_window_occupied')
    if verb == 'inspect' or mode == 'background':
        return dict(view=config['view'], status='closed', owner=config['destination'],
                    conversation=config['conversation'])

    try:
        probe = _capture(_ssh(config, registered, destination_kind, 'probe', mode), timeout=20, limit=8192)
    except subprocess.SubprocessError as exc:
        raise ViewError('destination_probe_failed') from exc
    result = json.loads(probe)
    if (result.get('owner') != config['destination'] or result.get('conversation') != config['conversation']
            or result.get('view') != config['view'] or result.get('state') not in (*_LIVE, 'notLoaded')):
        raise ViewError('destination_identity_unqualified')
    if result.get('allowed') is not True:
        return dict(view=config['view'], status='held', reason='saved_resume_not_authorized',
                    owner=config['destination'], conversation=config['conversation'])
    if any(pane['index'] == index or pane['name'] == name for pane in _placement(config)[3]):
        raise ViewError('source_window_occupied')
    shell = _ssh(config, registered, destination_kind, 'present', mode)
    arguments = ['--', *shell] if os.name == 'nt' else [shlex.join(shell)]
    cwd = Path(config['terminal']['cwd'])
    if not cwd.is_absolute() or not cwd.is_dir() or cwd != cwd.resolve():
        raise ViewError('source_workspace_changed')
    window = _terminal(config, 'new-window', '-d', '-P', '-F', '#{window_id}',
                       '-t', f'{session}:{index}', '-n', name, '-c', str(cwd), *arguments)
    if not re.fullmatch(r'@[0-9]+', window):
        raise ViewError('source_window_outcome_unverified')
    found = [pane for pane in _placement(config)[3]
             if pane['index'] == index or pane['name'] == name]
    if (len(found) != 1 or found[0]['window_id'] != window or found[0]['index'] != index
            or found[0]['name'] != name):
        raise ViewError('source_window_outcome_unverified')
    _record_view(receipt, config, found[0])
    return dict(view=config['view'], status='present', owner=config['destination'],
                conversation=config['conversation'], placement=found[0])


def main(argv=None):
    parser = argparse.ArgumentParser(prog='codex-wake ssh-views')
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('verb', choices=('inspect', 'recover', 'probe', 'present'))
    parser.add_argument('mode', choices=('background', 'existing', 'resume'), default='existing', nargs='?')
    args = parser.parse_args(argv)
    from websockets.exceptions import WebSocketException

    try:
        receiver = args.verb in ('probe', 'present')
        path, config, registered, kinds = _config(args.config, 'destination' if receiver else 'source')
        _windows_normal()
        if receiver:
            if args.mode == 'background':
                raise ViewError('background_has_no_ssh_presentation')
            result, command, cwd, env = _receiver(config, resume=args.mode == 'resume')
            if args.verb == 'present':
                if not result['allowed'] or not sys.stdin.isatty() or not sys.stdout.isatty():
                    raise ViewError('remote_presentation_not_authorized')
                return subprocess.call(command, cwd=cwd, env=env)
        else:
            result = _source(path, config, registered, kinds[1], args.verb, args.mode)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (OSError, ValueError, KeyError, TypeError, WebSocketException, subprocess.SubprocessError) as error:
        code = str(error) if isinstance(error, ViewError) else 'ssh_view_unavailable'
        print(json.dumps(dict(status='held', reason=code)), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
