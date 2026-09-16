# GitHub webhook product lifecycle

State: OPEN
Lane: P53-C3
Issue: #106
Branch: `feat/issue-106-webhook-product-lifecycle`
Target: `main`
Integration: `squash-after-#105-join`

## Current state

Canonical main `1d32bb1d12531ab41fb36c0180fc0510be8e1c88`
contains the accepted provider-neutral HTTP transport and durable signed-ingest
runtime from #105. This branch joined that exact commit and now owns the
supported configuration, executable construction, user service,
readiness/status/support, packaging, and operator lifecycle acceptance.

## Objective

Productize one dedicated signed GitHub webhook listener as a supported
owner-scoped executable and user service with immutable bounded configuration,
opaque current/previous secret references, local readiness/status/support, and
clean install/uninstall behavior. Keep loopback default, dispatch absent, and
external ingress/provider mutation outside this slice.

## Frozen product contract

- Extend the existing GitHub source authority with a bounded webhook
  subconfiguration or adjacent owner-only store. Persist only listener budgets,
  exact source identity, enabled state, and one or two opaque secret references;
  never persist secret bytes.
- Material authority changes require a new source instance. A narrow enabled
  toggle and exact idempotent rewrite may reuse an instance.
- Default bind is `127.0.0.1:8820`; non-loopback requires persisted explicit
  `allow_non_loopback` authority. Wildcard binds remain forbidden.
  Port is explicit, exact route remains `/github/webhook`, and no public
  health, UI, status, config, metrics, or secret endpoint is added.
- Add a dedicated executable that constructs the #105 runtime only from one
  enabled configured source and owner-resolved environment references. It does
  not construct the wake daemon, evaluator, publisher, dispatcher, or polling
  loop.
- Add an owner-scoped systemd user unit/install lifecycle with explicit
  environment/config paths, restart policy, hardening compatible with the
  existing runtime, deterministic stop, and no global/system service mutation.
- Readiness proves configuration validity, exact process/service ownership,
  expected bind/port, and journal accessibility without provider calls.
  Status/support expose bounded nonsecret state and stable repair guidance.
- Disabled/reconfigured sources, missing/invalid refs, foreign ownership,
  symlinks, permissive modes, occupied ports, duplicate service ownership, and
  absent #105 runtime fail closed.

## Parallel boundary with #105

This lane owns CLI/config/service/packaging/docs/readiness/support files. It
must not edit `webhook_http.py`, `github_client.py`, `github_webhooks.py`,
the #105 integration module, or #105's focused tests. During parallel work it
may use an import seam or test double matching the frozen #105 lifecycle:
bound address, blocking main-thread `serve()`, and bounded `shutdown()`.
Final validation occurs only after merging canonical #105 into this branch.

## 2026-09-16 implementation evidence

- Added `webhook_lifecycle.py`: owner-scoped bounded configuration at
  `github/webhook-listeners.json`, fixed route, loopback-default/no-wildcard
  validation, idempotent rewrites, enabled-only reuse, current/previous
  opaque environment-reference rotation. The store and support projection do
  not contain secret values. The schema persists `allow_non_loopback`, has a
  262144-byte body default/1048576-byte ceiling, and exposes bounded
  `max_connections` rather than a worker or queue setting.
- Added `codex-wake-github-webhook` as a deferred-import executable seam and a
  provider-free lifecycle contract test double. It requires a runtime with a
  blocking main-thread `serve()` and bounded runtime-owned `shutdown()`.
- Corrected the lifecycle packet to use read-only MainPID plus `/proc` socket
  inode/address/port ownership proof by default (still injection-testable),
  require enabled sources for install/start, stop and confirm an active owner
  before a disable persists, and provide a per-request owner secret resolver
  instead of startup secret bytes.
- Joined canonical #105 behind the unchanged executable interface. The deep
  builder selects the same enabled GitHub source, opens the existing signal
  journal, derives a source-bound no-coverage seed without a provider call,
  creates a fresh deadline-leased `GitHubRestClient` per delivery, and passes
  explicit transport, signed-core, and provider/store budgets to one runtime.
- Added the fixed owner-only `github/webhook.env` service contract. The unit
  persists only its path; installation/start and readiness reject missing,
  symlinked, foreign-owned, permissive, or oversized files without reading or
  projecting secret values.
- Added user-service render/install/stop/status/uninstall helpers and CLI
  configuration, service, readiness, and support commands. No real service was
  installed during this lane.
- A real-socket builder tracer uses configured source authority, an existing
  temporary SQLite journal, a signed fixture, and a provider-free authoritative
  attempt fake to prove commit-before-ack through the joined executable module.
  The executable interface remains bound address, blocking main-thread
  `serve()`, and bounded no-argument `shutdown()`.

## TDD sequence

1. Owner-only nonsecret configuration and rotation/reference validation.
2. CLI configure/list/show and stable JSON/nonsecret summaries.
3. Dedicated executable construction, disabled/error paths, and dispatch
   absence with injected runtime factories.
4. User-service render/install/uninstall/restart configuration.
5. Readiness, status, support, occupied-port/second-owner, and secret absence.
6. Join canonical #105 and run an executable loopback signed fixture without
   provider or dispatch effects.

## Validation

- Focused config/CLI/executable/service/readiness/support tests.
- Secret canaries absent from argv, output, support, status, tracked files, and
  rendered units.
- Package build and installed-wheel entry-point smoke in an isolated target.
- Comprehensive Python, plugin, compilation, diff hygiene, planning audit, and
  required Python 3.11/3.12 CI after the #105 join.
- No real service install, provider call, non-loopback bind, Cooper route,
  release, deployment, or dispatch effect.

## Combined local validation | 2026-09-16

- Joined lifecycle, runtime, and client focused suites passed: 18, 10, and 12
  tests respectively.
- Comprehensive Python passed 486 tests in 17.939 seconds; the OpenClaw plugin
  tier passed 12 tests. Compilation, diff hygiene, and the active planning
  audit passed with only its accepted legacy baseline.
- The first packaging command failed because the selected interpreter's
  installed `build` package has no executable module. The failure was retained;
  `uv build --wheel` then produced the isolated candidate wheel with SHA-256
  `86c4d59fcbdca38409d7a198bbdfa454d7e3d36b656aa44ecdee98a60624e766`.
  An isolated target install read back version `0.5.2` and entry point
  `codex-wake-github-webhook = codex_wake.webhook_listener:main`.
- This evidence is local and provider-free. Independent review and required
  Python 3.11/3.12 PR checks remain before #106 acceptance.

## Stop conditions

Stop and replan on secret persistence/output, wildcard bind without named
authority, public diagnostics, generic callback/plugin loading, overlapping
#105 edits, runtime interface drift, global/system service mutation, provider
traffic, or any need to evaluate or dispatch wakes.

## Definition of done

After #105 is canonical, PR and CI accept the supported product lifecycle;
issue #106 closes from exact package and lifecycle evidence; branch/worktree/
active-lane custody is cleaned up; and #107 can perform one isolated installed
loopback qualification without inventing configuration or service behavior.
