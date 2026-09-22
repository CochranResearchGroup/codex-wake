# App-server readiness installed rollout

State: OPEN
Lane: I156
Issue: #156
Branch: `chore/issue-156-app-server-readiness-rollout`
Target: `main`
Integration: `squash`

## Current state

Issue #153 is complete on canonical `main`: PR #154 integrated the product
correction at `781e4e7cff304d3189537b27c519fe60fcc01a6e`, and PR #155 closed its
delivery ledger at `1c05e4bf09dea1808299dca5d903afc9cebd3734`. The installed user tool
is still Codex Wake `0.5.2`, and `codex-wake-supervisor.service` is active from
the older installation with PID 1073 and a September 16 start timestamp.

The pre-rollout doctor readback reproduces the stale installed behavior: this
root is supervisor-owned, but app-server readiness is attributed to
`unit_environment`. The repo-scoped service is inactive and disabled. All four
enrolled roots report zero active and zero firing wakes, so a brief bounded
supervisor restart has a clean execution window. No installation or service
mutation has occurred in this plan yet.

## Objective

Validate the integrated #153 correction, install one exact candidate wheel into
the existing user-scoped Codex Wake tool environment, restart only the active
user supervisor, and preserve source, artifact, process, readiness, rollback,
and canonical closeout evidence.

## Scope

- Run focused and comprehensive provider-free validation against canonical
  source before installation.
- Build and hash one candidate wheel from an exact commit already integrated
  into `origin/main`.
- Build and hash a rollback wheel from tag `v0.5.2` before mutation.
- Force-reinstall the candidate wheel into the existing user-scoped Codex Wake
  tool environment and explicitly restart `codex-wake-supervisor.service`.
- Verify installed file provenance, exact installed regression behavior,
  supervisor process replacement, enrolled-root health, and owner-specific
  doctor readiness.
- Record the rollout in verification, roadmap, runbook, issue, pull request,
  hosted checks, and canonical-main evidence.

## Non-goals

- No live wake dispatch, visible app-server turn, OpenClaw operation, enrolled
  root change, wake-record rewrite, provider mutation, package publication,
  version bump, release, other-host deployment, or unrelated service restart.
- Do not start or enable the inactive repo-scoped service.
- Do not alter or complete P54-C4 / issue #141; preserve its product and runtime
  state while this bounded tool/supervisor rollout executes.
- Do not delete historical branches, worktrees, or runtime records.

## Authority and safety bounds

- The operator explicitly requested testing, closeout, and rollout on
  2026-09-22. This authorizes replacement of the installed user-scoped Codex
  Wake tool and one restart of `codex-wake-supervisor.service` for this host.
- The mutation is limited to the existing Codex Wake uv tool environment and
  the named supervisor unit. No other `codex-wake-*.service` unit is mutated.
- Pre-effect state must show zero firing wakes across every enrolled root. If a
  firing wake appears, stop before installation or restart.
- One candidate installation attempt and, only on failed postconditions, one
  rollback installation attempt are allowed.
- Preserve the rollback wheel until every installed-runtime criterion passes.

## Test and rollout sequence

1. Integrate this plan and lane projection through a non-closing pull request.
2. Re-anchor the execution checkout to the resulting exact `origin/main` SHA.
3. Run the affected Python tier, comprehensive Python tier, plugin tier,
   compilation, diff hygiene, and planning/goal audits.
4. Build the candidate wheel from that clean canonical tree and a rollback
   wheel from the clean `v0.5.2` tag; record both SHA-256 values.
5. Capture installed executable, module, unit, service PID/start timestamp,
   enrolled-root counts, and doctor readiness before mutation.
6. Force-reinstall the candidate with the existing tool environment's Python,
   then explicitly restart `codex-wake-supervisor.service`.
7. Verify the installed package files match the candidate wheel, run the exact
   supervisor dispatch regression with the installed interpreter, and read back
   service plus all enrolled-root health.
8. Require this root's doctor projection to report `monitor_source=supervisor`,
   `codex_cmd_source=supervisor_registry`, the enrolled executable path, and a
   ready command.
9. On any failed postcondition, reinstall the captured `v0.5.2` rollback wheel,
   restart the supervisor, verify baseline service health, and close the rollout
   as failed rather than retrying the candidate.
10. On success, commit the verification receipt and ledger closeout, publish a
    closing PR, require hosted checks, merge, and read back canonical main and
    issue closure.

## Acceptance criteria

- Focused and comprehensive provider-free tests pass from the exact canonical
  source used to build the candidate.
- Candidate and rollback wheels exist before mutation and have recorded
  SHA-256 identities.
- The installed `codex_wake` files match the candidate wheel contents, and the
  exact supervisor-command regression passes under the installed interpreter.
- The supervisor is active and enabled with a different PID and later start
  timestamp; all enrolled roots return fresh ready health.
- The codex-wake root remains free of active/firing records and doctor reports
  its app-server command from `supervisor_registry`, not the inactive repo unit.
- No live dispatch, OpenClaw, provider, release, package-publication, other
  service, or other-host effect occurs.
- The verification receipt, plan, P56 roadmap entry, runbook, active-lane
  projection, issue #156, pull requests, checks, and canonical `origin/main`
  agree on the outcome.

## Definition of done

The plan closes only after the installed candidate and restarted supervisor
pass every postcondition, the rollback boundary is discharged, the closing PR
passes hosted gates and integrates into canonical `origin/main`, lane I156 is
removed, and issue #156 closes from the recorded rollout evidence.
