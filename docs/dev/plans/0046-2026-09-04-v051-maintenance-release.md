# v0.5.1 Maintenance Release

Date: 2026-09-04

Status: CLOSED

## Objective

Publish the accumulated maintenance work as `v0.5.1`, then refresh and verify
the user-scoped CLI, hook, skills, supervisor, and OpenClaw plugin from the
public tag.

## Current State

`v0.5.1` is tagged and published from
`c31a03b7fce77679a08ddf9eb7036f545f055d85`. GitHub CI passed on Python 3.11
and 3.12, the public-tag smoke reports CLI `0.5.1` with schema version `1`, and
the CLI, hook, skills, supervisor, and OpenClaw plugin have been refreshed and
read back from their installed locations.

## Scope

- Include P44 app-server active-writer fail-closed behavior and its explicit
  bounded-retry option.
- Include P45 cross-root wake prompt routing and archived terminal handling.
- Include the unpublished stable executable resolution and removed-repository
  service protections already committed on `main`.
- Bump Python and OpenClaw plugin versions to `0.5.1`.
- Run source, plugin, package, installed-wheel, planning, and diff validation.
- Push `main`, tag `v0.5.1`, wait for GitHub CI, and publish release notes.
- Smoke the public tag and refresh installed user surfaces from it.

## Non-Goals

- Do not change wake-record schema version 1.
- Do not add a new trigger or transport.
- Do not run an unsolicited live app-server, tmux, or OpenClaw wake.
- Do not rewrite or squash the unpublished local commit history.

## Acceptance Criteria

- The working tree is reconciled with `origin/main` and no remote commit is
  overwritten.
- Versions and public install documentation consistently name `0.5.1`.
- Full Python tests, compilation, plugin tests and syntax checks, package build,
  installed-wheel smoke, planning audit, and `git diff --check` pass.
- The release commit and annotated `v0.5.1` tag are public on GitHub.
- GitHub CI succeeds and the GitHub release is published from tracked notes.
- A public-tag product smoke reports CLI `0.5.1` and schema version `1`.
- The user CLI, hook, three standard skill copies, user supervisor, and
  OpenClaw plugin are refreshed and read back successfully.
- Release verification is recorded and P46 is closed.

## Definition Of Done

The public release, installed runtime, and durable verification evidence all
agree on `v0.5.1`; required services are healthy; the repository is clean and
pushed; and any remaining warnings or intentionally skipped live delivery are
stated precisely.

## Result

- Preserved and pushed the unpublished local history without a rebase, squash,
  force push, or overwritten upstream commit.
- Published annotated tag and GitHub release `v0.5.1`.
- GitHub Actions run `33858855558` passed both release-gate jobs.
- Refreshed the user-scoped `uv tool` install, user hook, three standard skill
  copies, user supervisor, and managed OpenClaw plugin.
- Verified the installed active-writer option and cross-root archived-terminal
  hook behavior with disposable records.
- Recorded detailed evidence in
  `docs/dev/verification/0070-2026-09-04-v051-release.md`.

No live app-server, tmux injection, or OpenClaw delivery was initiated because
this release did not need to send a real external wake. The installed product
readiness warning is limited to the intentionally inactive repo-scoped service;
the enabled user supervisor owns the root and all three enrolled roots are
recent and ready.
