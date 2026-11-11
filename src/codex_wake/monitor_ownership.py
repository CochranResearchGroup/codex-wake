"""Cooperative, nonblocking polling custody for a canonical wake root.

The stable lock inode is never removed. OS ownership, rather than a stale PID
file, releases custody when an owner exits. This does not reconcile effects of
an interrupted poll; the supervisor's durable reconciliation marker does that.
"""
from __future__ import annotations

import contextvars
import fcntl
import json
import os
import stat
from pathlib import Path

from .records import WakeError


_current: contextvars.ContextVar["MonitorOwnership | None"] = contextvars.ContextVar(
    "codex_wake_monitor_ownership", default=None,
)
_open_owners: set["MonitorOwnership"] = set()


def _after_fork() -> None:
    # A fork-only child must not extend its parent's open-file-description lock.
    # Do not LOCK_UN here: that would release the parent's ownership as well.
    for owner in tuple(_open_owners):
        if owner.fd is not None:
            os.close(owner.fd)
            owner.fd = None
            owner.acquired = False
    _open_owners.clear()
    _current.set(None)


os.register_at_fork(after_in_child=_after_fork)


def ownership_held(root: Path) -> bool:
    owner = _current.get()
    return bool(owner is not None and owner.acquired and owner.pid == os.getpid()
                and owner.root == Path(root).resolve())


def reconciliation_required(root: Path) -> bool:
    """Any marker, including a broken link or unreadable marker, fails closed."""
    try:
        (Path(root) / "monitor-reconciliation.json").lstat()
    except FileNotFoundError:
        return False
    except OSError:
        return True
    return True


class MonitorOwnership:
    """Hold one root's raw poll lock; contention never waits or alters the owner.

    A caller doing explicit reconciliation may acquire this raw lock even when
    a reconciliation marker exists. Polling must check that marker while locked.
    """

    def __init__(self, root: Path) -> None:
        self.root = Path(root).resolve()
        self.path = self.root / "locks" / "monitor.lock"
        self.fd: int | None = None
        self.acquired = False
        self.pid = os.getpid()
        self._token = None

    def __enter__(self) -> "MonitorOwnership":
        directory = self.path.parent
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        if directory.is_symlink():
            raise WakeError("monitor lock directory must not be a symlink")
        self.fd = os.open(self.path, os.O_RDWR | os.O_CREAT | os.O_CLOEXEC | os.O_NOFOLLOW, 0o600)
        try:
            metadata = os.fstat(self.fd)
            if (not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.geteuid()
                    or metadata.st_mode & 0o077):
                raise WakeError("monitor lock must be a private owner-only regular file")
            try:
                fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                os.close(self.fd)
                self.fd = None
                return self
            self.acquired = True
            os.ftruncate(self.fd, 0)
            os.write(self.fd, (json.dumps({"pid": self.pid}) + "\n").encode("ascii"))
            self._token = _current.set(self)
            _open_owners.add(self)
            return self
        except BaseException:
            os.close(self.fd)
            self.fd = None
            self.acquired = False
            raise

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._token is not None and self.pid == os.getpid():
            _current.reset(self._token)
            self._token = None
        _open_owners.discard(self)
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None
        self.acquired = False
