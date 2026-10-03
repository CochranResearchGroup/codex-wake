# Plan 0107 receipt restore verification

Parent: Plan 0101 / issue #181
Branch: feat/p63-receipt-restore
Baseline: 24ddf11224a06c2b11764b66b8031be6242364c6
Outcome: exact restore and guarded no-dispatch publication accepted.

Receipt arms carry a nonsecret exact bus/root/message/actor-generation descriptor.
Restore uses separately supplied authority; descriptors do not open paths,
load capabilities or enroll actors. Mismatches are refused. Older descriptor-free
arms stay held. The source reconstruction registration requires an explicit
authority resolver and is not automatically in the production catalogue.

The daemon now requires an A2A source guard before publication. Loading the actual
old evaluator function body from the baseline commit reproduced the regression:
revoked cached receipts fired once instead of zero. The new guard keeps them
pending with or without a runner. This expected baseline failure is defect
evidence, not a flaky suite retry. Reopening the journal and reconstructing via
the source registry publishes one firing record; another poll adds none.

Focused: 50 receipt/registry/daemon tests passed in 2.944s; the additional denied
resolver fixture then passed in the nine-test receipt selection. Final full
suite: 824 tests in 48.520s, no failures or retries. Planning audit and diff check
passed. Isolated installed Python 3.12 receipt tests: nine passed in 1.134s,
module path verified in /tmp/codex-wake-p63-receipt-venv/site-packages.

Initial resource census: descriptors 4 -> 5, children 0 -> 0. Inspection found
the added descriptor was /dev/urandom. With imports/os.urandom initialized before
baseline, nine installed tests passed in 1.127s: descriptors 5 -> 5, children
0 -> 0. Preserve both samples; this is bounded fixture evidence, not a soak.
All bodies/actors/roots are synthetic; dispatch disabled, no service effects.

Remaining: production authority resolver/configuration, long-suspension CLI and
installed process restart; safe notification, named agents, lifecycle/multiroot
resource soak, supervisor, migrations/rollback and release. Memory disposition
unavailable; no authorized healthy Graphiti write path.

Pre-integration transport boundary check: generic dispatch now explicitly holds
A2A receipt firing records with "A2A receipt delivery is unqualified" before
transport selection. Receipt matching cannot silently route through the older
tmux/stdin/app-server transports. The real published fixture remains in firing
without an effect. This is a held delivery outcome, not successful suspension.

## Post-reboot webhook CI diagnosis | Plan 0108

Original failure retained: hosted run 37148747612, Python 3.12 job
111277982216, on 8dd07138661ca8b9b8e5ce913ce73ec5074a7a7c. Python 3.11
passed; Python 3.12 ran 824 tests in 29.696s and failed with one error and
one assertion failure. The trace can be recovered with
`gh run view 37148747612 --job 111277982216 --log-failed`.
The downloaded log is ephemeral at `/tmp/codex-wake-p63-ci-failure.log`.

Post-reboot baseline on local Python 3.12.13: 824 tests passed in 34.167s.
100 ordinary iterations of the two failing tests passed in 35.183s. These
passes are retry evidence, not erasure of the hosted failures.

The tight regression command is:

```sh
PYTHONPATH=src:tests python3 -m unittest \
  test_webhook_http.WebhookHTTPTests.test_connection_and_ingest_capacity_reject_without_queue \
  test_github_webhook_runtime.GitHubWebhookRuntimeTests.test_provider_timeout_runs_on_main_thread_and_fails_closed -v
```

Before repair, delaying the real SHUT_WR until the response was readable
produced the hosted ENOTCONN exception 3/3, in 0.085–0.112s per run. The
minimal condition is a saturated listener plus a client half-close after the
rejected peer has closed. Parsing was never reached. The helper now ignores
only ENOTCONN, then still checks exact status/code, Content-Length, complete
body, Connection: close, and Cache-Control: no-store. The existing capacity
test forces this errno at that seam while retaining the real listener and
both connection/worker admission cases; it checks one ingest before and
after the first request completes. A post-fix real-socket scheduling probe
also observed errno 107 and still parsed 503 ADMISSION with zero ingest
for the rejected connection.

Before repair, adding 300 ms before real durable ingest produced the exact
recovery response COMMIT_FAILED 3/3, in 0.538–0.558s per run. Controls with
zero and 100 ms delay passed. Instrumentation at store entry read fresh
remaining timers of 0.249190, 0.249246, and 0.249265 seconds respectively;
the 300 ms case raised GitHubReadError inside the store boundary. All three
ended with a disarmed timer. This rules out an inherited expired timer in
these probes and proves that the whole ingress deadline includes storage.
It does not prove whether the hosted storage delay was contention, disk,
or process scheduling; the hosted trace lacks phase timing.

Ranked predictions were premature client half-close, recovery storage budget,
stale timer/checkpoint, and incomplete admission response. The first two
were reproduced; no timer-leak or incomplete-response evidence was found.
The configured runtime contract remains Plan 0072: the POSIX main thread
owns one absolute deadline covering provider and store work.

The recovery fixture now uses a one-second operation budget, matching the
other durable runtime success fixtures, with a deliberate 300 ms store delay.
The provider stall is ten seconds so actual deadline expiration must
interrupt it. The test still requires 503 VERIFICATION_UNAVAILABLE then
200 COMMITTED on the same runtime, two main-thread factories with armed
fresh timers, no normal completion of the stalled provider, disarmed timer,
restored signal handler, and the same checkpoint after reopening SQLite.
Its aggregate elapsed bound is three seconds. These are fixture-only budget
changes; production deadline defaults and enforcement are unchanged.

With the regression stimuli added before repair, the tight command failed
with ENOTCONN in both admission cases and the exact COMMIT_FAILED assertion
in 0.658s. After repair it passed in 1.448s. Focused affected modules:
29 tests passed in 4.978s. Final full local Python suite: 824 tests passed
in 33.848s, no retry on that edited suite. Source/test/hook compilation and
diff hygiene passed. Python 3.11 affected modules: 29 tests passed in 4.338s.
Final active planning audit passed with only 20 accepted legacy findings.
No DEBUG instrumentation or throwaway repository scripts
remain. Installed/wheel and plugin checks were not repeated for these test-only
edits; no production source changed.

Hosted CI has not been rerun on the repair, and PR #188 has not been integrated.
The original hosted flake remains explicitly recorded; local acceptance of
this fixture repair does not establish hosted gate acceptance or full Plan
0101 completion. The fresh-agent handoff is preserved without modification.
Graphiti discovery was healthy, but the bounded atlas query established no
applicable authorized repository group; closeout disposition is unavailable,
with zero Graphiti writes.
Non-write receipt:
`/home/ecochran76/.graphiti-openclaw/state/closeout-memory/20261003T211337Z-remember.json`.
