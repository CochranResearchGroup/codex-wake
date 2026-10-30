# Ticket401 — expanded required adapter matrix clock hold

State: **HELD / incomplete acceptance**, not an optional matrix. Product source is exactly combined `be127d46e4c43eecb6a081091c9f6da107d9ac81` plus the bounded-memory revocation iterator retained with the successful receipt. The installed package and eight product-module hashes are unchanged from `runtime401-installed-public.json`. No production activation or provider authority.

The original successful harness is `scripts/controller_runtime_acceptance.py`, SHA256 `38f977c2011dec2c8c851de32247bbbdcd6a1bb281df275641b4ed2dd3fae183`. The expanded failed harness is preserved verbatim at `scripts/controller_runtime_expanded_acceptance.py`, SHA256 `09660eea4e4263a4c9ff2f0e821dfbea8c7dc513d4bc37e6682fe0aaa117a1b1`. Neither source contains actual issued tokens/passwords; the fixture generates private temporary credentials at run time. The passing script is not substituted for the failed all-capable send/wait gate.

The expanded version additionally exercises default response-requested supervised-command send and explicit OAuth-MCP/remote-CLI send/wait using the same original intent. Exact failed invocation, before the expanded source was copied to its retained filename:

```
cd /tmp/codex-wake-401-acceptance
/tmp/wake401-public/bin/python scripts/controller_runtime_acceptance.py --shared-cli > docs/dev/evidence/plan0190/runtime401-installed-public.json
```

Failure locator: completed tool session56713, exit1, output chunk914c65. Exact stack is retained in `runtime401-expanded-failure.stderr.txt`. Its target operation had already been admitted through direct API, then returned the same native message ID through OAuth MCP send and installed remote-CLI send. The next direct native-owner outbox inspection raised BusError(clock_anomaly) before the one-message-count assertion could complete. Later OAuth-MCP/remote-CLI wait assertions and the remainder of this expanded run were not reached and are not counted as passing. Earlier completed assertions, including default response-requested command stdout and actual native-MCP send/wait/result, remain evidence for their own boundaries.

The redirect left empty stdout because the harness emits its final receipt only after all assertions. The prior successful receipt was restored from the earlier completed session55903 stdout metadata, with every source/installed hash rechecked; it does not represent this failed attempt.

## Clock/bus fixture pins

The harness creates a fresh private bus with `BusStore.configure(<temporary>/bus)` and explicitly runs `Mailbox.migrate(bus, operator_capability)`. Source pins in the installed candidate are BusStore SCHEMA_VERSION=1 and Mailbox MAILBOX_SCHEMA=2; NETWORK_MAILBOX_SCHEMA=3 is not selected. No network-time migration, NTP opt-in or alternate clock policy is configured.

Every harness/controller/recipient Mailbox instance uses its default `clock=time.time`, `monotonic=time.monotonic` and real `/proc/sys/kernel/random/boot_id`. No clock, monotonic or time_provider value is injected. `time.time()` supplies only real synthetic observation timestamps and caller expiry; `time.sleep()` bounds fixture command/recipient delays. The worker made no system-clock adjustment, checkpoint reset, guard disable or allowance change.

The native owner's existing continuity gate rejects either wall time more than one second below its stored checkpoint, or same-boot wall/monotonic elapsed disagreement over three hundred seconds. The failure provides no retained checkpoint values, so this receipt does not infer which predicate fired or claim a system-clock jump. `TemporaryDirectory` cleanup removed the failed bus after the exception. Its checkpoint cannot be reconstructed honestly. The first readback after the failure observed UTC2026-10-30 11:47:53, wall1793360873.6645799 and monotonic166674.594152025; these are **post-failure observations**, not values from the failed transaction.

Each harness attempt uses new disposable roots and its own native IDs/receipts. No original uncertain operation was retried. Native fixture processes have finite bounds; recipient and HTTP processes are reaped in finally blocks. No live provider, shared service or credential copy was used.

Primary authorized one bounded fresh-fixture diagnosis/reproduction. The worker has not run it. Preserve the current clock hold; do not reset/disable it or recreate fabricated provenance. Primary must establish cause and complete the required adapter matrix before ticket401 closure. The earlier passing receipt and this failure are separate evidence boundaries.

Memory disposition: **forbidden** — delegated tests/evidence work does not authorize external memory effects; primary owns integration closeout.
