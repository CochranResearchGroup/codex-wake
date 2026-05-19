# CI Release Gates

State: CLOSED
Lane: P16

## Scope

Add GitHub Actions validation for the public repo.

## Non-Goals

- Do not automate publishing releases.
- Do not require live tmux or user systemd in CI.
- Do not add third-party runtime dependencies.

## Current State

Local and clean public-tag installs were validated manually before this lane. CI now runs source tests, package build, and installed-wheel CLI smoke checks on pushes to `main` and pull requests.

Validation evidence: [CI Release Gates](../verification/0010-2026-05-19-ci-release-gates.md)

## Acceptance Criteria

- CI runs Python unit tests.
- CI runs package build.
- CI runs a lightweight CLI smoke.
- CI avoids workstation-only live tmux/systemd checks.
- CI status is visible on the public upstream.
- Validation evidence is recorded.

## Definition Of Done

This lane can close when GitHub Actions validates the non-live release gates for this repo.
