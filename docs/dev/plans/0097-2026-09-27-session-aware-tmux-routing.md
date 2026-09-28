# Session-aware tmux wake routing

State: CLOSED
Lane: I172
Issue: #172
Branch: `fix/issue-172-session-aware-tmux`
Target: `main`
Integration: `squash`

## Current state

Tmux wake records bind only a socket and pane ID. Dispatch confirms that the
pane looks idle, but it does not confirm that the pane still represents the
Codex thread that created the wake. Codex exposes the durable thread ID at
creation and the app-server can read that exact thread's current identity
metadata, while tmux exposes the panes within the captured session.

The implementation and provider-free acceptance are complete. Creation
resolves inherited tmux location hints to the exact thread's unique pane and
stores the Codex client PID plus process start-time ticks. Dispatch validates
that process identity and exact-thread metadata before paste, finds a unique
relocation, or uses exact-thread app-server fallback. Focused tests pass
117/117 and the comprehensive suite passes 713/713; compilation, diff hygiene,
and active/goal planning audits pass. PR #173 passed hosted Python 3.11 and
3.12 gates and squash-merged as canonical `f18ca5e`; canonical main run
`36364547676` passed both gates and issue #172 is closed.

## Objective

Bind tmux wakes to the creating Codex thread, route to a unique matching pane
when the thread moves, and otherwise fall back to app-server dispatch for the
same exact thread without ever pasting into a stale or ambiguous pane.

## Scope

- Persist the creating Codex thread ID on tmux targets.
- Resolve pane identity from exact-thread app-server metadata and current tmux
  pane metadata within the originally captured tmux session.
- Route to the original pane, a unique relocated pane, or exact-thread
  app-server fallback; fail closed on ambiguity or unavailable fallback.
- Record route-selection evidence separately from transport-specific delivery
  and visibility evidence.
- Cover the issue's provider-free routing and contention cases.

## Non-goals

- No live wake dispatch, service/install mutation, release, or deployment.
- No pane-title-only authority when multiple panes share the same identity
  fingerprint.
- No relaxation of unsafe-pane, acknowledgement, active-writer, or retry
  safeguards.
- No inference of identity from repository cwd alone.

## Architecture rules

- The durable thread ID is the authority; the captured pane is a location hint.
- A pane is eligible only when it uniquely matches metadata read from that
  exact thread. Zero matches selects exact-thread app-server fallback; multiple
  matches fail closed without paste or fallback.
- App-server fallback reuses the existing preflight, active-writer, bounded
  retry, acknowledgement, and evidence implementation.
- Route selection is recorded independently from tmux visibility or app-server
  acknowledgement evidence.

## Execution packets

1. Freeze creation and routing behavior with focused regression tests.
2. Implement session capture, tmux-session enumeration, unique matching,
   relocation, ambiguity handling, and exact-thread fallback.
3. Update schema/operator documentation and run focused, comprehensive,
   compilation, planning, and diff-hygiene checks.

The primary agent owns the shared routing contract and integration. No worker
lane is planned because record creation, dispatch mutation, and route evidence
share one safety boundary.

## Acceptance criteria

- Tmux wake creation records the durable Codex thread ID.
- Dispatch validates the original pane and searches the captured tmux session
  for one matching relocated pane before any paste.
- Reused foreign panes receive no wake text.
- Zero pane matches falls back to the exact recorded app-server thread;
  ambiguous pane matches fail closed.
- Evidence distinguishes original pane, relocated pane, app-server fallback,
  ambiguous match, and no valid target.
- Visibility and acknowledgement evidence remains transport-specific.
- Focused tests cover unchanged, moved, foreign/reused, unique relocated,
  ambiguous, fallback success, active-writer contention, and no fallback.
- Comprehensive tests, compilation, planning audit, and hosted CI pass before
  integration.

## Goal controls

```text
goal_id: P59-G1
goal_version: P59-G1-v1
max_work_unit_attempts: 2
max_review_rework_cycles: 1
max_hardening_checkpoints: 2
max_review_discovery_passes: 1
checkpoint_interval: 1 execution packet or material gate
concurrency_limit: 1 primary lane
live_dispatch_attempts: 0
service_or_install_mutations: 0
authorization_gate: material_departure_or_explicit_action_gate_only
review_verification_mode: closed_world_if_reviewed
checkpoint_fields: state_transition, acceptance_state, progress_classification, evidence, material_blockers, next_action_or_stop_reason
```

## Next action

No further action is required for Plan 0097. Release, installation, or live
dispatch qualification remains separate scope.
