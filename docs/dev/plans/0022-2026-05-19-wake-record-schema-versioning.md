# Wake Record Schema Versioning

State: CLOSED
Lane: P22

## Scope

Document the wake record schema versioning contract and expose the current compatibility policy through the installed CLI.

## Non-Goals

- Do not migrate existing wake records.
- Do not bump `schema_version`.
- Do not add a database or registry format.
- Do not change predicate semantics in this lane.

## Current State

Wake records include `schema_version: 1`. Recent lanes added optional fields such as process identity, app-server dispatch results, context/evidence paths, archive metadata, and hook diagnostics without changing the schema version. The compatibility policy is currently spread across release notes and implementation behavior.

## Design

Keep schema version `1` and document it as an additive JSON object contract:

- required top-level fields stay stable
- unknown fields are preserved by read/write paths where practical
- optional fields may be absent
- new optional fields do not require a schema bump
- breaking field, status, target, or predicate changes require a schema bump and migration note

Add `codex-wake schema` so installed agents can inspect the current record schema policy.

Closed by [Wake Record Schema Versioning](../verification/0022-2026-05-19-wake-record-schema-versioning.md).

## Acceptance Criteria

- `docs/dev/wake-record-schema.md` documents schema version 1.
- The doc lists required fields, status vocabulary, target variants, predicate variants, optional fields, and schema bump triggers.
- `codex-wake schema` prints the current schema version and compatibility policy.
- `codex-wake schema --json` emits machine-readable schema metadata.
- Tests cover the schema summary and CLI command.
- Installed CLI smoke verifies the schema command.

## Definition Of Done

This lane can close when source tests and installed CLI smoke verify the schema command, and verification evidence is recorded.
