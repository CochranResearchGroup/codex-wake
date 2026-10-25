# Organizing managed tabs

`tabs preview` records a proposed order for one exact tmux session. Activity-first
is the default: working, awaiting-human, auth-required, ready, disconnected. A
repository identity and original position break ties. `--mode repository` groups
by repository first, then activity. Git worktrees share the canonical Git common
directory identity; titles and CWD resemblance do not establish repository identity.

Focused windows, explicit `--pin @ID` windows, windows linked into other sessions,
mixed-repository split windows and any window with unqualified panes retain their
indices. Pinned slots can split an otherwise contiguous repository group. The
preview identifies exact window IDs, target indices and pin reasons.

The local CLI requires an existing verified bus operator capability for apply and
undo. Permission checks use `workspace.order` and `workspace.undo` at admission
and before each effect, retaining mandatory denials. Model MCP use is limited to
preview and inspection until current caller/workspace authority is integrated.
Read-only preview grants no effect authority.

Example after shared CLI registration:

```sh
codex-wake tabs preview --socket-path /absolute/private/tmux.sock --session-id '$0' \
  --bus-root /absolute/bus --operator-capability /absolute/operator-capability --json
codex-wake tabs apply --socket-path /absolute/private/tmux.sock --session-id '$0' \
  --bus-root /absolute/bus --operator-capability /absolute/operator-capability \
  --plan-id plan_ID --json
```

Use the exact IDs returned by preview. The private wake-root `tab-organization`
directory retains plans and operation receipts across process restart. Apply
requires the complete prelayout fingerprint, including exact pane/process/native
bindings, semantic activity, focus, repository identity and permission revision,
to remain unchanged. A stale plan is refused before effects; preview again.

Each swap preserves the set of window indices and stable pane/window IDs. tmux
3.4 changed session focus during isolated `swap-window -d` testing, so the same
command queue explicitly restores the previously focused window. Every resulting
layout is checked. No terminal input, process restart, route rewrite or native
turn is submitted. Pending routes must identify stable recipients; this operation
does not reinterpret numeric tab selectors as durable conversation identity.

A pending journal entry precedes each submission. Timeout, lost response or a
changed postcondition records uncertainty. Repeating apply returns the original
receipt without submitting another swap. `show` reads the journal, including when
the server is unavailable. A pending receipt after controller death means the
effect is unresolved; it must not be retried. A fresh preview can supply current
read-only layout evidence, but does not resolve historical effect provenance.

Undo is conditional: it requires a fully observed applied receipt and the exact
recorded postlayout/bindings. New human layout/focus changes hold undo. Partial or
uncertain receipts cannot be undone automatically. Undo itself journals before
effects and has the same uncertainty rules. No blind compensation is attempted.

Each operation has a maximum 30-second budget; inventory is capped at 4096 panes
and 256 enrolled agents. Unknown/unsupported runtime evidence pins windows. The
built-in observer supports qualified enrolled Codex metadata; unsupported Grok
bindings remain pinned unless a host supplies an equivalent qualified observer.
No automatic sorting or cross-server/session move is provided.

The lock serializes cooperating Codex Wake writers. tmux offers no established
compare-and-swap against arbitrary human commands: observations and mutations have
a small race window, and focus restoration is not an OS-level transaction. An
unexpected result stops with an uncertain receipt rather than overwriting again.
Provider-free private-socket tests are source acceptance, not permission to reorder
existing operator tabs or proof of installed provider behavior.
