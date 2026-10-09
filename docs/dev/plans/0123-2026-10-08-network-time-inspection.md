# Plan 0123 — Inspect network time without changing the system clock

State: CLOSED
Workflow: DONE
Owner: primary agent lane
Branch: feature/network-time-consensus
Parent: docs/dev/plans/0122-2026-10-08-network-first-time-provider.md
Blocked by: None: can start immediately

## Current State

Implemented the bounded WSL inspection CLI, packaged Windows QPC collector, explicit source policy, fault controls and rate-limited cache. Actual installed-candidate output demonstrates two admitted independent plain-NTP inspection sources; Netnod/PTB remain visible and excluded. No production candidacy or deadline effect is asserted.

## What to Build

An operator runs a bounded inspection command and sees qualified network consensus or explicit source exclusions, without changing any system clock or mailbox.

## Required Inputs

Plan0122, its committed decision core and tests, and the primary-source production qualification note under `docs/dev/evidence/plan0122/production-requirements.md`. Read current repo policy and applicable TDD/code-review skills before implementation.

## Acceptance Criteria

- [x] Demonstrate the actual inspection entrypoint from source configuration through acquisition and normalization to bounded consensus and per-source diagnostics.
- [x] Keep all four candidate operators visible. Admit endpoints only with reviewed identity, explicit time-scale compatibility and a declared authentication policy; unknown profiles remain disabled.
- [x] Choose acquisition packaging through a bounded runnable NTS-client spike; record the decision and preserve failed evidence. Do not implement cryptography or silently downgrade authentication.
- [x] Validate age and common-instant alignment without assuming the WSL guest clock is correct. Evaluate host QPC bracketing, host/guest boot identity, collector generation and conservative interop bounds.
- [x] Select numeric tolerance, freshness, request deadlines, provider polling limits and retry/backoff with a recorded rationale; test values are not production defaults.
- [x] Cover malformed/replayed replies, excessive delay, DNS/transport failure, stale observations, duplicate operators, provider loss and 2–2 splits with deterministic controls.
- [x] Demonstrate at least two independent admitted sources before declaring production candidacy. If qualification remains unresolved, report uncertainty and leave this ticket incomplete rather than manufacture admission.

## Expected Write Surface

Inspection CLI, acquisition/normalization implementation, provider configuration, tests and curated qualification evidence.

## Validation and Definition of Done

Record meaningful failing controls before behavior fixes, focused passing tests, entrypoint readback and standards/spec review. Commit the bounded slice with acceptance evidence, reconcile dependency status, and close only when every criterion is supported. Documentation publication alone is not implementation completion.

## Non-goals

No mailbox integration, live clock or service changes, provider contact, installed production upgrade or effectful TLS bootstrap workaround.

## Acceptance Evidence

See `docs/dev/evidence/plan0123/qualification.md`. Focused time tests: 23 pass; existing CLI tests: 66 pass. Wheel built with `uv build`, installed only in `/tmp/codex-wake-time-candidate`, and its real `codex-wake time inspect` command returned network consensus. Initial plain pip wheel attempt failed for missing build backend; isolated uv build succeeded, with no production package changes. Whitespace and staged review are required before commit.
