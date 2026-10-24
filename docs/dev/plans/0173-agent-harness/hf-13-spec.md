# HF-13 specification: Wake ownership, lifetime and recipient-startup policy

State: APPROVED_SPEC
Owner: ecochran76
Decision authority: HF-01 and first-frontier interview records, including direct
2026-10-24 follow-up. Source baseline: origin/main f96f4c8; planning branch
4dfdc39. This spec describes proposed behavior, not implemented capability.
Public caller seams and the three-ticket breakdown were approved by the operator.

## Problem Statement

Wake requests already persist, but operators cannot explicitly select which
owner lifetimes they survive or what recipient startup is allowed. Those are
independent questions: a persistent record is not proof that a monitor runs after
reboot or that its saved conversation can be resumed.

## Solution

Extend durable wake intent with explicit owner/lifetime and recipient-startup
policy. Resolve defaults at registration, preserve them across recovery, and
explain whether requested execution is supported. Retire future owner-bound
delivery on verified completion by default without destroying evidence.

## User Stories

1. As an operator, I want to declare a wake conversation-owned, task-owned or independently persistent, so that I can recover scheduled intent without changing its delivery authority.
2. As an operator, I want to retain durable intent and its original due time through controller restarts, so that I can recover scheduled intent without changing its delivery authority.
3. As an operator, I want to choose owner-completion behavior per wake, so that I can recover scheduled intent without changing its delivery authority.
4. As an operator, I want to default pending owner-bound wakes to retirement on verified explicit completion, so that I can recover scheduled intent without changing its delivery authority.
5. As an operator, I want to keep a closed tab or missing process from being mistaken for completed work, so that I can recover scheduled intent without changing its delivery authority.
6. As an operator, I want to choose active-tab, background-saved-session or create/load/run recipient behavior, so that I can recover scheduled intent without changing its delivery authority.
7. As an operator, I want to default new wakes to configurable create/load/run behavior, so that I can recover scheduled intent without changing its delivery authority.
8. As an operator, I want to keep old wakes unchanged when new defaults are installed, so that I can recover scheduled intent without changing its delivery authority.
9. As an operator, I want to inspect unsupported recipient-startup operations before any hidden fallback, so that I can recover scheduled intent without changing its delivery authority.
10. As an operator, I want to preserve uncertain delivery attempts even when future delivery is retired, so that I can recover scheduled intent without changing its delivery authority.
11. As an operator, I want to keep daily occurrences and their original due times separate from delivery retries, so that I can recover scheduled intent without changing its delivery authority.
12. As an operator, I want to see persistence, monitor readiness and successful delivery as separate outcomes, so that I can recover scheduled intent without changing its delivery authority.

## Implementation Decisions

- Keep one authoritative wake/intention store. Extend the current versioned
  record/registration contract and its classifier; no parallel policy sidecar
  whose loss could silently widen delivery is permitted.
- Owner is an exact conversation reference, a stable task reference or independent
  persistence. Task references are opaque at this boundary; HF-13 can validate
  trusted owner events without requiring the full task-brief/workflow subsystem.
- Owner-completion action is configurable: retire, hold for review or retain
  eligibility until original expiry/cancellation. Default owner-bound action is
  retire. Persistent independent wakes have no owner-completion trigger.
- A terminal-owner event must identify its exact owner and authorized issuer.
  Deduplicate its application and preserve provenance. A missing tab, process,
  source or monitor never synthesizes completion. No age-based guess retires work.
- Startup policy is independent: require active tab; allow verified saved-session
  background delivery; or allow create/load/run. Freeze resolved selection and
  configuration revision with each newly registered intent. Later configuration
  changes cannot rewrite that intent. A wake's task/recipient policy separately
  distinguishes same-conversation resume from permission for fresh task launch.
- Default startup for new registrations is create/load/run, configurable by the
  operator. Existing persisted records retain their original delivery semantics;
  absence of the new field in an old record is legacy, not the new launch default.
- A new supported record version must cover validation, classification, workers,
  diagnostics and compatibility tests together. Unknown/unsupported versions hold
  without rewriting old records. Active incompatible readers produce an actionable
  retained-intent/worker-upgrade result, not a false delivery-ready receipt.
- Preserve original scheduling origin, relative-clock anchor, due time, expiry,
  prompt hash, attempt identity and uncertainty. Configuration/owner policy is part
  of intent identity: reuse returns the original intent or refuses conflicting
  explicit options; retries never re-resolve defaults into different authority.
- Owner retirement and delivery admission share the existing lifecycle lock.
  Once retirement is committed, new submissions are fenced. An already submitted
  effect cannot be withdrawn; uncertain effects remain reconcilable with no replay.
- HF-13 persists policy and enforces eligibility, cancellation/hold and capability
  admission at the current dispatcher boundary. Existing qualified execution can
  be reused; unsupported create/load/run does not silently downgrade to another
  mode. Actual new lifecycle execution belongs to HF-18/19/20 and need not be
  implemented to truthfully ship policy declaration and unsupported diagnostics.
- Existing trigger classes retain their meaning. Recurrence owner, timezone/DST,
  missed-run catch-up and overlap remain HF-20 decisions. Missed occurrences retain
  original due time; this ticket does not authorize catch-up or reset deadlines.

## Testing Decisions

Test public wake registration, reconstruction and dispatcher admission through
injected clocks, owner-event authority and runtime adapters. Use disposable roots;
cover each lifetime and completion action, untrusted/wrong-owner event, duplicate
completion, owner-end versus dispatch race, uncertainty versus retirement,
configuration change after registration, idempotent registration, old records,
unknown versions, incompatible worker, process/boot epoch discontinuity and all
three startup modes with supported/unsupported adapter responses. Observe exact
attempt count, retained origin/expiry and zero unintended submission. Existing
native-intent timing, cancellation and runtime-dispatch tests are prior art.
A simulated restart is source proof; actual reboot/installed monitor acceptance
is separate and must not be claimed from fixture tests.

## Out of Scope

No new recurrence engine, live machine reboot, host service installation,
automatic account switching, full workspace restore or implementation of lifecycle
startup modes not already qualified. Policy support and execution support are
reported separately; create/load/run is the desired default, not a false promise.

## Further Notes

[Resolved interview](first-frontier-decisions.md) and [shared decisions](hf-01-decisions-and-handoffs.md) own product provenance. This document proposes the bounded build contract. The parent backlog owns wider sequencing. Public caller seams and ticket granularity were approved by the operator.

Canonical implementation work item: [#317](https://github.com/CochranResearchGroup/codex-wake/issues/317).
