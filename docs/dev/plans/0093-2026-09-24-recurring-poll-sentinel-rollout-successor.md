# Recurring poll sentinel rollout successor

State: OPEN
Lane: P54-C4
Issue: #141
Branch: `chore/issue-141-retained-webhook-rollout-v4`
Target: `main`
Integration: `squash`
Parent plan: `docs/dev/plans/0092-2026-09-24-positive-polling-retained-rollout-successor.md`

## Current state

The v6-sentinel rehearsal has now passed: signed completed delivery returned
HTTP 200, two distinct successful polling timestamps were recorded with the
nonmatching failure sentinel pending, dispatch stayed zero, and exact cleanup
cancelled that sentinel, disabled/deleted the rehearsal hook, removed both
units, and freed port 8820. The fresh retained hook and current-generation
dispatch-disabled services are active with target and sentinel wakes armed.
Receipt 0088 records this pre-natural-occurrence checkpoint.

Canonical `f2a4c3c` fixes positive-only polling so a verified qualifying page
returns before unrelated history exhausts the request budget. The v5 rehearsal
proved that fix with signed HTTP 200 delivery and one successful poll, then
stopped: dispatch-disabled wakes remain `firing`, and with no pending record the
daemon has no source arm to poll again. Exact rollback restored zero hooks,
services, listeners, and dispatch. The persistent read token remains owner-only
mode 0600.

## Objective

Complete the retained activation using a pre-armed nonmatching sentinel wake to
keep each dispatch-disabled source runner active long enough to prove repeated
successful polling, without another product-code change.

## Scope

- Provider-free prove that a source configured for `success` and `failure`, a
  success target wake, and a failure sentinel wake behave as follows: a success
  observation fires only the target; the sentinel remains pending; a second
  cycle polls again; dispatch stays zero.
- Freeze canonical `f2a4c3c` into fresh v6 owner identities, roots, services,
  HMACs, runtime, wheel, manifest, counters, and deadlines. Reuse only the
  durable repository-scoped read credential.
- For rehearsal and retained owners, configure both conclusions before arming
  the success target and failure sentinel. Create the hook before service
  start, start the poller to establish reader capability, arm both wakes, then
  start the current-generation listener.
- Prove signed completed delivery, two distinct fresh successful poll
  timestamps, sentinel still pending, target firing, and zero dispatch.
- Exactly cancel the sentinel during each owner's authorized cleanup or final
  retained closeout so it cannot become operational debt.
- Preserve the same rehearsal disable/delete, retained evidence merge,
  listener restart, recurring health, ingress, and final closeout gates.

## Non-goals

- No dispatch, provider update, redelivery, historical-run deletion, product
  code change, release, arbitrary repository/event expansion, or persistent
  credential deletion/revocation.

## Effect bounds

- Provider: two creates, one rehearsal disable, one rehearsal delete, zero
  updates, and zero redeliveries.
- Workflow: one explicit rehearsal rerun; the evidence-PR merge is the retained
  natural occurrence; no other manual trigger.
- Services: one rehearsal install-start and stop-uninstall, one retained
  install-start, and one retained listener restart.
- Local wakes per owner: one success target plus one failure sentinel; exactly
  one sentinel cancellation per owner; dispatch remains zero.
- Integration: one evidence PR and one final closeout PR through both hosted
  Python gates. Ingress remains read-only absent proven exact-route drift.

## Stop conditions

Stop live mutation and preserve evidence on any identity, provider, service,
socket, credential, generation, signed-delivery, polling-timestamp, sentinel,
counter, or dispatch ambiguity. Do not retry exhausted provider or workflow
effects.

## Validation

- Run a provider-free public-interface sentinel fixture before provisioning.
- Reuse canonical qualification evidence for `f2a4c3c`, and re-run installed
  wheel smoke plus baseline/provider/credential readbacks for the fresh v6
  packet.
- Require distinct polling evidence timestamps at least one configured interval
  apart, with the sentinel pending and target firing after the second cycle.

## Acceptance criteria

- Rehearsal proves signed delivery, two distinct successful polls, sentinel
  continuity, exact cleanup, and zero dispatch.
- Retained activation proves the same recurring polling behavior, one listener
  restart, three health samples, all five ingress paths, and exact active
  provider/service state.
- The durable read credential remains owner-only and no long-lived service has
  webhook-administration authority.

## Definition of done

#141 closes only when v6 rehearsal is terminally absent, v6 retained state is
healthy and canonical receipts are merged, both sentinels have explicit final
disposition, P54-C4 is removed, dispatch is zero, and C5 remains separately
gated.
