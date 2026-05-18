# App-Server Controlled Mode

State: OPEN
Lane: P07

## Scope

Design and implement the app-server transport path for controlled wake dispatch without tmux paste heuristics.

## Non-Goals

- Do not expose app-server over non-local networks without auth and TLS.
- Do not remove the tmux MVP path in this slice.
- Do not implement unrelated Codex session-management behavior.

## Current State

The tmux MVP can create wake records, evaluate predicates, inject canonical prompts, observe hook acks, and archive terminal records. App-server controlled mode is only documented as the preferred future transport.

## Acceptance Criteria

- Current Codex app-server request/response contract is verified from official docs or local CLI behavior.
- Target records can represent app-server transport without breaking tmux records.
- App-server dispatch is implemented or a precise implementation-blocker note is recorded.
- Safety boundaries for localhost, SSH forwarding, auth, and TLS are documented.
- Tests cover app-server target records and dispatch behavior where implementation is possible.

## Definition Of Done

The plan can close when app-server mode has a verified contract and either a working controlled dispatch path or a concrete blocker with next steps.
