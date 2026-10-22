# Multi-runtime ticket drafts

Governing specification: [Plan0172](../0172-2026-10-22-multi-runtime-wake.md).
Local intake: CW-MR-172. Owner: ecochran76. Tracker: GitHub
CochranResearchGroup/codex-wake; these are local drafts, not posted issues.

Each ticket owns its slice outcome and references the specification's acceptance
criteria. Replace local locators with exact issue links only during authorized
tracker publication. A draft's readiness is separate from live-effect authority.

| ID | Ticket | Blocked by | State |
| --- | --- | --- | --- |
| MR-01 | [Qualify exact open Grok delivery](0001-2026-10-22-qualify-grok.md) | None | DONE — managed-launch terminal observation |
| MR-02 | [Preserve Codex through the runtime seam](0002-2026-10-22-codex-runtime-seam.md) | MR-01 satisfied | DONE — source and isolated wheel |
| MR-03 | [Deliver a durable open-Grok wake](0003-2026-10-22-grok-wake.md) | MR-02 satisfied | READY |
| MR-04 | [Cross-runtime request and reply](0004-2026-10-22-cross-runtime-a2a.md) | MR-03 | PLANNED |
| MR-05 | [Busy policies and terminal fallback](0005-2026-10-22-busy-and-fallback.md) | MR-03 | PLANNED |
| MR-06 | [Installed acceptance](0006-2026-10-22-installed-acceptance.md) | MR-04, MR-05 | PLANNED |

On “next ticket”, the primary owns one ready ticket and delegates one other ready
ticket per independent subagent, within runtime capacity. MR-04/MR-05 can run
independently with explicit write ownership and serialized integration of shared
delivery/authority changes. No external
tracker assignment, sub-issue relationship or label is claimed.

Wave 1 history: primary owned MR-01; zero other ready tickets and zero
subagents. Two disposable launches required sign-in. Protocol availability is
observed, live delivery is not qualified. Restore interactive Grok authentication
and rerun MR-01; ending the probe did not unblock MR-02.

Authenticated rerun: one already-open TUI accepted one prompt and displayed the
marker response; session UUID and process generation match before/after.
MR-01 DONE with managed-launch terminal observation; MR-02 READY. Native control
and authenticated receipts remain unqualified. No MR-02 work or subagent began
during the rerun; the next ticket wave starts from this frontier.

MR-02 wave: primary owned the only ready ticket; zero subagents. Source and
isolated wheel controls pass through the version1 runtime seam. MR-02 DONE;
MR-03 READY from the retained source checkpoint. Main integration, release and
production installation remain separate. [Verification](../../verification/0172-2026-10-22-mr02-runtime-seam.md).
