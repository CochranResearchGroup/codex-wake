# Plan0139 closeout — COMPLETE

The two approved repairs are shipped in0.11.1. Notification instructions now
require accepted-work ownership before processing/completed acknowledgment.
Tab-close inventory distinguishes receipt publication from pending notification
work and retains actual uncertain/malformed work holds.

| Gate | Observed outcome |
| --- | --- |
| Public red/green U1 live and saved pointers | claim_required reproduced; accepted then completed PASS |
| Public red/green U2 inventory/ordinary close | inventory_unavailable reproduced; terminal inbox/cancelled delivery close PASS |
| Preserved safety guards | uncertain notification and damaged actor attribution still hold |
| Serial review | Standards0blocking; Spec1resolved,0remaining; no independent review claim |
| Installed controls | focused107PASS61.239s; source PYTHONPATH unset |
| Actual result consumption | recipient native turn completed, accepted claim and terminal completed receipt, no reply |
| Actual ordinary close | separate terminal-inbox control closed forced=false on same explicit bus |
| Actual uncertainty hold | original ordinary close refused; exact uncertainty preserved; explicit cleanup forced=true |
| Artifact parity | all81package files match source/wheel/sdist/final prefix/tested candidate |
| Activation | four CLI links active0.11.1; all13service PID/state snapshots unchanged |
| Owned cleanup | both test panes and three owned PIDs absent; bus paused; clean published worktree closed |

PR233 https://github.com/CochranResearchGroup/codex-wake/pull/233,
source/integration/tag2e87f664dea6ef3bdc7b37d004f60f8748638af0;
feature checkpoint2679baa7373e841703a2140932ddc13e5dbc5e1a retained remotely.
Release https://github.com/CochranResearchGroup/codex-wake/releases/tag/v0.11.1.
Immutable prefix ~/.local/share/codex-wake/releases/0.11.1-2e87f66.
Downloaded released assets verified against build hashes in activation.json;
private release-parity.json retains per-fileSHA256. Prior0.11.0 immutable prefix
and old link targets retained for rollback. No unrelated service restart.

The original notification msg_887eda3fcdd64d35a6113df4677212a0 remains uncertain
although its actual recipient completed processing. Public reconcile only reports
held_for_exact_evidence. This release does not clear that uncertainty, resend it,
or qualify transport submission. Its precise next step is a separately bounded
investigation of notification visibility reconciliation, preserving original
attempt_891fb92c107d4bd189fcb05c242632f7 and native completed-turn evidence.
Plan0138 failed records remain untouched; broader Plan0101/0119 stay OPEN.
Hosted CI waiting waived by user; no comprehensive-suite or hosted-CI pass claimed.

Old plan127 checkout retained because fresh /proc readback shows active owners;
this is distinct from the newly closed P69 checkout. Raw capabilities, native
histories, logs and operator receipts remain private under
~/.local/state/codex-wake/plan0139/. Installed-acceptance.md identifies public
seams and controlled test IDs; cleanup-os-readback.json and worktree-cleanup.json
retain fresh workstation evidence.

Memory disposition: unavailable. Narrow discovery returned no reviewed Codex Wake
Graphiti group suitable for this qualified closeout; machine-readable non-write
receipt retained privately as memory-disposition.json. No memory write attempted.
