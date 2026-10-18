# Codex Wake 0.17.1

Make same-conversation self-refresh operational with explicit shared MCP scope.
A durable public MCP request waits for all loaded conversations to be observed
idle. Its independent monitor reloads shared MCP connections once and verifies
native goals/counters and selected real skill/MCP behavior. Existing TUI clients
are preserved. Lost reload responses reconcile without blindly repeating effects.

- Private host profiles own caller, workspace, endpoint, scope approval and proofs.
- Separate lifecycle journals preserve other wake-tool roots; a separate refresh
  monitor preserves resource-enforcer polling.
- Missing setup returns a structured refusal. Queued is not completed. Fixed
  expiry never renews a goal's allocation or resets counters.
- Native Codex0.163 has no thread-only reload or atomic idle CAS. Shared scope
  reconnects every loaded conversation's MCP servers; racing starts after the
  last idle observation remain possible. Legacy guarded client refresh remains.

Native two-conversation public acceptance preserves IDs/goals/counters with zero
model turns. The first fixture failure and unexpected HTTP401 provider warmup
attempt are retained; the passing fixture uses a loopback-only provider.
