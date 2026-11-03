"""Install only Wake-owned completion files and narrowly managed startup blocks."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile

from .completion import render_script

_PATHS = {'bash': '.local/share/bash-completion/completions/codex-wake',
          'zsh': '.zsh/completions/_codex-wake'}
_STATE = '.local/state/codex-wake/completion/manifest.json'
_START = '# >>> codex-wake completion >>>'
_END = '# <<< codex-wake completion <<<'


def _digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def _check(path, *, directory=False):
    info = path.lstat()
    if path.is_symlink() or info.st_uid != os.getuid():
        raise ValueError('completion path must be owned and not symlinked: ' + str(path))
    if directory and (not stat.S_ISDIR(info.st_mode) or info.st_mode & 0o022):
        raise ValueError('completion parent is not a directory: ' + str(path))
    if not directory and (not stat.S_ISREG(info.st_mode) or info.st_size > 1048576):
        raise ValueError('bounded regular completion file required: ' + str(path))


def _path(home, relative):
    path = home
    for part in Path(relative).parts:
        path = path / part
        if os.path.lexists(path):
            _check(path, directory=path != home / relative)
    return home / relative


def _read(path):
    if not path.exists():
        return None
    _check(path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, encoding='utf-8') as stream:
        return stream.read(1048577)


def _write(home, path, text):
    # Revalidate parents immediately before write, then atomically replace only
    # a preflight-approved file. Completion setup never follows user symlinks.
    _path(home, str(path.relative_to(home)))
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    _path(home, str(path.relative_to(home)))
    previous = path.stat().st_mode & 0o777 if path.exists() else 0o600
    fd, temporary = tempfile.mkstemp(prefix='.wake-completion-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            stream.write(text)
        os.chmod(temporary, previous)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _block(shell):
    if shell == 'bash':
        body = 'if [ -r "$HOME/.local/share/bash-completion/completions/codex-wake" ]; then\n  . "$HOME/.local/share/bash-completion/completions/codex-wake"\nfi\n'
    else:
        body = 'fpath=("$HOME/.zsh/completions" $fpath)\nautoload -Uz compinit\n(( $+functions[compdef] )) || compinit\nif [[ -r "$HOME/.zsh/completions/_codex-wake" ]]; then\n  source "$HOME/.zsh/completions/_codex-wake"\nfi\n'
    return _START + '\n' + body + _END + '\n'


def _already_activated(rc, shell):
    path = '$HOME/' + _PATHS[shell]
    return any(line.strip() in ('. \"' + path + '\"', 'source \"' + path + '\"') for line in rc.splitlines())


def configure(action, *, shell='all', home=None):
    """Install/update or remove unchanged owned content; preserve external edits."""
    if action not in ('install', 'uninstall') or shell not in ('all', 'bash', 'zsh'):
        raise ValueError('choose install/uninstall and bash/zsh/all')
    home = Path.home() if home is None else Path(home).expanduser().absolute()
    if home != home.resolve(strict=True):
        raise ValueError('completion home must be canonical')
    _check(home, directory=True)
    state_path = _path(home, _STATE)
    raw = _read(state_path)
    state = json.loads(raw) if raw is not None else {'version': 1, 'shells': {}}
    if not isinstance(state, dict) or state.get('version') != 1 or not isinstance(state.get('shells'), dict):
        raise ValueError('unsupported completion ownership manifest')
    planned = []
    preserved = []
    selected = ('bash', 'zsh') if shell == 'all' else (shell,)
    for name in selected:
        file = _path(home, _PATHS[name])
        startup = _path(home, '.' + name + 'rc')
        content = _read(file)
        rc = _read(startup)
        rc = '' if rc is None else rc
        owned = state['shells'].get(name)
        if owned is not None and (not isinstance(owned, dict) or not isinstance(owned.get('file_sha256'), str) or not isinstance(owned.get('block'), str)):
            raise ValueError('invalid completion ownership record')
        block = owned['block'] if owned else None
        markers = rc.count(_START) + rc.count(_END)
        valid_block = block is not None and rc.count(block) == 1 and markers == 2
        valid_file = owned is not None and content is not None and _digest(content) == owned['file_sha256']
        if action == 'install':
            if content is not None and not valid_file:
                raise ValueError('preserving unowned or edited completion file: ' + str(file))
            if markers and not valid_block:
                raise ValueError('preserving ambiguous or edited completion activation: ' + str(startup))
            new_block = _block(name)
            if valid_block:
                updated = rc.replace(block, new_block, 1)
                prefix = owned.get('prefix', '')
            elif _already_activated(rc, name):
                new_block = ''
                prefix = ''
                updated = rc
            else:
                prefix = '' if not rc or rc.endswith('\n') else '\n'
                updated = rc + prefix + new_block
            planned.append((name, file, render_script(name), startup, updated,
                            {'file_sha256': _digest(render_script(name)), 'block': new_block, 'prefix': prefix}))
        elif owned is not None:
            new_file = None if valid_file else content
            if content is not None and not valid_file:
                preserved.append(str(file))
            updated = rc
            if valid_block:
                removal = owned.get('prefix', '') + block
                updated = rc.replace(removal if removal in rc else block, '', 1)
            elif markers:
                preserved.append(str(startup))
            retained = owned if (content is not None and not valid_file) or (markers and not valid_block) else None
            planned.append((name, file, new_file, startup, updated, retained))
    for name, file, content, startup, rc, owned in planned:
        if content is None:
            if file.exists():
                _check(file)
                file.unlink()
        elif content != _read(file):
            _write(home, file, content)
        if rc != (_read(startup) or ''):
            _write(home, startup, rc)
        if owned is None:
            state['shells'].pop(name, None)
        else:
            state['shells'][name] = owned
    if state['shells']:
        _write(home, state_path, json.dumps(state, indent=2) + '\n')
    elif state_path.exists():
        _check(state_path)
        state_path.unlink()
    return {'status': 'completed', 'action': action, 'shells': list(selected),
            'preserved': preserved, 'reload': 'Open a new shell or reload its startup file.' if action == 'install' else None}
