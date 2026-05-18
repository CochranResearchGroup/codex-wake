# Codex Wake

## Repo Context

This repo is for designing and building a local wake-timer tool for TUI-bound Codex agents. The tool should let an agent register a durable wake request so future agent work can resume a long job, check an outcome, or react to a defined trigger.

The product surface is agent-runtime infrastructure, not ordinary application state. Treat wake registration, trigger evaluation, resume payloads, and completion evidence as durable operational contracts.

## Policy Loading Contract

- `AGENTS.md` is the repo entrypoint, not the full policy body.
- Re-read the relevant files under `docs/dev/policies/` at the start of any non-trivial turn.
- Re-read the relevant policy files whenever task scope changes, especially when moving between design, implementation, runtime state, and validation work.
- When behavior is ambiguous, prefer the policy files and repo-local docs over assumptions from chat history.

## Selected Policy Profile

Adoption shape: custom composition.

Base profile: `repo-product-engineering`, because this repo is expected to develop an agent-facing tool with planning, validation, release, and architecture decisions.

Overrides:

- Add `runtime-state-governance` because wake requests and scheduler state must be classified as durable, derived, ephemeral, or sensitive.
- Add `subagent-runtime-governance` because the tool exists to coordinate agent lifecycle across delayed execution.
- Keep `standalone-library` concerns for packaging and versioning when the CLI/library shape becomes concrete.

## Policy Entry

Read and follow:

- [Policy Selection](docs/dev/policies/0001-policy-selection.md)
- [Planning And Documentation](docs/dev/policies/0002-planning-and-documentation.md)
- [Runtime State And Wake Semantics](docs/dev/policies/0003-runtime-state-and-wake-semantics.md)
- [Agent Runtime Governance](docs/dev/policies/0004-agent-runtime-governance.md)
- [Engineering, Git, And Release](docs/dev/policies/0005-engineering-git-and-release.md)
- [Validation And Closeout](docs/dev/policies/0006-validation-and-closeout.md)

## Repo-Specific Guidance

- Design wake timers as durable operational records with explicit ownership, trigger semantics, status transitions, and audit evidence.
- Do not treat a model-written intention to wake up later as sufficient; the wake request must be materialized in a deterministic local state surface.
- Prefer small, inspectable state files or a simple local database over opaque scheduler state unless a later plan justifies the tradeoff.
- Keep human-private prompts, secrets, raw transcripts, and credential material out of tracked repo files.
- Before claiming runtime behavior works, verify the installed or executable surface, not only the source tree.

## Policy Re-read Triggers

- Re-read planning policy before creating or changing roadmap, runbook, or bounded plan artifacts.
- Re-read runtime policy before changing wake-state storage, schema, trigger semantics, cleanup, or retention.
- Re-read agent runtime policy before changing resume payloads, session identifiers, status vocabulary, or agent handoff behavior.
- Re-read validation policy before reporting a feature complete.
