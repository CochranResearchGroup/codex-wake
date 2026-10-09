# Plan 0122 — Network-first time provider

State: OPEN
Branch: feature/network-time-consensus
Owner: primary agent

## Current State

Plans0123–0126 are implemented and accepted on feature/network-time-consensus. The isolated 0.8.0 candidate includes real WSL host-QPC acquisition, two admitted plain-NTP operators, healthy Windows fallback, opt-in versioned mailbox migration and network deadline wakes. Final regression: 950 tests; installed workflow and owned host cache controls passed. See `docs/dev/evidence/plan0126/acceptance-review.md`. Overall plan remains OPEN for production activation and additional-source/authentication qualification; no production upgrade, live migration or real session dispatch occurred.

## Problem Statement

Unreliable guest timing can block agent communication. Windows time also disagreed with two network sources and its synchronization service was stopped. Network redundancy must tolerate outages without selecting arbitrarily between competing groups.

## Solution

Prefer one unambiguous network consensus among independently operated sources. Healthy Windows time is a fallback when the network cannot form any consensus, provided it is consistent with remaining usable network evidence. Conflicting network consensuses always pause time-dependent effects.

## User Stories

1. As an operator, I want multiple independent servers so one outage does not stop deadline evaluation.
2. As an operator, I want network consensus to override an outlying Windows reading.
3. As an operator, I want a 2–2 split to pause rather than choose a potentially wrong clock.
4. As an agent, I want original deadlines retained through sleep and restart.
5. As an operator, I want stale or incompatible observations excluded with visible reasons.
6. As an agent, I want an uncertain deadline to wait rather than fire early.
7. As an operator, I want unhealthy Windows excluded from fallback.
8. As an agent, I want cancellation and inspection available during time uncertainty.

## Implementation Decisions

One new public time-provider interface consumes normalized observations already aligned to the same instant, round and boot. Adapters own actual observation acquisition, protocol validation, authentication and age/alignment uncertainty. The core does not assume Linux wall/monotonic correctness or call clocks/network APIs.

Each observation carries source ID, independently reviewed operator ID, bounded UTC interval, sample age, boot ID, round ID, kind (network/windows), time-scale profile and health. Inputs from adapters are trusted configuration/evidence, not arbitrary user claims of operator independence.

Require at least two distinct network operators. Enumerate all agreeing subsets whose conservative union width is within an explicit tolerance. Select only a unique maximum-cardinality subset. Any tie between different equally large subsets pauses, including overlapping ambiguous clusters. Three agreeing sources beat a dissenting fourth. Two agreeing sources may proceed if the others are absent or isolated outliers. More than one fresh observation per operator is excluded as ambiguous; endpoint aliases do not add votes. Network tie cannot be resolved by Windows.

Filter nonfinite/reversed/wide bounds, stale/future ages, invalid metadata, unhealthy sources, incompatible time scales, wrong boot and wrong round. Caller must supply tolerance and freshness; no production values are silently selected. Healthy Windows fallback cannot override conflicting usable network evidence.

Deadline decision is due only when the accepted lower bound reaches the original deadline; pending only when the upper bound is strictly before it; otherwise uncertain. Sample age is a caller-supplied validated duration, never inferred from wall-clock subtraction. After restart, new boot/round evidence is required. Sleep-inclusive UTC deadlines remain unchanged. This core does not extrapolate cached time or persist state.

## Testing Decisions

Use the existing unittest harness at the public select-time and deadline-decision interfaces. One red-green slice at a time. Cover network selection, outages, unique majority, tied/overlapping clusters, duplicate operators, invalid metadata/bounds, stale/foreign boot evidence, Windows fallback and exact deadline boundaries. These tests prove pure decision behavior, not live adapter safety.

## Scope and Definition of Done for Current Packet

Research note with primary citations and real four-operator transport readback; deterministic selection/deadline core with regression coverage; standards/spec review and committed evidence. Implementation stays isolated and unintegrated. The overall plan stays OPEN until production adapter qualification and mailbox migration are separately completed.

## Out of Scope

No live clock adjustments, service changes, mailbox checkpoint rewrite, installed runtime upgrade, production NTP polling loop, or OpenClaw changes. No claim that two unauthenticated agreeing replies prove canonical UTC. Leap-scale compatibility for additional operators must be explicit before live default admission.

## Current Packet Result

Completed the read-only four-operator transport probe and pure selection/deadline core. Research and raw replies are under `docs/dev/evidence/plan0122/`. No endpoint is enabled in the installed runtime.

Validation: `PYTHONPATH=src python3 -m unittest discover -s tests -p test_time_provider.py` — 16 tests pass. Test-first failures were observed for network voting, invalid observations, deadline handling, policy bounds and review regressions. Four additional invariant checks passed against existing behavior; they are regression coverage, not claimed red-green implementation slices.

Review baseline: commit `50c2eb9`. Standards/spec review found and fixed duplicate source voting, duplicate-operator conflicting evidence being lost before Windows fallback, unenforced per-kind observation limits, and malformed decision intervals permitting deadline release. Each correction was demonstrated failing before its fix. Search is bounded to at most four network observations plus one Windows observation. Core outputs overall uncertainty reasons; per-source rejection diagnostics in user story 5 remain an adapter/integration requirement.

Current packet is complete. Overall state remains OPEN. Next packet: qualify and implement production acquisition/normalization and diagnostics before integrating deadline decisions into mailbox state. Stories about persistence, sleep, cancellation and live wake behavior remain acceptance requirements; pure tests do not prove those runtime properties. No existing persisted schema, mailbox guard, clock or service was changed.

## Production Qualification Follow-up

See `docs/dev/evidence/plan0122/production-requirements.md` for bounded primary-source research and a proposed four-ticket breakdown. NTS availability and a candidate Windows QPC age source are documented; current Netnod/PTB leap profiles, acquisition packaging, numeric bounds and NIST authentication admission remain unresolved. The breakdown is draft pending the to-tickets review; no tickets have been published or marked ready. Repo-native plans remain the tracker authority under policy 0002; there is no configured `docs/agents/issue-tracker.md`, so no remote tracker or competing scratch tracker was created.

## Successor Integration Result (2026-10-08)

The historical packet results and draft breakdown above describe their original state. Their current successor is the accepted Plans0123–0126 implementation, with candidate identity, acceptance matrix, failure dispositions and limits under `docs/dev/evidence/plan0126/`. Original deadlines and legacy guard evidence are preserved. Only Cloudflare/NIST are admitted; Netnod/PTB and NTS remain unqualified. Production activation remains a separate scope. Next: reconcile the exact live bus, guard, bindings and worker; then prepare bounded integration/activation and a real-session exchange for this candidate. Additional independent sources and authenticated acquisition remain useful follow-ups, not implicit blockers to the explicitly opted-in two-provider plain-NTP mode. See `docs/dev/notes/0010-2026-10-08-a2a-readiness-reconciliation.md`.
