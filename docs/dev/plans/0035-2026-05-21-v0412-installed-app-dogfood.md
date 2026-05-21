# v0.4.12 Installed App Dogfood

## Scope

Dogfood the refreshed public `v0.4.12` installed runtime with one app-server-targeted wake in the repo wake root.

## Non-Goals

- Do not inject into the active TUI pane.
- Do not enable the user service permanently.
- Do not change wake schema or dispatch behavior.
- Do not leave active wake records behind.

## Current State

Closed by `docs/dev/verification/0044-2026-05-21-v0412-installed-app-dogfood.md`. The installed public `v0.4.12` runtime created, fired, app-server-dispatched, submitted, and archived one dogfood wake.

## Plan

- Select a repo-local idle app-server candidate using installed `codex-wake app candidates --validate --only-idle`.
- Register a short `not_before` app-server wake using installed `codex-wake`.
- Run installed `codex-waked --once` after the predicate is due.
- Verify the record reaches `submitted` with `predicate_matched`, `dispatch_attempt`, `app_server_preflight`, and `ack_observed` evidence.
- Archive the dogfood record and verify the wake root is tidy.

## Acceptance Criteria

- Wake request is created from the installed CLI.
- Daemon evaluates the predicate and dispatches through app-server.
- Submitted wake evidence is inspectable.
- Dogfood wake is archived after verification.
- Final wake root has no active or terminal records.

## Definition Of Done

This lane can close when the installed runtime dogfood wake is recorded, archived, documented, committed, pushed, and CI is green.
