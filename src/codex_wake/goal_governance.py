"""Operator-owned governor switch, independent of watcher health and budgets."""

from contextlib import ExitStack
import hashlib
import json
from pathlib import Path
import time

from . import goal_supervision as supervision
from .permission_enforcement import authorize
from .session_permissions import PermissionDenied, Principal


def sync(receipt):
    """Allocation state is authoritative, including after a partial member write."""
    source = receipt
    if receipt.get("allocation_path"):
        path = Path(receipt["allocation_path"])
        with supervision._lock(path.parent, path.stem):
            supervision._private(path)
            source = json.loads(path.read_text())
    for key in ("governor_enabled", "governor_revision", "governor_control", "request_accounting"):
        if key in source:
            receipt[key] = source[key]
    return receipt.get("governor_enabled", True) is False


def native_operator(root, receipt, native_context, enabled):
    """Only a whole native user message in the exact live caller turn authorizes.

    Claimed roles, tool outputs, quoted instructions and historical user messages
    never confer operator authority. The model mechanically consumes this action.
    """
    caller = supervision.verified_native_caller(native_context, receipt["thread_id"])
    native = supervision._request(
        receipt["grant"],
        "thread/read",
        dict(threadId=receipt["thread_id"], includeTurns=True),
    )["thread"]
    if native.get("id") != receipt["thread_id"]:
        raise PermissionDenied("governor_operator_required")
    turns = [
        turn for turn in native.get("turns", []) if turn.get("id") == caller["turn_id"]
    ]
    command = "Reactivate governor" if enabled else "Deactivate governor"
    if len(turns) != 1 or turns[0].get("status") != "inProgress":
        raise PermissionDenied("governor_operator_required")
    users = [
        item for item in turns[0].get("items", []) if item.get("type") == "userMessage"
    ]
    content = users[0].get("content") if len(users) == 1 else None
    if (
        not isinstance(content, list)
        or len(content) != 1
        or not isinstance(content[0], dict)
        or content[0].get("type") != "text"
        or content[0].get("text") != command
    ):
        raise PermissionDenied("governor_operator_required")
    # A stale caller packet cannot consume an old directive after another turn.
    _, active = supervision._native(receipt["grant"], receipt["thread_id"])
    if active != [caller["turn_id"]]:
        raise PermissionDenied("governor_operator_required")
    return dict(
        source="native_user_message",
        turn_id=caller["turn_id"],
        call_id=caller["call_id"],
    )


def change(
    root, thread, *, enabled, principal=None, native_context=None, allocation_id=None
):
    """Commit one scope switch under the same locks as every controller effect.

    Maintenance fences enrollment/membership. All member locks precede the shared
    ledger lock (the existing poll order), so pending polls either precede the
    durable switch or observe it before any effect. No native work is resumed.
    """
    if type(enabled) is not bool:
        raise ValueError("boolean governor state required")
    directory = supervision._directory(root)
    path = directory / (supervision._name(thread) + ".json")
    notices = []
    with (
        supervision._lock(directory, "recovery"),
        supervision._lock(directory, "maintenance"),
    ):
        supervision._private(path)
        first = json.loads(path.read_text())
        allocation_path = (
            Path(first["allocation_path"]) if first.get("allocation_path") else None
        )
        if allocation_id is not None and allocation_id != first["allocation_id"]:
            raise ValueError("governor selected scope does not match session")
        allocation = None
        if allocation_path:
            expected = supervision._allocation_path(directory, first["allocation_id"])
            if allocation_path != expected:
                raise ValueError("governor allocation scope path changed")
            supervision._private(allocation_path)
            allocation = json.loads(allocation_path.read_text())
            if (
                allocation["allocation_id"] != first["allocation_id"]
                or thread not in allocation["members"]
            ):
                raise ValueError("governor allocation membership changed")
        members = sorted((allocation or {}).get("members", {thread: {}}))
        with ExitStack() as locks:
            for member in members:
                locks.enter_context(
                    supervision._lock(directory, supervision._name(member))
                )
            if allocation_path:
                locks.enter_context(
                    supervision._lock(allocation_path.parent, allocation_path.stem)
                )
                allocation = json.loads(allocation_path.read_text())
                if sorted(allocation["members"]) != members:
                    raise ValueError(
                        "governor scope changed; inspect current allocation"
                    )
            first = json.loads(path.read_text())
            if first["thread_id"] != thread:
                raise ValueError("governor target identity changed")
            if native_context is not None:
                control = native_operator(root, first, native_context, enabled)
                principal = Principal(thread, "operator")
            else:
                if (
                    not isinstance(principal, Principal)
                    or principal.role != "operator"
                    or principal.subject != thread
                ):
                    raise PermissionDenied("governor_operator_required")
                control = dict(source="authenticated_operator")
            permission = authorize(root, "enforcement.disable", principal)
            for member in members:
                authorize(root, "enforcement.disable", Principal(member, "operator"))
            authority = allocation if allocation is not None else first
            revision = authority.get("governor_revision", 0)
            changed = authority.get("governor_enabled", True) != enabled
            if changed:
                revision += 1
                control.update(
                    at=time.time(),
                    revision=revision,
                    enabled=enabled,
                    scope=first["allocation_id"],
                    members=members,
                )
            else:
                control = authority.get("governor_control", control)
            state = dict(
                governor_enabled=enabled,
                governor_revision=revision,
                governor_control=control,
            )
            # Commit scope authority first. A crash leaves disabled member copies
            # repairable from this record, never an active orphaned member.
            if allocation_path:
                allocation.update(state)
                supervision._save(allocation_path, allocation)
            for member in members:
                member_path = directory / (supervision._name(member) + ".json")
                if not member_path.exists():
                    continue
                supervision._private(member_path)
                receipt = json.loads(member_path.read_text())
                if receipt["allocation_id"] != first["allocation_id"]:
                    continue  # historical finalized member, now in another scope
                receipt.update(state)
                kind = "reactivation" if enabled else "deactivation"
                # Record/reconcile the same revision notice on an idempotent retry.
                if revision:
                    supervision._record_supervision_notice(member_path, receipt, kind)
                    event = receipt.get("notice_ids", {}).get(kind)
                    if event:
                        notices.append(event)
                supervision._save(member_path, receipt)
                if member == thread:
                    first = receipt
    # Delivery is separate from effective state and needs no running watcher.
    from .goal_notices import present_notice, governor_status

    presentation = []
    for event in notices:
        try:
            notice = present_notice(root, event)
            presentation.append(dict(event_id=event, state=notice["delivery"]["state"]))
        except Exception as error:
            presentation.append(
                dict(event_id=event, state="unavailable", error=type(error).__name__)
            )
    return dict(
        supervision._public(first),
        governor=governor_status(root, first),
        changed=changed,
        permission=permission,
        notices=presentation,
        members=members,
        resumed=False,
        renewed_resources=False,
        controller=supervision._heartbeat(directory),
        message=(
            "Governor inactive in this scope. Drop stale governor checkpoint/stop instructions; "
            "independent platform controls remain. Accounting and checkpoints are preserved; "
            "no work is resumed and no resources renewed."
            if not enabled
            else f"Governor reactivated in this scope in {first.get('request_accounting',{}).get('mode','sampled_stop')} mode; no work resumed or resources renewed."
        ),
    )


def snapshot(root, thread_id):
    """Read-only host snapshot for a first dispatch intent, never a work gate.

    Callers retain this original snapshot on retry; fresh scope authority wins at
    effect boundaries. Unknown availability neither enables nor disables work.
    """
    try:
        name = supervision._name(thread_id)
        root = Path(root).absolute()
        if root != root.resolve():
            raise ValueError("noncanonical root")
        supervision._private(root, True)
        directory = root / "goal-supervision"
        supervision._private(directory, True)
        path = directory / (name + ".json")
        supervision._private(path)
        receipt = json.loads(path.read_text())
        if receipt["thread_id"] != thread_id:
            raise ValueError("session identity changed")
        authority, source = receipt, "session_receipt"
        if receipt.get("allocation_path"):
            expected = (
                directory
                / "allocations"
                / (
                    hashlib.sha256(receipt["allocation_id"].encode()).hexdigest()
                    + ".json"
                )
            )
            if (
                Path(receipt["allocation_path"]) != expected
                or expected.resolve() != expected
            ):
                raise ValueError("allocation scope path changed")
            supervision._private(expected)
            authority = json.loads(expected.read_text())
            if (
                authority["allocation_id"] != receipt["allocation_id"]
                or thread_id not in authority["members"]
            ):
                raise ValueError("allocation membership changed")
            source = "allocation_ledger"
        enabled = authority.get("governor_enabled", True)
        if type(enabled) is not bool:
            raise ValueError("invalid governor control state")
        return dict(
            state="available",
            enabled=enabled,
            mode=authority.get("request_accounting",{}).get("mode","sampled_stop") if enabled else "inactive",
            revision=authority.get("governor_revision", 0),
            scope=receipt["allocation_id"],
            thread_id=thread_id,
            source=source,
            observed_at=time.time(),
        )
    except (OSError, ValueError, KeyError, TypeError) as error:
        return dict(
            state="unavailable",
            enabled=None,
            mode="unknown",
            thread_id=thread_id,
            reason=type(error).__name__,
            observed_at=time.time(),
        )
