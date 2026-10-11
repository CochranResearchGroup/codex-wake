# Plan0153 — Retain wake intent during time outages

State: CLOSED
Workflow: DONE
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

DONE. PR244 integrated241d7a4; v0.13.1 published/downloaded/activated at exact
release prefix. Matt setup/default labels applied. Four current StableTime adapter
files preserved in public source; contract2.0 finite bounds supported.1072 full
source tests OK/two skips,45 affected checks PASS, two optional MCP tests and
installed MCP smoke PASS. Published prefix eight-worker qualification proves one
monitor successor, no crash replay, no unknown-origin expiry extension and old
reader rollback. Seven daemon roots advertise schemas1–6; supervisor new-prefix
active; independent webhook unchanged; all70 existing records accounted for.
Root/main dirty alternative preserved separately, no production incident replay,
new wake or completed model turn claimed. See final-acceptance.md and activation
receipts for exact scope/limits. Companion StableTime availability not resolved.

## Seams

Actual native CLI and record inventory; poll_once/time acquisition; native queue
submission and reconciliation; installed package and worker fixture. Tests use
public receipts and independently fixed deadlines, not private storage assertions.

## Completion audit correction

Second bounded review/remediation cycle: unknown initial origins must not be
rebased when time recovers, because doing so extends an original expiry that
cannot be established. The retained request instead holds with an actionable
relative_origin_unanchored alert. Existing anchored counter/UTC recovery remains
automatic. Acceptance of the earlier first-qualified-origin behavior is revoked;
its public CLI/poll regression failed before the correction. Refreshed installed and optional-composite receipts pass; full source results
are recorded in acceptance.md before the corrected source checkpoint publication.

## Approved integration packet

Operator approved Matt/default-label setup and retained adapter publication.
Six docs/agents files and default labels applied. AGENTS pilot inventory hash
refreshed. Current adapter includes contract2.0 finite authenticated wide bounds;
native clock consumer updated against ../wsl-time/src/client.rs contract.
Root competing pending_time candidate remains preserved separately: its later
relative-origin behavior conflicts with F4 and its schema6 representation differs.
Only the four current adapter source/test files are admitted to PR244; root patch
and untracked files retained privately in triage-243/root-reconciliation.
Source/installed verification must refresh for this exact combined packet before
main integration, published release and activation. Preserve all other sessions.

## Terminal disposition

All accepted work complete. Later historical pending-decision text records earlier
checkpoints and is superseded by final-acceptance.md. Public source and installed
identity verified; root dirty work preserved. Worktree closes after exact remote
custody and documentation integration. No further implementation packet required.
