# Managed webhook secret rotation

State: CLOSED
Lane: P54-C2
Issue: #139
Branch: `feat/issue-139-webhook-secret-rotation`
Target: `main`
Integration: `squash`
Parent plan: `docs/dev/plans/0083-2026-09-16-managed-github-webhook-wakes.md`

## Current state

C2 is accepted on canonical `origin/main` at
`143b1d3d6f1bedf7ea41ae0a422f1d5300aae5a1`; PR #147 passed both hosted
Python release gates and GitHub closed #139. It has a durable six-phase
rotation transaction, generation-specific
request attribution, process-bound runtime readiness, committed-delivery
proof, immutable deadline enforcement, explicit expiry/rollback, polling
identity continuity, and sanitized effect-free CLI status/preview.

The public CLI intentionally exposes no rotation apply command. Provider GET
cannot prove an HMAC generation, and the current binding contract has neither
a secret-retirement effect adapter nor a terminal binding-consolidation
transition. Publishing apply before those contracts exist would make provider
rollback and durable authority disagree. Generic binding `reconcile --apply`
is therefore fenced for the full preview/mutation/readback window whenever a
rotation record owns the source.

The accepted provider-free feature tip is
`ab398ff5b431ddbda193bd140256af0ca18d1f75`; its local validation passed 638
Python tests, 12 plugin tests, compilation, and diff hygiene. Provider,
service, secret, ingress, installation, release, and dispatch effects remained
zero. C3 owns the next provider-free integration; live activation remains a
separate C4 gate.

## Objective

Deliver a persisted managed-secret rotation that resumes after process loss,
advances only on fresh runtime and key evidence, safely retires or rolls back
generations, and preserves source, journal, checkpoint, armed-wake, polling,
and occurrence identity.

## Scope

- Add a strict owner-only atomic rotation record containing immutable ownership
  identity, revisions, generation references, overlap deadline, pending effect,
  sanitized evidence locators, and terminal outcome without secret values.
- Implement `PREPARED -> DUAL_READY -> PROVIDER_PENDING ->
  AWAITING_DELIVERY -> RETIRING -> COMPLETE`, plus explicit `UNKNOWN`, expiry,
  and rollback outcomes.
- Record intent before each effect; observe after uncertain results and never
  repeat an ambiguous provider write.
- Prove the exact service/process loaded generation set through a private,
  process-bound channel. Record the matched numeric generation only after
  authoritative attempt verification and durable journal ingest.
- Enforce an immutable overlap deadline at request admission even while the
  controller is absent; backward time movement fails closed.
- Preserve polling and occurrence identity through restart, expiry, failure,
  and rollback; add preview-first sanitized CLI integration after interfaces
  stabilize.

## Non-goals

- Live GitHub writes, retained service deployment, real secret provisioning,
  ingress changes, global installation, release, redelivery, or dispatch.
- Treating provider GET, active/enabled state, an open port, an environment
  write, or a local challenge as provider-delivery proof.
- Resetting polling anchors, source identity, the journal, armed wakes,
  checkpoints, or occurrence keys.
- General credential management or storing secret values, raw provider
  responses, payloads, tokens, or unkeyed secret hashes.

## Frozen contract

- GitHub exposes no readable secret generation. Exact public-hook equality
  cannot clear uncertain secret-write state.
- Readiness proof binds the exact fresh process, authority revision, and loaded
  generation set. It remains distinct from provider-delivery proof.
- Retirement requires a target-generation match tied to the current rotation
  and process after durable ingest. Rejected or failed-commit requests do not
  qualify.
- Deadline expiry removes previous-key admission independently of controller
  progress. Unresolved forward state blocks webhook admission while polling
  continues. Reversal after completion is a new rotation.

## Execution graph

| Unit | Owner | Write surface | Exit condition |
| --- | --- | --- | --- |
| C2-A | standard implementation worker | new rotation module and focused tests | codec, store, state, crash, expiry, rollback tests pass |
| C2-B | primary | binding fence and listener/runtime/lifecycle joins | process-generation and committed-delivery proofs pass |
| C2-C | primary | CLI and polling/identity integration | provider-free rotation and redaction pass |
| C2-D | economical independent reviewer | none | crash/expiry/ambiguity matrix accepted |
| C2-E | primary | corrections, PR, receipts, canonical docs | local/hosted gates pass and #139 closes |

C2-A may run beside C3-A because their initial files are disjoint. The primary
owns shared schemas, lifecycle, runtime, CLI, authority, integration, and final
acceptance. No nested delegation is allowed.

## Implementation checkpoint

- `fe727de` establishes the persisted rotation domain, durable admission
  clock, legal phase graph, explicit rollback/expiry, and successor rules.
- `e7f5b38` joins listener generations, exact-one HMAC attribution, durable
  ingest callbacks, owner/source/repository/service/binding fences, process
  attestation, delivery proof, and safe proof refresh after a pre-delivery
  restart.
- `23eaba0` adds redacted local status/preview, numeric generation resolution,
  a full-duration generic-reconcile fence, and the polling occurrence-identity
  regression through expiry and rollback.
- Specialist review accepted the rotation causality contract. Economical
  review accepted the final runtime-attestation and CLI/remediation checkpoints
  after direct race and drift reproductions. The primary retained shared
  architecture, authority, CLI, integration, and acceptance ownership.
- Final validation passes 638 comprehensive Python tests, 12 OpenClaw plugin
  tests, compilation, and diff hygiene on the documented checkpoint plus
  closeout changes.
- Provider, service, secret, ingress, installation, release, and dispatch
  effect counts are all zero.

## Validation

- Inject failure before and after staging, authority update, restart, provider
  call/readback, delivery proof, retirement, rollback, and finalization.
- Cover stale PID/start identity, wrong generation/root/service, foreign
  socket, equal-secret rejection, expiry, backward clock, redaction,
  concurrency, partial state, and terminal idempotence.
- Provider timeout fixtures prove one mutation maximum and no false secret
  confirmation from public state.
- Webhook/polling fixtures prove one occurrence and continued polling across
  restart and rollback.
- Run focused and comprehensive Python, OpenClaw plugin, compilation, diff,
  goal/planning audits, independent review, and both hosted Python gates.

## Model allocation

Use one standard `gpt-5.6-terra` high-effort worker for the new rotation module
and tests, the primary for consequential shared integration, and one economical
`gpt-5.6-luna` medium-effort reviewer for the crash matrix. Specialist
escalation is reserved for a concrete unresolved causality finding. Effective
allocation telemetry is unavailable, so no cost or speed claim is made.

## Acceptance criteria

- Every phase resumes safely and rejects stale or conflicting revisions.
- Dual and target-only readiness bind the exact process and authority revision;
  public provider state never substitutes for secret proof.
- New-key delivery precedes retirement; overlap never silently extends; and
  rollback is explicit and bounded from every phase.
- Polling continues and durable event identities remain stable without a
  duplicate occurrence.
- Output contains no secret, token, raw payload/provider body, or opaque
  secret-reference name.

## Definition of done

#139 closes only after this provider-free path is canonical on `origin/main`,
C3 can consume its frozen nonsecret lifecycle summary, the lane is reconciled,
and all external and installed effect counts remain zero.
