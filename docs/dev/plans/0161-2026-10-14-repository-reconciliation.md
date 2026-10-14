# Plan0161 — Repository and worktree reconciliation

State: CLOSED
Workflow: DONE
Owner: primary / ecochran76
Branch: chore/reconcile-20261014
Target: origin/main
Work-Item: https://github.com/CochranResearchGroup/codex-wake/issues/260

## Current State

Bounded reconciliation completed; canonical projection repairs prepared for PR
integration. Evidence: docs/dev/evidence/plan0161/reconciliation.md.
Lifecycle lane remains active; draft PR253 is not acceptance or integration ready.

## Scope

Primary serially reconciles registered worktrees, exact remote custody, open PRs
and canonical catalog. Fix catalog identity and projection drift; update completed
A2A delivery records; remove clean archived checkout after fresh runtime census.

## Non-goals

No feature completion, active-owner checkout mutation, runtime effects, branch
history deletion, historical plan migration or release. No process termination.

## Acceptance criteria

- Registered worktrees have explicit dispositions and clean/dirty readbacks.
- Retired Plan127 preserves exact local/remote archive and original named ref.
- Canonical lane IDs unique; active P156 and integrated P160 discoverable.
- Lifecycle conflicts and incomplete acceptance remain explicit owner obligations.
- Existing 15 catalog custody checkpoints verified; repair checks pass.

## Definition of done

Published reconciliation PR passes CI and merges; private final receipt records
exact main and retained worktrees; temporary reconciliation checkout closes.

## Bounds and validation

One serial documentation packet; no workers. Literal docs and Git inspection,
exact ref/PR readbacks, fresh process-CWD census, catalog uniqueness/custody check,
canonical policy wiring and whitespace. Hosted CI required before merge.
