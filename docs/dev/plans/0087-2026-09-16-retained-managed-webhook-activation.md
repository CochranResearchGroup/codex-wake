# Retained managed webhook activation

State: OPEN
Lane: P54-C4
Issue: #141
Branch: `feat/issue-141-retained-webhook-activation`
Target: `main`
Integration: `squash`
Parent plan: `docs/dev/plans/0083-2026-09-16-managed-github-webhook-wakes.md`

## Current state

C1-C3 are accepted on canonical `origin/main` through
`7bdef169bde17cbac568f84729bca6a78f1ca171`, and the C4 registration merged
through PR #151 as canonical
`7ceb93ceaab2e256bae99aea678bad68428c09b5`. Fresh C4 preflight confirms the
GitHub actor `ecochran76` (user ID `8397615`) has administration capability on
the unarchived repository `CochranResearchGroup/codex-wake` (repository ID
`1242753508`), and the provider hook inventory is empty. The retained Cooper
route already maps exact `POST /github/webhook` from
`https://codex-wake.ecochran.dyndns.org` to loopback port `8820`; both ingress
layers and the certificate are loaded, while the absent listener truthfully
returns `502`. No live C4 effect has occurred.

The operator explicitly authorized the C4 GitHub hook, secret, installed
runtime, local service, and external-ingress activation effects on 2026-09-16.
Target dispatch remains excluded until C5. That authority does not waive the
provider-free gates below.

Preflight also found three product blockers to truthful activation: managed
health cannot consume first-generation delivery or polling observations; the
standard persistent daemon service cannot freeze `--no-dispatch`; and a
cleanup tombstone correctly makes an owner terminal, so cleanup cannot be
rehearsed and then silently reversed on the retained owner. C4 therefore starts
with a bounded provider-free correction. Live cleanup proof uses a separately
named rehearsal installation, whose tombstone remains terminal, followed by
one fresh final installation that remains active.

The provider-free correction is implementation-complete at `47ce753`. It adds
an explicit persistent no-dispatch service marker, command flag, and
fail-closed status readback plus owner-bound current-generation delivery and
polling evidence written only after durable ingest. Independent review found
and verified repairs for generation succession, recurring deliveries, unsafe
files, cross-root ownership, symlink/FIFO blocking, and the installed fixture's
expired wall-clock anchor. Final local gates pass 680 Python tests, 12 plugin
tests, compilation, planning/goal audits, provider-free cleanup qualification,
wheel build, and diff hygiene. No live effect has occurred; hosted integration
and canonical-main readback precede C4-D.

## Objective

Correct the minimum product surfaces needed for truthful zero-dispatch health,
then install and retain one exact managed GitHub webhook deployment with
independent ownership, signed-delivery, restart, recurring polling, ingress,
and rollback evidence.

## Scope

- Add an explicit persistent dispatch-disabled daemon service option whose
  installed unit and runtime status prove the selected mode.
- Add a bounded managed-health evidence seam for current-generation signed
  delivery and fresh polling observations, without treating provider state or
  local readiness as either proof.
- Preserve terminal cleanup ownership. Exercise live disable/delete only on a
  distinct cleanup-rehearsal owner, retain its history and tombstone, and use a
  fresh owner for the retained activation.
- Freeze an owner-only activation manifest before effects: accepted commit and
  wheel hash, roots, source and installation IDs, units, executable, callback,
  repository, hook intent/ID, event set, fingerprints, credential references,
  HMAC generations, polling anchor, budgets, counters, and final disposition.
- Install the exact accepted wheel, provision owner-only secret references,
  run polling with dispatch disabled, start the loopback listener, and validate
  raw, Cooper-host, and public HTTPS boundaries.
- Reconcile bounded provider create/readback operations; prove signed delivery,
  authoritative run-attempt verification, durable journal commit, webhook/poll
  convergence, restart correctness, recurring health, and no dispatch.
- Produce sanitized verification receipts, close through an issue-linked pull
  request and hosted gates, and leave exactly one final managed activation
  retained for C5.

## Non-goals

- Any target dispatch, webhook redelivery, broad workflow triggering, release,
  automatic repair, generic provider support, or arbitrary callback/event
  expansion.
- Reversing or deleting cleanup history, reusing a deleted P53 hook ID, or
  adopting a hook by URL similarity.
- Claiming secret generation from provider configuration, delivery from an HTTP
  success alone, polling health from a configured timer, or zero dispatch from
  the absence of armed wakes.
- Editing the accepted Cooper inventory unless fresh readback proves drift.
- Completing managed secret rotation or its terminal binding consolidation.

## Frozen execution graph

| Unit | Owner | Write/effect surface | Exit condition |
| --- | --- | --- | --- |
| C4-A | primary | plan, active lane, issue/PR custody | registration is canonical and audits pass |
| C4-B1 | standard implementation worker | dispatch-disabled service option and focused tests | one public test moves RED to GREEN and installed unit preserves the mode |
| C4-B2 | standard implementation worker | current-generation health evidence seam and focused tests | one public test moves RED to GREEN and stale/ambiguous evidence fails closed |
| C4-B3 | primary | shared CLI, schemas, integration, docs | comprehensive and installed provider-free gates pass |
| C4-C | security/causality specialist | read-only exact checkpoint review | ownership, evidence, cleanup separation, and dispatch interlock accepted |
| C4-D | primary | exact install, secrets, no-dispatch polling/listener, ingress readback | local runtime and all ingress boundaries match the frozen manifest |
| C4-E | primary | rehearsal create/disable/delete, final create, delivery/restart/health reads | rehearsal is terminal and absent; final owner is exact, healthy, and retained |
| C4-F | primary | verification, PR, hosted gates, canonical reconciliation | #141 acceptance evidence is canonical and final disposition is retained-active |

C4-B1 and C4-B2 may run in parallel only after C4-A is canonical because their
initial source and test surfaces are disjoint. The primary owns shared schemas,
CLI integration, live effects, GitHub custody, and final acceptance. No nested
delegation is allowed. Live effects serialize after C4-C.

## Live effect packet and bounds

- Two owner identities are permitted: one cleanup rehearsal and one final
  retained installation. Each has a distinct root, source, binding, unit set,
  secret artifacts, fingerprint, and hook create intent.
- Provider mutation ceiling: two creates, one disable, and one delete. Each is
  intent-before-effect, exact-generation, one-attempt, and independently read
  back. An ambiguous result makes the affected owner read-only.
- Service effect ceiling: one install/start and one stop/uninstall for the
  rehearsal owner; one install/start and one bounded restart for the retained
  owner. Exact PID, cgroup, executable, socket, environment references, and
  start identity are read back after each effect.
- Secret effect ceiling: one HMAC generation and the minimum listener read
  credential per owner. The administrative credential never enters listener
  or polling service environments. Rehearsal secrets retire only after exact
  provider and local absence; retained secrets remain owner-only.
- Ingress changes are allowed only if current inventory, rendered hashes, or
  loaded-route readback drifts. Otherwise C4 performs readback only.
- Provider delivery observation is read-only. If no fresh natural exact
  `workflow_run` arrives within the frozen deadline, one separately recorded
  workflow trigger may be used only after its exact action and attempt bound
  are added to the manifest. Redelivery is forbidden.
- Dispatch effect count must remain zero. Both polling and webhook ingest run
  with explicit product/runtime dispatch-disabled evidence.

## TDD and validation

- Work in vertical slices: one public behavior test RED, minimum GREEN, then
  the next behavior. Do not batch speculative tests or implementation.
- Service tests prove default compatibility, explicit persistent
  dispatch-disabled rendering, installed-unit readback, and no widening of
  service authority.
- Health tests prove current first-generation delivery, fresh polling, stale
  evidence, mismatched owner/source/generation, webhook-degraded plus
  polling-healthy, restart continuity, and dispatch `NOT_INCLUDED`.
- Cleanup tests preserve the existing terminal-owner fence and demonstrate that
  a fresh owner cannot inherit the rehearsal tombstone or secret references.
- Run focused tests after each slice, then comprehensive Python, OpenClaw
  plugin, compilation, diff hygiene, planning/goal audits, an isolated-wheel
  provider-free qualification, independent checkpoint review, and both hosted
  Python release gates.
- Live receipts record exact identities and sanitized counters for provider
  writes/reads, service effects, deliveries, journal occurrences, poll cycles,
  dispatch, secrets, and ingress changes. Secret bytes, tokens, raw payloads,
  provider bodies, and credential-reference names are forbidden.

## Stop conditions

Stop live mutation and preserve read-only diagnosis if package or manifest
identity disagrees; ownership is foreign, duplicated, colliding, drifted, or
ambiguous; a provider effect is unresolved; root/unit/process/socket ownership
is unclear; permissions are permissive; polling lacks two fresh successful
cycles; dispatch-disabled mode is not independently proven; ingress widens
beyond exact HTTPS POST; delivery cannot be joined to authoritative attempt and
journal evidence; restart loads stale identity; or any bound is exhausted.

## Model allocation

Use the standard calibrated implementation tier for the two bounded product
slices. Use an economical tier only for deterministic inventory, hashing, and
receipt-schema checks. Use the specialist tier once for the named ownership,
cleanup, evidence-causality, and dispatch-interlock review. The primary owns
architecture, integration, all live effects, and acceptance. Record accepted
slice count, corrections, elapsed time, and effective configuration when
available; measured allocation telemetry is unavailable.

## Acceptance criteria

- The accepted product can persist and prove an explicitly dispatch-disabled
  daemon service and can project truthful current-generation delivery and
  fresh polling evidence for a first-generation managed activation.
- The rehearsal owner performs at most one create, disable, and delete; exact
  provider and local absence, secret retirement, retained history, and its
  terminal tombstone are independently proven.
- The final owner performs at most one create and remains one exact active hook,
  listener, and dispatch-disabled poller after signed delivery and restart.
- At least two fresh polling cycles occur before final provider creation and
  three bounded recurring health samples span the retained listener restart;
  webhook/polling convergence retains one occurrence identity.
- Raw loopback, local Traefik, Cooper-host, bastion, and public HTTPS readbacks
  prove only exact `POST /github/webhook`; no ingress mutation occurs unless
  drift was first recorded.
- Sanitized receipts prove all write/read/effect counters, zero dispatch, and
  explicit final disposition `RETAINED_ACTIVE` without exposing secrets.

## Definition of done

#141 closes only after the provider-free correction and live verification are
accepted through issue-linked pull requests and hosted gates, canonical main
contains the verification receipt, the rehearsal owner is terminal and absent,
the final installation is exact and retained-active for C5, the lane catalog is
reconciled, and dispatch remains zero.
