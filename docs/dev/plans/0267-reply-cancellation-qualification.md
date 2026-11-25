# Plan0267 reply and cancellation lifecycle

Issue [#769](https://github.com/CochranResearchGroup/codex-wake/issues/769)
covers correlated reply retrieval, an optional reply wake, verified
cancellation and redirecting a bounce.

## Public operations

- Retrieve the original sender's retained replies with
  `codex-wake messages replies MESSAGE_ID --json` or native MCP
  `wake_messages_replies`. Read an exact reply with `messages read REPLY_ID`.
  The reply stays in the sender's inbox under its own ID, with `in_reply_to`
  carrying the original ID. The shared store retains that relation.
- To ask Wake to notify the exact sending conversation on reply, register
  `messages arm-reply MESSAGE_ID --idempotency-key KEY --expires-at UTC` using
  the existing operator-delegated sender authority, Wake root and bound worker.
  The arm observes a qualifying correlated reply, then reuses the selected
  owning-client notification path. An inbox-only reply remains retrievable.
- To redirect an existing bounce, use `messages redirect MESSAGE_ID --to
  thread:UUID --idempotency-key KEY`. It requires the original sender and a
  distinct, currently authorized recipient. It creates a new ID with
  `redirected_from`, retains the original absolute expiry and requested busy
  policy, and applies current authorization and DND to the new recipient.
  The original bounce stays in history. Timed wake and schedule IDs return
  `redirect_source_unavailable` on this mailbox command.
- `messages cancel` retires a mailbox message before an effect is admitted.
  Once notification is in flight or its outcome is uncertain, the mailbox
  retains the original evidence. `codex-wake cancel WAKE_ID --json` reports
  `cancelled` before admission, verified `native_queue_removed` with the exact queue ID,
  `native_queue_expired`, or `native_turn_started` with the verified turn ID.
  A requested cancellation never interrupts a turn. A backend with only
  unqualified or opaque queue evidence remains held.

When a shared store is configured, apply its additive schema upgrade with
`messages database-init` for the selected scope. A qualified queue tombstone
retires the existing shared dispatch window in the same database transaction
that records the terminal evidence on the original attempt.

## Validation boundary

The disposable PostgreSQL regression crosses public CLI parsing, verified
mailbox participant authority, scheduler bounce, durable correlation and shared
admission readback. A fixture transport produces the tagged busy observation.
The bounded cancellation regression crosses the wake cancellation CLI using the
real adapter and synthetic exact transport protocol evidence, including a lost
delete response. Its typed evidence distinguishes a verified deletion from
a started turn. Existing reply-wake tests exercise the independently delegated
sender arm and owning-client worker. No production provider or external
ChatGPT OAuth connector was used for this qualification.
