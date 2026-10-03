# A2A identity and enrollment

State: CLOSED
Lane: P63
Parent: Plan 0101 / P63.2
Depends-On: Plan 0100 accepted in PR #182
Work-Item: https://github.com/CochranResearchGroup/codex-wake/issues/181
Branch: feat/p63-identity-mailbox
Target: origin/main
Owner: primary

## Scope

Implement owner-only bus initialization, immutable bus/root binding, versioned
SQLite policy authority, explicit enrollment, operator capability, and exact
thread capability issuance/validation. Canonical namespace derives from the
server's initialize.codexHome and the exact thread's modelProvider, never the
launcher's inherited pane. CLI context remains a claim validated against the
existing daemon and the explicitly issued actor capability.

An operator-issued capability identifies one bus, namespace, thread, enrolled
root, and actor generation. Its secret digest is stored in the journal; the
secret file is private and never emitted in receipts. No arbitrary --from
bypass. Same-UID filesystem access is not a security isolation boundary; peer
content cannot confer enrollment or operator authority through product APIs.

No automatic notification or production enrollment in this packet. Store
fixtures use disposable directories and no providers. Mailbox implementation
follows identity qualification under the same campaign, with a separate bounded
packet and the frozen identity API.

## API and ownership

BusStore.configure creates a fresh private bus with an operator secret. Opening
existing state is nondestructive and rejects unknown schema, wrong ownership,
symlinks, network filesystems, or a copied canonical root. Enroll/issue/pause
mutations require the configured operator capability and append attributable
receipts. Actor capability checks require a matching runtime identity, cwd
within its exact enrolled root, and unchanged generation. Revocation is explicit.
Cross-root permission defaults false and automatic delivery defaults unavailable.

## Acceptance and definition of done

Provider-free tests prove explicit grants, token mismatch, parent/child claims,
wrong runtime namespace, root denial, revocation, private modes, copied-root
rejection, schema refusal, and failed store opens without implicit creation.
Installed CLI/operator qualification and hosted integration follow the mailbox
API packet; no P63 completion from these tests alone.

## Execution bounds

One owner and one dependent implementation lane. Two implementation attempts,
one consolidated review/rework pass. Checkpoint this packet; campaign stop
before 750,000 goal tokens remains applicable. No live runtime restart.

## Identity checkpoint

Bus identity/capability library and explicit operator CLI are implemented. Core
policy schema is version 1; mailbox domain version 1 now has an explicit operator migration.
Configure starts paused, cross-root disabled unless explicitly selected, and
notification capability unqualified. No peer body or discovery result grants
operator authority. Actor grants are explicit and are published before their
transaction commits. Failed issuance rolls back its actor authority; enrollment
receipts from an earlier committed operator step remain visible on failure.

Independent review: /root/identity_review completed one bounded read-only
drift_discovery pass. Sole candidate F1 was accepted blocking: generic filesystem
errors hid committed enrollment receipts. Primary reproduced the failing
regression, preserved partial_receipt_ids/reconciliation_required in that error
path, and verified it passes. Conformance had no separate candidate. No second
broad review; mailbox/delivery remained outside this frozen review.

Focused bus tests: 16 pass; CLI tests including F1: 5 pass before the final
invoking-context case. Installed disposable operator configure/enroll/resume/
pause/status passed, with no actors issued and no production roots enrolled.
Existing-daemon metadata supplies server codexHome and thread modelProvider.
Hosted integration and full mailbox API acceptance remain pending.

Hosted integration: PR #183 merged at 2026-10-03T18:19:14Z after Python 3.11/3.12 success (run 37143648918). Canonical commit 42893b190eb19c30dc702b2377893b1ba5736b88. Parent Plan 0101 remains OPEN.
