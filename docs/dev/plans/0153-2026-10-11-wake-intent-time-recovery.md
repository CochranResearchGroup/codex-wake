# Plan0153 — Retain wake intent during time outages

State: OPEN
Workflow: IN_PROGRESS
Owner: primary / ecochran76
Lane: P153
Branch: fix/issue243-intent-recovery
Target: origin/main
Work-Item: https://github.com/CochranResearchGroup/codex-wake/issues/243

## Goal control

Resolve #243 using Matt's setup, triage, diagnosis, seam design, TDD, review and
acceptance process. Operator limit: stop and checkpoint before 2,000,000 tokens
or six hours; backstop checkpoint at 1,900,000 tokens or 5h45m. Primary only.
Three attempts per behavior seam, two serial review/rework cycles. Checkpoint
at diagnosis, working recovery, installed acceptance and closeout; at most
30 minutes between durable checkpoints. No CI waiting (standing operator rule).

## Scope and authority

Setup GitHub tracker/triage/domain routing after the pending default-label
choice; review/reproduce #243; retain and deduplicate exact native scheduling
requests on acquisition failure, expose recovery and alerts, implement bounded
recovery and deadline-aware qualified timing without guest-wall substitution.
Preserve not-before, expiry/stop, exact-thread/root and uncertain-effect fences.

Owned worktree: /home/ecochran76/workspace.local/codex-wake-issue243.
Root checkout's existing StableTime rollout and dirty docs are preserved.
Read-only dependency overlay copies time_inspection, stable_time and its tests
from root reproduced current installed behavior, then was removed after exact
hash verification. The feature builds without publishing that overlay. Plan0152
forbids commits/push for its separate rollout; activation must reconcile it.
No production scheduling, replay, clock setting, Windows authority restart,
unrelated services/sessions, new tenant or second mailbox/dispatcher.

## Acceptance

- Current installed unavailable-time / native after 3h failure reproduced.
- Durable original intent and inspectable pending-time receipt exist on failure;
  overlapping retries/restart/recovery yield one eligible successor.
- Authenticated interval bounds and supported relative-counter policy govern
  precision; absolute UTC deadlines and stop/expiry constraints remain strict.
- Prolonged outage, recovery, restart/suspend, malformed evidence, uncertainty
  boundary cases, cancellation and uncertainty-after-submission are covered.
- Installed executable proves monitoring-chain survival and no duplicate effect;
  source, integration, deployment and issue closure are separate receipts.
- Scope/memory/release/rollback recorded; user-approved setup role mapping applied
  without touching other issue state or changing existing provider labels.

## Current State

Installed 0.13.0-stable-time-01 reproduction confirmed: exit2, zero records,
injected unavailable acquisition at actual CLI entrypoint in private root. Fifteen
installed baseline tests PASS. Standalone repair retains schema6 intent, supports
authenticated elapsed fallback, preserves stop/expiry, unknown-origin/continuity
holds and uncertain effects, and advertises recovery alerts. 1061 comprehensive
tests passed with declared dependencies; 117 subsequent focused checks passed.
Installed private 0.13.1 CLI/worker, concurrent creators, four fresh workers,
live schema6 capability and exactlyone fixture successor passed. No model turn
or production wake is claimed. Final reviewed-source rebuild/rollback remains.
Current incident uncertainty magnitude remains unknown.
Setup draft at ~/.local/state/codex-wake/triage-243/setup-draft.md, default labels
await user preference. Integration and activation remain separate gates; global
activation cannot silently remove the current uncommitted StableTime adapter.

## Seams

Actual native CLI and record inventory; poll_once/time acquisition; native queue
submission and reconciliation; installed package and worker fixture. Tests use
public receipts and independently fixed deadlines, not private storage assertions.
