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
uv tool install git+https://github.com/CochranResearchGroup/codex-wake.git@v0.3.1
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

For an installed tool, let Codex Wake write the repo-local hook config:

```bash
codex-wake hook install
codex-wake hook check
```

`hook check` verifies the repo-local config and reports ack evidence from
`.codex/wake/acks/`. If no ack exists, the active TUI hook-loaded state is
reported as `unknown_without_ack`; that is not proof that tmux injection failed.
Codex may show the hook source under `UserPromptHooks` during `/hooks` review.

This writes or checks this `.codex/hooks.json` shape:

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

Codex may require a one-time `/hooks` review before a new repo-local hook runs. Codex Wake reports that prerequisite, but it does not bypass Codex hook trust. If `/hooks` does not list this repo hook source, the active TUI has not loaded the repo hook file; restart or resume Codex in this repo, then review hooks before testing wake ack behavior.

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

Wake when a file is created or changes:

```bash
codex-wake changed .codex/events/build.log -- \
  "The build log changed. Read .codex/events/build.log and continue."
```

Wake when a known background process exits:

```bash
long-running-command > .codex/events/job.log 2>&1 &
codex-wake pid "$!" -- \
  "The background process exited. Read .codex/events/job.log and continue."
```

On Linux, `pid` wakes record the process start time from `/proc/<pid>/stat`
and the current boot id when available. The daemon fires if the PID disappears
or if the live PID no longer matches that registered process identity.

Create an app-server-targeted wake instead of a tmux-targeted wake:

```bash
codex-wake app after thread_abc 45m -- "Resume this thread through app-server."
codex-wake app at thread_abc "2026-05-19T17:30:00-05:00" -- "Check the release state."
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

Run a readiness report:

```bash
codex-wake doctor
codex-wake doctor --json
```

`doctor` prints the same hook ack evidence as `hook check`, including the latest
ack wake id, submitted timestamp, and session id when available. Use
`doctor --json` when automation needs command, tmux, hook, ack, and service
readiness without parsing text output.

Inspect and manage wakes:

```bash
codex-wake list
codex-wake list --json
codex-wake show <wake-id>
codex-wake cancel <wake-id>
codex-wake archive <wake-id>
codex-wake archive --all-terminal
codex-wake cleanup --older-than 30d
codex-wake cleanup --older-than 30d --delete
codex-wake schema
codex-wake schema --json
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

Cleanup is conservative. `codex-wake cleanup` is dry-run by default and only
targets records already under `.codex/wake/archive/`. Add `--delete` to remove
matching archived records, and `--archive-terminal` to archive terminal records
before cleanup evaluation. Active `pending/` and `firing/` records are never
deleted by cleanup.

Wake records currently use schema version `1`. The compatibility policy is
additive optional fields; inspect it with `codex-wake schema` or read
`docs/dev/wake-record-schema.md`.

## Current Limits

- The tmux path is intentionally narrow: the daemon injects only `WAKE_TRIGGER_ID=<id>` plus a short resume instruction.
- The first hook use in a repo may require manual `/hooks` trust review in Codex.
- The daemon polls; it does not install a system service or systemd timer.
- `not_before`, `file_exists`, `file_changed`, and `process_done` are polled predicates.
- `process_done` falls back to PID liveness on platforms where process identity is unavailable.
- App-server targeting is present for stdio dispatch experiments, but unauthenticated WebSocket dispatch is intentionally not implemented.

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
PYTHONPATH=src python -m codex_wake.cli app after thread_abc 45m -- "Resume the scheduled task."
```

Design and validation notes live under `docs/dev/`.
