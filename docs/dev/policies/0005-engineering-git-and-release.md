# Engineering, Git, And Release

## Policy

- Start branch-sensitive work by checking the repo state when a git repository exists.
- Treat pre-existing dirty state as a real constraint and preserve unrelated user work.
- Keep one bounded branch, worktree, or execution slice per major lane.
- Prefer commits that represent one coherent change.
- Do not mix unrelated fixes, refactors, and feature work when they can be separated cleanly.
- Write commit messages that make sense without chat context.
- Use versioning and release notes once the CLI or library has external users, installed commands, or persisted state compatibility.
- Document compatibility impacts for wake-record schema changes.

## Integration Bias

- Early design work may proceed directly in the initial repo until a branch model exists.
- Once implementation begins, prefer short-lived feature branches or worktrees for parallel design, scheduler, CLI, and validation lanes.
- Do not call a feature merge-ready while runtime behavior or persisted-state migration remains unverified.
