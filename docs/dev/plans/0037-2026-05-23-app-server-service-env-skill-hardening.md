# App-Server Service Environment Skill Hardening

Date: 2026-05-23

## Scope

Harden the `codex-wake` agent skill after the Ragmail service dogfood showed
that app-server dispatch can fail when the repo-scoped user service cannot
resolve the `codex` CLI even though the interactive shell can.

## Current State

The skill documents app-server candidate selection and wake creation, but it
does not tell agents to inspect the user-systemd daemon environment before
relying on a repo-scoped service for app-server dispatch.

## Non-Goals

- Do not change app-server dispatch code in this slice.
- Do not change service install behavior in this slice.
- Do not treat importing the current shell environment into user-systemd as a
  portable product fix.
- Do not broaden tmux dogfood guidance.

## Acceptance Criteria

- `skills/codex-wake/SKILL.md` warns that app-server service dispatch uses the
  daemon environment, not the interactive shell environment.
- `skills/codex-wake/references/use-cases.md` gives app-server service
  preflight, recovery, and closeout commands.
- The skill classifies `No such file or directory: 'codex'` as a service
  environment failure.
- Installed skill copies are synced and diff-clean.

## Definition Of Done

- Handoff recommendations from verification note `0052` are reflected in the
  skill source.
- Lightweight text assertions validate the new guidance.
- Full source tests remain green.
- Verification evidence is recorded under `docs/dev/verification/`.
