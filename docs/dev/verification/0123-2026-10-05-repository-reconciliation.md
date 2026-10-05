# Repository reconciliation

User-directed reconciliation after requested remaining-gate acceptance. Baseline
origin/main516661f9291f1feefcf2d6e010ff5ed153b8cf63 / merged PR218. This changes
repository routing and custody records; no runtime/service/release effect.

## Verified Git cleanup

Original checkout was feat/p63-receipt-restore/e107ee3, with only the pre-existing
untracked note0003. All nine auxiliary checkouts were clean; each exact head
matched its remote branch and merged PR source, with its squash integration
receipt reachable from origin/main. Removed normally without force. All source
branches remain retained as provenance. Original checkout switched to main and
fast-forwarded by31 commits; note0003 byte hash was identical before/after.

| Retained branch | Exact remote checkpoint | Merged PR |
| --- | --- | --- |
| docs/p63-backup-closeout | 559ae16a86bc9e3f7c56a9d585cbe211ad624043 | 201 |
| feat/p63-backup-recovery | 0e7c94655c55b51b96468972a31ecfd02bc8d4d6 | 200 |
| feat/p63-held-recovery | 928effef29648d1c082e94ef6c482b073cab5ffd | 204 |
| docs/p63-million-checkpoint | 5fced75d5a18758563f779bd077d52cf69237bf1 | 205 |
| feat/p63-quiesced-restore | 9d9cb867c1e0d737225609b2b3d63e4cee2ad34a | 202 |
| docs/p63-reboot-checkpoint | 5fc8d7ea8be308dcc3ef8a9aca7ce8a4fd7ce743 | 199 |
| docs/p63-restore-closeout | 75d8efd2a7a58e18a27bf31272289b10755598de | 203 |
| feat/p63-retention-lifecycle | 95f68c749f688a4e3a596464b780c9823bc97c20 | 197 |
| docs/p63-500k-checkpoint | 8e757eb5d4fbde31cd691ddb77e9ec4138043f71 | 196 |

Private before/after custody receipts:
/home/ecochran76/.local/state/codex-wake/reconciliation/20261005T032012Z

## Retained older branch custody

At inventory time, all78 local branch refs were inspected:58 match their remote refs exactly,
20 have no corresponding current remote ref, and none differ from an existing
remote ref. Those older source/checkpoint refs are preserved without deletion
or automatic publication. Exact ancestry and matching PR metadata are recorded
in retained-local-only-refs.json. A verified repository-refs.bundle preserves
all refs under the private custody receipt directory; it is local backup custody,
not proof those20 refs were published. No older lane is reactivated.

## Canonical routing corrections

P63 catalog now points to accepted source branch docs/p63-soak-closeout, checkpoint
5c394af and integration516661f/PR218. Installed acceptance points to0122, and
previous offline-admission source/PR211 remain explicitly recorded separately.
Parent Plan0101 also reflects this accepted custody and labels its expired goal
authority/initial state historical. The catalog plan_ref points to the retained
reconciliation follow-up source containing that corrected parent header.
Branch retention is intentional; no implementation checkout is required.
Plan0119's current summary reflects completed requested gates and the remaining
wider scope, while its original baseline/execution decisions are labeled historical.

AGENTS.md contained29 links to nonexistent policy files0022-0050. Removed those
broken pointers; all21 existing adopted policy files and bodies remain unchanged.
No bundle upgrade, policy-body retirement or new policy authority was introduced.

## Validation and scope

Every retained policy pointer resolves locally. The first pre-merge lane audit
read the old default-ref catalog; a post-merge audit caught the parent plan header
still naming held recovery. Preserve that failure privately; the follow-up aligns
parent plan and plan_ref, then audits the actual candidate ref before publishing.
The final published catalog-only lane audit verifies
matching local/remote custody and integration; an integrated_cleanup_pending
advisory denotes deliberately retained source refs, not an open checkout.
Git diff whitespace check passes. Hosted Python3.11/3.12 gates govern integration
of this docs/routing correction. Source acceptance remains verification0122;
issue181 remains OPEN for its wider retained obligations. Historical evidence,
capabilities and journals are not reset or deleted. The untracked note remains
outside this commit.
