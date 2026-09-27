# Generic HTTP/JSON completion wakes

State: OPEN
Lane: I169
Issue: #169
Branch: `feat/issue-169-auracall-terminal-source`
Target: `main`
Integration: `squash`

## Current state

The reusable HTTP/JSON completion source is implemented. Operators can save a
bounded fixed URL and JSON Pointer contract, inspect or check it, arm a normal
wake, and remove it after dependent wakes are cancelled. The built-in source
family reads terminal state through the shared journal and dispatch path, with
restart-stable deduplication and separate readiness reporting. AuraCall's
existing status envelope is covered as an ordinary compatibility fixture; no
AuraCall-specific runtime code was added.

Local acceptance is complete: 705 comprehensive Python tests and 12 OpenClaw
plugin tests pass; compilation, diff hygiene, active/goal planning audits,
source-registry smoke, and an isolated installed-wheel smoke also pass. Hosted
CI and integration remain pending.

Plan 0095 is cancelled before implementation because its private receipt-
directory contract was unnecessarily product-specific.

## Objective

Add a reusable, declaratively configured HTTP/JSON event source that watches a
bounded job-status resource, detects configured terminal states, and creates a
normal idempotent Codex Wake. Prove AuraCall response completion as the first
use case through AuraCall's existing run-status API.

## User-facing design

An operator configures:

- a source name and fixed HTTP(S) status URL;
- a standard JSON Pointer selecting the state value;
- the terminal values that should wake, such as `succeeded`, `failed`, or
  `cancelled`;
- a stable event identity, selected from a response field or explicitly bound
  to the configured job identity;
- optional bounded selectors for fields such as job type or profile;
- an existing credential reference when authentication is required; and
- the normal Codex Wake target and monitor-readiness requirement.

The source is not aware of AuraCall types. AuraCall configuration points it at
the existing `/v1/runs/{run_id}/status` resource and selects the existing
`status`, `id`, and update/completion fields.

## Scope

- A generic HTTP/JSON polling source built on the existing signal adapter,
  journal, source registry, wake creation, and dispatch seams.
- Fixed-origin, fixed-method `GET` requests with strict time, redirect, body,
  response-count, and polling budgets.
- Declarative JSON Pointer extraction and bounded equality/inclusion matching;
  no executable expressions or product-specific callbacks.
- Restart-correct observation and immutable event deduplication.
- Configuration, show, check, and remove commands plus health/readiness output.
- Provider-free local HTTP fixtures covering ordinary job APIs, with AuraCall's
  current run-status envelope as one fixture rather than the core schema.
- Tmux and app-server routing-boundary tests through the existing wake path.

## Non-goals

- No AuraCall-specific receipt format, marker file, plugin, callback, or code
  change made solely for Codex Wake.
- No arbitrary shell command, embedded script, JSONPath program, dynamic
  package loading, custom Python callback, or unrestricted URL template.
- No POST, mutation, retry of the watched job, provider action, or raw response
  body stored in wake records.
- No claim that HTTP acknowledgement proves visible Codex delivery.
- No live AuraCall request, live dispatch, service/install change, release, or
  deployment in the provider-free implementation packet.

## Architecture rules

- The transport reads a common HTTP resource; the event layer normalizes only
  bounded selected fields into the existing `NormalizedObservation` contract.
- Source configuration is an allowlist and contains no executable behavior.
- Loopback works by default. Non-loopback origins require explicit operator
  configuration and must resist DNS rebinding, redirect escape, local-network
  pivoting, oversized responses, slow responses, and credential leakage.
- Credentials are referenced through a narrow resolver and never persisted in
  source health, observations, wake records, logs, or support exports.
- Polling re-verifies the resource after restart. One immutable job plus one
  terminal transition produces one logical occurrence.
- Wake context contains the configured source, safe resource locator, selected
  terminal state, and event identity only. The resumed agent must read the
  authoritative system before acting.

## Execution packets

1. Freeze the generic HTTP/JSON configuration and observation contract with
   provider-free red tests, including the AuraCall status envelope fixture.
2. Implement the bounded HTTP reader, JSON Pointer extraction, signal adapter,
   runner, registry entry, and restart deduplication.
3. Add configuration/arming/check/remove commands and readiness projection.
4. Prove existing tmux/app-server routing boundaries, update documentation,
   and run focused, comprehensive, compilation, planning, and hosted checks.

The primary agent owns the shared contract and integration. No parallel worker
is planned because the first three packets share the same security and durable
identity boundary.

## Acceptance criteria

- A standard HTTP/JSON job-status resource can wake Codex when its selected
  field reaches a configured terminal value, without producer-specific code.
- AuraCall's existing `/v1/runs/{run_id}/status` envelope works as a normal
  configuration of that generic source.
- Repeated polling and daemon restart create one logical wake for one terminal
  event.
- Nonterminal, missing, malformed, oversized, timed-out, redirected outside
  the allowed origin, unauthorized, or unverifiable responses fail closed and
  do not dispatch.
- Stored observations and wake prompts contain selected bounded metadata only,
  never raw response bodies or credentials.
- Source, monitor, hook, dispatch acknowledgement, and visible delivery remain
  separate readiness/evidence states.
- Focused, comprehensive, compilation, planning, and hosted CI checks pass
  before integration.

## Goal controls

```text
goal_id: P58-G1
goal_version: P58-G1-v2
max_work_unit_attempts: 2
max_review_rework_cycles: 1
max_hardening_checkpoints: 2
max_review_discovery_passes: 1
checkpoint_interval: 1 execution packet or material gate
concurrency_limit: 1 primary lane
live_provider_reads: 0
live_provider_mutations: 0
live_dispatch_attempts: 0
service_or_install_mutations: 0
authorization_gate: material_departure_or_explicit_action_gate_only
review_verification_mode: closed_world_if_reviewed
checkpoint_fields: state_transition, acceptance_state, progress_classification, evidence, material_blockers, next_action_or_stop_reason
```

## Next action

Publish the implementation, open the issue-linked pull request, and require the
hosted Python 3.11 and 3.12 release gates before squash integration.
