# Codex Wake

## Repo Context

- Describe the product area, architecture boundaries, and canonical planning surfaces here.

## Repo-Specific Guidance

- Add the exact build, test, deploy, and service-boundary rules this repo expects.

## Policy Loading Contract

- `AGENTS.md` is a routing surface, not a one-time pointer.
- Re-read the relevant policy files under `docs/dev/policies/` at the start of any non-trivial turn.
- Re-read the relevant policy files when task scope changes mid-session.
- When behavior is ambiguous, prefer re-reading policy over improvising from stale assumptions.

## Policy Re-read Triggers

- re-read planning-related policy before opening, revising, or closing a substantive plan
- re-read documentation-related policy before changing docs, contracts, or canonical authorities
- re-read validation and closeout policy before claiming work complete
- re-read branch, commit, and integration policy before starting a multi-file or multi-step implementation slice

## Policy Entry

This repo keeps its durable repo-local policy under `docs/dev/policies/`.

Read and follow:
- `docs/dev/policies/0001-policy-selection.md`
- `docs/dev/policies/0002-planning-and-documentation.md`
- `docs/dev/policies/0003-runtime-state-and-wake-semantics.md`
- `docs/dev/policies/0004-agent-runtime-governance.md`
- `docs/dev/policies/0005-engineering-git-and-release.md`
- `docs/dev/policies/0006-validation-and-closeout.md`
- `docs/dev/policies/0007-graph-backed-memory-usage.md`
- `docs/dev/policies/0008-codegraph-usage.md`
- `docs/dev/policies/0009-goal-execution-governance.md`
- `docs/dev/policies/0010-policy-management.md`
- `docs/dev/policies/0011-policy-adoption-feedback-loop.md`
- `docs/dev/policies/0012-notes-and-memories.md`
- `docs/dev/policies/0013-planning-discipline.md`
- `docs/dev/policies/0014-architecture-guardrails.md`
- `docs/dev/policies/0015-turn-closeout.md`
- `docs/dev/policies/0016-policy-management.md`
- `docs/dev/policies/0017-policy-upgrade-management.md`
- `docs/dev/policies/0018-policy-adoption-feedback-loop.md`
- `docs/dev/policies/0019-notes-and-memories.md`
- `docs/dev/policies/0020-graph-backed-memory-usage.md`
- `docs/dev/policies/0021-codegraph-usage.md`
- `docs/dev/policies/0022-planning-discipline.md`
- `docs/dev/policies/0023-goal-execution-governance.md`
- `docs/dev/policies/0024-parallel-plan-design.md`
- `docs/dev/policies/0025-roadmap-runbook-governance.md`
- `docs/dev/policies/0026-architecture-guardrails.md`
- `docs/dev/policies/0027-documentation-change-control.md`
- `docs/dev/policies/0028-git-worktree-hygiene.md`
- `docs/dev/policies/0029-active-lane-coordination.md`
- `docs/dev/policies/0030-commit-history-discipline.md`
- `docs/dev/policies/0031-branch-and-integration-strategy.md`
- `docs/dev/policies/0032-commit-and-push-cadence.md`
- `docs/dev/policies/0033-multi-agent-reconciliation.md`
- `docs/dev/policies/0034-subagent-workflow-optimization.md`
- `docs/dev/policies/0035-versioning-and-release.md`
- `docs/dev/policies/0036-turn-closeout.md`
- `docs/dev/policies/0037-validation-and-handoff.md`
- `docs/dev/policies/0038-subagent-runtime-governance.md`

## Scope

- `AGENTS.md` includes repo-local guidance plus the policy entry section.
- The durable policy body lives under `docs/dev/policies/`.
- Keep repo-specific commands, environment details, and operational caveats in this file or adjacent local docs.
