# PR341 local validation repair

State: OPEN
Issue: https://github.com/CochranResearchGroup/codex-wake/issues/342
Owner: ecochran76 / primary coordinator
Branch: feat/harness-next-frontier
Source baseline: e6e2227c63f3b7cc22a6a921db686b5a1e78ba9c

## Current State

Feature source acceptance is complete. One comprehensive local run has two
handoff qualification failures, three acceptance freshness errors and one
ambient offline-time configuration error. All first failures retained in the
prior validation evidence. This corrective packet changes no provider authority,
production installation, CI policy or accepted scope. Main integration remains
separate. User authorized diagnosis and repair through Ask Matt recommendation.

## Work and bounds

Primary owns freshness diagnosis at WorkAcceptance/ResourceClaims public seam.
Independent diagnose_time owns time-inspection tests; diagnose_handoff owns
handoff fixture diagnosis/test and direct proven source if required. Three
lanes maximum, no nested delegation, shared checkout with disjoint file ownership.

Each lane builds a red-capable loop, minimizes, ranks falsifiable hypotheses,
changes one variable per probe and keeps red/green evidence. Initial freshness
loop10cases/7.100s reproduces2 errors; minimized one-verifier20cases and two-verifier
10cases pass. Numeric boundary instrumentation distinguishes future observation,
expired observation and malformed identity; instrumentation sweep bounded30cases.
Handoff initial10iterations of a pair, then one complete51-test module with
fixture-only failure diagnostics; no speculative production fix. Time lane uses
one-variable ambient configuration comparison and publicCLI regression.

Join after fixes/proven diagnostic dispositions; run focused tests on3.11/3.12,
then one comprehensive3.12 suite(max15min) with failure evidence. A repeat broad
suite requires a new concrete change or discovered cause; no retry-until-green.

Done means causes and repairs are supported by evidence, focused regressions and
one full local result recorded, temporary debug instrumentation removed, owned
fixtures cleaned and PR341 updated. Preserve any unresolved gate explicitly.
No new broad review or renewal of the completed goal allocation is implied.
