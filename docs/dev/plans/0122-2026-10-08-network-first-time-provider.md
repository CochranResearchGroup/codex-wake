# Plan 0122 — Network-first time provider

State: CLOSED
Branch: feat/network-time-provider (integration); feature/network-time-consensus (preserved source)
Owner: primary agent
Work-Item: https://github.com/CochranResearchGroup/codex-wake/issues/224

## Current State

Revision2 is COMPLETE under issue224. Implementation PR225 merged as edf2aea4c5480202639bb3e94be7f16300b8efcb after hosted Python3.11/3.12 gates; published v0.8.0 and stable installed files match that exact main commit. Three independently operated plain-NTP sources form bounded consensus and each controlled single-source omission retains quorum. The stable native A→B→A exchange completed automatically, with suspended sender, actual peer reads/reply, verified digest/correlation, exactly two submitted notifications and submitted arm.963 comprehensive tests pass; installed workflow and provider controls pass. See `docs/dev/evidence/plan0122/activation/requirement-audit.md` and its receipts.

The owned bus is paused and backed up at schema3; owned worker finished and both owned client process trees are stopped. Existing service roots/checkpoints were not reset or migrated. NTS, unknown Netnod/PTB profiles, actual host reboot/suspend and healthy Windows observation remain explicit limits under the approved unauthenticated opt-in scope. The original packet/proposal sections below are historical; this current state and revision2 govern completion.

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

## Goal execution revision 2 — 2026-10-08

User objective: complete Plan0122; diagnose and fix bugs; checkpoint before two million tokens or three hours. Goal began about02:05UTC October9; checkpoint by05:00UTC. Earlier isolated-packet exclusions remain historical for those packets. The user now authorizes the ordinary integration, installed activation and bounded live acceptance needed to complete this plan. Clock adjustment, reboot/suspend, legacy checkpoint reset, unrelated private messages and OpenClaw changes remain excluded.

Primary lane remains feature/network-time-consensus. Serial critical path: reproduce and repair end-to-end worker/reply time-domain gaps; qualify adequate independent-source redundancy; review/regress/build; reconcile existing live store/guard before any migration; integrate/install using recoverable custody; run one owned bounded exact-thread request/reply exchange and audit every original user story. Use a fresh explicitly enrolled bus if the historical store's guard cannot safely migrate; preserve and report the historical hold without resetting it. Do not substitute a synthetic transport or fixture acknowledgement for actual agent delivery. The first new evidence is a CLI worker outage regression, not another planning packet. Current goal counters are authoritative via get_goal; all subsequent turns inherit the same ceiling.

Completion requires verified source/installed identities, bounded acquisition and provider-loss behavior, versioned migration without guard bypass, retained deadlines through restart/outage, usable inspection/cancellation, and actual automatic A2A delivery on the network-time path. Extra-source and authentication work must have a truthful qualification disposition; no endpoint is enabled from ordinary agreement alone. If authentication cannot be qualified, retain the explicit unauthenticated trust policy and record that boundary rather than claim canonical authenticated UTC. Review once against the frozen baseline7a4666a and repair accepted findings, avoiding repeated unrelated hardening.


## Revision2 Acceptance Result

All eight original stories are audited in activation/requirement-audit.md. Candidate exchange1 failed and is preserved; its contention pattern was reproduced and repaired. Candidate exchange2 and stable installed exchange3 both passed without controller intervention after admission. Additional native-path review fixes cover outage recovery, reply/transport clock domain, current idle composer and read-only persisted continuity. Source review and exact receipts remain in activation/review.md and activation/progress.md.

Release: https://github.com/CochranResearchGroup/codex-wake/releases/tag/v0.8.0 . No authentication guarantee, arbitrary old-reader compatibility, indefinite service rollout or historical clock root-cause conclusion is implied. Existing issue181/wider Plan0101 retained obligations remain separate.
