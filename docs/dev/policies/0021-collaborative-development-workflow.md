# Policy | Collaborative Development Workflow

## Policy

- Use GitHub Issues as this repository's canonical coordination ledger. Use
  plans, the active-lane catalog, Git, pull requests, checks, and receipts for
  their separate execution and evidence roles.
- Treat `origin/main` as the canonical integration ref. Fetch it before opening
  a lane, start normal work from that readback, and modify it only through a
  merged pull request.
- Give every substantive change one accountable human owner. An agent may work
  within delegated scope, but it does not acquire scope, merge, release,
  deployment, or provider authority merely by doing the work.
- Search open issues and pull requests before implementation. Reuse an existing
  work item when it matches the intent; otherwise create one through the
  governed GitHub issue workflow and claim it before editing implementation.
- Keep each work item concise: objective, owner, state, affected surface, live
  effect, branch, plan locator, dependencies, overlaps, and pull request.
- Use one short-lived branch per independently mergeable intent. Use `feat/`,
  `fix/`, `docs/`, or `chore/` prefixes. Put simultaneous write lanes in
  separate worktrees and do not let two sessions edit one checkout.
- Keep at most three substantive implementation lanes in progress. Finish,
  pause, split, or cancel work before exceeding that limit.
- Register concurrent implementation branches in
  `docs/dev/active-lanes.yaml`. Treat the catalog as a projection; current
  GitHub and Git refs remain authoritative for tracker state and custody.
- Push coherent checkpoints when collaboration, recovery, CI, or review needs
  them. Verify that the remote branch resolves to the reported commit.
- Link every pull request to its work item. State the objective, affected
  surface, risk or live effect, plan locator, validation, and unresolved
  overlap.
- Prefer squash merge for independently mergeable slices. Preserve a merge
  commit only when its component history has durable review or reconciliation
  value.
- The accountable owner may self-check and merge after required CI passes when
  no separate review or approval rule applies. Self-check the published diff,
  base, scope, validation, and live effect before merging.
- Close an issue only when its stated outcome is complete. A merged pull
  request, successful check, release, deployment, or runtime observation proves
  only its own boundary.
- Release or deploy only an exact commit on `origin/main` that entered through
  a merged pull request. Preserve the target, actor, validation, authorization,
  and post-effect readback.

## Multi-Agent And Model Optimization

- Use a `balanced` execution bias. Keep architecture, shared schemas, authority
  decisions, integration, and final acceptance with the primary owner.
- Use bounded subagents for independent discovery, disjoint implementation,
  mechanical checks, and independent verification. Use no more than three
  concurrent subagents per lane and avoid nested delegation by default.
- Record consequential subagent handles, scope, status, evidence, and the
  primary owner's reconciliation decision in the plan, pull request, or
  closeout receipt.
- Route deterministic inspection, polling, hashing, and schema checks to tools.
  Use the economical calibrated model tier for mechanical work, the standard
  tier for implementation, and a specialist tier only for a named architecture,
  security, or causality decision that evidence shows the lower tier cannot
  resolve.
- Measure model and delegation choices by accepted slice outcomes, correction
  rate, elapsed time, and total allocation or a labeled proxy. Do not optimize
  for worker count, token count, or response novelty in isolation.

## Adoption Notes

The GitHub target registry lives at `docs/dev/forge-issue-targets.json`.
Repository CI runs the `release-gates` matrix for Python 3.11 and 3.12. This
policy does not grant live dispatch, release, deployment, or new provider
authority.
