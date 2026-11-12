# Formatting after terminal server replacement

State: CLOSED
Owner: primary / ecochran76
Work item: LOCAL-P221
Priority: bug
Branch: fix/tab-format-reboot
Target: origin/main
Base: 95bbebb308d22eb81b9909717ed61358d16095e5

## Current State

DONE (source-only). Exact stale_target reproduced twice against primary source and once
against current origin/main with a disposable real tmux restart. Plain system
Python lacks msgspec on current main; use the installed candidate Python with
PYTHONPATH=src. Runtime was already repaired separately; no deployment is authorized.
Local ticket is used because external issue mutation was not requested.

## Scope and acceptance

Explicit enable must work after namespace replacement, preserve old originals,
and capture new originals before writes. Status explains stale custody without
mutating it. Rollback/resume/reenable and automatic refresh retain identity fences.
Revisiting an old namespace must reuse its original baseline. Prove rollback uses
the new server's originals and unrelated terminal settings/pane identity survive.

## Execution and boundaries

One serial primary lane: red public controller/tmux test, smallest fix, focused
format/controller regression, isolated CLI/package acceptance, local validation.
No independent agent lane is needed for this tightly coupled fix. No provider,
working install, dispatch, service restart or unrelated dirty-file changes.
At most one diagnosis/remediation pass; stop for a concrete unprotected seam
or unresolved baseline-custody failure. Retain this checkout until source review
and commit custody; review cleanup at source-validation closeout.

## Hypotheses and evidence

1. Persisted namespace baseline fence blocks explicit enable: fresh transport
   still raises stale_target after real server replacement (confirmed).
2. Old transport alone: initial harness raised workspace_changed; recreating
   transport reproduces the reported stale_target instead (ruled out).
3. Monitor interference: no monitor exists in the minimal reproducer (ruled out).

## Definition of done

Regression red before green; original restart loop green; old/new baseline
custody and rollback proven; local checks recorded with source commit and limits.
Source completion, publication and installed activation are separate boundaries.

## Validation result

100 formatting tests and34 related controller/target tests PASS on Python3.12.13;
CI scope test PASS, repository undefined-name lint, compile, policy wiring and
whitespace checks PASS. Packaged CLI restart/enable/monitor/rollback fixture PASS.
Initial plain-Python probe lacked msgspec; installed dependency environment fixed
that setup issue. Initial same-socket test setup hit a tmux shutdown race; use a
new disposable socket for deterministic permanent regression. An attempted
related selection named nonexistent test_stable_tab_operations; corrected to
actual test_controller_tabs/test_tab_targets/test_tab_targets_mcp, all34 PASS.
No test assertion was weakened. No comprehensive-suite, Python3.11 or native
Windows runtime claim. No deployment or provider mutation. Hosted CI skipped by
cost policy; local tests use Linux/WSL and existing candidate dependencies.

Three maintained controller regressions protect: server replacement and rollback,
read-only stale inspection plus old-intent/refresh fences, and returning namespace
plus retained-alias custody. CLI/package fixture additionally exercises the common
journal and monitor startup. No DEBUG instrumentation remains.

## Custody

Primary owns this isolated source-review checkout, created because main has
unrelated dirty work and is behind origin/main. No earlier lane was repurposed.
Registered inventory before creation116;117 after creation. Others' registrations
(including stale entries) are outside this task's cleanup scope. Retain this one
until review/integration; next review point is the integration decision. No remote
source publication or merge authority was inferred from the diagnosis request.

Exact commands, source commit, wheel identity and limitations: [validation](../evidence/plan0221/validation.md).
