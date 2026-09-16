# Cooper webhook ingress publication

State: OPEN
Lane: P53-C5
Issue: #108
Branch: `chore/issue-108-ingress-qualification`
Target: `main`
Integration: `squash`
External repository: `CochranResearchGroup/cooper-webservices`
External branch: `feat/codex-wake-webhook-ingress-108`

## Current state

Issue #107 is accepted and its disposable qualifier is removed. The #108
runner and evidence contract are accepted on canonical Codex Wake main at
`033d2cc7187e4448e2809299701a2975d0790e80` after both hosted release gates
passed. The clean Cooper authority is `CochranResearchGroup/cooper-webservices`
main at `cd0d60f91d870c1372b2d7d5f8e16602f52f1d6a`; its reviewed inventory and
renderer emit only the frozen exact path-plus-method routes. The generated
bastion snippet has SHA-256
`ffcb4efabc644d9da705e3369be043de28fe5c8f3b4850681e002ca2f5a68a64`.

No #108 live effect has occurred. Port 8820 remains unclaimed, no matching C5
unit or process exists, the local route has not been rendered, and the bastion
target remains absent. The live qualification must re-read those boundaries
before consuming the one canary establishment or the one external publication.

A disposable network probe proved that Docker Desktop Traefik can reach a WSL
service bound only to `127.0.0.1`; no non-loopback bind or wildcard authority is
needed. Bastion publication is explicitly authorized by the operator. No
GitHub webhook/provider mutation or live dispatch is authorized in this slice.

## Objective

Publish one exact `POST /github/webhook` HTTPS route through the governed Cooper
inventory and bastion workflow after proving the exact installed main wheel on
`127.0.0.1:8820` with a provider-free signed fixture. Preserve raw request
bytes, expose no host catchall or diagnostic surface, bypass Authelia only on
that HMAC-authenticated route, and retain durable local, remote, runtime, and
rollback evidence.

## Effect bounds and ownership

- The primary owns the runtime, local Traefik, bastion, commits, publication,
  acceptance, and rollback decisions.
- One read-only independent reviewer may inspect topology and the frozen packet;
  implementation workers may edit only the isolated Cooper branch.
- `c5_ingress_canary_establishments: 1`; this is a new #108 prerequisite, not a
  retry of the consumed #107 qualification attempt.
- `external_ingress_publications: 1`; `external_ingress_retries: 0`.
- `github_provider_reads: 0`; `github_provider_mutations: 0`;
  `live_dispatch_attempts: 0`; `global_install_mutations: 0`.
- The canary uses a fresh owner-only, non-global, versioned wheel environment
  and a distinct `p53-c5-ingress-canary` source. It never mutates the retained
  #107 recovery root or the ordinary user installation.
- The provider-free bootstrap is permitted only for C5 route qualification.
  It injects one frozen authoritative attempt fixture before the installed
  listener entrypoint and is explicitly removed or stopped at closeout.
- The exact ingress routes remain durable for #109. Rollback evidence records
  the pre-publication absence, hashes, exact reversal commands, and independent
  local/remote boundaries; the route is not rolled back and republished because
  that would exceed the one-publication bound.

## Frozen ingress contract

1. Inventory service name is `codex-wake`, local host is
   `codex-wake.localhost`, public host is
   `codex-wake.ecochran.dyndns.org`, and the pinned upstream is
   `http://host.docker.internal:8820`.
2. The application stays on exactly `127.0.0.1:8820`. Cooper Traefik is the
   only bridge from Docker/local ingress; the raw port is not published by
   Traefik or bastion.
3. Local-host, Cooper external-host, and bastion routers select exactly
   `Path(`/github/webhook`) && Method(`POST`)`. No prefix selector, host-wide
   fallback, redirect, public HTTP router, or Authelia middleware is rendered.
4. The application remains the final admission authority: raw wrong paths and
   methods are rejected, unsigned requests are rejected, and only an exact
   signed fixture can commit.
5. The external request body and security headers reach the application
   unchanged. Evidence binds the fixture body digest and one durable logical
   occurrence across raw, local, Cooper-Host, and public routing checks.
6. No health, status, support, configuration, metrics, admin, secret, or raw
   port surface is exposed. Response headers and bodies must not disclose a
   port, filesystem path, diagnostic state, configuration, or secret.
7. The provider-free canary is stopped and uninstalled after public
   qualification. #109 must establish its distinct production source/runtime
   before creating the GitHub webhook; it may reuse the accepted routes but not
   the canary secret, fixture, source instance, journal, or bootstrap.

## Scope

- Correct the Cooper renderer to support `external.paths_only`, exact generic
  path selectors, and method selectors on both Cooper external-host and bastion
  routes.
- Add the `codex-wake` inventory entry and generated local/bastion artifacts.
- Build and install a fresh canonical-main wheel into a private C5 environment;
  configure one provider-free source/listener and supported user service.
- Validate raw upstream, local hostname, Cooper public Host routing, generated
  bastion syntax, bastion upstream reachability, and public HTTPS behavior.
- Commit the Cooper source/inventory changes separately from the bastion
  snippet plus `CODEX_LOG.md` entry, preserving unrelated bastion dirt.
- Record source commits, artifact hashes, process/socket ownership, config
  hashes, runtime readbacks, public responses, and exact rollback locators.

## Non-goals

- No GitHub webhook creation, secret shared with GitHub, live GitHub delivery,
  provider read, repository/workflow widening, release, tag, or dispatch.
- No Authelia rule or middleware, generic webhook ABI, public health surface,
  raw port exposure, wildcard/non-loopback bind, global install, or reuse of
  #107 evidence state.
- No unrelated Cooper, bastion, Docker Desktop, DNS, certificate, firewall, or
  service change.

## Execution sequence

1. Publish this plan and active-lane registration, claim issue #108, and bind
   both isolated branches to their canonical bases.
2. Test-drive the Cooper renderer correction and `codex-wake` inventory. Run
   focused tests, full Cooper tests, compilation, strict inventory validation,
   render-only generation, and exact config inspection. Land the focused
   Cooper pull request before live route changes.
3. Build a fresh wheel from exact canonical Codex Wake main, install it into a
   fresh owner-only C5 environment, capture provenance/hashes, initialize a
   distinct provider-free source and journal, and install the supported
   loopback unit once with the explicit fixture bootstrap.
4. Prove readiness, exact PID/socket ownership, no restart loop, raw signed
   commit/duplicate, unsigned rejection, application wrong-path/method
   rejection, provider exclusion, and dispatch absence.
5. Preflight local Traefik ownership and rendered config, then render/restart it
   once. Validate signed and unsigned behavior through
   `codex-wake.localhost` and the exact public Host header while checking the
   same durable occurrence and body digest.
6. Read bastion `AGENTS.md`, Git status, target absence, Traefik syntax/runtime,
   upstream Host behavior, and rollback locators. Stop before publication on
   any drift affecting the target or existing routes.
7. Consume the one external publication by installing the exact generated
   snippet and restarting bastion Traefik once. Validate public HTTPS signed,
   unsigned, wrong-path, and wrong-method behavior plus response leak checks.
8. Commit only the new bastion snippet and `CODEX_LOG.md` entry, record remote
   status/runtime/config hashes, then stop/uninstall the canary service and
   prove its process/socket cleanup without removing the accepted routes.
9. Publish the #108 verification artifact, reconcile issue/PR/CI/canonical
   state, close the lane, and hand #109 only the retained route and evidence.

## Acceptance criteria

- The fresh isolated installed wheel, supported unit, runtime configuration,
  and Cooper inventory agree on `127.0.0.1:8820`; port/process ownership and
  cleanup are explicit.
- Raw and local proxied signed fixtures return `200` only after durable commit;
  unsigned input is rejected, bytes are preserved, and provider/dispatch
  counters remain zero.
- Cooper and bastion generated config contain only exact path-plus-POST routers
  for this host, contain no catchall and no Authelia middleware, and pass syntax
  plus runtime loading checks.
- Public HTTPS reaches the same provider-free canary correctly; non-exact
  path/method traffic remains absent at the proxy while raw checks separately
  prove application rejection.
- Headers and bodies disclose no raw port, diagnostic/config/status surface,
  filesystem locator, or secret.
- Cooper source/inventory and bastion runtime changes have separate durable
  commits, post-effect readbacks, preserved unrelated dirt, and deterministic
  rollback receipts.

## Stop conditions

Stop before the live effect on a dirty or unreviewed Cooper candidate, occupied
8820, non-loopback requirement, missing installed provenance, provider-capable
fixture path, source/journal ambiguity, secret leakage, catchall/prefix router,
Authelia attachment, local proxy byte drift, bastion target collision, remote
policy or syntax failure, or unrelated route regression. Any failure after the
single bastion copy/restart consumes the publication; preserve evidence and do
not retry without a new explicit disposition.

## Definition of done

The one publication is accepted from durable local and bastion evidence; the
provider-free canary is removed with no listener/process left; exact ingress
routes remain ready for #109; Codex Wake issue #108 closes through its pull
request and required CI; both branches/worktrees and the active-lane catalog
are reconciled; and no provider, dispatch, release, global-install, or
non-loopback effect occurred.
