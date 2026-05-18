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
