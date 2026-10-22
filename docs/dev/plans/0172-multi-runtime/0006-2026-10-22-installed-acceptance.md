# MR-06: Qualify the installed Codex and Grok workflow

State: PLANNED
Owner: ecochran76
Work item: CW-MR-172/MR-06 (local draft; not posted)
Priority: First-release dependency order
Blocked by: MR-04, MR-05
Specification: [Plan0172](../0172-2026-10-22-multi-runtime-wake.md)

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
