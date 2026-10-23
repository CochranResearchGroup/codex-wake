# MR-05: Apply explicit busy policies and qualified terminal fallback

State: PLANNED
Ticket state: READY
Owner: ecochran76
Work item: CW-MR-172/MR-05 (local draft; not posted)
Priority: First-release dependency order
Blocked by: MR-03 satisfied
Specification: [Plan0172](../0172-2026-10-22-multi-runtime-wake.md)

## Outcome

The operator can choose wait, verified queue or authorized interruption, and can permit automatic last-resort terminal delivery through an approved profile, with accurate outcomes on both runtimes.

## Scope

Extend the MR-03 delivery route with the full policy/method decision contract. Qualify runtime/version UI recognition, protected composer checks, generation rechecks and method-specific evidence.

## Non-goals

Do not silently interrupt, switch methods after possible prior submission, infer permissions from terminal content, claim dequeue expiry that a runtime cannot enforce or submit into an unknown UI.

## Acceptance Evidence

- [ ] AC3: wait is default; queue/interrupt selections either meet their declared guarantees or refuse before effects.
- [ ] AC4: native-unavailable pre-I/O fallback is allowed only by the host-approved profile.
- [ ] AC4/AC5: possible prior submission blocks switching until definitive reconciliation; missing evidence never proves not-sent.
- [ ] AC4: terminal observed acceptance is exposed separately from native queue/receiver evidence; ambiguous input is not replayed.
- [ ] AC5: nonempty composer, shell/permission prompts, version drift and replaced process/session bindings hold/refuse without input.

## Repository Surface and Risks

Runtime policy selection, terminal host/recognizer, delivery journal, host profiles and public-interface fault controls.

Queue deadlines and interruption ownership vary by runtime. No generic capability may be advertised from one successful method on one version.

A complete slice requires its stated evidence. Source completion, integration,
installed acceptance and external publication remain separate states.
