# Plan0204: one review and bounded TDD remediation

Reviewed base: `c40dc79ec3b0abe25a4efbbcc138cd1c7ac6f908`.
Frozen reviewed tip: `c34ac066135af8227dc1f995cb4595dd17907b00`.
Diff: `git diff c40dc79...HEAD` at the frozen tip.
Remediation source: `7f87ac44e999e4ebf7b081caa094c57e6a6f8962`.
All six tickets (#480–#485) were closed with readback before this review.
Exactly one broad review and one bounded TDD remediation pass ran.

## Standards

- R1, P1, blocking → resolved. Resume reconciled build jobs but could discard a
  still-running qualification when inputs changed. This violated runtime-proof's
  custody/reconciliation rules. A real MCP regression reproduced the missing
  qualification record and new build submission. Resume now reconciles and holds
  active/unknown qualification jobs before invalidation; terminal evidence is
  archived when its acceptance is withdrawn.
- R3, P2, blocking → resolved. Preparation created its source worktree before
  saving a manifest, so a missing compiler left unrecorded custody. Planning
  discipline requires recoverable state at material boundaries. Preparation now
  saves its run before worktree creation and retains inspectable failure state.

Standards sources: AGENTS.md; engineering/Git, validation, planning, architecture,
code-testing, work-item and collaboration policies; runtime-proof. No standalone
CODING_STANDARDS.md or CONTRIBUTING.md exists. The Fowler smell baseline produced
no additional accepted finding. Mechanical lint was checked separately.

## Spec

- R1, P1, blocking → resolved. The active qualification custody defect also
  violated Plan0204's requirement to reconcile uncertain worker outcomes before
  retrying. The same regression proves the correction; it is one defect counted
  on both axes.
- R2, P1, blocking → resolved. A terminal failed qualification survived resume as
  the current failed record, preventing a repaired helper from being retried.
  Explicit resume now verifies the unchanged package, archives the terminal
  failure and admits a fresh qualification attempt. Both job receipts remain.
- R4, P2, blocking → resolved. Native MCP reconstructed only properties/required,
  dropping the run schema's mutually exclusive input alternatives. Native
  discovery now preserves complete canonical constraints while retaining its
  caller fields. A real SDK/stdin discovery regression verifies that pins or a
  run ID are accepted, while empty and mixed inputs are rejected by the schema.

Spec sources: approved Plan0204 and GitHub #480–#485. Each candidate was checked
by the primary through a failing public-seam regression before its correction.
No second broad review was run.

## TDD evidence

The command for each red/green slice was:

```sh
PYTHONPATH=.:src <declared-venv-python> -m unittest discover -s tests -p test_release_remediation.py
```

Private receipts retain review-red/green-active, retry, preparation and
native-schema logs. Observed red outcomes were: missing qualification custody;
`built` instead of `qualified` after repair; missing-rustc exception without an
inspectable run; and native discovery accepting empty input. The final four
regressions passed. All 28 release regressions then passed together, along with
19 MCP regressions and 191 controller regressions. No skipped test is represented
as a pass.

The actual PowerShell client rechecked the existing real0.167 run after remediation
using a fresh short-lived fixture grant; it remained qualified with unchanged
package inventory and all seven runtime checks. No native recompilation occurred.
The expired prior fixture token was correctly refused and its receipt retained.

## Validation boundaries

Fresh full-chain acceptance used actual PowerShell5.1, WSL CLI, REST, OAuth MCP,
native MCP, and real UID1017 disposable native upgrade/rollback/history checks.
The shared host kernel/resources remain a limitation. Historical compiler
provenance for the retained native package is unknown and explicitly disclosed.

The attempted broad Python run timed out at600.067 seconds. Its external runner
omitted the repository root from Python's import path; the same31 discovery
failures were reproduced on the unchanged baseline. Corrected discovery has zero
import failures and the corrected first109 tests passed. This is not a
comprehensive-suite pass. Parked OpenClaw execution tests were excluded. Passing
focused local checks, package build, lint, compilation, generated reference and
policy checks are recorded in validation.json; hosted GitHub CI was not used.

Working-account installation, merge and deployment remain separate from this
validated integration branch. Memory disposition: forbidden; no memory write was
requested.

Standards: 2 accepted findings, highest P1, both resolved. Spec: 3 accepted
findings, highest P1, all resolved (4 distinct findings overall).
