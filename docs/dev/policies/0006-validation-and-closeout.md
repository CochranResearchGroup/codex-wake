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

## Daemon build installation gate

Operator direction, 2026-10-28: qualify daemon build effects in either the separate real Linux test user or disposable `wsl-test` before installation on the working account. Private protocol fixtures and a successful updater exit are insufficient.

- Test the exact immutable complete package by executable hashes, using the actual launcher/profile wiring and supported updater in disposable test state.
- Seed synthetic session history across the relevant default/account/shared paths; verify resume-list visibility and opening existing sessions before and after upgrade and rollback. Never copy production credentials or raw private histories into fixtures.
- Exercise multiple clients, an active conversation, reconnect, and private-client ownership locks. Verify how interruption is communicated and that a refused launch identifies the lock owner and an actionable recovery path.
- Qualify an explicit supported rollback to the previous complete package, including failed-start recovery, launchability, session visibility and final process/resource census.
- Preserve governor state, grants, cumulative budgets and supervision records. Record any intentional interruption separately from recovered continuity.
- Retain a machine-readable receipt identifying environment, source/build hashes, updater outcome, launch/history/reconnect checks, rollback outcome and final owned processes. Any failed or unknown acceptance gate blocks working-host installation.
- Record the qualified result before proposing working-host installation. Test qualification alone does not initiate installation.

Operator correction, 2026-10-29: either separate real Linux test user OR disposable wsl-test is sufficient; both are not required. Use codex-daemon-test UID1017 for current qualification. A second Codex account under the working UID is insufficient. Report shared-kernel/resource limitations explicitly.
