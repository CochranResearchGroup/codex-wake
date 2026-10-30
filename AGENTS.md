# Codex Wake

## GitHub CI cost policy

- The operator does not pay for GitHub Actions CI. Skip hosted GitHub CI and run the applicable checks locally instead.
- Documented passing local checks satisfy CI validation for review, merge and release. Billing or spending limits that prevent hosted checks from starting are not a blocker and require no repeated approval.
- Record commands, results, source commit and material differences from the hosted environment. Resolve actual local failures before declaring validation complete.
- Do not purchase CI capacity, change billing settings or enable paid runs. Merge, deployment and live effects retain their separate authorization requirements.

## Repo Context

- Codex Wake provides durable triggers and agent-to-agent mailbox delivery.
- ROADMAP.md owns sequencing; RUNBOOK.md records execution; docs/dev/plans/ owns bounded plans.

## Repo-Specific Guidance

- CI commands live in .github/workflows/ci.yml. Runtime acceptance must identify the installed prefix and preserve unrelated sessions/services.

## Policy Loading Contract

- `AGENTS.md` is a routing surface, not a one-time pointer.
- For policy-maintenance tasks, call governance `gov_policy` with profile
  `codex-wake-policy-maintenance` and task_kind `policy-maintenance`.
  On first use or context loss set `include_source_text:true` and consume every
  selected section. Reuse `known_decision_digest` only with that exact consumed
  packet retained and unchanged action facts. Compact output is a freshness check.
- On unavailable, stale, invalid, conflicted, or out-of-scope responses, read
  canonical fallback paths; if no packet is available, use the policy list below.
- For other tasks, read the relevant canonical policy files directly. Scope
  expansion requires loading additional policies; the pilot grants no authority.
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
- `docs/dev/policies/0016-code-testing-discipline.md`
- `docs/dev/policies/0017-work-item-traceability.md`
- `docs/dev/policies/0018-model-selection-and-calibration.md`
- `docs/dev/policies/0019-forge-issue-reporting.md`
- `docs/dev/policies/0020-github-issue-operations.md`
- `docs/dev/policies/0021-collaborative-development-workflow.md`
- `docs/dev/policies/0022-policy-context-pilot.md`

## Scope

- `AGENTS.md` includes repo-local guidance plus the policy entry section.
- The durable policy body lives under `docs/dev/policies/`.
- Keep repo-specific commands, environment details, and operational caveats in this file or adjacent local docs.

## Agent skills

GitHub Issues at CochranResearchGroup/codex-wake owns intake and discussion;
repository plans, ROADMAP and RUNBOOK retain execution and evidence authority.
See docs/agents/issue-tracker.md and docs/agents/triage-labels.md.
Single-context terminology uses existing GLOSSARY.md; see docs/agents/domain.md.
Codex discovery/runtime rules: docs/agents/codex-stack.md,
docs/agents/codex-code-discovery.md and docs/agents/runtime-proof.md.
Existing docs/dev/policies remain the policy authority.
