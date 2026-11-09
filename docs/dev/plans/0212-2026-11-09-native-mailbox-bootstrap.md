# LOCAL-P212 | Host-managed native mailbox bootstrap

State: OPEN
Ticket: LOCAL-P212
Owner: primary
Priority: P1
Dependencies: none
Branch: fix/native-mailbox-bootstrap
WIP limit: one implementation lane

## Problem and outcome

Verified native callers cannot use semantic mailboxes from the shared MCP launch
without manual per-thread actor wiring. Provide opt-in host operator delegation
that lazily issues/reuses separate actors for verified callers within existing
enrolled roots. No implicit root enrollment, revocation reset, model-selected
credential path, or service change. Explicit fixed-actor mode remains supported.

## Acceptance

Reproduce missing capability through public CommandRunner; two native callers use
separate actors and complete a correlated question/claim/reply in an isolated bus.
Reject missing/contradictory native metadata, outside roots, revoked actors and
wrong operator credentials before mailbox effects. Reuse current rotated generation;
serialize concurrent issuance. Retain red/green evidence and exact test selection.
Native identity/runtime observations in fixture tests are injected and must not be
reported as real FigureLabs T06 acceptance. Deliver source branch; deployment and
live provisioning are separate.

## Diagnosis

Original installed CLI and current MCP fail authorization_denied with absent
actor capability. Global MCP config supplies neither A2A bus nor actor settings.
Ranked predictions: host resolver admits approved native callers; fixed actors
cannot authenticate a different caller; bus selection alone cannot mint authority.
See user-state a2a-setup-diagnosis/diagnosis.md for earlier bounded probes.
