# Signed GitHub webhook ingress goal campaign

State: OPEN
Lane: P53
Issues: #103, #104, #105, #106, #107, #108, #109
Branch: `multi-lane; see docs/dev/active-lanes.yaml`
Goal ID: P53-G1
Goal Version: P53-G1-v1
Checkpoint: P53-G1-C01

## Goal objective

> Deliver a supported, resource-bounded HTTP listener for the existing signed
> GitHub webhook core, productize its lifecycle, qualify the installed service,
> publish one exact Cooper/bastion HTTPS route, and prove one live GitHub
> delivery converges with polling. Preserve commit-before-ack, durable logical
> deduplication, fixed source authority, and dispatch separation. Do not create
> a generic webhook plugin ABI, trust proxy identity, expose diagnostics or
> secrets, release, deploy outside the named ingress route, or infer live
> dispatch authority.

## Current state

P52 closed at canonical commit `98089261857e0427b3df9a0aededf583e799775d`
with no open issue, pull request, topic branch, worktree, or active lane. The
existing `GitHubWebhookIngress` already authenticates exact bounded bytes,
performs one authoritative GitHub attempt read, normalizes to the polling
identity, commits before returning `200`, and preserves polling convergence.
It has provider-free tests but no HTTP listener, executable lifecycle, service,
or supported external route.

CodeGraph located the network join at `GitHubWebhookIngress.ingest` and the
separate daemon/service/CLI surfaces. A dedicated listener process is preferred
to embedding network admission in the polling/dispatch daemon. Current source,
closed Plan 0054, Git/GitHub state, and policy are authoritative; Graphiti was
not needed because no uncertain historical decision remained.

The shared `/home/ecochran76/workspace.local/cooper-webservices` checkout was
dirty before ingress planning. Per operator direction it was validated, split
into implementation commit `1065482` and documentation commit `5fcce95`, and
pushed cleanly to `CochranResearchGroup/cooper-webservices` main at exact commit
`5fcce954e2acca1bce5b1fd0e49eca9fda2a2cab`. No P53 ingress inventory or live
route has been created yet.

Parent issue #103 and dependency-ordered child issues #104 through #109 are the
coordination ledger. Issue #104 is the sole ready implementation slice.

## Architecture and security decisions

1. Run webhook admission in a dedicated process and service. It may share the
   durable SQLite journal through its supported WAL/transaction boundary, but
   it does not own polling, evaluation, publication reconciliation, or dispatch.
2. Default to an explicit loopback bind. A non-loopback bind is a named
   deployment state used only after installed acceptance and exact interface/
   reachability review; never silently widen to `0.0.0.0`.
3. Accept one exact `POST /github/webhook` route with one documented JSON media
   type. Reject aliases, query strings, redirects, unsupported encodings,
   ambiguous request targets, and every other method/path.
4. Require one valid bounded `Content-Length`; reject transfer encoding,
   duplicate/conflicting framing headers, incomplete bodies, hidden suffixes,
   pipelining, and duplicate security headers before core ingestion. Preserve
   raw header multiplicity until validation.
5. Bound request line, header count/bytes, accepted sockets, workers, body
   bytes/reads, absolute time, provider/store time, and shutdown. One source
   admits one ingest operation and queues none.
6. Forwarded headers and client IP never authenticate, select a source, change
   admission, build redirects, or establish freshness. Routing comes only from
   frozen operator configuration.
7. Persist only opaque current/previous secret references. Resolve at most two
   owner-authorized values per request; never expose secret bytes through argv,
   logs, status, readiness, support, fixtures, or tracked files.
8. Only a journal-confirmed `COMMITTED` or `DUPLICATE` result yields `200`.
   Transport and core failures retain bounded stable response codes without
   exception text or provider payloads.
9. Keep health local and side-effect-free. No public UI, diagnostics,
   configuration, status, or secret surface shares the webhook route.
10. Polling remains enabled. Restart may lose bounded transport cache/rate
    windows, but durable occurrence identity prevents duplicate logical wakes.
11. Cooper ingress uses pinned port `8820` only after a fresh collision check.
    The public path bypasses Authelia because GitHub authenticates with HMAC;
    any other host surface is absent or separately protected.
12. External ingress configuration is authorized by the operator once the
    installed service is ready. Creating the GitHub webhook/secret is a later
    provider mutation with its own exact preflight and readback. Live target
    dispatch remains outside that authority.

## Work graph and issue acceptance

```text
#104 bounded HTTP transport contract
              |
              +-------------------+
              v                   v
#105 durable signed ingest   #106 lifecycle/product evidence
              +-------------------+
                         |
                         v
#107 installed loopback qualification
                         |
                         v
#108 Cooper/bastion HTTPS ingress
                         |
                         v
#109 live GitHub delivery qualification
```

- #104 proves real-socket framing, routing, budgets, proxy distrust, and bounded
  shutdown without provider or journal effects.
- #105 connects the listener to the existing ingress core and durable journal,
  including replay, failure, restart, and polling convergence.
- #106 provides validated configuration, dedicated executable/service,
  owner-only secret references, readiness/status/support, and documentation.
- #107 proves the exact installed wheel and loopback service with provider-free
  signed fixtures, dispatch disabled, and complete process/port cleanup.
- #108 records the pinned Cooper inventory, local route, generated bastion
  route, public HTTPS behavior, and independent local/remote rollback.
- #109 configures one exact GitHub webhook only after provider preflight,
  observes one post-anchor delivery, proves polling convergence, and records
  provider/runtime cleanup without live target dispatch.

## Parallelism, ownership, and model routing

Execution bias is `balanced`. The primary owns architecture, authority,
integration, GitHub/provider mutations, installed effects, ingress publication,
and final acceptance. Concurrency is at most two implementation workers plus
one read-only reviewer, with no nested delegation.

- #104 is a security-critical contract slice owned by the primary or a
  `gpt-6-astra` high specialist.
- After #104 freezes the seam, #105 and #106 may run in disjoint worktrees in
  parallel using `gpt-5.6-terra` high/medium respectively.
- #107 through #109 are serialized joins owned by the primary; deterministic
  tools perform builds, hashes, polling, port/process checks, and readback.
- A fresh `gpt-5.6-luna` medium reviewer gets one broad discovery pass after
  #105/#106 join and closed-world follow-up only for accepted findings.

Read-only consultations were bounded. `/root/p53_security_architecture` was
requested on `gpt-6-astra` high and froze the HTTP/framing/secret/shutdown
contract. `/root/p53_ingress_topology` was requested on `gpt-5.6-terra` medium
and established the clean shared-repo prerequisite, port/path plan, Authelia
bypass, and rollback sequence. Effective runtime model/allocation metadata were
not reported, so no allocation-savings claim is made.

## Goal controls and bounds

```text
goal_id: P53-G1
goal_version: P53-G1-v1
max_work_unit_attempts: 2
max_review_rework_cycles: 1
max_review_discovery_passes: 1
max_hardening_checkpoints: 2
checkpoint_interval: 1 accepted issue or material effect gate
concurrency_limit: 2 implementation lanes plus 1 read-only reviewer
installed_service_attempts: 1
installed_service_retries: 0
external_ingress_publications: 1
external_ingress_retries: 0
github_webhook_mutation_attempts: 1
github_webhook_mutation_retries: 0
live_delivery_observation_attempts: 1
live_dispatch_attempts: 0
release_attempts: 0
global_install_mutations: 0
authorization_gate: github_webhook_provider_mutation_or_material_departure_only
review_verification_mode: closed_world_if_reviewed
checkpoint_fields: state_transition, acceptance_state, progress_classification, evidence, material_blockers, next_action_or_stop_reason
```

Packet bounds are convergence controls and do not expire standing authority for
safe in-scope work. A failed live or external effect is retained as evidence and
does not silently grant a retry.

## Scope

- Bounded HTTP/1.1 request admission around the accepted webhook core.
- Exact source/listener configuration and secret-reference lifecycle.
- Dedicated installed executable and user-service lifecycle.
- Readiness, status, support, documentation, fixtures, and packaging.
- One isolated installed loopback qualification.
- One exact Cooper local and bastion HTTPS route using the ingress inventory.
- One exact GitHub webhook delivery qualification after provider preflight.
- GitHub issues, short-lived branches/worktrees, pull requests, required CI,
  canonical-main readback, and effect receipts for each accepted slice.

## Non-goals and effect boundaries

- No generic or third-party webhook/plugin ABI, arbitrary package loading,
  dynamic callback, executable payload, provider-selected URL, or raw payload
  persistence.
- No trust in client IP, `Host`, forwarding headers, delivery ID, or payload
  fields as authorization.
- No public health, metrics, status, configuration, admin UI, secret endpoint,
  or browser-login flow on the webhook path.
- No arbitrary repository/workflow/ref widening, GitHub App installation,
  organization webhook, release, tag, global installation refresh, or unrelated
  Cooper/bastion/Authelia change.
- No live tmux, app-server, or OpenClaw dispatch in this goal.

## Validation and invalidation map

- Transport: real sockets, malformed framing, duplicate headers, short/slow/
  oversized bodies, connection floods, deadlines, shutdown, and port ownership.
- Core join: HMAC rotation, provider-read budgets, journal commit/rollback,
  disconnect after commit, replay, restart, and poll/webhook ordering.
- Product: CLI/service install/uninstall, immutable configuration, ownership,
  readiness/status/support, package entry points, and secret absence.
- Installed: exact wheel and executable hashes, isolated roots/service/port,
  signed fixture commit/duplicate, restart, cleanup, and fresh process census.
- Ingress: raw upstream, local hostname, proxy byte preservation, generated
  config, bastion Host-route, public HTTPS, exact-path rejection, and rollback.
- Live delivery: exact GitHub configuration, post-anchor delivery, provider
  status, journal occurrence, polling deduplication, and provider cleanup.
- Every implementation slice passes focused tests, 438-or-current comprehensive
  Python tests, 12-or-current plugin tests, compilation, diff hygiene, and
  required Python 3.11/3.12 CI.

A framing/authentication/commit-order defect invalidates #105 onward. A product
lifecycle defect blocks #107 onward without erasing accepted transport
evidence. An installed failure blocks external ingress. An ingress failure
blocks provider configuration. Provider or live-delivery failure does not erase
accepted local product behavior, but P53 cannot close without an explicit
accepted disposition.

## Stop and replan conditions

Stop on ambiguous HTTP framing, unbounded worker/socket/shutdown behavior,
secret leakage, acknowledgement before durable commit, stale disabled-source
acceptance, unexpected provider or wake effects, loss of polling convergence,
an unplanned interface bind expansion, shared ingress worktree drift, or any
need to expose a non-webhook surface publicly. Stop before GitHub webhook
creation unless the exact repository, workflow, URL, secret reference, actor,
rollback, and provider-mutation authority are all current and explicit.

## Acceptance criteria

- Issues #104 through #106 deliver and productize the bounded listener without
  changing accepted webhook-core or dispatch semantics.
- #107 proves the installed service is restart-correct and fully cleaned up.
- #108 proves the exact external HTTPS route and rollback through the governed
  `cooper-service-ingress` workflow.
- #109 proves one real GitHub delivery commits once and converges with polling,
  with provider and runtime state read back independently.
- ROADMAP, RUNBOOK, this plan, active lanes, issues, PRs, Git, tests, CI, and
  receipts agree on the final state.

## Definition of done

Issues #103 through #109 are closed from accepted evidence; all branches and
worktrees are reconciled; the P53 plan and roadmap lane are closed; the active-
lane catalogue is empty; comprehensive, plugin, package, installed, ingress,
and live-delivery gates pass; polling remains available; provider/runtime
cleanup or intentionally retained state is explicit; and synchronized
`origin/main` has no open P53 pull request or topic branch.
