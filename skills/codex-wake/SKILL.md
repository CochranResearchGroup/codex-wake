---
name: codex-wake
description: Schedule durable wake cycles for TUI-bound Codex agents with codex-wake. Use when an agent needs to resume later, wait for CI/tests/builds, monitor a file/process, continue a long job, dogfood wake behavior, or inspect/cancel/archive wake records.
---

# Codex Wake

Use `codex-wake` when work should resume after a defined trigger instead of relying on model memory or a foreground sleep.

## Preconditions

Run from the repo or workspace that owns the wake state.

```bash
command -v codex-wake
command -v codex-waked
command -v codex-wake-hook
codex-wake --wake-root .codex/wake doctor
codex-wake --wake-root .codex/wake hook check
```

For user-scope hook setup:

```bash
codex-wake --wake-root .codex/wake hook user check
codex-wake --wake-root .codex/wake hook user install
```

If both project and user hooks are installed, `doctor` may report `hook_duplicate_install=true`; expect duplicate wake context until one source is removed or disabled.

## Core Rules

- Create a durable wake record with `codex-wake`; do not say you will remember to check later.
- Put logs and marker files under `.codex/events/` unless the repo has a stronger convention.
- Keep prompts short, idempotent, and evidence-oriented: tell the future agent what to verify first.
- Never put secrets, raw credentials, or private transcript bodies in wake prompts or tracked docs.
- Use `codex-waked --once` for bounded checks, or `codex-wake service install/status/logs` for longer monitoring.
- After a wake fires, inspect `codex-wake show <wake-id>`, `.codex/wake/acks/`, and `codex-wake status --json` before claiming success.
- Treat ack as proof that Codex submitted the wake prompt in the target session, not proof that the operator saw a new turn in the pane they were watching.
- For tmux wakes, report `visibility_result.classification` when present; `visible_prompt_observed` is stronger than ack alone, and `ack_observed_visibility_unproven` must not be described as operator-visible success.
- For app-server wakes fired by a repo-scoped service, verify the daemon's user-systemd environment; `command -v codex` in the interactive shell is not enough evidence that the service can launch `codex app-server`.
- If the goal is an operator-visible current-TUI wake, schedule the daemon to run after this agent turn has stopped, then stop. Do not immediately fire the wake from the same active turn.
- Archive completed dogfood or one-off wakes so future agents see a clean active state.

## Common Patterns

Wake after a delay:

```bash
codex-wake --wake-root .codex/wake after 45m -- \
  "Wake idempotently. First run codex-wake --wake-root .codex/wake status --json, then continue the migration if it is not already complete."
```

Wake at an absolute time:

```bash
codex-wake --wake-root .codex/wake at "2026-05-22T17:30:00-05:00" -- \
  "Check the release branch. First verify whether the release is already complete."
```

Wake when a marker file exists:

```bash
mkdir -p .codex/events
(
  pytest -q > .codex/events/pytest.log 2>&1
  touch .codex/events/pytest.done
) &
codex-wake --wake-root .codex/wake file .codex/events/pytest.done -- \
  "Pytest finished. Read .codex/events/pytest.log, summarize failures, and continue only if fixes are still needed."
```

Wake when a file changes:

```bash
codex-wake --wake-root .codex/wake changed .codex/events/build.log -- \
  "The build log changed. Read .codex/events/build.log and continue from the current state."
```

Wake when a process exits:

```bash
long-running-command > .codex/events/job.log 2>&1 &
codex-wake --wake-root .codex/wake pid "$!" -- \
  "The background job exited. Read .codex/events/job.log, verify the outcome, and continue or report completion."
```

Run one daemon pass:

```bash
codex-waked --wake-root .codex/wake --once --ack-timeout 20
```

App-server service environment preflight:

```bash
command -v codex
systemctl --user show-environment | rg '^(PATH|CODEX_)='
systemctl --user status codex-wake-<repo>.service --no-pager
codex-wake --wake-root .codex/wake service status
codex-wake --wake-root .codex/wake service logs --lines 80
```

If service logs show `No such file or directory: 'codex'`, classify it as a service-environment failure, not an app-server protocol failure. Re-check the same wake record after recovery instead of creating a duplicate wake.

Operator-visible delayed wake:

```bash
wake_id=$(codex-wake --wake-root .codex/wake after 15s -- \
  "Visible wake check. Verify this wake id, ack evidence, target pane, and final status." | awk '{print $1}')
unit="codex-wake-${wake_id//_/-}"
systemd-run --user --unit="$unit" --on-active=25s \
  "$(command -v codex-waked)" --wake-root "$PWD/.codex/wake" --once --ack-timeout 20
```

After scheduling this delayed wake, end the current turn so the target TUI is idle enough to show the submitted wake prompt.

## Use Cases

Read `references/use-cases.md` when choosing a wake pattern for CI/test babysitting, long builds, review loops, staged migrations, app-server wakes, or dogfood runs.

## Closeout

After handling a wake:

```bash
codex-wake --wake-root .codex/wake show <wake-id>
codex-wake --wake-root .codex/wake status --json
codex-wake --wake-root .codex/wake archive <wake-id>
```

For app-server dogfood, inspect `app_server_preflight`, `dispatch_result.turn_id`, and `ack_observed`; if dispatch was service-fired, also inspect the service logs and daemon environment.

Report the wake id, trigger evidence, ack/submitted status, tmux visibility classification when present, app-server dispatch evidence when present, and any remaining active wake count.

If ack exists but no new turn is visible, read `references/use-cases.md#ack-but-no-visible-turn`.
