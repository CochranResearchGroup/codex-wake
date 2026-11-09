"""Opt-in host delegation for native callers in already enrolled mailbox roots."""
import fcntl
import os
import time
from pathlib import Path

from .a2a_bus import BusStore, private_path
from .a2a_cli import resolve_identity
from .a2a_identity import BusError
from .a2a_mailbox import Mailbox
from .goal_supervision import verified_native_caller


def actor_context(bus_root, operator, claimed, native_context, *, endpoint):
    """Return private launch context; never expose credentials as a tool result."""
    verified_native_caller(native_context, claimed)
    if bus_root is None:
        raise BusError('mailbox_host_scope_unavailable', 'Host mailbox delegation requires an explicit bus root.')
    store = BusStore(Path(bus_root))
    # Validate service authority before looking up any peer/native runtime.
    with store.connection(read_only=True) as db:
        store.operator(db, Path(operator))
        if store.recovery_held(db):
            raise BusError('recovery_hold', 'Mailbox authority is held pending recovery reconciliation.')
    Mailbox(store)  # Require prior explicit migration; never silently upgrade.
    identity = resolve_identity('thread:' + claimed, endpoint=endpoint, allow_offline=True)
    if identity.thread_id != claimed:
        raise BusError('identity_unavailable', 'Native runtime differs from the verified caller.')
    cwd = Path(identity.cwd).resolve(strict=True)
    # Serialize first use across MCP processes; issue_actor retains its own DB transaction.
    descriptor = os.open(store.root / 'native-actor-bootstrap.lock',
                         os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, 'a') as lock:
        private_path(store.root / 'native-actor-bootstrap.lock')
        deadline = time.monotonic() + 5
        while True:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise BusError('mailbox_bootstrap_busy', 'Host actor provisioning is busy; retry the same request after it finishes.') from None
                time.sleep(0.02)
        with store.connection(read_only=True) as db:
            store.operator(db, Path(operator))
            roots = [Path(r['root']) for r in db.execute('SELECT root FROM enrollments')
                     if cwd.is_relative_to(Path(r['root']))]
            if not roots:
                raise BusError('mailbox_root_not_enrolled', 'Enroll this project root once with a2a enroll; native identity alone grants no mailbox authority.')
            root = max(roots, key=lambda p: len(p.parts))
            grant = db.execute('SELECT can_send,can_receive FROM enrollments WHERE root=?', (str(root),)).fetchone()
            if not grant['can_send'] and not grant['can_receive']:
                raise BusError('authorization_denied', 'Mailbox enrollment disables both send and receive.')
            row = db.execute('SELECT * FROM actors WHERE namespace=? AND thread_id=?',
                             (identity.namespace, identity.thread_id)).fetchone()
            if row is not None:
                if row['revoked'] or row['root'] != str(root):
                    raise BusError('authorization_denied', 'Existing actor is revoked or differs from the selected enrolled root; operator reconciliation is required.')
                suffix = '' if row['generation'] == 1 else '_g' + str(row['generation'])
                capability = store.root / 'capabilities' / (row['actor_id'] + suffix + '.json')
            else:
                capability = None
        if capability is None:
            capability, _ = store.issue_actor(identity, root, Path(operator))
        # Missing/rotated/revoked credentials never cause automatic re-issuance.
        store.authenticate(capability, identity, invoking_cwd=cwd)
        return dict(bus_root=store.root, capability=capability, cwd=cwd)
