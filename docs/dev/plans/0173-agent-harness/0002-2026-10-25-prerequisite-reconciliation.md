# Consolidated prerequisite integration

State: CLOSED
Owner: ecochran76 / primary coordinator
Branch: feat/harness-next-frontier
Target: origin/main
Delivery: https://github.com/CochranResearchGroup/codex-wake/pull/341

## Outcome and current evidence

Reconciliation consolidates the three prerequisite PRs into the already validated
PR341. It does not merge main, deploy, delete branches or claim issue328 complete.
Fetched origin/main is37a5cbb03e1c9e7db5026c99d6dca3cbf443ee5f; PR341 base main,
published source1dcf0ec, mergeable. Original operator checkout stays43e3db2 and clean.

| Prerequisite | Exact remote tip | Carry evidence | Disposition |
|---|---|---|---|
| PR327 common permissions |5d34fc73089e3e45013a6428a789f190a2428a9f| Qualified f29042b..5d34fc7 delta integrated at3af0cb6; f29042b tree equals canonical37a5cbb; CLI/MCP combined with observation/resource dispatch | Superseded by341; branch retained |
| PR329 workspace correction |7746349a62265f0f0543f670c07c53d5f4904e43| Runtime and regression delta75789bd carried ata5ca8ef; task_briefs/task_brief_commands and owned regression files match329; missing canonical plan and user docs now restored | Superseded by341; issue328 staysopen until main integration |
| PR333 observation/resource custody |3dde546a1a9b07e9d27950252ce3599587bffd40| Exact commit is ancestor of341; all its source/history/evidence retained | Superseded by341; branch retained |

All source carries predate the final local comprehensive proof:1651tests/823.097s,
OK(skipped1), source16c2501. Current reconciliation restores documentation only;
runtime source, tests and pyproject remain byte-identical to tested16c2501.
No repeated full suite is justified by documentation restoration. Focused task-brief
and public-caller selections are rerun for the carried workspace boundary.

PR327's installed-deployment readback is separate operational authority; this
consolidation neither replays that installation nor refreshes existing sessions.
Its earlier7a52339 source differs from5d34fc7 only in deployment documentation,
not runtime code. Other sessions' PR332/lifecycle and goal-limit work are untouched.

## Scope and acceptance

Exact refs, ancestry/carry and documentary gaps reconciled; earlier PRs explicitly
link the consolidated delivery and close as superseded without deleting refs.
PR341 explains the consolidated base/diff and retains local proof/CI exception.
Issue328 remains an integration gate. No mainmerge/release/production effects.
CI skipped by user instruction. All tracker mutations receive readback.

Focused task-brief/store/CLI/native-caller selection passes17tests/1.524s on
qualifiedPython3.12. `git diff16c2501 -- src tests pyproject.toml` is empty;
workspace-owned files match329. The upstream repository/actor readback is
CochranResearchGroup/codex-wake, ecochran76, ADMIN, Issues enabled, unarchived.
The three exact remote tips are frozen before closing superseded PRs; branch
refs are retained. PR341 becomes ready for review, without main merge authority
being inferred from this reconciliation step. CI remains explicitly skipped.

Tracker readback:327/329/333 CLOSED as superseded, with each frozen head unchanged.
No underlying issue was closed by those PR closures. PR341 is the sole consolidated
integration delivery; its body links issue328 to close only on main integration.
The source is ready for review, not merged by this bounded reconciliation packet.
The three remote branches remain retained and existing installed services untouched.
