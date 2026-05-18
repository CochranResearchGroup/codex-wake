# Installed Runtime Verification

Date: 2026-05-18
Branch: `p02-agent-facing-cli`

## Environment

- Python virtualenv: `/tmp/codex-wake-venv`
- Install command: `/tmp/codex-wake-venv/bin/python -m pip install .`
- Smoke roots:
  - `/tmp/codex-wake-installed-smoke`
  - `/tmp/codex-wake-daemon-installed`
  - `/tmp/codex-wake-app-installed`

## Commands Verified

```bash
/tmp/codex-wake-venv/bin/codex-wake --help
/tmp/codex-wake-venv/bin/codex-waked --once --no-dispatch --wake-root /tmp/codex-wake-installed-smoke
```

Result:

```text
checked=0 fired=0 failed=0 pending=0 dispatched=0 submitted=0 requeued=0
```

## CLI Lifecycle Smoke

```bash
TMUX_PANE='%11' TMUX='/tmp/tmux-1000/default,123,0' \
  /tmp/codex-wake-venv/bin/codex-wake --wake-root /tmp/codex-wake-installed-smoke \
  file .codex/events/pytest.done -- 'Read pytest log'

/tmp/codex-wake-venv/bin/codex-wake --wake-root /tmp/codex-wake-installed-smoke list
/tmp/codex-wake-venv/bin/codex-wake --wake-root /tmp/codex-wake-installed-smoke cancel <wake-id>
/tmp/codex-wake-venv/bin/codex-wake --wake-root /tmp/codex-wake-installed-smoke archive <wake-id>
```

Observed:

```text
ID	STATUS	PREDICATE	NEXT
<wake-id>	pending	file_exists	<timestamp>
cancelled <wake-id> ...
archived <wake-id> ...
```

## Daemon Predicate Smoke

```bash
TMUX_PANE='%11' TMUX='/tmp/tmux-1000/default,123,0' \
  /tmp/codex-wake-venv/bin/codex-wake --wake-root /tmp/codex-wake-daemon-installed \
  at '2026-05-18T00:00:00Z' -- 'Due wake'

/tmp/codex-wake-venv/bin/codex-waked --wake-root /tmp/codex-wake-daemon-installed --once --no-dispatch
```

Observed:

```text
checked=1 fired=1 failed=0 pending=0 dispatched=0 submitted=0 requeued=0
/tmp/codex-wake-daemon-installed/firing/<wake-id>.json
```

## Hook Smoke

```bash
python -c 'import json, sys; print(json.dumps({"prompt":"WAKE_TRIGGER_ID=wake_installed\nResume","cwd":sys.argv[1],"turn_id":"turn_installed","session_id":"session_installed"}))' "$tmp" \
  | ./.codex/hooks/wake_user_prompt_submit.py
```

Observed:

```json
{
  "hookSpecificOutput": {
    "additionalContext": "Wake trigger wake_installed was submitted, but its trigger file was not found. Inspect .codex/wake before continuing, and ask the user if the wake state is ambiguous.",
    "hookEventName": "UserPromptSubmit"
  }
}
```

Ack file written:

```json
{
  "session_id": "session_installed",
  "turn_id": "turn_installed",
  "wake_id": "wake_installed"
}
```

## App-Server Target Smoke

```bash
/tmp/codex-wake-venv/bin/codex-wake --wake-root /tmp/codex-wake-app-installed \
  after --app-server-thread-id thread_installed 1m -- 'App server installed smoke'

/tmp/codex-wake-venv/bin/codex-wake --wake-root /tmp/codex-wake-app-installed list --json
```

Observed target:

```json
{
  "endpoint": "stdio://",
  "thread_id": "thread_installed",
  "transport": "app-server"
}
```

## Limitations

- Live tmux dispatch was not attempted because this smoke did not create a disposable Codex TUI pane target. The injector path is covered by focused tests with a fake tmux runner.
- Live app-server `thread/resume` plus `turn/start` was not attempted against a real Codex thread id. The stdio app-server payload path is covered by focused tests with a fake app-server client, and target record creation is installed-smoked.
- WebSocket app-server dispatch remains intentionally unimplemented because official docs mark it experimental and unsupported; non-loopback use requires auth and TLS.
