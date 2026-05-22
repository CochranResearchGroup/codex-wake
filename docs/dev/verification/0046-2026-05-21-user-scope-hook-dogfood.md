# User-Scope Hook Dogfood

Date: 2026-05-21

Request: prove the user-scope Codex Wake hook path from this live TUI session.

## Setup

User-scope hook definition:

```text
/home/ecochran76/.codex/hooks.json
```

Wake root:

```text
/home/ecochran76/workspace.local/codex-wake/.codex/wake
```

Target:

```text
tmux pane %202 on /tmp/tmux-1000/default
```

## Wake

Created a short live tmux wake:

```text
codex-wake --wake-root .codex/wake after 15s -- \
  'User-scope hook dogfood wake. Verify .codex/wake status and ack evidence for this wake id, then report whether the user-scope hook path worked and stop.'
```

Wake id:

```text
wake_20260522_002354_a43f
```

Systemd one-shot dispatch was scheduled:

```text
systemd-run --user --unit=codex-wake-user-hook-dogfood- \
  --on-active=25s /home/ecochran76/.local/bin/codex-waked \
  --wake-root /home/ecochran76/workspace.local/codex-wake/.codex/wake \
  --once --ack-timeout 20
```

The unit name lost the wake-id suffix because the parser expected an older
`id=` output shape. The transient timer still ran and dispatched the wake.

## Evidence

The first daemon pass pasted the wake prompt but timed out before observing the
ack:

```text
checked=1 fired=1 failed=0 pending=0 dispatched=1 submitted=0 requeued=1
```

The live TUI received:

```text
WAKE_TRIGGER_ID=wake_20260522_002354_a43f
Resume the scheduled wake task.
```

The hook added wake context into the turn, proving hook execution. Because both
the user-scope hook and this repo's project hook were active, Codex injected the
same wake developer context twice.

The ack file was written:

```json
{
  "session_id": "019e3c37-6dbf-70a0-bbaf-0668ed98ecc3",
  "submitted_at": "2026-05-22T00:25:02Z",
  "turn_id": "019e4d10-60b7-71e3-86ce-3b4b9e507ef0",
  "wake_id": "wake_20260522_002354_a43f"
}
```

A manual one-shot daemon reconciliation observed the ack and moved the record
to `submitted`:

```text
checked=1 fired=1 failed=0 pending=0 dispatched=1 submitted=1 requeued=0
```

Submitted record events:

```text
created
predicate_matched
dispatch_attempt attempt=1
ack_timeout attempt=1
requeued attempt=1
predicate_matched
dispatch_attempt attempt=2
ack_observed
```

The dogfood record was archived:

```text
archived wake_20260522_002354_a43f /home/ecochran76/workspace.local/codex-wake/.codex/wake/archive/wake_20260522_002354_a43f.json
```

Final wake-root status:

```json
{
  "active_total": 0,
  "archived_total": 10,
  "terminal_total": 0
}
```

## Result

Pass with caveat. The user-scope hook path worked in this live TUI: the wake
prompt landed, `UserPromptSubmit` hook context was injected, ack evidence was
written, and the durable wake record reached `submitted`.

The caveat is duplicate context injection when the same hook is installed at
both user scope and project scope. Future hook installation UX should detect
and explain this overlap, or provide an operator choice to use one source.
