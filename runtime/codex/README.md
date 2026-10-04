# Opt-in Codex owning-client binding

Disposition: inactive historical candidate. The operator rejected a custom Codex
runtime dependency for Plan0119; use the existing Wake transport instead. Do not
activate this patch or pin Codex updates. The build and launch instructions below
are retained as provenance, not the current product installation path.

This candidate patch is pinned to the official source revision in `manifest.json`.
It is **not the installed Codex release**, and compilation is not live acceptance.
Upstream source retains its Apache 2.0 license in `LICENSE.upstream`.

The opt-in TUI endpoint checks the actual thread, root, composer, pending input,
modal and offline state in its own event loop. It passes only an exact mailbox
retrieval pointer. The new `turn/startIfIdle` app-server operation uses Core's
atomic idle-only submission, does not load an unloaded thread, never steers or
queues input, and preserves existing `turn/start` behavior. Both server and client
must carry this patch. An older server has no delivery fallback.

Build the exact candidate without installing or restarting anything:

```sh
python scripts/build_wake_client.py --work-root /ABSOLUTE/OWNED/BUILD --download
```

The helper records archive/patch/executable hashes and toolchain. A supplied
`--archive` avoids downloading. `--prepare-only` verifies and applies the patch.
The release archive stamps workspace manifests to 0.160.0 while its lockfile
retains 0.0.0 for workspace packages. The helper normalizes only those source-less
entries, verifies the resulting lockfile hash, and builds with `--locked`.
External dependency versions remain pinned to the archive.
The default build uses four compile jobs; this may take substantially longer
than the ordinary Wake Python checks. Build receipts remain outside the repo.

For a client explicitly authorized to reconnect to its existing thread, opt in
at launch using an unused socket path in a canonical mode-0700 directory:

```sh
CODEX_WAKE_CLIENT_SOCKET=/OWNED/CLIENT/client.sock \
CODEX_WAKE_A2A_BUS_ROOT=/ENROLLED/BUS \
CODEX_WAKE_A2A_CAPABILITY=/ISSUED/ACTOR.json \
CODEX_WAKE_WAKE_ROOT=/OWNED/WAKE \
CODEX_WAKE_SENDER_RECEIPT_AUTHORITY=/OWNED/SENDERS.json \
  /EXACT/CANDIDATE/codex resume EXISTING_THREAD_ID
```

The same-UID boundary provides API authority, not OS isolation. The worker pins
socket credentials, PID start time, boot ID, client generation, exact runtime
namespace/thread and root. Reconnect requires an explicit new binding; old
uncertain attempts remain held. The client never adopts/unlinks an existing
socket. Its private socket is removed on normal client exit.

Operator setup, once per opted-in live client:

```sh
codex-wake a2a bind-client --bus-root /ENROLLED/BUS \
  --operator-capability /ISSUED/OPERATOR.json --thread EXISTING_THREAD_ID \
  --client-socket /OWNED/CLIENT/client.sock --bindings-file /OWNED/BINDINGS.json --json
codex-wake a2a worker --bus-root /ENROLLED/BUS \
  --operator-capability /ISSUED/OPERATOR.json --bindings-file /OWNED/BINDINGS.json \
  --duration 120 --max-dispatches 2 --json
```

For durable sender reply wakes, the operator explicitly delegates each sender
before agent work starts:

```sh
codex-wake a2a delegate-receipts --bus-root /ENROLLED/BUS \
  --operator-capability /ISSUED/OPERATOR.json --thread EXISTING_THREAD_ID \
  --wake-root /OWNED/WAKE --sender-receipt-authority /OWNED/SENDERS.json --json
codex-wake a2a worker --bus-root /ENROLLED/BUS \
  --operator-capability /ISSUED/OPERATOR.json --bindings-file /OWNED/BINDINGS.json \
  --wake-root /OWNED/WAKE --sender-receipt-authority /OWNED/SENDERS.json \
  --duration 120 --max-dispatches 2 --json
```

The worker advertises actual process-bound reader health for that wake root.
Set `CODEX_WAKE_WAKE_ROOT` and `CODEX_WAKE_SENDER_RECEIPT_AUTHORITY` in the opted-in
sender's environment. After sending, the sender runs native `messages arm-reply`
for the returned exact message ID with an explicit idempotency key and fixed
timezone-aware expiry, then ends its turn. No operator intervention is required
after send. The independent delegation authorizes only listed senders' own
outgoing messages; it is revalidated on receipt observation and delivery.
In this worker mode, a reply notification waits for a matching live reply arm.
Cancelled/expired arms and removed delegations cannot release it. The arm and
existing notification journal retain send evidence across worker restart.

Binding does not enroll actors or grant notification rights. Those are independent
operator actions. The worker uses the existing fenced mailbox scheduler. It
rechecks grants, cancellation, expiry, FIFO and pause before dispatch. Deferred
clients consume no actual send attempt; ambiguous I/O becomes `uncertain` and is
not automatically replayed. A transport submission is not receipt/ack/reply proof.

The Plan 119 live packet must still prove both resumed turns and acknowledgements.
Shared-daemon activation, reconnecting user-owned clients, release and installed
acceptance have their own concrete authority gates. Do not restart the shared
daemon merely to run this candidate.

## Selected stock-runtime alternative

Use the installed Wake CLI's explicit tmux binding for each enrolled client:

```sh
codex-wake a2a bind-tmux --bus-root /ENROLLED/BUS \
  --operator-capability /ISSUED/OPERATOR.json --thread EXISTING_THREAD_ID \
  --tmux-socket /OWNED/TMUX/SOCKET --bindings-file /OWNED/BINDINGS.json --json
```

Run the existing bounded `a2a worker` with those bindings and independently
delegated sender receipt authority. It submits the exact inbox retrieval pointer
through the existing paste transport, with metadata and empty-composer checks.
A visible pasted prompt is transport evidence; the live agent must separately
read, acknowledge and reply. Checks before paste are observational and cannot
provide atomic protection against simultaneous human input. Unknown composers
are deferred and ambiguous delivery is never automatically retried.
