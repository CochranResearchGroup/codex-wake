# User Daemon Service

Codex Wake can run as a user-scoped systemd service for a single repo wake root. This keeps `codex-waked` polling without requiring an agent turn to leave a foreground shell open.

This is the preferred persistent path on hosts where `systemctl --user` is available.

## Install

Use the CLI-managed path:

```bash
codex-wake service install
codex-wake service status
codex-wake service logs --lines 50
```

Stop and remove the service:

```bash
codex-wake service stop
codex-wake service uninstall
```

The manual equivalent is to create a user service from the example and adjust paths if the repo is not at `~/workspace.local/codex-wake`:

```bash
mkdir -p ~/.config/systemd/user ~/.local/state/codex-wake
cp docs/examples/systemd/codex-wake.service ~/.config/systemd/user/codex-wake-codex-wake.service
systemctl --user daemon-reload
systemctl --user enable --now codex-wake-codex-wake.service
```

Check status:

```bash
systemctl --user status --no-pager codex-wake-codex-wake.service
tail -n 50 ~/.local/state/codex-wake/codex-wake.log
```

Stop and disable manually:

```bash
systemctl --user disable --now codex-wake-codex-wake.service
```

## Service Contract

The example service runs:

```bash
~/.local/bin/codex-waked \
  --wake-root ~/workspace.local/codex-wake/.codex/wake \
  --interval 1
```

It logs stdout and stderr to:

```text
~/.local/state/codex-wake/codex-wake.log
```

The service is intentionally repo-specific. Use a separate service name and wake root per repo.

## Dogfood Flow

1. Start the user service.
2. Open or identify a Codex TUI pane in tmux.
3. Confirm the repo-local `UserPromptSubmit` hook is visible and trusted with `/hooks`. If `/hooks` does not list the repo hook source, restart or resume Codex in this repo before testing daemon ack behavior.
4. Register a wake from the target pane environment, or set `TMUX_PANE` and `TMUX` explicitly for a disposable pane:

```bash
TMUX_PANE="%123" TMUX="/tmp/tmux-1000/default,0,0" codex-wake after 10s -- \
  "Dogfood wake. Verify the predicate and report whether the daemon resolved it."
```

5. Inspect the wake:

```bash
codex-wake list
find .codex/wake/acks -type f -maxdepth 1 -print
```

## Limits

- This service does not install or trust Codex hooks for you.
- The service is user-scoped; it does not run before the user manager exists unless the host enables linger.
- The tmux target pane still needs to be a safe Codex TUI prompt when the wake fires.
