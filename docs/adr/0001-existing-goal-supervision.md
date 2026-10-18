# Supervise an existing goal without adopting its shared executor

The operator wants to enter resource-limited /goal work in an existing dev tab,
with the agent registering limits through Codex Wake MCP. The accepted stopping
boundary is a checkpoint request followed by native goal pause and an exact-turn
interrupt if needed; shared Codex servers and unrelated work must be preserved.
This goal-supervision workflow is separate from dedicated OS containment: failed
native control is reported as unverified termination, never represented as a hard
process-stop guarantee. Checkpoint preparation consumes the original allowance
and cannot delay its stopping condition. The default checkpoint threshold is 5% of token allowance remaining or 60
seconds remaining, whichever condition first holds, with explicit overrides
displayed at enrollment. Accounting begins at the original goal start and
includes cached input and attributable delegated usage exactly once. Unknown
accounting holds continuation. Registration and resumption cannot renew limits;
only explicit user renewal increases authority. Limits remain in force across replacement goals in the same native session.
Only an explicit user reset can reset counters or allocation. This grants pause
authority for the current goal in that exact session, including a replacement;
other threads remain outside that authority. Plan0167 tracks implementation.
