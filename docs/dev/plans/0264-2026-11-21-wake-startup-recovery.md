# Plan 0264 | Wake startup recovery

State: IN_PROGRESS
Owner: primary / ecochran76
Work items: #723 and #742
Spec: #749

## Current State

The operator confirmed that the wake service owns recovery and reconciliation
at startup. The operator approved readiness and placement fallbacks, same-harness
restoration, Wake Codex account continuity, and heuristic tab reclamation. The
design decisions below are settled.

## Agreed behavior

- On startup, automatically re-arm eligible recurring schedules with no
  unresolved delivery. Reconcile interrupted occurrences from retained intent
  and delivery evidence.
- Continue a provably unsent occurrence only while it remains eligible.
  Preserve its original identity, deadline, and missed-run policy. Retain
  accepted delivery outcomes without replay.
- Hold only the unresolved occurrence when evidence cannot settle delivery.
  Report why and expose a supported reconciliation action. Independent wakes
  continue. Future occurrences follow the existing overlap and missed-run policies.
- Resolve delivery eligibility before restoring the exact saved conversation.

## Tab restoration

- Report restoration readiness separately. A blocked restoration does not prevent
  delivery to a verified live attachment of the exact saved conversation.
- Capture terminal session, tab name, and position. For example, a tab displayed
  as `13: wk-grok` in the main Byobu session makes slot 13 a strong candidate
  after reboot when the saved placement and current presentation agree.
- Resume the exact conversation with its previous harness and working directory.
  A Wake Codex session reuses its saved profile and the same account. If that
  binding is unavailable, report the gap and hold restoration.
- Reuse a verified live attachment of the exact conversation even if the tab
  moved or was renamed. For an idle candidate, rank it using the saved terminal
  session, title, position, and the pane's observed working directory. A matching
  working directory corroborates placement, especially when title or position
  drifted. Verify pane ownership and idle placeholder status before reclaiming
  the position. Preserve the original shell when reclaiming its slot.
- Leave tabs with other work or ambiguous ownership intact. Create a new tab
  using the saved placement and naming fallbacks.
- Recreate a missing terminal session from its saved definition. Append when an
  anchor is gone and report actual placement. Hold when the destination session
  cannot be recovered. For a name collision, choose a unique restored name and
  report it.

## Restored tab presentation

- Keep the tab title and any existing Codex Bots family accent and immediate-parent
  label. Render a small **↻** marker beside the title on a restored tab, including
  a new tab created when the original slot is occupied.
- Clear the marker on the first explicit focus. Preserve the **Restored by Wake**
  record and the actual placement in tab inspection after the marker clears.

## Acceptance

Restart an isolated supervisor with clean, provably unsent, accepted, and unknown
occurrences. Verify automatic re-arming and one eligible delivery without manual
reconciliation. Keep the unknown result scoped and show the operator why it is
held. Separately verify exact tab restoration after isolated terminal loss,
including exact placement, mild layout drift with matching working directory,
and an occupied slot where another pane uses the same working directory.
Verify preservation of harness and Wake Codex profile/account. Check that the
restoration marker clears on explicit focus while inspection retains provenance
and placement, and that the title and bot family accent survive.

## Definition of done

Pass the isolated restart and tab-restoration acceptance cases through the
public surfaces, with matching startup, placement, and delivery evidence.

## Out of scope

Changes to existing production wakes or terminal sessions during design.

## Execution ledger

Integration branch `feat/issue-749-wake-recovery`, base `a1dbceed656c4c906f87b280185b9d8cdb5c7904`.

| Ticket | Blockers | Owner | State |
| --- | --- | --- | --- |
| #750 Startup recovery | None | primary | Validated locally at `9beac576` |
| #751 Binding and readiness | None | readiness751 | Source `97f1db94`, integrated and validated at `22eb8b9e` |
| #752 Exact tab restoration | #750, #751 | restore752 | Running from `22eb8b9e` |
| #753 First-focus marker | #752 | Unassigned | Pending |

Startup recovery hands versioned poll evidence to the existing durable
record-level dispatcher. Unversioned poll holds still require exact-token
reconciliation when their delivery effect cannot be proved. An empty firing
directory alone cannot clear one. A native delivery with durable uncertainty
retains its original occurrence and follows the schedule's overlap policy.

Local Python 3.12 supervisor scheduling tests passed (7 tests). A public
recurring schedule regression verified that an uncertain delivery retains its
identity and reason across scheduler generations while an independent
schedule materializes exactly once.

The supervisor, recurring schedule, native intent and native delivery selection
passed 66 tests on Python 3.12, including the disposable supervisor process
qualification. The comparable Python 3.11 source selection passed 65 tests
with the project dependencies installed in a disposable environment. A raw
Python 3.11 attempt lacked websockets and was superseded by that run.

The integrated binding, runtime mode and recurring schedule selection passed
34 tests on Python 3.12. The #751 worker also passed 24 CLI, API, MCP and
contract tests. Binding verifies the pinned account home and reports provider
login identity as unverified. Real restored delivery is part of #752.
