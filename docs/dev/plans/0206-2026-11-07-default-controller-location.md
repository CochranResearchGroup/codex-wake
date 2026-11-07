# Stable user controller and account-command defaults

State: CLOSED
Work item: https://github.com/CochranResearchGroup/codex-wake/issues/498
Owner: ecochran76 / primary
Priority: high. Tracker state: IN_PROGRESS. WIP: primary implementation plus one bounded native qualification worker.

## Current State

Merged PR499 as aaf619cc890828798d2c694d919b4ed02f4cdb4d and deployed its exact
Python prefix. The live user controller is now ~/.local/state/codex-wake/controller;
account commands/launchers work without root flags. Legacy saved history paths
resolve through the retained compatibility alias. All29 protected native-state
files and15 journal records are unchanged. Installed no-root status/recent/store,
launcher and Windows PowerShell checks passed. Existing interactive shell wrappers
were repaired; open a new terminal once to load the startup change.

Final31 focused tests pass eachPython3.11/3.12; prior broader3.12 WSL-vsock failure
remains retained separately. No new provider calls, native restarts or credential
copying. See ../evidence/plan0206/deployment.json. Issue498 acceptance complete.

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

Five public default-routing tests cover first-use canonical state, arbitrary cwd, shared launcher/MCP defaults, explicit/saved/environment precedence, project wakes and malformed-preference repair. Red failures retained for wrong project location, missing launcher configuration, MCP host-root-required and ignored explicit profile root. First broader join caught a symlink-root batch safety regression; restored non-following shortcut semantics and retained the original failure. Native UID1017 stopped-home rename+legacyalias qualification PASS with exact0.167 package, saved history/goal/counters/inodes preserved, freshnewhome peer verified,0provider calls and ownedprocessesempty. No working move yet.

A live same-user local HTTP controller remains in the legacyroot (PIDidentity read-only verified), serving shared native discovery from older Pythonprefix. Its15 journal operations are terminal/completed; no profile native processes are active. Physical cutover therefore includes only a supported stop/start of this idle selected HTTP listener, with fresh identity/idle checks, same port/nativeendpoint and regenerated private connection bootstrap. The shared native daemon, unrelated services, budgets and sessions remain running. This is separate from goal-watcher maintenance; no goal allocation or stop latch is changed.

Inherited CODEX_PROFILES_CONFIG still points at the retired Profiles project in the working environment. A saved Wake default is an explicit modern selection and now takes priority over this legacy fallback; --config/new CODEX_WAKE_ACCOUNTS_CONFIG and CODEX_WAKE_ROOT remain explicit overrides. Public regression reproduced selecting the wrong legacy account then verified the intended store, retaining direct --config access. This closes the same default-consistency outcome rather than changing legacy project files or requiring manual environment cleanup.

### Final source validation

Final source15740a6348e459995165c198adefb104d2ab683e:31 focusedPASS eachPython3.11/3.12; whole undefined-name Ruff, compile, policy, generatedreference and activeplanning PASS. Legacyprofilevariable and canonical-vs-project discovery regressions red→green retained. Earlier affected source4fbd008:3.11all118PASS,3.12one concreteintermittentWSLUtilAcceptVsock bootstrap error among117passing; unchanged controltransport files and successful3.11actualPowerShell workflow bound its environmental disposition. No cleancomprehensive/allgates claim, no more retries or scope expansion.

### Working cutover and installed acceptance

Exact merged wheel01cbec7818e873a66f529fe04c6946f46be5571e68ecc4fe23b98a656688aee0 in ~/.local/share/codex-wake/releases/0.22.0.dev2-aaf619c matches269Pythonfiles. Selected idle HTTPlistener stopped through publiccontrolserverstop, then root renamed in-place with oldnamealias. Updated3liveconfigurationfiles and13metadata/configsymlinks; raw native auth/history/SQLite untouched,29protectedfiles preserveinode/hash/mtime. All15terminal operation/event/revocation records preserve their digest. Sourcehomes/storeIDs/generations remain intact; historical receipts/transcripts are not rewritten.

First listener replacement inherited requested port0 and selected a new port, causing the explicit same-port verification to fail after the completed move. Preserved first intent/script, inspected known currentstate and rebound only that replacement listener to the prior observed37185; no directory retry or scope reset. Final listener currentPID3793423 is ready in canonicalcwd using newprefix.26remaining native generations unchanged,1earlierprocess exited independently, no native interruption.

Inherited CODEX_PROFILES_CONFIG exposed another installed binding: .zshrc legacyfunctions forced --config to the old project, bypassing the published launchers. Surgically replaced only that managed block, preserved unrelated startup bytes/legacy variables, syntaxcheckedZsh and verified the normalcommand launcher. Users open a fresh terminal or reload startup once; no root exports are required. Reinstalled Bash/Zsh completion.

Actual no-root accountsstatus,storesresolve,historyrecent(complete,noholds),controllerstatus and profileversion pass from unrelatedcwd. Actual Windows PowerShell→WSL no-root status completed in1.385s with canonicalhome; savedcredentialspresent, no provider call. Stockbinary hashunchanged. Rollback configuration/preferences/launchers/startup snapshots and oldprefix retained privately. ExistingMCPprocesses load module changes when individually reloaded. Memory disposition forbidden because no explicit memory-write request.
