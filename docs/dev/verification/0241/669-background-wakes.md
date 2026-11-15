# Ticket 669: background wake routing

Status: prepared; live acceptance has not run. The coordinator serializes native
acceptance and must release the live slot before execution. Ticket 669 remains
open until both due events and cleanup are demonstrated.

The opt-in `scripts/connector_background_wakes_acceptance.py` uses one disposable
native conversation with persisted setup history and one owned TUI on the actual
default tmux socket. It registers two separate interval schedules through the
public OAuth/MCP connector. Both explicitly select `session_mode=background`,
60-second cadence, count=1, missed=skip with 30-second maximum lateness,
overlap=skip and a 45-second delivery window. The first due event must use the
original live attachment. The script then closes only its owned tab; the second
due event must use the same saved UUID without creating another visible tab.

Each case requires one completed schedule occurrence, accepted native delivery,
exact persisted selected route (`existing_tab` or `background`), one matching
native user message carrying its wake ID, and the final reply in that same native
turn. Both schedules are cancelled with the current revision. The disposable
thread is archived, the separate exact-target OAuth grant is revoked and checked
for HTTP 401, and the owned TUI process is checked for exit. Raw synthetic runtime
receipts and provenance stay in the user state directory outside Git.

The script adapts readiness from ticket 666 at
`1de611fa91a6a17114b2d0ea82920f45c5b880a7`. It creates no fixture framework and
changes no product code, permission policy, trust configuration or deployment.

## Route prerequisites

Installed dev28 `wake_mode_runtime.py` selects `LiveWakeRestorer` only for
`reopen_live` when absent. Background mode selects the same saved conversation
with `resume_policy=same_thread`, then sends native `turn/start` for that UUID
through the app server. It does not require the visible-restoration profile.
`permission_wake.decorate_policy` preserves the version 1 wake policy while the
common policy store is inactive; activating that store is a separate action and
is not part of this script.

Both routes still require a complete, unambiguous recipient observation. A live
recipient requires one `metadata_matched` attachment; an absent recipient must
have no attachment. The coordinator owns the observed session inventory deadline
repair and any qualification/deployment. No runtime bypass is authorized.

## Local preparation checks

Frozen source base: `882aae8007e71cc2641c66a742e340e6cf007310`.

- `python -m py_compile scripts/connector_background_wakes_acceptance.py`: PASS.
- Installed dev28 Python `scripts/connector_background_wakes_acceptance.py --help`:
  PASS; imports and argument parser only, no native/OAuth effects.
- `git diff --check`: PASS.

These preparation checks do not prove live routing. Hosted GitHub Actions is
intentionally skipped under the operator's CI cost policy. No hosted environment
is used; the eventual opt-in run must identify the installed prefix and receipt.

Memory disposition: forbidden; the task explicitly excludes memory writes.

## Live-slot preflight, 2026-11-15 UTC

The coordinator released the sole live slot with dev28 unchanged. Installed
`read_monitor_health(controller)` returned no health record (`{}`), and
`probe_managed_reader_capability(controller)` returned `None`. The script now
checks the same readiness fields used by schedule receipts before creating any
native target or grant. Its opt-in invocation exited with
`persistent_monitor_not_ready`; zero targets, grants and schedules were created.
The private receipt is
`~/.local/state/codex-wake/connector-background-wakes/live-preflight-20261115.json`.

This is an unmet runtime prerequisite, not a demonstrated background routing
failure. Neither due case ran. No global worker was started because doing so
could dispatch unrelated pending wakes. The coordinator owns monitor activation
and any service restart. No session-observation timeout defect is established
by this preflight.
