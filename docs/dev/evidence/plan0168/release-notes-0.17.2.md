# Codex Wake0.17.2

Keep shared self-refresh intents pending after native observation timeouts.
A timed-out RPC no longer falsely expires an intent whose original fixed
deadline has not arrived. Goal, checkpoint and one-reload guards remain intact.
Historical terminal receipts remain terminal; this patch never revives or
requeues them, extends an expiry, or renews resource allocations.

Regression uses public CLI admission and an independent monitor: a native read
timeout before a2030 deadline must recover and complete once, preserving the
original expiry and goals. Genuine expiry and lost-response guards remain covered.
