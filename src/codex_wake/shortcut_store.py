"""Private local shortcut preferences and frozen-copy manifests."""
import fcntl
import json
import os
from pathlib import Path
import stat
import tempfile
from contextlib import contextmanager


def private_directory(path):
    path = Path(path).absolute()
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = path.lstat()
    if path != path.resolve() or not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ValueError('private owned real shortcut directory required')
    return path


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate shortcut key')
        result[key] = value
    return result


def read(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077 or info.st_nlink != 1 or info.st_size > 2097152:
            raise ValueError('private bounded shortcut file required')
        raw = stream.read(2097153)
        if len(raw) > 2097152:
            raise ValueError('shortcut file too large')
        return json.loads(raw, object_pairs_hook=_object)


def write(path, value):
    content = json.dumps(value, indent=2) + '\n'
    if len(content.encode()) > 2097152:
        raise ValueError('shortcut file too large')
    private_directory(path.parent)
    if os.path.lexists(path):
        read(path)
    fd, temporary = tempfile.mkstemp(prefix='.shortcut-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


@contextmanager
def locked(directory):
    directory = private_directory(directory)
    fd = os.open(directory / '.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077 or info.st_nlink != 1:
            raise ValueError('private shortcut lock required')
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield directory
    finally:
        os.close(fd)


def preference_path():
    return Path(os.environ.get('XDG_CONFIG_HOME', str(Path.home() / '.config'))) / 'codex-wake' / 'shortcuts.json'


def default_root(explicit=None):
    if explicit is not None:
        return Path(explicit).expanduser().absolute()
    try:
        value = read(preference_path())
    except FileNotFoundError:
        raise ValueError('Select a root with configuration default-root ROOT, or pass --wake-root ROOT') from None
    if not isinstance(value, dict) or value.get('version') != 1 or not isinstance(value.get('wake_root'), str) or not Path(value['wake_root']).is_absolute():
        raise ValueError('invalid shortcut root preference')
    return Path(value['wake_root'])
