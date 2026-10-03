# A2A receipt restore and guarded publication

State: CLOSED
Lane: P63
Owner: primary
Parent: Plan 0101 / issue #181
Branch: feat/p63-receipt-restore
Target: origin/main
Integration: squash_pr

## Current State

PR #187 integrated foreground workflow at 24ddf11224a06c2b11764b66b8031be6242364c6.
Receipt replay lacks a durable restore descriptor and daemon evaluation does
not require an A2A source guard. This packet owns exact restore and guarded
publication. Automatic delivery remains unqualified.

## Scope

Persist a nonsecret exact bus/message/actor-generation descriptor in the arm.
Restore only against explicitly supplied authorized mailbox and actor; never
open paths or enroll actors merely because an arm names them. Add a bounded
runner for existing source reconstruction injection and require its guard before
daemon publication. Test restart, generation/root mismatch, revoked cached
evidence, malformed arms and repeated replay without duplicate firing.

## Non-goals and successor

No live notification, default root enrollment, daemon actor impersonation,
service or provider effect. Production configuration, long-suspension CLI and
installed restart proof remain in the full campaign after this restore seam.
This is one dependent implementation unit, not a replacement acceptance goal.

## Bounds and acceptance

Primary serialized lane, two implementation attempts, one targeted repair;
no new broad review allowance. Limit replay to 100 receipts and arms to 100.
Affected tests, full suite and explicit no-dispatch daemon restart fixture.
Done only when exact descriptor validation and revocation prevent publication,
and a restored authorized runner can replay and publish one durable firing.
Full Plan 0101 remains OPEN. Cumulative ceiling 1,500,000, checkpoint 1,400,000.

## Closeout

Exact descriptor, explicit reconstruction seam and source-guarded publication
implemented. Verification 0100 records the reproduced pre-fix defect, 824 tests
and installed resource evidence. Only this restore/guard unit is accepted;
production resolver, CLI and installed long-suspension acceptance remain
successor work. Integration is separate from local acceptance.
