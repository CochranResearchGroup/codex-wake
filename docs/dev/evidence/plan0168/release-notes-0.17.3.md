# Codex Wake0.17.3

Accept fractional checkpoint-token percentages through both MCP and CLI.
For example,17.5percent preserves a350k-token checkpoint reserve in a2M-token
allocation. Previously MCP rejected it as invalid_argument and CLI rejected it
as an integer parse error, despite the supervision backend supporting fractions.
Range, finite-value, host-grant and accounting checks remain unchanged.

Clarify that a new conversation UUID requires its own host grant; sharing a
tab or CWD does not inherit authority. This patch never auto-provisions a grant,
enrolls/resumes a blocked goal, migrates counters or renews an allocation.
