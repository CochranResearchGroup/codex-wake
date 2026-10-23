# MR-06 installed Codex/Grok qualification

Work item CW-MR-172/MR-06. Primary owns the only ready ticket; no independent
nonblocked ticket exists to delegate. State: DONE for installed candidate acceptance. [Machine receipt](../evidence/plan0172/mr06-interop-qualification.json).

## Accepted live sample

Sample8 passed in33.623s with four original synthetic prompt attempts, below the
per-run six-prompt/300-second limit. Real Codex0.164.0 and Grok1.0.40
(eb1a2256660d stable, minimal UI, Grok4.7) each showed two completion responses.
Three durable intents each submitted once; one mailbox notification submitted
once. Codex sent a request to Grok; Grok authenticated, read, newly claimed and
replied, then sent a reverse request. Codex authenticated, read, newly claimed
and replied. Grok observed the correlated reverse reply. Both helpers observed
the actual inherited session IDs; no session context was inserted by the harness.

Grok uses native_preferred with an explicitly approved terminal-observation
fallback after definite pre-I/O native-unavailable evidence. Its terminal marker
is delivery evidence, not a work acknowledgment. The subsequent independent
mailbox capabilities, managed generation/ancestry/root checks and claimed=true
receipts authorize the work. Native Grok caller attestation remains NOT_QUALIFIED.
Codex uses the private native app-server and the thread created by its real TUI.

The final OS census found zero introduced residuals, zero unattributed new runtime
processes and no changed pre-existing Codex/Grok/tmux generations. No existing PID
was targeted. This is a bounded census, not indefinite global process-health proof.

Candidate: unreleased0.19.1, rebuilt wheel SHA256
`5e0f2125313d6a086ebc584a68f9344ec64e5f5c7f54182411f8e288e7025c43`.
All121 installed modules matched that wheel before launch. The exact launcher
snapshot/hash and module inventory were retained before effects. The source ref
in the run records identifies a dirty checkpoint; the wheel and launcher hashes
bind its exact bytes, subsequently committed as759d700 for review. The previous wheel
`c5078cd1d94286bbd84c71f112a62514501d6de63481ec9f20c864ec8d6aab34`
and its prior1451-test result are historical evidence, not qualification of the
new adapter. The temporary candidate prefix was reinstalled; production was not.

## Diagnosis and retained failures

The user explicitly approved interop reruns to solve the bug and close the ticket
on2026-10-23. Each test uses new private sessions, bus, grants, nonce and intents;
no uncertain original work is replayed. Runs stop on refusal or uncertainty.

| Sample | Result | Prompt attempts | Disposition |
| --- | --- | --- | --- |
| 1 | FAIL6.338s, Codex pane disappeared | 0 | Original startup error unavailable; initial cleanup failure retained; later residual gone |
| 2 | FAIL6.424s, explicit remote-resume permission refusal | 0 | Retained error; clean runtime census |
| 3 | FAIL29.984s, legacy mailbox clock anomaly | 4 | Guest clock regression measured independently; failed bus preserved |
| 4 | INCOMPLETE83.674s, operator stopped | 4 | Claims/replies passed; helper omitted printed claimed=true, so Codex correctly refused final completion |
| 5 | INCOMPLETE72.431s, operator stopped | 4 | Actual helpers/visible responses passed; harness parsed dispatch envelope at wrong depth |
| 6 | FAIL20.289s, terminal acceptance unconfirmed | 3 | Original notification uncertain; no replay, clean census |
| 7 | FAIL20.088s, terminal acceptance unconfirmed | 3 | Same failure retained; no replay, clean census |
| 8 | PASS33.623s | 4 | Corrected adapter/wheel; full bidirectional/visible evidence; clean census |

Sample1 remains historical FAIL/cleanup_incomplete. Its initial introduced
PID1373703 was later already gone; no remedial signal was sent. A subsequent
census found pre-existing PID1367443 absent, cause unattributed. Missing original
Codex captures/empty native log cannot prove its exit cause or native turn count.
The original launcher was not snapshotted; later corrected source is not its hash.

The exact current startup reproducer used a private app-server, a new empty thread
and `codex resume --remote ENDPOINT -a never -s danger-full-access THREAD`.
`startup_probe.py both` reproduced the permission error in2.808s, zero prompts.
Either permission flag alone reproduced it. Removing both exposed an independent
empty-thread/no-rollout resume error. Starting a fresh TUI against the private
server succeeded. The launcher now configures permissions on that server and
binds the unique thread created by the TUI. Codex auto-updated from0.163.0 to
0.164.0 between samples1/2; sample1's exact historical cause remains unproven.

A six-second independent guest-clock sampler detected wall regression >1s and
11.434275s wall/monotonic offset variation. No host-clock configuration or clock
guard changed. Fresh acceptance buses explicitly opt into the existing
network-first plain-NTP policy; this is not authenticated UTC. Old anomalous
checkpoints are preserved, never reset or migrated to mask the failure.

The helper now prints the actual verified claim result. Its provider-free test
failed with None instead of True, then passed after the fix. The notification
parser now consumes the real CLI `dispatch.results` envelope; its fixture failed
before the fix and passed after it. Each dispatch response gets its own artifact.

Samples6/7 isolated asynchronous terminal painting: Enter completed before the
first capture showed the exact marker; later retained frames contained it. A
single-call adapter fixture with one stale post-paste frame reproduced uncertain
instead of accepted. The repaired adapter observes only the original marker for
at most one second within the original deadline. There is exactly one paste;
missing evidence or changed generation/session remains uncertain. Rebuilt sample8
reran the original visible interop scenario successfully. Failed samples are not
reclassified as clean; terminal delivery can still be uncertain and forbids replay.

## Checks and independent criteria

Focused source adapter/harness selection:13 PASS1.334s, no skip. This includes
real tmux startup retention, actual helper stdout, CLI receipt parsing and the
new delayed-paint regression. Installed candidate changed-axis61 PASS9.249s under isolated time/XDG config
and PYTHONPATH=.:tests. The initial selected-module command omitted the tests
import directory and produced three fixture-import errors; retained, then
corrected without changing tests. Full local suite1455 tests, zero failures/errors, one expected opt-in systemd
skip, PASS310.046s; frozen source/tests unchanged. No release/CI claim.
The first full command omitted the previously established stable-time/XDG
isolation, reproduced known native scheduling-time failures, and was aborted as
non-qualifying with output retained. The corrected full command uses empty
CODEX_WAKE_STABLE_TIME_CONFIG, private XDG_CONFIG_HOME/XDG_STATE_HOME,
PYTHONPATH=src:. and the frozen manifest runner.
Compile, F821/F822/F823 and whitespace checks pass. No debug log prefixes were
introduced. Temporary diagnostic source, red failures, probes, logs and raw TUI
captures are retained privately outside Git at
`~/.local/state/codex-wake/design/grok-multi-runtime-20261021/mr06/`.

| Criterion | Evidence and qualified boundary |
| --- | --- |
| AC1 | Sample8: installed durable exact Codex and Grok wakes, real visible completions, original typed records |
| AC2 | Sample8: both scoped directions, inherited identities, independent actor checks, claimed=true and correlated replies |
| AC3 | Prior installed policy controls: default wait; queue/interrupt explicitly unsupported and refused before effects |
| AC4 | Sample8 native_preferred/approved terminal fallback; prior binding/composer/profile controls; samples6/7 uncertain/no replay; delayed-paint red/green |
| AC5 | Existing isolated expiry/cancel/crash/restart/generation/uncertainty controls; originals retained; full1455-test compatibility rerun PASS |
| AC6 | Real0.164.0 Codex native wake and actor calls in sample8; full1455-test source compatibility suite PASS |
| AC7 | Versioned CLI/MCP capability controls and published support matrix; host delegation is explicit, native Grok attestation/resource guarantees unqualified |

These source/installed control proofs are distinct from the bounded real-TUI
positive path; not every fault was injected into a live provider conversation.
[Support and recovery](../multi-runtime-mailbox.md) states the qualified modes.
Main integration, CI matrix, release and production rollout remain separate.
