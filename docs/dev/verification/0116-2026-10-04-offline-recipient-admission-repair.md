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
smell baseline. Exact diff: `git diff 3bd0078` (including pending working changes).
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

## Integrated and installed proof

PR211 merged source db24f6ed098b09a4f515adc2d72913e6c6e46e59 as exact main
eb79e927fb227af3657d5b121aa17026294976d7. Hosted run37244618664 passed required
Python3.11/3.12 release gates. The private installed live command was rebuilt
from that exact main; installed a2a_cli/messages_cli bytes match source, recorded
in private offline-repair-installation.json. Stock Codex0.160.0 remains selected.
Previous docs-only checkpoint PR210 merged as3bd0078; its clean checkout was
removed after verifying its c7ed85d checkpoint retained on its remote branch.

First changed-source live qualification admitted request
msg_37d668f3cfda482a859ef305d80547b5 from actual A with B clientPID49283 terminal.
Native worker deferred with zero attempts. A's native cancellation failed with
clock_anomaly before effect, and A stopped without retry. Preserve that failed
cancellation verdict. WorkerPID10084 finished with0 submissions/89ticks; a
bounded expiry-only worker then observed accepted->expired/suppressed, still
zero attempts. Original B explicitly reconnected and rebound as PID40360/
start3640315, generation9ab4b9978e0642b5a4531bfc0005a60e. No request replay,
arm extension, or late dispatch. Private offline-repair-cancel artifacts retain
actual send/cancel outputs, observations, expiry proof and worker custody.

Loaded inventory still included B in the sampled disconnected state; this live
test proves disconnected-client admission and safe deferral, not server unload.
Cancellation remains UNPROVEN because of the real host clock-continuity failure.
The second changed-source live qualification is recorded below.

## Reconnect qualification outcome

Actual A admitted request msg_3c2460167e9443798c9b1502fbd9c8ca while B's
clientPID40360 was terminal. Pending-before-reconnect receipt shows no attempt;
A's actual reply arm wake_71e297b329f84cd1be06b712654bf46f was registered and
A was idle before reconnect. Controller explicitly resumed the ORIGINAL B
thread and refreshed binding to PID57334/start3653045/
generationecce6178191746768b17ab28e4a098cd. Product worker reloaded the binding
and submitted the original request exactly once, attempt_8817c90b0e4f45cfb61c14bf50cc62a8.
B read receipt_324a1682d9a24931a1fa12acceedbad2, claimed
receipt_65cede0c0f9041c49d1fb756b699cdb0 and sent one correlated notify reply
msg_3246ab5d81ec422fbc4512ea75221677, completing its request claim.

Return notification failed FIFO eligibility: old unread result
msg_8221be2f67804df69f524e536edf1a78 from the preserved M2 attempt2 has an
expired reply arm and remains ahead of the new result. Journal proves one request
attempt, zero return attempts, both results still unread before cleanup. The
worker did not bypass order or manufacture a receipt. Native bounded worker
finished0; actual A automatic read was not observed. This qualifies pending
disconnected-recipient admission and exact delivery after reconnect, not the
120-second automatic return exchange or M3 restart acceptance.

Private offline-repair-reconnect bootstrap, pending-before-reconnect,
B-rebind, native actor outputs, worker journals, worker-terminal and
final-before-cleanup receipts retain the distinction. After the attempt and
worker were terminal, an explicit manual A read of the two retained results was
requested to reconcile the demo backlog. This post-test controller prompt is
cleanup, never automatic-delivery acceptance. No new request, reply, deletion
or arm extension was authorized. Preserve manual outputs separately under
post-qualification-cleanup.

Both changed-source qualification slots are consumed. Do not run a third unchanged
trial. Next work must address host clock stability and prepare an explicitly
reconciled mailbox before another bounded acceptance packet. Keep FIFO, clock,
enrollment and exact-client checks intact. Plan0119 M2 remains PARTIAL; M3/M4 open.

## Final readback and custody

Manual A reads completed after the test: old-result read receipt
receipt_fa43b26cc842439e99ddbcb790cc7bcf and reconnect-result read receipt
receipt_217a51ac950a438ba126f06912f4806d. Both retained results now have recipient
received; notification remains deferred. These reads neither prove automatic
return notification nor erase its failed verdict. The expired cancellation
fixture remains expired/suppressed/unread with no delivery attempt.

Private offline-repair-final-state.json is a fresh OS/runtime readback:
zero matching native demo workers, actual A PID5322/start2076335/pane%71 and
B PID57334/start3653045/pane%72, both original thread IDs idle with ready empty
composers. Stock0.160.0 package remains selected. Original root's unrelated
untracked handoff note is preserved. Source repair is integrated; live evidence
checkpoint branch is docs/p63-offline-live-checkpoint. Issue181 remains OPEN.

Budget meter remains frozen at548526 with carried prior subtotal1544740;
additional continuation work is unmetered. This bounded packet stops with a
published checkpoint before further live work, preserving reserve below the
user's1800000 ceiling without claiming an exact cumulative total.

Memory disposition: unavailable, because no reviewed Codex Wake Graphiti target
group is established. Canonical source and live receipts are retained; no memory
write is attempted.
