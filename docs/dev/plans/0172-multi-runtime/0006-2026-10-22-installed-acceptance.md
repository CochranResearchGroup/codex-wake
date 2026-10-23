# MR-06: Qualify the installed Codex and Grok workflow

State: OPEN
Ticket state: IN_PROGRESS
Owner: ecochran76
Work item: CW-MR-172/MR-06 (local draft; not posted)
Priority: First-release dependency order
Blocked by: MR-04 and MR-05 source/isolated-artifact gates satisfied
Specification: [Plan0172](../0172-2026-10-22-multi-runtime-wake.md)

Lane: P172-MR06
Branch: test/mr06-installed-acceptance
Base: 651d493
Target: origin/main
Integration: squash_pr

## Current execution

The user's “ok go” after the MR-06 ready closeout authorizes this bounded live
acceptance. Primary owns the only ready ticket; no independent nonblocked ticket
exists to delegate. The accepted121 modules, wheel and non-editable installation
match exactly; prior1451-test qualification remains source-bound and retained.

Live envelope: one disposable private Codex app-server/TUI and one Grok TUI,
at most six original synthetic prompts,300 seconds including cleanup, one owner,
no replay or extra launch. Default auth coordination is reused without copying
secrets or changing production config; native configured MCPs are disabled for
the private server. Only new private sessions, bus, actor capabilities and runtime
bindings are created. Grok's Bash tool is limited to the exact probe/work helper
commands; inherited session context and ancestry are observed, never synthesized.
A refusal/uncertainty stops the path with retained evidence; source fixes or further
live qualification are not inferred from a failed sample.

## Outcome

The first-release workflow is reproducible through an isolated installed CLI/MCP surface, with exact versions, bounded live evidence and a usable capability/support matrix.

## Scope

Build/install an isolated candidate, run required compatibility and acceptance checks, preserve failed samples and produce a source-bound acceptance receipt. Document use, recovery and unsupported modes.

## Non-goals

Do not publish a release, deploy into the user tool prefix, mutate production grants/buses/services or claim other runtimes are qualified as a side effect of testing.

## Acceptance Evidence

- [ ] AC1–AC7: each criterion has an independent pass/fail/not-qualified verdict tied to exact versions and method.
- [ ] Exercise both real visible TUIs and bidirectional A2A; fixtures/queue acceptance alone cannot pass live criteria.
- [ ] Run required changed-surface/compatibility checks with declared environment and record exclusions.
- [ ] Retain source/installed identity, run scope, original failures and owned-process cleanup readback.
- [ ] Publish user-facing capability/support/recovery documentation, with any production rollout left as an explicit separate action.

## Repository Surface and Risks

Installed acceptance harness, packaging candidate, support documentation and retained sanitized evidence.

Release and installation into the production prefix remain distinct effects. Failure on one axis preserves unaffected samples but cannot promote the whole release to accepted.

A complete slice requires its stated evidence. Source completion, integration,
installed acceptance and external publication remain separate states.


## Retained sample and current gate

One Codex and one Grok launch stopped in6.338s: Codex pane exited before capture,
zero conversation prompts and no bus/grants/bindings/wakes. Original immediate
cleanup retained one introduced process; later OS readback finds it gone, preserved
as a separate observation. The exact Codex exit cause remains unconfirmed.

Provider-free launcher repair retains dead panes/errors, explicitly scopes resume
flags, verifies wheel/module identity and snapshots launcher source before input.
One real tmux startup-evidence regression passes; no second live launch occurred.
The recorded recipient envelope is consumed. A proposed extension is one additional
Codex+Grok pair, at most six synthetic prompts and five minutes including cleanup,
no replay. This needs its response before launch. MR-06 remains IN_PROGRESS.
[Verification](../../verification/0172-2026-10-22-mr06-installed-acceptance.md).
