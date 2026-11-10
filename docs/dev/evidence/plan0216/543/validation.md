# Ticket 543 qualification

Base source: `5de58e5` on `feat/observer-tmux-543`. Implements the frozen P216
adapter contract, with the primary owner's requested additive pane_title,
pane_current_path and pane_tty metadata. No production sockets were contacted.

Commands and outcomes:

- RED: `PYTHONPATH=src python -m unittest discover -s tests -p test_tab_tmux_feed.py`
  failed with missing `codex_wake.tab_tmux_feed` before implementation.
- GREEN: the same focused selection with `/tmp/wake216-py311/bin/python`:
  four tests passed, 2.359 seconds.
- GREEN: the same focused selection with `/tmp/wake216-py312/bin/python`:
  four tests passed, 2.245 seconds.
- `/tmp/wake216-py312/bin/python -m ruff check --select F821,F822,F823`
  for the new module, test and qualification script: passed.
- `git diff --check`: passed.
- `PYTHONPATH=src /tmp/wake216-py312/bin/python docs/dev/evidence/plan0216/543/qualify.py`:
  stock tmux 3.4, 20 rename events, p95 0.004595 seconds including the external
  rename command. Startup measured separately at 0.004642 seconds. Exact receipt
  is native-tmux-acceptance.json. Pane identity/layout/focus preserved and owned
  control client reaped. This is a private native protocol qualification, not
  the parent ticket's 100-tab workload or installed/live-host acceptance.

The retained client uses no-output, ignore-size and read-only flags. Only fixed
metadata list-panes and refresh-client subscriptions are submitted after attach.
A read-only tmux client flag is not treated as a general command authorization
boundary. The code's finite command set is the restriction. Labels never become
commands. Name escaping matches the existing TmuxTransport snapshot, including
its tmux-provided visual escapes for backslashes/control characters.

Socket identity, session existence, bounded framed output, command deadlines and
own-child termination fence the source. Reconnection emits a new baseline epoch.
One-second reconnect backoff and metadata subscriptions avoid periodic inventory
commands when no metadata changes. Subscription cadence can add up to about one
second for changes without a direct tmux control notification. No per-pane child
is created. The existing snapshot owner does not expose process birth; this
adapter supplies pane PID and metadata, leaving birth qualification to its owner.

No hosted CI ran; this local Linux runtime uses the installed stock tmux binary
and both supported Python versions. Parent integration, installed package and
existing-host gates remain with the primary owner. No issue closure, merge,
deployment, production formatting mutation or provider request was performed.
Memory disposition is owned by the primary closeout; this worker made no write.
