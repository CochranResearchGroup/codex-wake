"""Bounded read-only discovery of existing same-user terminal workspaces."""
import hashlib
import os
from pathlib import Path
import stat
import subprocess
import time


def discover(*, deadline=None):
    deadline = deadline or time.monotonic() + 5
    sockets = []
    current = os.environ.get('TMUX', '').split(',', 1)[0]
    if current:
        sockets.append(Path(current))
    directory = Path('/tmp') / ('tmux-' + str(os.getuid()))
    try:
        info = directory.lstat()
        if stat.S_ISDIR(info.st_mode) and info.st_uid == os.getuid() and not directory.is_symlink():
            sockets.extend(sorted(directory.iterdir())[:16])
    except OSError:
        pass
    workspaces, diagnostics = {}, []
    for path in dict.fromkeys(sockets):
        if len(workspaces) >= 64 or time.monotonic() >= deadline:
            diagnostics.append(dict(code='discovery_bounded', message='Refresh to inspect remaining workspaces.'))
            break
        try:
            info = path.lstat()
            if (not path.is_absolute() or path != path.resolve() or not stat.S_ISSOCK(info.st_mode)
                    or info.st_uid != os.getuid()):
                continue
            result = subprocess.run(['tmux', '-S', str(path), 'list-sessions', '-F',
                                     '#{session_id}\t#{session_name}'], capture_output=True, text=True,
                                    timeout=max(.001, min(1, deadline-time.monotonic())))
            if result.returncode:
                diagnostics.append(dict(code='workspace_unavailable', socket=str(path)))
                continue
            if len(result.stdout) > 65536:
                diagnostics.append(dict(code='inventory_bounded', socket=str(path)))
                continue
            for line in result.stdout.splitlines()[:64]:
                session, label = line.split('\t', 1)
                from .controller_tab_adapters import TmuxAttachmentTransport
                key = 'tmux-' + hashlib.sha256(str(path).encode()).hexdigest()[:8] + '-' + session[1:]
                workspaces[key] = dict(kind='byobu' if 'byobu' in label.casefold() else 'tmux',
                                       label=label, transport=TmuxAttachmentTransport(str(path),session),
                                       socket_path=str(path), session_id=session, discovered=True)
        except (OSError, ValueError, subprocess.SubprocessError):
            diagnostics.append(dict(code='workspace_unavailable', socket=str(path)))
    return workspaces, diagnostics
