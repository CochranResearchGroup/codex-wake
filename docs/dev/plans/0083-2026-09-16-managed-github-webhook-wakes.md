# Managed GitHub webhook wakes goal campaign

State: OPEN
Lane: P54
Issue: #135
Branch: `docs/issue-135-managed-webhook-plan`
Target: `main`
Integration: `squash`
Predecessor: `docs/dev/plans/0070-2026-09-16-signed-github-webhook-ingress.md`

## Current state

P53 is closed and accepted on canonical commit
`8171220259e33064b86d0be871b221607cbfc980`. It proves one signed GitHub
`workflow_run` delivery through the retained Cooper route into the durable
journal, authoritative attempt verification, `0 -> 1 -> 1` convergence, and
zero dispatch. Its hook, secret, service, and isolated root were deliberately
removed. P53 therefore proves the ingress boundary, not a retained managed
installation.

GitHub issue #135 owns P54. The current product has local listener/service
lifecycle, dual current/previous secret references, a durable webhook/polling
join, and a read-oriented GitHub client. It does not yet have a durable
provider-hook binding, a provider-management protocol, reconciliation after an
ambiguous write, a managed rotation workflow, or combined local/provider/
polling health. Editing the listener environment is not rotation proof: the
running process must restart into the intended secret generation, while the
event-source and journal identities remain stable.

PR #136 passed both hosted release gates and squash-merged the kickoff as
canonical `8b74e3eea3ae02b9f60833bc5941add2b15a9f68`; PR #137 reconciled custody at
canonical `74dd2e6c3db6745fc91384c08ea8aa40c7ad964c`. The approved child graph is
published as #138 through #142. C1 issue #138 and Plan 0084 are accepted on
canonical `a3b2c985d9b3d9ef4e1db53d7fbc8479c08455c2`; PR #143 passed both hosted
release gates and GitHub closed #138. Plans 0085 and 0086 now register C2 #139
and the parallel-safe C3-A health packet. Their initial new-module surfaces are
disjoint; the primary serializes shared lifecycle, runtime, CLI, cleanup, and
installed-qualification integration. C3's final qualification remains blocked
on C2 acceptance. No provider, service, secret, ingress, release,
installation, or dispatch effect occurred in C1.

## Objective

Turn the accepted one-shot GitHub webhook proof into an operator-managed,
restart-correct wake capability with exact durable ownership, idempotent
provider reconciliation, bounded secret rotation, observable polling fallback,
safe disable/delete rollback, and one separately gated visible dispatch.

## Product contract

- One owner-scoped, nonsecret managed binding identifies the canonical root,
  source instance, repository identity, exact callback and event intent,
  provider hook ID, service and executable identities, provider credential
  reference, desired fingerprint, secret generation, lifecycle state, and
  sanitized receipt locators. URL similarity alone never proves ownership.
- Provider reconciliation follows `observe -> calculate -> record intent ->
  execute once -> independent readback -> record outcome`. Mutations serialize
  per installation and reject stale generations. An ambiguous write enters
  `UNKNOWN`; only read reconciliation may follow until ownership is resolved.
- Repeating reconciliation against converged state performs no provider or
  service write. Duplicate, foreign, drifted, or colliding hooks fail closed.
- The listener receives HMAC material and only the minimum read credential
  needed for authoritative run-attempt verification. Provider hook
  administration uses a separate opaque credential reference that never enters
  the public listener environment.
- Rotation preserves the source, journal, checkpoint, armed wakes, and
  occurrence identity. It stages a fresh owner-only generation, restarts into
  bounded dual-key acceptance, proves readiness, updates only the exact owned
  hook, proves a new-key delivery, then retires the prior key. Every durable
  phase has crash recovery, an overlap deadline, and an explicit rollback.
- Polling remains independently scheduled and is the correctness fallback.
  Webhook outage, overload, rotation, or rejection cannot reset polling
  anchors, suppress polling, or create a second occurrence.
- Status reports local ingress, provider object/delivery, polling coverage,
  and dispatch as separate planes. `webhook_degraded + polling_healthy` is a
  valid truthful state; it is not permission for automatic provider repair or
  dispatch.
- Disable and delete touch only the proven owned hook and exact service.
  Cleanup independently verifies provider state, unit/PID/socket absence, and
  secret retirement while retaining the journal, wakes, management history,
  tombstone, and accepted Cooper route.
- Ingress and reconciliation never dispatch. A live wake requires a separate
  exact target, wake, payload, trigger, attempt bound, and observed target
  receipt. An uncertain dispatch result is never retried automatically.

## Scope

- Add an owner-only, atomic, nonsecret managed-binding codec and lifecycle
  state machine with desired fingerprints, generations, receipts, and
  tombstones.
- Add an injectable GitHub webhook-management protocol and bounded production
  adapter for exact inventory, get, create, update, disable, delete, and
  delivery inspection operations.
- Add a reconciliation controller with dry-run/status, exact ownership and
  drift classification, operation journaling, per-installation serialization,
  stale-generation rejection, and crash recovery.
- Join managed provider state to the existing listener/service lifecycle
  without changing the durable event-source, journal, checkpoint, or occurrence
  identities.
- Add explicit secret-generation rotation, restart/readiness proof, bounded
  overlap, retirement, rollback, and polling-continuity evidence.
- Add separate local/provider/polling/dispatch health projection and
  secret-free support output.
- Add provider-free fixtures and installed qualification before any provider
  mutation, followed by separately gated retained activation and visible
  dispatch packets.
- Carry work through linked issues, scoped branches, pull requests, hosted
  gates, canonical-main readback, and durable verification receipts.

## Non-goals

- Generic webhook providers, arbitrary repositories/events/refs, or dynamic
  third-party plugin loading.
- Promoting the disposable P53 live-qualification script into the production
  manager.
- Inferring ownership from callback URL, repository name, or other partial
  matches; adopting an unowned provider hook without explicit evidence.
- Storing secret bytes, provider tokens, raw payloads, or unsanitized provider
  responses in binding state, status, support bundles, logs, or receipts.
- Automatic provider mutation, redelivery, public diagnostics, ingress-route
  changes, release, global installation, or unattended target dispatch.
- Treating provider object readback as proof that a secret works, or treating
  local readiness as proof of provider delivery.

## Execution graph

The proposed issue slices are independently reviewable vertical outcomes.
Their final GitHub locators will be added only after decomposition review.

| Slice | Outcome | Depends on | Parallelism and write surface | Exit evidence |
| --- | --- | --- | --- | --- |
| P54-C1 / #138 | Managed binding, provider protocol, and reconciliation controller | #135 | Critical path; product modules, codec, fake transport, CLI/status, focused tests | Exact ownership and lifecycle transitions; absent/exact/duplicate/foreign/drifted/ambiguous inventories; no second write after ambiguity |
| P54-C2 / #139 | Restart-correct secret rotation and local lifecycle join | #138 | May begin design in parallel; implementation serializes on C1 contracts; listener lifecycle, service join, rotation tests | Stable source/journal identity, dual-key restart/readiness, new-key proof, bounded retirement/rollback, polling continuity |
| P54-C3 / #140 | Unified health, fallback, disable/delete, and installed provider-free qualification | #138; integrates #139 | Health projection can parallel C2 after C1; status/support, cleanup controller, installed fixture | Independent health planes, exact-ID-only cleanup, tombstone retention, fresh unit/PID/port census, zero provider/dispatch effects |
| P54-C4 / #141 | Retained managed GitHub activation | #138-#140 integrated | Primary-only gated provider/deployment packet | One exact retained hook and service, signed delivery, restart/readback, recurring health and polling fallback evidence, reversible disable/delete receipt |
| P54-C5 / #142 | One visible webhook-origin wake | #141 accepted | Primary-only dispatch packet | One fresh exact wake reaches one named existing target once; webhook/poll/restart duplication suppressed; rollback/readback recorded |

The critical path is C1 -> C2/C3 integration -> C4 -> C5. C2 rotation work
and C3 health projection may run in parallel only after C1 freezes their shared
contracts; one primary owner reconciles the shared CLI and lifecycle surfaces.
Provider activation and visible dispatch always serialize.

## Agent and model allocation

- The primary owner retains architecture, GitHub issue/PR custody, authority
  gates, shared-surface reconciliation, provider effects, and final acceptance.
- A security/causality specialist uses the strongest available reasoning model
  for ownership, ambiguous writes, credential separation, rotation, and
  dispatch interlocks. The kickoff review used `gpt-6-astra` at high effort.
- A standard implementation model owns bounded product slices and lifecycle
  integration. The kickoff lifecycle review used `gpt-5.6-terra` at high
  effort.
- An economical model is preferred for deterministic fixture matrices,
  mechanical codec/CLI tests, and issue drafting after contracts are frozen.
  The intended `gpt-5.6-luna` issue-slicing worker was not started because the
  concurrent-agent limit was already occupied; the primary performed that
  deterministic decomposition without increasing topology.
- Keep at most three concurrent subagents, no nested delegation, disjoint write
  surfaces, one bounded attempt per packet, and one primary integration owner.
  Escalate model strength only for verified security, causality, or ambiguous
  external-effect risk; do not claim cost or speed savings without telemetry.

## Effect and authority gates

1. C1-C3 product code, fixtures, docs, and provider-free installed checks grant
   no provider, service, secret, ingress, release, global-install, or dispatch
   authority.
2. Local deployment effects require an exact package, root, unit, executable,
   environment, port, owner, and cleanup/readback packet.
3. Each provider create/update/disable/delete action requires exact actor,
   repository, hook ID or create intent, desired fingerprint, attempt bound,
   idempotency/reconciliation rule, and post-write readback. Ambiguity permits
   read-only reconciliation, never another write.
4. Secret provisioning and retirement are separate deployment effects. Secret
   values remain outside Git, argv, unit text, status, support, and receipts.
5. Retained activation requires a fresh gate after C1-C3 are canonical and an
   exact provider/local absence and ownership census passes.
6. Visible dispatch requires a later fresh gate after retained activation is
   accepted. It names one target and one wake and cannot renew or broaden any
   provider or deployment authority.

## Failure and stop conditions

Stop the affected mutation while preserving read-only diagnosis when ownership
is ambiguous; a provider-write result is unresolved; another controller owns a
newer generation; callback/events/content/TLS drift cannot be classified; a
foreign hook or service collision exists; secret files are missing or
permissive; the rotation overlap expired; the listener restarted with stale
environment; polling coverage is unavailable; or package/unit/PID/socket
identity disagrees. Rate limiting and authentication failure degrade provider
health but do not authorize repair, redelivery, polling reset, or dispatch.

Acceptance fixtures must cover concurrent controllers, crashes after provider
acceptance but before local recording, ambiguous create/update/delete,
duplicate inventory, foreign hook/unit collisions, drift, failed restart,
expired overlap, rollback at every rotation phase, and webhook/polling races.

## Validation strategy

- Focused provider-free unit and integration tests for each slice, including
  request budgets, response bounds, sanitized errors, transition legality,
  atomic owner-only writes, and failure injection after every durable phase.
- Comprehensive Python tier:
  `PYTHONPATH=src python -m unittest discover -s tests -p 'test_*.py'`.
- OpenClaw plugin tier:
  `npm --prefix plugins/openclaw-codex-wake test`.
- Compilation, diff hygiene, goal/active planning audits, independent
  closed-world review for security-sensitive controllers, and both hosted
  Python release gates before integration.
- Provider-free installed-wheel qualification proves restart persistence,
  ownership census, rotation fixtures, polling fallback, cleanup, and zero
  provider/dispatch calls.
- Live C4 and C5 verification use sanitized receipts with exact identities,
  counters, hashes, readbacks, rollback state, and explicit retained or removed
  disposition.

## Acceptance criteria

- One durable binding proves exact ownership and remains secret-free; illegal,
  stale, conflicting, or ambiguous state transitions fail closed.
- Provider reconciliation is idempotent, bounded, crash-recoverable, and never
  repeats an unresolved write or mutates a merely similar/foreign hook.
- Rotation preserves event identity and polling continuity, proves the running
  listener accepts the intended generation, proves a new-key delivery before
  retirement, and can roll back from each durable phase.
- Local listener, provider, polling, and dispatch health remain separately
  truthful across restart, drift, outage, disable, delete, and recovery.
- Disable/delete affects only the exact owned hook and service, retires secrets
  only after safe readback, and retains a sanitized tombstone and journal.
- One installed retained activation proves recurring management and fallback;
  one later exact visible dispatch occurs once despite webhook, polling, and
  restart convergence.
- Every slice is linked to #135, integrated through a scoped PR and hosted
  gates, and reconciled against canonical `origin/main` with durable receipts.

## Definition of done

P54 is done only when C1-C5 are accepted on canonical main; the managed
installation has a truthful explicit retained-or-removed disposition; secret,
provider, service, ingress, polling, and dispatch authorities remain separate;
the exact visible wake is deduplicated and evidenced; rollback and cleanup are
verified; #135 closes from canonical evidence; and the roadmap, runbook, plan,
active-lane catalogue, GitHub issue graph, and verification artifacts agree.
