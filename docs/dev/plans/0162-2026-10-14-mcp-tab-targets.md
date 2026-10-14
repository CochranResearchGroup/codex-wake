# Plan0162 — MCP tab targeting

State: CLOSED
Workflow: DONE
Owner: primary / ecochran76
Target: origin/main
Work-Item: https://github.com/CochranResearchGroup/codex-wake/issues/262
Branch: fix/p162-startup-readiness
Pull-Request: https://github.com/CochranResearchGroup/codex-wake/pull/265
Dependency: Plan0156 / PR253 integrated and closed (PR264); original pinned source5b14c05 retained

## Current State

DONE. Feature PR263 integrated88f008d; corrective PR265 integrated1ee7229.
Released v0.15.1 from exact main1ee722979234ade7f5e675f1c995e6ac8e6b4ab8.
Active prefix:/home/ecochran76/.local/share/codex-wake/releases/0.15.1-1ee7229.
Five command links match;99 Python files byte-match main; both installed skill
roots match all4 canonical files. Release wheel/sdist downloaded with exact parity.
Hosted3.11/3.12 release gates passed;1,231 unit tests in the patch CI. Local
integration1,230 and focused startup36 passed; public installed MCP19-tool smoke
covers request/read/claim/completion/reply and capability denials without turns.

Actual installed owned tab-only/fresh/exact-resume proof PASS with0 model turns.
Its raw process observer included the invoking verification shell; a separate
fresh native-process environment census after shell exit found0 owned processes
and0 denied reads. All ten active Wake services retain baseline PIDs/states;
no shared services or unrelated TUIs restarted. New MCP processes expose19 tools;
existing TUI clients require ordinary resource/session refresh for new schemas.
Startup policies still require explicit host-approved profile/caller grants;
installation does not auto-enroll messaging actors or approve workspaces.

0.15.0 post-install proof exposed a pending-binding race. Restored0.14.0 links
and both skills before repair, observed red/green, then qualified0.15.1 in candidate
and exact-main installed prefixes. Failed0.15.0 tag/assets retained as superseded
prerelease;0.14.0 prefix and deployment backups remain for rollback. Source/backup
refs retained. Production-peer notifications/model execution are unclaimed and
unchanged; qualification targets routing, persistence and owned lifecycle startup.

Evidence: docs/dev/evidence/plan0162/final-installed-acceptance.json and
final-acceptance.md. Final documentation custody/issue closure travels through a
separate closeout PR; remove only its clean temporary checkout after integration.
Graphiti disposition unavailable: no reviewed repo target group. No memory-folder
writes. Independent reviewer /root/tab_target_review findings were remediated.

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
