# User-Scope Install And Operator Smoke

Date: 2026-05-18
Branch: `main`

## Install

Direct `python -m pip install --user .` was blocked by the workstation's uv-managed Python environment:

```text
error: externally-managed-environment
This Python installation is managed by uv and should not be modified.
```

Used the safer user-scoped tool install path:

```bash
uv tool install --force .
```

Result:

```text
Installed 2 executables: codex-wake, codex-waked
```

## Installed Commands

```bash
command -v codex-wake
command -v codex-waked
uv tool list
```

Observed:

```text
/home/ecochran76/.local/bin/codex-wake
/home/ecochran76/.local/bin/codex-waked
codex-wake v0.1.0
- codex-wake
- codex-waked
```

## Smoke

Verified:

```bash
codex-wake --help
codex-waked --once --no-dispatch --wake-root /tmp/codex-wake-user-install-empty
```

Observed:

```text
checked=0 fired=0 failed=0 pending=0 dispatched=0 submitted=0 requeued=0
```

## CLI Lifecycle

Verified with PATH-resolved `codex-wake`:

```bash
TMUX_PANE='%11' TMUX='/tmp/tmux-1000/default,123,0' codex-wake --wake-root /tmp/codex-wake-user-install-smoke file .codex/events/pytest.done -- 'Read pytest log'
codex-wake --wake-root /tmp/codex-wake-user-install-smoke list
codex-wake --wake-root /tmp/codex-wake-user-install-smoke cancel <wake-id>
codex-wake --wake-root /tmp/codex-wake-user-install-smoke archive <wake-id>
```

Observed create, list, cancel, and archive all succeeded.

## Daemon Predicate

Verified with PATH-resolved `codex-waked`:

```bash
TMUX_PANE='%11' TMUX='/tmp/tmux-1000/default,123,0' codex-wake --wake-root /tmp/codex-wake-user-install-daemon at '2026-05-18T00:00:00Z' -- 'Due wake'
codex-waked --wake-root /tmp/codex-wake-user-install-daemon --once --no-dispatch
```

Observed:

```text
checked=1 fired=1 failed=0 pending=0 dispatched=0 submitted=0 requeued=0
/tmp/codex-wake-user-install-daemon/firing/<wake-id>.json
```

## Hook And App-Server Target

Verified the repo-local hook wrapper writes an ack and returns hook-specific output from a JSON payload.

Verified app-server target creation:

```bash
codex-wake --wake-root /tmp/codex-wake-user-app after --app-server-thread-id thread_user_scope 1m -- 'App server user-scope smoke'
codex-wake --wake-root /tmp/codex-wake-user-app list --json
```

Observed target:

```json
{
  "endpoint": "stdio://",
  "thread_id": "thread_user_scope",
  "transport": "app-server"
}
```

## Remaining Live Smoke

Live tmux injection into a disposable Codex TUI pane remains the best next operator smoke. It needs an intentionally disposable tmux pane running Codex with the repo hook configured so the daemon can paste the canonical prompt and observe the hook ack without disturbing a human session.
