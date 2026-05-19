# CI Release Gates

State: OPEN
Lane: P16

## Scope

Add GitHub Actions validation for the public repo.

## Non-Goals

- Do not automate publishing releases.
- Do not require live tmux or user systemd in CI.
- Do not add third-party runtime dependencies.

## Current State

Local and clean public-tag installs are validated manually. The repo does not yet have CI to run source tests and package builds on pushes or pull requests.

## Acceptance Criteria

- CI runs Python unit tests.
- CI runs package build.
- CI runs a lightweight CLI smoke.
- CI avoids workstation-only live tmux/systemd checks.
- CI status is visible on the public upstream.
- Validation evidence is recorded.

## Definition Of Done

This lane can close when GitHub Actions validates the non-live release gates for this repo.
