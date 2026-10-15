# Plan0164 — Wake emergency controls

State: CLOSED
Workflow: DONE
Owner: primary / ecochran76
Branch: feat/wake-emergency-controls
Target: origin/main
Pull-Request: https://github.com/CochranResearchGroup/codex-wake/pull/272
Work-Item: https://github.com/CochranResearchGroup/codex-wake/issues/271
Dependencies: integrated P156/P162/P163

## Current State

DONE. PR272 merged d3ea192; v0.16.0 released, exact installed101-file parity,
25 MCP tools and isolated actual daemon/MCP qualification pass. Final CI1268
unit tests plus all release gates pass both Python versions. Both installed
skills match six files. Source, installation and runtime boundaries are recorded
in docs/dev/evidence/plan0164/final-acceptance.md.

Deployment reconciliation: initial six-root registry omitted seven existing
systemd-owned Wake roots, revealed by fresh OS census. All were verified idle;
added disabled inventory-only registrations and upgraded their existing workers.
Two obsolete uv executable locators repaired without changing other unit flags.
Nine related worker processes now use current prefix and13 roots report protocol
capability. Four unrelated service PID/state snapshots unchanged. No live
emergency action or paid native turn; old prefixes/backups retained. This is an
explicit bounded deployment reconciliation of the user's all-wakes intent, not
new monitoring/A2A permission. Future registry additions remain outside prior scope.

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

## Validation checkpoint

Source5191cf3: final local1267 tests PASS206.442s within240s presubmit budget.
Focused36 PASS. Isolated installed0.16.0 matches101 Python sources, actual CLI
pause blocks daemon, both fixture roots cancel/resume, six MCP controls work and
ungranted root denied,25 tools. No model turns or shared-service restart.
CI38802564058 exposed only obsolete19-tool smoke expectation; corrected to25 and
six control names. New installed qualification added to CI. Evidence includes
initial failure retention and source/install/runtime distinction.

## Delivery closure

Public release assets downloaded with exact parity. Release/install/readback
receipts bind source tag,101 Python files,25 tools,13 roots and9 readers.
37 focused tests passed; final hosted1268 tests plus installed qualification pass.
Memory disposition unavailable: no configured reviewed repository group; canonical
receipts retain source-backed outcome with no Graphiti or memory-folder write.
Source ref retained; final doc custody closeout uses protected-main workflow.
