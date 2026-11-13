# P231 single broad review

Frozen source: Wakeaaf21dfa against17e2c3fe; Bots7e16e59 against1e315c3.
Commands: git diff BASE...TARGET; git log BASE..TARGET --oneline per repository.
Independent workers /root/p231_standards_review and /root/p231_spec_review completed;
primary inspected exact causal paths and accepted the three findings below.

## Standards

STD-1 P1 blocking: child supervision admission lacks the desktop-control and
private-auth holds used by ordinary chat/participant dispatch. Direct send/stop
can bypass those holds. Rule: Bots docs/auth-receipts.md Ownership and existing
desktop/session/foreground-input guard. Reuse normal admission before pending
operation, retaining read-only inspect. No other consequential Standards finding.

## Spec

SPEC-1 P1 blocking: connected peer delivery bypasses prepareBot; proxy send copies
cached context. Next-turn inherited guidance must be refreshed before capture,
with active-turn and uncertain-delivery protections retained.
SPEC-2 P2 blocking: null child model override means inherit, but Object.assign
replaces ancestor model with null and falls back to runtime defaults. Merge
nearest nonnull lineage value per setting.

No Wake blocker identified. These are candidate findings reconciled by primary,
not unverified reviewer output. One TDD remediation pass targets exactly these
three IDs. No second broad review. Missing optional Bots policy0022 in its frozen
tree is a source-availability note, not a code finding. No CONTRIBUTING/CODING_STANDARDS
files found. Provider/live installation were out of scope, not failed acceptance.

Accepted findings: Standards1(P1); Spec2(highestP1). Verification follows the
single remediation result; initial findings remain retained after correction.

## Focused remediation verification

One TDD pass fixed all three accepted IDs at Bots19129412; each observed red
before green. Coordinator reran only accepted blockers:5PASS0FAIL0SKIP1.176s.
Module syntax and diff checks PASS. PR78 mergeda9e868fd. No second broad review.
Initial findings remain above; unresolved accepted findings:none.

Accepted findings: Standards1(P1), Spec2(highestP1); all corrected and integrated.
