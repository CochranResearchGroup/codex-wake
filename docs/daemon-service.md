# User Daemon Service

Codex Wake can run as a user-scoped systemd service. There are two modes:

- a repo-scoped `codex-waked` service for one wake root;
- a user-scoped `codex-wake-supervisor.service` for explicitly registered
  wake roots across Codex and OpenClaw workflows.

Both keep wake polling out of the model turn. The supervisor is preferred for
multi-repo and OpenClaw plugin-created wakes because it avoids one disabled
per-repo service silently stranding records.

Before relying on unattended delivery, check monitor readiness:

```bash
codex-wake --wake-root .codex/wake monitor check --json
codex-wake --wake-root .codex/wake doctor --json
```

`monitor_ready=true` means an active repo service matches the exact wake root,
or recent persistent daemon/supervisor health was observed.

## Repo-Scoped Service

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

## User Supervisor

Install the user-scoped supervisor:

```bash
codex-wake supervisor install
codex-wake supervisor status --all
```

Enroll a wake root explicitly:

```bash
codex-wake supervisor enroll --wake-root "$PWD/.codex/wake" --repo-root "$PWD"
codex-wake supervisor status --all
codex-wake --wake-root .codex/wake monitor check --json
```

The supervisor stores root registrations under:

```text
~/.config/codex-wake/roots.d/
```

It writes runtime health under:

```text
~/.local/state/codex-wake/monitors/
~/.local/state/codex-wake/supervisor/
```

If OpenClaw Gateway authentication is configured through environment-variable
references, import those variables into the user systemd manager before relying
on supervisor-fired OpenClaw wakes:

```bash
systemctl --user import-environment OPENCLAW_GATEWAY_TOKEN OPENCLAW_GATEWAY_PASSWORD
systemctl --user restart codex-wake-supervisor.service
```

Do not write token or password values into tracked docs, registry files, or
systemd units.

Stop and remove it:

```bash
codex-wake supervisor stop
codex-wake supervisor uninstall
```

Do not point the supervisor at arbitrary workspace scans. Every root must be
enrolled explicitly so ownership and retention stay inspectable.

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

For supervisor dogfood, enroll the root first and then run one bounded pass or
inspect the running service:

```bash
codex-wake supervisor enroll --wake-root "$PWD/.codex/wake" --repo-root "$PWD"
codex-wake supervisor run --once
codex-wake supervisor status --all
codex-wake --wake-root .codex/wake monitor check --json
```

## Limits

- This service does not install or trust Codex hooks for you.
- The service is user-scoped; it does not run before the user manager exists unless the host enables linger.
- The tmux target pane still needs to be a safe Codex TUI prompt when the wake fires.
