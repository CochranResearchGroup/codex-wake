# Plan 0263 | Tab management parity

State: OPEN
Owner: primary / ecochran76
Branch: feat/issue-743-tab-management
Spec: #743
Base: 265d6fd1dc2734b23eac785fb6cbd97b729e7b9a
Related work: #716, #540, #568

## Current State

The design interview is complete. The operator approved the scope, target semantics, placement, formatting, launch, movement, pane I/O, and mutation outcomes.

## Agreed scope

- The controller API, CLI, and MCP cover inspection, creation, rename, reorder, formatting, pane capture, pane input, and destruction for authorized terminal tabs across terminal sessions, including background tabs.
- Byobu/tmux and native Windows psmux have equivalent acceptance behaviors and separate installed evidence.
- A single-pane tab may resolve its pane automatically. For a split tab, expose pane identities and require a selection for capture or input. Text submission is explicit.
- Destruction identifies the exact tab and affected panes and may end active processes. Parking is available to preserve live attachments while moving them to a holding workspace.

## Placement and formatting

- Create and move accept before or after an exact tab, plus first or last in a named terminal session. If the anchor disappears, return a stale-target result without applying a different placement.
- Creating, moving, renaming, or formatting a background tab preserves current focus. Focus is a separate action.
- Explicit per-tab formatting persists across automatic formatting passes until cleared. Rename and formatting remain independent.

## Launch, style, and movement

- Create supports a shell or a saved launch profile and an optional working directory. With no profile, use the destination session's default shell. An unsupported launch profile is reported before creating the tab.
- Formatting overrides cover foreground, background, and supported text attributes. Inspect and clear are available. Rename owns the title, and pane splits and sizing belong to layout.
- A live move within one terminal server preserves running processes, including across terminal sessions. An independent server is an unsupported destination for a live move. Conversation reopen across servers is a separate operation.

## Pane I/O and mutation outcomes

- Read returns the visible screen by default. Callers can request a bounded amount of scrollback. Write accepts literal text and named keys. Enter and submission are explicit.
- Resolve the exact pane at dispatch. If it has disappeared or been replaced, return a stale-target result.
- Destruction closes the underlying tab, all linked appearances, and its live panes. Preview identifies all affected sessions and panes. Unlink removes a single appearance. See [ADR 0008](../../adr/0008-tab-destruction-and-unlink.md).
- An interrupted mutation returns an operation ID and an unknown outcome until the controller can establish what occurred. Input and destruction are never replayed automatically after an unknown result.

## Out of scope

Cross-server live moves, pane layout editing, and operations against existing live tabs during acceptance.

## Acceptance and completion

Exercise these cases through the installed controller API, CLI, and MCP on real dedicated Byobu/tmux and native Windows psmux test tabs. Retain independent evidence per backend.

1. Find and inspect a tab in another terminal session. List panes, capture visible output and bounded scrollback, and send literal text without submitting it. Send an explicit key separately and verify the addressed pane received it.
2. Create a tab using the destination default shell and using a saved launch profile with a selected working directory. Verify first, last, before, and after placement, exact rename, and stable focus while working in another session.
3. Reorder and move a live tab within one server while preserving its processes. Verify missing anchors and cross-server destinations are rejected before a layout change.
4. Set and inspect a manual formatting override, run the automatic formatting pass, clear the override, and verify the chosen title survives throughout.
5. Unlink one appearance of a shared test tab and verify its processes survive. Preview and explicitly destroy a populated shared test tab, then observe closure of the stated panes and appearances.
6. Replace a pane between inspection and input dispatch and verify the stale identity is rejected. Interrupt a client result and verify operation-ID readback without a second input or destruction request.

Completion requires equivalent outcomes on all three public surfaces, with backend limitations reported explicitly. Implementation starts after the design is confirmed for delivery.

## Execution ledger

| Ticket | Dependencies | Owner | State |
| --- | --- | --- | --- |
| #744 Create, rename, place, move, and focus | None | primary | validated, tracker closed |
| #745 Inspect and read or write exact panes | None | pane745 | validated, tracker closed |
| #746 Formatting overrides | None | format746 | validated |
| #747 Unlink and destroy | #745 | destroy747 | validated, tracker closed |

Primary owns placement, lifecycle and shared client contracts. Pane worker owns capture/input and operation readback. Formatting worker owns per-tab override storage and rendering. Coordinate any shared file hunks with primary and integrate serially. Tests use the existing public paths and dedicated real tabs only.

## Placement checkpoint

Primary implementation `37637250cbb3fb62a90a6da583b233a902657cd0`. Explicit shell launch can bypass a saved profile or argv default. Existing callers that rely on saved launch defaults retain that behavior. An unsupported native profile is refused before creating a shell fallback.

The 31-test source selection passed on Python 3.11 and 3.12. Final installed wheel passed 28 tests over real tmux lifecycle, CLI/MCP, saved profiles, and terminal-session defaults. The existing native psmux acceptance runner passed all seven checks, including installed CLI relative create, MCP reorder without focus change, HTTP focus, native PowerShell access, explicit cross-server refusal, and empty final owned namespace. An initial broader run reached public parity before timing out during close. Its failure is retained with the passing fresh run.

Pane worker source `a2846f18ec934939129d89bb49d7d2ec9151e46c` integrated as `58334e507cdfdfe744f7348f55cb5a7238c97ccf`. Installed parity passed on real tmux and native Windows psmux. The scoped runner verified CLI visible capture and literal paste, MCP exact capture and explicit Enter, and protected controller bounded scrollback. Split and stale pane refusal plus lost-result readback are covered by public regressions.

## Format and destruction checkpoints

Formatting source checkpoints `1d15484b`, `f35c7533`, `e895c89a`, and `0d2be796` are integrated. They add persistent overrides, exact linked appearances and a portable client correction. The installed Windows frontend rerun passed.

The destruction worker's `44006a86905cffbafe5b761a2404cabe1944f526` integrated as `f0809ad1` after preserving both schema additions in the shared contract. Existing public tests on real tmux verified unlink with live pane survival, cross-session preview, stale membership refusal, explicit destroy, and lost-result readback without replay. Installed native psmux acceptance passed all eight checks with no remaining owned test sessions. Its native link operation creates an independent window, pane, and process, so a shared unlink is explicitly unavailable there. Exact standalone native destruction passed.

The integrated affected selection (tab contract, controller tabs, lifecycle, CLI, profile create, terminal sessions, native psmux and formatting) passed 62 tests on Python 3.11 and 3.12. Generated unified contract and command coverage were regenerated.

Installed formatting acceptance passed five checks on real tmux and six on native Windows psmux. Native Windows CLI proved override set through the controller API and inspect/clear through OAuth MCP. The installed psmux path proved explicit styling survived an automatic pass. The exact portable rerun wheel SHA256 is `93ac480b8fc4e401f314fd1aaffb2eb060f495dc0c26828775728bfdebd03f48`. Private receipt hashes are `11146de24f4dbaa16f0cfe6814d8849f52c317a92b419528ee95deda95a2229f` (tmux) and `98e0687af935a6713f71228fd15e1ddec2d5acc56304d0159add5428399e66e2` (psmux).
