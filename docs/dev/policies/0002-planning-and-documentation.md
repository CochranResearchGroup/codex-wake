# Planning And Documentation

## Policy

- Use bounded plan artifacts under `docs/dev/plans/` for substantive design or implementation slices.
- Plan filenames should use a deterministic prefix such as `0001-YYYY-MM-DD-plan-slug.md`.
- Each active plan should include scope, non-goals, acceptance criteria, definition of done, and current state.
- Keep architecture decisions explicit when they affect wake semantics, durable state, resume behavior, or operator safety.
- If `ROADMAP.md` is added, treat it as the master priority map and lane catalog.
- If `RUNBOOK.md` is added, treat it as the dated turn log of what happened.
- Do not scatter active design authority across loose notes when a canonical plan or roadmap exists.
- Move stale or superseded notes out of active planning surfaces instead of leaving ambiguous near-duplicates.

## Wake-Timer Planning Requirements

- Define trigger classes before implementation, such as wall-clock time, command completion, file existence, process exit, external check, or manual review gate.
- Define the status vocabulary before runtime code depends on it.
- Separate the agent-facing API from the scheduler implementation so storage and trigger mechanisms can change without breaking agent workflows.
- Document any unsafe or unsupported trigger class rather than leaving behavior implicit.
