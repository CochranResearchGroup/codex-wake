# Plan0162 — MCP tab targeting

State: OPEN
Workflow: IN_PROGRESS
Owner: primary / ecochran76
Target: origin/main
Work-Item: https://github.com/CochranResearchGroup/codex-wake/issues/262
Branch: feat/mcp-tab-targets
Dependency: Plan0156 / PR253, pinned source 5b14c05

## Current State

Issue262 accepted for execution by operator `ok go`. Isolated worktree at
/home/ecochran76/workspace.local/codex-wake-tab-targets preserves dirty lifecycle
acceptance work in the root checkout. Main readback439f749 lacks the lifecycle
controller. This is a stacked dependency exception to normal main-based work:
only Plan0162 changes may be ported after PR253 integration, never merge the
parent's unaccepted work through this feature. Integration/install gates remain.
Graphiti discovery skipped: supplied feature and current source are sufficient;
no approved repository group is configured. Local memory quick pass had no
relevant project decisions. One primary owns coupled resolution/lifecycle work.

## Scope and interface

Keep exact selectors compatible. Extend session resolution with deterministic
normalization and bounded typo correction. Introduce `sessions target` /
`wake_sessions_target` to inspect or prepare a human target; add equivalent
options to message send so the caller can supply the human descriptor once.
The module owns inventory, matching, exact identity pinning, CWD saved-history
lookup, guarded launch and revalidation. No caller enumeration or shell parsing.

Match precedence: exact literal name; casefold/whitespace normalization (optional
`tab ` prefix); exact numeric/index:name/pane forms; unique fuzzy name at edit
distance <=3 for length>=6 (<=1 for length4–5), normalized distance <=0.4, length>=4. Reject a second candidate
within one edit of the winner. Explicit index/name disagreement is a conflict.
Reserved thread/pane/window selectors stay exact. Split panes and multiple tmux
sessions require qualification; partial inventory never proves absence.

Machine outcomes: resolved, tab_not_found, no_live_codex, ambiguous_target,
descriptor_conflict, inventory_unavailable, target_busy, cwd_mismatch,
resume_not_found, resume_ambiguous, policy_denied, target_changed,
effect_uncertain, tab_created, starting. Return compact source/target evidence,
match method/confidence, requested policy, effects and next actions.

Missing/inactive policies: error(default), tab_only, fresh, resume. Existing live
idle agent resolves regardless of requested fallback. Busy/unknown never replaced.
Existing dormant tabs retain their shell: create the Codex pane using split-window
in the existing single-pane window (no keys, shell termination or draft loss).
The preserved shell is returned in effects; resolution after launch pins the exact
new Codex pane internally. Existing split windows remain ambiguous to loose names.
Tab_only on an existing dormant tab reuses it without a second tab. Missing targets
need explicit CWD or the selected approved profile CWD; expected_cwd mismatch holds.
Resume searches exact canonical CWD (symlinks equivalent; other worktrees distinct),
requires one saved thread or exact resume_thread_id, never latest-by-guess/fresh
fallback. Read-only discovery uses thread/list with bounded complete pagination
and allows no transcript fields into results. Native thread/read revalidates it.

Launch uses approved profiles, caller grant, existing lifecycle journal locking,
atomic save and before_effect expiry. No initial task is injected by preparation;
message admission stays in the capability-checked mailbox. Retry binds selector,
policy, CWD, caller, saved identity and intent; an interrupted creation holds exact
uncertainty instead of making another tab/thread. Existing mailbox idempotency
continues to govern delivery and recipient enrollment is never automatic.

## Execution and acceptance

1. Resolver vertical slice: observed red/green through public CLI/MCP seam for
   the supplied examples, precedence/conflict/ambiguity and partial sources.
2. CWD saved lookup and condition matrix, with read-only native fixture transport.
3. Journaled lifecycle preparation and send integration; restart/race tests.
4. Packaged documentation and stdio MCP checks, focused then presubmit checks.
5. Review diff against issue; installed isolated acceptance and owned cleanup only
   where runtime authorization exists. Production peers/services untouched.

Tests use existing unittest harness. Focused feedback target60s; presubmit local
suite budget240s one process; no retries to erase failures. Record commands and
first failures. Public seams: session CLI/MCP prove target contract; mailbox send
proves authorized admission; real owned TUI proof alone establishes installed
launch behavior. Two correction attempts per failing runtime experiment, then
record/reframe the concrete blocker without automatic expansion.

## Non-goals

No lifecycle parent acceptance, shared daemon restarts, production messages,
auto-enrollment, arbitrary commands/credential paths, implicit latest/fresh
fallback, work replacement, goal/budget reset, or release from unmerged source.

## Definition of done

Issue262 behavior and fixture/installed acceptance pass, combined guidance matches
packaged surface, exact changes reviewed and published, dependency integrated,
required checks pass and canonical main integration recorded. Source completion,
installation and live proof remain distinct; keep plan/issue open for missing gates.
