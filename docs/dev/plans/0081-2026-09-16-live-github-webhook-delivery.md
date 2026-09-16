# Live GitHub webhook delivery qualification

State: OPEN
Lane: P53-C6
Issue: #109
Branch: `feat/issue-109-live-qualification-runner`
Target: `main`
Integration: `squash`
Parent plan: `docs/dev/plans/0070-2026-09-16-signed-github-webhook-ingress.md`

## Current state

Issue #108 is accepted at canonical
`fd038ebaea5fb1e9a7e81d3f48d18417430258dc`. The exact Cooper and bastion
routes retain only `POST /github/webhook` for
`codex-wake.ecochran.dyndns.org`; no listener currently owns
`127.0.0.1:8820`, and no #109 runtime, secret, provider hook, or dispatch
exists.

Read-only GitHub preflight identified actor `ecochran76`, repository
`CochranResearchGroup/codex-wake` / ID `1242753508`, and active workflow
`CI` / ID `279450573` at `.github/workflows/ci.yml`. The repository is an
unarchived non-fork with ADMIN viewer permission, the workflow runs on pushes
to `main` and pull requests, and the repository currently has no webhooks.
The latest observed main run was successful, but it predates the required
anchor and is not acceptance evidence.

The installed product already has the required runtime boundary: one enabled
source instance, one exact loopback listener, owner-only secret references,
one authoritative attempt read per admitted delivery, commit-before-ack, and a
shared durable journal for polling convergence. What remains is a tested,
fail-closed live qualification runner, an isolated canonical-main runtime, one
separately authorized provider lifecycle, and a durable closeout receipt.

Registration merged through PR #128 at canonical
`75484bbe18d2f1e43c84368805556aba85d8424f`. The provider-free implementation
continues on the re-anchored runner branch; no runtime or provider effect was
performed by registration.

Checkpoint `ec2fddf47ca76370b6fc4c69ed94b6f444835856` implements the
provider-free lifecycle contract and production-local adapter. It binds the
real squash-trigger delivery to the resulting main merge SHA, stages partial
runtime progress for fail-closed cleanup, provisions owner-only token/secret
material, initializes a disabled source before enabling and arming it under a
no-dispatch daemon, validates the exact loopback service, and reads the durable
journal before and after one production no-dispatch poll. Focused C6 tests
pass 16/16, comprehensive Python passes 557/557, the OpenClaw plugin passes
12/12, and compilation/diff checks pass. PR #130 and closed-world review remain
before the trigger PR and exact provider gate.

## Objective

Build and validate a provider-safe live qualification runner, then, only after
exact action-specific authorization, create one repository webhook, trigger
one post-anchor CI run on `main`, prove its completed `workflow_run` delivery
commits once and remains one occurrence after polling, and delete the webhook,
retire the secret, and remove the isolated runtime. Retain only the already
accepted ingress route. Never dispatch a live wake.

## Frozen authority and identities

- GitHub host and actor: `github.com`, `ecochran76`.
- Repository: `CochranResearchGroup/codex-wake`, ID `1242753508`.
- Workflow: `CI`, ID `279450573`, path `.github/workflows/ci.yml`.
- Accepted ref and conclusion: `refs/heads/main`, `success`.
- Provider event: exactly `workflow_run`; qualifying action: exactly
  `completed`.
- Callback: `https://codex-wake.ecochran.dyndns.org/github/webhook` with JSON
  content type and TLS verification enabled.
- Source instance: `p53-c6-live-github`; service:
  `codex-wake-github-webhook-p53-c6-live-github.service`; listener:
  `127.0.0.1:8820`.
- Credential references: `CODEX_WAKE_P53_C6_GITHUB_TOKEN` and
  `CODEX_WAKE_P53_C6_WEBHOOK_SECRET`. Secret bytes are owner-only and never
  enter argv, tracked files, logs, comments, or receipts.
- Trigger: merge one already-green docs-only qualification-trigger pull
  request into `main` after the durable anchor and provider hook exist. Freeze
  its head SHA and expected merge method immediately before the live gate.
- Cleanup: delete the exact newly created hook by returned ID, retire the HMAC
  secret, uninstall the exact user service, and remove the isolated root only
  after safe cleanup evidence. Retain the accepted ingress route unchanged.

These identities establish the requested packet. They do not themselves grant
the provider or trigger authority described below.

## Effect bounds

```text
c6_runtime_establishments: 1
c6_runtime_retries: 0
c6_runtime_cleanup_attempts: 1
c6_secret_provisions: 1
c6_secret_retirements: 1
github_webhook_create_attempts: 1
github_webhook_create_retries: 0
github_workflow_trigger_attempts: 1
github_workflow_trigger_retries: 0
github_webhook_delete_attempts: 1
github_webhook_delete_retries: 0
github_webhook_redelivery_attempts: 0
live_delivery_observation_attempts: 1
live_delivery_observation_retries: 0
live_dispatch_attempts: 0
global_install_mutations: 0
release_attempts: 0
ingress_route_mutations: 0
authorization_gate: exact_hook_create_trigger_and_delete_lifecycle
```

One observation attempt is one bounded window, not one raw provider request.
The hook creation ping and every non-completed or non-allowlisted delivery in
that window are recorded and must cause no journal commit. This plan permits no
manual redelivery. An ambiguous provider write is reconciled by exact readback
before any further write and never grants a retry.

## Ownership, parallelism, and model routing

The primary owns architecture, action-specific authority, GitHub writes,
runtime effects, trigger merge, evidence reconciliation, cleanup, and final
acceptance. At most one standard-tier implementation worker may edit the
provider-free runner and tests. One economical read-only worker may collect
provider state, and one fresh reviewer may perform a single closed-world
verification after implementation. No worker may mutate GitHub, services,
secrets, routes, or scope.

Deterministic tools own hashes, schema checks, test execution, GitHub readback,
polling, and unit/process/socket censuses. Effective model/allocation metadata
is recorded when available; no cost-savings claim is made from requested model
labels alone.

Delegation receipts: `/root/p53_c6_provider_preflight` completed the read-only
provider inventory; `/root/p53_c6_acceptance_audit` found and bounded the
create/trigger/delete and cleanup counters; `/root/p53_c6_runner_impl` produced
checkpoint `7d651f4` after one incomplete checkpoint and one closed-world
remediation pass. The primary rejected the incomplete execution boundary,
integrated the remediated contract, and added the production-local adapter at
`ec2fddf`. Effective runtime model/cost metadata was not reported, so no
allocation claim is made. `/root/p53_c6_runner_review` owns one final
closed-world review of `ec2fddf`.

## Work graph

```text
A registration + read-only preflight
                 |
                 v
B provider-free runner + tests + required CI
                 |
                 v
C already-green docs-only trigger PR, left unmerged
                 |
                 v
D exact operator gate
                 |
                 v
E isolated runtime + durable anchor
                 |
                 v
F create hook -> read back -> merge trigger once
                 |
                 v
G observe completed delivery -> poll convergence -> independent reads
                 |
                 v
H delete hook -> retire secret -> remove runtime -> fresh census
                 |
                 v
I verification + issue/parent/plan closeout
```

A through C are provider-free and proceed under the standing development goal.
D is a hard stop. E through H form one serialized lifecycle after exact
authorization; cleanup remains required after a post-create failure.

## Runner contract

The source runner must default to read-only preflight and require an explicit
execution arm plus the exact private root for every effectful phase. It must:

1. bind the candidate to a clean exact `origin/main` commit and fresh isolated
   wheel/virtual environment without changing the ordinary global install;
2. create a fresh owner-only root, environment file, source/listener config,
   journal, and durable wake anchor with dispatch disabled;
3. verify the accepted route, source identity, unit/PID/socket ownership,
   readiness, secret-file ownership/mode/reference, and zero pre-existing hook;
4. construct provider requests without exposing secret bytes and preserve only
   sanitized request fingerprints plus returned hook/delivery identifiers;
5. read back the exact hook configuration after create and stop on any URL,
   event, active-state, content-type, or TLS-verification mismatch;
6. observe a bounded delivery window and accept exactly one authenticated,
   authoritative, completed allowlisted occurrence after the anchor;
7. run one real polling pass against the same source and prove receipt count
   remains one while the wake transitions only locally with dispatch zero;
8. independently read provider delivery status, journal counts and identity,
   source checkpoint, listener/unit/PID/socket state, and dispatch-disabled
   state;
9. delete only the returned hook ID, prove it absent, uninstall the exact
   service, retire the secret, and remove the root only when the cleanup
   interlock is safe; and
10. stage a secret-scanned receipt after every material phase, preserving the
    private root and fail-closed cleanup state on uncertainty.

The runner never creates a hook, merges a pull request, redelivers a webhook,
dispatches a wake, edits ingress, releases, or refreshes a global install
without the primary's explicit external orchestration at the relevant gate.

## Live sequence and rollback

1. Re-read canonical Git/CI, provider actor/repository/workflow/hooks, exact
   public route, port/process/unit, and unrelated failed-unit baselines.
2. Establish the one isolated runtime and durable post-install anchor. Confirm
   listener readiness and an unsigned public rejection without committing an
   occurrence.
3. Stop for exact operator authority if it is not already current for all of:
   one hook creation, the frozen trigger-PR merge, and one hook deletion.
4. Generate the fresh HMAC secret into the owner-only environment, create the
   exact hook once, and read it back by returned ID. Record the automatic ping
   separately.
5. Merge the frozen already-green docs-only trigger PR once. Record its merge
   SHA and the resulting exact main CI run ID/attempt.
6. Observe the bounded provider delivery window. The qualifying completed
   delivery must return `200`, and authoritative API readback must agree on
   repository/workflow/ref/conclusion/run/attempt/head SHA and post-anchor
   terminal proof.
7. Prove the journal contains one normalized occurrence, then poll once and
   prove the same occurrence remains one while dispatch stays zero. Read
   provider delivery status and runtime health independently.
8. In an unconditional finally path after hook creation, delete the exact hook
   once and read back absence. Retire the HMAC secret, uninstall the service,
   verify unit/PID/process/listener absence, and remove the isolated root only
   after the cleanup interlock passes.
9. Record that the Cooper/bastion route remains intentionally retained and
   unchanged. Publish verification and reconcile #109, parent #103, Plan 0070,
   ROADMAP, RUNBOOK, branches, worktrees, and the active-lane catalog.

If creation is ambiguous, list exact hooks and match only the frozen callback
and events before deciding state; do not issue another create. If deletion is
ambiguous, read the exact hook ID/list before any further mutation. Any failure
after creation still proceeds to the single cleanup attempt, but it does not
authorize redelivery, a second trigger, or a retry.

## Acceptance evidence

- exact actor, repository ID, workflow ID/path, ref, conclusion, callback,
  event, active state, content type, TLS verification, opaque secret refs, and
  sanitized hook configuration;
- canonical candidate/tree/wheel hashes, isolated root identity, source and
  listener summaries, anchor/checkpoint, unit/PID/start/socket identity, and
  owner/mode evidence without secret bytes;
- hook ID and provider create/readback timestamps; every bounded-window
  delivery ID/action/status plus exactly one qualifying completed delivery;
- trigger PR/head/merge SHA and resulting run ID, attempt, head SHA, event,
  status, conclusion, and authoritative terminal proof;
- normalized occurrence identity
  `github:repository:<repository_id>:run:<run_id>:attempt:<run_attempt>`, durable
  receipt count before/after polling, checkpoint movement, wake state, and
  dispatch counters of zero;
- hook deletion readback, secret retirement, service/root cleanup or preserved
  uncertainty, fresh unit/process/socket census, unrelated-state deltas, and
  explicit retained-route identity/hash;
- focused, comprehensive, plugin, compilation, diff, planning, hosted CI, and
  closed-world review results tied to exact commits.

## Stop conditions

Stop before creation on dirty/unreviewed canonical state, a pre-existing or
colliding hook, repo/workflow/actor drift, an ungreen or mutable trigger PR,
route/hash drift, occupied port, matching unit/process, unsafe credential or
secret ownership, absent journal/anchor, enabled dispatch, non-loopback bind,
or missing exact lifecycle authority. After creation, stop qualification on an
unexpected repo/workflow/ref/conclusion, pre-anchor terminal proof, secret or
payload leakage, authoritative-read mismatch, non-unique durable occurrence,
provider ambiguity, listener restart, unexpected dispatch, or unrelated
mutation. Run only the bounded cleanup path.

## Non-goals

- No organization/global webhook, GitHub App, arbitrary repository/workflow/
  ref widening, manual redelivery, workflow file change, release, tag, global
  install refresh, route/Traefik/DNS/certificate/firewall mutation, Authelia,
  public diagnostics, non-loopback bind, or live tmux/app-server/OpenClaw
  dispatch.
- No reuse of C4/C5 canary roots, fixtures, secrets, sources, deliveries,
  wakes, journals, or bootstrap seams.
- No provider hook or secret retained after the packet; retaining either would
  be a materially different ongoing effect requiring new exact authority.

## Acceptance criteria

- The provider-free runner and its failure/cleanup/redaction tests pass and are
  integrated through both hosted release gates before any live effect.
- One exact post-anchor completed main CI occurrence is authenticated,
  authoritatively verified, committed once, and remains one durable occurrence
  after polling; dispatch remains zero.
- Provider hook state/delivery, journal/checkpoint/wake state, listener/service
  health, secret-reference ownership, and unrelated state are independently
  read and agree.
- The hook is deleted, its secret retired, the isolated runtime cleaned safely,
  and only the previously accepted exact ingress route is intentionally
  retained.
- No out-of-scope provider, route, release, global-install, diagnostic, or
  dispatch effect occurs.

## Definition of done

The live lifecycle is accepted from a durable verification artifact or has one
truthful no-retry failure disposition; cleanup state is independently known;
issue #109 and parent #103 close only if their criteria are satisfied; Plan
0070, ROADMAP, RUNBOOK, GitHub, Git, CI, branches/worktrees, and the active-lane
catalog agree; and synchronized `origin/main` has no open P53 pull request or
active P53 lane.
