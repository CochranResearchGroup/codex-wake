# Plan0164 — Wake emergency controls

State: OPEN
Workflow: IN_PROGRESS
Owner: primary / ecochran76
Branch: feat/wake-emergency-controls
Target: origin/main
Work-Item: https://github.com/CochranResearchGroup/codex-wake/issues/271
Dependencies: integrated P156/P162/P163

## Current State

Clean base75c54a9, one registered checkout. Operator accepted all recommended
controls through Ask Matt, including separate explicit owned-turn interruption.
Existing list/cancel operate one root; no bulk command or persistent pause.

## Frozen scope

CLI: list --all-roots; cancel ID or --all, with optional --all-roots;
pause/resume/pause-status/interrupt with the same explicit root scope. Root
selection uses a snapshot of the operator's registry, including disabled roots;
newly enrolled roots after that snapshot are outside the operation's scope.
All roots are shown with canonical identity; malformed inventory fails visibly.
MCP: wake_list/cancel/pause/resume/pause_status/interrupt, host-owned configuration
and exact root/action grants. Peer requests cannot select paths or expand grants.

Persistent per-root sidecar schema1: pause state, revision, history and explicit
interrupt request. Shared effect locks serialize dispatch with cancellation;
pause records intent immediately and reports in-flight delivery rather than
promising retraction. New deliveries and lifecycle admissions/activation hold;
existing accounting enforcement continues. Resume alone never replenishes time,
resources or cancelled wakes. Running turns require the separate interrupt action.
Existing native submission identity and lifecycle goal/owner receipts constrain
interrupts; unknown effects reconcile without blind resend. No blanket process kill.
Older workers do not enforce this new protocol; readback must state the version
boundary, rather than imply a marker can constrain incompatible code.

## Non-goals

No OpenClaw service work (parked), arbitrary process kill, retraction of submitted
prompts, private data export, live emergency test against operator work, renewed
budgets or authority transfer. No hidden resume or automatic retry of uncertain effects.

## Acceptance and seams

- Public CLI list/cancel/pause/resume/status and native dispatch seam: cross-process
  persistent pause, delivery race, terminal/uncertain cancellation, explicit scopes,
  corrupt state failclosed, history and deadlines retained.
- Public MCP CommandRunner: exact host root/action grants, no caller-controlled
  paths, zero subprocess effects on denied requests, structured partial results.
- Explicit interrupt adapter: owned/foreign turn distinction, uncertain response
  reconciliation, handoff request consumed by original resident monitor.
- Focused tests <=45s per slice; full presubmit <=240s plus package/plugin gates.
  Full suite on final integration, not after each small edit. Record red/green.
- Installed isolated command/MCP smoke and cleanup; source/install/live enforcement
  reported separately. No claim that old resident workers were upgraded implicitly.

## Execution and bounded review

Critical path owner primary: control sidecar/guard -> CLI -> integration -> validation.
Independent worker emergency_ownership_discovery owns interruption adapter/tests;
wake_control_mcp owns MCP adapter/tests, frozen command/grant contract supplied.
Three active agents maximum, no nested delegation. Workers return receipts; primary
reconciles. One broad Standards/Spec pass, one bounded remediation verification.
No independent duplicate graph exploration. Graphiti discovery skipped because
current supplied scope and current authoritative code suffice; no historical
product decision needs recovery. Memory folder search found no relevant repo entry.

## Definition of done

Approved controls implemented, documented and validated with explicit limitations;
source integrated through protected-main checks and coherent installed rollout
qualified without changing unrelated live state. Plan/roadmap/lane and issue
readback reconciled, owned fixtures cleaned, one explicit memory disposition.
