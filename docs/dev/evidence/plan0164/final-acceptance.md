# Plan0164 released acceptance

PR272 merged at d3ea192eb9071be3c49f89bbb346cec7aecd3b83. Release v0.16.0
published and downloaded wheel/sdist byte-match exact local build. Active prefix:
/home/ecochran76/.local/share/codex-wake/releases/0.16.0-d3ea192. All101 Python
files match merged source. Five command links switched after original-target
checks; both installed skills match six source files, backups retained.

## Proof matrix

| Criterion | Evidence |
|---|---|
| CLI persistent pause/resume, bulk cancellation, scopes | Focused public CLI tests and scripts/wake_control_qualification.py |
| Race-safe cancellation / failclosed unknown inventory | EC-R1/EC-R2 red/green; independent closed-world review |
| Cross-process control, corrupt keys, old worker reporting | Real-process effect-lock test, duplicate-state red/green, observed incompatible worker held/exit5 regression |
| Six MCP controls, host root/action grants, registry race | CommandRunner fixtures plus actual installed25-tool stdio MCP qualification |
| Owned native interruption, unknown-effect reconciliation |15 provider fixture/integration tests; exact payload/message/turn evidence, no blind resend |
| Handoff resident owner and goal fencing | Real daemon-to-supervisor fixture tests: pause-only preserves active successor; explicit owner stop; unavailable/foreign owner stays pending |
| Full source regressions | Local1267 passed206.442s at5191cf3; final hosted1268 passed Python3.11/3.12 atbcecae7; all release/package/plugin/installed gates pass CI38803279350 |
| Exact merged installed surface |101 source byte matches, actual isolated daemon holds delivery, two fixture roots cancel/resume, six MCP calls and ungranted scope denial |
| Current worker deployment |13 registered roots,9 user-owned Wake reader processes from current prefix, all13 root capability observations support emergency protocol |
| Preservation and cleanup |4 other service PID/state snapshots unchanged; no operator emergency actions, no paid model turns, no owned fixture MCP processes remain |

## Fleet reconciliation

Initial registry listed6 roots covered by2 units. Fresh OS census also found7
older Wake workers whose roots were missing from that registry. All7 mapped to
exact baseline systemd units, with no firing wakes or lifecycle stop hazards.
Added disabled service-owned registry entries: inventory now covers13 existing
roots without creating duplicate supervisor monitoring. Upgraded those7 idle
workers;2 Odollo worker units pinned obsolete uv-tool executables and now point
to the existing stable codex-waked command. Flags/environment preserved; original
unit files, registry, command links and skills backed up. Total related units
restarted9, other4 service PID/state snapshots unchanged.

Fresh process census finds9 current-prefix Wake readers, no remaining old Wake
reader in the user-owned population examined. This is a current-user census,
not an all-user/OS-wide guarantee. Root status deliberately labels capability
observation rather than promising exclusive reader authority. No live pause,
cancel or interrupt was executed as an acceptance test.

## Limits

Old/incompatible future readers can ignore the protocol. All-roots covers an
explicit registry snapshot, including disabled entries, not future enrollments.
Native queued-only work holds; submitted legacy transports are unsupported for
owned-turn interruption. Handoff stop waits for the original resident owner.
Mailbox delivery is a distinct surface. MCP requires explicit host action/root
grants; existing MCP clients need ordinary refresh/reload to expose new tools.
Native interruption proof uses injected providers, not newly purchased live model
turns. The exact installed ordinary delivery gate was exercised through its real
one-shot daemon on isolated fixtures.

Initial installed harness failed on obsolete SDK attribute spelling; corrected
without product changes. First CI failed only obsolete19-tool smoke expectation;
updated25-tool check and new controls qualification now pass. Original failures
retained. One initial once-health fixture artifact removed after process-generation
and missing-root verification; qualified reruns isolate their complete state.
