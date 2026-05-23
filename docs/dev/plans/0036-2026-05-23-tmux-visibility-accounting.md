# Tmux Visibility Accounting

Date: 2026-05-23

## Scope

Add sanitized tmux dispatch evidence that distinguishes hook ack from an
operator-visible wake in the target pane.

## Current State

Tmux dispatch captures the pane before injection for unsafe-state heuristics,
pastes the canonical wake prompt, waits for the hook ack file, and moves the
record to `submitted` when ack is observed. The wake record does not preserve
whether the wake marker was visible in pane scrollback before or after dispatch.

## Non-Goals

- Do not store raw tmux pane text in wake records.
- Do not change the status vocabulary or directory layout.
- Do not change app-server dispatch semantics in this slice.
- Do not require live tmux or Codex TUI execution in CI.

## Acceptance Criteria

- Tmux dispatch records an optional visibility object for submitted records.
- The visibility object classifies `visible_prompt_observed`,
  `ack_observed_visibility_unproven`, or `visibility_check_failed`.
- Events include enough sanitized metadata to explain the classification.
- Tests cover visible-marker, unproven-marker, and post-capture failure paths.
- Schema/runtime docs describe the optional field and privacy boundary.

## Definition Of Done

- Focused injector tests pass.
- Full unit test suite passes.
- Source compile and whitespace checks pass.
- Verification evidence is recorded under `docs/dev/verification/`.
