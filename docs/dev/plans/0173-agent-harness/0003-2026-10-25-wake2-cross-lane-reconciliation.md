# Wake2 refresh and goal-limit reconciliation

State: CLOSED
Owner: ecochran76 / primary coordinator
Scope: read-only cross-lane qualification and integration handoff
Branch: feat/harness-next-frontier
Main integration, native activation and resumed implementation: not performed

## Verified current state

The operator's Wake2 tab is tmux default/window20/pane%22. Its implementation
stopped at the manual token ceiling; its current turn is read-only explanation,
not resumed implementation. No allowance is renewed by this status/reconciliation.
Facts below were checked against fresh GitHub refs, source reports and live paths.

| Area | Progress | Outstanding gate |
|---|---|---|
| Observation-fault recovery319 | CLOSED; deployed Wake0.21.2 runtime311da84; explicit authorized recovery retains charges, deadline and stop history | Source main integration remains separate |
| Scoped MCP refresh318/current-session310 | Wake adapter and native scoped dependency qualified on two isolated threads, selected resource upgrade and unchanged peer; opt-in experiment passed | Actual requesting/shared daemon still Codex0.164.0; patched native not activated; two broader native failures unclassified;318/310 OPEN |
| Goal-limit UX343–346 | Source45c0820 / PR348 implements exact-revision first-poll readiness, configured watcher startup, durable no-turn notices, approved extend/reset; real native/MCP/stock-TUI journey passed | Watcher-restart variant after f81811d unverified, final native static/schema/format custody incomplete, acceptance audit/closure, review0/1 and remediation0/1 pending; all four issues OPEN |

CI40165653279 is SUCCESS on exact45c0820320f5ca0867c56b137d2ca92fcfb7b47d
for both Python3.11/3.12 release gates. This is newer than PR348's earlier pending
CI description. It does not qualify the remaining native/restart/review boundaries.
The final resource-stop ledger is newer than the PR body's earlier accounting
writer blocker: authentic response accounting and native caller metadata were
ported and the isolated full happy journey subsequently passed.

Real journey evidence pins nativeb0ce988429488a3e37966c318f3fe0bfdf3af77a,
stockTUI0.164.0 and Wakee9a46b3 (before restart correction). It proves engagement,
checkpoint/hard-stop presentation, model-input receipt, reconnect once, genuine
MCP enrollment, approved extension retaining spend and reset retaining lifetime
usage, with unchanged peer. It is not final45c0820 installed acceptance or default
production support. Native notice patch explicitly builds on scoped-refresh
base6115475dd95f6ffd525992bd5f98051d543a4c68; these native dependencies are related,
not two arbitrary alternative binaries.

Live readback: codex-wake link resolves releases/0.21.2-311da84/bin/codex-wake;
codex CLI0.164.0; actual daemonPID2692768 executable is the standalone0.164.0
release. codex-wake-goal-limits.service is masked; shared-refresh service is active.
Neither mask nor daemon was changed. Staged0.22.0.dev0 UX is not installed by default.

## Source reconciliation and safe integration route

Frozen refs:341a606e12,3324356ec3,34845c0820. Main remains37a5cbb.
348 is already based on341's qualified16c2501 source. Our later changes are docs
and tracker custody; a read-only merge-tree of341+348 is clean.

332 is stacked on the now-superseded HF06 PR327. Naive ancestry merging reports
many false add/add conflicts because the HF06/history was carried over a squashed
base. Reconcile its qualified delta5d34fc7..4356ec3, not its duplicated prerequisite
history. Read-only `git merge-tree --write-tree --merge-base=5d34fc7 a606e12 4356ec3`
is clean. No worktree/index/ref was changed by these merge probes.

Combining332+348 with that explicit common-permissions base leaves real conflicts:
RUNBOOK.md, pyproject.toml, src/codex_wake/__init__.py, goal_supervision.py and
permission_enforcement.py. Preserve explicit observation-fault recovery and current
refresh policy from332 alongside startup/readiness/notice/renewal semantics from348.
CLI and MCP also overlap and need combined caller qualification even where text
merges automatically. Resolve version metadata as a combined candidate, not by
selecting one branch's number without release qualification.

Do not deploy341 alone over installed0.21.2:341 source is0.21.0 and lacks
src/codex_wake/goal_recovery.py. Its source acceptance is valid as a foundation,
not as a replacement of the newer installed operational fixes. Consolidated route:
341 foundation -> qualified332 delta ->348 UX, with semantic conflict resolution,
combined caller tests, the outstanding native/restart acceptance, then the requested
single review/remediation before release/activation. The development native successor
already builds on scoped-refresh source but still needs final exact-artifact proof.

## Authority and evidence custody

Source reports: PR332 docs/dev/evidence/hf06/318-scoped-refresh.md and319-recovery.md;
PR348 goal-limit-ux-execution.md, goal-native-ux-journey.md, goal-renewal-installed.md
and patches/codex/345-no-turn-notice.md. First failures and the2,055,524-token stop
remain retained. No sibling branch, active worktree, ticket acceptance, service,
shared native runtime or production resource state was changed by reconciliation.
This receipt is discovery/integration direction, not finished UX implementation.
