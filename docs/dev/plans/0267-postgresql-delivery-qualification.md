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
