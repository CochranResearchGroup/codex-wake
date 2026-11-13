# P230 | Specialist bot families and identifiable terminal tabs

## Problem Statement

Operators cannot reliably identify which bot specializes in a product, account or
task, who supervises it, or why its terminal tab exists. Agent-spawned tabs become
scattered and transient presentation is confused with durable bot identity.

## Solution

Persistent specialist bot families: ChatGPT specialist -> account specialist ->
task/ticket-graph specialist. Codex-bots owns identity, inherited expertise and
supervision; Codex Wake organizes client-specific tabs with background placement,
muted family accents, clear scope labels, navigation and acceptance-based cleanup.

## User Stories

1. As an operator, I want durable root specialist bots, so expertise persists.
2. As a parent bot, I want account-specialist children, so work stays scoped.
3. As an account bot, I want task/ticket-graph children, so concurrent tasks remain distinct.
4. As an operator, I want every child to have its own identity, so reopening a tab preserves history.
5. As a child bot, I want inherited guidance automatically, so creation needs no repeated setup.
6. As a child bot, I want existing delegable context/access reused, so approved work starts without approval friction.
7. As an operator, I want genuinely new accounts/permissions held, so inheritance does not expand authority.
8. As a child, I want parent guidance updates on my next turn, so expertise stays current.
9. As a child, I want local specialization preserved, so inheritance retains my focus.
10. As an operator, I want active turns unchanged by guidance updates, so execution stays predictable.
11. As a parent, I want to assign and inspect child work, so supervision is actionable.
12. As a parent, I want to accept results and request pause/stop within existing authority, so lifecycle is controlled.
13. As an operator, I want one shared workers session per terminal server, so tab proliferation is contained.
14. As an operator, I want adjacent-to-parent placement as an override, so local workflows remain possible.
15. As an operator, I want nested workers grouped by original root, so families stay recognizable.
16. As an operator, I want muted family accents and account/task labels, so family and specialization are visible.
17. As an operator, I want error/attention indicators distinct, so family color does not hide intervention needs.
18. As an operator, I want parent/root navigation, so I can follow supervision relationships.
19. As an operator, I want newly spawned tabs in the background, so focus is preserved.
20. As an operator, I want primary-tab reuse per client/environment, so repeated opens do not duplicate tabs.
21. As another client, I want my own attachment, so shared bot identity does not conflate clients.
22. As an operator, I want manual moves and adopted tabs respected, so automation does not fight me.
23. As a parent, I want only explicitly temporary tabs cleaned after accepted results, so failed or unfinished work remains inspectable.
24. As an operator, I want empty managed workers sessions removed, so ephemeral clutter disappears.
25. As an operator, I want children retained when a root tab closes, so presentation loss does not terminate work.
26. As an operator, I want bot identity and history retained after tab cleanup or retirement, so outcomes remain attributable.

## Implementation Decisions

- A bot has a stable ID, optional parent ID, derived root ID, scope kind
  (specialist/account/task), scope reference/label and explicit temporary flag.
  Parentage is acyclic; an unknown parent is rejected; root IDs are derived, not trusted.
- Existing Bot records and clients remain valid without hierarchy fields. Expertise
  and granted context narrow through parentage; no credential copying or budget renewal.
- A Wake family registry stores metadata and exact client/environment attachment
  bindings separately from durable bot identity. It confers no provider authority.
- Frozen exchange descriptor: bot_id, parent_bot_id (nullable), name, scope_kind,
  scope_ref (nonsecret identifier), temporary (default false). Wake derives root_bot_id.
  Registration is idempotent for equal descriptors and rejects conflicting parentage.
- Binding key is bot_id + client_id + environment. Attachment stores workspace,
  window_id and pane_id, with backend/server and observed generation as needed.
  Reuse requires live exact attachment evidence, never a title or working directory guess.
- Public Wake operations use the existing tab command/API path: family register,
  list, show, open, accept, adopt and focus. Register ancestors before descendants.
  Open uses existing named sessions/lifecycle; default workers session is server-scoped,
  create/open runs detached, family tabs are contiguous without displacing manual holds.
- Adjacent override uses the exact parent attachment in the same environment.
  Missing parent presentation retains bot lineage and reports root-tab-unavailable.
- Accept names the exact immediate parent and child/result; only temporary, accepted,
  live owned tabs are eligible for close. Failed/unfinished/adopted tabs remain.
  Unknown native outcomes are reconciled rather than replayed; history is not deleted.
- Display reads registered metadata, uses compact account/task labels and deterministic
  muted family accents through existing reversible decoration. Opt-outs/manual holds
  remain effective; error/attention styling takes precedence.
- Codex-bots exposes child creation/inspection/supervision through existing service
  interfaces. Before starting a turn, inherited guidance is recomputed and local
  additions retained; the snapshot is fixed for the active turn.
- An explicitly configured Wake adapter registers the ancestry and opens/reuses the
  exact bot conversation attachment. Existing installations without the adapter keep
  their prior behavior. Existing native ownership/binding checks remain mandatory.
- Task dependencies remain task-graph edges, distinct from bot parentage. Parent
  closure or retirement never implicitly cancels descendant work.

## Testing Decisions

- Use existing Bot service commands and Wake public tab command/API boundaries.
  The task directives approve proceeding with these established seams.
- Tests assert externally visible identity, inherited guidance, placement, focus,
  reuse, redaction/labels, acceptance and preserved history through current harnesses.
- Use the existing lightweight synthetic bot/native service harness and disposable
  real tmux sessions where physical placement is the acceptance criterion. No new
  fixture projects/frameworks, provider journeys, credential copies or live bots.
- Preserve observed red/green commands. Validate each ticket after integration before
  unlocking dependents. Local affected tests satisfy CI; no paid hosted runs.
- After all implementation tickets close: one broad Standards/Spec review of the
  frozen integration diff, one bounded TDD remediation pass for accepted findings,
  then focused verification only. Keep findings and first failures attributable.

## Out of Scope

Live deployment, real account enrollment, provider calls, credential-provider changes,
new authority/budgets, native daemon rebuilds, arbitrary shell-created tab adoption,
automatic task cancellation, deleting conversation history, broad architecture cleanup,
new test frameworks and repeated review/hardening loops.

## Further Notes

Operator approved the complete design and directed ticket publication/delegated
execution. One coordinator owns the joined delivery, with one integration branch
per participating Git repository. GitHub implementation tickets close after their
integrated PR acceptance; parent spec remains open. Merge needed for that acceptance
is part of requested ticket closure; production deployment remains out of scope.
Fixed review bases: Wake e8c79a79da0b0482e2403e634394c70f5c66e333;
Bots origin/main is recorded in the execution ledger before workers start.
