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
codex-wake --version
codex-wake --wake-root .codex/wake doctor
codex-wake --wake-root .codex/wake monitor check --json
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
- Choose the wake transport before scheduling. The runtime you are waking determines the required target id, dispatcher, and completion evidence.
- Put logs and marker files under `.codex/events/` unless the repo has a stronger convention.
- Keep prompts short, idempotent, and evidence-oriented: tell the future agent what to verify first.
- Never put secrets, raw credentials, or private transcript bodies in wake prompts or tracked docs.
- Use `codex-waked --once` for bounded checks, or `codex-wake service install/status/logs` for longer monitoring.
- Before scheduling any unattended wake, prove that an active monitor owns the selected wake root with `codex-wake --wake-root .codex/wake monitor check --json`; use `--require-monitor` when creating wakes that must fire without a manual daemon pass.
- Do not call a wake smoke successful when using `codex-waked --no-dispatch`; that only proves predicate evaluation.
- After a wake fires, inspect `codex-wake show <wake-id>`, `.codex/wake/acks/`, and `codex-wake status --json` before claiming success.
- Treat ack as proof that Codex submitted the wake prompt in the target session, not proof that the operator saw a new turn in the pane they were watching.
- For tmux wakes, report `visibility_result.classification` when present; `visible_prompt_observed` is stronger than ack alone, and `ack_observed_visibility_unproven` must not be described as operator-visible success.
- For app-server wakes fired by a repo-scoped service, verify the daemon's user-systemd environment; `command -v codex` in the interactive shell is not enough evidence that the service can launch `codex app-server`.
- Prefer `codex-wake service install --codex-path "$(command -v codex)"` for service-fired app-server wakes when the repo service needs a durable Codex CLI command.
- App-server wakes fail by default if the target thread has an active writer. Use `--retry-active-writer` only when bounded delayed delivery is preferable; it never permits `turn/start` while the thread is active.
- If the goal is an operator-visible current-TUI wake, schedule the daemon to run after this agent turn has stopped, then stop. Do not immediately fire the wake from the same active turn.
- Archive completed dogfood or one-off wakes so future agents see a clean active state.

## Monitor Readiness

Unattended wake delivery requires a running monitor. A wake JSON file by itself
does not prove any daemon will poll it.

For a repo-scoped service:

```bash
codex-wake --wake-root .codex/wake monitor check --json
codex-wake --wake-root .codex/wake service status
codex-wake --wake-root .codex/wake doctor --json
codex-wake --wake-root .codex/wake product-readiness --json
```

`monitor_ready=true` means either the repo-scoped service is active for this
exact wake root, or recent persistent daemon/supervisor health was observed.
If it is false, install or repair a monitor before scheduling:

```bash
codex-wake --wake-root .codex/wake service install --codex-path "$(command -v codex)"
```

For multi-repo or OpenClaw usage, prefer the user-scoped supervisor once
available:

```bash
codex-wake supervisor install
codex-wake supervisor enroll --wake-root "$PWD/.codex/wake" --repo-root "$PWD"
codex-wake supervisor status --all
```

When a wake must fire unattended, create it with `--require-monitor`:

```bash
codex-wake --wake-root .codex/wake after --require-monitor 45m -- \
  "Wake idempotently. First inspect the wake record and continue only if work remains."
```

If `--require-monitor` fails, do not work around it by omitting the flag unless
you intend to run `codex-waked --once` manually before the due time. Treat
missing monitor evidence as a delivery risk, not as a scheduled wake.

## Choose Wake Transport

Classify the target runtime before creating a wake:

| Target runtime | Use | Required target proof | Required delivery proof |
| --- | --- | --- | --- |
| Live Codex TUI in tmux | default `after`, `at`, `file`, `changed`, or `pid` commands | `TMUX_PANE` and tmux socket captured from the target pane | ack evidence plus `visibility_result.classification=visible_prompt_observed` or direct pane inspection for operator-visible claims |
| Codex app-server thread | `codex-wake app ...` commands | real resumable Codex thread id from `app candidates --validate` or `app status --resume` | `app_server_preflight`, `dispatch_result.turn_id` when returned, `submitted`, `ack_observed`, or target transcript evidence |
| OpenClaw Slack/API agent | `codex_wake_schedule` plugin tool, or `codex-wake openclaw ...` when scheduling externally | real OpenClaw session key plus agent/workspace/channel evidence captured by OpenClaw or explicitly provided | `openclaw_gateway_preflight`, `dispatch_result.run_id`, `dispatch_result.session_id`, `submitted`, `openclaw_gateway_dispatch_result`, and Slack/transcript readback when human-visible proof is required |

Do not confuse transports:

- An OpenClaw Slack channel, OpenClaw agent id, or OpenClaw session key is not a Codex app-server thread id.
- A Codex app-server thread id is not a tmux pane and does not prove a visible turn in the active TUI.
- A tmux ack is not proof that an OpenClaw Slack/API session received a wake.
- `TMUX_PANE` empty means the default tmux-targeted creation path is unavailable.
- `codex-waked --no-dispatch` proves only trigger evaluation and state movement, not delivery.
- Placeholder ids such as `noop-smoke-test`, `thread_abc`, or copied sample session keys are invalid readiness evidence.

Before scheduling, be able to answer:

- What runtime am I waking?
- What durable identifier will route the wake?
- Which dispatcher will deliver it?
- What evidence will prove it landed?
- What will I inspect if dispatch succeeds but no human-visible turn appears?

## OpenClaw Sessions

OpenClaw Slack/API sessions are not tmux panes. Before using tmux wake patterns:

```bash
printf 'TMUX_PANE=%s\n' "${TMUX_PANE-}"
```

If `TMUX_PANE` is empty, the default `codex-wake after ...` path cannot capture a tmux target. For OpenClaw Slack/API sessions, prefer an OpenClaw Gateway wake with a real durable session key:

```bash
codex-wake --wake-root .codex/wake openclaw after \
  --agent main \
  --session-key agent:main:slack:channel:c0ahqqcg7j4 \
  --workspace default \
  --channel C0AHQQCG7J4 \
  --thread-ts 1779729958.218239 \
  --openclaw-path "$(command -v openclaw)" \
  30m -- "Resume this OpenClaw session. Inspect the wake record first."
```

When the OpenClaw `codex-wake` plugin is installed, prefer the
`codex_wake_schedule` tool from inside the live OpenClaw turn. It captures the
current `agentId`, `sessionKey`, and channel/thread evidence; do not invent or
copy placeholder session keys into wake records.

Plugin readiness checks:

```bash
codex-wake openclaw-plugin install --tag <codex-wake-tag> --prune-linked-path
openclaw gateway restart
openclaw plugins inspect codex-wake --runtime --json
openclaw gateway call tools.catalog --json --params '{"agentId":"main","includePlugins":true}' | rg 'codex_wake_schedule|codex-wake'
codex-wake --wake-root .codex/wake monitor check --json
codex-wake supervisor status --all
```

Use `codex-wake openclaw-plugin update --tag <tag> --prune-linked-path` for
routine updates. The prune option removes only linked `plugins.load.paths`
entries whose manifest id is `codex-wake`, writes an OpenClaw config backup,
and refreshes the generated plugin registry. Use `openclaw plugins install --link
./plugins/openclaw-codex-wake` only for local plugin development; linked plugin
state is not durable product evidence.

If OpenClaw Gateway auth uses environment-variable references, ensure the user
systemd manager that runs `codex-wake-supervisor.service` has those variables:

```bash
systemctl --user import-environment OPENCLAW_GATEWAY_TOKEN OPENCLAW_GATEWAY_PASSWORD
systemctl --user restart codex-wake-supervisor.service
```

Use an app-server wake only when you have a real resumable Codex thread id:

```bash
codex-wake --wake-root .codex/wake app candidates --cwd "$PWD" --validate --only-idle --json
codex-wake --wake-root .codex/wake app status --codex-path "$(command -v codex)" --resume <THREAD_ID>
codex-wake --wake-root .codex/wake app after --retry-active-writer <THREAD_ID> 30m -- \
  "Resume only after the target thread becomes idle."
```

Omit `--retry-active-writer` for the fail-fast default. With the flag, active
writer contention requeues only within the wake record's bounded attempt and
backoff policy.

Never use placeholder thread ids or session keys such as `noop-smoke-test` as proof of OpenClaw wake readiness. For OpenClaw skill availability, use `openclaw skills info codex-wake --agent <id> --json`; for wake execution, require a real dispatch without `--no-dispatch` and then verify `submitted`, `openclaw_gateway_dispatch_result`, `ack_observed`, or app-server turn evidence.

## Common Patterns

Wake after a delay:

```bash
codex-wake --wake-root .codex/wake after --require-monitor 45m -- \
  "Wake idempotently. First run codex-wake --wake-root .codex/wake status --json, then continue the migration if it is not already complete."
```

Wake at an absolute time:

```bash
codex-wake --wake-root .codex/wake at --require-monitor "2026-05-22T17:30:00-05:00" -- \
  "Check the release branch. First verify whether the release is already complete."
```

Wake when a marker file exists:

```bash
mkdir -p .codex/events
(
  pytest -q > .codex/events/pytest.log 2>&1
  touch .codex/events/pytest.done
) &
codex-wake --wake-root .codex/wake file --require-monitor .codex/events/pytest.done -- \
  "Pytest finished. Read .codex/events/pytest.log, summarize failures, and continue only if fixes are still needed."
```

Wake when a file changes:

```bash
codex-wake --wake-root .codex/wake changed --require-monitor .codex/events/build.log -- \
  "The build log changed. Read .codex/events/build.log and continue from the current state."
```

Wake when a process exits:

```bash
long-running-command > .codex/events/job.log 2>&1 &
codex-wake --wake-root .codex/wake pid --require-monitor "$!" -- \
  "The background job exited. Read .codex/events/job.log, verify the outcome, and continue or report completion."
```

Run one daemon pass:

```bash
codex-waked --wake-root .codex/wake --once --ack-timeout 20
```

App-server service environment preflight:

```bash
command -v codex
codex-wake --wake-root .codex/wake doctor
codex-wake --wake-root .codex/wake doctor --json
codex-wake --wake-root .codex/wake product-readiness --json
codex-wake --wake-root .codex/wake monitor check --json
systemctl --user show-environment | rg '^(PATH|CODEX_)='
systemctl --user status codex-wake-<repo>.service --no-pager
codex-wake --wake-root .codex/wake service status
codex-wake --wake-root .codex/wake service logs --lines 80
```

`doctor` should report `service_app_server_codex_ready=true` before relying on
the repo service for app-server dispatch. If it reports
`interactive_path_only` or `missing`, reinstall the service with:

```bash
codex-wake --wake-root .codex/wake service install --codex-path "$(command -v codex)"
```

Use `product-readiness --json` for productization and release gates. It reports
normalized `ready`, `not_needed`, `warning`, `manual_only`, and `blocked`
outcomes for CLI, hooks, skill installs, repo service, supervisor roots, monitor health,
app-server dispatch, OpenClaw Gateway, OpenClaw plugin, and tmux availability
without emitting Gateway secret values.

`repo_service=not_needed` is healthy when `covered_by=supervisor`: it means the
active user supervisor is enrolled for this wake root and has ready monitor
evidence, so a redundant repo-scoped service should remain inactive.

Use the tracked product smoke harness when validating an installed release:

```bash
python scripts/product_smoke.py --json
python scripts/product_smoke.py --public-tag v0.5.0 --json
```

The safe smoke uses `--no-dispatch` for daemon and supervisor checks. For live
Codex app-server or OpenClaw Gateway proof, pass the harness real thread/session
arguments and verify the unique marker in the resulting turn, transcript, or
channel readback. Treat tmux as `manual_only` unless pane visibility evidence is
captured. Read `docs/support-boundary.md` before claiming unsupported cases as
product evidence.

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
codex-wake --wake-root .codex/wake cleanup --archive-terminal --json
```

`cleanup` is dry-run by default and deletes only archived records when
`--delete` is supplied. It does not delete active wakes, terminal records before
archive, acks, logs, monitor health, or supervisor registry entries. Use
`codex-wake supervisor status --json` to find stale roots; remediate them with
`supervisor run --once` or `supervisor unenroll`.

For OpenClaw Gateway dogfood, inspect `openclaw_gateway_preflight`, `dispatch_result.run_id`, `dispatch_result.session_id`, and `openclaw_gateway_dispatch_result`. For plugin-scheduled OpenClaw wakes, also verify that the wake target dispatch block did not acquire inferred `reply_channel`, `reply_to`, or `reply_account_id` values unless those overrides were explicitly configured. For app-server dogfood, inspect `app_server_preflight`, `dispatch_result.turn_id`, and `ack_observed`; if dispatch was service-fired, also inspect the service logs and daemon environment.

Use live channel readback when Slack-visible proof is required:

```bash
openclaw message read --channel slack --account default --target channel:<channel-id> --limit 20 --json
```

Report the wake id, trigger evidence, ack/submitted status, tmux visibility classification when present, OpenClaw/app-server dispatch evidence when present, Slack readback evidence when used, and any remaining active wake count.

If ack exists but no new turn is visible, read `references/use-cases.md#ack-but-no-visible-turn`.
