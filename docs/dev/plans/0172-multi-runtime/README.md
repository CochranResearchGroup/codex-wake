# Multi-runtime ticket drafts

Governing specification: [Plan0172](../0172-2026-10-22-multi-runtime-wake.md).
Local intake: CW-MR-172. Owner: ecochran76. Tracker: GitHub
CochranResearchGroup/codex-wake; these are local drafts, not posted issues.

Each ticket owns its slice outcome and references the specification's acceptance
criteria. Replace local locators with exact issue links only during authorized
tracker publication. A draft's readiness is separate from live-effect authority.

| ID | Ticket | Blocked by | State |
| --- | --- | --- | --- |
| MR-01 | [Qualify exact open Grok delivery](0001-2026-10-22-qualify-grok.md) | None | READY for preparation; live run scope required |
| MR-02 | [Preserve Codex through the runtime seam](0002-2026-10-22-codex-runtime-seam.md) | MR-01 | PLANNED |
| MR-03 | [Deliver a durable open-Grok wake](0003-2026-10-22-grok-wake.md) | MR-02 | PLANNED |
| MR-04 | [Cross-runtime request and reply](0004-2026-10-22-cross-runtime-a2a.md) | MR-03 | PLANNED |
| MR-05 | [Busy policies and terminal fallback](0005-2026-10-22-busy-and-fallback.md) | MR-03 | PLANNED |
| MR-06 | [Installed acceptance](0006-2026-10-22-installed-acceptance.md) | MR-04, MR-05 | PLANNED |

One implementation slice at a time. MR-04/MR-05 can be reasoned about
independently, but shared delivery/authority writes are serialized. No external
tracker assignment, sub-issue relationship or label is claimed.
