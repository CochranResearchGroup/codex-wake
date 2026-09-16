# Ingress canary evidence successor

State: CLOSED
Lane: P53-C5-E1
Issue: #108
Predecessor: Plan 0078 runner review
Branch: `feat/issue-108-cooper-ingress`
Target: `main`
Integration: `squash`

## Current state

The first Plan 0078 runner candidate was rejected before any live effect. One
bounded remediation pass corrected its seven concrete fail-closed defects, and
closed-world verification accepted those corrections. The evaluator retained
two evidence objections: the recorded delivery/header fingerprint is generated
client-side, and the zero production-provider/dispatch counters were not both
backed by executable tripwires.

The delivery objection does not invalidate the issue acceptance contract.
Codex Wake explicitly treats `X-GitHub-Delivery` as an unsigned bounded
diagnostic; durable identity comes from repository/run/attempt. HMAC acceptance
proves the exact body bytes survived each proxy, while application admission
separately proves the required signature, event, media type, path, and method.
A proxy-selected different valid UUID would not change authorization or durable
occurrence identity, so delivery-ID continuity is retained as supporting
evidence rather than an acceptance authority.

Dispatch absence is also not a callable provider-style seam in this executable:
the dedicated listener constructs no evaluator, publisher, daemon, target, or
dispatcher. Readiness projects `dispatch: not_included`, and the journal plus
wake records prove zero firing/submitted/failed transitions. Calling its stored
zero an independently measured function counter overstates the evidence; the
structural projection and terminal-state readback are authoritative.

The production GitHub client factory is a real callable seam and can carry a
network effect. Its zero must therefore be enforced, not merely initialized.

## Objective

Add one fail-closed production-client factory tripwire to the provider-free
bootstrap so any regression increments the owner-only counter and aborts before
network access. Preserve the accepted seven runner corrections and explicitly
record the evidence disposition for delivery identity and dispatch absence.

## Result

Accepted as the terminal evidence correction before publication. The generated
installed bootstrap now replaces the production `GitHubRestClient` constructor
with a counted raising tripwire before runtime construction. Normal fixture
construction leaves that counter at zero; the regression test invokes the
tripwire directly, proves it increments, and proves it raises before client or
socket construction. The owner-only counter remains mode 0600.

The narrow focused suites passed 46 tests. The comprehensive Python suite
passed 538 tests on its first run, the OpenClaw plugin suite passed 12 tests,
and compilation, runner help, and diff hygiene passed. The active-lane audit is
expected to reconcile only after this checkpoint is committed and published.
No listener, service, provider, dispatcher, Traefik, bastion, certificate, or
public-route effect occurred during this successor.

## Scope

- Patch the generated fixture bootstrap to replace the installed listener's
  production `GitHubRestClient` symbol with a counted raising tripwire before
  constructing the runtime.
- Keep the explicitly injected fixture attempt client as the only successful
  authoritative-read path.
- Test counter mode/shape, the zero normal path, and the increment-plus-failure
  regression path.
- Re-run the focused runner/installed suites, comprehensive Python, plugin,
  compilation, CLI help, and diff hygiene gates.

## Non-goals

- No new evaluator pass, architecture change, route change, service effect,
  provider request/mutation, dispatch, global install, or publication.
- No attempt to make the unsigned delivery UUID an authentication authority.
- No synthetic dispatcher import solely to manufacture a counter; retain the
  product's stronger no-dispatch construction and state readback.

## Acceptance criteria

- Normal provider-free construction leaves
  `production_provider_factory_calls == 0` and increments only the fixture
  authoritative-read counter when a signed request is verified.
- Direct or accidental production-client factory use increments the counter
  and raises before a client or socket can be created.
- The counter file remains owner-only and every previously accepted runner
  correction and regression suite remains green.

## Stop condition

Any failed focused, comprehensive, plugin, compilation, help, or diff gate
blocks Plan 0078 live execution. There is no further automatic review/rework
cycle in this packet.

## Definition of done

The production provider factory is a measured zero guarded by an executable
tripwire; the two evidence dispositions are explicit; all validation passes;
and Plan 0078 may publish its runner for canonical-main CI before any live
effect.
