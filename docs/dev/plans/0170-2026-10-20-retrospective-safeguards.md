# Plan0170 — Issue289 retrospective safeguards

State: OPEN
Owner: primary / ecochran76
Branch: fix/289-retro-runtime. Base: 75e7d9f. Target: origin/main.
Work item: https://github.com/CochranResearchGroup/codex-wake/issues/299
Plan version: 1

## Current State

Issue289 is closed with retained real-agent and historical-accounting acceptance.
The user authorized implementing all six retrospective improvements. Three
isolated lanes implement controller maintenance/evidence (primary), conservative
CI/static checking (control_repair_review), and reusable acceptance preflight
(native_authority_capability). Primary integrates and validates; workers commit
only their owned surfaces. No new campaign, allowance reset or shared daemon restart.

## Scope and boundaries

Implement an operator-authorized bounded controller handover that preserves
latches, deadlines, identities and accounting; immutable first-stop diagnostics;
a reusable real-agent acceptance launcher that rejects blocked configuration
before model dispatch; undefined-name checking; conservative documentation CI;
a short installed skill router and one current plan checkpoint.
Historical evidence remains append-only. Existing connection refresh remains
Plan0168/#282. Parent timeout latch and fixed renewed 2M fresh deadline
2026-10-20T03:55:35.869783Z remain unchanged.

## Validation and definition of done

Public-boundary red/green regressions for each behavioral change; review exact
integrated diff; both required Python matrix gates before merge. Runtime delivery
must identify exact main commit and installed prefix, preserve the shared native
daemon, and verify isolated handover without resuming any existing goal. Do not
repeat the already accepted paid demo merely to prove unchanged acceptance.
At deadline retain a precise checkpoint instead of renewing or clearing latches.

## Integration

Workers own disjoint files in /tmp/cw289-retro-ci and
/tmp/cw289-retro-acceptance; primary owns supervision, CLI, tests and docs. Worker
commits are reconciled into one reviewed issue299 change. No worker live effects.
