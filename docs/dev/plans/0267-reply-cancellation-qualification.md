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
  The original bounce stays in history. For a bounced timed wake or a timed
  occurrence of a recurring schedule, use `native redirect WAKE_ID --to UUID
  --idempotency-key KEY` with the receiving harness and endpoint options.
  If the permission store is active, use a verified operator capability. The
  existing registration path applies current permissions and recipient policy.
  A durable timed bounce is required, and a new redirect must fit the original
  absolute deadline. Replaying an admitted key returns its existing receipt.
  A recurring schedule's ID itself is outside the redirect surface.
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
The timed path also checks durable DND bounce in the local journal and
PostgreSQL, linked ID and exact original expiry, old-record preservation,
idempotent readback after expiry, and refusal of a new expired redirect.
The bounded cancellation regression crosses the wake cancellation CLI using the
real adapter and synthetic exact transport protocol evidence, including a lost
delete response. Existing reply-wake tests exercise the independently delegated
sender arm and owning-client worker.

A separate actual native qualification ran the public scheduling and cancel
CLI and the native MCP `wake_cancel` command runner under UID1017. The runner
used an exact host grant and invoked the real cancel CLI against the private
app-server. The Wake package came from `08bb54f9cc10cb283d6a96b6441dff4986dc2cfe`,
wheel SHA-256 `8ce1302ac5d9c195ca1bff877eda5c85a7062cc4308de2243b6fd1a785de32ed`.
The daemon used the #695 GNU package built from
`9af0e8e48d0c2dcfe1800a3deaadfcec7e2c0bd7`, executable SHA-256
`6bc59c44a04dcf1c1a36f9754397b26994ccf6a3a932c7e872560a8016bac978`.
A private StableTime configuration qualified the backend. The CLI and MCP
runner each matched the original accepted queue ID to a real canceled
tombstone. A queued input that had already started returned the exact native
turn ID. Two loopback model requests ran, and the owned daemon stopped
successfully. The receipt is `/tmp/cw769mcp.53XzDzmJ/receipt.json`, SHA-256
`821e58b1eded0ad8685b53c37f340b9dbb6476ac8936b6198b1a6072618f0a88`.
No production provider or external ChatGPT OAuth connector was used.

The focused local suite passed 135 tests with the disposable PostgreSQL
scope. Log: `/tmp/issue769-pg.0fkj5yvQ/final-focused.log`.
