# Ticket #667: this-session-only wake lifecycle

Scope: approved spec #663, ticket #667. This lane owns only its opt-in live
acceptance script and this evidence summary. The integration owner maintains
ledger 0241, product repairs, deployment and issue closure.

Source base: `882aae8007e71cc2641c66a742e340e6cf007310`.
Installed acceptance prefix:
`~/.local/share/codex-wake/releases/0.22.0.dev28-1fb9180`.

The script addresses one newly seeded native conversation, resumes its exact
executable in an owned tmux session on the existing supported server, then uses
a separately scoped OAuth grant through the deployed HTTPS MCP endpoint. Tokens
remain in memory. Receipts and synthetic native metadata stay outside Git.

Declared experiment: `session_only`; interval starts 45 seconds after definition,
30-second cadence; count two; missed policy skip with maximum lateness 15 seconds;
overlap skip; delivery window 15 seconds. Missing mode must be refused before
registration. A detached tmux client must leave the schedule enabled. Destroying
only the owned recipient session must cancel the schedule with `session_closed`;
observation past the first due event must show no occurrence or new native input.
The script cancels its exact schedule on failure, archives its conversation,
revokes its grant and removes its own session. It never restarts native services.

Run explicitly with the installed prefix's Python:

```sh
PREFIX/bin/python scripts/connector_session_only_acceptance.py --run-live
```

## Evidence status

Live acceptance is **BLOCKED**, not passed. Ticket #667 remains open. Initial attempts exposed setup
constraints rather than proving scheduler behavior: native attachment requires
matching native conversation name and actual pane working directory; remote
resume must not override permissions. Two initial unattached-recipient attempts
were cleaned up without a schedule or grant. Subsequent locator/read failures
were retained privately; another probe was interrupted at the coordinator's
serialization boundary and its conversation/session were cleaned up. No passing
scheduler claim follows from these attempts.

Private receipts are under
`~/.local/state/codex-wake/connector-acceptance-spec/session-only-*.json`.

Focused local checks: `python -m py_compile
scripts/connector_session_only_acceptance.py` passed. Installed-prefix Python
`--help` passed. System Python lacks installed connector dependency `httpx2`;
therefore the actual live command uses the installed environment. This opt-in
network/native acceptance is outside the default local test lane. Hosted GitHub
CI was not run under the repository CI cost policy.

## Serialized deployed result

With a persistent uniquely named native client, the exact disposable conversation
was seeded, named, resumed in its own default-server tmux session, and observed as
`metadata_matched` from real exact-thread metadata and native tmux inventory.
The protected `wake_wakes_schedules_register` operation correctly refused missing
`session_mode` with `explicit_schedule_fields_required`. The full explicit request
then failed with `MCPError: session_owner_unverified`. No schedule was admitted.
Private evidence: `session-only-1565a1b8.json` under the directory above; the earlier
`session-only-0b40d1f0.json` retains the initial expected-refusal handling failure.
The exact owned UUID is retained privately for `--reuse-thread` qualification;
this option verifies the expected disposable name and scratch directory.

Observed cleanup: temporary grant revoked; disposable thread archived; owned tmux
session absent; no monitor or scheduler process launched; no admitted timer. The
script's native connection closed. The original default tmux session was retained.
Two initial standalone temporary-directory trust entries created by this lane
were removed exactly; other trust entries were preserved.

Small repair proposal for the integration owner: inspect `bind_mode` in
`wake_session_modes.py`, which calls broad `sessions.observe` with a five-second
bound. Exact-thread native evidence plus the supported tmux inventory was
sufficient to match the recipient, while the protected registration failed its
owner check. Narrow owner observation to the exact recipient while preserving
complete tmux evidence, process birth, native name and working directory checks.
This is a diagnosis proposal, not proof of the refusal's internal cause. Do not
inject a session owner, native principal or mock snapshot to satisfy acceptance.
Re-run this same owned conversation after any repair is separately qualified.
Detachment survival, closure cancellation and past-due non-delivery remain
unverified because registration did not complete.

Memory disposition: `forbidden`; the coordinator explicitly prohibited memory
writes. A private non-write receipt records this boundary outside Git.
