# MR-05: Apply explicit busy policies and qualified terminal fallback

State: CLOSED
Ticket state: DONE
Owner: ecochran76
Work item: CW-MR-172/MR-05 (local draft; not posted)
Priority: First-release dependency order
Blocked by: MR-03 satisfied
Specification: [Plan0172](../0172-2026-10-22-multi-runtime-wake.md)

Lane: P172-MR05
Branch: feat/mr05-runtime-policies
Base: 36412c4
Target: origin/main
Integration: squash_pr

## Current State

Worker `/root/mr05` source packetdd2ca6d is integrated as1cf56a7. Primary added
shared CLI/MCP selection and authority guards; reconciled sourceef8b5b4 qualifies
the combined artifact. Frozen1451 PASS341.346s/one expected skip, installed changed
axis15 PASS5.140s, lint PASS. MR-05 DONE for source and isolated artifact; MR-06
READY for actual visible TUI acceptance. No provider or production effects.

## Outcome

The operator can choose wait, verified queue or authorized interruption, and can permit automatic last-resort terminal delivery through an approved profile, with accurate outcomes on both runtimes.

## Scope

Extend the MR-03 delivery route with the full policy/method decision contract. Qualify runtime/version UI recognition, protected composer checks, generation rechecks and method-specific evidence.

## Non-goals

Do not silently interrupt, switch methods after possible prior submission, infer permissions from terminal content, claim dequeue expiry that a runtime cannot enforce or submit into an unknown UI.

## Acceptance Evidence

- [x] AC3: wait is default; queue/interrupt selections either meet their declared guarantees or refuse before effects.
- [x] AC4: native-unavailable pre-I/O fallback is allowed only by the host-approved profile.
- [x] AC4/AC5: possible prior submission blocks switching until definitive reconciliation; missing evidence never proves not-sent.
- [x] AC4: terminal observed acceptance is exposed separately from native queue/receiver evidence; ambiguous input is not replayed.
- [x] AC5: nonempty composer, shell/permission prompts, version drift and replaced process/session bindings hold/refuse without input.

## Repository Surface and Risks

Runtime policy selection, terminal host/recognizer, delivery journal, host profiles and public-interface fault controls.

Queue deadlines and interruption ownership vary by runtime. No generic capability may be advertised from one successful method on one version.

A complete slice requires its stated evidence. Source completion, integration,
installed acceptance and external publication remain separate states.


## Reconciled acceptance

Primary coordinator sourceef8b5b4 qualifies this slice for source and isolated
artifact: frozen1451 tests PASS341.346s/one expected skip, unchanged source/tests,
final installed changed-axis15 PASS5.140s and lint PASS. Independent source packet
is retained, with shared CLI/MCP and authority corrections owned by the primary.
No packet ref alone is a merge-ready claim. MR-06 is READY for real visible TUI and
bidirectional live acceptance; native Grok caller attestation remains unqualified.
Production installation, main integration and release remain separate.
