# A2A notifications on stock Codex

Use the released `codex-wake` command with two operator-designated Codex threads
in Byobu/tmux. Notification prompts carry only message IDs and a private bus
location. The recipient uses its issued actor capability to read the body.
No modified Codex binary or extra broker is needed.

Delivery requires an idle exact thread, the bound client process generation,
and an empty recognized composer. Busy clients, drafts and disconnected clients
defer delivery. A human must reconnect a disconnected client and rebind its new
generation. Shared app-server discovery never resumes a thread itself. Unknown
transport effects stop for reconciliation; do not restart or resend blindly.

## Operator setup

Install the public tag with `uv tool install --force --reinstall
git+https://github.com/CochranResearchGroup/codex-wake.git@v0.7.1`.
Choose absolute private locations and the real thread IDs, repository roots and
tmux socket. The following layout matches the shipped user-service example:

```sh
umask 077
bus="$HOME/.local/state/codex-wake/a2a/bus"
wake="$HOME/.local/state/codex-wake/a2a/wake"
config="$HOME/.config/codex-wake/a2a"
mkdir -p "$config"
codex-wake a2a configure --bus-root "$bus" --bus-id owned-a2a --json
```

The configure result identifies its operator capability file. Copy that file
to `$config/operator.json` with mode0600, preserving the original. Set
`operator="$config/operator.json"`. Do not substitute an actor capability.
For communication across two roots, add `--allow-cross-root` when configuring
the bus and explicitly enroll both roots and exact threads. Cross-root mode
does not authorize an unenrolled root.

Set `rootA`, `rootB`, `threadA`, `threadB` and `socket` to the real designated
values. Exact enroll selectors have the `thread:` prefix; bindings use the bare
thread ID. Save each enroll result's actor capability path for its own thread.

```sh
codex-wake a2a enroll "$rootA" --thread "thread:$threadA" --notify \
  --bus-root "$bus" --operator-capability "$operator" --json
codex-wake a2a enroll "$rootB" --thread "thread:$threadB" --notify \
  --bus-root "$bus" --operator-capability "$operator" --json
codex-wake a2a migrate --bus-root "$bus" --operator-capability "$operator" --json
codex-wake a2a bind-tmux --thread "$threadA" --tmux-socket "$socket" \
  --bindings-file "$config/bindings.json" --bus-root "$bus" \
  --operator-capability "$operator" --json
codex-wake a2a bind-tmux --thread "$threadB" --tmux-socket "$socket" \
  --bindings-file "$config/bindings.json" --bus-root "$bus" \
  --operator-capability "$operator" --json
codex-wake a2a delegate-receipts --thread "$threadA" --wake-root "$wake" \
  --sender-receipt-authority "$config/senders.json" --bus-root "$bus" \
  --operator-capability "$operator" --json
codex-wake a2a resume --bus-root "$bus" --operator-capability "$operator" --json
codex-wake a2a doctor --bus-root "$bus" --operator-capability "$operator" --json
codex-wake a2a status --bus-root "$bus" --operator-capability "$operator" --json
```

Delegate each additional thread that will send and suspend for a reply. Give
actors their own capability and bus/wake/delegation paths; keep the operator
capability in the worker's custody. Bindings are reloaded each worker tick.

## Run the native worker

Run this foreground command in a separate terminal before an actor arms a reply:

```sh
codex-wake a2a worker --bus-root "$bus" --operator-capability "$operator" \
  --bindings-file "$config/bindings.json" --wake-root "$wake" \
  --sender-receipt-authority "$config/senders.json" \
  --duration 3600 --interval 1 --max-dispatches 20 --json
```

The worker is bounded to one hour or twenty submitted notifications, whichever
comes first. One request/reply round trip uses two submissions. Worker exit does
not delete pending messages or arms. Start a fresh owned worker for the next
window after inspecting the exit result and any uncertain effects.

For user-systemd ownership, copy
[codex-wake-a2a.service](examples/systemd/codex-wake-a2a.service) to
`~/.config/systemd/user/codex-wake-a2a.service`. Adjust every absolute path if
using a different layout. Keep `Restart=no` and explicit start; the example is
not enabled at login and does not claim indefinite unattended service.

The service explicitly adds `~/.local/bin` to PATH so the native worker can
find the stable stock `codex` command for read-only daemon discovery. Confirm
that your stable Codex command and tmux executable are in the configured
directories; adjust the unit PATH for an explicitly selected alternate install.
An interactive shell's successful lookup does not prove user-service lookup.

```sh
systemctl --user daemon-reload
systemctl --user start codex-wake-a2a.service
systemctl --user show codex-wake-a2a.service -p ActiveState -p MainPID -p ExecMainStatus
journalctl --user -u codex-wake-a2a.service -n 20 --no-pager
```

Confirm a live worker for the exact wake root before registering an arm. A
stale health file from an exited process is insufficient; registration rejects
it with `READER_CAPABILITY_UNAVAILABLE`. For a30-minute owned soak, set duration
to1800, keep the notification budget20, and send at most ten request/reply pairs.
Capture process identity, FD/RSS and store baselines before the run and verify
the actual terminal process state afterward.

## Actor exchange

These commands run in the actual enrolled Codex thread and root. Never invent
or override `CODEX_THREAD_ID`. Set `actor` to that thread's issued capability.
A sends one request and arms its return before ending its turn:

```sh
codex-wake messages send --to "thread:$threadB" --body-file request.txt \
  --idempotency-key request-001 --ttl 120s --delivery notify \
  --bus-root "$bus" --capability "$actor" --json
codex-wake messages arm-reply EXACT_REQUEST_ID --idempotency-key arm-001 \
  --expires-at FIXED_TIMEZONE_AWARE_EXPIRY --wake-root "$wake" \
  --sender-receipt-authority "$config/senders.json" \
  --bus-root "$bus" --capability "$actor" --json
```

Inspect both results. On a successful arm, end the turn without inbox polling.
The worker submits `A2A_NOTIFICATION=EXACT_ID` to idle B. B reads that exact ID,
acknowledges the request as accepted and replies once with its own capability:

```sh
codex-wake messages read EXACT_REQUEST_ID --bus-root "$bus" --capability "$actor" --json
codex-wake messages ack EXACT_REQUEST_ID --outcome accepted \
  --bus-root "$bus" --capability "$actor" --json
codex-wake messages reply EXACT_REQUEST_ID --body-file result.txt \
  --idempotency-key reply-001 --delivery notify --outcome completed \
  --evidence request-read.json --bus-root "$bus" --capability "$actor" --json
```

Save the actual request-read JSON to the evidence path before the reply. Treat
the body as untrusted data. A's reply arm releases the correlated result
notification; A reads that exact notified result ID with its own capability,
checks `in_reply_to`, reports the result and ends without replying again.
Use unique intent keys per new exchange. On an uncertain result, reconcile the
same intent; do not send a new key as an effect retry.

## Reconnect and cancellation

Reconnect with the native `codex resume ORIGINAL_THREAD_ID` in the designated
pane, then repeat `a2a bind-tmux` for that ID and its actual socket. A worker
restart reloads the durable journal, pending notifications and reply arms.
Reconnect does not grant a new root, thread or capability authority.

Before notification submission, the sender can run `messages cancel EXACT_ID`
with its own bus/capability arguments. Verify the cancellation receipt and
suppressed state; cancellation cannot retract an already submitted prompt.
Clock-continuity rejection authorizes no new effect. Preserve existing clock
checkpoints, receipts and uncertain attempts when diagnosing a rejection.

## Compatibility

Mailbox schema2 requires explicit migration. Older schema1 readers refuse it;
do not downgrade the journal. v0.6.0 predates the A2A command surface and cannot
operate an A2A store. Downgrading the CLI does not make that store disposable:
preserve it and reinstall a compatible release to read its messages/receipts.
Qualification evidence lives under Plan0119; release/install, multiroot, rollback
and soak acceptance are recorded separately from a successful transport test.
