# Plan 0123 — Inspect network time without changing the system clock

State: PLANNED
Workflow: READY
Owner: primary agent lane
Branch: feature/network-time-consensus
Parent: docs/dev/plans/0122-2026-10-08-network-first-time-provider.md
Blocked by: None: can start immediately

## Current State

Approved breakdown published as a repo-native ticket. Implementation has not started. This is the first execution frontier.

## What to Build

An operator runs a bounded inspection command and sees qualified network consensus or explicit source exclusions, without changing any system clock or mailbox.

## Required Inputs

Plan0122, its committed decision core and tests, and the primary-source production qualification note under `docs/dev/evidence/plan0122/production-requirements.md`. Read current repo policy and applicable TDD/code-review skills before implementation.

## Acceptance Criteria

- [ ] Demonstrate the actual inspection entrypoint from source configuration through acquisition and normalization to bounded consensus and per-source diagnostics.
- [ ] Keep all four candidate operators visible. Admit endpoints only with reviewed identity, explicit time-scale compatibility and a declared authentication policy; unknown profiles remain disabled.
- [ ] Choose acquisition packaging through a bounded runnable NTS-client spike; record the decision and preserve failed evidence. Do not implement cryptography or silently downgrade authentication.
- [ ] Validate age and common-instant alignment without assuming the WSL guest clock is correct. Evaluate host QPC bracketing, host/guest boot identity, collector generation and conservative interop bounds.
- [ ] Select numeric tolerance, freshness, request deadlines, provider polling limits and retry/backoff with a recorded rationale; test values are not production defaults.
- [ ] Cover malformed/replayed replies, excessive delay, DNS/transport failure, stale observations, duplicate operators, provider loss and 2–2 splits with deterministic controls.
- [ ] Demonstrate at least two independent admitted sources before declaring production candidacy. If qualification remains unresolved, report uncertainty and leave this ticket incomplete rather than manufacture admission.

## Expected Write Surface

Inspection CLI, acquisition/normalization implementation, provider configuration, tests and curated qualification evidence.

## Validation and Definition of Done

Record meaningful failing controls before behavior fixes, focused passing tests, entrypoint readback and standards/spec review. Commit the bounded slice with acceptance evidence, reconcile dependency status, and close only when every criterion is supported. Documentation publication alone is not implementation completion.

## Non-goals

No mailbox integration, live clock or service changes, provider contact, installed production upgrade or effectful TLS bootstrap workaround.
