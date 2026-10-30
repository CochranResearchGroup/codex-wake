# Controller #411 durable-flow qualification

Source `3d13a919339c267ee058280075d28ffadbd359d4` is qualified in an isolated installed
`0.22.0.dev2` package. The retained receipt is
[`flows411-installed.json`](../evidence/plan0190/flows411-installed.json).
All 123 installed controller tests passed; 12 focused condition tests and selected
Ruff undefined-name checks passed. Seven installed acceptance programs exercise
branch/wait and late answers, new/sequential/fork foreach, joins, safe retries,
cancellation/revocation, nested conditions, limits and process-loss recovery.
Hosted GitHub Actions was not run under the operator's local-CI policy. Validation
used Linux/WSL Python 3.12 and deterministic private Unix fixtures; it does not
substitute for a hosted platform matrix, actual provider work or production use.

The recovery fixture kills the real evaluating CLI process after the original
semantic child has a durable waiting handle. Each of local CLI, direct OAuth API,
OAuth MCP, remote CLI and native stdio MCP observes that same operation under the
same original service identity. Pending results stay uncertain; a later completed
result selects the pinned branch. Each run retains three calls and 32 estimated
tokens, with zero repeated native effects. A newer published flow version does
not migrate the active run. No allocation or governor is created or renewed.

Condition receipts now retain evaluation/path identity, arguments, nested frame
baselines, intermediate semantic delegation and final results within the existing
flow database. Recovery consumes retained results without re-admission or charge,
and waits on original operations without submitting a new prompt. A per-run OS
lock fences concurrent recovery while an evaluator is alive and releases on exit.
The original elapsed deadline remains in force; an expired pending condition
requests cancellation through its original owner and retains confirmed/uncertain
cleanup evidence. An uncertain native submission remains recoverable rather than
being flattened into a final predicate error.

Compatibility is additive. Older interrupted receipts without evaluation/path
identity remain explicitly uncertain as `legacy_condition_interrupted_no_replay`;
the controller does not invent missing continuation identity or reset accounting.
Explicit checkpoint migration is not advertised. The aggregate fork check is a
protocol fixture; actual packaged native common-prefix qualification remains the
separate pinned #408 correction receipt. Exact native semantic metering,
observation-only tool isolation and parallel predicates remain unqualified and
are refused before effects. Windows/remote-host acceptance and production
activation belong to their separate tickets. This implementation and acceptance
work consumes no final graph code-review/remediation round.
