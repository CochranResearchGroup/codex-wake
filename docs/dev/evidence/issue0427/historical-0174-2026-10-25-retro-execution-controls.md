# Retrospective execution controls

> Historical planning snapshot preserved for issue427. The OPEN wording below
> describes the original October25 planning checkpoint. Current source authority
> is issue350, Plan0175 and merged PR358; this snapshot authorizes no new work.


Work item: RETRO-CONTROLS-DESIGN
State: OPEN — specification published, no implementation claim
Owner: primary agent with operator decisions
Priority: prevent recurrence before another bounded campaign
Base: origin/main 37a5cbb03e1c9e7db5026c99d6dca3cbf443ee5f

## Scope

Turn the October 25 retrospective into an agreed specification and a dependency-aware ticket breakdown. Cover aggregate request admission, compact dispatch, native compatibility preflight, reliable validation receipts, and funding acceptance/review/remediation through closure.

Source: `/tmp/codex-wake-session-retro-20261025/retrospective.md` and its `evidence-index.md`. These temporary artifacts are historical inputs, not runtime authority.

## Non-goals

This planning lane does not renew the exhausted PR348 campaign, close its tickets, change services, unmask the watcher, run provider experiments, or qualify the installed native host. Manual resource monitoring remains authorized for development and repair; it provides observation rather than a hard token cap.

## Verified discovery

- Wake already has an atomic objective reservation ledger in `src/codex_wake/objective_ledger.py` and lifecycle admission in `src/codex_wake/lifecycle_budget.py`. Assess extension rather than assuming a new ledger is required.
- `src/codex_wake/strict_executor.py:47–71` reports `sampled_stop` and no maximum token overshoot. Sampled supervision does not establish synchronous admission before each inference.
- In native prototype `/home/ecochran76/workspace.local/codex-345`, `codex-rs/core/src/client.rs` sends HTTP at line 1414 and WebSocket requests at lines 1602–1608. Instrumentation immediately before those calls is not an admission callback. Retry, fallback, warmup, and ambiguous completion paths need explicit coverage.
- Native response completion can contain usage; missing completion cannot justify refunding a possibly consumed reservation. Request metadata contains session/turn/fork identity but does not establish objective binding.
- These are source observations from a dirty prototype, not proof of a supported hook in the installed host.

## Governing operator decision

The operator clarified: “the governor is to prevent runaway agents not to cause operator friction.” This settles the product priority; the previous three-question approval frontier is withdrawn. Routine architecture and accounting choices are engineering work, not operator approval gates.

Required behavior:

- Apply authorized limits automatically across the objective, including delegates and retries. Do not require the operator to allocate every request or approve routine enforcement steps.
- Carry explicit operator choices forward. Manual monitoring for development/repair is already authorized here; an unavailable or masked watcher must not create a circular gate that prevents its repair or repeats the same permission question.
- Keep monitoring status truthful. Manual observation is not a guaranteed hard cap, and its use does not silently renew an exhausted allowance or change service configuration.
- Contain the affected autonomous work when its limit is reached or its consumption becomes unaccountable. Preserve completed work and explain the concrete stopping reason once. Ask the operator only when progress actually needs new authority or a material choice.
- Qualify available enforcement automatically. Reuse the existing ledger; investigate request-level admission as an engineering option. Do not turn an unproven native hook into a blanket prerequisite for ordinary authorized work.
- Make operation transparent without repeated consent prompts. Both the operator and model must receive explicit notice when the governor is attached or activated, with its scope, active limits, enforcement mode, and available controls. No silent insertion.
- Every intervention must be explicit to both audiences: identify the governor, affected work, trigger and supporting accounting, action taken, and concrete resume/deactivation options. Do not depend on the stopped model producing the operator notice. Missing delivery must remain visible as a failure; recording an event alone is not proof either audience received it.
- Deactivation must be easy: provide a discoverable direct control in the normal operator interface, without requiring service-mask manipulation, shell access, repeated confirmation, or governor approval. Make its scope clear, honor it promptly, and show the resulting inactive state to both operator and model. Do not silently reactivate on continuation, retry, delegate creation, or restart. Preserve accounting/history; deactivation does not replenish an allowance or automatically resume previously stopped work.

## Observable acceptance cases

- Activation visibly identifies the governor and its effective scope/limits to operator and model before it governs work.
- A forced intervention produces an operator-visible explanation even when the model cannot take another turn; the model receives the intervention state on its next available interaction.
- Operator deactivation through the normal interface takes effect without a shell workaround or repeated approval loop, reports any failure explicitly, and prevents further governor intervention in the selected scope.
- Retry, continuation, delegation, and restart preserve the explicit deactivation choice until an explicit activation or operator change of scope; existing accounting remains intact.
- Tests distinguish durable event creation, model delivery, and operator rendering. None alone proves all three.

## Remaining engineering work

Define observable runaway conditions and containment actions; establish which guarantees each supported host can actually provide; specify aggregate accounting, retry/failure semantics, and automatic fallback behavior. Derive compact dispatch, preflight, reliable validation, and completion funding slices from the retrospective. Escalate only a concrete unresolved product tradeoff, not an implementation detail.

## Acceptance and definition of done

The operator confirms the shared design; an implementable specification names ownership, unsupported-host behavior, accounting bounds, failure semantics, and public test seams; the proposed vertical ticket slices have real blocking edges and measurable acceptance. Publishing tickets and implementation follow their respective approval boundaries. No implementation completion is claimed by this document.

## Current state and next action

Read-only discovery complete for the first frontier. Planning branch is `docs/retro-execution-controls` in the isolated `codex-wake-retro-controls` worktree. Operator priority, explicit activation/intervention transparency, and easy persistent deactivation recorded; the redundant approval frontier is withdrawn. Next: derive a concrete behavior specification and bounded acceptance cases from this priority; retain the separate implementation authorization boundary.

Memory disposition: forbidden — this round records the decision in the project plan only; developer instructions require an explicit user request before updating persistent memories.

## Specification publication

Canonical specification: https://github.com/CochranResearchGroup/codex-wake/issues/350. Published as `ready-for-agent`; issue body and label read back against the prepared body. Local specification snapshot: `0174-2026-10-25-retro-execution-controls-spec.md`. The earlier next-action text is superseded: specification synthesis is complete; public acceptance seam is proposed for operator review, and ticket decomposition remains a subsequent workflow.
