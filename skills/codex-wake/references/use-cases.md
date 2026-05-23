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

Common causes:

- The wake targeted a different pane than the one the operator watched.
- The target TUI was busy; Codex accepted the prompt, but the visible UI continued an interrupted or already-running turn.
- The wake used app-server transport, which can resume a thread without showing in a live tmux pane.
- The record was archived after handling, so only ack/archive evidence remains.
- Duplicate project and user hooks injected duplicate wake context, which can make the visible event harder to interpret.

Report this as `ack_observed; operator-visible turn not proven` unless the target pane scrollback shows the wake prompt or the turn output.

## App-Server Wake

Use when a resumable app-server-backed thread is the target instead of a live tmux pane.

Pattern:

```bash
codex-wake --wake-root .codex/wake app candidates --cwd "$PWD" --validate --only-idle --json
codex-wake --wake-root .codex/wake app after <THREAD_ID> 30m -- \
  "Resume this app-server thread. Verify current thread status and continue only if the task is incomplete."
```

Only target a thread that can be resumed and is idle. Use `codex-wake app status --resume <THREAD_ID>` when in doubt.

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
