# Retained webhook rollout second successor

State: CANCELLED
Lane: P54-C4
Issue: #141
Branch: `chore/issue-141-retained-webhook-rollout-v2`
Target: `main`
Integration: `squash`
Parent plan: `docs/dev/plans/0090-2026-09-22-retained-webhook-rollout-successor.md`

## Current state

The second-successor rehearsal is terminally rolled back. It proved the
provider-create-before-listener ordering, signed HTTP 200 delivery, successful
hosted Python 3.11 and 3.12 gates, and zero dispatch, but its positive-only
polling path exhausted the fixed 200-request budget while walking 334
historical workflow runs. Receipt 0086 preserves the failure and exact
disable/delete cleanup. Plan 0092 supersedes this plan with a test-driven
polling correction and fresh rollout identities; the retained owner defined
here never started.

Canonical Plan 0090's rehearsal created exactly one GitHub hook and one
workflow rerun, then failed closed because its listener captured the binding
before provider reconciliation advanced that binding to `ACTIVE`. Its exact
rollback disabled and deleted hook `685323162`, removed both rehearsal units,
freed port `8820`, and retired its local secret files. The retained services
never started. Verification receipt 0085 and issue #141 comment `5825324571`
preserve the sanitized evidence. No provider hook, C4 service, or port 8820
listener remains.

The operator reauthorized the unchanged retained-activation objective on
2026-09-24. A repository-scoped read credential now persists owner-only at
`/home/ecochran76/.config/codex-wake/credentials/github-read-token`; it reads
the target repository and Actions runs while lacking webhook-administration
authority. This successor reuses that credential without regenerating it but
uses fresh owner identities, roots, service names, HMAC generations, manifests,
and effect counters.

## Objective

Complete one exact retained managed GitHub webhook activation with signed
delivery, polling convergence, restart and recurring-health evidence,
reversible rehearsal cleanup, and zero dispatch.

## Scope

- Preserve Plans 0087, 0090, their roots, manifests, tombstones, and receipts
  as immutable history.
- Re-freeze current canonical source, build and hash a fresh wheel, and install
  it into a fresh isolated runtime.
- Create fresh rehearsal and retained owners with new roots, units, private
  references, and HMAC generations; reuse only the durable repository-scoped
  read credential.
- For each owner, configure local nonsecret authority and reconcile the exact
  provider hook before installing or starting the listener. A failed create-
  time ping while the listener is intentionally absent is diagnostic only and
  is not delivery evidence.
- Start one dispatch-disabled listener and poller only after exact provider
  readback reports the corresponding hook active.
- Prove the rehearsal with one bounded main-workflow trigger, signed delivery,
  durable journal identity, and at least two fresh polling cycles; then disable
  and delete that exact hook and remove its exact services and secrets.
- Create and retain the final owner only after rehearsal absence is proven.
- Use the normal evidence-PR merge as the retained owner's natural main-branch
  workflow occurrence. Record the post-merge delivery in a final closeout PR;
  this is not a separate manual workflow-trigger effect.
- Require three retained recurring-health samples, one bounded retained
  listener restart, exact ingress readbacks, and zero dispatch before closure.

## Non-goals

- Any visible target dispatch, C5 execution, webhook redelivery, provider
  update, arbitrary event expansion, release, unrelated service mutation, or
  automatic retry after an ambiguous provider result.
- Reusing an earlier owner identity, HMAC generation, service name, root, or
  mutable manifest.
- Storing the administrative provider credential in a listener or poller
  environment.
- Deleting or revoking the durable repository-scoped read credential.
- Treating create-time ping, HTTP reachability, configured timers, or provider
  configuration as signed-delivery or polling proof.

## Execution graph

| Unit | Write or effect surface | Exit condition |
| --- | --- | --- |
| S1 | successor plan, lane, canonical merge, rollout branch | Plan 0091 is canonical and the exact rollout branch exists |
| S2 | read-only census, wheel, isolated runtime, manifest, fresh local owners | identity and zero-effect baseline are frozen; durable read credential is valid |
| S3 | rehearsal provider create, then listener/poller start | exact hook and generation are loaded by the first listener process |
| S4 | one workflow trigger and observation | signed delivery joins authoritative attempt and journal evidence; two polling cycles are fresh; dispatch is zero |
| S5 | exact rehearsal disable/delete and local cleanup | provider/local absence and terminal tombstone are proven |
| S6 | retained provider create, then listener/poller start | one exact final hook and current-generation services are active |
| S7 | evidence PR, hosted gates, merge, retained observations | merge produces the natural main occurrence; delivery, polling, restart, recurring health, ingress, and zero dispatch pass |
| S8 | final receipt PR and canonical reconciliation | final evidence is canonical, lane removed, and #141 closes with retained state exact |

All provider and service mutations are serialized and primary-owned. No
subagent or delegated live-effect worker is required.

## Effect bounds

- Provider: two creates, one rehearsal disable, one rehearsal delete, zero
  updates, zero redeliveries, and no retry after ambiguity.
- Services: one rehearsal listener/poller install-start and stop-uninstall; one
  retained listener/poller install-start; one retained listener restart.
- Workflow: one explicit rerun for rehearsal. The evidence-PR merge is an
  integration effect whose resulting main workflow is the retained natural
  occurrence; no additional rerun or manual dispatch is allowed.
- Secrets: one fresh HMAC per owner and one minimum read-credential reference
  per owner. The persistent user-scoped read credential is copied into the
  owner-only runtime environments but is neither printed nor deleted.
- Ingress: read-only unless exact inventory, rendered hash, or loaded-route
  evidence proves drift; any repair must remain exact HTTPS
  `POST /github/webhook` only.
- Dispatch: zero for listener and polling paths.

## Stop conditions

Stop mutation and preserve evidence if candidate, artifact, manifest, provider
inventory, root, UID, unit, process, socket, callback, event, credential
separation, or ingress identity disagrees; if a provider outcome is ambiguous;
if an owner-only file is unsafe; if the listener starts before its binding is
`ACTIVE`; if delivery cannot join authoritative attempt and journal evidence;
if polling lacks two fresh successful cycles; if the retained restart loads a
stale generation; if dispatch is nonzero; or if an effect bound is exhausted.

## Validation

- Run focused managed webhook, service, lifecycle, runtime, CLI, health, and
  cleanup tests against the exact candidate.
- Run the comprehensive Python tier, provider-free plugin tier, compilation,
  diff hygiene, active/goal planning audits, and isolated-wheel qualification
  before the first live effect.
- Preserve exact pre/post provider inventory, hook generation, unit/PID/cgroup,
  socket, delivery, journal occurrence, polling, restart, recurring-health,
  ingress, counter, and zero-dispatch evidence in owner-only state and
  sanitized tracked receipts.
- Require both hosted Python release gates on the evidence PR and final
  closeout PR.

## Acceptance criteria

- Prior attempts remain attributable and unmodified; this successor uses fresh
  owner identities and loads provider-created authority on first service start.
- Rehearsal performs at most one create, disable, and delete, proves signed
  delivery and polling, then reaches exact provider/local absence with a
  terminal tombstone.
- The retained owner performs at most one create and remains active after
  signed delivery, two polling cycles, one bounded restart, three recurring
  health samples, and all five ingress readbacks.
- The durable read credential remains at its user-scoped owner-only path and
  the administrative credential is absent from long-running service
  environments.
- Sanitized counters prove all effect ceilings and final disposition
  `RETAINED_ACTIVE` with zero dispatch and zero redelivery.

## Definition of done

#141 closes only when the retained hook and exact services remain active, the
rehearsal is terminally absent, verification and closeout receipts are
canonical through hosted gates, the P54-C4 lane is removed, C5 remains
separately gated, and the durable read credential is preserved.
