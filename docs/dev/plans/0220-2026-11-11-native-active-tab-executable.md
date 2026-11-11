# Native active-tab executable continuity

State: CLOSED
Owner: current primary debugging lane
Branch: fix/native-wake-existing-tab-readiness
Base: 7af9b29 (installed dev7 source)

## Current State

Installed live read-only loop reproduces missing active-tab capability under
systemd in seconds; identical interactive invocation passes. A single PATH
addition resolves the symptom. The three-test public factory/observer-chain
regression first failed for missing PATH Codex while explicit-endpoint and unbound
controls passed. Source fix,233 related tests, static checks and packaged-wheel live read-only
probe pass. The bounded source diagnosis is complete. Operator-approved installation now
passes isolated UID1017 rollback/reselect and working source/runtime checks; one
actual automatic continuation is verified with the original submission marker
and one attempt. Separate native acknowledgment/execution fields remain unobserved. See the linked diagnosis note.

## Scope

Make active-tab observation resolve the shared endpoint using the wake's pinned
Codex executable. Preserve existing exact attachment, permissions, busy, no-replay
and state semantics. Do not update the working installation, dispatch another live
wake, restart shared services or alter production wake records in source validation.
Classify the observed cancellation lock contention independently from delivery.

## Acceptance

A deterministic real factory-to-inventory regression catches the service-PATH
failure. Pinned executable and explicit-endpoint paths pass; unbound recipients
remain unavailable. The original installed-code read-only loop fails and the
source-candidate loop passes under identical systemd environment, without sending
any prompt. Related native/session/permission tests and local static checks pass.
Document runtime limits separately from source repair. No hosted CI.

## Custody and terminal condition

One isolated worktree from the installed source preserves the dirty/stale primary
checkout and other active lanes. No uncommitted prerequisite was required.
Retain this uncommitted checkout for source review/adoption; do not remove it
without durable custody. Close the bounded source diagnosis after evidence and
remaining installed acceptance gate are recorded. Graphiti discovery is skipped:
current supplied incident receipts and installed readback are sufficient.

Evidence: [diagnosis](../notes/0220-2026-11-11-native-active-tab-path-diagnosis.md).

## Approved runtime extension

Operator yes2026-11-11 authorizes the qualified package installation and one
exact-self automatic continuation. The earlier non-goals apply to source testing;
this explicit extension adds bounded runtime adoption without authorizing extra
Slack sends, credential use, other service changes or uncertain wake retries.
Close after actual delivery evidence, or record its precise remaining gate.
