# Agent harness ticket drafts

HF-01 is DONE (design only); HF-02/HF-07/HF-13 are READY_FOR_AGENT; other tickets remain TRIAGE. No implementation or live-effect authority is granted.
[HF-01 decisions](hf-01-decisions-and-handoffs.md) resolve the shared-contract interview; every later ticket still needs
its own Matt grill-with-docs process before coding. Stable local locators are
CW-HARNESS-173/HF-NN. The approved first frontier is published as #315, #316 and #317.

[Parent plan and ownership/sequence decisions](../0173-2026-10-23-agent-harness-backlog.md).
`index.json` is a generated dependency/coverage projection; Markdown bodies own
scope and acceptance. Priority indicates proposed product value, not readiness.

| Ticket | Outcome | Priority | Hard implementation prerequisites |
| --- | --- | --- | --- |
| [HF-01](0001-2026-10-23-hf-01-shared-contracts.md) | Grill and reconcile the shared harness contracts | P0 | shared-contract grill only |
| [HF-02](0002-2026-10-23-hf-02-managed-inventory.md) | Enroll one existing agent into a unified managed inventory | P0 | HF-01 |
| [HF-03](0003-2026-10-23-hf-03-semantic-observation.md) | Observe and wait for meaningful agent states | P0 | HF-02 |
| [HF-04](0004-2026-10-23-hf-04-resource-ownership.md) | Prevent competing agents from mutating the same resource | P0 | HF-02 |
| [HF-05](0005-2026-10-23-hf-05-guarded-interactions.md) | Perform one guarded multi-step interaction and human takeover | P1 | HF-03, HF-04, HF-06 |
| [HF-06](0006-2026-10-23-hf-06-step-permissions.md) | Apply host-approved permissions to an assignment step | P0 | HF-02, HF-07 |
| [HF-07](0007-2026-10-23-hf-07-task-brief-context.md) | Pin a task brief and bounded context package to one assignment | P0 | HF-01 |
| [HF-08](0008-2026-10-23-hf-08-acceptance-gates.md) | Accept one work result using independent declared checks | P0 | HF-04, HF-06, HF-07 |
| [HF-09](0009-2026-10-23-hf-09-turn-sequence.md) | Execute and recover a durable sequence of bounded agent turns | P0 | HF-03, HF-06, HF-07, HF-08 |
| [HF-10](0010-2026-10-23-hf-10-branching.md) | Choose if/else and select/case branches from verified outcomes | P1 | HF-09 |
| [HF-11](0011-2026-10-23-hf-11-finite-foreach.md) | Execute a finite for-each collection with a durable cursor | P1 | HF-10 |
| [HF-12](0012-2026-10-23-hf-12-bounded-repeat.md) | Repeat a checked step with explicit exit and progress limits | P1 | HF-10 |
| [HF-13](0013-2026-10-23-hf-13-wake-durability.md) | Specify wake lifetime, ownership and reboot recovery | P0 | HF-01 |
| [HF-14](0014-2026-10-23-hf-14-background-jobs.md) | Own a durable background job and await its result | P1 | HF-02, HF-04, HF-06, HF-13 |
| [HF-15](0015-2026-10-23-hf-15-parallel-join.md) | Run a bounded worker team and join accepted results | P1 | HF-11, HF-14 |
| [HF-16](0016-2026-10-23-hf-16-tab-ordering.md) | Preview and apply active/repo tab ordering with pins | P1 | HF-03, HF-04, HF-06 |
| [HF-17](0017-2026-10-23-hf-17-holding-session.md) | Park and restore dormant live tabs in a holding session | P1 | HF-16 |
| [HF-18](0018-2026-10-23-hf-18-agent-resume.md) | Resume one saved agent binding after crash, reboot or profile change | P0 | HF-03, HF-06 |
| [HF-19](0019-2026-10-23-hf-19-workspace-resume.md) | Restore a saved workspace and its conversation bindings | P1 | HF-17, HF-18 |
| [HF-20](0020-2026-10-23-hf-20-daily-bot-task.md) | Run one reboot-safe daily codex-bots task occurrence | P0 | HF-13, HF-18, HF-21 |
| [HF-21](0021-2026-10-23-hf-21-attention-inbox.md) | Route one blocked decision through a durable human-attention queue | P0 | HF-03, HF-06 |
| [HF-22](0022-2026-10-23-hf-22-drift-guard.md) | Review and correct or hold one overlong owned turn | P0 | HF-05, HF-08, HF-21 |
| [HF-23](0023-2026-10-23-hf-23-portable-accounting.md) | Report cumulative usage and remaining allowance across agents and jobs | P2 | HF-09, HF-14 |
| [HF-24](0024-2026-10-23-hf-24-portable-enforcement.md) | Enforce one qualified allowance through continuation and recovery | P2 | HF-18, HF-23 |
| [HF-25](0025-2026-10-23-hf-25-adapter-recording.md) | Record a redacted adapter interaction and replay it as a conformance fixture | P1 | HF-05 |
| [HF-26](0026-2026-10-23-hf-26-grok-lifecycle.md) | Qualify managed Grok lifecycle operations through the common interface | P2 | HF-18, HF-25 |
| [HF-27](0027-2026-10-23-hf-27-dashboard-overview.md) | Show a unified operator overview and attach to a known agent | P1 | HF-03 |
| [HF-28](0028-2026-10-23-hf-28-dashboard-controls.md) | Approve a decision and step a paused workflow from the console | P1 | HF-05, HF-11, HF-21, HF-27 |
| [HF-29](0029-2026-10-23-hf-29-work-economics.md) | Attribute time and usage to accepted work and correction cycles | P2 | HF-23 |
| [HF-30](0030-2026-10-23-hf-30-completion-retirement.md) | Deliver an accepted work package and retire only its owned resources | P2 | HF-09, HF-14 |
| [HF-31](0031-2026-10-23-hf-31-additional-runtime.md) | Qualify one selected additional TUI adapter | P2 | HF-25 |
| [HF-32](0032-2026-10-23-hf-32-automatic-organization.md) | Apply opt-in tab organization with stable protection rules | P2 | HF-17, HF-21 |

[Common session permissions: requirements and HF-06 design proposal](session-permissions-contract.md).

## Feature coverage

| Conversation feature | Owning tickets |
| --- | --- |
| Unified session inventory/adoption | HF-02 |
| Cross-runtime lifecycle | HF-18, HF-19, HF-26, HF-31 |
| Semantic observe/wait | HF-03 |
| Guarded interactions/human takeover | HF-04, HF-05, HF-06 |
| Task scope/context and acceptance | HF-07, HF-08 |
| One turn per instruction/sequence | HF-09 |
| If/else/select | HF-10 |
| Finite for-each/break/continue/return | HF-11 |
| Bounded repeat/progress checks | HF-12 |
| Await/background jobs | HF-13, HF-14 |
| Parallel/join/team/worktree recipes | HF-04, HF-15 |
| Active/repo ordering/pins/preview/undo | HF-16 |
| Dormant holding/restore | HF-17 |
| Persistent TUI conversation resume/account profile | HF-18, HF-19 |
| Explicit wake durability | HF-13 |
| Codex-bots daily tasks | HF-20 |
| Human attention queue | HF-21 |
| Drift Guard/interrogation/steer/human hold | HF-22 |
| Portable aggregate accounting/enforcement | HF-23, HF-24 |
| Diagnostic recording/conformance/version drift | HF-25 |
| Dashboard overview/attach | HF-27 |
| Dashboard controls/step/breakpoints/variables | HF-28 |
| Work economics | HF-29 |
| Completion/artifact delivery/cleanup | HF-30 |
| Automatic tab policy | HF-32 |

## Technical frontiers

These are dependency sets, not instructions to start every item concurrently.
Keep at most three implementation lanes, and serialize shared hub edits.

- Frontier 0: HF-01.
- Frontier 1: HF-02, HF-07, HF-13.
- Frontier 2: HF-03, HF-04, HF-06.
- Frontier 3: HF-05, HF-08, HF-14, HF-16, HF-18, HF-21, HF-27.
- Frontier 4: HF-09, HF-17, HF-20, HF-22, HF-25.
- Frontier 5: HF-10, HF-19, HF-23, HF-26, HF-30, HF-31, HF-32.
- Frontier 6: HF-11, HF-12, HF-24, HF-29.
- Frontier 7: HF-15, HF-28.

## First-frontier specifications

[Review HF-02/HF-07/HF-13 specs, testing seams and slice boundaries](first-frontier-spec-review.md).
The three specs and testing seams are approved and published; implementation has not started.


## HF-06 confirmed product and proposed implementation

[Common permissions spec](hf-06-spec.md) records confirmed policy decisions and
#318's scoped-refresh capability boundary. [Six-slice proposal](hf-06-implementation-breakdown.md)
is pending operator approval of seams/granularity/dependencies. No new issue was
published and HF-06 remains TRIAGE for implementation.
