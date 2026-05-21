# App Candidate Validation

## Scope

Add an optional validation mode for `codex-wake app candidates` so operators can check discovered rollout-backed thread ids with resume-backed app-server status before registering a wake.

## Non-Goals

- Do not start app-server turns.
- Do not change app-server dispatch behavior.
- Do not change wake record schema.
- Do not expose non-stdio app-server endpoints.
- Do not read or emit prompt or transcript body content.

## Current State

Closed by `docs/dev/verification/0041-2026-05-21-app-candidate-validation.md`. `codex-wake app candidates --validate` now checks candidates with resume-backed status without starting turns, and `--only-idle` filters validated candidates to idle threads.

## Plan

- Add `codex-wake app candidates --validate`.
- Validate each candidate with `thread/resume`, not `turn/start`.
- Add `--only-idle` as a filter that requires `--validate`.
- Include validation status and resumed thread status in JSON output.
- Keep default `app candidates` output unchanged except for additive JSON fields.

## Acceptance Criteria

- `app candidates --validate --json` includes `validation`, `status_type`, and `status` for successful resume checks.
- Resume failures are represented as row-level validation failures, not process-wide crashes.
- `app candidates --validate --only-idle --json` filters to idle resumed candidates.
- Text output remains usable for operator inspection.
- Tests cover validation, idle filtering, and invalid flag combinations.

## Definition Of Done

This lane can close when source tests pass, source and installed CLI smokes cover the new flags, and verification evidence records that validation does not start turns.
