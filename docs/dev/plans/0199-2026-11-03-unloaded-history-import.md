# Copy completed unloaded native histories

State: OPEN
Owner: primary / ecochran76
Ticket: LOCAL-0199
Branch: fix/unloaded-history-import
Base: e5c7d56818664e356d88da068a98eb85a31d9521
Priority: regression blocker

## Current State

Regression red confirmed at public history.import seam; minimal predicate fix
passes14 history tests on each Python3.11/3.12 and4shortcut tests on3.12.
Installed UID1017 qualification passed;238 source/wheel/installed Python files
match. Synthetic native source remains idle; real notLoaded acceptance is next.
See ../evidence/plan0199/acceptance.json.

Live Plan0198 copy failed before native fork: persisted completed/full source
reports notLoaded after its client exits; import requires idle. Old uncertain
intent remains immutable. User authorized fix, deploy and real-account retest.

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
