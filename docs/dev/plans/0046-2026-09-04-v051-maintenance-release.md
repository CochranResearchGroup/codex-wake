# v0.5.1 Maintenance Release

Date: 2026-09-04

Status: OPEN

## Objective

Publish the accumulated maintenance work as `v0.5.1`, then refresh and verify
the user-scoped CLI, hook, skills, supervisor, and OpenClaw plugin from the
public tag.

## Current State

`main` contains the closed P44 and P45 changes plus eleven unpublished
maintenance commits. `origin/main` is not ahead, so the history can be pushed
without rebasing or force-pushing. Package and plugin metadata have been
prepared for `0.5.1`; publication and installed readback remain open.

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
