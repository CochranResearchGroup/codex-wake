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
| MR-03 | [Deliver a durable open-Grok wake](0003-2026-10-22-grok-wake.md) | MR-02 satisfied | DONE — source, isolated artifact and live terminal acceptance |
| MR-04 | [Cross-runtime request and reply](0004-2026-10-22-cross-runtime-a2a.md) | MR-03 satisfied | DONE — source and isolated artifact |
| MR-05 | [Busy policies and terminal fallback](0005-2026-10-22-busy-and-fallback.md) | MR-03 satisfied | DONE — source and isolated artifact |
| MR-06 | [Installed acceptance](0006-2026-10-22-installed-acceptance.md) | MR-04/MR-05 source gates satisfied | DONE — installed candidate and real bidirectional TUI path qualified |

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

MR-03 wave: primary owns the only ready ticket; zero subagents. The source
candidate adds schema7, host-approved Grok bindings and weak terminal evidence.
Two setup probes sent zero conversation prompts and cleaned up, but saw no
active session. The user-approved extra probe PASSED: one prompt, exact bound
recipient and reply, no replay, clean teardown in13.996s. Full-suite QA stays open. MR-04/MR-05 stay blocked. [Verification](../../verification/0172-2026-10-22-mr03-grok-wake.md).

MR-03 final reconciliation: frozen full1438 PASS/one expected skip in462.612s,
source/tests unchanged; all119 production modules match the live-qualified wheel.
Test-only repair9fd40a0 preserves guards. Prior failures remain retained, including
the unclassified historical backup-create error. MR-03 DONE; MR-04/MR-05 READY
for the next parallel wave. MR-06 remains blocked. Main/release/production separate.

MR-04/MR-05 parallel wave reconciled: primary MR-04, independent `/root/mr05`
MR-05; separate worktrees, serial integration, one repaired lock finding verified.
Sourceef8b5b4/final wheel:1451 full PASS341.346s/one expected skip, unchanged
source/tests; final installed changed-axis15 PASS. Both source slices DONE;
MR-06 READY for real TUI/bidirectional live evidence. No production effects.
[Combined receipt](../../evidence/plan0172/mr04-mr05-runtime-wave.json).

MR-06 update: one live pair failed during setup in6.338s, zero conversation
prompts, no bus/grants/wakes. Corrected harness startup regression1 PASS.
[Retained failure and next envelope](../../verification/0172-2026-10-22-mr06-installed-acceptance.md).


MR-06 final: source759d700, installed candidate live sample8 PASS33.623s with
four original prompt attempts, two responses per real TUI and authenticated
claims/correlated replies in both directions. Full1455 tests PASS310.046s, one
expected opt-in skip; installed61 PASS9.249s. Historical failures retained.
MR-01–MR-06 candidate gates complete; broader program/main/CI/release/production
and additional runtime qualification remain separate.


Integration readback: PR306 squash merged at dbc2dff; integration issue305 CLOSED.
Both required Python3.11/3.12 release gates passed CI40014889364 on head7c02df6,
whose tree equals canonical main. Initial stale-catalog smoke failure retained;
installed smoke contracts now explicitly require32 tools and five named Grok tools.
Release/production and additional runtime capabilities remain separate.
