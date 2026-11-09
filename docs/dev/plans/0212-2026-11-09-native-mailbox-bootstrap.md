# LOCAL-P212 | Host-managed native mailbox bootstrap

State: CLOSED
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

## Current state and delivery

Implemented at bd79923, source branch fix/native-mailbox-bootstrap. Public two-caller
reproduction went red at missing actor capability, then green without per-thread
configuration. Final focused Python3.12 selection23PASS/25.652s; Python3.11 selection
21PASS/15.760s (the two preexisting stdio tests ran only3.12). Exact installed wheel
public stdio/CLI four-check fixture PASS;305 package members source/wheel/install
equal. Qualification uses injected private native metadata, not live FigureLabs
attestation. No live root enrollment, service reconfiguration or production deploy.
See evidence/plan0212/qualification.md. Original production MCP still needs host
activation of this opt-in mode after integration. Memory disposition forbidden;
no explicit memory-write request. Supplied current evidence suffices; Graphiti
historical discovery skipped to avoid revisiting the established setup diagnosis.

Publication: draft PR536, https://github.com/CochranResearchGroup/codex-wake/pull/536.

## Subsequent authorized review, merge and deployment

Operator requested review/merge/deploy. Standards0/Spec0 accepted findings;
PR536 merged74d6ea7. Exact qualified wheel deployed to release0.22.0.dev2-74d6ea7,
all305members equal; nine launchers switched, local HTTP controller restarted at
original endpoint, completion installed. Existing workspace enrollment/operator
validated; only shared global MCP launch args changed to opt-in host delegation.
No root grant changes. Supported native config/mcpServer/reload timed out;
no retry. New host-mode workers observed, metadata-read timeout retained, then
actual native MCP self-registration/inbox PASS0.483s. Reload effects reconciled
without requiring another reload. All30 observed native harness births preserved,
stock hash unchanged, ten protected files unchanged. Rollback includes selective
MCP args restoration, independently roundtrip-tested without production rollback.
Real FigureLabs question/claim/reply remains unexecuted; no provider prompts.
See deployment.json; initial source-only delivery statements are historical.
