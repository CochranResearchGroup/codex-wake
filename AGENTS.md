# Codex Wake

## Repo Context

- Codex Wake is a local, durable wake scheduler for resuming agent work through
  tmux, Codex app-server, or OpenClaw Gateway targets.
- `ROADMAP.md` owns product priority, `RUNBOOK.md` owns chronological execution
  history, and bounded plans under `docs/dev/plans/` own implementation scope.
- GitHub Issues are the coordination ledger. Git branches, pull requests,
  checks, merge ancestry, and release receipts prove implementation custody.

## Repo-Specific Guidance

- `origin/main` is the canonical integration branch. Substantive changes use a
  linked GitHub issue, scoped branch, and pull request; do not push directly to
  `main`.
- Prefer squash merge for independently mergeable slices. Do not rewrite a
  published branch after another lane or review surface depends on its tip.
- Run `PYTHONPATH=src python -m unittest discover -s tests -p 'test_*.py'` for
  the comprehensive Python test tier and `npm --prefix
  plugins/openclaw-codex-wake test` for the OpenClaw plugin tier.
- Treat live dispatch, installed-runtime changes, releases, and provider
  mutations as separate effects with their own authority and readback.
- The default product-development execution bias is `balanced`. Keep one
  primary coordination owner, use at most three concurrent subagents per lane,
  and avoid nested subagents unless a plan defines the topology and result flow.

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
- `docs/dev/policies/0016-code-testing-discipline.md`
- `docs/dev/policies/0017-work-item-traceability.md`
- `docs/dev/policies/0018-model-selection-and-calibration.md`
- `docs/dev/policies/0019-forge-issue-reporting.md`
- `docs/dev/policies/0020-github-issue-operations.md`
- `docs/dev/policies/0021-collaborative-development-workflow.md`

## Scope

- `AGENTS.md` includes repo-local guidance plus the policy entry section.
- The durable policy body lives under `docs/dev/policies/`.
- Keep repo-specific commands, environment details, and operational caveats in this file or adjacent local docs.
