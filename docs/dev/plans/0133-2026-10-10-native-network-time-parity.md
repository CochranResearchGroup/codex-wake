# Plan 0133 — Native network-time parity

State: OPEN
Workflow: IN_PROGRESS
Owner: primary agent
Lane: P66
Target: origin/main
Integration: squash_pr
Branch: feat/native-network-time
Work-Item: docs/dev/plans/0133-2026-10-10-native-network-time-parity.md

## Current State

Planning approved on 2026-10-10. Plan0122 supplies the released network-first
provider; Plan0127 supplies released native delivery. At canonical baseline
38c74f3, native creation and expiry still use guest UTC. This plan and its three
tickets define the successor; no successor implementation or runtime acceptance
has run. Repo-native plans remain the ticket authority.

## Problem Statement

A native follow-up must use the same trustworthy deadline policy as a classic
network-time wake. Guest clock disagreement must not produce early delivery,
premature expiry, or a changed deadline after restart.

## Solution

Reuse the existing admitted network consensus and health-qualified Windows
fallback for new native wakes and every time-dependent effect on those wakes.
Reject an arming command visibly and create no record when trustworthy time is
unavailable. Existing armed wakes hold through uncertainty, retaining their
original due time and expiry. Inspection and cancellation remain available.

## User Stories

1. As an agent, I want `native after` based on bounded external time so guest clock errors cannot shorten my wait.
2. As an agent, I want `native at` to preserve my timezone-qualified absolute deadline.
3. As an operator, I want an unavailable-time arm rejected with no partial record.
4. As an operator, I want a single admitted server loss tolerated by existing consensus.
5. As an operator, I want conflicting or stale evidence to hold effects visibly.
6. As an agent, I want healthy Windows fallback to obey the existing admission policy.
7. As an agent, I want my wake's due time and TTL unchanged through outage and restart.
8. As an operator, I want expiry decided conservatively using trustworthy time.
9. As an operator, I want native file-trigger TTL to use the same policy.
10. As an operator, I want cancellation and inspection during a time hold.
11. As an agent, I want uncertain native submission reconciled without resend.
12. As an existing user, I want old records preserved and their time policy reported honestly.

## Implementation Decisions

- Reuse the provider, admitted operators, independence rules, bounded intervals,
  source freshness, and health-qualified fallback from Plan0122. No new servers,
  authentication claims, tolerance changes, clock adjustment or clock diagnosis.
- New native wakes use network-first time by default. Relative deadlines and TTL
  start from the conservative upper bound; absolute deadlines retain their input
  instant. Preserve existing timestamp precision and never round toward early firing.
- Use accepted lower-bound time to release due work and declare expiry. An interval
  crossing a deadline holds; do not fall back to guest UTC to resolve uncertainty.
- Cover native file registration/TTL and recipient retry eligibility as deadline
  operations. File existence remains a condition, not proof of trustworthy time.
- Persist policy identity and original deadlines. Settle the versioned record
  contract in ticket0134 before coding; do not overwrite schema4 with the classic
  schema3 marker or silently change old records' time domain.
- Existing records retain their semantics unless explicitly migrated with a
  recoverable backup and documented reader compatibility. No bulk live migration.
- After worker restart require fresh admitted observation; never rebase deadlines.
- Exact thread, explicit same-thread resume, busy/missing guards, durable intent,
  attempts, accepted-versus-completed distinction and no-blind-resend remain intact.

## Testing Decisions

Primary behavior seam: public CLI plus scheduler reading persisted records across
process boundaries. Use the existing provider seam to supply bounded observations
for deterministic outage, boundary, skew and restart tests. Existing network-wake
and native-delivery tests are prior art. Finish with an immutable installed wheel,
normal supervisor, and disposable real Codex recipient. A fake transport proves
only its fixture; controller-triggered replies cannot satisfy unattended acceptance.

## Scope and Non-goals

Scope: native after/at deadline creation and native deadline-dependent evaluation,
including file TTL, retry, expiry, inspection, recovery and compatibility proof.
Non-goals: P63 mailbox obligations, new trigger classes, native Codex changes,
shared-daemon patches, new time providers, NTS, host reboot/suspend, unrelated
worker rollout, or deletion/replay of retained uncertain state.

## Execution Contract — No Implementation Theater

One owner; one substantive ticket in progress. Execute0134 →0135 →0136.
Each ticket delivers externally observable behavior and records evidence before
its dependent starts. Red-green tests where behavior changes; no tests that merely
mirror helpers. Freeze source/config identities for acceptance and retain failed
samples. One Standards/Spec review and one bounded remediation pass; unresolved
blocking findings stop the affected ticket rather than start endless review loops.
Planning, test count and queue acceptance cannot substitute for runtime completion.
An implementation run must establish its own explicit checkpoint budget; this
planning approval does not restart the completed Plan0127 goal or its counters.
Source qualification, integration, release and installed activation are separate
gates. Do not upgrade unrelated services or replace live imported package files.

## Tickets and Blocking Edges

1. [0134 — Native network-time arming](0134-2026-10-10-native-network-time-arming.md): no ticket blockers.
2. [0135 — Safe deadline evaluation and recovery](0135-2026-10-10-native-network-time-recovery.md): blocked by0134 acceptance.
3. [0136 — Installed unattended acceptance](0136-2026-10-10-native-network-time-installed-acceptance.md): blocked by0135 acceptance.

## Acceptance Criteria and Definition of Done

Every child criterion has source-bound evidence; full relevant regressions and
required hosted gates pass. Installed exact-thread delivery completes unattended;
outage holds, original deadlines, cancellation, restart, expiry and rollback are
proved. Reader compatibility is explicit, failed samples retained, disposable
clients stopped and histories preserved. Release/installed identities and roadmap
readback agree before closing this plan. Unrelated P63 status remains OPEN.
