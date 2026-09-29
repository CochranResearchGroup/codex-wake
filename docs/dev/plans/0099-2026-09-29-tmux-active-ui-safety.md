# Tmux active-UI safety and dispatch accounting

State: CLOSED
Lane: P61
Issue: #178
Branch: `chore/issue-178-live-acceptance`
Target: `main`
Integration: `squash`

## Current state

The product correction squash-merged through PR #179 as canonical
`5abbc098d4c0f6832b10818755602630f2528ecc`. Hosted Python 3.11 and 3.12
checks passed. A separately isolated live acceptance consumed one genuine
AuraCall terminal `error` receipt without retrying AuraCall and delivered wake
`wake_59378fecd82144b288c326d4e95b6f98` to disposable tmux pane `%27`.
The classifier now inspects the final 12 non-empty lines, requires recognizable
question structure for approval/confirmation rules, and emits privacy-safe rule
and region metadata. Unsafe-pane preflight increments a separate bounded
`safety_deferrals` counter without emitting `dispatch_attempt` or consuming
`attempts`; three consecutive unsafe results fail deterministically. Focused
injector tests pass 24/24, the comprehensive Python suite passes 716/716, the
OpenClaw plugin suite passes 12/12, and compilation, diff hygiene, active
planning, and goal audits pass. The live record reports `attempts: 1`,
`ack_observed`, verified bounded HTTP/JSON evidence, and
`visible_prompt_observed`; raw pane text was not stored. Verification receipt
0093 contains the bounded closeout evidence.

## Objective

Distinguish active tmux approval/confirmation UI from inert transcript history,
record privacy-safe classifier evidence, and keep bounded safety unavailability
separate from actual prompt-delivery attempts.

## Scope

- Replace whole-capture isolated-word matching with bounded active-region rules
  that require recognizable interactive prompt structure.
- Preserve fail-closed handling for genuine approval, confirmation, running-tool,
  and foreign shell surfaces.
- Record a stable rule identifier and bounded-region metadata without storing
  raw pane text.
- Requeue transient unsafe-pane results without consuming an actual delivery
  attempt; retain a bounded retry count so persistent unsafe state terminates.
- Add public-behavior regressions through `unsafe_pane_reason()` and
  `dispatch_firing_record()`.

## Non-goals

- No live AuraCall trigger, target dispatch, installed-runtime mutation, service
  restart, release, or deployment without a separately frozen live packet.
- No storage of raw pane captures or matching line contents.
- No redesign of app-server or OpenClaw transports.

## Execution packet

1. Add one benign-transcript classifier regression and make it pass.
2. Add one dispatch regression proving unsafe preflight does not consume the
   sole delivery attempt, while persistent unsafe state remains bounded.
3. Add privacy-safe classifier evidence and preserve genuine prompt rejection.
4. Run focused injector tests, comprehensive Python and plugin suites,
   compilation, diff hygiene, and planning audits.
5. Publish the issue-linked pull request; run the live AuraCall/tmux acceptance
   only under a fresh named-target authority gate.

## Bounds

- `max_work_unit_attempts: 2`
- `max_review_rework_cycles: 1`
- `max_hardening_checkpoints: 2`
- `checkpoint_interval: 2 slices`
- `live_dispatch_attempts: 1` in the separately frozen acceptance packet

## Acceptance criteria

- Benign command flags and explanatory prose containing `approval` leave an
  otherwise idle pane safe.
- A genuine active `Approve command?` surface remains unsafe.
- Classification examines only a bounded active region using recognizable UI
  structure, not isolated words across the whole capture.
- Unsafe classification records privacy-safe rule and region evidence.
- Unsafe preflight does not consume `attempts`; persistent unsafe state uses a
  separate bounded counter and reaches a deterministic terminal state.
- Focused and comprehensive local validation passes.
- A live AuraCall-origin tmux wake with acknowledgement and
  `visible_prompt_observed` is either recorded under a fresh live gate or
  remains explicitly pending without weakening product acceptance claims.

## Definition of done

The product fix and deterministic regressions are integrated through the
issue-linked pull request with hosted checks passing. The separately gated
live AuraCall/tmux acceptance receipt is recorded in verification 0093, so no
successor issue is required.
