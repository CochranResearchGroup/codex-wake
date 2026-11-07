# Stable user controller and account-command defaults

State: OPEN
Work item: https://github.com/CochranResearchGroup/codex-wake/issues/498
Owner: ecochran76 / primary
Priority: high. Tracker state: IN_PROGRESS. WIP: primary implementation plus one bounded native qualification worker.

## Current State

Default-routing implementation4fbd008 passes the four new public regressions.
Native stopped-home relocation qualified on UID1017 without provider calls.
Affected Python3.11 run118PASS; Python3.12 run117PASS plus one retained
PowerShell/WSL bootstrap timeout. One instrumented retry exposed OS
UtilAcceptVsock accept4 error110 in unchanged boundary code. Actual PowerShell
workflow passed on3.11; no clean-all-gates claim. Static/planning checks pass.
Working controller location is not moved yet.

## Scope and outcome

User rejects the testing-era installation name and manual WAKE_ROOT exports. Existing shortcut preference ownership must serve all account/store/configuration/history/build/daemon/migration commands, compatibility launchers, completion and corresponding local MCP calls. Explicit roots/configuration retain priority. Use XDG_STATE_HOME/codex-wake/controller (normally ~/.local/state/codex-wake/controller) for first-use user account state; continue project-local scheduler/control semantics. Existing saved default-root remains authoritative; no competing preference registry. Retain legacy project account discovery only when no user default exists. Malformed preference fails explicitly and can be repaired with configuration default-root.

Relocate the existing stopped installation to the permanent controller directory with recovery custody and a compatibility alias for historical absolute history references. Preserve authentication/history/native state inodes, store IDs/home generations, packages, grants/usage, raw receipts, unrelated stock and running sessions. Update selected live configuration paths/launcher defaults, not historical receipts or private conversation payloads. If any affected native client/daemon is active, do not move beneath it; first establish an explicit supported safe boundary. No live provider calls or new sign-ins are needed.

## Acceptance and seams

Public CLI root selection: no-root accounts/status/stores/configuration/history use saved/canonical controller from unrelated project cwd; explicit override wins; malformed default remains repairable. Scheduler commands retain .codex/wake. Completion and launcher/MCP default registry agree. Focused red then minimal green at each seam, existing harness only.

Native qualification: disposable test-user stopped home rename plus legacy alias, supported native startup/resume and saved history/auth-independent state preserved. Same complete qualified0.167 package; no Rust rebuild, no external model calls. Working relocation only after this proof and fresh process readback. Installed final commands without --wake-root, canonical homes, profile version/resume readiness, completion and actual PowerShell checks; preserve rollback and initial failures.

## Non-goals / boundaries

No new account manager, credential copying, global scheduler-root rewrite, implicit service restart, history rewriting, paid hostedCI, broad feature redesign or parked OpenClaw work. Any merge/deploy is the directly requested continuation of the installed UX fix; preserve exact main/source/prefix/readback identity through PRs and local validation. No repeat of Plan0205 broad review.

## Execution

Base main ba8092c73eae7066e5674661ad2766e45468a4d2; branch fix/default-controller-location; isolated worktree codex-wake-controller-defaults, primary dirtyconfig preserved. Primary owns default routing/installed cutover; bounded worker qualifies native relocation only. Standalone canonical naming choices and fallback order are frozen above. Implementation, native acceptance, physical move and deployment remain distinct receipts.

Memory disposition pending closeout; no memory-write request.

### Source and native qualification checkpoint

Four public default-routing tests cover first-use canonical state, arbitrary cwd, shared launcher/MCP defaults, explicit/saved/environment precedence, project wakes and malformed-preference repair. Red failures retained for wrong project location, missing launcher configuration, MCP host-root-required and ignored explicit profile root. First broader join caught a symlink-root batch safety regression; restored non-following shortcut semantics and retained the original failure. Native UID1017 stopped-home rename+legacyalias qualification PASS with exact0.167 package, saved history/goal/counters/inodes preserved, freshnewhome peer verified,0provider calls and ownedprocessesempty. No working move yet.

A live same-user local HTTP controller remains in the legacyroot (PIDidentity read-only verified), serving shared native discovery from older Pythonprefix. Its15 journal operations are terminal/completed; no profile native processes are active. Physical cutover therefore includes only a supported stop/start of this idle selected HTTP listener, with fresh identity/idle checks, same port/nativeendpoint and regenerated private connection bootstrap. The shared native daemon, unrelated services, budgets and sessions remain running. This is separate from goal-watcher maintenance; no goal allocation or stop latch is changed.

Inherited CODEX_PROFILES_CONFIG still points at the retired Profiles project in the working environment. A saved Wake default is an explicit modern selection and now takes priority over this legacy fallback; --config/new CODEX_WAKE_ACCOUNTS_CONFIG and CODEX_WAKE_ROOT remain explicit overrides. Public regression reproduced selecting the wrong legacy account then verified the intended store, retaining direct --config access. This closes the same default-consistency outcome rather than changing legacy project files or requiring manual environment cleanup.
