# Copy completed unloaded native histories

State: CLOSED
Owner: primary / ecochran76
Ticket: LOCAL-0199
Branch: fix/unloaded-history-import
Base: e5c7d56818664e356d88da068a98eb85a31d9521
Priority: regression blocker

## Current State

LOCAL-0199 DONE. PR464 merged at5079f2a and exact matching238-member package
installed at ~/.local/share/codex-wake/releases/0.22.0.dev2-5079f2a.
Fourteen affected history tests/version plus four shortcut tests on3.12 pass;
UID1017 native installed qualification passed. Real source and existing matching
child both report notLoaded and qualify under the fixed predicate. Existing copy
content, ancestry, goal-free state and source revision verified; supported journal
reconcile_result recorded owner-observed result. Original batch then completed,
and two retries return that same child. Native resume displays saved answer.
No new live fork or model turn; daemon targets and stock executable unchanged;
fixture UID process census and final test-client census empty. See acceptance.json
and deployment.json under ../evidence/plan0199; raw private evidence under
~/.local/state/codex-wake/testing/importfix. No memory write requested.

Initial failure-stage inference was too strong: existing deterministic snapshot
predated failed test, so it did not establish whether that attempt reached fork.
Native listing omitted fork ancestry; exact native reads established the existing
matching child. The recovery precheck stopped without issuing a new fork. No
uncertain journal was reset or blindly redispatched. Qualification distinguishes
fresh synthetic native forks from reconciled real existing copy.

## Scope and acceptance

Accept persisted notLoaded sources with nonempty complete/full turns under all
existing account/revision/goal guards. Reject active, unknown and incomplete
sources. Preserve uncertain journal no-refork behavior. Public history.import
operation is the test seam; injected native boundary models actual read response.
Run affected tests on3.11/3.12, exact installed UID1017 native qualification,
then PR merge/deploy Wake client only and live one-copy/retry/reopen acceptance.
No model turn, daemon restart, credential movement or memory write.

## Execution

One primary bounded slice; no parallel implementation needed. Retain red/green
logs under user testing/importfix. Source changes only import predicate/tests;
update evidence and runbook at acceptance. A previously uncertain intent cannot
be silently reset. Reconcile pre-effect rejection before any new live intent.
