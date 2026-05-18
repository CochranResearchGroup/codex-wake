# Agent Runtime Governance

## Policy

- Treat delayed wake and resume behavior as an agent lifecycle system with provenance, status, and retention rules.
- Require completion and wake signals to come from runtime state, logs, or transcripts rather than model-written claims alone.
- Define the resume payload shape before relying on it across sessions.
- Keep agent tool access and wake-trigger capabilities explicit.
- Deny destructive, credential, session-management, and live-operation behavior by default unless a documented workflow requires it.
- Prefer shallow orchestration. A wake timer should resume or notify the primary workflow rather than creating unbounded nested agent chains.
- Require timeouts or watchdog expectations for long-running checks.
- Treat transcript cleanup, archive, and deletion as retention decisions.

## Required Runtime Metadata

When available, preserve:

- wake id
- parent session id or session key
- target agent or profile
- trigger type and trigger parameters
- start and finish timestamps
- runtime status
- log or transcript pointer
- result summary and retrieval path
- model, token, or cost metadata if the runtime exposes it

## Handoff Requirements

- A fired wake must produce a deterministic handoff surface that a future TUI-bound Codex agent can inspect.
- A missed or failed wake must be visible as a first-class outcome, not buried in logs.
- Cancellation must be explicit and auditable.
