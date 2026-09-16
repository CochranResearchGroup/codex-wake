# Managed webhook ownership and reconciliation

State: OPEN
Lane: P54-C1
Issue: #138
Branch: `feat/issue-138-managed-webhook-reconciliation`
Target: `main`
Integration: `squash`
Parent plan: `docs/dev/plans/0083-2026-09-16-managed-github-webhook-wakes.md`

## Current state

Plan 0083 is canonical at `74dd2e6`, parent issue #135 is open, and the
approved child graph is published as #138 through #142. Issue #138 is the
unblocked critical-path slice. Existing code supplies immutable listener and
GitHub polling-source stores, owner-only atomic JSON persistence, an injected
read-only GitHub client, CLI JSON conventions, and the durable polling/webhook
occurrence join. It does not supply managed provider-hook ownership, provider
administration, operation journaling, or ambiguity-safe reconciliation.

This branch starts from canonical `74dd2e6`. No provider, service, secret,
ingress, installation, release, or dispatch effect is authorized. Production
transport may be implemented behind an injected protocol, but all C1 execution
and acceptance are provider-free.

## Objective

Deliver one provider-free end-to-end management path that can persist an exact
secret-free hook binding, inspect a bounded provider inventory, preview a
deterministic reconciliation decision, execute at most one explicitly armed
provider mutation with intent-before-effect and independent readback, recover
unknown effects without retrying them, and expose sanitized CLI status.

## Scope

- Define a strict managed-binding identity and desired-state fingerprint that
  binds canonical root, owner, source, repository, callback/event intent,
  service/executable identity, provider credential reference, hook ID,
  lifecycle, and generation without secret values.
- Persist bounded bindings and operation records atomically in owner-only,
  symlink-rejecting state beneath the wake root.
- Define an injectable provider-management protocol plus bounded request and
  response objects for list/get/create/update/disable/delete observation.
- Classify absent, exact-owned, duplicate, foreign, drifted, and colliding
  inventories deterministically from complete identity, never URL similarity.
- Expose dry-run/status and one explicitly armed reconcile command through the
  supported CLI with JSON and concise human output.
- Record intent before a write, perform at most one write, independently read
  back, and record success or `UNKNOWN`. Unknown effects allow only read
  reconciliation until resolved.
- Serialize mutations per installation and reject stale desired generations.
- Add provider-free fake-transport tests for every classification, legal and
  illegal transition, crash boundary, ambiguity, redaction, and no-dispatch
  invariant.

## Non-goals

- Secret-generation rotation, service restart, provider health/fallback,
  disable/delete cleanup qualification, installed qualification, or tombstone
  productization owned by #139 and #140.
- A retained live hook or service, live GitHub mutation, public ingress change,
  release, global installation, redelivery, or target dispatch.
- Adopting a provider hook from partial identity, automatically repairing
  drift, or retrying an ambiguous provider write.
- Storing HMAC values, provider tokens, raw payloads, or unsanitized provider
  responses.

## Frozen reconciliation contract

```text
observe bounded inventory
  -> classify exact ownership and drift
  -> calculate zero-or-one action
  -> persist generation-bound intent
  -> execute once only when explicitly armed
  -> independently read back
  -> persist converged outcome or UNKNOWN
```

An `UNKNOWN` operation is not failure permission. The controller may perform
bounded read-only inventory/get operations to resolve it, but it cannot issue a
second create/update/disable/delete until the original effect is attributable.
Repeated reconciliation of converged state emits no provider write.

## Execution graph

| Unit | Owner | Depends on | Write surface | Exit condition |
| --- | --- | --- | --- | --- |
| C1-A | standard implementation worker `/root/p54_c1_core` | frozen contract | new core management module and focused tests only | binding/store/protocol/reconciler tests pass |
| C1-B | economical read-only worker `/root/p54_c1_cli_contract` | frozen contract | none | minimal CLI/status contract and test matrix returned |
| C1-C | primary owner | C1-A and C1-B | plan, CLI integration, integration tests, docs/catalog | end-to-end provider-free command path passes |
| C1-D | independent closed-world reviewer | C1-C checkpoint | no writes | all #138 acceptance criteria accepted or bounded findings returned |
| C1-E | primary owner | C1-D | corrections, PR, receipts, roadmap/runbook | local/hosted gates pass and canonical-main readback closes #138 |

C1-A and C1-B run in parallel with disjoint surfaces. The primary owns shared
CLI and integration decisions. At most two workers plus the primary are active;
no nested delegation is allowed. One implementation pass and one bounded
review/remediation pass are the loop bounds.

## Implementation checkpoint

Checkpoint `06db2b7` supplied the first provider-free end-to-end path. The binding
store now preserves exact local custody by provider hook ID and attributable
operation receipt; an unbound same-URL hook is a collision and is never
adopted. Reconciliation records intent before one create/update, performs one
independent exact-ID readback, and preserves a returned create ID in `UNKNOWN`
when readback cannot prove the effect. Pending, unknown, duplicate, collision,
and missing states cannot issue a second provider write.

The production transport is a serial, bounded GitHub.com adapter pinned to
`api.github.com` and API version `2026-03-10`. It resolves token and listener
secret values only at request time, follows no redirects, performs no retries,
does not expose raw response bodies, and can inventory nonconforming foreign
hooks without confusing them for the desired hook. Disable/delete/delivery
methods are present only as exact-ID transport primitives for the later C3
lifecycle slice; C1 does not invoke them.

The supported CLI is `github-webhook binding configure|show|status|reconcile`.
Configuration joins an existing listener source to one immutable installation
and repository identity. `show` is local, `status` is read-only, and
`reconcile` defaults to dry-run; only explicit `--apply` may execute the
calculated zero-or-one provider mutation. Human and JSON output omit provider
credential and listener-secret reference names as well as their values.

Independent review of exact checkpoint `a2606e6` returned changes required:
readback did not compare the returned exact ID; numeric repository identity was
not provider-attested; separate bindings could preview the same absence;
rolling observations could evict ownership provenance; an oversized successful
write could make the store unreadable; the lock followed symlinks; copied-root
state loaded before failing on save; and CLI reconfiguration silently retained
a different requested installation ID.

Remediation checkpoint `729f4cc` closes those findings with exact-ID checks in
the reconciler and adapter, a bounded repository ID/name read before every
provider operation, conflicting-binding rejection, under-lock inventory
revalidation before intent, preserved ownership receipts, encoded-size checks
before replacement, descriptor-level no-follow locking, root/UID validation on
load, and explicit immutable-installation rejection. Exact re-verification
found one remaining variant: a rejected mismatched UPDATE response could
replace the already-owned ID in its `UNKNOWN` receipt. Checkpoint `d2de93e`
closes that hole by retaining the pre-write exact ID for every ambiguous
UPDATE while allowing only CREATE to acquire a returned ID. It also preserves local
`show` when listener configuration is missing while preventing an armed apply,
and admits bounded nonconforming foreign inventory without granting ownership.

Local remediation validation passes 37 focused management tests, including a
two-process stale-generation race, 602 comprehensive Python tests, 12 OpenClaw
plugin tests, compilation, and diff hygiene. All provider paths use fakes;
provider, service, secret, ingress, installation, release, and dispatch effect
counts remain zero. Final exact-checkpoint independent re-verification and hosted
integration gates remain.

## Model allocation

- Core implementation uses the standard calibrated tier, `gpt-5.6-terra` at
  high effort, because persistence and unknown-effect recovery are
  correctness-sensitive but the architecture is already frozen.
- CLI contract analysis uses economical `gpt-5.6-luna` at medium effort and is
  read-only with deterministic acceptance outputs.
- The primary retains architecture, security/authority decisions,
  reconciliation, GitHub custody, integration, and final acceptance. A
  specialist tier is reserved for a concrete unresolved security or causality
  finding rather than routine review.
- Effective allocation telemetry is unavailable; no cost-saving claim is made.

## Validation

- Focused core and CLI tests prove persistence bounds, modes/ownership,
  symlink rejection, duplicate-key rejection, lifecycle legality, inventory
  classification, generation checks, intent-before-effect, one-write budgets,
  unknown-effect recovery, readback convergence, and redaction.
- The fake provider records every call and fails if a path performs an
  unbudgeted second write or any dispatch-like action.
- Comprehensive Python:
  `PYTHONPATH=src python -m unittest discover -s tests -p 'test_*.py'`.
- OpenClaw plugin: `npm --prefix plugins/openclaw-codex-wake test`.
- Compilation, diff hygiene, goal/active planning audits, independent review,
  and both hosted Python release gates pass before integration.

## Acceptance criteria

- Exact complete binding identity distinguishes owned, foreign, duplicate,
  drifted, colliding, and absent inventories without secret material.
- Owner-only atomic persistence and strict bounded decoding fail closed on
  malformed, permissive, symlinked, duplicate, or stale-generation state.
- Preview/status is read-only and deterministic; explicitly armed reconcile
  performs zero or one provider write and independently verifies its result.
- Ambiguous writes persist `UNKNOWN` and cannot be retried; read-only recovery
  either attributes the original effect or remains safely unresolved.
- CLI and support-visible output is sanitized and contains no provider token,
  secret bytes, raw payload, or unsanitized response body.
- Provider-free tests prove zero service, ingress, release, installation, and
  dispatch effects.

## Definition of done

Issue #138 closes only after the supported provider-free management path and
all acceptance evidence are canonical on `origin/main`; the active lane is
reconciled; #139 and #140 reference the accepted contract; and no live or
installed effect occurred.
