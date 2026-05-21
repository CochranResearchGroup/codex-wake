# App-Server Target Discovery

## Scope

Add a read-only CLI surface for finding local rollout-backed Codex thread ids before registering an app-server wake.

## Non-Goals

- Do not start app-server turns.
- Do not add WebSocket app-server support.
- Do not copy transcript bodies or prompt content into discovery output.
- Do not change wake record schema or dispatch status semantics.

## Current State

Closed by `docs/dev/verification/0039-2026-05-21-app-server-target-discovery.md`. `codex-wake app candidates` now lists recent local rollout-backed thread ids from Codex session metadata without starting app-server turns or surfacing transcript bodies.

## Plan

- Add `codex-wake app candidates` to scan local Codex session rollout metadata.
- Read only each rollout file's `session_meta` line.
- Print recent thread ids with created/updated metadata and cwd.
- Support JSON output and optional cwd filtering.
- Document that candidates should be checked with `codex-wake app status --resume <thread-id>` before wake registration.

## Acceptance Criteria

- `codex-wake app candidates --json` emits structured candidate rows.
- Text output points operators to `app status --resume`.
- Discovery does not read or surface transcript bodies.
- Tests cover candidate discovery, cwd filtering, and CLI output.

## Definition Of Done

This lane can close when the command is implemented, documented, validated from source and installed command surfaces, and the known limits are recorded.
