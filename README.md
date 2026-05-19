# Codex Wake

Codex Wake is a local wake spooler for TUI-bound Codex agents. It lets an agent register a durable wake request, lets a deterministic daemon wait for the trigger, and resumes a Codex TUI pane by submitting a short wake prompt.

The v0.1.0 MVP supports:

- `codex-wake after`, `codex-wake at`, and `codex-wake file`
- durable JSON wake records under `.codex/wake/`
- `codex-waked` polling and dispatch
- tmux pane injection with `UserPromptSubmit` hook ack
- terminal-state archival with `codex-wake archive`
- experimental stdio app-server targeted wake records

## Requirements

- Python 3.11+
- `tmux` for TUI-bound wake dispatch
- Codex CLI with hook support
- `uv` for the recommended user-scoped install path

## Install

From a checked-out repo:

```bash
uv tool install --force .
```

After the first release tag exists, a fresh machine can install from GitHub:

```bash
uv tool install git+https://github.com/CochranResearchGroup/codex-wake.git@v0.2.0
```

Verify the installed commands:

```bash
command -v codex-wake
command -v codex-waked
command -v codex-wake-hook
codex-wake --help
codex-waked --once --no-dispatch --wake-root /tmp/codex-wake-empty
```

## Hook Setup

Codex Wake needs a `UserPromptSubmit` hook so the daemon can confirm that its pasted wake prompt was actually submitted and so Codex receives the full wake context from the trigger JSON.

For an installed tool, add this to the target repo's `.codex/hooks.json`:

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "codex-wake-hook",
            "timeout": 5,
            "statusMessage": "Checking wake trigger"
          }
        ]
      }
    ]
  }
}
```

This repo tracks a source-tree hook wrapper at `.codex/hooks/wake_user_prompt_submit.py` and a matching `.codex/hooks.json` for development. Codex may require a one-time `/hooks` review before a new repo-local hook runs.

## Basic Usage

Run these commands inside a tmux pane that is hosting the Codex TUI you want to wake. `codex-wake` captures `TMUX_PANE` and the tmux socket from the environment.

Wake after a duration:

```bash
codex-wake after 45m -- "Continue the migration. First inspect .codex/events/migration.log."
```

Wake at an absolute timestamp:

```bash
codex-wake at "2026-05-18T17:30:00-05:00" -- "Check whether the release branch is ready."
```

Wake when a marker file exists:

```bash
mkdir -p .codex/events
(
  pytest -q > .codex/events/pytest.log 2>&1
  touch .codex/events/pytest.done
) &
codex-wake file .codex/events/pytest.done -- \
  "Pytest finished. Read .codex/events/pytest.log and continue from the failing tests."
```

Run the daemon once:

```bash
codex-waked --once
```

Run the daemon in polling mode:

```bash
codex-waked --interval 5
```

Manage a repo-local user service:

```bash
codex-wake service install
codex-wake service status
codex-wake service logs --lines 50
codex-wake service stop
codex-wake service uninstall
```

Inspect and manage wakes:

```bash
codex-wake list
codex-wake list --json
codex-wake show <wake-id>
codex-wake cancel <wake-id>
codex-wake archive <wake-id>
codex-wake archive --all-terminal
```

## Runtime State

By default, Codex Wake stores state under the current repo:

```text
.codex/wake/pending/
.codex/wake/firing/
.codex/wake/submitted/
.codex/wake/failed/
.codex/wake/cancelled/
.codex/wake/expired/
.codex/wake/acks/
.codex/wake/locks/
.codex/wake/archive/
```

`.codex/wake/` and `.codex/events/` are ignored by this repo because they are runtime state, not source.

## Current Limits

- The tmux path is intentionally narrow: the daemon injects only `WAKE_TRIGGER_ID=<id>` plus a short resume instruction.
- The first hook use in a repo may require manual `/hooks` trust review in Codex.
- The daemon polls; it does not install a system service or systemd timer.
- `file_exists` and `not_before` are the verified trigger predicates in v0.1.0.
- App-server targeting is present for stdio dispatch experiments, but the tmux/hook path is the verified operator flow.

## Development

Run the focused test suite:

```bash
PYTHONPATH=src python -m unittest discover -s tests -p 'test_*.py'
```

Run the CLIs from source:

```bash
PYTHONPATH=src python -m codex_wake.cli --help
PYTHONPATH=src python -m codex_wake.daemon --once --no-dispatch
```

Create an app-server-targeted wake instead of a tmux-targeted wake:

```bash
PYTHONPATH=src python -m codex_wake.cli after --app-server-thread-id thread_abc 45m -- "Resume the scheduled task."
```

Design and validation notes live under `docs/dev/`.
