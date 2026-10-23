# MR-06: Qualify the installed Codex and Grok workflow

State: CLOSED
Ticket state: DONE
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

The user explicitly approved Codex/Grok interop reruns to solve the bug and close
this ticket on2026-10-23. This supersedes the earlier one-launch-only gate for
bounded diagnostic tests. Each run remains at most six original synthetic prompts
and300 seconds including cleanup; new sessions/bus/intents, no uncertain-work
replay or production mutations. Primary owns the sole ready ticket; no subagents.

Real installed sample8 PASS33.623s: four prompt attempts, two visible responses
in each TUI, authenticated claims and correlated replies in both directions,
zero introduced/unattributed runtime processes and no changed pre-existing
runtime generations. Codex0.164.0 / Grok1.0.40. Rebuilt candidate digest and
all original failures are retained in the verification and machine receipt.
Full local1455 tests PASS310.046s, zero failures/errors, one expected opt-in
systemd skip; frozen source/tests unchanged. Installed changed-axis61 PASS9.249s.
The omitted-isolation first full run remains retained as non-qualifying.

## Outcome

The first-release workflow is reproducible through an isolated installed CLI/MCP surface, with exact versions, bounded live evidence and a usable capability/support matrix.

## Scope

Build/install an isolated candidate, run required compatibility and acceptance checks, preserve failed samples and produce a source-bound acceptance receipt. Document use, recovery and unsupported modes.

## Non-goals

Do not publish a release, deploy into the user tool prefix, mutate production grants/buses/services or claim other runtimes are qualified as a side effect of testing.

## Acceptance Evidence

- [x] AC1–AC7: each criterion has an independent pass/fail/not-qualified verdict tied to exact versions and method.
- [x] Exercise both real visible TUIs and bidirectional A2A; fixtures/queue acceptance alone cannot pass live criteria.
- [x] Run required changed-surface/compatibility checks with declared environment and record exclusions.
- [x] Retain source/installed identity, run scope, original failures and owned-process cleanup readback.
- [x] Publish user-facing capability/support/recovery documentation, with any production rollout left as an explicit separate action.

## Repository Surface and Risks

Installed acceptance harness, packaging candidate, support documentation and retained sanitized evidence.

Release and installation into the production prefix remain distinct effects. Failure on one axis preserves unaffected samples but cannot promote the whole release to accepted.

A complete slice requires its stated evidence. Source completion, integration,
installed acceptance and external publication remain separate states.


## Retained failures and closeout

Remote resume rejects per-client permission overrides and empty threads lack
persisted rollout history. The fresh remote TUI now creates its own verified
thread. Guest wall regression is handled by explicitly selecting the existing
network-first policy on a new private bus, preserving the failed old checkpoint.
Helper claim output and CLI dispatch-envelope parsing were corrected with red/
green tests. Terminal acceptance now permits one second of read-only observation
for the original marker; it never pastes twice or changes the original deadline.
Sample8 passes the original interop scenario; samples1–7 retain original verdicts.
Source checkpoint759d700, full suite and installed controls qualify the candidate.
Support/recovery matrix is published. Main integration, CI, release and production
installation remain separate; no external GitHub issue was posted or closed.
[Verification](../../verification/0172-2026-10-22-mr06-installed-acceptance.md).
