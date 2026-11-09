## Standards

Frozen review58b1631 against3a02f9d. Primary adjudication:

- R1 / P2 / blocking: rollback-hold test sleeps300ms although a monitor cycle may take2s; no post-rollback cycle is proved. Verified existing test and policy0016 requirement to use explicit readiness signals. Replace elapsed-sleep assumption with public cycle-completion evidence.
- R3 / P3 / nonblocking_backlog accepted for this bounded cleanup: TabFormatting.apply accepts unused automatic flag. AST/source confirms it is never read; remove misleading argument without new behavior tests.
- R4 / P3 / nonblocking_backlog accepted for this bounded cleanup: native bridge validation/execution duplicate the exact managed-option tuples. Consolidate within standalone bridge; preserve finite vocabulary and standalone packaging.

## Spec

- R2 / P2 / blocking: rollback/reset can mutate a saved window newly linked into another workspace. Requirement518: stale identities never affect another namespace; linked windows are documented as held. Primary independently reproduced on a disposable real tmux server: linked=True, rollback returned rolled_back, other workspace option changed. Preserve retryable baseline, report partial linked_window and perform no window writes until unlinked.

One-line summary: Standards3 accepted (highestP2); Spec1 accepted (highestP2). Two blockers; two optional maintenance judgments included in the same bounded remediation, no extra broad review.
