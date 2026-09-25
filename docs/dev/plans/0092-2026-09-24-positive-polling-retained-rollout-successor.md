# Positive polling retained rollout successor

State: OPEN
Lane: P54-C4
Issue: #141
Branch: `fix/issue-141-positive-polling-rollout-v3`
Target: `main`
Integration: `squash`
Parent plan: `docs/dev/plans/0091-2026-09-24-retained-webhook-rollout-second-successor.md`

## Current state

Plan 0091's rehearsal used fresh authority and correctly created the provider
hook before starting its listener. Main workflow run `36089822519` attempt 2
passed both hosted gates, its completed signed delivery returned HTTP 200, and
the dispatch-disabled wake fired. Polling nevertheless remained unobserved:
positive-only polling verified historical attempts until the fixed
`max_requests=200` ceiling was exhausted against 334 retained workflow runs,
even though a qualifying verified positive occurrence had already been found.
Exact cleanup disabled and deleted hook `685357376`, removed both rehearsal
units, freed port 8820, and retained zero dispatch. The user-scoped read token
remains owner-only and must be preserved.

## Objective

Make positive-only polling return bounded verified positive evidence without
requiring exhaustive negative coverage, then complete one fresh rehearsal and
one retained managed webhook activation with signed delivery, fresh polling,
restart, recurring-health, exact cleanup, and zero dispatch.

## Scope

- Add one public-interface regression proving a verified qualifying positive
  is returned before unrelated historical pagination exhausts the request
  budget. Preserve fail-closed behavior when no qualifying positive exists.
- Make the smallest polling-adapter correction needed for that regression;
  do not weaken exact-attempt verification, source scoping, occurrence
  identity, request limits, or negative-coverage semantics.
- Qualify the corrected candidate through focused, comprehensive,
  provider-free plugin, compilation, installed-wheel, and hosted Python 3.11
  and 3.12 gates before live use.
- Use fresh v5 rehearsal and retained owners, roots, units, HMAC references,
  manifest, wheel, runtime, and effect counters. Reuse only the persistent
  repository-scoped read credential.
- Preserve provider-create-before-listener ordering. Start the dispatch-
  disabled poller first only to establish the managed-reader capability,
  register the wake, then start the listener against the active binding.
- Prove rehearsal with one explicit workflow rerun, signed completed delivery,
  at least two fresh successful polling cycles, and zero dispatch; then exactly
  disable/delete and remove only the rehearsal resources.
- Create the retained owner only after rehearsal absence is proven. Use the
  evidence-PR merge as its natural main occurrence, then prove restart and
  recurring health before final closeout.

## Non-goals

- No dispatch, webhook redelivery, provider update, release, arbitrary event
  expansion, historical-run deletion, or weakening of credential separation.
- No mutation of prior manifests, roots, tombstones, receipts, owner
  identities, or service names.
- No deletion or revocation of the persistent user-scoped read credential.
- No claim that a provider hook, HTTP reachability, or a configured poller is
  delivery or polling proof by itself.

## Execution graph

| Unit | Write or effect surface | Exit condition |
| --- | --- | --- |
| S1 | successor plan and failure receipt | Plan 0092 and receipt 0086 are canonical |
| S2 | one regression and minimal polling correction | red-before/green-after evidence is recorded |
| S3 | full qualification and hosted integration | exact corrected candidate and wheel are frozen |
| S4 | fresh rehearsal create/services/rerun | signed delivery and two fresh polling cycles pass with zero dispatch |
| S5 | exact rehearsal rollback | hook, services, socket, and v5 rehearsal HMAC are absent |
| S6 | fresh retained create/services/evidence merge | natural main occurrence proves signed delivery and polling |
| S7 | retained restart, health, and closeout | retained state is exact and #141 closes canonically |

## Effect bounds

- Provider: two creates, one rehearsal disable, one rehearsal delete, zero
  updates, and zero redeliveries.
- Workflow: one explicit rehearsal rerun. The evidence-PR merge supplies the
  retained natural occurrence; no other manual trigger is allowed.
- Services: one rehearsal install-start and stop-uninstall, one retained
  install-start, and one retained listener restart.
- Secrets: one fresh HMAC per v5 owner and one owner-only copy of the existing
  read credential per owner. Preserve the persistent master token.
- Integration: one correction PR, one retained-evidence PR, and one final
  closeout PR, each through both hosted Python gates.
- Ingress: read-only unless exact inventory or loaded-route evidence proves
  drift. Dispatch remains exactly zero.

## Stop conditions

Stop live mutation and preserve evidence on identity, authority, provider,
service, socket, ingress, credential, generation, delivery, polling, restart,
counter, or dispatch ambiguity. Do not retry an exhausted provider or workflow
effect. A code or hosted-gate failure returns to the correction unit without
crossing a live gate.

## Validation

- Record one failing-then-passing focused test through the polling adapter's
  public `observe` interface. The regression must include a qualifying verified
  occurrence followed by enough unrelated history to exceed the old budget.
- Retain tests showing no-positive scans remain bounded and degraded rather
  than claiming negative coverage.
- Run the affected polling/signal/webhook suites, comprehensive Python tier,
  provider-free plugin tier, compilation, diff and planning audits, and an
  isolated installed-wheel qualification.
- Before each live effect, re-freeze candidate, artifact hash, provider
  inventory, owner identity, unit names, callback, event, credentials, effect
  counters, deadlines, and rollback targets.

## Acceptance criteria

- A qualifying verified positive can converge inside the fixed budget even
  when total historical runs exceed that budget; absence still fails closed
  when coverage is incomplete.
- Fresh rehearsal signed delivery and two polling cycles pass, then exact
  disable/delete and local cleanup reach zero hooks, units, and port listeners.
- One fresh retained hook and exact services remain active after signed
  delivery, polling, one listener restart, three recurring-health samples, and
  all five ingress readbacks.
- The durable read credential remains at its owner-only user path, long-lived
  services contain no administrative credential, and dispatch/redelivery stay
  zero.

## Definition of done

#141 closes only after the correction and both receipts are canonical, the v5
rehearsal is terminally absent, the v5 retained hook and services are healthy,
the P54-C4 lane is removed, the durable read credential is preserved, and C5
remains separately gated.
