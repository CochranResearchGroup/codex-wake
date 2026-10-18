# Native goal supervision facts | Codex 0.163.0

Read-only packet from /root/native_containment_probe, accepted as source-backed
design evidence, not descendant runtime acceptance. No provider calls or native
control effects in this packet.

- thread/goal/set accepts threadId and optional objective/origin/status/tokenBudget;
  no expected goal identity, createdAt, revision or CAS. Read-before/read-after
  cannot atomically protect a replacement goal.
- turn/steer requires expectedTurnId; turn/interrupt requires turnId. Queue add
  requires clientUserMessageId. Identities enable reconciliation, not a proven
  exactly-once replay guarantee.
- Native goal counters charge input minus cached input plus output, including
  separate descendant accounting. They cannot enforce cached-inclusive totals.
- Forked child cumulative counters inherit parent history. Summing cumulative
  per-thread maxima double counts. Prefer token_usage_record noncumulative
  usage.total_tokens, with identical (thread_id,response_id) deduplication;
  cached input is already included, never add it again. Conflicts hold.
- Require qualified original-goal boundary, response/turn ownership, complete
  recursive descendant coverage, and resolved history_base/fork prefix metadata.
  Missing history, concurrent boundary work or unfinished publication is unknown.
- Existing owned fixtures contain no descendants; delegated aggregation is not
  yet live-qualified. Their verified cached-inclusive goal delta is 90477 from
  settled cumulative baseline 55175.

Version-matched upstream sources:
- https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/core/src/session/mod.rs#L1729
- https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/core/src/session/mod.rs#L5011
- https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/core/src/state/session.rs#L219
- https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/protocol/src/protocol.rs#L3225
- https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/ext/goal/src/accounting.rs#L570

Generated installed schemas: /tmp/cw-native-schema-0163/v2/ (ephemeral;
regenerate with installed codex app-server schema generation for reproduction).
