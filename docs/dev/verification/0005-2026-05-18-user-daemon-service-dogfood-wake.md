# User Daemon Service And Dogfood Wake Verification

Date: 2026-05-18
Branch: `main`

## Host Capability

Verified user systemd is available on this workstation:

```bash
systemctl --user is-system-running
loginctl show-user "$USER" -p Linger
```

Observed:

```text
degraded
Linger=yes
```

The user manager is usable even though unrelated user units keep the aggregate state degraded.

## Service Path

Selected a user-scoped systemd service for repo-local daemon operation.

Tracked docs:

```text
docs/daemon-service.md
docs/examples/systemd/codex-wake.service
```

Installed for this repo:

```bash
mkdir -p ~/.config/systemd/user ~/.local/state/codex-wake
cp docs/examples/systemd/codex-wake.service ~/.config/systemd/user/codex-wake-codex-wake.service
systemctl --user daemon-reload
systemctl --user enable --now codex-wake-codex-wake.service
```

Observed:

```text
active
codex-waked --wake-root /home/ecochran76/workspace.local/codex-wake/.codex/wake --interval 1
```

## Logging Fix

The first service dogfood resolved a wake, but the service log was empty because the continuous daemon loop did not print poll results. Added activity logging for non-empty poll results and bumped the package to `0.1.1`.

Verified installed daemon code includes:

```text
format_poll_result
poll_result_has_activity
print(format_poll_result(result), flush=True)
```

## Dogfood Wake

Started a disposable tmux-hosted Codex pane:

```bash
SESSION="codex-wake-dogfood-20260518210919"
tmux new-session -d -s "$SESSION" -c /home/ecochran76/workspace.local/codex-wake
tmux send-keys -t "$PANE" "codex -C /home/ecochran76/workspace.local/codex-wake --no-alt-screen" Enter
```

Created a wake targeted at that pane while the user service was running:

```bash
TMUX_PANE="$PANE" TMUX="$SOCKET,0,0" codex-wake after 5s -- \
  "P12 v0.1.1 logged service dogfood wake. Verify the predicate is true, report that the systemd daemon resolved it, then stop."
```

Observed:

```text
wake_20260519_020927_a301 /home/ecochran76/workspace.local/codex-wake/.codex/wake/pending/wake_20260519_020927_a301.json
ack observed after 13s
```

Ack:

```json
{
  "session_id": "019e3dfe-7f5e-7532-bb9f-d5246edb3663",
  "submitted_at": "2026-05-19T02:09:38Z",
  "turn_id": "019e3dfe-d9c6-7b62-ab07-950e5d360a25",
  "wake_id": "wake_20260519_020927_a301"
}
```

Submitted record:

```text
status: submitted
events: created -> predicate_matched -> dispatch_attempt -> ack_observed
target: tmux /tmp/tmux-1000/default pane %217
```

Service log:

```text
checked=1 fired=0 failed=0 pending=1 dispatched=0 submitted=0 requeued=0
checked=1 fired=0 failed=0 pending=1 dispatched=0 submitted=0 requeued=0
checked=1 fired=0 failed=0 pending=1 dispatched=0 submitted=0 requeued=0
checked=1 fired=0 failed=0 pending=1 dispatched=0 submitted=0 requeued=0
checked=1 fired=1 failed=0 pending=0 dispatched=1 submitted=1 requeued=0
```

Codex pane evidence:

```text
UserPromptSubmit hook (completed)
Wake id: wake_20260519_020927_a301
Original wake prompt: P12 v0.1.1 logged service dogfood wake...
```

The disposable pane also showed an unrelated `ragmail` MCP startup timeout. That did not block wake submission, hook ack, or daemon resolution.

## Stop And Cleanup

Stopped and disabled the user service:

```bash
systemctl --user disable --now codex-wake-codex-wake.service
systemctl --user is-active codex-wake-codex-wake.service
```

Observed:

```text
inactive
```

Killed the disposable tmux session. Runtime wake state remains ignored under `.codex/wake/` and can be removed after evidence capture.
