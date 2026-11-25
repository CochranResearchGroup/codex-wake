# Plan0267 PostgreSQL delivery qualification

Use an isolated PostgreSQL database. Install the optional `postgres` extra,
set `CODEX_WAKE_MESSAGE_DB_DSN` in the privately managed process environment,
and run `codex-wake messages database-init` against that database once. The
direct-send command, its notification dispatcher, the timed-wake command, and
the owning monitor must use the same database. A missing setting selects the
existing legacy path. The opt-in retains the existing local message and wake
records as the execution owner's journals.

Run `test_postgres_message_delivery` with `CODEX_WAKE_TEST_MESSAGE_DB_DSN`
set to the disposable database and `PYTHONPATH=src:tests`. The test exercises
the existing direct-send and timed-wake CLI, the A2A dispatcher and the Wake
monitor, and checks the same PostgreSQL admission and receipt tables for both.
The owning-client and queue transport doubles and injected time are isolated
acceptance inputs. The stock Codex journey additionally uses a real stock
daemon, StableTime, disposable Wake roots and a local loopback model response.

A transport intent is committed before calling the harness. If its outcome is
uncertain, another attempt cannot overtake it. An admitted command and
PostgreSQL-backed dispatch are separate observables. A command retained while
PostgreSQL is down reports pending shared admission. No private production
data or runtime units participate in this qualification.

## One-scope legacy cutover

In a disposable deployment, place the existing Wake and A2A state roots
under one private scope directory. Stop its Wake monitor and pause the
mailbox using its existing operator capability. Use the absolute paths to the
three directories and the mailbox capability. Preview first.

```sh
codex-wake --wake-root "$wake_root" migration message-cutover \
  --isolated-root "$scope_root" --bus-root "$bus_root" \
  --operator-capability "$mailbox_operator" --json
```

Configure `CODEX_WAKE_CUTOVER_DB_DSN` with the private disposable database
connection for the cutover command and the two owning workers. Apply the same
command with `--expected-source` set to the preview's `source_digest`. An
`activated` result confirms the unchanged source snapshot and PostgreSQL
readback, then enables shared message admission and dispatch receipts for
those two roots. The worker can resume using its existing monitor command
and mailbox resume control. Keep the local journals for scheduling and
compatibility. Do not combine this procedure with the unscoped
`CODEX_WAKE_MESSAGE_DB_DSN` test setting.

Original transport attempts with missing or uncertain receipts remain fenced.
Run the existing `codex-wake native reconcile <wake-id>` in the migrated scope
to look for positive evidence. When it finds the exact receipt, the worker
records it against the original PostgreSQL attempt before marking the local
Wake submitted. An unresolved observation holds the original attempt.

Run `test_message_cutover` with `CODEX_WAKE_TEST_MESSAGE_DB_DSN` and
`PYTHONPATH=src:tests` to verify the public cutover and reconciliation
commands against disposable PostgreSQL. The test uses an isolated legacy
mailbox, a recurring schedule and a transport evidence double.

## Normal Windows and WSL message owners

Each owner uses a private local state directory and an exact pair of
registrations from the host registry. Create one operator-owned JSON config
per account. The config includes `root`, `registry`, `owner`, `peer` and,
for workers started without an operator shell, `db_dsn_file`. The owner and
peer values are the full host registration targets, including authority and
generation. Point both owners to the same PostgreSQL instance. Keep the
local owner state directories in their respective filesystems.

Run `codex-wake message-owner --config OWNER.json run` for an owning worker.
The Windows package includes `windows_message_owner.ps1`. Invoke it with the
native Python executable, owner config, and the preconfigured native PostgreSQL
service name. It waits for that service, then the worker verifies PostgreSQL
and restores its local journal before reporting shared ingress ready. For an
isolated native PostgreSQL foreground process, omit the service name. The
same SQL readiness check still runs. Register a production service or task
separately under the normal Windows owner.

The Windows owner can optionally configure `wsl_auto_start` with the pinned
peer `environment`, registered `distribution`, absolute WSL `python`
executable and `config` path. An eligible WSL-bound message can start that
owner using `wsl.exe --exec`. The source keeps forwarding custody until it
reads the destination's durable outcome. Status reads use the local journal
and do not activate the peer. Ordinary SSH tabs do not start this worker or
either side's multiplexer.

Use `send --request FILE` with a JSON object containing `identifier`,
`recipient`, `body` and absolute UTC `expires` in microseconds. `due` and
`in_reply_to` are optional. `status ID` returns cached outbound custody, and
`--inbound` reads the recipient owner's journal. A local `set-local` or
forwarded `request-setting` carries `recipient`, expected `revision` and
Boolean `dnd`. A forwarded edit also needs an `identifier`. On a revision
conflict, the owner returns its current revision and keeps its own setting.

An owner can configure `bindings` from exact recipient UUIDs to absolute
local transport argv. This is an owning adapter boundary. Each adapter gets
one Message JSON frame on stdin after the owner checks the original expiry
and its current local DND setting. A submitted receipt must echo the message
ID, recipient and original expiry. The adapter owns any final idle check and
harness operation. A recipient without a binding remains held. The worker
reconstructs original submitted and uncertain effect records after a database
restore. An uncertain effect is held under its original ID.

The opt-in `test_message_owner` verification uses disposable PostgreSQL and
owning transport doubles. It exercises both directions, original reply and
expiry, missing transport receipt, offline settings, stale edits and journal
restoration.

## Native Windows psmux recipient

Use the normal Windows message owner with a Codex app server bound to
IPv4 loopback and a private capability-token file. Enroll the exact
conversation while it is idle. The enrollment request JSON contains
`thread`, `namespace`, `session`, `title`, `index`, `cwd`, `home`,
`codex`, `port`, `server_pid`, and `token_file`. Use a private directory
for the binding and its placement journal.

```powershell
python -m codex_wake.psmux_message_recovery --binding C:\WakeBindings\BINDING.json enroll --request REQUEST.json
python -m codex_wake.psmux_message_recovery --binding C:\WakeBindings\BINDING.json present
python -m codex_wake.psmux_message_recovery --binding C:\WakeBindings\BINDING.json status
```

Give the Windows owner's exact recipient UUID an absolute Python binding
that invokes `-m codex_wake.psmux_message_recovery --binding C:\WakeBindings\BINDING.json deliver`. The retained message controls original eligibility and expiry.
The adapter verifies the pinned Windows owner, original Codex home,
application process, provider and conversation before restoring its view.
A busy detached turn holds both the presentation and delivery.

After tab loss, recovery first tries the saved vacant slot. A same-title
idle shell in that slot and directory can move to a spare slot with its
process intact. A different occupant retains its pane and placement. After
psmux server loss, the adapter opens the original named session and places
the new client in the saved slot. Status reads inspect the tracked
presentation without opening a client. An exact stock Codex queue receipt
confirms acceptance by the original thread.

This owner binding covers managed Windows Codex presentations. Enrollment
creates and tracks the client's process receipt. Existing untracked panes
require explicit selection or migration. The Codex app-server process
remains pinned across the two psmux recovery cases.

## External OAuth MCP scheduled recovery

The protected tmux owner uses `wake_wakes_schedules_register` and
`wake_wakes_schedules_bind_restoration` with the exact conversation and
the host’s existing managed restoration profile. Retained registration
and a configured restoration binding are separate from a running
monitor and a submitted wake.

For Windows psmux, the external connector can expose
`wake_wakes_messages_schedule` and `wake_wakes_messages_status` when
its private policy includes `windows_message_owner`. Set its
`owner_config` to the absolute private WSL MessageOwner config for the
pinned Windows peer. Set `targets` to exact psmux conversation entries.
Each entry has the connector’s local `host` and `environment`,
`presentation` set to `psmux`, the exact `conversation_id`, and the
Windows peer’s `namespace` (registered environment), `authority` and
`generation`. Include those exact targets in the available OAuth
consent choices.

A control grant bound to one of those exact targets can admit a
`message_id`, body, original `due_at` and original `expires_at`. Use the
same request and UUID to reconcile a lost admission receipt. The WSL
owner retains the message and the Windows owner performs recipient
recovery when eligible. The original grant can include observe to read
its own admission’s metadata, including the original delivery window and receipt. Reading a
receipt preserves both terminal owners’ current activation state.

For ordinary external mailbox send, a control-only grant can retain a
message and get a metadata receipt. Waiting synchronously for a reply
requires `content.observe`. Former-tab history metadata requires
`history.observe`. Reading its saved records also requires
`content.observe` and the exact saved account scope.

## Elevated Windows recipient

Register the normal and elevated Windows owners as two exact execution
environments. Run `codex-wake windows-scope` from each native Windows
execution account and register its JSON with `hosts register --windows-identity`.
Use kind `windows` for the normal owner and `windows-elevated` for the
elevated owner. Two scopes can have the same account SID. The explicit
elevation field distinguishes them. Pair their registrations directly for
local Windows forwarding and keep separate owner journals.

Provision the elevated owner and its PSMux recovery in dedicated private
directories with the elevated account SID as owner and a High mandatory
label with no-write-up. Apply the label to the directories and protected
files. Give the elevated app-server token file a High label with both
no-write-up and no-read-up. Supply the owner config with an absolute `executor_activation` path.
Its exact JSON is `{"version":1,"scope":{"sid":"S-1-5-21-100-200-300-1001","elevated":true},"enabled":false}`
using the SID returned by `windows-scope`. An authorized high-integrity
executor enables recovery by setting `enabled` to true. An absent or disabled
record keeps the original message pending for that executor. The normal
owner continues operating independently.

Add the elevated owner's exact `execution_scope` and `executor_activation`
path to the PSMux enrollment request. Run enrollment, the Codex app server,
and the PSMux presentation from that same native scope. Recovery verifies
the process token and the saved conversation before restoring its view. A
normal owner with a matching tab title or position cannot claim the message.

## Separately operated Wake servers

Configure one exact owner pair on each server with `message-owner`. Each
server uses its own private owner journal and PostgreSQL database. Register
both exact owners in both local host registries with matching authorities
and generations. Use different host identifiers and a concrete execution
kind. Set each peer's SSH destination to a literal host or `user@host` and
set its SSH executable to an absolute path.

Add the following object to each private owner configuration. Pin the
corresponding SSH server host key in the private `known_hosts` file.

```json
{
  "cross_server": {
    "identity_file": "/private/wake/peer-ed25519",
    "known_hosts": "/private/wake/peer-known-hosts",
    "port": 22
  }
}
```

Authorize only that peer key on the receiving account. Use a restricted SSH
key and a forced command that accepts the fixed original command
`codex-wake-message-relay-v1` and runs
`codex-wake message-owner --config /private/wake/owner.json receive-forward`.
This command accepts one protocol frame on stdin, saves it to the receiving
owner journal, and returns that owner's current disposition. It does not
invoke the harness or modify recipient settings. Start the `message-owner
run` worker on each server to forward and process retained messages.

Use the existing `message-owner send` and `status` commands. A sender's
`waiting_for_peer` means it has retained its original request without a
confirmed peer disposition. A lost transport response leaves the current
sender status intact. The worker retries the original immutable envelope
and accepts a response only for that owner pair, recipient, message ID,
reply correlation and original eligibility window. The recipient's local
journal arbitrates delivery and retains the original harness receipt. A
received `uncertain` outcome remains fenced and status never treats it as
submitted.
