# Runtime State, Retention, And Safety

State: CLOSED
Lane: P06

## Scope

Finalize runtime-state layout, retention rules, cleanup behavior, and safety documentation for wake records and ack/log artifacts.

## Non-Goals

- Do not implement app-server transport in this slice.
- Do not expand trigger types in this slice.
- Do not store raw private transcripts or credentials in wake records.

## Current State

The CLI creates wake records, the daemon evaluates predicates and dispatches firing records, the tmux injector handles canonical prompt injection, and the Codex hook writes ack files plus wake context. Runtime state exists under `.codex/wake/`, but retention and cleanup semantics are not yet fully specified or implemented.

## Acceptance Criteria

- Runtime-state directories are documented as authoritative, derived, ephemeral, or sensitive.
- Cleanup/archive behavior is explicit.
- The CLI exposes safe inspection of active and terminal wakes.
- A cleanup or archive command exists, or the plan records why it is deferred.
- Safety documentation states what must never be stored in trigger JSON.
- Tests cover any implemented cleanup/archive behavior.

## Definition Of Done

Closed on 2026-05-18. Operators can understand what wake runtime files mean, what is safe to keep, and how terminal records are retained or archived.
