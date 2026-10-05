# Requested remaining gates and native thirty-minute soak acceptance

Result: requested remaining-gate packet PASS. This audits the active goal's live
cancellation, clean reconnect automatic return, full normal owned-worker restart,
ordinary released installation, multiroot/rollback and thirty-minute soak.
The user's Plan191 reference was mapped to existing Plan0119; no Plan191 exists.
Plan0101/issue181 and broader deferred recovery obligations remain OPEN.

## Requirement audit

| Requirement | Actual proof | Result |
| --- | --- | --- |
| Live cancellation | Verification0117; actual cancelled/suppressed request, zero attempts before and after recipient eligibility;19.222847-second bound | PASS |
| Automatic return after reconnect | Verification0117; original B reconnect, one request and one correlated return submission, actual automatic A read;118.184840-second monotonic upper bound | PASS |
| Full normal owned-worker restart recovery | Verification0118; original clients terminal through restart, pending request and identical durable arm retained across worker8331 exit/new worker14751; same original thread reconnects; actual automatic A read in109.313353seconds | PASS |
| Normal released installation | Verifications0120/0121; ordinary public-tag uv tool install at stable user CLI; native installed v0.7.1 service round trip in77.851579seconds | PASS |
| Multiroot and unenrolled denial | Verification0121; actual root2 actor/thread, native denial with zero admission before enrollment, then cross-root exchange in71.081458seconds | PASS |
| Actual installed rollback | Verification0120; ordinary isolated public v0.7.0 -> v0.6.0 -> v0.7.0, mailbox bytes preserved, old command refusal, actual A compatible read returns same message/receipt | PASS |
| Thirty-minute owned workload | Same released native worker46789, four automatic pairs, full monotonic duration and resources reconciled below | PASS |

The rollback's exact tested versions remain0.7.0/0.6.0/0.7.0. Source comparison
v0.7.0..v0.7.1 under src changes only __version__; mailbox behavior is identical.
The old released refusal is absent command surface, separately from existing
schema1-reader/schema2 refusal qualification. No unsupported downgrade is claimed.
Restart proof is the requested normal process lifecycle; forced ambiguous crash
replay and wider held-recovery work are not qualified by this packet.

## Actual released native soak

Unit codex-wake-plan119-v071-soak-successor.service used the shipped user-systemd
example and ordinary global installed v0.7.1 CLI, duration1800, interval1,
max_dispatches20, Restart=no. Frozen limits: at most ten pairs (four planned),
store<=10485760bytes, stable FD growth<=2, RSS growth<=67108864bytes,
residual owned children0. Baseline was captured after actual managed-reader
initialization, before admission. Original A/B identities and issued capabilities
were preserved. No controller prompt/body relay after each request admission.

Worker PID46789/start ticks4708771, invocation
2cd8c51d712a403c8601c84ee613a4b7. Captured manager process start monotonic
47087768548us; matching native finished journal timestamp48888091508us:
1800.32296seconds. Native finished below its effect budget with eight submissions
and1452 ticks, so its own monotonic duration deadline ended the run. No restart
or observer-triggered stop occurred. Fresh manager: inactive/MainPID0/status0,
Resultsuccess; original process absent.

| Pair | Request | Correlated reply | Actual send-to-read seconds |
| --- | --- | --- | --- |
| 1 | msg_6e192a1e724e4501bb372b2999f84aa1 | msg_ea25cf01595f46729354824176ba936e |88.381574515 |
| 2 | msg_308d1cd2069a4c378bc8c91e1b3837a7 | msg_4108a4c8d1674f6d912e82f2a378182b |92.010906665 |
| 3 | msg_a97f695706b8472aa8af4e1ee304bdee | msg_d6809a76c6c6473f984d8f0d500c22ec |96.735517974 |
| 4 | msg_ae5d504770ca4edb9628825093da0044 | msg_060bde908c48474c8712da60a13bf35e |92.088026441 |

Each pair: actual B received/claimed/replied/completed; actual automatic A read
verified in_reply_to and body challenge. Exactly one submitted attempt per
request/reply, eight unique messages, one worker owner and process generation, no unfinished
dispatching/uncertain attempts. Eight exact notification turns were separately
read and verified completed. Truncated multi-turn summaries were not used as
complete-turn proof. All first reads succeeded; the bounded clock-error read
retry policy was present but not exercised. Worker clock holds occurred without
weakening the clock guard or authorizing duplicate transport.

Baseline RSS29122560bytes; peak33382400; final stable32714752. Maximum RSS
growth4259840bytes, final growth3592192. Stable FD count4 throughout, growth0;
transient peak9 is separately recorded. Peak store783105bytes. No residual
owned children/cgroup PIDs; all five named demo units have MainPID0. These bounds
qualify this owned workload, not production scale or indefinite leak freedom.

## Failure preservation and evidence reconciliation

The earlier soak remains FAIL at786.195835seconds after native recipient
clock_anomaly and incorrect observer lifecycle handling; verification0121 retains
it. Its request was later marked expired by explicit native operator inspection,
without a read/claim/reply or notification replay. That preparation does not
convert the old failure into automatic-delivery acceptance.

In the successor, pre-admission setup initially queried a duplicated fixture unit
name. Corrected on the same worker before any A admission; original script and
failure retained. At pair3 the observer encountered an incomplete JSON write and
exited. Native worker and actors continued; actual read completed within its
original bound. Observation resumed after exact reconciliation with incomplete
JSON treated as observation-only until the existing bound; only pair4's original
planned setup followed. No message/effect retry or worker restart.

The resource observer preserved a FAIL/unknown duration when systemd cleared
terminal timestamps. Independent captured start plus the exact PID/invocation
native finished journal and below-budget deadline termination establish duration.
The original summary is retained, not overwritten. Resource observations and
native actor/mailbox correctness are reconciled independently; observer failure
does not erase completed native samples or substitute for their missing evidence.

## Installed identity and final state

Ordinary stable CLI remains0.7.1, requested_revision v0.7.1, exact source
bec10055a171a6e3c4de51718a16b15387fe80b9. Stock Codex0.160.0 remains selected;
shared daemon and OpenClaw were not modified/restarted. Existing Wake supervisor
PID80755 remains active; the same four root identities are registered. A/B and
the additional root2 actor are idle/ready with original IDs. Original root's
unrelated untracked handoff note is preserved. Observer handles are terminal;
journal-only capture ended at its explicit1850-second timeout after native exit.

## Provenance and scope

Private evidence:
/home/ecochran76/.local/state/codex-wake/live-demos/20261004-wakeA-wakeB/tmux-plan119

continuation-v2/cancel-1/final-proof.json;
continuation-v2/reconnect-1/{mailbox-final-proof,deadline-proof,worker-terminal}.json;
continuation-v2/restart-2/final-proof.json and before/after arms/actual turns;
v070/rollback/final-proof.json and actual compatible actor read;
v070/v071-live/m1/final-proof.json;
v070/multiroot/{unenrolled-final-proof,m1-normal/final-proof}.json.

v070/soak-successor/final-proof.json binds native/mailbox/resource results;
final-runtime-and-actor-audit.json verifies current identity, roots and exact
notification turns. A/B-actual-notification-turns.json retain full bounded turns;
pair-XX/m1 holds native outputs/clocks; resource-before/final.json,
resource-observations.jsonl, worker-journal.jsonl, frozen-thresholds.json,
spaced-setup-failure.json and resumed observer receipts retain all observations.
Credentials and peer bodies remain private. No memory write is attempted without
a reviewed Codex Wake Graphiti target group.

This completes the explicit remaining-gate objective. It does not close issue181
or the wider Plan0101 program: damaged-source hold release, broader ancestry/fault
matrices, cross-generation recovery and server-unloaded-recipient qualification
retain their existing scope/status. No new live recovery authority is inferred.
