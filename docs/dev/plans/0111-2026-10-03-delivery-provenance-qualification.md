# Delivery runtime provenance qualification

State: CLOSED
Lane: P63
Owner: primary
Parent: Plan 0101 / issue #181
Branch: feat/p63-delivery-qualification
Target: origin/main
Integration: squash_pr

## Current State

Receipt arming integrated in PR #190, main 9c3bbe8. Full campaign remains OPEN.
Delivery verification 0098 has release-source evidence but no installed binary
provenance or composer/client authority proof. Previous turn was outcome_progress.
The new active goal meter starts at zero with the operator's explicit 500k stop
threshold. Preserve older meters as history; checkpoint by 450k on this meter,
never reset work-unit/review allowances. Latest instruction governs this stop.

## Scope and authority

One serialized read-only qualification packet compares the installed executable
against the official versioned release asset and its published digest, then
reviews exact-source delivery ownership and installed metadata. No turn, queue,
resume, actor enrollment, service, private transcript or provider mutation.
Downloads stay in temporary state; curated hashes and locators go in verification.
No subagents. Write surface: this plan, verification, parent and runbook.

## Acceptance, bounds and non-goals

At most one release asset download (90 seconds), one hash comparison and bounded
metadata observation. Record whether binary identity and release-source mapping
are proven separately from composer ownership and actual safe-operation proof.
No schema/source observation alone qualifies a notification. Freeze an actionable
next gate instead of repeating the prior vague qualification loop.

## Definition of done

An attributable provenance verdict removes or precisely confirms the installed
identity blocker. Full Plan 0101, actual delivery and suspension stay OPEN until
all original acceptance requirements are established. Checkpoint after packet.

## Closeout

Installed binary identity is proven against the official release asset and
release source mapping; verification 0103 records hashes and limits. Isolated
installed reader successfully observed the existing shared daemon. Prior
provenance and apparent daemon-unavailability blockers reduced; composer/client
ownership and named disposable live-effect scope remain unmet. No broad review
or effect allowance renewed. Progress classification: blocker_reduction.
