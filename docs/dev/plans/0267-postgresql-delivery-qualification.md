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
