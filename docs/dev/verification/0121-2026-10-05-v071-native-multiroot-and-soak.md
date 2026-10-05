# Released v0.7.1 native service, multiroot and failed soak

Plan0119 / issue181; primary serialized execution. Public v0.7.1 peels to
bec10055a171a6e3c4de51718a16b15387fe80b9, integrated through PR216 after required
Python3.11/3.12 CI37251607355 passed. Ordinary global uv installation records
that exact revision and reports0.7.1. The shipped unit adds the stable user CLI
directory to PATH. Stock Codex0.160.0 remains unchanged; OpenClaw remains parked.

## Released native service PASS

Native unit codex-wake-plan119-v071-smoke.service used the global installed CLI,
duration180, notification budget2 and Restart=no. Original A/B threads exchanged
request msg_e03ec6398cf44276ba3c88c2cb475887 and correlated reply
msg_6d7d5ccc20514719ba29c8bd42b1e86e. Actual automatic A read receipt
receipt_aab1bfa09bb14e0cbd1531c23cca2529 completed in77.85157925199746 monotonic
seconds from before send. Exactly two submitted transport attempts. Worker92521
exited0 and is absent; both original bindings ready. No controller relay after
admission. The v0.7.0 PATH failure remains a failure in verification0120.

## Actual multiroot PASS

Additional owned root2 thread01a109b0-13d6-7882-b9e3-6ff6d6bdd38b retained its
identity throughout setup corrections. Before enrollment, actual A's send was
authorization_denied and the journal contained zero envelopes for its intent.
After explicit root/thread enrollment and native binding, released native unit
codex-wake-plan119-v071-root2.service delivered request
msg_232b86ba8ebd4802902fe57d6de12d03 and correlated root2 reply
msg_0e107aec46cc4f55a309480a36446a0e. Actual A read receipt
receipt_f0e61f62f7034897b58091dbe5e58b25 completed in71.08145843799866 monotonic
seconds. Exact sender/recipient roots differ in both directions; exactly two
submitted attempts. Worker25841 exited0 and is absent; all three bindings ready.

Setup failures are retained: tmux's owning pane must actually have root2 cwd;
Codex -C alone did not establish it. The initially selected workspace-write
fixture could not access the existing daemon Unix socket. Resuming that same
thread with the user's existing normal danger-full-access setting allowed the
read-only native preflight. No shared daemon or global sandbox setting changed.

## Thirty-minute soak FAIL / incomplete

Frozen native unit duration1800, budget20, at most ten pairs (four planned),
store ceiling10485760bytes, stable FD growth<=2, RSS growth<=67108864bytes,
residual owned children0. Installed version/source were fixed before admission.
Worker1788 ran786.195835seconds to the manager's stopped journal event, then was
absent. Fresh manager readback: inactive, MainPID0, ExecMainStatus0.

Pair1 passed actual automatic round trip in82.01725472800172seconds. Pair2 request
msg_186461c7881147dda1018d68eb5cb27d had exactly one submitted notification;
actual B's native read returned exit8/clock_anomaly before any read effect.
Read-only reconciliation still shows unread, no read/claim/terminal receipt and
zero replies. No acknowledgement, reply or retry occurred. Pairs3/4 were not
admitted. The clock guard remains intact; no host clock/checkpoint was modified.

Qualification errors are separate: the observer omitted B-read-request.json
from failure detection and stopped the unit after its file-observation deadline.
An observer timeout alone was insufficient terminal evidence. Its resource
summary also subtracted a cleared systemd exit timestamp and produced an invalid
negative duration. Preserve that raw FAIL; terminal-reconciliation.json records
the actual captured start and manager stop monotonic timestamps. Neither error
can turn this sample into a thirty-minute pass.

Observed stable FD growth0, RSS growth3022848bytes, peak store564112bytes;
resource observations cannot prove the missing duration or failed exchange.
No residual children/cgroup processes were found at termination.

## Provenance and next bounded packet

Private evidence base:
/home/ecochran76/.local/state/codex-wake/live-demos/20261004-wakeA-wakeB/tmux-plan119/v070

v071-live/m1/final-proof.json and actual actor outputs/turns;
multiroot/unenrolled-final-proof.json and m1-normal/final-proof.json/turns;
soak/frozen-thresholds.json, resource-before.json, resource-observations.jsonl,
resource-final.json, worker-journal.jsonl, pair-outcomes.json,
pair-02/m1/B-read-request.json and terminal-reconciliation.json.
Credentials and message bodies remain outside git.

The original soak loop is closed as failed, not silently retried. Next packet:
correct qualification observers to distinguish observation errors, native
zero-effect rejection and authoritative process termination; diagnose the live
clock discontinuity read-only; establish a bounded actor recovery policy before
another full-duration run. Retain same guard, original identities, all failed
evidence and the fixed120-second exchange bound. No replay of the already
submitted pair2 notification. Full Plan0119/issue181 remain OPEN. Prior live
cancellation/reconnect/normal worker-restart and installed rollback passes stand.
