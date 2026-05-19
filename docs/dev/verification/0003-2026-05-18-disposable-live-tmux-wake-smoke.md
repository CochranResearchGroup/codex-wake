# Disposable Live Tmux Wake Smoke

Date: 2026-05-18
Branch: `main`

## Target

Created a disposable tmux session and pane:

```bash
SESSION="codex-wake-smoke-20260518193054"
tmux new-session -d -s "$SESSION" -c /home/ecochran76/workspace.local/codex-wake
PANE=$(tmux display-message -p -t "$SESSION":0.0 '#{pane_id}')
tmux send-keys -t "$PANE" "codex -C /home/ecochran76/workspace.local/codex-wake --no-alt-screen" Enter
```

Observed Codex TUI in the disposable pane:

```text
OpenAI Codex (v0.130.0)
directory: ~/workspace.local/codex-wake
permissions: YOLO mode
```

## Hook Trust Gate

The first live dispatch pasted the canonical wake prompt, but Codex blocked the hook until review:

```text
1 hook needs review before it can run. Open /hooks to review it.
```

Reviewed the disposable pane's `/hooks` screen and trusted the repo-local `UserPromptSubmit` hook from `.codex/hooks.json`.

## Submit Timing Fix

The first daemon-owned submit attempts left the two-line wake prompt in the Codex composer. Manual `C-m` after the paste delay submitted it and produced the ack, so the tmux injector was changed to:

- paste the canonical prompt
- wait briefly for the paste to settle
- send `C-m`
- wait briefly
- send `C-m` again

This matches the observed Codex multiline composer behavior in tmux.

## Successful Smoke

Created a due wake targeted at the disposable pane:

```bash
PANE=$(cat /tmp/codex-wake-smoke-pane)
SOCKET=$(tmux display-message -p -t "$PANE" '#{socket_path}')
rm -rf .codex/wake
TMUX_PANE="$PANE" TMUX="$SOCKET,0,0" PYTHONPATH=src python -m codex_wake.cli after 1s -- \
  "This is disposable wake smoke P10 with delayed daemon submit. First verify whether the task is already complete; if complete, report that and stop."
sleep 2
PYTHONPATH=src python -m codex_wake.daemon --once --wake-root .codex/wake --ack-timeout 20
```

Observed daemon result:

```text
wake_20260519_003526_bfaa /home/ecochran76/workspace.local/codex-wake/.codex/wake/pending/wake_20260519_003526_bfaa.json
checked=1 fired=1 failed=0 pending=0 dispatched=1 submitted=1 requeued=0
```

Observed ack:

```json
{
  "session_id": "019e3da4-99f8-7882-9e16-75616f27ed3a",
  "submitted_at": "2026-05-19T00:35:28Z",
  "turn_id": "019e3da8-bb77-7891-aff0-93f01f94c0d6",
  "wake_id": "wake_20260519_003526_bfaa"
}
```

Observed submitted record:

```text
.codex/wake/submitted/wake_20260519_003526_bfaa.json
status: submitted
events: created -> predicate_matched -> dispatch_attempt -> ack_observed
target: tmux /tmp/tmux-1000/default pane %212
```

Observed pane context:

```text
UserPromptSubmit hook (completed)
hook context: A scheduled wake trigger fired.
Wake id: wake_20260519_003526_bfaa
Original wake prompt: This is disposable wake smoke P10 with delayed daemon submit...
```

## Cleanup

Interrupted the disposable Codex wake turn after ack observation and killed the disposable tmux session:

```bash
tmux kill-session -t codex-wake-smoke-20260518193054
```

Runtime wake state was removed after evidence capture. `.codex/wake/` remains ignored for future smokes.

## Installed Tool Refresh

Refreshed the user-scoped tool install after the injector submit timing fix:

```bash
uv tool install --force .
command -v codex-wake
command -v codex-waked
codex-waked --once --no-dispatch --wake-root /tmp/codex-wake-post-p10-empty
```

Observed:

```text
Installed 2 executables: codex-wake, codex-waked
/home/ecochran76/.local/bin/codex-wake
/home/ecochran76/.local/bin/codex-waked
checked=0 fired=0 failed=0 pending=0 dispatched=0 submitted=0 requeued=0
```
