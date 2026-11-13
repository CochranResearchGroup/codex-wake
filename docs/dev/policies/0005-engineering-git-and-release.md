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

## Worktree Lifecycle

- Start branch-sensitive work by checking `git status`.
- Inventory all registered worktrees with `git worktree list --porcelain` before creating, closing, pruning, or reassigning one; the current checkout alone is not the repository topology.
- Ordinarily keep the primary/root checkout on `main` (or the repository's
  documented default branch). Use it for inspection, integration, and work the
  repository permits directly on that branch. Do not switch it to a topic branch
  merely to avoid creating a justified linked worktree. A temporary exception
  needs a concrete reason and a return-to-default-branch step; never reset or
  discard existing work to restore the anchor.
- Worktrees are a normal tool for off-main development while preserving that
  root anchor, concurrent editing, isolated experiments or review/testing, and
  incompatible build/runtime environments. These purposes do not require an
  extra permission round when already within the authorized task. Record the
  purpose and expected lifetime. Create a new worktree only when a separate
  checkout serves that purpose and no suitable existing lane checkout is
  available; do not create one mechanically.
- Before creation, inspect the registered inventory and determine whether an
  existing clean checkout already owns the intended branch and lane. Reuse the
  correct lane checkout when safe, including its own in-progress changes.
  Continue the same lane
  across tasks, sessions and plan steps in that checkout. Read-only inspection
  normally needs no new checkout; a fresh agent, session or step alone is not
  a creation reason; do not repurpose another active lane's checkout, overwrite
  dirty work, or create a duplicate to avoid determining custody.
- Use the repository's documented worktree root and naming convention. If none
  exists, use `<primary-checkout-parent>/.worktrees/<repo>/<lane-slug>`; derive
  `<repo>` from the primary checkout, not the current linked worktree. Use a stable
  lowercase kebab-case work-item or lane slug, such as `issue-123-parser-fix`.
  Keep the branch name in the repo's branch convention and record its mapping.
  Do not scatter checkouts among sibling folders, temporary directories, or
  agent/session/timestamp names. Resolve collisions by inspecting ownership,
  not by adding random suffixes. Additional clones are not a workaround.
  Tool-managed worktrees may use a documented tool-owned root and naming scheme;
  record that exception and retain the same inventory and cleanup obligations.
  Do not relocate existing or tool-managed worktrees opportunistically.
- Record owner, purpose, branch, creation reason, cleanup trigger, and next review
  point in the existing lane/handoff record; keep machine-specific absolute paths
  in workstation-local metadata, outside shared catalogs. Allocate at most one
  linked worktree per active lane by default. Additional checkouts for the same
  lane require a separately recorded concurrent need and cleanup trigger.
- Before adding a checkout, reconcile unneeded worktrees owned by the current
  task. Do not delete, relocate, or take over another owner's checkout to meet
  this rule; report unresolved ownership or cleanup blockers explicitly.
- Treat pre-existing dirty state as a real constraint.
- Keep branch scope coherent with the repo's integration model; do not allocate a
  new worktree for every execution slice or roadmap step.
- Prefer `git worktree` over a second full clone when a separate checkout is useful.
- Keep checkout count proportional to active lanes and explicitly retained needs.
  Before creation, account for existing linked worktrees by owner and purpose;
  report unknown ownership without treating it as deletion authority. Include
  counts before/after creation or cleanup. Do not keep spare idle checkouts for
  hypothetical future tasks. A paused lane normally retains refs and a handoff,
  and releases its checkout unless a concrete environment need justifies retention.
- Do not call work merge-ready while the intended changes are still uncommitted.
- Treat the worktree as a checkout, the branch or detached commit as local custody, and a verified remote or archive ref as shared custody. Removing a worktree does not preserve uncommitted changes and does not prove the commits remain discoverable.
- Before removing a worktree, require a clean status, a named branch or explicitly preserved detached commit, an exact checkpoint SHA, and verified durable custody on the intended remote ref or on matching local and remote archive refs.
- Close a worktree promptly when its branch is integrated, its work is durably
  handed off without needing the checkout, or its preserved branch is paused or
  archived. Do not accumulate idle worktrees as informal reminders or confuse a
  retained branch with a need to retain its checkout.
- Cleanup is part of task completion. Remove the task's unneeded checkout in the
  same closeout after custody and integration requirements are satisfied. Run
  removal from a retained checkout, not from inside the worktree being removed.
  Do not defer routine safe removal to the operator. A retained checkout needs
  an owner, concrete remaining need or blocker, and a next review point; "might
  need it later" and an open branch/PR alone are insufficient. Report retained
  paths and reasons, and keep cleanup-pending distinct from cleanup-complete.
- Account for ignored/untracked artifacts before removal, including local env
  files, databases, dependencies and build outputs. Preserve irreplaceable data;
  remove only task-owned disposable outputs through normal project cleanup.
  Avoid duplicating large caches, dependencies or indexes without a demonstrated
  need; use supported shared caches where available without sharing mutable state
  that requires isolation. Worktree removal does not clean external artifacts:
  reconcile task-owned external outputs separately within the authorized scope.
- Normal closure uses `git worktree remove` without `--force`. Forced removal is exceptional recovery work: first inventory the exact path, preserve any recoverable diff and commit, establish a durable ref, record the reason, and verify the retained SHA.
- After removal, verify the exact path is absent from the registered worktree
  inventory. Prune only stale administrative entries whose checkout absence and
  branch custody have been established; pruning is not a substitute for closing
  a live worktree deliberately.
- Do not delete an unmerged branch merely because its worktree is gone. Prove integration, archival, or explicit discard approval separately.
- If overlapping dirty work exists across branches or worktrees, open a reconciliation step rather than calling it a normal merge.
- Keep branch scope narrow and avoid mixing unrelated lanes unless the active slice requires it.
