# GitHub webhook product lifecycle

State: OPEN
Lane: P53-C3
Issue: #106
Branch: `feat/issue-106-webhook-product-lifecycle`
Target: `main`
Integration: `squash-after-#105-join`

## Current state

Canonical main `558ae15723a9dfcd4b79b31c7a66e53439328707`
contains the accepted provider-neutral HTTP transport but no supported webhook
configuration, executable, user service, readiness/status/support projection,
packaging entry point, or operator lifecycle. Issue #105 is implementing the
durable runtime join on a disjoint branch. This lane may build its product
surfaces in parallel but cannot integrate or claim executable acceptance until
it joins #105's canonical runtime.

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
- Default bind is `127.0.0.1`; non-loopback requires an explicit named option.
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
