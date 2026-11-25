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
