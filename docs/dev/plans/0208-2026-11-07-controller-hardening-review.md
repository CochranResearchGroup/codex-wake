# P208: Existing controller specification and ticket hardening review

State: CLOSED
Work item: LOCAL-P208
Workflow: DONE (review); proposed hardening items remain TRIAGE
Owner: primary / ecochran76
Priority: P1
Branch: docs/hardening-readiness-0208
Base: 20e396b5aa469ed814c123218cc356a68b229936
Dependencies: none for review
WIP limit: one review; no implementation lanes opened

## Current State

Review completed against current source, installed release 0.22.0.dev2-aaf619c,
GitHub readbacks and existing acceptance artifacts on 2026-11-07. This document
reconciles ownership and proposes bounded corrections; it does not replace the
existing specifications or claim fresh qualification of every feature. No issue
was created, reopened or closed, and no live tab was changed.

## Scope and authority

Review the existing workspace, session, controller, flow, resource-control and
account specifications. Capture reproducible product gaps and distinguish
hardening from unfinished feature delivery. No new implementation, model turns,
service restart, grant changes, global deployment or destructive cleanup.

GitHub owns current issue state. Specification bodies own product acceptance;
source/disposable/installed/live receipts prove only their stated boundaries.
Historical issue body checkboxes and branch labels are not current completion
proof. Latest source and installed boundaries must be reconciled before executing
a successor packet. The original operator preference remains functional same-user
WSL/PowerShell control without manual per-session enrollment/grant rituals.

## Authority and feature map

| Surface | Existing authority/tickets | Reconciled boundary and hardening target |
| --- | --- | --- |
| Original harness backlog | Plan0173 and HF-01 through HF-32 | Index and original draft headers are stale; do not start implementation from their blanket TRIAGE status. Consult refined specs and current issues. |
| Group/order tabs | HF-16, closed #337; hf-16-spec.md | Activity/repository ordering, pins, preview/apply/undo within one exact session; no cross-session moves or automatic sorting. |
| Host attachment adapters | Plan0190/#393, closed #402/#405 | CLI/API/MCP operations and Byobu/psmux adapters; actual Windows psmux capture through WSL bridge was qualified. This is not full Windows-owned service or CRUD qualification. |
| Create/resume/close Byobu tabs | closed Plan0129; HF-18 closed #338 | Existing exact lifecycle and guarded close; naming, full CRUD and movement are not one completed controller contract. |
| Park/restore live tabs | HF-17 local draft | Still TRIAGE; preserve process/conversation and wake/mailbox routing. Clarify manual whole-tab moves separately from dormancy automation. |
| Workspace recovery | HF-19, open #368 | Single-agent resume is insufficient. Existing issue requires durable identity capture and correct workspace reconnection, avoiding per-agent enrollment rituals. It already asks whether HF-17 is a real dependency. |
| Automatic organization | HF-32 local draft | Planned, not delivered by manual ordering. Depends on protected manual movement and observable state. |
| Local WSL/PowerShell control | Plan0200/#466; closed #467–#475; merged PR477 | Genuine installed Codex qualification covers discovery, prompt acknowledgement, response modes, slash actions, own limits, health and recovery. Retain failed PowerShell bootstrap evidence; #478/Plan0202 adds diagnostics, not a proven root-cause fix. |
| Grok | #412 and closed #476/Plan0201 | Supported sole-owned headless ACP session; arbitrary existing TUI ownership, exact TUI health/cancellation/metering remain unsupported. |
| Cross-host/auth/answers | #393, closed #394/#399–#401/#405 | Source and disposable transport qualification exist. Recheck installed capability/error parity; no implication of Windows-native execution ownership. |
| Structured flows | #393, closed #406–#411 | Branch/wait, new/sequential/fork foreach, joins, semantic conditions and nested limits have scoped qualification. Do not relabel old HF-09–15 drafts as wholly missing. Fresh operational requalification remains separate. |
| Governor/notices/recovery | open #343–#346/#350/#413 and closed implementing children, #403/#404/#468 | Reconcile child evidence against parent acceptance before closure. Local voluntary self-limits do not alone prove externally governed stop/extend/reset UX or upgrade recovery. |
| Accounts/builds/config/history | #371/#380; Plans0195–0199 and0205–0206; closed #488–#495/#498 | Real account setup and installed profile evidence now exist. Reconcile older parent production gates against later receipts instead of assuming either fully open or universally complete. |
| Generated help/completion/parity | Plan0197/LOCAL-0197, command-coverage.json | Shared definition currently lists43 migrated operations and289 deferred command paths; all seven tabs verbs are deferred. Deferred means not migrated to this contract, not absent or universally lacking API/MCP support. |
| Other pending capabilities | HF-20/22/23/24/25/28/29/30/31; open #370/#458/#500 | Daily orchestration, drift correction, portable controls, recorder, console controls, economics, retirement and additional runtime need criterion-by-criterion reconciliation. This audit does not declare them implemented or failed. #370 handoff, #458 pending-wake edits and #500 interruption continuity retain their own ownership. |

All issue references resolve to https://github.com/CochranResearchGroup/codex-wake/issues/NUMBER.
PR341 remains open; its status alone does not establish whether individual source
components were integrated through later work. PR477 is merged at25d7005.

## Confirmed findings

### H1 — P1: installed tab defaults and missing-configuration handling

Commands already executed against the installed prefix:

- `codex-wake tabs list --json`: TypeError constructing Path(None).
- `codex-wake --wake-root /home/ecochran76/.local/state/codex-wake/controller tabs list --json`:
  uncaught FileNotFoundError for controller-tabs.json.

In tab_organization_commands.run, the new adapter path passes args to
 tab_commands.command and drops the separately resolved root. That adapter uses
args.wake_root directly. This explains the no-root failure. The canonical
controller has no tab workspace configuration. Missing configuration must yield
an actionable typed result, not a traceback or a false healthy empty inventory.

Existing owners: #402 and root-default #498; create one corrective successor
rather than reopen unrelated accepted work wholesale.

### H2 — P1: installed factory omits the grouping observer

controller_tabs_from_root constructs transport/broker/privacy but does not wire
WorkspaceObserver or an equivalent qualified observer. ControllerTabs then passes
config.get('observer') to TabOrganization. Without observations, windows are
pinned as unqualified; with configured transports the apparent grouping operation
can become a no-op. The older direct CLI path does construct WorkspaceObserver.
Source finding; a configured installed regression must reproduce the no-op before
fixing it. No claim of a live failed reorder is made.

Existing owner: #402/HF-16. Acceptance: installed CLI/API/MCP fixture identifies
movable qualified windows, actually reorders, preserves focus/pins/processes and
undoes. A no-op must distinguish already-ordered from unavailable observations.

### H3 — P1: specification and completion-state drift

Plan0173 README says most tickets remain TRIAGE even though #330/#331/#334–#340
are closed and later refined specs/ledgers exist. Closed issue bodies may still
say IN_PROGRESS with unchecked criteria. Plan0190 carries historical remaining
production gates; later account work must be reconciled against them. Retain
historical evidence, update navigation/current-state projections, and link exact
remaining criteria. Do not rewrite source acceptance as deployment acceptance.

### H4 — P1: full tab CRUD and movement need explicit acceptance

Current tabs operation list is list/show/preview/apply/undo/capture/input. Existing
sessions lifecycle supplies part of create/read/delete. No shared full contract
for rename, explicit placement, manual cross-session move, named-group management
or cross-backend movement was established by #337/#402.

Treat missing verbs as feature completion, not bug fixes. Define grouping first:
repository ordering is implemented; arbitrary named groups and separate workspace
placement need explicit specification. Byobu/tmux to psmux cannot silently mean
moving a live process across operating systems; require explicit unsupported
results or a separately qualified conversation reattachment/successor workflow.

## Proposed successor work items (local TRIAGE, not newly posted issues)

| ID / priority | Reuse / dependency | Observable outcome and acceptance |
| --- | --- | --- |
| HARD-01 / P1 | H1; #402/#498 | Ordinary no-root tabs list works from repo/unrelated cwd with saved/explicit roots; missing config returns typed actionable result on CLI/API/MCP, no tracebacks. |
| HARD-02 / P1 | H2; HARD-01 | Enrolled workspace receives fresh session observations; actual installed preview/apply/undo reorders eligible Byobu windows. Unknown/mixed/focused/pinned windows stay protected and reasons are visible. |
| HARD-03 / P1 | #402/#405; HARD-01 | Discover available Byobu/psmux workspaces from WSL and actual PowerShell; explicit bounded workspace adoption where needed, no per-tab grants. Verify psmux bridge identity, unavailable/replaced bridge behavior and declared capability matrix. |
| HARD-04 / P1 | HF-17; HARD-02/03 | Specify and deliver manual whole-tab move/park/restore with exact source/destination and preview; stable identity/routing/focus, collision handling, rollback and uncertain-outcome reconciliation. Include explicit rename/close contract gaps. |
| HARD-05 / P1 | Existing #368, #338 | Persist bindings without manual per-agent enrollment; preview/recover exact conversations after layout restoration; duplicate/repeated recovery safe, non-Codex tabs preserved. Don't wait for automatic sorting if holding is not a real dependency. |
| HARD-06 / P1 | #466/#475, #478/#500 | Exercise installed ordinary-shell WSL/PowerShell/API/MCP discovery → prompt → ack → selected output → reconnect/result, native slash interaction, self-limits and interruption continuity. No new model calls until an explicit bounded acceptance packet. |
| HARD-07 / P1 | Plan0197, #402, #488/#498 | Extend shared typed help/reference/parity coverage to tabs/session controls. Document every capable interface and local-only/unsupported exception; completion must remain read-only and bounded. |
| HARD-08 / P1 | H3, #343/#350/#371/#380/#413 | Reconcile acceptance evidence and current installed identity for existing parents; amend stale projections and propose precise remaining criteria, not blanket reopen/close. |
| HARD-09 / P2 | #406–#411, #476 | Packaged flow recovery/unknown conditions/foreach/join/cancellation/accounting smoke with retained intent, plus honest Grok mode/capability reporting. Use synthetic seams first; separately qualify provider boundaries. |
| HARD-10 / P2 | HF-32 after manual movement | Optional automatic organization only after manual control is dependable; debounce, manual overrides, visible pause/disable and restart non-repetition. |

Each successor needs one accountable owner (ecochran76 / primary), a scoped branch,
current dependencies, red-capable public seam, source identity, exact installed
prefix and acceptance evidence. Keep at most three lanes; serialize common
root/registry/schema/CLI changes. The review itself opens no implementation lane.

## Hardening acceptance standard

For each selected feature, record separately: specified, implemented, integrated,
installed, operationally qualified. Name supported backends (Byobu/tmux/psmux;
Codex/headless Grok), callers (WSL/actual PowerShell/API/MCP), default discovery,
all normal outcomes, stale/ambiguous/offline/unsupported outcomes, replay and
reconnect behavior, help/completion and rollback. Acceptance uses the public
installed entrypoint with ordinary user defaults; injection-only adapter tests
cannot prove host integration. Use the existing journal/inventory/session owners.
Preserve credentials/history, native processes, work and cumulative accounting.
Run focused local checks; widen only for changed risk. Skip paid hosted CI.

## Recommended execution order

HARD-01 then HARD-02 is the first bounded outcome: the operator can list the real
workspace and preview/apply/undo useful grouping. HARD-03 qualifies psmux alongside
it; HARD-07 shares the same contracts. Next, refine HF-17/manual CRUD and implement
#368 recovery, while HARD-06 proves the codex-bots critical path. HARD-08 reconciles
existing tracking evidence throughout. Flows/automatic policies follow working
manual lifecycle. No generic new framework is required.

## Review evidence and definition of done

Completed: scoped specs, current issue/PR readbacks, existing acceptance receipts,
source flow inspection and installed read-only probes reconciled into this map.
Current main20e396b; deployed sourceaaf619c. P207 fix4e6fe79 remains on a separate
unmerged branch and must not be mistaken for an installed migration-command fix.
Original tab audit directly verified the two installed failures above. Other
acceptance rows cite historical qualification; no new full suite/provider/native
restart/reboot was run for this documentation review. Documentation diff checks
and link validation recorded at commit closeout. Raw transient issue readbacks
remain outside Git; no private account identifiers/credentials copied here.

Memory disposition: forbidden; no explicit request to write memory.
