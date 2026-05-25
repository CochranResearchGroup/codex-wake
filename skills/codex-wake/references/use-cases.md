# Codex Wake Use Cases

Use these patterns when deciding how an agent should schedule its own wake cycle.

## CI Or Test Babysitting

Use when a test suite or CI run is too slow to wait on in the active turn.

Pattern:

```bash
mkdir -p .codex/events
(
  pytest -q > .codex/events/pytest.log 2>&1
  touch .codex/events/pytest.done
) &
codex-wake --wake-root .codex/wake file .codex/events/pytest.done -- \
  "Background pytest is complete. Read .codex/events/pytest.log. If failures remain, fix them; if not, report pass and archive this wake."
```

Best prompt requirements:

- Name the log path.
- Require the future agent to verify whether the task is already complete.
- Avoid asking for broad refactors on wake; continue from evidence.

## Long Build Or Indexing Job

Use when a deterministic job writes a log and eventually exits.

Pattern:

```bash
mkdir -p .codex/events
build-or-index-command > .codex/events/build.log 2>&1 &
pid=$!
codex-wake --wake-root .codex/wake pid "$pid" -- \
  "The build/index job exited. Read .codex/events/build.log, verify success or failure, and continue from the recorded outcome."
```

Prefer `pid` over an arbitrary time delay when the process lifetime is the trigger.

## External Artifact Appears

Use when a separate tool, human action, or service writes a marker file.

Pattern:

```bash
codex-wake --wake-root .codex/wake file .codex/events/review-ready.json -- \
  "Review input arrived. Read .codex/events/review-ready.json, verify it belongs to this task, then continue."
```

Use a marker file that contains enough context to continue safely. Do not put secrets in the marker.

## Periodic Self-Check

Use when the agent needs a bounded follow-up, such as checking CI status after a push.

Pattern:

```bash
codex-wake --wake-root .codex/wake after 20m -- \
  "Check CI for the current branch. First verify the branch and latest commit, then inspect CI status and report or repair failures."
```

If repeated checks are needed, each wake turn may schedule a new wake after inspecting current state. Keep each prompt idempotent.

## Staged Migration

Use when a migration should proceed only after a delay, service restart, queue drain, or background validation.

Pattern:

```bash
codex-wake --wake-root .codex/wake after 10m -- \
  "Continue the staged migration. First inspect .codex/events/migration.log and codex-wake status. If the migration already completed, report evidence and stop."
```

Write migration logs to `.codex/events/` before scheduling the wake.

## Current TUI Dogfood

Use when validating that tmux injection, hook execution, ack persistence, and daemon status movement work in the active TUI.

Preflight:

```bash
printf 'TMUX_PANE=%s\n' "${TMUX_PANE-}"
```

If `TMUX_PANE` is empty, this is not a TUI-bound tmux session. Do not use the default `after`, `at`, `file`, `changed`, or `pid` creation path as a tmux dogfood proof; it will fail with `TMUX_PANE is required to create a tmux-targeted wake`.

Immediate pattern, only when the target pane is idle:

```bash
codex-wake --wake-root .codex/wake hook check
codex-wake --wake-root .codex/wake hook user check
codex-wake --wake-root .codex/wake status --json
codex-wake --wake-root .codex/wake after 15s -- \
  "Dogfood wake. Verify this wake id, ack evidence, and final status, then archive the record."
codex-waked --wake-root .codex/wake --once --ack-timeout 20
```

Operator-visible delayed pattern:

```bash
wake_id=$(codex-wake --wake-root .codex/wake after 15s -- \
  "Dogfood wake. Verify this wake id, ack evidence, target pane, and final status, then archive the record." | awk '{print $1}')
unit="codex-wake-${wake_id//_/-}"
systemd-run --user --unit="$unit" --on-active=25s \
  "$(command -v codex-waked)" --wake-root "$PWD/.codex/wake" --once --ack-timeout 20
```

After creating the delayed pattern, stop the current turn. The daemon should fire after the active TUI is no longer in the middle of a tool/model turn.

If `ack_timeout` occurs but the TUI later receives the wake prompt, inspect the ack file and rerun one daemon pass to reconcile pending state.

## Ack But No Visible Turn

Ack means `UserPromptSubmit` ran for the wake prompt. It does not prove the operator saw a new turn in the pane they were watching.

Check:

```bash
codex-wake --wake-root .codex/wake show <wake-id>
python -m json.tool .codex/wake/acks/<wake-id>.submitted
tmux list-panes -a -F '#{session_name}:#{window_index}.#{pane_index} #{pane_id} cwd=#{pane_current_path} cmd=#{pane_current_command} title=#{pane_title}'
tmux capture-pane -p -S -120 -t <pane-id>
```

For tmux wakes, inspect `visibility_result.classification` in the wake record.
`visible_prompt_observed` means the wake marker newly appeared in captured
scrollback after ack. `ack_observed_visibility_unproven` means the hook ack was
real, but operator-visible display was not proven.

Common causes:

- The wake targeted a different pane than the one the operator watched.
- The target TUI was busy; Codex accepted the prompt, but the visible UI continued an interrupted or already-running turn.
- The wake used app-server transport, which can resume a thread without showing in a live tmux pane.
- The record was archived after handling, so only ack/archive evidence remains.
- Duplicate project and user hooks injected duplicate wake context, which can make the visible event harder to interpret.

Report this as `ack_observed; operator-visible turn not proven` unless `visibility_result.classification` is `visible_prompt_observed` or direct target-pane inspection shows the wake prompt or the turn output.

## App-Server Wake

Use when a resumable app-server-backed thread is the target instead of a live tmux pane.

Interactive protocol check:

```bash
codex-wake --wake-root .codex/wake app candidates --cwd "$PWD" --validate --only-idle --json
codex-wake --wake-root .codex/wake app status --codex-path "$(command -v codex)" --resume <THREAD_ID>
codex-wake --wake-root .codex/wake app after <THREAD_ID> 30m -- \
  "Resume this app-server thread. Verify current thread status and continue only if the task is incomplete."
```

Only target a thread that can be resumed and is idle. Use `codex-wake app status --resume <THREAD_ID>` when in doubt.

In OpenClaw Slack/API sessions, this is the only viable wake transport unless the agent is explicitly running inside a tmux-backed Codex TUI. Do not use fake thread ids for smoke tests. A dummy app-server target plus `codex-waked --no-dispatch` proves only that a wake record can be created and its predicate can move to `firing`; it does not prove a wake turn, Slack reply, hook ack, or operator-visible behavior.

OpenClaw readiness levels:

- Skill visible: `openclaw skills info codex-wake --agent <id> --json` reports `modelVisible=true` and `commandVisible=true`.
- Predicate fired: `codex-waked --once --no-dispatch` reports `fired=1`; this is not dispatch.
- Wake dispatched: run without `--no-dispatch`, then inspect `codex-wake show <wake-id>` for app-server dispatch evidence.
- Wake accepted by Codex: inspect `dispatch_result.turn_id`, `submitted`, `ack_observed`, or the target app-server transcript.
- Operator-visible current TUI wake: only tmux transport with `visibility_result.classification=visible_prompt_observed` or direct pane inspection proves this.

If the repo-scoped user service will fire the wake, check the service
environment before relying on it. App-server dispatch is executed by the daemon
process, so `command -v codex` in the current shell is insufficient evidence.

Service-fired app-server preflight:

```bash
command -v codex
codex --version
codex-wake --wake-root .codex/wake doctor
codex-wake --wake-root .codex/wake doctor --json
systemctl --user show-environment | rg '^(PATH|CODEX_)='
systemctl --user status codex-wake-<repo>.service --no-pager
codex-wake --wake-root .codex/wake service status
codex-wake --wake-root .codex/wake service logs --lines 80
codex-wake --wake-root .codex/wake app candidates --cwd "$PWD" --validate --only-idle --json
```

`doctor` should report `service_app_server_codex_ready=true` before you rely on
the repo service to fire an app-server wake. If it reports
`interactive_path_only` or `missing`, reinstall the service with an explicit
Codex CLI path:

```bash
codex-wake --wake-root .codex/wake service install --codex-path "$(command -v codex)"
```

If logs contain `No such file or directory: 'codex'`, classify the wake as a
service-environment failure, not an app-server protocol failure. Do not create a
duplicate wake just because dispatch failed; inspect and continue the same wake
record when possible.

Immediate recovery, when the current shell is the desired runtime environment:

```bash
systemctl --user import-environment PATH CODEX_CI CODEX_MANAGED_BY_NPM CODEX_MANAGED_PACKAGE_ROOT CODEX_PROFILES_CONFIG CODEX_PROFILES_REPO
systemctl --user restart codex-wake-<repo>.service
codex-wake --wake-root .codex/wake service logs --lines 80
codex-wake --wake-root .codex/wake show <wake-id>
```

This is a workstation recovery step, not a portable product fix. After recovery,
wait for or run one bounded daemon pass and re-check the same wake record.

For one-off app-server protocol validation, prefer a shell-fired pass:

```bash
codex-waked --wake-root .codex/wake --once --ack-timeout 20
```

Use the repo-scoped service path when the goal is to validate service-fired
dispatch specifically.

After app-server dogfood, inspect:

```bash
codex-wake --wake-root .codex/wake show <wake-id>
codex-wake --wake-root .codex/wake status --json
codex-wake --wake-root .codex/wake service logs --lines 80
```

Report `app_server_preflight.status.type`, `dispatch_result.turn_id`,
`ack_observed`, and whether any service-environment failure was seen.

## Cleanup Or Closeout Wake

Use when a future agent should confirm cleanup after asynchronous work.

Pattern:

```bash
codex-wake --wake-root .codex/wake after 5m -- \
  "Cleanup check. Run codex-wake --wake-root .codex/wake status --json. Archive terminal records for this dogfood lane and report active_total and terminal_total."
```

Closeout should report:

- wake id
- trigger type and evidence
- whether an ack was observed
- final `active_total` and `terminal_total`
