"""Private, idle-expiring bridge to fresh Windows QPC reads (never UTC)."""
import base64
import fcntl
import json
import os
from pathlib import Path
import select
import socket
import stat
import subprocess
import sys
import time
import uuid

SCRIPT = '''while ($null -ne ($id = [Console]::ReadLine())) {
 [Console]::WriteLine("{0},{1},{2}",$id,[Diagnostics.Stopwatch]::GetTimestamp(),[Diagnostics.Stopwatch]::Frequency)
}'''
_CHILDREN = []
COMMAND = ['/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe',
           '-NoProfile', '-NonInteractive', '-EncodedCommand',
           base64.b64encode(SCRIPT.encode('utf-16le')).decode()]


def _directory(directory):
    root = Path(directory) if directory else Path.home()/'.local/state/codex-wake/host-counter'
    root.mkdir(parents=True, mode=0o700, exist_ok=True)
    info = root.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ValueError('counter_directory_not_private')
    return root


def _line(stream, deadline):
    data = bytearray()
    while len(data) < 256:
        remaining = deadline-time.monotonic()
        if remaining <= 0 or not select.select([stream], [], [], remaining)[0]:
            raise TimeoutError('counter_read_timeout')
        chunk = os.read(stream.fileno(), 1)
        if not chunk:
            raise ValueError('counter_eof')
        if chunk == b'\n':
            return bytes(data).decode('ascii').strip()
        data.extend(chunk)
    raise ValueError('counter_response_too_large')


def _values(counter, frequency):
    if not all(type(x) is int for x in (counter, frequency)) or counter < 0 or frequency <= 0:
        raise ValueError('invalid_host_counter')
    return counter, frequency


def read_counter(directory=None, *, start=True):
    """Read a newly sampled counter through the current user's private bridge."""
    root = _directory(directory)
    deadline = time.monotonic()+5
    launched = False
    request_id = uuid.uuid4().hex
    while True:
        try:
            info = (root/'counter.sock').lstat()
            if not stat.S_ISSOCK(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
                raise ValueError('counter_socket_not_private')
            with socket.socket(socket.AF_UNIX) as client:
                client.settimeout(max(.001, deadline-time.monotonic()))
                client.connect(str(root/'counter.sock'))
                client.sendall((request_id+'\n').encode())
                data = _line(client, deadline)
                response = json.loads(data)
                if not isinstance(response, dict) or response.get('id') != request_id or response.get('status') != 'ok':
                    raise ValueError('counter_response_rejected')
                return _values(response['counter'], response['frequency'])
        except (FileNotFoundError, ConnectionRefusedError) as exc:
            # A private bridge publishes its socket before listen(). Waiting for
            # that existing owner does not start a bridge or replay a request:
            # connect() refused before any bytes reached the producer.
            if not start and isinstance(exc, ConnectionRefusedError) and time.monotonic() < deadline:
                time.sleep(.02)
                continue
            if not start or time.monotonic() >= deadline:
                raise ValueError('counter_bridge_unavailable') from None
            if not launched:
                # Child imports this exact source/release; never substitute another CLI.
                for pid in _CHILDREN[:]:
                    try:
                        if os.waitpid(pid, os.WNOHANG)[0]:
                            _CHILDREN.remove(pid)
                    except ChildProcessError:
                        _CHILDREN.remove(pid)
                actions = [(os.POSIX_SPAWN_OPEN, fd, '/dev/null',
                            os.O_RDONLY if fd == 0 else os.O_WRONLY, 0o600) for fd in range(3)]
                _CHILDREN.append(os.posix_spawn(sys.executable,
                    [sys.executable, str(Path(__file__).resolve()), '--serve', str(root)],
                    os.environ, file_actions=actions, setpgroup=0))
                launched = True
            time.sleep(.02)


def serve_counter(directory, *, command=None, idle_seconds=60):
    """Own one serialized native producer; terminate on malformed or late output."""
    root = _directory(directory)
    lock_path = root/'bridge.lock'
    descriptor = os.open(lock_path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, 'w') as lock:
        info = os.fstat(lock.fileno())
        if info.st_uid != os.getuid() or not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077:
            raise ValueError('counter_lock_not_private')
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        address = root/'counter.sock'
        if address.exists() or address.is_symlink():
            info = address.lstat()
            if not stat.S_ISSOCK(info.st_mode) or info.st_uid != os.getuid():
                raise ValueError('counter_socket_not_owned')
            address.unlink()
        producer = None
        try:
            with socket.socket(socket.AF_UNIX) as server:
                server.bind(str(address))
                address.chmod(0o600)
                server.listen(16)
                producer = subprocess.Popen(command or COMMAND, stdin=subprocess.PIPE,
                                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=0)
                server.settimeout(idle_seconds)
                while True:
                    try:
                        client, _ = server.accept()
                    except socket.timeout:
                        return
                    with client:
                        try:
                            request_id = _line(client, time.monotonic()+1)
                            if len(request_id) != 32 or any(c not in '0123456789abcdef' for c in request_id):
                                continue
                            producer.stdin.write((request_id+'\n').encode())
                            producer.stdin.flush()
                            parts = _line(producer.stdout, time.monotonic()+4).split(',')
                            if len(parts) != 3 or parts[0] != request_id or not all(x.isascii() and x.isdigit() for x in parts[1:]):
                                raise ValueError('counter_producer_mismatch')
                            counter, frequency = _values(*map(int, parts[1:]))
                            client.settimeout(1)
                            client.sendall((json.dumps(dict(id=request_id, status='ok', counter=counter,
                                                           frequency=frequency))+'\n').encode())
                        except (OSError, ValueError, TimeoutError):
                            # No stale output reuse, fallback or automatic replay of this read.
                            return
        finally:
            if producer:
                producer.stdin.close()
                try:
                    producer.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    producer.kill()
                    producer.wait()
                producer.stdout.close()
            address.unlink(missing_ok=True)


if __name__ == '__main__':
    if len(sys.argv) != 3 or sys.argv[1] != '--serve':
        raise SystemExit(2)
    serve_counter(Path(sys.argv[2]))
