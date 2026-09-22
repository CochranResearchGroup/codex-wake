# App-server dispatch readiness correction

State: OPEN
Lane: I153
Issue: #153
Branch: `fix/issue-153-app-server-command-readiness`
Target: `main`
Integration: `squash`

## Current state

Issue #153 is reproduced against canonical `f90b6c8` through two deterministic
provider-free paths. A supervisor-owned wake root stores a valid
`dispatch.codex_cmd`, but `supervisor_poll_once` does not pass it to app-server
dispatch. Independently, reinstalling an already-active repo service rewrites
and reloads its unit but does not restart the process, so the daemon can retain
an older environment. Monitor readiness can then combine fresh supervisor
health with the inactive repo unit's command configuration and report a command
that the actual dispatcher cannot use.

The provider-free implementation is complete locally. Focused validation passes
173 affected Python tests; comprehensive validation passes 688 Python tests,
12 plugin tests, compilation, diff hygiene, and active/goal planning audits.
No production or provider mutation occurred. Publication, hosted checks,
canonical integration, issue closure, and any installed-runtime rollout remain.

## Objective

Make app-server command readiness and dispatch agree for both supported monitor
owners: a supervisor must consume the enrolled root's stable Codex command, and
a repo-service reinstall that changes the unit must restart an already-running
daemon before readiness is accepted.

## Scope

- Carry the enrolled supervisor root's Codex command through the existing
  polling and dispatch seam without rewriting durable wake records.
- Record supervisor-owned app-server command readiness in fresh monitor health
  and make monitor/doctor output use the actual dispatcher source.
- Restart an already-active repo service when installation changes its rendered
  unit, while preserving first-install and `--no-start` behavior.
- Update the app-server and daemon-service contracts and add public regression
  coverage for the two exact failure paths.

## Non-goals

- No live wake dispatch, installed-runtime refresh, service restart, release,
  provider mutation, wake-record schema change, or OpenClaw dispatch change.
- No generic dispatch-configuration framework or alteration of explicit
  record-level `target.codex_cmd` precedence.
- No cleanup of unrelated worktrees, branches, plans, or runtime records.

## Design

The existing `poll_once` to `dispatch_firing_record` interface remains the
dispatch seam. It gains one optional supervisor-supplied app-server default;
the app-server target's explicit command remains authoritative. This keeps
registry knowledge in the supervisor and command selection in app-server
dispatch rather than teaching record creation about monitor implementations.

Fresh supervisor health will carry a sanitized transport-readiness projection
derived from the exact enrolled root. `monitor_readiness` will select transport
readiness from the active dispatcher source and fail closed when a fresh
supervisor does not provide a usable Codex command. Repo-service readiness will
continue to resolve the installed unit command after lifecycle reconciliation.

## Execution graph

| Unit | Owner | Write surface | Exit condition |
| --- | --- | --- | --- |
| I153-A | primary | plan and active-lane catalog | bounded plan and issue custody are inspectable |
| I153-B | primary | supervisor, daemon, injector, app-server, focused tests | public supervisor dispatch test moves RED to GREEN |
| I153-C | primary | service lifecycle and focused tests | changed active unit is restarted; unchanged and no-start behavior remain bounded |
| I153-D | primary | monitor/doctor readiness, docs, tests | readiness names and validates the actual dispatch owner |
| I153-E | primary | plan closeout, Git, PR | comprehensive gates and published diff pass |

The units are serialized because they share dispatch/readiness semantics. One
implementation owner is sufficient; no subagent lane is justified for the
small overlapping write surface.

## Goal control record

- Authority: user requested plan and execution for existing issue #153.
- Worktree: `/home/ecochran76/workspace.local/codex-wake.issue-153` only.
- Live effects: forbidden in this plan; tests use temporary roots and fake
  system boundaries.
- Work-unit attempts: at most two per red-to-green slice.
- Review/rework: one closed-world self-review after comprehensive validation.
- Checkpoint cadence: after each green slice and before publication.
- Stop conditions: unexpected wake-record schema change, need for a live
  dispatch/service mutation, unresolved overlap with canonical main, or a
  second failed repair attempt for the same slice.

## Acceptance criteria

- A supervisor-owned due app-server wake without `target.codex_cmd` uses the
  enrolled root's validated `dispatch.codex_cmd` and reaches submission.
- An explicit record-level Codex command retains precedence over any supervisor
  default.
- Supervisor health and doctor readiness report the enrolled command only when
  it is usable by that dispatch path; an absent or invalid command fails closed
  instead of borrowing readiness from an inactive repo unit.
- Reinstalling a changed unit restarts an already-active repo service, while a
  first install starts once and `start=False` performs no start or restart.
- Focused regression tests, the comprehensive Python suite, the OpenClaw plugin
  suite, compilation, and planning/goal audits pass without live effects.

## Definition of done

The plan closes only after the issue-linked branch is published, the pull
request records validation and zero live effects, hosted checks pass, the
accepted change is integrated into canonical `origin/main`, and issue #153 has
truthful completion evidence. Release and installed-runtime rollout remain
separate effects.
