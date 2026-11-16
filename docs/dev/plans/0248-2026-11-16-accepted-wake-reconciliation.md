# Accepted wake completion reconciliation

State: OPEN
Work item: LOCAL-WAKE-ACCEPTED-RECONCILIATION (IN_PROGRESS)
Owner: root / ecochran76
Priority: P1
Branch: fix/accepted-wake-reconciliation
Base: 12345152

## Current State

Installed dev39 retains the observed gap: explicit native reconcile skips accepted
submissions. Registration reports peer_history_reconciliation_required while
terminal evidence is absent. Automatic due-time admission can reconcile these
records, so the prior413-record snapshot is not a migration requirement.

## Scope and acceptance

User authorized continuing diagnosis and repair. One serial lane, WIP1.
Extend the public native reconcile command to inspect accepted submissions and
publish the existing bound terminal-evidence receipt only after exact native
completion evidence. Preserve original record bytes, target, submission, status,
expiry, attempts and acceptance. Unknown/nonterminal evidence remains held.
Reuse the existing native_evidence public seam and terminal receipt format.
Regression at CLI + registration readiness observes hold, explicit reconciliation,
then readiness; synthetic native protocol only. No native input or resend.

No bulk production migration, runtime installation, service changes, native daemon
restart, or deadline extension. Historical missing CLI remains unavailable unless
an existing qualified transport is available; no automatic account fallback.
No external tracker mutation authorized: local work item records this packet.

## Execution and validation

Red/green at public CLI and readiness seams; one narrow implementation followed
by focused native delivery/peer admission/reconciliation checks. Local CI checks
replace hosted CI; record exact commands, source SHA and environment differences.
Discovery bound: relevant two modules and existing native delivery fixtures,
expand only for a failed invariant. Retain private incident data outside Git.
Definition of done: focused tests pass, source checkpoint published and reviewed;
report installed runtime separately. Checkout retained only for active testing
until published custody or explicit bounded handoff; review at source closeout.

## Source validation checkpoint

Public CLI regression red: original command skipped accepted submission and
readiness stayed held. First environment invocation lacked websockets; rerun in
the installed dev39 Python3.12 environment reproduced the actual held assertion.
Green: test_native_delivery, test_wake_mode_runtime,
test_native_reconcile_discovery:33 tests PASS7.332s, PYTHONPATH=src:tests.
Pinned ruff0.14.2 F821/F822/F823 all source/scripts/tests/hooks PASS; policy wiring
PASS; diff whitespace PASS. Synthetic external native boundary only. Python3.11,
full suite, installed-wheel acceptance and hosted CI not run. No daemon changes.
Self-review against base12345152: standards and spec pass for bounded command
repair; terminal identity and deduplication use existing adapter validation.
Original records remain byte-identical; unfinished and wrong-thread evidence
remain held; replay reuses the bound receipt. No temporary DEBUG logging added.

## Evidenced scope refinement

One original peer reconciled live; readiness changed held to ready, no dispatch,
original SHA256 unchanged. A bounded active-conversation pass inspected39 peers:
9 more verified,30 unresolved, all30 original executables removed by upgrades.
Expose explicit --read-codex-path using the existing qualified _peer_read_target
mechanism. Red at CLI rejects the new argument; green must qualify ownership,
mode/executable/absolute path and preserve saved targets. Existing unsafe-reader
and wrong-identity holds remain intact. No automatic executable/account fallback.
