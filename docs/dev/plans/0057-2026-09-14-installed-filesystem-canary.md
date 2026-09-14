# Plan 0057: Installed Filesystem Wake Canary

State: OPEN
Lane: P49
Owner: ecochran76
Work Item: CochranResearchGroup/codex-wake#30
Goal Version: P49-G1-v1
Branch: chore/issue-30-installed-filesystem-canary-receipt
Target: origin/main
Integration: squash pull request

## Objective

Install the exact accepted `origin/main` candidate into an isolated venv and
named user service, then prove one schema-v2 `file.created` wake persists,
crosses the service boundary, dispatches exactly once to the captured live
Codex TUI pane, receives hook acknowledgement, records visibility evidence,
archives, and rolls back without changing the global installation or normal
repo wake root.

## Current State

Issue #30 is open and assigned. Canonical `main` is
`86291bf8782759dfd6d4bd19e1429392e8f77279`; prerequisite PR #32 is merged and
provides the tested `--max-attempts 1` contract. The global installed CLI is `codex-wake 0.5.2`
from the uv tool environment and does not expose the newly merged `filesystem`
or `support` commands, while current source does. The existing user supervisor
is active and owns the normal repo wake root, which has zero active wakes and
is observation-only for P49. User hook configuration is installed. Tmux pane
`%36` in session `recovered-050801-20542` is live in this repo. At initial
preflight, no P49 runtime state, service, marker, or dispatch existed.

The prerequisite merged in PR #32 at `86291bf8782759dfd6d4bd19e1429392e8f77279`.
The wheel built from that clean commit has SHA-256
`956846a82cd9007c423f11ee19400e0cd1ec4a9a79659befd638d869f80b6b75`.
The isolated service started as PID `3287811`, then a controlled restart moved
it to PID `3292411` while wake
`wake_9dbc51cc5a2d405d8ef4f1d2623d9c0d` remained pending with zero attempts,
`max_attempts: 1`, an absent marker, and current source/monitor readiness. The
live marker effect and dispatch have not yet occurred.

Graphiti was healthy but returned no P49-specific recall. CodeGraph was healthy
at 90 files, 2,284 nodes, and 8,200 edges. Current repo, GitHub, process,
systemd, tmux, and wake readbacks remain authoritative.

## Authority And Isolation

Authorized effects are one candidate installation inside the exact canary
runtime root, one named user-systemd service, and one live tmux dispatch to the
captured pane. Use these exact identities:

- runtime root: `/home/ecochran76/.local/state/codex-wake/p49-canary-20260914`
- wake root: runtime root plus `/wake`
- marker: runtime root plus `/events/created.marker`
- venv: runtime root plus `/venv`
- service: `codex-wake-p49-canary.service`
- service state: runtime root plus `/xdg-state`
- service drop-in: `/home/ecochran76/.config/systemd/user/codex-wake-p49-canary.service.d/10-p49-isolation.conf`
- service log: runtime root plus `/codex-wake-p49-canary.log`
- marker trigger: `codex-wake-p49-marker-20260914`

The global uv tool installation, `.codex/wake`, supervisor registry, other
services, provider credentials, GitHub sources, public ingress, app-server and
OpenClaw transports, deployment, tags, and releases are excluded. The service
must invoke the canary venv's absolute `codex-waked` path, monitor only the
canary wake root, and set `XDG_STATE_HOME` to the exact service-state path in
the named unit's drop-in. Candidate CLI readiness checks must use that same
environment. The registration command runs from the runtime root with relative
path `events/created.marker`; its cwd is intentionally distinct from the
captured target pane cwd.

## Execution Graph

1. Merge this coordination checkpoint so the active lane is canonical.
2. Create `chore/issue-30-installed-filesystem-canary` from that exact main.
3. Add a supported filesystem registration option that persists an operator
   selected attempt bound in the journal-authoritative schema-v2 record. Prove
   `--max-attempts 1` through focused CLI, idempotency, record, and retry tests;
   do not patch persisted JSON directly.
4. Build a wheel from the exact source commit; record source SHA and wheel
   SHA-256; create the exact empty runtime root and install only into its venv.
5. Install and start the exact named service with explicit daemon, wake-root,
   repo-root, interval, log, and unit-specific state paths. Prove unit and
   drop-in contents, PID, executable, enabled/active state, and recent
   persistent health for only the canary root.
6. Verify the marker is absent and the canary wake root has no active record.
   From the runtime root, arm one `filesystem created --max-attempts 1
   --require-monitor` wake with one stable idempotency key and the current tmux
   target.
7. Restart the exact named service while the marker remains absent. Prove a new
   service PID recovered the same pending wake, remained monitor-ready, and
   made zero dispatch attempts.
8. Schedule marker creation through the exact named transient user-systemd
   trigger after the initiating turn ends, then yield. Do not manually poll or
   create a second wake.
9. On the resumed turn, inspect the original wake id, trigger match, dispatch
   count, `submitted` state, ack file/session, and
   `visibility_result.classification`. Ack alone cannot prove visibility.
10. Export sanitized support/readiness evidence, archive the terminal wake,
   uninstall the named service, and remove the exact canary runtime root after
   durable receipt extraction.
11. Prove the service unit, drop-in, monitor state, marker trigger, process, and
   runtime root are absent, normal repo wake
   active count is still zero, and global installed identity is unchanged.
12. Record verification, close this plan and P49, clear the active lane, pass
    CI, merge, close issue #30, and reconcile `origin/main`.

## Acceptance

- Candidate source, wheel hash, venv executable, service unit, service PID, and
  wake root form one attributable installed identity.
- The service is persistent and ready before registration; registration fails
  closed otherwise.
- The schema-v2 record durably carries `max_attempts: 1`; an unsafe pane or
  acknowledgement timeout becomes terminal rather than eligible for requeue.
- A controlled service restart recovers the same pending wake before the
  marker exists and before any dispatch attempt.
- The marker is absent at registration and created only after this turn is no
  longer the active writer.
- Exactly one wake and one dispatch attempt exist. The accepted outcome is
  `submitted` with hook ack plus `visible_prompt_observed`; any weaker
  visibility classification is recorded as a failed criterion, not upgraded.
- Trigger evidence shows verified filesystem state and contains no file body.
- Support/readiness evidence is bounded and sanitized.
- Archive and rollback leave no canary unit, process, active wake, runtime
  directory, or global-install drift.
- Required CI passes and the issue closes from the merged receipt.

## Bounds And Stop Rules

- work-unit attempts: one installation/service attempt and one live dispatch;
- live retry allowance: zero after registration or any ambiguous effect;
- review: one fresh read-only plan/runtime-boundary review before mutation;
- repair: one bounded pre-effect repair cycle; no review loop after dispatch;
- checkpoint cadence: before runtime mutation, after registration, after live
  outcome readback, and after rollback;
- evidence deadline: candidate identity and ready isolated service before arm;
- no-progress limit: two consecutive hardening-only checkpoints before local
  reframe; this does not authorize another dispatch.

Stop before installation if the exact runtime root already exists or is
nonempty. Stop before the live effect if the source/wheel/service identities disagree,
the unit is not isolated, the pane is dead or changed, the user hook is absent,
the marker already exists, the canary wake root contains an existing wake,
the runtime root contains unexpected files, monitor readiness is false, the
persisted bound is not exactly one, restart recovery fails, or normal/global
state changes. After registration, preserve and inspect the original record on
any uncertainty; never create a replacement wake.

## Validation And Evidence

Before the live gate, run focused candidate tests for bounded filesystem
registration and idempotency, terminal no-retry behavior, daemon dispatch,
hook acknowledgement, service lifecycle, support export, and CLI behavior,
plus both Python comprehensive tiers and plugin tests. After the
live gate, bind the receipt to exact JSON/status/unit/process readbacks and run
the active planning/goal audits. CI remains the integration gate.

## Rollback

On success or failure: stop and uninstall only
`codex-wake-p49-canary.service`; remove its exact drop-in and reload the user
manager; stop, reset, and remove only the named marker trigger; verify their
PIDs, unit state, isolated monitor state, and files are gone; archive a
terminal wake or cancel a still-pending wake with the reason preserved; extract
the bounded receipt; then delete only the validated exact canary runtime root.
Do not mutate the supervisor registry, normal repo service, normal wake root,
global uv tool, or unrelated process tree.

## Definition Of Done

All acceptance criteria have current evidence, rollback is complete, issue #30
and its pull request are closed/merged, Plan 0057 and roadmap P49 are closed,
the active-lane catalog is empty, and canonical `origin/main` contains the
verification receipt. A failed live criterion still requires truthful rollback
and integration but does not count as successful P49 completion.
