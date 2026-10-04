# Exact-thread offline admission repair

Parent Plan0119, issue181; human owner ecochran76, primary executor.
Branch fix/p63-offline-admission. Review baseline
3bd007889bd1d61fe8b840a87bef4d8a5fc64ab1 (merged PR210).
Previous live failures remain in verification0115; M2's original loop is closed.

## Diagnosis and red/green evidence

Public seam: native messages CLI with real temporary mailbox and actor capability,
read-only runtime fixture with sender loaded and exact recipient stored/unloaded.
No internal resolver stub. Test reader exposes no resume/start/turn API.

Command before and after repair:
`PYTHONPATH=src python3 -m unittest discover -s tests -p test_offline_message_admission.py -v`.
Initial red: exit1, assertion CLIexit3 rather than0, exact error
`selection_error: session not found`, selector thread:recipient. Green: four tests,
CLI notify admission pending/unread; unenrolled recipient denied;
cross-root-disabled bus denied; mismatched returned exact ID denied. One guard
test initially expected cross_root_disabled; corrected the test to the existing
cross_root_denied public code without changing runtime policy.
Existing CLI regression suites: six a2a CLI and seven messages CLI tests passed.
Full source suite:908 tests passed in128.655s. Compileall and git diff --check
passed. These are source checks, not installed/live milestone acceptance.

Cause confirmed: loaded inventory selection preceded read-only exact identity
resolution. The resolver now permits only message send's exact thread selector
to read stored metadata without loaded discovery. Mailbox authorization remains
the admission authority; current process/composer checks remain delivery authority.
No transport/lifecycle calls, schema or persisted-state migration, runtime patch,
or relaxed notification eligibility.

## Standards

Serial primary review against policies0003/0004/0005/0006/0021 and the skill's
smell baseline. Exact diff: git diff3bd0078 (including pending working changes).
The optional resolver mode has an actual single caller and preserves enrollment
discovery. Tests exercise CLI behavior with runtime I/O replaced at its boundary.
Accepted blocking findings:0. No temporary production instrumentation.

## Spec

Plan0119 M2 requires pending delivery to an unloaded exact recipient and denial
until client eligibility. Source repair addresses failed admission without
resuming the recipient. Missing live cancellation/reconnect qualification is
needs_evidence, not satisfied by fixture tests. M3/M4 remain unproven and are
outside this independently mergeable repair. Accepted blocking source findings:0.
Live milestone acceptance is still pending.

## Remaining proof

Required hosted release gates and exact merged-main installation precede new
live tests. This changed-source packet permits one offline cancellation scenario
and one pending reconnect scenario, with120-second per-scenario bounds, no blind
effect retry, original A/B IDs preserved and only owned worker/client lifecycle.
Source tests cannot close Plan0119 or issue181.
