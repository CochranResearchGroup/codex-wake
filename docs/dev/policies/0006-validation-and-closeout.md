# Validation And Closeout

## Policy

- Validate the surface that users or agents will actually run, not only helper functions.
- For runtime changes, verify installed commands, local service behavior, scheduler behavior, or executable entrypoints as applicable.
- Use focused tests for narrow behavior and broader end-to-end checks when changing state schema, trigger semantics, or resume handoff.
- Record known validation gaps plainly in closeout.
- Do not claim a wake feature works unless a deterministic trigger can be registered, observed, and resolved.

## Minimum Wake-Timer Validation

Before marking an implementation slice complete, verify:

- a wake request can be created
- the wake request persists across process boundaries when persistence is in scope
- trigger evaluation changes status deterministically
- the resume or handoff payload is inspectable by a later agent
- cancellation or timeout behavior is defined and covered when implemented

## Turn Closeout

Closeouts should include:

- files changed
- selected validation commands and outcomes
- known gaps or deferred risks
- next concrete implementation slice when useful
