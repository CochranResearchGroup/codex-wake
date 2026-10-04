# Bounded multiroot and resource qualification

Parent: Plan 0112 / Plan 0101 / issue #181.
Baseline: 0049a2a19925e33b7bba6031e530691f09a10e64.

## Scope and first verdict

Reproducible harness: scripts/a2a_resource_qualification.py. All buses, enrolled
roots, bodies and actor identities are synthetic and temporary. Default production
mailbox limits remain unchanged. Fake clock advances seven seconds per admission
to respect the ten-per-minute limit; this does not measure real-time soak.

Thresholds frozen before measurement: 100 requests, 20 replies, ten fresh
subprocess reopen checks, 30 seconds total, 15 seconds per subprocess capped by
remaining total time, 10 MiB store, FD growth at most two, no residual children.
Installed CI wraps the harness in a 40-second hard watchdog.

First run failed at copied-root error assertion: harness expected copied_store
but runtime correctly returned bus_identity_mismatch. Corrected the assertion;
no runtime repair. Preserve this failed harness verdict separately from corrected
qualification, with one implementation correction and no hidden retry.

## Acceptance evidence

100 explicit inbox-only requests retained immutable identity on duplicate intent,
recipient FIFO pages returned the exact 100 IDs with contiguous sequences. Twenty
recipient retrievals/accepted dispositions and correlated replies completed; sender
retrieval preserved reply contents. Ten fresh processes re-opened the same canonical
bus and verified inbox order. Cross-root-disabled bus rejected admission without
an envelope; explicitly enabled bus allowed it. Copied-root bus activation refused.
120 envelopes, zero transport attempts. Temporary fixture removed on exit.

Commands and recorded metrics:

- Source Python 3.12: {"accepted": true, "after": {"children": [], "fd_count": 5}, "before": {"children": [], "fd_count": 5}, "copied_root_denied": true, "cross_root_denied": true, "dispatch_attempts": 0, "elapsed_seconds": 4.032, "fixture_removed": true, "live_delivery_qualified": false, "schema_version": 1, "store_bytes": 565248, "synthetic": true, "thresholds": {"elapsed_seconds": 30, "fd_growth": 2, "reopen_processes": 10, "replies": 20, "requests": 100, "residual_children": 0, "store_bytes": 10485760}}
- Source Python 3.11: {"accepted": true, "after": {"children": [], "fd_count": 5}, "before": {"children": [], "fd_count": 5}, "copied_root_denied": true, "cross_root_denied": true, "dispatch_attempts": 0, "elapsed_seconds": 2.866, "fixture_removed": true, "live_delivery_qualified": false, "schema_version": 1, "store_bytes": 565248, "synthetic": true, "thresholds": {"elapsed_seconds": 30, "fd_growth": 2, "reopen_processes": 10, "replies": 20, "requests": 100, "residual_children": 0, "store_bytes": 10485760}}
- Isolated installed Python 3.12: {"accepted": true, "after": {"children": [], "fd_count": 5}, "before": {"children": [], "fd_count": 5}, "copied_root_denied": true, "cross_root_denied": true, "dispatch_attempts": 0, "elapsed_seconds": 2.169, "fixture_removed": true, "live_delivery_qualified": false, "schema_version": 1, "store_bytes": 565248, "synthetic": true, "thresholds": {"elapsed_seconds": 30, "fd_growth": 2, "reopen_processes": 10, "replies": 20, "requests": 100, "residual_children": 0, "store_bytes": 10485760}}

Source command: PYTHONPATH=src python3 scripts/a2a_resource_qualification.py.
Python 3.11 uses the same command with python3.11. Installed command:
/tmp/codex-wake-p63-arming-venv/bin/python scripts/a2a_resource_qualification.py
with no source PYTHONPATH. Runtime API comes from its installed site-packages;
main runtime is unchanged since that wheel. Final diff and script compile pass.
Active planning audit passes with the existing exact legacy baseline.

## Remaining requirements

This advances synthetic multiroot/restart and bounded resource acceptance only.
Live two-agent delivery, actual suspension, managed-service restart, resource soak,
production retention-pin acknowledgement, compact tombstones, physical compaction
and release/install/rollback remain unqualified. Current Plan 0101 remains OPEN.
Named disposable live scope is still awaiting operator answer; the prepared gate
is verification 0103. Never use existing idle threads by default.
