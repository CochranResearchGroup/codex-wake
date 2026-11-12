# Actionable tab CLI outcomes (unreleased)

Workspace `tabs format enable` and `reenable` now restore a disabled workspace
preference. A global opt-out remains authoritative and reports why formatting
was not applied, with a configure command and a nonzero exit code. Reapply with
a new request ID after policy changes; old requests retain their original result.

Human tab mutation output starts with the actual outcome rather than journal
metadata. Partial session/monitor results retain failure details. `tabs format
status` is concise; `inspect` and explicit JSON retain full diagnostics.

Shell compatibility: disabled, unsupported, stale, unavailable and failed tab
results now exit `3`, alongside held, partial and uncertain outcomes. `tabs result`
returns the retained outcome's exit code. Intentional pause and successful
rollback continue to exit `0`; blocked enable/resume exits `3`. Full JSON journal
envelopes remain available and can still have outer `status: completed` when the
actual outcome is unsuccessful.

This source change does not activate formatting, start/restart monitors, install
a working package or alter the existing tmux incident containment.
