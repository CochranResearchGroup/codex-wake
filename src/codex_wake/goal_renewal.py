"""Explicit, operation-bound external budget renewal; native usage is never reset.

The common attention queue owns decisions. Files here are application journals,
not another approval queue. Host adapters supply verified Principal objects.
"""

from contextlib import ExitStack, contextmanager
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import time
from uuid import uuid4

from . import goal_supervision as supervision
from .attention_queue import AttentionQueue, fingerprint
from .goal_usage import observe_usage
from .permission_enforcement import authorize
from .records import WakeError
from .session_permissions import PermissionStore, Principal


class RenewalError(WakeError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def _fail(code, message):
    raise RenewalError(code, message)


def _now():
    from .lifecycle_budget import trusted_upper

    return trusted_upper()


def _number(value, label, *, integer=False):
    if (
        type(value) not in ((int,) if integer else (int, float))
        or not math.isfinite(value)
        or value <= 0
    ):
        _fail("renewal_invalid", "positive finite " + label + " required")
    return value


def _principal(principal, thread):
    if not isinstance(principal, Principal) or principal.subject != thread:
        _fail(
            "renewal_identity_unverified", "verified exact-session principal required"
        )


def _read(path):
    supervision._private(path)
    try:
        value = json.loads(path.read_text())
    except (ValueError, OSError):
        _fail(
            "renewal_store_unavailable",
            "retained state is unreadable; reconcile without replay",
        )
    return value


def _journal_path(directory, identifier):
    if (
        not isinstance(identifier, str)
        or not identifier.startswith("renewal_")
        or len(identifier) != 72
    ):
        _fail("renewal_invalid", "exact renewal identity required")
    child = directory / "renewals"
    child.mkdir(mode=0o700, exist_ok=True)
    supervision._private(child, True)
    return child / (identifier + ".json")


def _id(thread, operation_id):
    if not isinstance(operation_id, str) or not operation_id or len(operation_id) > 256:
        _fail("renewal_invalid", "stable bounded operation identity required")
    return (
        "renewal_" + hashlib.sha256((thread + "\0" + operation_id).encode()).hexdigest()
    )


@contextmanager
def _campaign(root, policy, thread):
    directory = supervision._directory(root)
    with supervision._lock(directory, "maintenance"):
        path = directory / (supervision._name(thread) + ".json")
        first = _read(path)
        allocation_path = (
            Path(first["allocation_path"]) if first.get("allocation_path") else None
        )
        allocation = _read(allocation_path) if allocation_path else None
        members = sorted(allocation["members"]) if allocation else [thread]
        if any(
            "finalized_charges" in item
            for item in (allocation or {}).get("members", {}).values()
        ):
            _fail(
                "renewal_finalized_members",
                "retired shared members require explicit allocation reconciliation",
            )
        with ExitStack() as locks:
            for member in members:
                locks.enter_context(
                    supervision._lock(directory, supervision._name(member))
                )
            if allocation_path:
                locks.enter_context(
                    supervision._lock(allocation_path.parent, allocation_path.stem)
                )
                allocation = _read(allocation_path)
                if sorted(allocation["members"]) != members:
                    _fail("renewal_stale", "allocation member set changed")
            receipts = {
                member: _read(directory / (supervision._name(member) + ".json"))
                for member in members
            }
            for member, receipt in receipts.items():
                if (
                    receipt["thread_id"] != member
                    or receipt["allocation_id"] != first["allocation_id"]
                ):
                    _fail("renewal_stale", "allocation member identity changed")
                grant = supervision._grant(policy, member, first["allocation_id"], root)
                if grant != receipt["grant"]:
                    _fail(
                        "renewal_policy_changed",
                        "host policy changed; renewal cannot override it",
                    )
            yield directory, receipts, allocation_path, allocation


def _native_caller(native_context, thread):
    if native_context is None:
        return None
    return supervision.verified_native_caller(native_context, thread)


def _attested_operator_reply(receipt, active, caller, goal):
    """Exclude only the host-attested later reply from captured campaign work.

    A claimed turn argument is never accepted. Native metadata, the exact active
    turn and retained proof that the original campaign stopped must all agree.
    Peers and every historical campaign work turn remain outside this exception.
    """
    if (
        not caller
        or caller["thread_id"] != receipt["thread_id"]
        or active != [caller["turn_id"]]
        or goal.get("createdAt") != receipt["goal_created_at"]
    ):
        return False
    episodes = [receipt] + [
        entry["previous"] for entry in receipt.get("budget_history", [])
    ]
    campaign_turns = {
        turn for episode in episodes for turn in episode.get("stop_turns", [])
    }
    stopped = any(
        episode.get("stop_latched") is True
        and episode.get("stop_proof") is True
        and episode.get("pause_observed") is True
        for episode in episodes
    )
    return stopped and caller["turn_id"] not in campaign_turns


def _snapshot(root, receipts, allocation, *, caller=None):
    now = _now()
    directory = supervision._directory(root)
    from .goal_maintenance import admission_guard

    admission_guard(directory)
    controller = supervision._heartbeat(directory)
    if not controller.get("fresh"):
        _fail(
            "renewal_controller_unavailable",
            "a fresh independent configured watcher is required",
        )
    if allocation and allocation.get("boot_id") != supervision.boot_id_value():
        _fail("renewal_boot_changed", "shared allocation boot identity changed")
    observations = {}
    goals = {}
    charges = {}
    for thread, receipt in receipts.items():
        if receipt.get("renewal_pending") or (allocation or {}).get("renewal_pending"):
            _fail(
                "renewal_pending",
                "an interrupted renewal must be reconciled before new work",
            )
        from .permission_enforcement import controller_permission

        if controller_permission(root, receipt)["permission"] not in (
            "allow",
            "legacy",
        ):
            _fail(
                "renewal_permission_revoked",
                "current enforcement enrollment permission is revoked",
            )
        first_stop = receipt.get("first_stop", {})
        replaced_exhaustion = (
            receipt.get("reason") == "controller_stopped"
            and first_stop.get("reason") == "allocation_exhausted"
            and first_stop.get("controller_generation")
            and controller.get("generation") != first_stop["controller_generation"]
            and receipt.get("stop_proof") is True
            and receipt.get("pause_observed") is True
            and not any(
                receipt.get(key)
                for key in ("winddown_reason", "observation_error", "control_error")
            )
        )
        if (
            receipt.get("stop_latched")
            and receipt.get("reason")
            not in (
                "allocation_exhausted",
                "continuation_held",
            )
            and not replaced_exhaustion
        ):
            _fail(
                "renewal_fault_held",
                "resource renewal cannot recover a different current supervision fault",
            )
        if receipt.get("stop_latched") and receipt.get("first_stop", {}).get(
            "reason", receipt.get("reason")
        ) not in ("allocation_exhausted", "continuation_held"):
            _fail(
                "renewal_fault_held",
                "resource renewal cannot clear an unrelated supervision fault",
            )
        if receipt["boot_id"] != supervision.boot_id_value():
            _fail("renewal_boot_changed", "budget boot identity changed")
        elapsed = time.clock_gettime(time.CLOCK_BOOTTIME) - receipt["started_boottime"]
        if elapsed < 0 or now < receipt["started_upper"]:
            _fail("renewal_clock_unqualified", "nondecreasing qualified clock required")
        goal, active = supervision._native(receipt["grant"], thread)
        if (
            not goal
            or goal.get("threadId") != thread
            or goal.get("status") != "paused"
            or (active and not _attested_operator_reply(receipt, active, caller, goal))
        ):
            _fail(
                "renewal_native_not_paused",
                "pause the exact goal and finish its captured work before renewal",
            )
        goals[thread] = dict(
            thread_id=thread, created_at=goal["createdAt"], status=goal["status"]
        )
        member = allocation["members"][thread] if allocation else receipt
        observation = observe_usage(
            receipt["grant"]["codex_home"],
            thread,
            member["goal_created_at"],
            reset_anchor=member.get("reset_anchor"),
            token_accounting=receipt.get("token_accounting", "cache_inclusive"),
        )
        if observation.get("state") != "qualified" or not observation.get("anchor"):
            _fail(
                "renewal_accounting_unavailable",
                "complete qualified all-member accounting required",
            )
        observations[thread] = observation
        for key, value in observation["charges"].items():
            if key in charges and charges[key] != value:
                _fail(
                    "renewal_accounting_conflict", "shared response evidence conflicts"
                )
            charges[key] = value
    prior = (
        allocation["charges"]
        if allocation
        else next(iter(receipts.values())).get("accounting", {}).get("charges", {})
    )
    if any(charges.get(key) != value for key, value in prior.items()):
        _fail("renewal_accounting_changed", "retained charge evidence changed")
    used = sum(value["tokens"] for value in charges.values())
    if any(used < receipt["used_tokens"] for receipt in receipts.values()):
        _fail("renewal_accounting_decreased", "qualified spending decreased")
    return dict(
        now=now,
        controller=controller,
        observations=observations,
        goals=goals,
        charges=charges,
        used_tokens=used,
    )


def _binding(receipts, allocation, goals):
    return dict(
        members=sorted(receipts),
        goals=goals,
        allocation_id=next(iter(receipts.values()))["allocation_id"],
        members_state={
            thread: {
                key: receipt.get(key)
                for key in (
                    "generation",
                    "budget_revision",
                    "enrollment_revision",
                    "token_limit",
                    "deadline",
                    "time_origin",
                    "token_accounting",
                    "boot_id",
                )
            }
            for thread, receipt in receipts.items()
        },
        allocation_generation=(allocation or {}).get("generation"),
        allocation_revision=(allocation or {}).get("budget_revision", 1),
    )


def _context(root, proposal):
    policy = PermissionStore(root)
    revision = policy._read()["revision"] if policy.active() else 1
    return dict(
        owner=proposal["thread_id"],
        operation_id=proposal["operation_id"],
        attempt=1,
        task_id=proposal["task_id"],
        allocation_id=proposal["binding"]["allocation_id"],
        runtime="codex",
        conversation_id=proposal["thread_id"],
        account="local-native",
        target=proposal["thread_id"],
        action="enforcement.increase",
        effect_scope=proposal["fingerprint"],
        policy_root=str(policy.root),
        policy_revision=revision,
        operation_state="blocked",
    )


def _public(journal):
    return {
        key: deepcopy(journal[key])
        for key in ("proposal_id", "fingerprint", "proposal", "attention", "status")
        if key in journal
    }


def propose(
    root,
    policy,
    thread,
    *,
    principal,
    operation_id,
    mode,
    token_limit,
    expires_at,
    deadline=None,
    remaining_seconds=None,
    shared=False,
    resume=False,
    task_id=None,
    native_context=None,
):
    """Freeze an exact proposal. This grants no resources and never resumes work."""
    _principal(principal, thread)
    authorize(root, "session.inspect", principal)
    caller = _native_caller(native_context, thread)
    if mode not in ("extend", "reset"):
        _fail("renewal_invalid", "mode must be extend or reset")
    _number(token_limit, "token limit", integer=True)
    _number(expires_at, "proposal expiry")
    if type(shared) is not bool or type(resume) is not bool:
        _fail("renewal_invalid", "explicit shared scope and resume choice required")
    if (deadline is None) == (remaining_seconds is None):
        _fail(
            "renewal_invalid",
            "provide one absolute deadline or remaining-seconds grant",
        )
    identifier = _id(thread, operation_id)
    intent = dict(
        mode=mode,
        token_limit=token_limit,
        deadline=deadline,
        remaining_seconds=remaining_seconds,
        expires_at=expires_at,
        shared=shared,
        resume=resume,
        task_id=task_id,
    )
    with _campaign(root, policy, thread) as (
        directory,
        receipts,
        allocation_path,
        allocation,
    ):
        path = _journal_path(directory, identifier)
        if path.exists():
            prior = _read(path)
            if prior["intent"] != intent:
                _fail(
                    "renewal_operation_conflict",
                    "operation already names a different proposal",
                )
            return _public(prior)
        snapshot = _snapshot(root, receipts, allocation, caller=caller)
        if not snapshot["now"] < expires_at <= snapshot["now"] + 3600:
            _fail("renewal_invalid", "proposal expiry must be within the next hour")
        if len(receipts) > 1 and not shared:
            _fail(
                "renewal_shared_scope_required",
                "explicit shared-allocation authority is required",
            )
        receipt = receipts[thread]
        target_deadline = (
            _number(deadline, "absolute deadline")
            if deadline is not None
            else snapshot["now"]
            + _number(remaining_seconds, "remaining seconds", integer=True)
        )
        if mode == "extend" and (
            token_limit < receipt["token_limit"]
            or target_deadline < receipt["deadline"]
        ):
            _fail("renewal_invalid", "extension cannot lower a ceiling or deadline")
        window_used = snapshot["used_tokens"] if mode == "extend" else 0
        if target_deadline <= snapshot["now"] or token_limit <= window_used:
            _fail("renewal_invalid", "renewal must leave positive time and tokens")
        for member in receipts.values():
            if (
                token_limit > member["grant"]["max_tokens"]
                or target_deadline
                - (member["time_origin"] if mode == "extend" else snapshot["now"])
                > member["grant"]["max_seconds"]
            ):
                _fail("renewal_host_ceiling", "proposal exceeds hard host ceilings")
        proposal = dict(
            thread_id=thread,
            operation_id=operation_id,
            mode=mode,
            native_proposal_caller=caller,
            task_id=task_id or "goal-renewal",
            binding=_binding(receipts, allocation, snapshot["goals"]),
            old=dict(
                token_limit=receipt["token_limit"],
                deadline=receipt["deadline"],
                used_tokens=snapshot["used_tokens"],
                revision=receipt.get("budget_revision", 1),
                generation=receipt["generation"],
            ),
            new=dict(
                token_limit=token_limit,
                deadline=target_deadline,
                used_tokens=window_used,
                remaining_tokens=token_limit - window_used,
                revision=receipt.get("budget_revision", 1) + 1,
                generation=receipt["generation"] if mode == "extend" else uuid4().hex,
            ),
            expires_at=expires_at,
            shared=shared,
            resume=resume,
        )
        digest = fingerprint(proposal)
        proposal["fingerprint"] = digest
        journal = dict(
            version=1,
            proposal_id=identifier,
            fingerprint=digest,
            intent=intent,
            proposal=proposal,
            status="proposed",
        )
        supervision._save(path, journal)
        context = _context(root, proposal)
        journal["context"] = context
        attention = AttentionQueue(
            root, now=_now, context_validator=lambda row: context
        )
        journal["attention"] = attention.request(
            principal,
            dict(
                key=identifier,
                kind="decision",
                question="Apply external budget "
                + mode
                + "? "
                + json.dumps(
                    dict(
                        old=proposal["old"],
                        new=proposal["new"],
                        members=proposal["binding"]["members"],
                        resume=resume,
                    ),
                    sort_keys=True,
                ),
                options=["accept", "decline"],
                evidence=["renewal:" + identifier, "fingerprint:" + digest],
                priority="high",
                expires_at=expires_at,
                context=context,
                permission_decision=False,
            ),
        )
        supervision._save(path, journal)
        return _public(journal)


def apply(
    root,
    policy,
    thread,
    proposal_id,
    *,
    principal,
    expected_fingerprint,
    explicit=False,
    native_context=None,
):
    """Apply exact verified operator authority, preserving lifetime history."""
    _principal(principal, thread)
    caller = _native_caller(native_context, thread)
    directory = supervision._directory(root)
    with supervision._lock(directory, "renewal-applications"):
        path = _journal_path(directory, proposal_id)
        journal = _read(path)
        if (
            journal["proposal"]["thread_id"] != thread
            or journal["fingerprint"] != expected_fingerprint
        ):
            _fail(
                "renewal_proposal_mismatch",
                "inspect the exact current proposal before applying",
            )
        if journal["status"] == "applied":
            return (
                _resume(root, policy, thread, path, journal, principal, caller=caller)
                if journal["proposal"]["resume"]
                else deepcopy(journal["result"])
            )
        if journal["status"] in ("authorized", "applying"):
            return _reconcile_application(
                root, policy, thread, path, journal, principal, caller=caller
            )
        if journal["status"] != "proposed":
            _fail(
                "renewal_pending",
                "interrupted application requires reconciliation without a new proposal",
            )
        with _campaign(root, policy, thread) as (
            _,
            receipts,
            allocation_path,
            allocation,
        ):
            snapshot = _snapshot(root, receipts, allocation, caller=caller)
            proposal = journal["proposal"]
            if _now() >= proposal["expires_at"]:
                _fail("renewal_expired", "proposal expired; authority was not changed")
            if _binding(receipts, allocation, snapshot["goals"]) != proposal["binding"]:
                _fail(
                    "renewal_stale",
                    "goal, allocation, membership or budget revision changed",
                )
            if _context(root, proposal) != journal["context"]:
                _fail(
                    "renewal_policy_changed", "permission policy changed since proposal"
                )
            context = journal["context"]
            queue = AttentionQueue(
                root, now=_now, context_validator=lambda row: context
            )
            row = queue.inspect(principal, journal["attention"]["request_id"])
            if explicit:
                if principal.role != "operator":
                    _fail(
                        "renewal_operator_required",
                        "a model directive cannot approve more resources",
                    )
                if row["status"] == "open":
                    row = queue.respond(
                        principal,
                        row["request_id"],
                        "accept",
                        expected_revision=row["revision"],
                        expected_fingerprint=row["fingerprint"],
                    )
            if row["status"] != "responded" or row["response"]["choice"] != "accept":
                _fail(
                    "renewal_approval_required",
                    "exact current operator acceptance required",
                )
            # Only AttentionQueue.respond can create this authenticated operator response.
            authority = Principal(thread, "operator")
            decisions = {
                member: authorize(
                    root,
                    "enforcement.increase",
                    Principal(member, "operator"),
                    task_id=proposal["task_id"],
                    operation_id=proposal["operation_id"],
                )
                for member in receipts
            }
            approval = dict(
                request_id=row["request_id"],
                response_id=row["response"]["response_id"],
                fingerprint=row["fingerprint"],
                choice="accept",
                grants_permission=False,
            )
            targets = {}
            for member, receipt in receipts.items():
                target = deepcopy(receipt)
                target.setdefault("budget_history", []).append(
                    dict(
                        operation=proposal_id,
                        previous={
                            key: deepcopy(value)
                            for key, value in supervision._public(receipt).items()
                            if key != "budget_history"
                        },
                        approved_by=row["response"],
                    )
                )
                target.update(
                    token_limit=proposal["new"]["token_limit"],
                    deadline=proposal["new"]["deadline"],
                    time_limit_seconds=proposal["new"]["deadline"]
                    - receipt["time_origin"],
                    used_tokens=snapshot["used_tokens"],
                    budget_revision=proposal["new"]["revision"],
                    state="armed",
                    reason=None,
                    stop_latched=False,
                    checkpoint=None,
                    renewal_approval=approval,
                    renewal_permission=decisions[member],
                    lifetime_used_tokens=receipt.get("lifetime_tokens_before_window", 0)
                    + snapshot["used_tokens"],
                )
                for key in (
                    "first_stop",
                    "stop_turns",
                    "stop_proof",
                    "pause_observed",
                    "pause_epoch",
                    "winddown_deadline",
                    "winddown_reason",
                    "allocation_winddown_deadline",
                    "allocation_first_stop",
                ):
                    target.pop(key, None)
                target["effects"] = {}
                target["enrollment_revision"] = (
                    receipt.get("enrollment_revision", 1) + 1
                )
                target.pop("poll_ack", None)
                if proposal["mode"] == "reset":
                    target.update(
                        generation=proposal["new"]["generation"],
                        time_origin=snapshot["now"],
                        started_upper=snapshot["now"],
                        started_boottime=time.clock_gettime(time.CLOCK_BOOTTIME),
                        used_tokens=0,
                        reset_anchor=snapshot["observations"][member]["anchor"],
                        lifetime_tokens_before_window=receipt.get(
                            "lifetime_tokens_before_window", 0
                        )
                        + snapshot["used_tokens"],
                        time_limit_seconds=proposal["new"]["deadline"]
                        - snapshot["now"],
                    )
                target["accounting"] = (
                    dict(
                        state="qualified",
                        used_tokens=snapshot["used_tokens"],
                        member_thread_ids=sorted(receipts),
                        token_accounting=receipt["token_accounting"],
                        renewed_out_tokens=0,
                    )
                    if allocation
                    else snapshot["observations"][member]
                )
                if proposal["mode"] == "reset":
                    target["accounting"] = dict(
                        state="qualified",
                        used_tokens=0,
                        token_accounting=receipt["token_accounting"],
                        charges={},
                        anchor=snapshot["observations"][member]["anchor"],
                    )
                targets[member] = target
            allocation_target = deepcopy(allocation)
            if allocation_target:
                allocation_target.setdefault("budget_history", []).append(
                    dict(
                        operation=proposal_id,
                        previous={
                            key: deepcopy(value)
                            for key, value in allocation.items()
                            if key != "budget_history"
                        },
                    )
                )
                allocation_target.update(
                    token_limit=proposal["new"]["token_limit"],
                    deadline=proposal["new"]["deadline"],
                    time_limit_seconds=proposal["new"]["deadline"]
                    - allocation["time_origin"],
                    used_tokens=snapshot["used_tokens"],
                    charges=snapshot["charges"],
                    stop_latched=False,
                    budget_revision=proposal["new"]["revision"],
                )
                if proposal["mode"] == "reset":
                    allocation_target.update(
                        generation=proposal["new"]["generation"],
                        time_origin=snapshot["now"],
                        time_limit_seconds=proposal["new"]["deadline"]
                        - snapshot["now"],
                        used_tokens=0,
                        charges={},
                    )
                    for member in allocation_target["members"]:
                        allocation_target["members"][member]["reset_anchor"] = snapshot[
                            "observations"
                        ][member]["anchor"]
                for key in ("first_stop", "stop_reason", "winddown_deadline"):
                    allocation_target.pop(key, None)
            result = dict(
                status="applied",
                proposal_id=proposal_id,
                fingerprint=expected_fingerprint,
                mode=proposal["mode"],
                resumed=False,
                old=proposal["old"],
                new=dict(
                    proposal["new"],
                    used_tokens=targets[thread]["used_tokens"],
                    remaining_tokens=proposal["new"]["token_limit"]
                    - targets[thread]["used_tokens"],
                ),
                members=sorted(receipts),
                approval=approval,
                generation=targets[thread]["generation"],
            )
            if proposal["resume"]:
                result["resume_state"] = "awaiting_first_poll"
                result["next_action"] = (
                    "Wait for the configured watcher acknowledgement, then apply this same approved proposal again."
                )
            journal.update(
                status="authorized",
                targets=targets,
                allocation_target=allocation_target,
                approval=approval,
                sources=deepcopy(receipts),
                allocation_source=deepcopy(allocation),
                result=result,
                accepted_at=_now(),
                native_application_caller=caller,
                response=deepcopy(row["response"]),
            )
            supervision._save(path, journal)
            journal["consumption"] = queue.consume(
                authority,
                row["request_id"],
                expected_revision=row["revision"],
                expected_fingerprint=row["fingerprint"],
            )
            journal["status"] = "applying"
            supervision._save(path, journal)
            _commit_targets(directory, path, journal, allocation_path)
            return deepcopy(result)


def _commit_targets(directory, path, journal, allocation_path):
    identifier = journal["proposal_id"]
    for member, receipt in journal["sources"].items():
        supervision._save(
            directory / (supervision._name(member) + ".json"),
            dict(receipt, renewal_pending=identifier),
        )
    if allocation_path:
        supervision._save(
            allocation_path,
            dict(journal["allocation_source"], renewal_pending=identifier),
        )
    for member, target in journal["targets"].items():
        supervision._save(directory / (supervision._name(member) + ".json"), target)
    if allocation_path:
        supervision._save(allocation_path, journal["allocation_target"])
    journal["status"] = "applied"
    supervision._save(path, journal)


def _reconcile_application(
    root, policy, thread, path, journal, principal, *, caller=None
):
    """Complete only the recorded filesystem transaction; no new allowance/effect."""
    with _campaign(root, policy, thread) as (
        directory,
        receipts,
        allocation_path,
        allocation,
    ):
        if sorted(receipts) != sorted(journal["sources"]):
            _fail("renewal_stale", "interrupted renewal member set changed")
        sources = journal["sources"]
        targets = journal["targets"]

        def is_target(receipt, target):
            return all(
                receipt.get(key) == target.get(key)
                for key in (
                    "generation",
                    "enrollment_revision",
                    "budget_revision",
                    "token_limit",
                    "deadline",
                    "reset_anchor",
                    "renewal_approval",
                    "lifetime_tokens_before_window",
                )
            )

        all_applied = all(
            is_target(receipts[member], targets[member]) for member in receipts
        )
        allocation_applied = allocation is None or all(
            allocation.get(key) == journal["allocation_target"].get(key)
            for key in (
                "generation",
                "budget_revision",
                "token_limit",
                "deadline",
                "members",
            )
        )
        if (
            all_applied
            and allocation_applied
            and not (allocation or {}).get("renewal_pending")
        ):
            journal["status"] = "applied"
            supervision._save(path, journal)
            return deepcopy(journal["result"])
        for member, receipt in receipts.items():
            if receipt not in (
                sources[member],
                dict(sources[member], renewal_pending=journal["proposal_id"]),
                targets[member],
            ):
                _fail(
                    "renewal_reconciliation_conflict",
                    "current receipt differs from recorded source/target; preserve it for operator reconciliation",
                )
        if allocation not in (
            journal["allocation_source"],
            dict(
                journal["allocation_source"] or {},
                renewal_pending=journal["proposal_id"],
            ),
            journal["allocation_target"],
        ):
            _fail(
                "renewal_reconciliation_conflict",
                "allocation differs from recorded transaction",
            )
        snapshot = _snapshot(root, sources, journal["allocation_source"], caller=caller)
        if (
            _binding(sources, journal["allocation_source"], snapshot["goals"])
            != journal["proposal"]["binding"]
        ):
            _fail("renewal_stale", "native goal changed during interrupted application")
        if _context(root, journal["proposal"]) != journal["context"]:
            _fail(
                "renewal_policy_changed",
                "permission policy changed during interrupted application",
            )
        if snapshot["now"] >= journal["proposal"]["new"]["deadline"]:
            _fail(
                "renewal_expired",
                "recorded new deadline already elapsed; do not manufacture another window",
            )
        for member in receipts:
            authorize(
                root,
                "enforcement.increase",
                Principal(member, "operator"),
                task_id=journal["proposal"]["task_id"],
                operation_id=journal["proposal"]["operation_id"],
            )
        queue = AttentionQueue(
            root, now=_now, context_validator=lambda row: journal["context"]
        )
        row = queue.inspect(principal, journal["attention"]["request_id"])
        if row.get("response") != journal["response"] or row["status"] not in (
            "responded",
            "consumed",
        ):
            _fail(
                "renewal_approval_required",
                "recorded operator response no longer reconciles",
            )
        if row["status"] == "responded":
            journal["consumption"] = queue.consume(
                Principal(thread, "operator"),
                row["request_id"],
                expected_revision=row["revision"],
                expected_fingerprint=row["fingerprint"],
            )
        journal["status"] = "applying"
        supervision._save(path, journal)
        _commit_targets(directory, path, journal, allocation_path)
        return deepcopy(journal["result"])


def renewal_hold(root, receipt):
    """Primary controller calls before enrollment, accounting, or native effects."""
    pending = receipt.get("renewal_pending")
    if receipt.get("allocation_path"):
        pending = pending or _read(Path(receipt["allocation_path"])).get(
            "renewal_pending"
        )
    if pending:
        return dict(
            state="held",
            reason="renewal_pending",
            armed=False,
            proposal_id=pending,
            next_action="Reconcile the same approved renewal operation; do not enroll, reset or replay it under a new identity.",
        )
    return None


def _resume(root, policy, thread, path, journal, principal, *, caller=None):
    """Reconcile one approved resume; never replay an uncertain native effect."""
    result = deepcopy(journal["result"])
    if result.get("resumed"):
        return result
    with _campaign(root, policy, thread) as (_, receipts, allocation_path, allocation):
        if (allocation or next(iter(receipts.values()))).get('governor_enabled',True) is False:
            result['resume_state'] = 'governor_inactive'
            result['next_action'] = 'Governor was deactivated; this queued resume cannot start work. Reactivation does not itself authorize resume.'
            return result
        now = _now()
        controller = supervision._heartbeat(supervision._directory(root))
        if not controller.get("fresh"):
            result["resume_state"] = "watcher_unavailable"
            return result
        for member, receipt in receipts.items():
            if (
                receipt.get("budget_revision") != journal["proposal"]["new"]["revision"]
                or receipt.get("renewal_approval") != journal["approval"]
            ):
                _fail(
                    "renewal_stale",
                    "approved resume belongs to a previous budget revision",
                )
            ack = receipt.get("poll_ack", {})
            age = time.clock_gettime(time.CLOCK_BOOTTIME) - ack.get(
                "observed_boottime", -1e30
            )
            if (
                ack.get("enrollment_revision") != receipt.get("enrollment_revision")
                or ack.get("receipt_generation") != receipt["generation"]
                or ack.get("controller_generation") != controller.get("generation")
                or age < 0
                or age > max(3, 3 * controller.get("interval", 1))
            ):
                result["resume_state"] = "awaiting_first_poll"
                result["next_action"] = (
                    "Wait for the configured watcher acknowledgement, then apply this same approved proposal again; do not request another approval."
                )
                return result
            if (
                now >= receipt["deadline"]
                or receipt["used_tokens"] >= receipt["token_limit"]
                or receipt.get("stop_latched")
            ):
                _fail(
                    "renewal_resume_held",
                    "fresh budget has no usable continuation allowance",
                )
        # Requalify original files, boot, paused goal and shared accounting immediately
        # before each first attempt. After an uncertain attempt use readback only.
        effects = journal.setdefault("resume_effects", {})
        if not effects:
            _snapshot(root, receipts, allocation, caller=caller)
        for member, receipt in receipts.items():
            effect = effects.get(member)
            if effect:
                goal, active = supervision._native(receipt["grant"], member)
                if (
                    goal
                    and goal.get("createdAt")
                    == journal["proposal"]["binding"]["goals"][member]["created_at"]
                    and goal.get("status") == "active"
                ):
                    effect["state"] = "verified"
                elif effect["state"] != "verified":
                    result["resume_state"] = "uncertain"
                    supervision._save(path, journal)
                    return result
                continue
            goal, active = supervision._native(receipt["grant"], member)
            if (
                not goal
                or (
                    active
                    and not _attested_operator_reply(receipt, active, caller, goal)
                )
                or goal.get("status") != "paused"
                or goal.get("createdAt")
                != journal["proposal"]["binding"]["goals"][member]["created_at"]
            ):
                _fail(
                    "renewal_resume_held",
                    "exact paused goal proof changed before resume",
                )
            authorize(
                root,
                "enforcement.increase",
                Principal(member, "operator"),
                task_id=journal["proposal"]["task_id"],
                operation_id=journal["proposal"]["operation_id"],
            )
            effect = effects[member] = dict(
                state="intended",
                goal_created_at=journal["proposal"]["binding"]["goals"][member][
                    "created_at"
                ],
            )
            supervision._save(path, journal)
            try:
                supervision._request(
                    receipt["grant"],
                    "thread/goal/set",
                    dict(threadId=member, status="active"),
                )
            except Exception:
                effect["state"] = "uncertain"
            else:
                effect["state"] = "acknowledged"
            supervision._save(path, journal)
            goal, active = supervision._native(receipt["grant"], member)
            if (
                goal
                and goal.get("createdAt") == effect["goal_created_at"]
                and goal.get("status") == "active"
            ):
                effect["state"] = "verified"
            else:
                result["resume_state"] = "uncertain"
                supervision._save(path, journal)
                return result
        result.update(resumed=True, resume_state="verified")
        journal["result"] = result
        supervision._save(path, journal)
        return deepcopy(result)
