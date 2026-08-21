# Policy Selection

## Selected Bundle

This repo adopts a custom composition from the local `repo-policy-selector` library.

Deterministic selector result on an empty repo:

- inferred purpose: `library-cli`
- recommended profile: `standalone-library`
- reason: the repo had no source, roadmap, runbook, or policy surfaces yet

Repo-purpose override from the user-stated goal:

- inferred purpose: `product-engineering`
- workflow subtype: agent-runtime infrastructure
- selected base profile: `repo-product-engineering`
- selected overrides: `runtime-state-governance`, `subagent-runtime-governance`

## Adopted Modules

- `policy-management`
- `policy-upgrade-management`
- `policy-adoption-feedback-loop`
- `notes-and-memories`
- `planning-discipline`
- `parallel-plan-design`
- `roadmap-runbook-governance`
- `architecture-guardrails`
- `documentation-change-control`
- `git-worktree-hygiene`
- `commit-history-discipline`
- `branch-and-integration-strategy`
- `commit-and-push-cadence`
- `multi-agent-reconciliation`
- `subagent-workflow-optimization`
- `runtime-state-governance`
- `subagent-runtime-governance`
- `versioning-and-release`
- `turn-closeout`
- `validation-and-handoff`

## Adoption Rules

- Keep durable repo policy under `docs/dev/policies/`.
- Keep `AGENTS.md` as the wire-in entrypoint with repo-specific guidance.
- Preserve local nuance when shared policy and repo-specific wake-timer requirements conflict.
- Record meaningful policy friction in `docs/dev/notes/` so the policy selection can be revisited later.
- Treat the policy library as a source library; the repo-local files are the operating contract for this repo.
# Policy | Parallel Plan Design

## Policy

- Give each parallel lane a clear owner, bounded scope, and expected write surface.
- Keep the critical path visible so parallel work does not hide the real blocker.
- Prefer plan slices that minimize cross-lane file overlap and reconciliation cost.
- Call out integration points explicitly when multiple lanes must converge before completion.
- Express non-trivial execution as inspectable work units and dependency edges,
  including fan-out, join, review, retry, and terminal transitions. A table or
  plan section is sufficient; a graph framework is not required.
- Do not open parallel lanes just because tools allow delegation; open them only when the work can move independently.
- If a lane becomes coordination-heavy, collapse it back into the critical path or redefine the lane boundary.
- Declare the intended active-agent concurrency before spawning many subagents or parallel workers.
- Cap active subagents per plan lane unless the repo explicitly optimizes for `max-dev-speed` and has strong reconciliation rules.
- Avoid nested subagents by default.
- Use nested or orchestrator subagents only when the plan names the parent orchestration role, child scopes, result-flow path, and synthesis responsibility.
- Treat high fan-out as a plan smell unless the subtasks are independent, low-conflict, and cheap to verify.
- Put a semantic exit condition and a hard bound on every review, retry, repair,
  or agent-handoff edge that can cycle back to prior work.
- Reaching a local loop bound ends or reframes that loop; it does not create a
  user-approval gate by itself. Continue another safe in-scope route when one is
  available, and escalate only when no meaningful route remains or an exact
  action-specific boundary requires a user decision.
- When a work unit cannot be bounded or has too many coupled write surfaces,
  return it for split/reframe before spawning workers.
- Delegate only concrete, bounded subtasks that materially advance the active slice.
- At the start of non-trivial work and after material replanning, consider
  whether delegation would create a genuinely useful independent lane. This is
  an execution choice, not a user-approval event.
- When subagent tooling and capacity are available, spawn without additional
  user prompting if at least one useful bounded lane exists, such as:
  - independent discovery or evidence collection off the immediate critical path
  - implementation with a disjoint write surface
  - context-heavy work that benefits from an isolated context window
  - independent validation, audit, or adversarial review
- Record a non-delegation reason only when a plan expected a worker or the lack
  of delegation materially affects timing, independence, or evidence. Do not
  create a `not_spawned` receipt for every routine packet.
- When delegation occurs, leave a durable receipt for consequential work:
  record the bounded lane, available agent/run/session handle, terminal status,
  evidence returned, and the primary agent's reconciliation decision.
- Keep urgent blocking work local when the next action depends directly on the answer.
- Give delegated work explicit ownership, expected output, and write scope.
- Prefer subagents for independent sidecar work, verification, or implementation slices with disjoint write sets.
- Do not spawn parallel work that duplicates context loading or repeats the same exploration without a clear benefit.
- Reuse prior agent context when the task is a continuation of the same bounded thread.
- Prefer fresh context when independence is part of the value: neutral review,
  adversarial audit, a newly split work unit after drift, or a handoff intended
  to shed accumulated context and assumptions.
- For a fresh reviewer, provide a frozen review packet: objective, acceptance
  criteria, non-goals, target identity or commit, applicable gates, review mode,
  and—during remediation verification—the accepted finding ledger. Ask for
  evidence-shaped candidate findings and explicitly permit a no-finding result.
- A reviewer detects drift; it does not own scope, finding disposition, goal
  authority, or operator approval. The primary agent reconciles the result and
  may reject, backlog, or seek evidence for a candidate that does not satisfy
  the frozen contract.
- Do not turn reviewer completion, reviewer agreement, or a second reviewer
  opinion into a prerequisite for obvious low-risk progress unless an explicit
  acceptance or safety contract requires that review.
- Use broad fresh context for the initial drift scan. Use closed-world prompts
  for later verification and carry the same finding identifiers across worker
  replacement, plan revisions, and successor packets so review discovery does
  not restart accidentally.
- Keep final integration responsibility with the primary agent even when subagents perform part of the work.
- Be explicit about whether the repo optimizes for wall-clock speed, token efficiency, or a balance of the two.
- Treat spawned subagents as asynchronous runtime artifacts, not just informal delegation.
- Record the subagent run id, session id, transcript path, or equivalent handle when the runtime provides one.
- Do not assume delegated work completed until an announce payload, status check, log read, or transcript inspection confirms completion.
- A plan that merely names a subagent role is design evidence, not proof that a
  worker ran. Effectiveness claims require a runtime handle or an explicit
  unavailable-runtime receipt plus the resulting integration decision.
- For critical or high-risk delegated work, inspect the transcript or logs instead of relying only on a summarized announce.
- Prefer subagent closeout that includes status, result, notes, and available runtime, token, or cost metadata.
- Set explicit timeout expectations for long-running, slow-tool, or uncertain delegated work.
- Give each subagent a stop condition and require it to return partial evidence
  rather than self-extending into adjacent work when the bound is reached.
- Use lower-cost or lower-reasoning models for bounded sidecar work only when the quality risk is low; keep synthesis, architecture, and final integration on an appropriately capable model.
- Treat subagent cleanup and transcript retention as deliberate choices when later evidence or reconciliation may matter.
- Run the relevant validation for the touched surface before commit, handoff, or merge preparation.
- Prefer targeted verification that matches the changed area, and widen to broader suites when the impact is user-visible or cross-cutting.
- Include concrete pass/fail evidence in the handoff or closeout note.
- Keep handoff notes concise, explicit about remaining risk, and clear about the next recommended action.
- When live or manual smoke matters for the changed surface, record whether it was run and what it proved.
- Prefer validation receipts that bind the result to a durable commit, artifact,
  installed version, endpoint response, or other current-state identifier.
  Temporary paths alone are not durable handoff evidence; preserve or publish
  the necessary artifact in a repo-approved location, or record why the proof
  is intentionally ephemeral and how it can be reproduced.
- Distinguish validation run by the primary agent from validation reported by a subagent or delegated worker.
- If validation was delegated, record whether the primary agent independently verified the result or accepted the delegated evidence as-is.
- For failed, timed-out, incomplete, or unknown subagent statuses, state what was trusted, what was ignored, and what remains unverified.
- Use an independent evaluator when fresh judgment materially reduces risk or
  uncertainty, or when an explicit acceptance contract requires it. Duration or
  plan count alone does not make independent review mandatory for routine,
  low-risk work.
- Treat evaluator output as candidate evidence, not an automatic veto. The
  primary agent owns adjudication and records each candidate as `blocking`,
  `nonblocking_backlog`, `rejected`, or `needs_evidence` against the frozen
  objective, acceptance criteria, non-goals, and applicable safety controls.
- A reviewer is not an approver. Work may continue on unaffected in-scope units
  while candidates are adjudicated, and only an accepted blocking finding may
  block the action or criterion it actually affects.
- Require each candidate finding to state the criterion, evidence, consequence,
  reproducer, confidence, and suggested disposition. A useful independent
  review may return no findings; novelty and finding count are not quality
  metrics.
- Separate review modes. Use at most one broad fresh-context `drift_discovery`
  pass when observed drift, consequence, or uncertainty justifies it. After
  adjudication, use `closed_world` remediation
  verification limited to accepted blocking findings and critical regressions
  introduced by their fixes. Do not reopen broad discovery merely because a
  new evaluator performs final verification.
- Bound review and rework at the goal level, not only per plan version. Prefer
  one consolidated candidate set and one bounded remediation pass; if accepted
  blocking findings still fail verification, split, reframe, or block the unit
  instead of continuing an open-ended evaluator/optimizer loop. Record
  nonblocking concerns in backlog without silently expanding the active plan.
- A review or rework bound ending triggers primary-agent disposition, local
  reframe, or a scoped block. It does not consume goal authority or require user
  approval when another safe in-scope action remains.
- Validate the resulting outcome and current external state, not only the
  transcript, diff shape, test count, or agent's narrative of progress.
- Treat fail-closed gates as successful policy execution when they prevent an
  unsafe or disproven change from integrating. Report the blocked outcome and
  evidence instead of grading effectiveness only by shipped changes.
- Use this contract in repositories where several projects, agents, branches, or worktrees may remain active at once. Keep lighter repositories on proportional planning and Git policy without requiring a lane catalog.
- Keep a compact machine-readable active-lane catalog on the canonical default branch, normally `docs/dev/active-lanes.yaml`. A documented equivalent path is allowed.
- Treat the catalog as a discovery projection. A roadmap owns priority, a branch-local plan owns execution detail, a runbook owns chronological history, review tooling owns review state, and Git refs plus receipts prove custody and integration.
- Give each lane one stable id and one branch owner. Record its objective, plan path and source ref, branch, target, plan state, custody state, published checkpoint, remote ref, integration method, dependencies, overlaps, reconciliation date, and any blocker or disposition.
- Keep plan outcome state separate from Git custody state. Use a small plan vocabulary such as `PLANNED`, `OPEN`, `BLOCKED`, `CLOSED`, and `CANCELLED`, and a custody vocabulary such as `ACTIVE_WORKTREE`, `PAUSED_REF`, `INTEGRATION_READY`, `INTEGRATED`, `ARCHIVED`, and `DISCARD_APPROVED`.
- Keep detailed plans with their topic branches. Expose deterministic metadata for lane, state, branch, target, integration method, dependencies, overlaps, and base or checkpoint evidence so an auditor can read it from an explicit ref without checkout.
- Do not put absolute worktree paths, ephemeral agent identifiers, secrets, tenant data, or private runtime details in the shared catalog. Derive local worktree locations during reconciliation.
- Reconcile the catalog against current worktrees, bounded local and remote refs, branch-local plan metadata, checkpoint SHAs, target ancestry, receipts, dependencies, and overlap before planning, handoff, integration, or cleanup decisions. Prefer catalog-only discovery when the catalog is the complete authorized population; use exact repeated branch selectors for bounded unregistered-lane discovery. Prefix discovery is an explicit broader survey and should not be the default in repositories with large historical branch namespaces.
- For active worktree custody, classify equal, local-ahead, remote-ahead, and diverged local/remote tips explicitly. Local-ahead, remote-ahead, and diverged state fail closed until the lane owner reconciles and publishes the intended checkpoint.
- Fetching is a caller-controlled operation. A lane auditor must remain read-only and must not fetch, merge, rebase, push, delete refs, remove worktrees, edit plans, or infer authority from a clean report.
- Register normal work before parallel execution begins. An urgent lane may start first only when delay creates greater risk; register and publish its first recoverable checkpoint at the earliest safe boundary.
- Do not silently resolve catalog conflicts. Duplicate lane ids, two lanes claiming one branch, missing custody, stale checkpoints, active local/remote mismatch, plan/catalog drift, and unresolved overlaps fail closed until reconciled.
- Keep the catalog current through the repository's protected-default-branch workflow. A lane branch may propose its own registration, but it is not globally discoverable until that projection lands on the configured default ref.

## Adoption Notes

Use this module when repos regularly use subagents, parallel contributors, or multiple active implementation lanes.

Execution-bias guidance:
- `max-dev-speed`: open more parallel lanes when ownership and write surfaces are clear enough to keep wall-clock time down
- `balanced`: parallelize bounded sidecar work but keep urgent blockers and tightly coupled work on the critical path
- `max-token-efficiency`: keep fewer active lanes, prefer larger local ownership, and avoid parallel decomposition that duplicates context or creates heavy reconciliation work
