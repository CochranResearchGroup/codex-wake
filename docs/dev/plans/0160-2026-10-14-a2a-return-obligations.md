# Plan0160 — Explicit A2A return and wait obligations

State: CLOSED
Workflow: DONE
Owner: primary / ecochran76
Branch: docs/a2a-return-obligations
Target: origin/main
Work-Item: https://github.com/CochranResearchGroup/codex-wake/issues/258

## Current State

Local standard and both installed agent skill copies updated and verified.
Review: docs/dev/evidence/plan0160/review.md. Local documentation outcome complete;
Git integration remains unpublished. Active lifecycle checkout preserved.

## Scope

One serial documentation packet following Plan0154: mandatory request/reply
checklist, explicit wait ownership, bounded foreground/inbox/TUI alternatives,
checkpoint and timeout obligations, installed skill parity and scenario review.
Primary owns changes; no parallel agent work needed for this coupled contract.

## Non-goals

No runtime/schema changes, live messages, incident replay, service changes,
release or automatic enforcement. No changes to lifecycle implementation.
Initial local packet excluded publication. Operator subsequently authorized
PR, merge and deployment; issue258 owns this delivery continuation.

## Acceptance criteria

- Recipient transmits a correlated answer and inspects admission before local
  closeout; processing completion does not prove answer delivery.
- Requester selects an owned bounded return path, verifies its arm before
  yielding and inspects the actual result before dependent continuation.
- Pending exchanges have exact IDs, deadline, next action and owner; timeout
  produces explicit pending/blocker state rather than success or blind retry.
- Inbox/TUI exceptions are explicit and supervised; terminal results do not loop.
- Bundled and both installed skills match; reported incident remains attributed
  and is not represented as reproduced or diagnosed runtime failure.

## Definition of done

Local source and installed instructions aligned; routing scenarios reviewed,
links, policy wiring and whitespace checked; durable outcome and limits recorded.
Publication/integration is a separate Git custody boundary.

## Validation and bounds

Documentation only: primary scenario review, changed-link check, policy wiring,
whitespace and four-file installed parity. No runtime tests for prose; no live
compliance claim. No new transport or expiry-extension authority.
