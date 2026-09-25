# Retained webhook rollout successor

State: CANCELLED
Lane: P54-C4
Issue: #141
Branch: `chore/issue-141-retained-webhook-rollout`
Target: `main`
Integration: `squash`
Parent plan: `docs/dev/plans/0087-2026-09-16-retained-managed-webhook-activation.md`
Successor plan: `docs/dev/plans/0091-2026-09-24-retained-webhook-rollout-second-successor.md`

## Current state

The 2026-09-24 rehearsal consumed its one create and trigger, then stopped
fail-closed. The listener had started against the pre-create `UNMANAGED`
binding, so the successful provider create advanced durable authority beyond
the listener's captured generation and all provider deliveries returned HTTP
503. The one permitted workflow rerun then failed the timing-sensitive Python
3.11 runtime test while Python 3.12 passed. Exact disable/delete and local
cleanup completed, GitHub hook inventory returned empty, all four planned
units were absent, port 8820 was free, and zero dispatch occurred. Verification
receipt 0085 preserves the bounded failure and rollback.

This plan is cancelled because its effect counters are terminal. Plan 0091
uses fresh identities and corrects the lifecycle order by reconciling each
provider hook before starting its listener.

### Original pre-execution state

PR #152 integrated C4's provider-free product gate as canonical `f90b6c8`.
The prior live attempt froze manifests against that commit, installed one
isolated runtime, and prepared two owner-scoped local roots. Its effect receipt
records zero provider writes, zero service starts, zero ingress mutations, and
zero dispatches; execution stopped before the distinct repository-scoped read
credential gate.

Read-only reconciliation on 2026-09-22 confirms GitHub has zero hooks for
`CochranResearchGroup/codex-wake`, port `8820` has no listener, and the four
planned C4 units do not exist. All fourteen files below the old owner roots are
mode `0600`. Canonical `origin/main` is
`919fd2affd88216e1b3fc5359e6c175899921797`, which includes the later
app-server readiness correction and installed-rollout closeout. The old
manifests and owner roots are retained as read-only evidence but are not
authority for a resumed effect.

The operator authorized this successor on 2026-09-22 after reviewing the
reconciliation. The authorized effects are fresh candidate installation,
fresh owner-scoped secret and service material, one rehearsal hook create plus
disable/delete, one final retained hook create, a bounded retained-service
restart, and ingress mutation only if exact readback proves drift. Dispatch,
redelivery, release, and unrelated provider or service effects remain excluded.

## Objective

Re-freeze the accepted current canonical product and complete one exact
retained managed GitHub webhook activation with signed-delivery, restart,
recurring-health, polling-fallback, reversible-cleanup, and zero-dispatch
evidence.

## Scope

- Preserve the old manifests, partial-effect receipt, isolated runtime, and
  owner roots as immutable prior-attempt evidence until final disposition.
- Build and hash a fresh wheel from the exact accepted canonical commit and
  install it in a new isolated runtime.
- Use new rehearsal and retained owner identities; do not reuse the prior
  owner configurations, secret generations, service names, or roots.
- Freeze an owner-only successor manifest before effects, including exact
  commit and wheel identity, roots, units, callback, repository and hook
  intent, event set, redacted credential separation, counters, bounds, and
  rollback disposition.
- Require a distinct repository-scoped read-only credential for polling. The
  administrative provider credential must not enter listener or polling
  service environments.
- Run the rehearsal create, signed-delivery/readiness proof, disable/delete,
  local cleanup, absence census, and terminal tombstone before creating the
  retained owner.
- Retain one exact final hook, listener, and dispatch-disabled poller after
  signed delivery, bounded restart, recurring health, polling convergence, and
  all ingress readbacks.
- Commit sanitized verification and closeout receipts through an issue-linked
  pull request and hosted gates.

## Non-goals

- Any target dispatch, C5 execution, webhook redelivery, generic provider
  support, arbitrary callback or event expansion, release, unattended repair,
  or mutation of unrelated services and ingress routes.
- Reusing the prior owner identities or silently editing their frozen
  manifests and effect receipt.
- Using an administrative GitHub credential inside a long-running listener or
  poll service.
- Treating HTTP success, configured timers, absent wakes, or provider
  configuration alone as delivery, polling, zero-dispatch, or ownership proof.

## Execution graph

| Unit | Write or effect surface | Exit condition |
| --- | --- | --- |
| S1 | canonical reconciliation, new branch, plan, lane | successor plan is canonical and the exact rollout branch is published |
| S2 | read-only inventory, candidate wheel, isolated runtime, successor manifest | exact identities and zero-effect baseline are frozen; required credential capability is present |
| S3 | fresh rehearsal owner, local services, first provider create | signed delivery and polling evidence are current with dispatch disabled |
| S4 | rehearsal disable/delete and local cleanup | exact provider/local absence and terminal tombstone are proven |
| S5 | fresh retained owner and second provider create | one exact retained hook and service set pass delivery, restart, recurring health, polling, and ingress checks |
| S6 | receipts, PR, hosted gates, canonical reconciliation | #141 evidence is canonical, the lane is removed, and issue state matches the retained disposition |

S1 and S2 are serialized. Provider and service mutations are primary-only and
serialize after the manifest and credential gates. No subagents or nested
delegation are required; deterministic inventory, hashing, and polling remain
tool-driven.

## Effect bounds

- Provider ceiling: two creates, one rehearsal disable, one rehearsal delete,
  zero updates, zero redeliveries, and no automatic retry after ambiguity.
- Service ceiling: one rehearsal install/start and stop/uninstall; one retained
  install/start and one bounded restart.
- Secret ceiling: one fresh HMAC generation and minimum read credential
  reference per new owner. Secret bytes and credential-reference names never
  enter receipts, Git, logs, or chat.
- Ingress ceiling: read-only unless exact inventory, rendered hashes, or loaded
  routes prove drift; any repair is separately recorded and must preserve exact
  HTTPS `POST /github/webhook` only.
- Dispatch ceiling: zero. Both listener and polling paths must independently
  report explicit dispatch-disabled state.
- Natural delivery is preferred. One workflow trigger is permitted only if a
  fresh natural exact `workflow_run` does not arrive within a frozen deadline
  and the manifest records its exact attempt bound before the effect.

## Stop conditions

Stop mutation and retain read-only diagnosis if candidate, wheel, manifest,
provider inventory, owner, UID, root, unit, process, socket, callback, event,
credential separation, or ingress identity disagrees; if any provider result
is ambiguous; if required files are not owner-only regular files; if polling
lacks two fresh successful cycles; if dispatch-disabled mode is not proven; if
delivery cannot join authoritative attempt and durable journal evidence; if a
restart loads stale identity; or if any effect bound is exhausted.

## Validation

- Re-run the focused managed-health, service, lifecycle, CLI, and installed
  webhook tests against the exact candidate.
- Run the comprehensive Python tier, the OpenClaw plugin tier, compilation,
  diff hygiene, active/goal planning audits, and isolated-wheel provider-free
  qualification before the first live effect.
- Preserve exact pre/post provider inventory, unit/PID/cgroup/socket identity,
  polling cycles, delivery and journal occurrence identity, restart readback,
  recurring health samples, ingress results, effect counters, zero dispatch,
  and final disposition in sanitized durable receipts.
- Require both hosted Python release gates on the final issue-linked PR before
  closeout becomes canonical.

## Acceptance criteria

- The prior attempt remains attributable and unmodified, and the successor uses
  a fresh exact canonical candidate plus fresh owner identities.
- The rehearsal owner performs at most one create, disable, and delete; its
  provider and local absence, secret retirement, history, and terminal
  tombstone are proven.
- The retained owner performs at most one create and remains exactly active
  with a dispatch-disabled listener and poller after signed delivery, restart,
  three recurring health samples, and at least two fresh polling cycles.
- Raw loopback, local ingress, Cooper-host, bastion, and public HTTPS readbacks
  prove only the intended callback route; ingress changes remain zero unless
  prior drift evidence justifies a bounded repair.
- Sanitized counters prove the authorized effect ceilings, zero dispatch, and
  final disposition `RETAINED_ACTIVE` without exposing secret material.

## Definition of done

#141 closes only when the final retained deployment and reversible rehearsal
cleanup are truthfully evidenced, the verification receipt and closeout are
canonical through hosted gates, the active lane is removed, C5 remains
separately gated, and zero dispatch is preserved.
