# App-Server Service Environment Product Hardening

Date: 2026-05-23

## Scope

Harden app-server wake dispatch so repo-scoped user-systemd services do not
depend silently on the interactive shell's `PATH` to find the Codex CLI.

This follows the Ragmail service environment handoff in
`docs/dev/verification/0052-2026-05-23-ragmail-app-server-service-env-handoff.md`.

## Non-Goals

- Do not add WebSocket app-server dispatch.
- Do not dump the full user-systemd environment into doctor output or tracked
  docs.
- Do not mutate Ragmail or any other downstream repo in this slice.
- Do not treat app-server `turn/start` acceptance as proof of visible output in
  an active TUI pane.

## Current State

`codex-wake` can create app-server wake records and dispatch them through a
local stdio `codex app-server` process. The stdio client currently defaults to
`codex` from the dispatching process environment. That is fragile for wakes
fired by a user-scoped service, because the user-systemd manager may not have
the same `PATH` as the interactive shell that created the wake.

## Acceptance Criteria

- `codex-wake service install` can persist an explicit Codex CLI command for
  daemon-side app-server dispatch when `codex` is resolvable or
  `--codex-path` is provided.
- App-server wake records can optionally carry a validated `target.codex_cmd`
  for dispatch.
- App-server dispatch reports a clear `last_error` when the Codex CLI command
  cannot be launched.
- `codex-wake doctor` and `doctor --json` report whether the installed service
  can resolve the Codex CLI for app-server dispatch without exposing unrelated
  environment values.
- Focused tests cover command resolution, service unit rendering, doctor
  output, and the missing-command failure signature.

## Definition Of Done

- Source tests and compile checks pass.
- Installed CLI is refreshed and `doctor --json` exposes the new readiness
  fields.
- Verification evidence is recorded under `docs/dev/verification/`.
- Changes are committed, pushed, and CI is watched to completion.
