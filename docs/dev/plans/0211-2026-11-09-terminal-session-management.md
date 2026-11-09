# Terminal session management and criteria-based tab relocation

State: OPEN
Owner: primary / ecochran76
Work item: #526; implementation #527–#534
Branch: feat/terminal-sessions-526
Domain authority: GLOSSARY.md

## Current State

Operator approved all seventeen design decisions and explicitly invoked spec,
ticket publication and implementation. Spec #526 and eight vertical tickets
#527–#534 are published with native dependencies. Primary owns #527; independent
#528 is delegated. The execution ledger owns readiness, custody and review counts.
Public seams are existing controller CLI/API/MCP and disposable native adapters,
as agreed in the interview; no new interface choice needs operator input.

Graphiti discovery: skip; supplied current conversation, deployed source and its
canonical receipts provide the decisions needed for this bounded interview.
Memory disposition: forbidden; no explicit memory-write request.

## Scope and non-goals

Specify session create/list/show/update/delete, human-readable discovery and
selection, moving tabs by explicit selection or criteria, and saved categories.
Keep CLI/API/MCP behavior equivalent; qualify Byobu/tmux and psmux independently.
Do not change terminal layouts, launch codex-bots, stop sessions, implement code,
merge or deploy during this interview. Stock Codex remains independent.

## Confirmed requirements

- Session CRUD is required, alongside existing tab management.
- Development and bot tabs can occupy distinct named terminal sessions.
- Tab relocation supports arbitrary categories or selection criteria.
- Users should not need opaque workspace IDs for ordinary use.
- A logical group/view is distinct from moving tabs between terminal sessions.

## Verified starting capabilities

Read-only source check: discovery already retains native session names as labels;
local CLI accepts unique labels for source and destination. Current listing still
obscures that affordance. TabLifecycle provides tab CRUD and same-server tmux moves,
not terminal session CRUD. Moving the final tab is refused; closing the last tab
removes the native session. No durable empty-session abstraction exists. Native
psmux cross-session moves are explicitly unsupported because sessions have separate
servers and repeating window/pane IDs; no conversation restart may be substituted
and described as moving a running tab. Evidence: tab_workspace_discovery.py,
tab_commands.py, tab_lifecycle.py and tab_psmux_bridge.py in deployed source cb7cf62.

## Settled decisions — round 1

Operator accepted all five recommendations:

1. Names are the ordinary interface; omitted selection infers the current terminal
   session, ambiguity offers an interactive picker, and scripts can select explicitly.
2. A saved session definition survives having no tabs. Recreate its native container
   when needed; distinguish running and empty states.
3. Plain delete removes an empty session. Populated deletion requires an explicit
   destination for its tabs or an explicit instruction to terminate them.
4. Moves preserve panes, processes and conversations, including running turns, and
   do not switch focus by default. Unsupported continuity is reported, not simulated
   by restarting or copying conversations.
5. Saved categories support preview/apply relocation and optional continuous routing.
   Enable continuous routing explicitly per rule.

Architectural consequence: saved session identity/lifecycle is distinct from native
container liveness; see docs/adr/0003-saved-terminal-session-lifecycle.md.

## Settled decisions — round 2

Operator accepted all six recommendations:

6. Session names are unique within a terminal server; qualify host/backend when
   ambiguous. Rename preserves identity and references. Reusing a retired name
   never redirects old rules to the replacement session.
7. Editable metadata includes description, labels, default directory, launch
   profile/command and formatting preferences. Launch defaults affect new tabs;
   updates do not restart existing tabs or change their accounts.
8. Select explicit tabs, saved groups and custom labels; combine criteria with
   AND/OR/NOT, exact matches and patterns. Unknown traits match only explicit
   unknown criteria.
9. Preview freezes a bulk selection. Apply rechecks identities, preserves completed
   moves and reports moved/failed/uncertain outcomes. Reconcile uncertainty before
   retry; undo completed moves only where original destinations remain compatible.
10. First matching routing rule by explicit priority wins. Conflicting equal-priority
    rules hold the tab and explain the conflict.
11. Manual movement holds automatic routing for the tab until explicitly resumed.
    Pins also prevent automatic relocation.

## Settled decisions — round 3

Operator accepted all six recommendations:

12. codex-bots creates or reuses its dedicated `bots` session and places its own
    bot tabs there. It leaves `default` alone. Repeated launch does not duplicate
    or restart existing bots merely because the session exists.
13. Discover existing native sessions without requiring registration. Show them
    immediately; save management settings when first edited. Preserve running
    tabs and existing native settings unless explicitly changed.
14. Enabling continuous routing previews existing matches and moves them only
    when explicitly included. Require configurable trait stability before later
    state-driven moves. Preserve manual holds across restart and reconcile
    unfinished moves before creating new effects.
15. Delete disables dependent destination rules with a visible explanation.
    Complete the requested drain/termination before deleting; partial success
    retains the session. Keep history and never let old rules silently recreate
    a deleted session.
16. Ordinary CLI lists use readable tables showing session name, backend,
    running/empty state, tab count and activity/health summaries. Interactive
    ambiguity can open a picker. Scripts/API/MCP get structured candidates and
    errors; noninteractive calls never wait for input.
17. Undo preserves subsequent manual placement. Restore only tabs still in the
    placement produced by the original operation, report skipped conflicts,
    and put successfully undone tabs on routing hold.

## Design tree and current frontier

Root: terminal session CRUD and tab relocation.
Settled round1: names/inference, durable empty sessions, explicit populated deletion,
continuity-preserving moves, on-demand and opt-in continuous routing.
Settled round2: scoped names/stable rename, defaults, composable selection, partial
bulk outcomes/conditional undo, rule priority/conflicts, manual routing holds/pins.
Settled round3: launcher reuse, automatic discovery/adoption, routing backfill and
stability, delete dependencies/partial drain, human/machine interfaces, undo conflicts.
Frontier: empty. Next step: operator confirmation of the consolidated understanding;
then derive the formal specification and tickets under subsequent task scope.

Backend capability facts remain implementation qualification, not operator
questions or permission gates. First delivery uses the WSL authority and existing
Byobu/tmux capabilities. psmux session operations require independent qualification;
current cross-server whole-tab movement stays explicitly unsupported, with no
replacement process/conversation presented as a successful move. Windows-native
hosting remains a separate roadmap milestone.

## Consolidated intended workflow

- List terminal sessions by recognizable name; discover `default` immediately.
- Create/show/edit/rename/delete named sessions; keep empty saved definitions.
- codex-bots creates/reuses `bots` without disturbing development tabs.
- Preview explicit or criteria-selected tabs, then apply process-preserving moves.
- Save categories/rules and opt into continuous routing where desired.
- Explain conflicts, unknown traits, held/pinned tabs, unsupported backend actions
  and per-tab partial/uncertain outcomes. Reconcile before retry; undo conditionally.
- All controller surfaces share operation semantics. Existing workspace IDs remain
  internal compatibility selectors; ordinary use relies on names/current context.

## Acceptance criteria and definition of done

Interview done when every branch is settled, backend facts are checked and the
operator confirms the shared understanding. Update this plan and GLOSSARY as
terms settle; record ADRs only for consequential tradeoffs meeting the skill's
criteria. A later spec/ticket packet owns executable acceptance and implementation.

## Execution bounds

One primary design lane; a read-only delegated fact check may verify backend
capabilities. No implementation workers. Next action: confirm consolidated understanding before formal
specification/ticketing. No runtime tests needed for these documentation-only changes.
